"""Basic usage example for the topic analysis pipeline."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.topic_modeler import run_topic_model
from src.models import ModelType

docs = [
    "The wait time was over two hours and nobody explained the delay.",
    "Dr Smith was very thorough and took time to explain my diagnosis clearly.",
    "The reception staff were rude and unhelpful when I called to reschedule.",
    "My medication was changed without any explanation and I had side effects.",
    "The nurses were incredibly kind and made me feel comfortable during my stay.",
    "The hospital parking is expensive and there are never enough spaces.",
    "The specialist explained everything patiently and answered all my questions.",
    "Billing department sent me an incorrect invoice and took weeks to fix it.",
    "The follow-up appointment was easy to book and the doctor remembered my case.",
    "I was not informed about the procedure risks beforehand.",
]

result = run_topic_model(docs, ModelType.BERTOPIC_MINI)

print(f"Model:  {result.model_type}")
print(f"Topics: {result.num_topics}")
print(f"Outliers: {result.outlier_count}\n")

for t in result.topics:
    print(f"Topic {t.topic_id} ({t.doc_count} docs): {', '.join(t.keywords[:6])}")

print()
for d in result.documents:
    print(f"  Doc {d.doc_id:2d} → Topic {d.topic_id:2d} ({d.probability:.1%})  {d.text[:60]}…")
