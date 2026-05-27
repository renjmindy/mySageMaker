#!/usr/bin/env python3
"""
Local smoke-test for the HealthcareTopicClassifier — no Lambda/AWS required.

Run from the project root after training the classical models:
    python scripts/train_models.py          # build model artefacts first
    python examples/test_healthcare_classifier.py

Or (without pre-trained classical models) test BERTopic models only:
    python examples/test_healthcare_classifier.py --bert-only
"""

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Override MODEL_DIR to local path (not /app/models used inside Lambda)
LOCAL_MODELS = os.path.join(ROOT, "models")
os.environ.setdefault("MODEL_DIR", LOCAL_MODELS)

# ── Test texts (one per PREM topic) ───────────────────────────────────────────
TEST_CASES = [
    (0,  "Dr Smith was incredibly thorough and explained my entire care plan step by step."),
    (1,  "The receptionist at the front desk resolved my billing issue very efficiently."),
    (2,  "I waited two hours past my appointment time with no explanation given."),
    (3,  "The Zedoc patient portal crashed every time I tried to book an appointment."),
    (4,  "The specialist explained all treatment options and asked for my preference."),
    (5,  "I felt humiliated when the doctor discussed my case without acknowledging me."),
    (6,  "The standard of care was outstanding — thorough, careful, and highly professional."),
    (7,  "My referral was seamlessly coordinated between my GP and the specialist team."),
    (8,  "I waited three weeks for my blood test results and couldn't understand the report."),
    (9,  "The car park was full and I had to walk from the Westfield centre with difficulty."),
    (10, "My telehealth video consultation was smooth and saved a long drive to the clinic."),
    (11, "I was very anxious before surgery but the nurse reassured me and I felt safe."),
    (12, "An interpreter was arranged which allowed me to communicate with my doctor properly."),
    (13, "I was discharged without clear instructions about my medications or follow-up date."),
    (14, "I cannot praise this team enough — I left every appointment feeling in great hands."),
]


def run_test(models_to_test: list[str]) -> None:
    from healthcare_classifier import HealthcareTopicClassifier
    from healthcare_classifier.topics import TOPIC_NAMES

    clf = HealthcareTopicClassifier()

    print("\n" + "═" * 72)
    print("  Healthcare PREM Topic Classifier — smoke test")
    print(f"  Models: {models_to_test}")
    print("═" * 72)

    texts  = [t for _, t in TEST_CASES]
    labels = [l for l, _ in TEST_CASES]

    t0      = time.time()
    results = clf.classify(texts=texts, models=models_to_test, top_n=3)
    elapsed = time.time() - t0

    correct_per_model: dict = {m: 0 for m in models_to_test}
    total = len(TEST_CASES)

    for i, (item, true_label) in enumerate(zip(results, labels)):
        expected = TOPIC_NAMES[true_label]
        print(f"\n[{i:02d}] Expected: {expected}")
        print(f"     Text   : {item['text'][:75]}…")
        for model_name, clf_result in item["classifications"].items():
            pred   = clf_result["topic_name"]
            conf   = clf_result["confidence"]
            hit    = "✅" if pred == expected else "❌"
            print(f"     {model_name:<18}  {hit}  {pred:<44} ({conf:.2%})")
            if pred == expected:
                correct_per_model[model_name] += 1

    print("\n" + "═" * 72)
    print(f"  Elapsed: {elapsed:.1f}s   |   {total} test cases\n")
    for model_name, n_correct in correct_per_model.items():
        pct = n_correct / total * 100
        bar = "█" * n_correct + "░" * (total - n_correct)
        print(f"  {model_name:<18}  {bar}  {n_correct:2d}/{total}  ({pct:.0f}%)")
    print("═" * 72 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smoke-test the healthcare classifier locally")
    parser.add_argument("--bert-only", action="store_true",
                        help="Only test BERTopic models (no pre-trained classical models needed)")
    parser.add_argument("--models", nargs="+",
                        default=["bertopic_mini", "bertopic_mpnet", "lda", "lsi", "hdp", "nmf"],
                        help="Models to test")
    args = parser.parse_args()

    if args.bert_only:
        models = ["bertopic_mini", "bertopic_mpnet"]
    else:
        models = args.models

    run_test(models)


if __name__ == "__main__":
    main()
