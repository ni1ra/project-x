# Project X

Research scaffold for a novel token-prediction architecture.

The repository is organized around three durable surfaces:

- `ref/`: public reference material, source manifests, and downloaded papers.
- `docs/`: implementation plans and operational next steps.
- `src/project_x/`: runnable research harness for architecture experiments.

This project treats public frontier model reports and papers as reference data only.
The implementation target is intentionally novel: a small, measurable harness first,
then increasingly hard architecture experiments with evidence artifacts.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m project_x.smoke
pytest
```

## Key Artifacts

- `docs/A_TO_Z_PLAN.md`
- `docs/DO_THIS_NEXT.md`
- `ref/SOURCE_MANIFEST.md`
- `ref/sources.json`

