# Code Review for Analysis Code
- Cleaning logic only in `lib/contactor_io.py`
- Scripts accept `--data-dir`, `--start`, `--near-full-min`
- No hard-coded paths or business parameters (cost, UPH)
- Demo/defaults clearly labelled illustrative
- Output deterministic; `python -I` runs clean
