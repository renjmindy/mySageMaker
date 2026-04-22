"""
Gradio Web Interface for Medical PII De-identification.

Interactive demo showcasing HIPAA-compliant PII detection and removal.
"""

import os
import sys
import json

import gradio as gr

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pii_detector import PIIDetector, get_detector
from src.deidentify import Deidentifier, ReplacementStrategy
from src.entities import EntityType, HIPAA_ENTITIES

# Sample clinical notes for demonstration
SAMPLE_TEXTS = {
    "Discharge Summary": """DISCHARGE SUMMARY

Patient: John Michael Smith
DOB: March 15, 1985
MRN: 123456789
SSN: 123-45-6789

Date of Admission: January 10, 2024
Date of Discharge: January 15, 2024

Attending Physician: Dr. Sarah Elizabeth Johnson, MD
Department: Internal Medicine
Hospital: Memorial General Hospital
Address: 123 Medical Center Drive, Boston, MA 02101

Contact Information:
Phone: (555) 123-4567
Fax: (555) 123-4568
Email: john.smith@personalmail.com

CHIEF COMPLAINT:
Patient presented with chest pain and shortness of breath.

HOSPITAL COURSE:
The patient was admitted for observation and cardiac workup.
EKG showed normal sinus rhythm. Troponins were negative x3.
Patient was started on aspirin 81mg daily.

DISCHARGE MEDICATIONS:
1. Aspirin 81mg PO daily
2. Metoprolol 25mg PO BID

FOLLOW-UP:
Patient to follow up with Dr. Johnson at Memorial Cardiology Clinic
Phone: 555-987-6543
Appointment scheduled for January 25, 2024 at 2:00 PM

Electronically signed by:
Sarah E. Johnson, MD
License #: MA12345
NPI: 1234567890""",

    "Clinical Note": """PROGRESS NOTE

Date: 02/14/2024
Time: 14:30

Patient: Mary Patricia Williams
DOB: 07/22/1958 (Age: 65)
MRN: MRN-987654321

Seen today for follow-up of Type 2 Diabetes Mellitus.

Current Medications:
- Metformin 1000mg BID
- Lisinopril 10mg daily

Vitals:
BP: 128/82  HR: 72  Temp: 98.6F  Weight: 165 lbs

Assessment:
Diabetes well-controlled. A1C improved to 6.8%.
Continue current regimen.

Plan:
1. Continue current medications
2. Recheck A1C in 3 months
3. Annual eye exam scheduled with Dr. Robert Chen at
   Boston Eye Associates, 456 Vision Lane, Cambridge MA 02139
   Phone: 617-555-7890

Next Appointment: May 14, 2024

Provider: James Michael Anderson, NP
Email: janderson@clinic.org
Pager: 555-PAGE-001""",

    "Lab Report": """LABORATORY REPORT

Patient Name: Robert James Garcia
Date of Birth: 11/30/1972
Patient ID: PID-2024-00123
Account Number: ACC-789456123

Collection Date: 01/20/2024 08:45 AM
Report Date: 01/20/2024 14:22 PM

Ordering Physician: Dr. Emily Chen
Phone: (555) 234-5678
Fax: (555) 234-5679

COMPLETE BLOOD COUNT (CBC)

WBC: 7.2 K/uL (4.5-11.0)
RBC: 4.8 M/uL (4.5-5.5)
Hemoglobin: 14.2 g/dL (13.5-17.5)
Hematocrit: 42.1% (38.8-50.0)
Platelets: 245 K/uL (150-400)

COMPREHENSIVE METABOLIC PANEL

Glucose: 95 mg/dL (70-100)
BUN: 15 mg/dL (7-20)
Creatinine: 1.0 mg/dL (0.7-1.3)
eGFR: >90 mL/min/1.73m2

Specimen collected at:
City Medical Laboratory
789 Lab Way, Suite 100
San Francisco, CA 94102

Results reviewed and approved by:
Lisa Marie Thompson, MD, PhD
Laboratory Director
NPI: 9876543210""",

    "Referral Letter": """REFERRAL LETTER

Date: February 20, 2024

FROM:
Dr. Michael Brown
Family Medicine Associates
100 Primary Care Blvd
Chicago, IL 60601
Phone: 312-555-1234
Fax: 312-555-1235

TO:
Dr. Jennifer Lee, MD
Cardiology Specialists
200 Heart Center Dr
Chicago, IL 60602

RE: Patient Referral
Patient: David Allen Thompson
DOB: 05/18/1965
SSN: 987-65-4321
Insurance ID: BCBS-IL-123456789

Dear Dr. Lee,

I am referring Mr. Thompson to your practice for evaluation of
exertional chest pain. He is a 58-year-old male with history of
hypertension and hyperlipidemia.

Recent stress test was equivocal. Please evaluate for possible CAD.

Patient contact: david.thompson@email.com, (312) 555-9876

Thank you for seeing this patient.

Sincerely,
Michael Brown, MD
License: IL-MD-98765""",

"Operative Report": """OPERATIVE REPORT

Patient: Susan Marie Rodriguez
MRN: 555666777
DOB: 09/12/1970

Date of Surgery: March 5, 2024
Surgeon: Dr. William James Carter, MD, FACS
Assistant: Dr. Amanda Foster
Anesthesiologist: Dr. Richard Park

Procedure: Laparoscopic Cholecystectomy

Preoperative Diagnosis: Symptomatic cholelithiasis
Postoperative Diagnosis: Same

Procedure Details:
The patient was brought to the operating room and placed in supine
position. General anesthesia was induced without complication.

[Detailed surgical notes omitted for brevity]

The patient tolerated the procedure well and was transferred to
recovery in stable condition.

Estimated Blood Loss: <50 mL
Specimens: Gallbladder sent to pathology

Follow-up scheduled for March 15, 2024 at our office:
Chicago Surgical Associates
500 Surgery Way, Chicago IL 60603
Phone: 312-555-3456

Dictated by: William Carter, MD
Date: 03/05/2024
T: 03/05/2024 15:30
D: 03/05/2024 16:45""",

    "Patient Report Measures": """PATIENT REPORT

Dr Priya Patel in the respiratory clinic was absolutely wonderful. She took time to explain my COPD management plan and made sure I understood every step. The nurse on reception, Karen Thompson, was also very welcoming.

The parking at 45 Albert Street is very limited. I had to walk from the Westfield car park which is difficult at my age.

I had my appointment on 15 January 2026 at 2pm and wasn't seen until after 3:15pm. Dr James Richardson seemed rushed and didn't listen to my concerns about the medication side effects. I called the clinic at 07 3456 7890 twice before my appointment to ask about preparation and nobody answered. My wife Angela Chen had a much better experience at the Chermside Day Surgery last month.

The physiotherapist Michael was great. He gave me a detailed home exercise program after my knee surgery and followed up via email at susan.obrien82@gmail.com to check on my progress. Very impressed with that level of care.

The online booking system could be easier to use. I ended up calling reception to book because I couldn't figure out the Zedoc portal. I was referred by Dr Nguyen at the Ipswich Hospital and the transition was smooth.

Nurse Rebecca Taylor in the diabetes clinic was exceptional. She spent over 40 minutes with me going through my HbA1c results and adjusting my insulin plan. She also coordinated with my GP Dr Samantha Lee at the Toowoomba Medical Practice to ensure consistent care.

Dr Patel is always thorough and patient. She remembers details from previous visits which makes me feel valued.

I'm 81 years old and find the forms quite difficult to fill in. My daughter Sarah Fitzpatrick usually helps me but she wasn't available this time. Could you offer some assistance at the front desk for elderly patients? Also my Medicare number is 2345 67890 1 and I think there was a billing error on my last visit on 28 January 2026.

The midwifery team, especially Lisa and Jenny, were amazing throughout my pregnancy. They made me feel safe and supported. The antenatal classes at the centre on George Street were also excellent.

It would be nice to have later appointment slots. As a working mum I find it hard to attend before 4pm. My employer at Bright Horizons Childcare is not always flexible with time off. I recommended this clinic to my sister-in-law Patricia Nakamura who is expecting in July.

The new blood collection nurse, Daniel Kim, was very skilled. Best blood draw I've had - barely felt it. He mentioned he previously worked at the Royal Brisbane and Women's Hospital.

The results portal is confusing. I had to call Dr Richardson's office at 07 3456 7891 to get my pathology explained because I couldn't understand the online report.

Dr Patel and Nurse Rebecca were both excellent. They were respectful of my cultural needs and ensured a female practitioner was available for my examination. This was very important to me.

The interpreter service was not available on 4 March 2026 when my mother attended. She speaks Arabic and struggled to communicate her symptoms. Please ensure interpreters are booked in advance. My mother Zahra Al-Rashid (patient ID PAT-91603) would like to provide feedback separately. Can someone contact her at fatima.alrashid@outlook.com to arrange an Arabic-language survey?

Outstanding mental health support from psychologist Dr Amanda Clarke. She helped me develop coping strategies after my workplace incident at BHP Mitsubishi Alliance in Mount Isa last year. The telehealth option made it possible to continue sessions when I was FIFO.

The mental health waiting list is too long. I was referred on 15 November 2025 and didn't get my first appointment until 8 January 2026. That's nearly 8 weeks.

The wound care nurse Jacinta was thorough and gentle. She explained the healing process for my post-surgical wound clearly and gave me written instructions to take home.

I received a reminder SMS from Zedoc to complete this survey but the link didn't work on my Samsung phone. I had to use my husband David Tran's iPhone instead. The SMS came from number 0437 123 456. I was transferred from Logan Hospital after my surgery there on 2 March 2026. The handover between hospitals could have been smoother - my medication list wasn't updated correctly.

The car park needs more disabled bays. I have a temporary mobility permit after my cardiac rehab and struggled to find a spot on 20 March 2026. My cardiologist at the Prince Charles Hospital, Dr Andrew Walsh, also coordinates with Dr Richardson here which gives me great confidence in my care plan.""",
}


# Initialize detector (will load on first use)
detector = None
deidentifier = None


def get_models():
    """Initialize models on first use."""
    global detector, deidentifier
    if detector is None:
        detector = get_detector()
        deidentifier = Deidentifier(detector=detector)
    return detector, deidentifier


def detect_and_highlight(text: str, confidence: float) -> tuple:
    """Detect PII and return highlighted text with entity list."""
    if not text.strip():
        return "", "No text provided", "[]"

    detector, _ = get_models()
    detector.confidence_threshold = confidence

    entities = detector.detect(text)

    if not entities:
        return text, "No PII detected", "[]"

    # Build highlighted HTML
    highlighted = text
    # Sort by position (reverse) for replacement
    sorted_entities = sorted(entities, key=lambda e: e.start, reverse=True)

    colors = {
        EntityType.NAME: "#ff6b6b",
        EntityType.DATE: "#4ecdc4",
        EntityType.PHONE: "#45b7d1",
        EntityType.EMAIL: "#96ceb4",
        EntityType.SSN: "#ff8c42",
        EntityType.MRN: "#a8e6cf",
        EntityType.LOCATION: "#dda0dd",
        EntityType.LICENSE: "#f7dc6f",
        EntityType.PROVIDER: "#bb8fce",
        EntityType.ORGANIZATION: "#85c1e9",
    }

    for entity in sorted_entities:
        color = colors.get(entity.entity_type, "#ffeaa7")
        highlighted = (
            highlighted[:entity.start] +
            f'<mark style="background-color: {color}; padding: 2px 4px; border-radius: 3px;" '
            f'title="{entity.entity_type.value}: {entity.confidence:.2%}">{entity.text}</mark>' +
            highlighted[entity.end:]
        )

    # Build entity summary
    entity_summary = []
    for entity in entities:
        entity_summary.append(
            f"- **{entity.entity_type.value}**: `{entity.text}` "
            f"(confidence: {entity.confidence:.2%})"
        )

    summary = f"### Found {len(entities)} PII Entities\n\n" + "\n".join(entity_summary)

    # JSON output
    json_output = json.dumps([e.to_dict() for e in entities], indent=2)

    return f"<div style='white-space: pre-wrap; font-family: monospace;'>{highlighted}</div>", summary, json_output


def deidentify_text(text: str, strategy: str, confidence: float) -> tuple:
    """De-identify text and return result."""
    if not text.strip():
        return "", "No text provided"

    _, deidentifier = get_models()

    # Map strategy
    strategy_map = {
        "Placeholder [NAME]": ReplacementStrategy.PLACEHOLDER,
        "Consistent Fakes": ReplacementStrategy.CONSISTENT,
        "Redact (████)": ReplacementStrategy.REDACT,
        "Hash-based": ReplacementStrategy.HASH,
    }
    strat = strategy_map.get(strategy, ReplacementStrategy.PLACEHOLDER)

    deidentifier.strategy = strat
    deidentifier.detector.confidence_threshold = confidence

    if strat == ReplacementStrategy.CONSISTENT:
        deidentifier.reset_mappings()

    result = deidentifier.deidentify(text)

    # Build summary
    if result.entity_count == 0:
        summary = "No PII detected - text unchanged"
    else:
        summary = f"### Replaced {result.entity_count} PII Entities\n\n"
        for original, replacement in result.replacements_made.items():
            summary += f"- `{original}` → `{replacement}`\n"

    return result.deidentified_text, summary


def load_sample(sample_name: str) -> str:
    """Load a sample text."""
    return SAMPLE_TEXTS.get(sample_name, "")


# Build Gradio interface
with gr.Blocks(
    title="Medical PII De-identification",
) as demo:
    gr.Markdown("""
    # Medical PII De-identification Demo

    **HIPAA-compliant PII detection and removal** using OpenMed's clinical NLP models.

    This tool detects and removes Protected Health Information (PHI) including:
    Names, Dates, Phone/Fax, Email, SSN, MRN, Locations, and 18+ HIPAA identifiers.

    ---
    """)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Load Sample")
            sample_dropdown = gr.Dropdown(
                choices=list(SAMPLE_TEXTS.keys()),
                label="Select Sample Clinical Note",
                value="Discharge Summary"
            )
            load_btn = gr.Button("Load Sample", variant="secondary")

    with gr.Tabs():
        # Tab 1: Detection
        with gr.TabItem("Detect PII"):
            with gr.Row():
                with gr.Column():
                    detect_input = gr.Textbox(
                        label="Input Clinical Text",
                        placeholder="Paste clinical notes here...",
                        lines=15,
                        max_lines=30
                    )
                    detect_confidence = gr.Slider(
                        minimum=0.1,
                        maximum=0.99,
                        value=0.5,
                        step=0.05,
                        label="Confidence Threshold"
                    )
                    detect_btn = gr.Button("Detect PII", variant="primary")

                with gr.Column():
                    detect_output = gr.HTML(label="Highlighted Text")
                    detect_summary = gr.Markdown(label="Entity Summary")

            with gr.Accordion("JSON Output", open=False):
                detect_json = gr.Code(language="json", label="Detected Entities (JSON)")

        # Tab 2: De-identification
        with gr.TabItem("De-identify"):
            with gr.Row():
                with gr.Column():
                    deid_input = gr.Textbox(
                        label="Input Clinical Text",
                        placeholder="Paste clinical notes here...",
                        lines=15,
                        max_lines=30
                    )
                    deid_strategy = gr.Radio(
                        choices=[
                            "Placeholder [NAME]",
                            "Consistent Fakes",
                            "Redact (████)",
                            "Hash-based"
                        ],
                        value="Placeholder [NAME]",
                        label="Replacement Strategy"
                    )
                    deid_confidence = gr.Slider(
                        minimum=0.1,
                        maximum=0.99,
                        value=0.5,
                        step=0.05,
                        label="Confidence Threshold"
                    )
                    deid_btn = gr.Button("De-identify Text", variant="primary")

                with gr.Column():
                    deid_output = gr.Textbox(
                        label="De-identified Text",
                        lines=15,
                        max_lines=30
                    )
                    deid_summary = gr.Markdown(label="Replacement Summary")

        # Tab 3: About
        with gr.TabItem("About"):
            gr.Markdown("""
            ## About This Tool

            This demo uses the **OpenMed SuperClinical PII Detection Model** (44M parameters),
            specifically designed for clinical text de-identification.

            ### HIPAA Safe Harbor - 18 Identifiers

            | Category | Examples |
            |----------|----------|
            | Names | Patient names, Doctor names |
            | Dates | DOB, Admission dates, Appointment dates |
            | Contact | Phone, Fax, Email |
            | IDs | SSN, MRN, Account numbers, License numbers |
            | Location | Addresses, City, State, ZIP |
            | Other | URLs, IP addresses, Device IDs |

            ### Replacement Strategies

            - **Placeholder**: Generic labels like `[NAME]`, `[DATE]`
            - **Consistent Fakes**: Same entity → same fake value (useful for analysis)
            - **Redact**: Black bars `████████`
            - **Hash-based**: Deterministic pseudonyms `[NAME_a1b2c3d4]`

            ### Model Information

            - **Model**: OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1
            - **Architecture**: Transformer (BERT-based)
            - **Parameters**: 44 million
            - **Optimized for**: Clinical discharge notes, progress notes, lab reports

            ### Privacy Notice

            This demo processes text **in-memory only**. No data is logged or stored.
            For production use, deploy on your own infrastructure.

            ---

""")

    # Event handlers
    load_btn.click(
        fn=load_sample,
        inputs=[sample_dropdown],
        outputs=[detect_input]
    ).then(
        fn=load_sample,
        inputs=[sample_dropdown],
        outputs=[deid_input]
    )

    detect_btn.click(
        fn=detect_and_highlight,
        inputs=[detect_input, detect_confidence],
        outputs=[detect_output, detect_summary, detect_json]
    )

    deid_btn.click(
        fn=deidentify_text,
        inputs=[deid_input, deid_strategy, deid_confidence],
        outputs=[deid_output, deid_summary]
    )


# Launch configuration
_on_hf_spaces = os.getenv("SPACE_ID") is not None

demo.launch(
    server_name="0.0.0.0" if not _on_hf_spaces else None,
    server_port=int(os.getenv("GRADIO_PORT", 7860)) if not _on_hf_spaces else None,
    share=os.getenv("GRADIO_SHARE", "false").lower() == "true",
        theme=gr.themes.Soft(),
        js="""
        function() {
            const observer = new MutationObserver(function() {
                document.querySelectorAll(
                    'button[aria-label*="dark"], button[aria-label*="light"], button[aria-label*="Dark"], button[aria-label*="Light"], .theme-toggle, input[type="checkbox"].theme, label[for*="theme"]'
                ).forEach(el => el.closest('label, div, span') ? el.closest('label, div, span').remove() : el.remove());
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }
        """,
        css="""
        .container { max-width: 1200px; margin: auto; }
        .highlight mark { cursor: help; }
        .gradio-container, .gradio-container * { font-family: Arial, Helvetica, sans-serif !important; }
        .theme-toggle, .dark-mode-toggle, [class*="theme"], [id*="theme"], button[aria-label*="dark"], button[aria-label*="light"], button[aria-label*="Dark"], button[aria-label*="Light"] { display: none !important; }
        :root {
            --background-fill-primary: #000000 !important;
            --background-fill-secondary: #000000 !important;
            --body-background-fill: #000000 !important;
            --panel-background-fill: #000000 !important;
            --block-background-fill: #000000 !important;
            --input-background-fill: #000000 !important;
            --color-background-primary: #000000 !important;
        }
        body, html { background-color: #000000 !important; }
        .gradio-container { background-color: #000000 !important; color: white !important; font-size: 800% !important; }
        .gradio-container * { color: white !important; }
        .tab-nav, .tab-nav *, div[role="tablist"], div[role="tablist"] * { background-color: #000000 !important; }
        .tab-nav button, div[role="tab"], button[role="tab"] { background-color: #000000 !important; color: white !important; border-color: #ccc !important; }
        .tabitem { background-color: #000000 !important; color: white !important; }
        input[type="range"]::-webkit-slider-thumb { background-color: #000000 !important; }
        input[type="range"]::-moz-range-thumb { background-color: #000000 !important; }
        input[type="range"]::-webkit-slider-runnable-track { background-color: #000000 !important; }
        input[type="range"]::-moz-range-track { background-color: #000000 !important; }
        .block { background-color: #000000 !important; }
        label { background-color: #000000 !important; }
        textarea, input[type="text"], input[type="number"], .codemirror-wrapper, .cm-editor, .cm-scroller, pre { background-color: #000000 !important; }
        .prose, .markdown, .output-markdown { background-color: #000000 !important; }
        .wrap { background-color: #000000 !important; }
        .scroll-hide { background-color: #000000 !important; }
        select, .select, .dropdown, ul.options, ul.options li, .option { background-color: #000000 !important; }
        .svelte-select, .svelte-select .value-container, .svelte-select .listContainer, .svelte-select .item { background-color: #000000 !important; }
        """
    )
