# Reproducibility Protocol — FreshRoute AI

> Implements NeurIPS 2023 checklist [@neurips2023checklist] and FAIR [@wilkinson2016fair].

## One-Command Replay

```bash
git clone https://github.com/anomalyco/freshroute && cd freshroute
# Python optimizer
cd freshroute-optimizer-model
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/ -q
python scripts/citation_audit.py --bib ../docs/BIBLIOGRAPHY.bib --root ..
# (Phase P1+) dvc pull && python -m core.arrhenius_decay --validate
```

## Pinned Environment

- `freshroute-optimizer-model/requirements.txt` with `==` hashes
- `freshroute-optimizer-model/Dockerfile` digest `sha256:...` (record at build)
- `pip freeze > environment.lock` committed per gated tag
- `data_manifest.json` with SHA256 per gold file + retrieval timestamp

## Randomness & Determinism

- `PYTHONHASHSEED=0`, `np.random.seed(42)`, `torch.manual_seed(42)` where used
- OR-Tools solver seed fixed; LightGBM `deterministic=True` where applicable

## Data Provenance

- Every external pull recorded in `data/datasheets/*.md` + `data_manifest.json`
- Zenodo DOIs minted at gates P1, P2, P6, P7

## Metric Reproduction

- `mlruns/` logged runs; selected run ID copied to model card
- `notebooks/*.ipynb` executed headless via `jupyter nbconvert --execute`

## Checklist (NeurIPS adapted)

- [ ] Claims match experiments
- [ ] Train/val/test splits described (walk-forward for forecaster)
- [ ] Hyperparams + compute reported
- [ ] Error bars / intervals where stochastic
- [ ] Code + data accessibility statement with DOI
