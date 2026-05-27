"""
Predefined PREM (Patient Reported Experience Measure) topic taxonomy.

15 healthcare topics aligned with the notebook pipeline:
  healthcare-med-distilroberta-lda-topicanapipeline.ipynb — cells 51, 79.

Seed corpus (15 docs × 15 sentences = 225 documents) is used to:
  • train all classical models (LDA-sklearn, LSI, HDP, LDA-gensim, NMF) at
    Docker build time via scripts/train_models.py
  • pre-compute topic embeddings for BERTopic zero-shot classification
"""

from __future__ import annotations
from typing import Dict, List, Tuple

# ── Topic registry (index → display name) ─────────────────────────────────────
TOPIC_NAMES: Dict[int, str] = {
    0:  "Clinical Staff",
    1:  "Administrative Staff",
    2:  "Efficiency and Flow",
    3:  "Booking & Access",
    4:  "Information & Shared Decision-Making",
    5:  "Dignity & Respect",
    6:  "Care Quality",
    7:  "Care Coordination",
    8:  "Results & Information",
    9:  "Facilities & Environment & Environmental Hygiene",
    10: "Telehealth",
    11: "Emotional Support",
    12: "Cultural & Accessibility Needs",
    13: "Discharge & Follow-up",
    14: "Feeling in Good Hands",
}

N_TOPICS: int = len(TOPIC_NAMES)  # 15

# ── Keyword lists (used for topic-alignment after unsupervised training) ──────
TOPIC_KEYWORDS: Dict[int, List[str]] = {
    0:  ["doctor", "nurse", "GP", "specialist", "physiotherapist",
         "psychologist", "midwife", "physician", "clinician", "surgeon",
         "consultant", "practitioner", "staff", "medical"],
    1:  ["reception", "booking", "billing", "front desk", "receptionist",
         "admin", "administration", "clerk", "scheduling", "paperwork",
         "front office", "check-in", "invoice", "payment"],
    2:  ["waiting", "waited", "queue", "delay", "on time", "late",
         "wait time", "long wait", "punctual", "slow", "fast",
         "efficiency", "flow", "time", "hours"],
    3:  ["book", "appointment", "portal", "online", "Zedoc",
         "access", "system", "schedule", "unavailable", "cancellation",
         "rescheduling", "booked", "missed", "couldn't"],
    4:  ["explained", "told", "informed", "listened", "dismissed",
         "didn't listen", "information", "decision", "options",
         "consent", "communication", "understanding", "shared",
         "discuss", "choice"],
    5:  ["dignity", "respect", "respectful", "disrespectful", "rude",
         "kind", "compassionate", "ignored", "valued", "treated",
         "humiliated", "courteous", "manner", "polite", "attitude"],
    6:  ["thorough", "careful", "rushed", "excellent", "poor",
         "skilled", "quality", "competent", "professional",
         "incompetent", "attentive", "care", "treatment", "standard"],
    7:  ["handover", "referral", "transferred", "coordinated",
         "coordination", "team", "multidisciplinary", "communicate",
         "follow-up", "specialist", "pathway", "integrated", "liaison"],
    8:  ["results", "report", "pathology", "test", "didn't understand",
         "lab results", "blood", "scan", "imaging", "diagnosis",
         "findings", "explained results", "outcome", "interpret"],
    9:  ["parking", "car park", "clean", "comfortable", "building",
         "facilities", "environment", "hygiene", "hospital room",
         "cleanliness", "signage", "amenities", "toilet", "space"],
    10: ["telehealth", "video", "online consult", "remote", "phone",
         "virtual", "zoom", "telemedicine", "digital", "video call",
         "telephone", "app", "platform", "consult", "screen"],
    11: ["anxious", "reassured", "felt safe", "valued", "dismissed",
         "emotional", "support", "comfort", "scared", "frightened",
         "calmed", "mental health", "anxiety", "worried", "distressed"],
    12: ["cultural", "language", "disability", "female practitioner",
         "interpreter", "accessibility", "needs", "diversity",
         "inclusion", "LGBTQ", "competency", "barrier", "accommodation"],
    13: ["discharge", "follow-up", "home", "after care", "instructions",
         "aftercare", "post discharge", "home care", "medication",
         "post-op", "recovery", "plan", "summary", "next steps"],
    14: ["feeling in good hands", "confident", "trust", "safe",
         "overall", "good experience", "positive", "satisfied",
         "wonderful", "great", "excellent", "highly recommend",
         "outstanding", "impressed"],
}

# ── Rich descriptions for BERTopic zero-shot embeddings ──────────────────────
TOPIC_DESCRIPTIONS: Dict[int, str] = {
    0:  ("Clinical staff including doctor nurse GP specialist physiotherapist "
         "psychologist midwife physician surgeon consultant provided care"),
    1:  ("Administrative staff including receptionist booking billing front desk "
         "admin clerk scheduling paperwork check-in invoice payment"),
    2:  ("Efficiency and flow including waiting queue delay on time late wait time "
         "long wait punctual slow fast efficiency hours"),
    3:  ("Booking and access including appointment portal online Zedoc system "
         "schedule unavailable cancellation rescheduling couldn't book"),
    4:  ("Information and shared decision-making including explained informed "
         "listened dismissed didn't listen shared decision options consent "
         "communication understanding"),
    5:  ("Dignity and respect including respectful disrespectful rude kind "
         "compassionate ignored valued treated humiliated courteous polite attitude"),
    6:  ("Care quality including thorough careful rushed excellent poor skilled "
         "quality competent professional incompetent attentive treatment standard"),
    7:  ("Care coordination including handover referral transferred coordinated "
         "team multidisciplinary communicate specialist pathway integrated"),
    8:  ("Results and information including results report pathology test blood "
         "scan imaging diagnosis findings explained outcome interpret"),
    9:  ("Facilities environment hygiene including parking car park clean "
         "comfortable building hospital room cleanliness signage amenities"),
    10: ("Telehealth including video online consult remote phone virtual zoom "
         "telemedicine digital video call telephone app platform"),
    11: ("Emotional support including anxious reassured felt safe valued dismissed "
         "emotional comfort scared frightened calmed mental health anxiety"),
    12: ("Cultural and accessibility needs including cultural language disability "
         "female practitioner interpreter accessibility diversity inclusion"),
    13: ("Discharge and follow-up including discharge home after care instructions "
         "aftercare post discharge home care medication recovery plan"),
    14: ("Feeling in good hands overall positive satisfied wonderful great "
         "excellent highly recommend outstanding confident trust safe"),
}

# ── Seed corpus: 15 representative sentences per topic (225 total) ────────────
# Used to train classical models at Docker build time.
SEED_CORPUS: List[Tuple[int, str]] = [
    # 0 — Clinical Staff
    (0, "My GP Dr Smith was very thorough and spent extra time answering all my questions about my treatment."),
    (0, "The nurse who administered my injection was professional, gentle, and reassuring throughout the procedure."),
    (0, "I saw a specialist at the clinic and the consultant explained my condition clearly and answered every question."),
    (0, "The physiotherapist Michael was great and gave me a detailed home exercise plan to follow after surgery."),
    (0, "Dr Priya Patel in the respiratory clinic was absolutely wonderful and took time to explain my COPD management plan."),
    (0, "The midwife was incredibly supportive during my labour and made me feel confident and cared for."),
    (0, "My psychologist listened carefully to my concerns and offered practical strategies to manage my anxiety."),
    (0, "The surgeon was highly skilled and the operation went smoothly with no complications whatsoever."),
    (0, "The nurse checked on me regularly and made sure I was comfortable and not in any pain."),
    (0, "I was impressed by the specialist who reviewed my test results and explained the next steps in detail."),
    (0, "The doctor took the time to listen to all my symptoms before making a thorough and accurate diagnosis."),
    (0, "My GP referred me to a physiotherapist who provided excellent treatment for my back pain."),
    (0, "The clinician was knowledgeable and answered all my medical questions without making me feel rushed."),
    (0, "The nursing staff on the ward were attentive and checked in frequently to ensure I was comfortable."),
    (0, "Dr Johnson is an excellent consultant who explained all my treatment options in plain language."),
    # 1 — Administrative Staff
    (1, "The receptionist at the front desk was very helpful when I arrived for my appointment and checked me in quickly."),
    (1, "I had a billing issue and the administrative staff resolved it efficiently and professionally."),
    (1, "The front desk clerk was friendly and organized and managed the queue calmly during a busy morning."),
    (1, "Reception staff were prompt in calling my name and directing me to the correct waiting area."),
    (1, "The admin team processed my referral paperwork quickly and kept me informed about the next steps."),
    (1, "The receptionist answered all my questions about my invoice and helped me understand the billing process."),
    (1, "Front desk staff were very welcoming and made me feel comfortable when I arrived for the first time."),
    (1, "The administrative team sent me appointment reminders by SMS and email which I found very helpful."),
    (1, "I was greeted warmly by reception and the check-in process was smooth and hassle-free."),
    (1, "The billing department contacted me promptly when there was an issue with my health fund claim."),
    (1, "The clinic receptionist was patient and helpful when I needed to reschedule my appointment."),
    (1, "Administrative staff organized my records quickly and ensured all paperwork was completed before my consultation."),
    (1, "The front office team were professional and courteous and helped me complete the intake forms."),
    (1, "The admin clerk guided me through the insurance process step by step and resolved the issue within minutes."),
    (1, "Reception staff were efficient and the check-in process took less than two minutes."),
    # 2 — Efficiency and Flow
    (2, "I waited over two hours past my appointment time which was very frustrating and disrespectful of my time."),
    (2, "The clinic ran on time and I was seen within five minutes of my scheduled appointment."),
    (2, "The queue at the outpatient clinic was very long and there was no clear communication about the delays."),
    (2, "My appointment was delayed by forty-five minutes with no explanation or apology from the staff."),
    (2, "I was impressed by how efficiently the clinic managed patient flow with minimal waiting time."),
    (2, "The waiting room was very crowded and I waited for more than an hour before being seen."),
    (2, "The clinic was running late but staff kept us updated every fifteen minutes which I appreciated."),
    (2, "I was seen quickly and the entire consultation was completed within the scheduled time."),
    (2, "The long wait time at the emergency department was concerning but I understand they were very busy."),
    (2, "The hospital discharge process was slow and I waited three hours to be formally discharged."),
    (2, "I arrived on time but was kept waiting for ninety minutes without any reason given for the delay."),
    (2, "The flow through the clinic was very smooth and I moved efficiently from check-in to consultation to pharmacy."),
    (2, "There were significant delays at the imaging department and I had to wait over an hour for my scan."),
    (2, "The appointment ran on schedule and the doctor did not rush through the consultation despite being busy."),
    (2, "I was frustrated by the inefficiency of the system and the long queue at the pathology collection."),
    # 3 — Booking & Access
    (3, "I tried to book an appointment online through the patient portal but the system kept crashing."),
    (3, "The Zedoc booking system was difficult to navigate and I could not find an available appointment slot."),
    (3, "I called the clinic multiple times to schedule an appointment but no one answered the phone."),
    (3, "The online booking portal was user-friendly and I was able to schedule my appointment within minutes."),
    (3, "I couldn't access the patient portal to book my follow-up appointment and had to call reception instead."),
    (3, "The appointment I booked online was cancelled without any prior notice or explanation."),
    (3, "The clinic offered convenient online booking and I appreciated the variety of available time slots."),
    (3, "I had difficulty rescheduling my appointment through the app because the system showed no available dates."),
    (3, "The GP system was overbooked and I couldn't get an appointment for three weeks despite being unwell."),
    (3, "Booking an appointment was straightforward and I received an immediate confirmation by email."),
    (3, "The patient portal allowed me to manage all my appointments and medical records in one place."),
    (3, "I was unable to book a specialist appointment online and had to visit the clinic in person to schedule."),
    (3, "The telehealth booking link sent to me was broken and I missed my appointment as a result."),
    (3, "Access to after-hours appointments was very limited and I had to wait over a week to be seen."),
    (3, "The Zedoc link worked perfectly and I was connected to my doctor's video consultation on time."),
    # 4 — Information & Shared Decision-Making
    (4, "The doctor explained all my treatment options clearly and asked for my preference before proceeding."),
    (4, "I felt dismissed when I raised my concerns about the medication side effects and was not listened to."),
    (4, "The nurse took time to explain the procedure step by step so I felt fully informed and prepared."),
    (4, "I didn't feel involved in the decisions about my care and wished the doctor had asked for my input."),
    (4, "The specialist informed me of all the risks and benefits before I signed the consent form."),
    (4, "I was told nothing about what to expect after the procedure and had to search for information online."),
    (4, "The GP explained my diagnosis in simple language and gave me written information to take home."),
    (4, "I felt the doctor didn't listen to my concerns about my symptoms and dismissed my worries."),
    (4, "The clinical team shared all the information I needed to make an informed decision about my treatment."),
    (4, "I appreciated that the nurse checked my understanding after explaining the discharge instructions."),
    (4, "The doctor involved me in the discussion about my care plan and respected my choices and preferences."),
    (4, "I was not given enough information about my condition and left the appointment feeling confused."),
    (4, "The physiotherapist explained each exercise and why it was important for my recovery."),
    (4, "I felt the specialist talked over my head using too much medical jargon and didn't check my understanding."),
    (4, "The doctor took time to explain the pros and cons of surgery versus conservative management."),
    # 5 — Dignity & Respect
    (5, "The nurse spoke to me with great kindness and respect throughout my entire hospital stay."),
    (5, "I felt humiliated when the doctor spoke about me to other staff as if I was not in the room."),
    (5, "The staff treated me with dignity and never made me feel judged about my lifestyle choices."),
    (5, "I was spoken to rudely by a staff member and felt very disrespected during my visit."),
    (5, "The doctor was courteous and attentive and made me feel like my concerns were taken seriously."),
    (5, "I felt ignored and dismissed in the waiting room when I tried to ask a question at the desk."),
    (5, "The nursing staff maintained my privacy at all times and always knocked before entering my room."),
    (5, "I felt valued and respected as a patient and the entire team was compassionate and polite."),
    (5, "The receptionist was rude and unhelpful and made me feel unwelcome when I arrived for my appointment."),
    (5, "The doctor listened without judgement and treated me with respect and kindness throughout my consultation."),
    (5, "My dignity was maintained during the examination and the nurse ensured I was always covered appropriately."),
    (5, "I was spoken to dismissively by the consultant who seemed impatient and disinterested in my concerns."),
    (5, "The entire team showed great compassion and respect during what was a very difficult time for me."),
    (5, "I felt my opinions were not valued and the doctor made decisions without consulting me."),
    (5, "The staff were courteous friendly and professional and I always felt welcome and respected at this clinic."),
    # 6 — Care Quality
    (6, "The standard of care I received was outstanding and I could not fault anything about my treatment."),
    (6, "The doctor seemed rushed and did not perform a thorough examination before making a diagnosis."),
    (6, "I received excellent care from the entire team who were skilled and highly professional throughout."),
    (6, "The quality of treatment was poor and I had to seek a second opinion at another hospital."),
    (6, "The nurse changed my dressings carefully and thoroughly and ensured the wound was healing correctly."),
    (6, "The care provided was of a very high standard and I was impressed by the competence of all the staff."),
    (6, "The doctor appeared rushed and did not listen carefully to my symptoms before prescribing medication."),
    (6, "The physiotherapy sessions were professionally delivered and I noticed significant improvement quickly."),
    (6, "The surgeon performed an excellent procedure and my recovery has been smooth and complication-free."),
    (6, "The treatment I received was thorough careful and highly professional and exceeded my expectations."),
    (6, "I was disappointed by the poor quality of care I received which did not meet acceptable standards."),
    (6, "The doctor was attentive and competent and provided a thorough assessment before recommending treatment."),
    (6, "The nursing staff were skilled and attentive and the standard of ward care was consistently high."),
    (6, "The care provided was average at best and I felt the clinical team could have been more thorough."),
    (6, "I received exceptional care from a very skilled and professional team who went above and beyond for me."),
    # 7 — Care Coordination
    (7, "My care was well coordinated between the GP and the specialist and I never felt lost in the system."),
    (7, "The handover between the hospital team and my GP was poorly managed and my records were incomplete."),
    (7, "My referral to the specialist was processed quickly and I received an appointment within two weeks."),
    (7, "The multidisciplinary team worked together seamlessly and my care plan was coordinated effectively."),
    (7, "I was transferred between departments without any communication about my case or care history."),
    (7, "The GP and specialist communicated well and I received consistent information from both providers."),
    (7, "My care coordination was excellent and I always knew who to contact at each stage of my treatment."),
    (7, "There was a serious breakdown in communication between the hospital and my GP about my discharge plan."),
    (7, "The integrated care team coordinated my pathway efficiently from diagnosis through to rehabilitation."),
    (7, "My referral was lost in the system and I waited months before anyone realized the error."),
    (7, "The care team held regular meetings to coordinate my complex care and I was kept informed of all decisions."),
    (7, "My specialist and GP shared notes and I appreciated how seamlessly they coordinated my ongoing care."),
    (7, "After my hospital discharge the community nursing team was well briefed and visited me the next day."),
    (7, "The handover to the palliative care team was compassionate well organized and clearly communicated."),
    (7, "I was impressed by how well the multidisciplinary team coordinated my cancer treatment plan."),
    # 8 — Results & Information
    (8, "I waited three weeks for my blood test results and had to call multiple times to chase them up."),
    (8, "The doctor called me to explain my pathology results clearly and answered all my questions."),
    (8, "My scan results were available on the portal but I couldn't understand what the report meant."),
    (8, "The nurse explained my blood test findings in plain language and I understood exactly what they meant."),
    (8, "I received a letter about my results but the medical terminology was confusing and not explained."),
    (8, "The specialist reviewed my imaging results and provided a clear explanation of what they showed."),
    (8, "I was not informed promptly when my results came back and had to call the clinic to follow up."),
    (8, "The GP explained my cholesterol and blood sugar results and we discussed a management plan together."),
    (8, "My pathology results were uploaded to the portal and my doctor walked me through them in detail."),
    (8, "I received my test results via the app and found the automated report very difficult to interpret."),
    (8, "The radiologist's report was thorough and the specialist explained all the imaging findings clearly."),
    (8, "I didn't understand the results that were read to me over the phone and had no written explanation."),
    (8, "The doctor showed me my MRI scan and explained what the findings meant for my diagnosis and treatment."),
    (8, "My biopsy results were communicated sensitively by the oncologist who allowed time for questions."),
    (8, "I was given my test results at the consultation and the doctor explained everything very clearly."),
    # 9 — Facilities & Environment & Environmental Hygiene
    (9, "The clinic was spotlessly clean and well maintained and I felt comfortable in the environment."),
    (9, "The parking at the hospital was very limited and I had to walk a long distance from the car park."),
    (9, "The waiting room was cramped and uncomfortable with insufficient seating for the number of patients."),
    (9, "The hospital facilities were modern and well-equipped and the rooms were clean and comfortable."),
    (9, "The toilets in the outpatient clinic were not cleaned regularly and I found this very concerning."),
    (9, "The signage throughout the building was clear and I had no difficulty finding the correct department."),
    (9, "The ward was very noisy at night and I found it difficult to rest during my hospital stay."),
    (9, "The clinic environment was welcoming and the decor was calming and professionally maintained."),
    (9, "The parking situation was a major issue as there were very few spots and the area was poorly lit."),
    (9, "The hospital room was clean comfortable and well-equipped with all the amenities I needed."),
    (9, "I was concerned about hygiene standards as I noticed used equipment left in the common areas."),
    (9, "The building was accessible for wheelchair users with ramps lifts and disabled parking available."),
    (9, "The car park was expensive and inconveniently located making it difficult for elderly patients."),
    (9, "The clinic maintained excellent infection control practices and I felt very safe during my visit."),
    (9, "The environment was clean quiet and peaceful and I felt very comfortable during my stay."),
    # 10 — Telehealth
    (10, "My telehealth consultation via video call was smooth and I connected to my doctor without any issues."),
    (10, "The online consult was convenient and saved me a two-hour drive to the clinic for a routine follow-up."),
    (10, "I had a phone consultation with my GP which was helpful but I felt a face-to-face would have been better."),
    (10, "The Zoom link for my telehealth appointment didn't work and I missed my consultation as a result."),
    (10, "My video appointment was professional and the doctor was able to assess my condition effectively remotely."),
    (10, "I was impressed by the quality of the telehealth platform and found the virtual consultation very convenient."),
    (10, "The remote consultation with the psychologist was just as effective as an in-person session."),
    (10, "The digital health app allowed me to consult with my GP from home which was very convenient."),
    (10, "My telemedicine appointment ran smoothly and the doctor sent a prescription to my pharmacy electronically."),
    (10, "The online consult was a great option for a quick review and I appreciated not having to travel."),
    (10, "I struggled with the technology for my video call and couldn't connect properly to the virtual consultation."),
    (10, "The telehealth appointment was efficient and my concerns were addressed thoroughly via the video platform."),
    (10, "The phone consultation was fine for a routine check but I felt a video call would have been more thorough."),
    (10, "My psychiatrist offered telehealth sessions which made it much easier to attend regular appointments."),
    (10, "The remote consultation worked well and my doctor followed up with a detailed written summary by email."),
    # 11 — Emotional Support
    (11, "I was very anxious before my procedure but the nurse reassured me and helped me feel calm."),
    (11, "The staff noticed I was distressed and took time to sit with me and offer emotional support."),
    (11, "I felt safe and supported throughout my hospital stay and never felt alone or frightened."),
    (11, "The doctor seemed unaware of how scared I was and did not offer any reassurance or comfort."),
    (11, "The counsellor was compassionate and created a safe space for me to express my feelings freely."),
    (11, "I was very worried about my diagnosis but the nurse provided wonderful emotional support and comfort."),
    (11, "The team checked in on my emotional wellbeing regularly during my long hospital admission."),
    (11, "I felt dismissed when I expressed my anxiety and the doctor did not acknowledge my emotional state."),
    (11, "The social worker provided excellent support to my family during a very difficult and uncertain time."),
    (11, "I felt valued and cared for by the nursing team who always took time to check how I was feeling."),
    (11, "The mental health nurse was incredibly supportive and helped me feel less anxious about my treatment."),
    (11, "I was frightened after receiving my diagnosis but the care team provided outstanding emotional support."),
    (11, "The staff were empathetic and acknowledged my distress and provided comfort at a very difficult time."),
    (11, "I felt the doctor was clinical and impersonal and did not acknowledge the emotional impact of my diagnosis."),
    (11, "The nursing team went above and beyond to support me emotionally during my recovery."),
    # 12 — Cultural & Accessibility Needs
    (12, "An interpreter was provided for my appointment which allowed me to communicate effectively with my doctor."),
    (12, "My request for a female practitioner was respected without question and I felt comfortable throughout."),
    (12, "The clinic was not wheelchair accessible and I had difficulty navigating the building."),
    (12, "The staff were culturally sensitive and respectful of my religious practices during my hospital stay."),
    (12, "Language was a significant barrier and no interpreter was offered despite my limited English."),
    (12, "The clinic accommodated my disability needs and ensured I had access to appropriate facilities."),
    (12, "I appreciated that the staff asked about my cultural background and dietary preferences during admission."),
    (12, "The clinic did not have materials available in my language and I struggled to understand the information given."),
    (12, "The team was inclusive and respectful of my identity and I felt welcomed and safe during my visit."),
    (12, "I requested a female doctor for my examination and my preference was respected and accommodated."),
    (12, "The hospital had hearing loop facilities and staff were trained to communicate with hearing-impaired patients."),
    (12, "I felt my cultural and spiritual needs were not understood or accommodated during my hospital stay."),
    (12, "The clinic offered LGBTQ-inclusive care and I felt safe and respected throughout my treatment."),
    (12, "I needed an interpreter for my consultation but none was available and I struggled to communicate."),
    (12, "The team was respectful of my cultural dietary requirements and made appropriate arrangements."),
    # 13 — Discharge & Follow-up
    (13, "I received clear written discharge instructions including my medication schedule and follow-up appointments."),
    (13, "I was discharged without adequate information about what to expect during my recovery at home."),
    (13, "The follow-up appointment was organized before I left the hospital and I felt well supported after discharge."),
    (13, "I was not given clear instructions about my medications when I was discharged and became very confused."),
    (13, "The discharge planning was thorough and community nursing was arranged to visit me at home."),
    (13, "My GP received a detailed discharge summary within 24 hours of my hospital discharge."),
    (13, "I felt very unprepared when I went home after surgery as the aftercare instructions were minimal."),
    (13, "The post-operative follow-up appointment was scheduled promptly and my recovery was monitored closely."),
    (13, "I was given a clear aftercare plan and knew exactly who to contact if I had any concerns at home."),
    (13, "My discharge was rushed and I felt I was sent home too early without adequate support in place."),
    (13, "The team ensured I understood all my post-discharge instructions before I left the hospital."),
    (13, "I received a phone call from the clinic the day after discharge to check on my recovery and wellbeing."),
    (13, "The follow-up appointment confirmed my recovery was on track and my wound was healing well."),
    (13, "I was not contacted after discharge and had to call the clinic myself when I experienced complications."),
    (13, "The home care package was arranged before discharge and the transition from hospital to home was smooth."),
    # 14 — Feeling in Good Hands
    (14, "I felt completely confident in my healthcare team and trusted them with my care throughout my treatment."),
    (14, "The overall experience was outstanding and I left feeling very satisfied with the care I received."),
    (14, "I have never felt so well looked after and I would highly recommend this clinic to family and friends."),
    (14, "My experience at this hospital was positive and I felt safe and well cared for from start to finish."),
    (14, "I am very grateful for the exceptional care I received and feel confident about my recovery."),
    (14, "The entire team was wonderful and I left every appointment feeling reassured and in good hands."),
    (14, "I was impressed by the professionalism and dedication of the whole team and felt very well looked after."),
    (14, "My overall satisfaction with the care I received was very high and I cannot praise the team enough."),
    (14, "I felt at ease throughout my treatment knowing I was being cared for by such a skilled and caring team."),
    (14, "The clinic exceeded my expectations and I am extremely satisfied with every aspect of my care."),
    (14, "I have complete trust in this healthcare team and feel confident about my ongoing management plan."),
    (14, "My overall experience was excellent and I felt supported and cared for at every step of my journey."),
    (14, "I would not hesitate to recommend this clinic and I feel very lucky to have such wonderful care."),
    (14, "The care I received was truly exceptional and I feel very confident and positive about my health outcomes."),
    (14, "I left the clinic feeling reassured satisfied and grateful for the outstanding level of care I received."),
]

# ── Convenience helpers ────────────────────────────────────────────────────────

def get_seed_texts() -> List[str]:
    """Return just the text strings from the seed corpus."""
    return [text for _, text in SEED_CORPUS]


def get_seed_labels() -> List[int]:
    """Return just the topic indices from the seed corpus."""
    return [label for label, _ in SEED_CORPUS]


def get_all_topic_names() -> List[str]:
    """Return the list of topic names in index order."""
    return [TOPIC_NAMES[i] for i in range(N_TOPICS)]
