"""
Bundle project context into one Markdown file and estimate its size.

Usage:
    python context_bundler.py
    python context_bundler.py --budget-tokens 6000 --output ../../../out/context_package.md
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "02-documentation-knowledge/analysis-assumptions-log/scripts"))
import assumptions_tracker as at  # noqa: E402


def loader_rules() -> str:
    text = (ROOT / "lib" / "contactor_io.py").read_text(encoding="utf-8")
    return text.split('"""')[1].strip()


def latest_summary() -> str:
    runs = sorted((ROOT / "out" / "pipeline").glob("*/summary.json")) if (ROOT / "out" / "pipeline").exists() else []
    return json.dumps(json.loads(runs[-1].read_text()), indent=2) if runs else "(no pipeline run yet)"


def main():
    ap = argparse.ArgumentParser(description="Context bundler")
    ap.add_argument("--budget-tokens", type=int, default=8000)
    ap.add_argument("--output", default=str(ROOT / "out" / "context_package.md"))
    args = ap.parse_args()

    metric = (ROOT / "02-documentation-knowledge/semiconductor-metric-definitions/assets/metric_definition.yaml").read_text(encoding="utf-8")
    parts = [
        "# Context package - handler contactor utilization",
        "## 1. Data rules (loader)\n" + loader_rules(),
        "## 2. Assumptions log\n" + at.render(at.load()),
        "## 3. Metric definitions\n```yaml\n" + metric + "\n```",
        "## 4. Latest pipeline summary\n```json\n" + latest_summary() + "\n```",
    ]
    text = "\n\n".join(parts)
    tokens = len(text) // 4
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}  ~{tokens} tokens (chars/4)  budget {args.budget_tokens}  {'OK' if tokens <= args.budget_tokens else 'OVER BUDGET'}")


if __name__ == "__main__":
    main()
