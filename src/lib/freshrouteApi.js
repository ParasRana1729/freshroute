/**
 * FreshRoute Optimizer API client — Phase P6 wiring.
 *
 * Tries live FastAPI (vite proxy → http://localhost:8000) first,
 * falls back to mock simulation in src/data/mockData.js if backend down.
 * This keeps the landing console functional while exposing real kinetics/matcher
 * when `uvicorn api.app:app` is running.
 *
 * Endpoints match spec §5 and plan P6:
 *  POST /api/v1/predict/shelf-life
 *  POST /api/v1/optimize/match
 *  GET  /api/v1/forecast/demand?district_id=&horizon_days=
 *  POST /api/v1/optimize/routing
 */

const API_BASE = '' // vite proxy handles /api → 8000; empty means same origin

async function fetchJSON(url, opts = {}) {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    ...opts,
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json()
}

/**
 * Shelf-life prediction — wraps POST /api/v1/predict/shelf-life
 * Citation: core/arrhenius_decay.py [@arrhenius1889; @labuza1993kinetics]
 */
export async function predictShelfLife({ category = 'Dairy', ambient_temp_c = 36.0, humidity_pct = 72.0, elapsed_hours = 0.0 } = {}) {
  return fetchJSON('/api/v1/predict/shelf-life', {
    method: 'POST',
    body: JSON.stringify({ category, ambient_temp_c, humidity_pct, elapsed_hours }),
  })
}

/**
 * Surplus-to-recipient match — wraps POST /api/v1/optimize/match
 * Uses live decay + Pareto matcher (w=[0.35,0.30,0.20,0.15]) [@saaty1980ahp]
 * Pass opts e.g. {use_milp:true, solver:'pulp'} for MILP optimal (P4) vs greedy default.
 */
export async function optimizeMatch(surplus_batch, ambient_weather = null, candidate_recipients = null, opts = {}) {
  const payload = { surplus_batch, ambient_weather }
  if (candidate_recipients) payload.candidate_recipients = candidate_recipients
  if (opts.use_milp) payload.use_milp = true
  if (opts.solver) payload.solver = opts.solver
  if (opts.min_score) payload.min_score = opts.min_score
  return fetchJSON('/api/v1/optimize/match', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/**
 * District demand forecast — wraps GET /api/v1/forecast/demand
 */
export async function forecastDemand({ district_id = null, horizon_days = 7, include_langar_pilgrim_surge = true } = {}) {
  const qs = new URLSearchParams({
    horizon_days: String(horizon_days),
    include_langar_pilgrim_surge: String(include_langar_pilgrim_surge),
  })
  if (district_id) qs.set('district_id', district_id)
  return fetchJSON(`/api/v1/forecast/demand?${qs}`)
}

/**
 * VRP routing — wraps POST /api/v1/optimize/routing
 * Pass opts {use_or_tools:true, t_safe_hours:[6], lambda_penalty:2.0} for VRPTW (P5).
 */
export async function optimizeRouting({ pickup_nodes, dropoff_nodes, fleet_available = null, use_or_tools = false, t_safe_hours = null, lambda_penalty = null }) {
  const payload = { pickup_nodes, dropoff_nodes, fleet_available }
  if (use_or_tools) payload.use_or_tools = true
  if (t_safe_hours) payload.t_safe_hours = t_safe_hours
  if (lambda_penalty != null) payload.lambda_penalty = lambda_penalty
  return fetchJSON('/api/v1/optimize/routing', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/**
 * Health probe — used to show "Live Optimizer Connected" badge in console header.
 */
export async function checkHealth() {
  try {
    const h = await fetchJSON('/health')
    return h.status === 'healthy'
  } catch {
    return false
  }
}

/**
 * Utility: try live, else fallback value. Example:
 *   const data = await withFallback(() => predictShelfLife(req), mockShelfLife)
 */
export async function withFallback(liveFn, fallback) {
  try {
    return await liveFn()
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn('[FreshRoute API] live failed, using mock fallback:', e?.message || e)
    return typeof fallback === 'function' ? fallback() : fallback
  }
}
