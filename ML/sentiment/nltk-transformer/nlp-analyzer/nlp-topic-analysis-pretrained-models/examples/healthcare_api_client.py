#!/usr/bin/env python3
"""
Healthcare PREM Topic Classifier — example API client.

Usage:
    # Against the deployed API Gateway endpoint:
    python examples/healthcare_api_client.py \
        --url https://<api-id>.execute-api.<region>.amazonaws.com/classify

    # Against a local Lambda test server (see examples/run_local.py):
    python examples/healthcare_api_client.py --url http://localhost:9000/classify
"""

import argparse
import json
import sys

try:
    import requests
except ImportError:
    sys.exit("requests not installed: pip install requests")

# ── Sample texts covering all 15 PREM topics ─────────────────────────────────
SAMPLE_TEXTS = [
    # 0  Clinical Staff
    "Dr Smith was incredibly thorough, spending 30 minutes explaining my COPD "
    "management plan and making sure I understood everything.",
    # 1  Administrative Staff
    "The receptionist at the front desk was very helpful and resolved my billing "
    "issue within minutes.",
    # 2  Efficiency and Flow
    "I waited over two hours past my scheduled appointment time with no "
    "explanation or apology.",
    # 3  Booking & Access
    "The Zedoc portal kept crashing every time I tried to book an appointment "
    "online and I couldn't get through on the phone either.",
    # 4  Information & Shared Decision-Making
    "The specialist explained all my treatment options clearly and asked for my "
    "input before making any decisions — I felt truly involved in my care.",
    # 5  Dignity & Respect
    "I felt completely dismissed and humiliated when the doctor discussed my "
    "case with colleagues as if I wasn't in the room.",
    # 6  Care Quality
    "The standard of care I received was outstanding. The nurse changed my "
    "dressings with great care and thoroughness.",
    # 7  Care Coordination
    "My referral to the specialist was handled seamlessly and my GP and the "
    "hospital team communicated well throughout my treatment.",
    # 8  Results & Information
    "I waited three weeks for my blood test results and still couldn't "
    "understand the pathology report when it finally arrived.",
    # 9  Facilities & Environment
    "The car park was extremely limited and I had to walk from the Westfield "
    "centre which is very difficult at my age. The waiting room was clean though.",
    # 10 Telehealth
    "My telehealth video consultation worked perfectly and saved me a two-hour "
    "drive for a routine follow-up appointment.",
    # 11 Emotional Support
    "I was very anxious before the procedure but the nurse sat with me and "
    "reassured me throughout — I felt completely safe.",
    # 12 Cultural & Accessibility Needs
    "An interpreter was provided for my appointment which made it possible for "
    "me to communicate properly with my doctor for the first time.",
    # 13 Discharge & Follow-up
    "I was discharged without any written instructions about my medications or "
    "when to schedule my follow-up appointment.",
    # 14 Feeling in Good Hands
    "I cannot praise this team enough — I left every appointment feeling "
    "confident and completely reassured that I was in great hands.",
]


def classify(url: str, texts: list[str], models: list[str] = None,
             top_n: int = 3) -> dict:
    payload = {
        "texts":  texts,
        "models": models or ["all"],
        "top_n":  top_n,
    }
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


def health_check(base_url: str) -> dict:
    health_url = base_url.replace("/classify", "/health")
    resp = requests.get(health_url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def pretty_print(results: dict) -> None:
    if "error" in results:
        print(f"❌  API error: {results['error']}")
        return

    print(f"\n{'═'*70}")
    print(f"  Results  ({results.get('elapsed_sec', '?')}s)")
    print(f"{'═'*70}")

    for item in results.get("results", []):
        text = item["text"]
        print(f"\n📝  Text: {text[:80]}{'…' if len(text) > 80 else ''}")
        print(f"{'─'*70}")

        for model_name, clf in item["classifications"].items():
            top_name  = clf["topic_name"]
            top_score = clf["confidence"]
            print(f"  {model_name:<18} → {top_name:<46} ({top_score:.2%})")

        # Show full top-3 for the first model only
        first_model = next(iter(item["classifications"]))
        top_topics  = item["classifications"][first_model].get("top_topics", [])
        if len(top_topics) > 1:
            print(f"\n  Top-3 topics ({first_model}):")
            for rank, t in enumerate(top_topics, 1):
                print(f"    {rank}. {t['topic_name']:<44} {t['score']:.2%}")

    print(f"\n{'═'*70}")
    print(f"  Model status: {results.get('model_status', {})}")
    print(f"{'═'*70}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Healthcare PREM Topic Classifier — API client example")
    parser.add_argument(
        "--url",
        default="https://REPLACE_ME.execute-api.ap-southeast-2.amazonaws.com/classify",
        help="API Gateway classify endpoint URL",
    )
    parser.add_argument("--top-n", type=int, default=3,
                        help="Number of top topics to return (default 3)")
    parser.add_argument("--models", nargs="+", default=["all"],
                        help="Model(s) to use: all | bertopic_mini bertopic_mpnet lda lsi hdp nmf")
    parser.add_argument("--text", type=str, default=None,
                        help="Classify a single custom text (overrides sample texts)")
    parser.add_argument("--health", action="store_true",
                        help="Just run a health check")
    args = parser.parse_args()

    if args.health:
        print("Running health check ...")
        result = health_check(args.url)
        print(json.dumps(result, indent=2))
        return

    texts = [args.text] if args.text else SAMPLE_TEXTS

    print(f"Classifying {len(texts)} text(s) using models: {args.models}")
    print(f"Endpoint: {args.url}\n")

    result = classify(args.url, texts, models=args.models, top_n=args.top_n)
    pretty_print(result)


if __name__ == "__main__":
    main()
