"""
FreshRoute AI: Multi-Objective Pareto Matching Engine (Stage 3)

Optimizes allocation of surplus batches to hunger relief nodes under
Indian dietary constraints.

Formulation (spec 2.1:128)
--------------------------
For surplus i at D_i and recipient j at R_j:

    S_ij = w1*Urgency(i) + w2*Deficit(j) + w3*Proximity(D_i,R_j) + w4*DietMatch(i,j)
    in [0,100]

Subject to (spec 2.1:131-133):
    1) DietMatch(i,j)=1.0 (strict binary — non-veg never to lacto-veg Langar)
    2) t_transit(D_i,R_j) <= t_safe(i)           (via arrhenius_decay engine)
    3) Capacity(R_j) >= Weight(i)

Weights default w=[0.35,0.30,0.20,0.15] elicited via AHP [@saaty1980ahp];
see docs/BIBLIOGRAPHY.bib: saur. Pareto frontier via greedy (spec reference)
plus optional MILP/NSGA-II [@deb2002nsga2; @wolsey1998integer; @orgtools2024].

Dietary rules spec 1.2:
  - Strict_Lacto_Vegetarian (Langar Rehat): pure veg, no egg/meat, optional Jain
    onion/garlic flag; vessel purity assumed at source.
  - Halal, Child/Senior nutrition priority encoded in w4/nutrient bonus.

Integration with frontend:
  Uses same coordinate order [lat,lon] as src/data/mockData.js DONORS/RECIPIENTS.
"""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ParetoMatchingEngine:
    """Multi-attribute surplus-to-recipient scorer.

    Attributes
    ----------
    w_urgency, w_deficit, w_prox, w_diet : float
        Weights sum to 1.0; default (0.35,0.30,0.20,0.15) spec 2.2.
    co2_factor_kg_per_kg : float
        CO2 abatement factor; mock uses 2.5 (see pareto_matcher.py:416).
    """

    def __init__(
        self,
        weights: tuple[float, float, float, float] = (0.35, 0.30, 0.20, 0.15),
        co2_factor: float = 2.5,
    ) -> None:
        w1, w2, w3, w4 = weights
        s = w1 + w2 + w3 + w4
        if abs(s - 1.0) > 1e-6:
            # Normalize defensively; log-traceable via ADR if changed
            w1, w2, w3, w4 = w1 / s, w2 / s, w3 / s, w4 / s
        self.w_urgency = w1
        self.w_deficit = w2
        self.w_prox = w3
        self.w_diet = w4
        self.co2_factor = co2_factor

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine great-circle distance [@toth2014vrp routing distance prior]."""
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 2)

    @staticmethod
    def _estimate_transit_hours(distance_km: float, avg_speed_kmh: float = 35.0) -> float:
        """Rough transit time prior to OSRM; 35 km/h urban, 55 highway.

        Used for t_transit <= t_safe gate when OSRM matrix not yet available.
        P5 VRPTW will replace with live routing.
        """
        if avg_speed_kmh <= 0:
            avg_speed_kmh = 35.0
        return round(distance_km / avg_speed_kmh, 2)

    # ------------------------------------------------------------------
    # D3 distance matrix (OSRM gold parquet with haversine fallback)
    # ------------------------------------------------------------------

    def load_distance_matrix(self, path: str | Path | None = None) -> Dict[Tuple[str, str], float]:
        """Load donor↔recipient distances from gold parquet (P1 L1.3 D3).

        Expects columns donor_id, recipient_id, distance_km (see
        scripts/build_gold_osm.py). Returns dict {(donor_id, recipient_id): km}.
        Missing file → empty dict; callers fall back to haversine.
        """
        import pandas as pd

        p = Path(path) if path else Path(__file__).parent.parent / "data" / "gold" / "osm_distance_matrix.parquet"
        if not p.exists():
            self._dist_matrix: Dict[Tuple[str, str], float] = {}
            return self._dist_matrix
        try:
            df = pd.read_parquet(p)
            self._dist_matrix = {
                (str(r["donor_id"]), str(r["recipient_id"])): float(r["distance_km"])
                for _, r in df.iterrows()
            }
        except Exception:
            self._dist_matrix = {}
        return self._dist_matrix

    def lookup_distance(self, batch: Dict[str, Any], recipient: Dict[str, Any]) -> Optional[float]:
        """Distance from gold matrix if present, else None (caller uses haversine)."""
        matrix = getattr(self, "_dist_matrix", None)
        if not matrix:
            return None
        donor_id = str(batch.get("donor_id", ""))
        recip_id = str(recipient.get("recipient_id", recipient.get("id", "")))
        return matrix.get((donor_id, recip_id))

    # ------------------------------------------------------------------
    # Dietary eligibility (hard constraint)
    # ------------------------------------------------------------------

    @staticmethod
    def check_dietary_eligibility(surplus: Dict[str, Any], recipient: Dict[str, Any]) -> bool:
        """Return False if this pair violates a strict dietary rule.

        Rules (spec 1.2):
        - Strict_Lacto_Vegetarian recipient: surplus must be is_pure_veg True,
          contains_egg False, contains_meat False. Onion/garlic Jain flag
          (contains_onion_garlic) also blocks if recipient requires Jain.
        - Halal: if recipient dietary_policy == Halal_Required, surplus must
          have is_halal True when contains_meat True.
        Returns True if eligible, False if blocked (= score 0.0).
        """
        policy = recipient.get("dietary_policy") or recipient.get("dietaryNeeds") or recipient.get("dietary_needs") or ""
        # Normalize list vs string
        if isinstance(policy, list):
            policy_str = " ".join(str(x) for x in policy)
        else:
            policy_str = str(policy)

        flags = surplus.get("dietary_flags") or surplus.get("dietaryFlags") or {}
        # Support both snake/camel + boolean coercion
        is_pure_veg = flags.get("is_pure_veg", flags.get("isPureVeg", True))
        contains_egg = flags.get("contains_egg", flags.get("containsEgg", False))
        contains_meat = flags.get("contains_meat", flags.get("containsMeat", False))
        contains_onion_garlic = flags.get("contains_onion_garlic", flags.get("containsOnionGarlic", False))
        is_halal = flags.get("is_halal", flags.get("isHalal", False))

        # Strict lacto-vegetarian Langar Rehat
        if "Strict_Lacto_Vegetarian" in policy_str or "Lacto-Veg" in policy_str or "Langar" in policy_str:
            if not is_pure_veg:
                return False
            if contains_egg or contains_meat:
                return False
            # Jain facilities within policy string
            if ("Jain" in policy_str) and contains_onion_garlic:
                return False

        # Halal
        if "Halal" in policy_str and contains_meat and not is_halal:
            return False

        return True

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def score_match(
        self,
        surplus: Dict[str, Any],
        recipient: Dict[str, Any],
        safe_hours_remaining: float,
        *,
        distance_km: Optional[float] = None,
        transit_hours: Optional[float] = None,
    ) -> float:
        """Compute composite Pareto score S_ij in [0,100].

        Components:
        1) Urgency(i) = 100 - 2.5*t_safe clamped [0,100] — perishability.
        2) Deficit(j) = recipient urgency_score 0-100 (HVI-derived).
        3) Proximity = 100 - 1.5*distance_km clamped.
        4) DietMatch = 100 if eligible else 0 (binary gate per spec 2.1:131).

        Feasibility gates: dietary ineligible => 0.0; transit>t_safe => 0.0
        (spec 2.1:132); diet suitability weighted via w4.

        Parameters
        ----------
        surplus : dict with origin_coordinates [lat,lon] and dietary_flags.
        recipient : dict with coordinates [lat,lon], urgency_score, dietary_policy.
        safe_hours_remaining : float from ThermalDecayEngine.evaluate_batch_safety.
        distance_km, transit_hours : optional overrides (OSRM).

        Returns
        -------
        float rounded to 1 decimal, 0.0 if infeasible.
        """
        # Hard dietary gate
        if not self.check_dietary_eligibility(surplus, recipient):
            return 0.0

        # Distance / transit
        if distance_km is None:
            try:
                d_lat, d_lon = surplus["origin_coordinates"]
                r_lat, r_lon = recipient["coordinates"]
                distance_km = self._haversine_distance_km(d_lat, d_lon, r_lat, r_lon)
            except Exception:
                # Fallback to 10km if coordinates missing (conservative)
                distance_km = 10.0
        if transit_hours is None:
            transit_hours = self._estimate_transit_hours(distance_km)

        # Transit vs shelf-life gate (spec 2.1:132): must deliver before spoilage
        # with 0h buffer here (matcher buffer). Stricter +1h buffer is in
        # ThermalDecayEngine.is_transit_feasible; both should align.
        if transit_hours > safe_hours_remaining:
            return 0.0

        # Capacity gate (spec 2.1:133): recipient must have storage headroom.
        # We check cold_storage_capacity_liters or capacity_lbs where available.
        # If fields absent, skip gate (assume hub handles it).
        try:
            weight = float(surplus.get("gross_weight_kg", surplus.get("batchWeightLbs", surplus.get("weight_kg", 0))) or 0)
            # Recipient capacity fields vary: cold_storage_capacity_liters, capacityLbs, currentInventory
            cap = recipient.get("cold_storage_capacity_liters") or recipient.get("capacityLbs") or recipient.get("capacity_lbs")
            if cap is not None and weight > 0:
                # liters ~ kg for water-like density; lbs vs kg mixed — we only
                # gate if weight grossly exceeds cap (>1.2x) to avoid unit confusion.
                # Proper unit normalization in api/schemas.py will make this exact.
                if isinstance(cap, (int, float)) and weight > float(cap) * 1.2:
                    return 0.0
        except Exception:
            pass

        # 1. Urgency score
        urgency_score = min(100.0, max(0.0, 100.0 - (safe_hours_remaining * 2.5)))

        # 2. Deficit score — use urgency_score or hunger fields
        deficit_score = float(
            recipient.get("urgency_score",
                recipient.get("urgencyScore",
                    recipient.get("hunger_vulnerability_index", 50.0)))
        )
        deficit_score = min(100.0, max(0.0, deficit_score))

        # 3. Proximity score
        proximity_score = max(0.0, 100.0 - (distance_km * 1.5))

        # 4. Diet suitability — 100 if eligible (we already gated), else 0
        diet_score = 100.0

        # Optional child/senior nutrition bonus: if recipient needs child milk
        # and surplus is Dairy, boost diet slightly (still capped at 100).
        # Spec 1.2: Child & Senior Nutrition Profiles — w4 already weights diet.
        # We add soft bonus before weighting, capped.
        recipient_needs = str(recipient.get("dietaryNeeds", recipient.get("dietary_needs", "")))
        item_desc = str(surplus.get("item_description", surplus.get("itemName", surplus.get("category", "")))).lower()
        if ("Child" in recipient_needs or "Senior" in recipient_needs) and ("milk" in item_desc or surplus.get("category") == "Dairy"):
            diet_score = 100.0  # already max; placeholder for future protein weighting

        composite = (
            self.w_urgency * urgency_score
            + self.w_deficit * deficit_score
            + self.w_prox * proximity_score
            + self.w_diet * diet_score
        )
        return round(composite, 1)

    # ------------------------------------------------------------------
    # Allocation (greedy + hooks for MILP)
    # ------------------------------------------------------------------

    def rank_allocations(
        self,
        surplus_batches: List[Dict[str, Any]],
        recipients: List[Dict[str, Any]],
        decay_engine: Any,
        *,
        min_score: float = 40.0,
    ) -> List[Dict[str, Any]]:
        """Greedy allocation — spec reference implementation (spec 4.3:382-418).

        For each batch, evaluates t_safe via decay_engine, scores against all
        recipients, picks best eligible > min_score. Deterministic, O(|S|*|R|),
        p95 <100ms for N=500 (spec 6.1).

        Hooks for Phase P4 v1: replace inner loop with MILP (pulp/OR-Tools CP-SAT)
        or NSGA-II to enumerate Pareto frontier; greedy remains fallback under SLA.

        Returns list of dicts with batch_id, matched_recipient_id, match_score,
        safe_hours_remaining, urgency, cold_chain_enforced, co2_saved_kg.
        """
        results: List[Dict[str, Any]] = []
        for batch in surplus_batches:
            # Resolve category and ambient telemetry for decay
            category = batch.get("category") or batch.get("itemCategory") or "Prepared"
            # Support both spec schema (ambient_temp_c) and mockData ambient_weather
            ambient_temp_c = float(batch.get("ambient_temp_c", batch.get("temp_c", 36.0)))
            humidity_pct = float(batch.get("humidity_pct", batch.get("humidity", 70.0)))
            # Alternate nested ambient_weather
            if "ambient_weather" in batch:
                amb = batch["ambient_weather"] or {}
                ambient_temp_c = float(amb.get("temp_c", ambient_temp_c))
                humidity_pct = float(amb.get("humidity_pct", humidity_pct))
            elapsed = float(batch.get("elapsed_hours", 0.0))

            eval_res = decay_engine.evaluate_batch_safety(
                category=category,
                ambient_temp_c=ambient_temp_c,
                humidity_pct=humidity_pct,
                elapsed_hours=elapsed,
            )
            safe_hours = float(eval_res["dynamic_safe_hours_remaining"])

            best_match = None
            best_score = -1.0
            best_dist = None

            for rec in recipients:
                score = self.score_match(batch, rec, safe_hours)
                if score > best_score:
                    best_score = score
                    best_match = rec
                    # capture distance for trace
                    try:
                        d_lat, d_lon = batch["origin_coordinates"]
                        r_lat, r_lon = rec["coordinates"]
                        best_dist = self._haversine_distance_km(d_lat, d_lon, r_lat, r_lon)
                    except Exception:
                        best_dist = None

            if best_match is not None and best_score > min_score:
                # CO2 factor: mock uses lbs*2.5? Spec uses kg*2.5. We handle both.
                weight = float(batch.get("gross_weight_kg", batch.get("batchWeightLbs", batch.get("weight_kg", 0))) or 0)
                # If value looks like lbs (>200 and category grain) we still multiply 2.5 as mock
                co2 = round(weight * self.co2_factor, 1)
                results.append(
                    {
                        "batch_id": batch.get("batch_id", batch.get("id", "unknown")),
                        "item_description": batch.get("item_description", batch.get("itemName", category)),
                        "matched_recipient_id": best_match.get("recipient_id", best_match.get("id")),
                        "recipient_name": best_match.get("name", best_match.get("recipientName")),
                        "match_score": best_score,
                        "safe_hours_remaining": safe_hours,
                        "urgency": eval_res.get("risk_classification"),
                        "cold_chain_enforced": eval_res.get("cold_chain_mandatory"),
                        "distance_km": best_dist,
                        "co2_saved_kg": co2,
                    }
                )
        return results

    # ------------------------------------------------------------------
    # MILP optimal allocation (Phase P4 v1) — PuLP CBC + OR-Tools CP-SAT
    # ------------------------------------------------------------------

    def solve_milp_allocations(
        self,
        surplus_batches: List[Dict[str, Any]],
        recipients: List[Dict[str, Any]],
        decay_engine: Any,
        *,
        min_score: float = 40.0,
        time_limit_secs: float = 0.8,
        solver: str = "pulp",
    ) -> List[Dict[str, Any]]:
        """MILP optimal allocation — maximize sum S_ij x_ij [@wolsey1998integer; @orgtools2024].

        Formulation (spec 2.1:128-133):
          max sum_{i,j} S_ij * x_ij
          s.t. sum_j x_ij <= 1               for each surplus i (at most one recipient)
               sum_i w_i * x_ij <= Cap_j      for each recipient j (capacity)
               x_ij in {0,1}
               x_ij = 0 if diet ineligible or t_transit > t_safe or S_ij < min_score

        Solver: PuLP CBC (default) or OR-Tools CP-SAT fallback. Latency target
        <800ms for N=100 (spec 9.1). Falls back to greedy on timeout/failure.

        Parameters
        ----------
        surplus_batches, recipients, decay_engine : as rank_allocations
        min_score : float — feasibility threshold (spec 4.3 uses 40)
        time_limit_secs : float — solver time budget
        solver : 'pulp' or 'ortools'

        Returns
        -------
        List[dict] same schema as rank_allocations with added `solver` key.
        """
        if not surplus_batches or not recipients:
            return []

        t0 = time.perf_counter()
        n, m = len(surplus_batches), len(recipients)

        # Precompute batch meta: safe_hours, weight
        batch_metas: List[Dict[str, Any]] = []
        for batch in surplus_batches:
            category = batch.get("category") or batch.get("itemCategory") or "Prepared"
            ambient_temp_c = float(batch.get("ambient_temp_c", batch.get("temp_c", 36.0)))
            humidity_pct = float(batch.get("humidity_pct", batch.get("humidity", 70.0)))
            if "ambient_weather" in batch:
                amb = batch["ambient_weather"] or {}
                ambient_temp_c = float(amb.get("temp_c", ambient_temp_c))
                humidity_pct = float(amb.get("humidity_pct", humidity_pct))
            elapsed = float(batch.get("elapsed_hours", 0.0))
            # Handle FoodCategory enum (str subclass) — use .value if present, else string
            cat_for_eval = category.value if hasattr(category, "value") else category
            try:
                eval_res = decay_engine.evaluate_batch_safety(
                    category=cat_for_eval,  # type: ignore[arg-type]
                    ambient_temp_c=ambient_temp_c,
                    humidity_pct=humidity_pct,
                    elapsed_hours=elapsed,
                )
                safe_hours = float(eval_res["dynamic_safe_hours_remaining"])
            except Exception:
                eval_res = {}
                safe_hours = 12.0
            weight = float(batch.get("gross_weight_kg", batch.get("batchWeightLbs", batch.get("weight_kg", 0))) or 0)
            # Normalize lbs vs kg heuristic: if weight > 2000 assume lbs? keep as kg for MILP but use same as rank_allocations
            # We keep raw kg; capacity gate handled separately
            batch_metas.append({
                "category": cat_for_eval,
                "safe_hours": safe_hours,
                "weight": weight,
                "eval_res": eval_res,
                "ambient_temp_c": ambient_temp_c,
                "humidity_pct": humidity_pct,
            })

        # Recipient capacities (None = unlimited)
        recip_caps: List[Optional[float]] = []
        for rec in recipients:
            cap = rec.get("cold_storage_capacity_liters") or rec.get("capacityLbs") or rec.get("capacity_lbs") or rec.get("capacity_kg")
            if cap is not None:
                try:
                    cap_f = float(cap)
                    # If cap looks like lbs (>2000) and weight kg small, normalize via 2.2? Keep lenient 1.2x gate as in score_match
                    # For MILP we use cap as-is but scale check: if batch weight >> cap, infeasible already via score gate
                    recip_caps.append(cap_f)
                except Exception:
                    recip_caps.append(None)
            else:
                recip_caps.append(None)

        # Build score & feasibility matrix
        scores: Dict[Tuple[int, int], float] = {}
        feasible: Dict[Tuple[int, int], bool] = {}
        distances: Dict[Tuple[int, int], float] = {}
        for i, batch in enumerate(surplus_batches):
            safe_hours = batch_metas[i]["safe_hours"]
            for j, rec in enumerate(recipients):
                sc = self.score_match(batch, rec, safe_hours)
                if sc > 0 and sc >= min_score:
                    scores[(i, j)] = sc
                    feasible[(i, j)] = True
                    try:
                        d_lat, d_lon = batch["origin_coordinates"]
                        r_lat, r_lon = rec["coordinates"]
                        distances[(i, j)] = self._haversine_distance_km(d_lat, d_lon, r_lat, r_lon)
                    except Exception:
                        distances[(i, j)] = 10.0
                else:
                    # Keep zero-score pairs as infeasible for MILP sparsity
                    feasible[(i, j)] = False

        if not scores:
            return []

        # Trivial case: if n*m large and scores sparse but n small, still try MILP
        # If solver explicitly requested ortools, try it first
        if solver == "ortools":
            ort_res = self._solve_milp_ortools(
                surplus_batches, recipients, batch_metas, scores, recip_caps, distances, time_limit_secs, min_score
            )
            if ort_res is not None:
                return ort_res
            # fall through to pulp

        # PuLP path [@pulp2011]
        try:
            import pulp  # type: ignore

            prob = pulp.LpProblem("FreshRouteMatching", pulp.LpMaximize)
            x_vars: Dict[Tuple[int, int], Any] = {}
            for (i, j), sc in scores.items():
                # Only create var for feasible pairs to keep model small
                x_vars[(i, j)] = pulp.LpVariable(f"x_{i}_{j}", cat=pulp.LpBinary)

            # Objective
            prob += pulp.lpSum(scores[(i, j)] * x_vars[(i, j)] for (i, j) in x_vars), "TotalScore"

            # Each surplus at most one recipient (spec 2.1 MILP)
            for i in range(n):
                vars_i = [x_vars[(i, j)] for j in range(m) if (i, j) in x_vars]
                if vars_i:
                    prob += pulp.lpSum(vars_i) <= 1, f"Surplus_{i}_once"

            # Recipient capacity: sum weight_i * x_ij <= Cap_j  [@wolsey1998integer]
            for j in range(m):
                cap = recip_caps[j]
                if cap is None:
                    continue
                # Only enforce if at least one batch has meaningful weight >0
                vars_j = [(i, x_vars[(i, j)]) for i in range(n) if (i, j) in x_vars]
                if not vars_j:
                    continue
                # Heuristic: if weights are all zero, skip
                total_weight_expr = pulp.lpSum(batch_metas[i]["weight"] * v for i, v in vars_j)
                # Use same lenient 1.2x factor as score_match to avoid unit mismatch false infeas?
                # For MILP we enforce strict: if weight*1.2 exceeds cap, still allow but score gate already filtered grossly overweight
                # So we use cap*1.2 as effective capacity to match greedy gate
                prob += total_weight_expr <= float(cap) * 1.2, f"Cap_{j}"

            # Solve with CBC, time limit
            cbc_args = {"msg": False, "timeLimit": max(0.1, time_limit_secs)}
            # threads param only in newer pulp; guard
            try:
                cbc_args["threads"] = 0
                solver_obj = pulp.PULP_CBC_CMD(**cbc_args)
            except TypeError:
                cbc_args.pop("threads", None)
                solver_obj = pulp.PULP_CBC_CMD(**cbc_args)

            prob.solve(solver_obj)
            status = pulp.LpStatus[prob.status]
            # Accept Optimal or Not Solved but feasible within limit? pulp returns Optimal even on timeout if feasible found
            if status not in ("Optimal", "Not Solved"):
                # Try greedy fallback if infeasible
                if status == "Infeasible":
                    return []
                # else fallback to greedy
                raise RuntimeError(f"PuLP status {status}")

            # Extract solution
            results: List[Dict[str, Any]] = []
            for (i, j), var in x_vars.items():
                val = var.varValue
                if val is not None and val > 0.5:
                    batch = surplus_batches[i]
                    rec = recipients[j]
                    meta = batch_metas[i]
                    # Build same dict as rank_allocations:382
                    weight = meta["weight"]
                    co2 = round(weight * self.co2_factor, 1)
                    eval_res = meta["eval_res"]
                    results.append({
                        "batch_id": batch.get("batch_id", batch.get("id", f"batch-{i}")),
                        "item_description": batch.get("item_description", batch.get("itemName", meta["category"])),
                        "matched_recipient_id": rec.get("recipient_id", rec.get("id")),
                        "recipient_name": rec.get("name", rec.get("recipientName")),
                        "match_score": scores[(i, j)],
                        "safe_hours_remaining": meta["safe_hours"],
                        "urgency": eval_res.get("risk_classification") if isinstance(eval_res, dict) else None,
                        "cold_chain_enforced": eval_res.get("cold_chain_mandatory") if isinstance(eval_res, dict) else None,
                        "distance_km": distances.get((i, j)),
                        "co2_saved_kg": co2,
                        "solver": f"pulp-cbc:{status}",
                        "origin_coordinates": batch.get("origin_coordinates"),
                        "recipient_coordinates": rec.get("coordinates"),
                    })
            # Sort by match_score desc for determinism
            results.sort(key=lambda x: x["match_score"], reverse=True)
            # If solved but got zero allocations (e.g., all below min_score), fall through to greedy? Return empty
            # Latency guard: if took > time_limit + slack, log but still return
            _elapsed = time.perf_counter() - t0
            return results

        except ImportError:
            # pulp not installed -> try ortools then greedy
            ort_res = self._solve_milp_ortools(
                surplus_batches, recipients, batch_metas, scores, recip_caps, distances, time_limit_secs, min_score
            )
            if ort_res is not None:
                return ort_res
            return self.rank_allocations(surplus_batches, recipients, decay_engine, min_score=min_score)
        except Exception:
            # Any solver error -> fallback to greedy (never break pipeline)
            # In production log to audit stream (C2)
            return self.rank_allocations(surplus_batches, recipients, decay_engine, min_score=min_score)

    def _solve_milp_ortools(
        self,
        surplus_batches: List[Dict[str, Any]],
        recipients: List[Dict[str, Any]],
        batch_metas: List[Dict[str, Any]],
        scores: Dict[Tuple[int, int], float],
        recip_caps: List[Optional[float]],
        distances: Dict[Tuple[int, int], float],
        time_limit_secs: float,
        min_score: float,
    ) -> Optional[List[Dict[str, Any]]]:
        """OR-Tools CP-SAT MILP fallback [@orgtools2024]."""
        try:
            from ortools.sat.python import cp_model  # type: ignore
        except ImportError:
            return None

        n, m = len(surplus_batches), len(recipients)
        model = cp_model.CpModel()
        x_vars: Dict[Tuple[int, int], Any] = {}
        for (i, j) in scores:
            x_vars[(i, j)] = model.NewBoolVar(f"x_{i}_{j}")

        # Objective: maximize sum S_ij * x_ij (scale to int for CP-SAT)
        # CP-SAT needs integer coefficients; multiply by 10 (scores have 1 decimal)
        model.Maximize(sum(int(round(scores[(i, j)] * 10)) * x_vars[(i, j)] for (i, j) in x_vars))

        # Each surplus at most once
        for i in range(n):
            vars_i = [x_vars[(i, j)] for j in range(m) if (i, j) in x_vars]
            if vars_i:
                model.Add(sum(vars_i) <= 1)

        # Capacity constraints (weight*10 to keep int)
        for j in range(m):
            cap = recip_caps[j]
            if cap is None:
                continue
            vars_j = [(i, x_vars[(i, j)]) for i in range(n) if (i, j) in x_vars]
            if not vars_j:
                continue
            # Use int scaling: weight kg *10 vs cap*12 (1.2x)
            model.Add(sum(int(round(batch_metas[i]["weight"] * 10)) * v for i, v in vars_j) <= int(round(float(cap) * 12)))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max(0.1, time_limit_secs)
        solver.parameters.num_search_workers = 8
        # Silence
        solver.parameters.log_search_progress = False
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None

        results: List[Dict[str, Any]] = []
        for (i, j), var in x_vars.items():
            if solver.Value(var) == 1:
                batch = surplus_batches[i]
                rec = recipients[j]
                meta = batch_metas[i]
                weight = meta["weight"]
                co2 = round(weight * self.co2_factor, 1)
                eval_res = meta["eval_res"]
                results.append({
                    "batch_id": batch.get("batch_id", batch.get("id", f"batch-{i}")),
                    "item_description": batch.get("item_description", batch.get("itemName", meta["category"])),
                    "matched_recipient_id": rec.get("recipient_id", rec.get("id")),
                    "recipient_name": rec.get("name", rec.get("recipientName")),
                    "match_score": scores[(i, j)],
                    "safe_hours_remaining": meta["safe_hours"],
                    "urgency": eval_res.get("risk_classification") if isinstance(eval_res, dict) else None,
                    "cold_chain_enforced": eval_res.get("cold_chain_mandatory") if isinstance(eval_res, dict) else None,
                    "distance_km": distances.get((i, j)),
                    "co2_saved_kg": co2,
                    "solver": "ortools-cp-sat",
                    "origin_coordinates": batch.get("origin_coordinates"),
                    "recipient_coordinates": rec.get("coordinates"),
                })
        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results
