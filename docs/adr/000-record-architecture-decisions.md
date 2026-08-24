# ADR 000: Record Architecture Decisions

**Date:** 2026-08-24
**Status:** Accepted
**Deciders:** FreshRoute AI Architecture Core

## Context

Spec `docs/FOOD_REDISTRIBUTION_OPTIMIZER_AI_SPEC.md:234-253` fixes directory layout, kinetics, matcher weights, vehicle tiers, and API contracts. Any deviation must be traceable, citable, and reversible. We adopt Architecture Decision Records (ADRs) per Nygard template.

## Decision

- Every substantive technical decision gets an ADR in `docs/adr/NNN-title.md`.
- ADR filename: `NNN-kebab-case-title.md` with incrementing NNN.
- Mandatory sections: Context, Decision, Consequences, Alternatives Considered, Citations (`[@key]` from `docs/BIBLIOGRAPHY.bib`), Reversibility.
- ADRs are immutable once Accepted; supersession creates a new ADR linking to the prior.
- CI checks: PR touching `freshroute-optimizer-model/core/*.py` or `api/*.py` without ADR when spec constant changed must fail (manual review today, scripted later).

## Consequences

- Preserves publication traceability and reviewer trust.
- Small overhead (one markdown per decision).

## Alternatives Considered

- Wiki-only: rejected (not versioned).
- Code comments only: rejected (not discoverable).

## Citations

- [@gebru2021datasheets] for provenance discipline
- Nygard, M. Documenting Architecture Decisions (2011)

## Template for Future ADRs

```markdown
# ADR-NNN: Title
Date: YYYY-MM-DD
Status: Proposed | Accepted | Rejected | Superseded by ADR-MMM
Context:
Decision:
Consequences:
Alternatives:
Citations: [@key]
Reversibility: <how to revert>
```
