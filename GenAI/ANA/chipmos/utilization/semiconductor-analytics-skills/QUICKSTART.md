# Quickstart

1. `pip install pandas numpy` (scripts use only these plus the stdlib; `playwright` is optional for screenshots)
2. Put `contactor_YYYYMMDD.csv` (front) and `contactor_rear_YYYYMMDD.csv` (rear) in `../dat` or pass `--data-dir`
3. Validate: `python 01-data-quality-validation/contactor-log-validation/scripts/read_failure_detector.py`
4. Headline: `python 03-data-analysis-investigation/site-availability/scripts/site_availability.py --quiet-days`
5. Where: `python 04-data-storytelling-visualization/visualization-builder/scripts/site_heatmap.py` -> `out/site_heatmap.html`
6. Gate and package: `python 05-stakeholder-communication/analysis-qa-checklist/scripts/qa_runner.py`, then `python 06-workflow-optimization/pipeline-automation/scripts/daily_pipeline.py`

Counts of 252-255 are treated as read failures by default (confirmed, assumption A8). `--near-full-min 0` restores the old 256-only rule for comparison.
