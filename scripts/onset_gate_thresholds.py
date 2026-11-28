"""Choose alert thresholds for the three normal-market rule states."""

import numpy as np


def choose_gate_thresholds(
    labels: np.ndarray, scores: np.ndarray, gates: np.ndarray
) -> tuple[dict[int, float | None], float]:
    """Optimize pooled F1 over validation thresholds for mutually exclusive gates."""
    groups = np.unique(gates)
    curves = []
    for group in groups:
        mask = gates == group
        order = np.argsort(-scores[mask], kind="stable")
        ranked = scores[mask][order]
        matched = np.cumsum(labels[mask][order], dtype=np.int64)
        # All rows with the same score must receive the same decision.
        ends = np.flatnonzero(np.r_[ranked[:-1] != ranked[1:], True])
        curves.append(
            (np.r_[0, matched[ends]], np.r_[0, ends + 1], np.r_[np.inf, ranked[ends]])
        )

    ratio = 0.0
    positives = int(labels.sum())
    # For a fixed ratio, maximizing the numerator minus that ratio times the
    # denominator separates by gate. Repeat with the F1 of the chosen thresholds.
    choices = []
    for _ in range(30):
        choices = [int(np.argmax(2 * tp - ratio * alarms)) for tp, alarms, _ in curves]
        hits = sum(tp[index] for (tp, _, _), index in zip(curves, choices))
        alerted = sum(alarms[index] for (_, alarms, _), index in zip(curves, choices))
        updated = (
            float(2 * hits / (positives + alerted)) if positives + alerted else 0.0
        )
        if abs(updated - ratio) < 1e-12:
            break
        ratio = updated

    cutoffs = {}
    for group, (_, _, thresholds), index in zip(groups, curves, choices):
        threshold = thresholds[index]
        cutoffs[int(group)] = float(threshold) if np.isfinite(threshold) else None
    return cutoffs, updated


def alert_thresholds(gates: np.ndarray, cutoffs: dict[int, float | None]) -> np.ndarray:
    """Map fitted cutoffs to rows, with disabled alerts represented by infinity."""
    result = np.full(len(gates), np.inf, dtype=np.float64)
    for level, cutoff in cutoffs.items():
        if cutoff is not None:
            result[gates == int(level)] = cutoff
    return result
