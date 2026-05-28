"""
Script to extend Patients Q–AJ from 5–6 months to 12 months each in ui/app.py.
Each anchor is a unique phrase from the patient's LAST existing month entry.
The new months are inserted before the closing `    },` of each patient dict.

Fix notes (v2):
- Anchors no longer include a leading `"` that doesn't appear in the file.
- Closing brace spacing: new_months ends with 4-space indent; we append `},'`
  (no extra spaces) so the final `    },` has correct 4-space indentation.
"""

APP_PATH = "ui/app.py"

# Anchor format: unique phrase that ends right before `"\n        ),\n    },`
# The anchor must appear EXACTLY ONCE in the file.
# Replacement: insert new_months after the last month's `),` and before `    },`.

INSERTIONS = [

    # ── Patient Q — COPD (Dr Priya Patel, Karen Thompson) ─────────────────────
    (
        'I am grateful to have found this team."\n        ),\n    },',
        '''\
        "Month 7 — July (Summer Heat Impact)": (
            "The summer heat has been a challenge for my COPD — high temperatures and "
            "humidity worsen my breathlessness more than cold air does. Dr Patel had "
            "forewarned me at my June review and provided written guidance on adjusting "
            "my activity schedule during heatwave conditions. Karen Thompson rang "
            "proactively when a heat advisory was issued to check whether I needed an "
            "earlier review. I did not require it, but the call itself was reassuring. "
            "Managing COPD in a Queensland summer is harder than I expected but "
            "I feel equipped to do it."
        ),
        "Month 8 — August (Spirometry Recheck)": (
            "Dr Patel completed a full spirometry recheck this month as part of my "
            "revised three-monthly schedule. My FEV1 has remained stable since March "
            "— no further decline — and Dr Patel described this as a meaningful outcome "
            "given the severity of my initial presentation. I have not required my "
            "reliever more than twice per week across the past six weeks, meeting the "
            "target she set when I started pulmonary rehabilitation. Stability in COPD "
            "is a genuine achievement worth recognising."
        ),
        "Month 9 — September (Minor Exacerbation — Self-Managed)": (
            "I experienced a mild exacerbation in mid-September — increased sputum, "
            "more breathlessness, and a low-grade fever. I followed my written action "
            "plan precisely: started the standby antibiotics on day two, increased my "
            "reliever to four-hourly, and called the clinic to report the event. "
            "The nurse advised me by phone and I avoided hospital entirely. Dr Patel "
            "reviewed me at the end of the month and confirmed the self-management "
            "had been correct. Two years ago I would have called an ambulance."
        ),
        "Month 10 — October (Post-Exacerbation Review)": (
            "My post-exacerbation lung function has returned to my recent stable "
            "baseline and Dr Patel is satisfied with the recovery. She adjusted my "
            "long-acting bronchodilator slightly to provide better cover during periods "
            "of higher demand. Karen Thompson set up my next two appointments in "
            "advance so I have continuity through the winter months. I feel more "
            "confident managing this condition than I did twelve months ago — the "
            "combination of good clinical care and patient education has genuinely "
            "changed my trajectory."
        ),
        "Month 11 — November (Winter Preparation Completed)": (
            "Both my influenza and pneumococcal vaccinations are up to date and my "
            "COPD action plan has been reviewed and updated for the coming winter. "
            "Dr Patel added a note about managing COPD during bushfire smoke events "
            "— thoughtful, practical advice I had not considered. My peak flow diary "
            "for the past month shows consistent readings within my personal best "
            "range. The progress from January to November has been more meaningful "
            "than I imagined when I first sat anxiously in Dr Patel's waiting room."
        ),
        "Month 12 — December (Annual Review — Twelve Months of Progress)": (
            "My twelve-month review with Dr Patel marks one full year of structured "
            "COPD management. My exacerbation rate is two this year — both self-managed "
            "without hospitalisation — compared to four in the preceding year including "
            "one emergency department visit. Dr Patel showed me the spirometry trend "
            "chart showing stability across all six measurements. Karen Thompson wished "
            "me a good Christmas as I left. I am sixty-seven, working part-time, and "
            "managing my COPD. This time last year I was not sure I could say that."
        ),
    '''),

    # ── Patient R — Musculoskeletal (45 Albert St, Westfield, elderly) ────────
    (
        'I am glad I said something."\n        ),\n    },',
        '''\
        "Month 7 — July (Hydrotherapy Milestone)": (
            "I have now attended twelve hydrotherapy sessions and the physiotherapist "
            "has commented that my hip flexion has improved to a level not expected at "
            "this stage given my age and initial presentation. I continue to use the "
            "patient transport service for every appointment at 45 Albert Street. "
            "The volunteer driver, a retired nurse named Bert, has become a familiar "
            "and reassuring presence. I told another patient in the waiting room about "
            "the transport service and she was completely unaware of it — communication "
            "gaps about this resource clearly persist."
        ),
        "Month 8 — August (Physiotherapy Discharge Planning)": (
            "My physiotherapist has begun discussing a discharge plan from formal "
            "sessions to a home maintenance program. I am not alarmed by this as I "
            "was earlier in my care — the goal was always to build independence rather "
            "than dependence. I can walk to the end of my street and back three times "
            "without stopping to rest. At 74 and having entered this program barely "
            "mobile, that progress is not small. The call-ahead parking bay at "
            "45 Albert Street continues to be available and used by other patients."
        ),
        "Month 9 — September (Medication Reduced Further)": (
            "The specialist reduced my pain medication by a second step this month. "
            "I manage two to three days per week with paracetamol only and my remaining "
            "days require only a mild analgesic. The specialist noted that my reported "
            "pain scores have been consistently lower than my objective physical "
            "assessments — suggesting I have adjusted my expectations upward, which is "
            "a positive sign of adaptation. Hydrotherapy continues once weekly "
            "as maintenance."
        ),
        "Month 10 — October (Functional Independence Growing)": (
            "I walked to my local shops — three hundred metres each way — without "
            "my walking stick for the first time since my back injury two years ago. "
            "The physiotherapist was pleased when I reported this at my monthly check. "
            "I am managing my own domestic tasks more independently, which matters "
            "enormously to my sense of dignity. My neighbour still drives me to "
            "appointments when Bert is unavailable but I no longer rely on her "
            "for shopping or housework."
        ),
        "Month 11 — November (Discharge from Formal Physiotherapy)": (
            "My physiotherapist formally discharged me from weekly sessions and "
            "gave me a detailed home program to continue independently. She spent "
            "forty minutes ensuring I could perform each exercise correctly and provided "
            "a printed guide with photographs. The specialist extended my review to "
            "six-monthly. I thanked the patient transport service coordinator in "
            "writing — without that service I would not have maintained attendance, "
            "and without attendance I would not have recovered."
        ),
        "Month 12 — December (Year-End Review — Meaningful Recovery)": (
            "Twelve months ago I arrived at 45 Albert Street in significant pain, "
            "exhausted from the walk from the Westfield car park. I am now walking "
            "without assistance for most activities, managing my own home, and attending "
            "reviews via patient transport without drama. The parking access improvement, "
            "the transport service, the hydrotherapy, and the consistent clinical care "
            "have each contributed to an outcome I am genuinely grateful for. "
            "At 74, I am managing my own life again."
        ),
    '''),

    # ── Patient S — RA (Dr James Richardson, Angela Chen, 07 3456 7890) ───────
    (
        'it led me to advocate for better care and I am glad I did."\n        ),\n    },',
        '''\
        "Month 7 — June 2026 (Bimonthly Review — Continuing Stability)": (
            "My first bimonthly review with Dr Patel confirmed the reduced frequency "
            "is appropriate — my inflammatory markers remain within the acceptable "
            "range and I have had no flare episodes since April. Angela accompanied "
            "me and was pleased with the progress report. I called the clinic at "
            "07 3456 7890 before the appointment to confirm timing and reached a "
            "staff member on the first attempt — the phone line reliability appears "
            "to have improved. Small operational improvements matter alongside "
            "clinical ones."
        ),
        "Month 8 — July 2026 (Summer Management — Holiday)": (
            "Angela and I managed a week's holiday in the Whitsundays this month "
            "— something I would not have contemplated at the height of my January "
            "flare. I carried my written action plan and medication list and had no "
            "significant joint symptoms throughout the trip. My methotrexate schedule "
            "was maintained without interruption. I have recommended Dr Patel to "
            "three people since February — the contrast in care quality between my "
            "early appointments and my current experience has been significant."
        ),
        "Month 9 — August 2026 (Occupational Therapy Review)": (
            "I attended a follow-up session with the occupational therapist to review "
            "the joint protection techniques I learned in April. She identified one "
            "modification that further reduces load on my wrist joints during computer "
            "work. Angela joined by phone and learned complementary strategies for "
            "supporting me during any future flare without taking over tasks I can "
            "manage myself. The OT's approach respects both my independence and the "
            "reality of living with RA as a couple."
        ),
        "Month 10 — September 2026 (Twelve-Month Progress Milestone)": (
            "Twelve months have passed since the December 2025 flare that brought "
            "me back into active specialist care. The trajectory from that nadir to "
            "the current stable phase represents the best twelve months of RA "
            "management I have experienced in six years. My inflammatory markers "
            "are consistently within range, I have had two minor flares both "
            "self-managed, and I have not missed a single dose of my adjusted "
            "methotrexate schedule. Angela says the improvement has been "
            "transformative for our household as well as for me personally."
        ),
        "Month 11 — October 2026 (Medication Review — Long-term Plan)": (
            "Dr Patel reviewed my long-term medication plan and discussed a slow "
            "methotrexate dose reduction if the next three months remain stable. "
            "That conversation — about reducing rather than managing medication — "
            "represents a shift in clinical expectation I had not anticipated in "
            "January. I called the clinic at 07 3456 7890 to ask about the proposed "
            "reduction and reached the nurse coordinator directly without hold time. "
            "The operational improvements have been as meaningful as the clinical ones."
        ),
        "Month 12 — November 2026 (Annual Review — A Year Transformed)": (
            "My annual review with Dr Patel marks one full year of high-quality RA "
            "management following the January 2026 experience that prompted me to "
            "request a different specialist. I reflected on the courage it took to "
            "raise that concern — and on the difference it has made. Dr Patel has "
            "earned my complete trust through consistent clinical excellence and "
            "genuine listening. Angela was present and expressed her own gratitude "
            "directly. Advocating for the right care is the most important clinical "
            "decision I have made in six years."
        ),
    '''),

    # ── Patient T — Post-Knee Surgery (Michael, susan.obrien82@gmail.com) ─────
    (
        'the recovery feel supervised rather than solitary."\n        ),\n    },',
        '''\
        "Month 7 — July (Independent Exercise Program)": (
            "I have been following Michael's maintenance program independently for "
            "four weeks and my compliance has been excellent — partly because he "
            "designed it around activities I actually do rather than generic exercises. "
            "I emailed him at the practice address to report my one-month progress "
            "and received a brief reply confirming my numbers were strong. Even at "
            "the discharge stage his responsiveness has not diminished. My flexion "
            "is holding at 118 degrees and my pain-free walking distance continues "
            "to increase."
        ),
        "Month 8 — August (Full Return to Gardening)": (
            "I spent three hours in my garden last weekend — pruning, weeding, and "
            "replanting the beds neglected since my surgery in January. Seven months "
            "ago I had been told to expect six to twelve months of recovery and I am "
            "pleased to be toward the shorter end of that range. Michael's "
            "physiotherapy approach and his email follow-up to "
            "susan.obrien82@gmail.com made the recovery feel managed rather than "
            "uncertain. I have recommended him to a friend scheduled for the same "
            "procedure next month."
        ),
        "Month 9 — September (GP Review — Excellent Outcome)": (
            "My GP reviewed my recovery at my routine appointment and described the "
            "outcome as excellent for my age group. She noted that physiotherapy "
            "engagement is the most significant predictor of good outcomes after knee "
            "replacement and that Michael's follow-up approach was likely a contributing "
            "factor in my compliance. My knee is functional for all the activities I "
            "care about — gardening, walking my district, and managing my home "
            "independently. I did not expect to be saying that nine months post-surgery."
        ),
        "Month 10 — October (Stair Climbing Achieved)": (
            "I climbed and descended a flight of stairs unaided this month at my "
            "niece's house — an environment I had been avoiding because the rail is "
            "on the wrong side for my recovery. The achievement felt significant not "
            "because stairs are dramatic but because they had represented a specific "
            "limitation in my mind. I sent Michael a brief email to report it. He "
            "replied within the day, noting it marked a functional milestone in his "
            "post-discharge framework. The ongoing communication feels genuinely "
            "connected even months after formal discharge."
        ),
        "Month 11 — November (Ten-Month Functional Assessment)": (
            "I completed a self-reported functional assessment questionnaire at my "
            "ten-month mark. My scores on all domains — pain, mobility, daily "
            "activities, and psychological wellbeing — were in the excellent range "
            "compared to the pre-surgical baseline. My knee pain scores have been "
            "consistently zero to one out of ten for the past six weeks. Living "
            "alone through a total knee replacement recovery requires careful support, "
            "and Michael's structured physiotherapy and email engagement provided "
            "that structure at the right times."
        ),
        "Month 12 — December (Twelve-Month Review — Full Recovery)": (
            "Twelve months post-surgery I attended a one-year review with the "
            "orthopaedic team. X-rays confirmed the prosthesis is well-positioned "
            "and the joint is stable. I reported full functional independence in "
            "all activities including gardening, extended walks, and stair navigation. "
            "The surgical team noted my outcome was in the top quartile for patients "
            "of my age. I gave credit to Michael's physiotherapy program and the "
            "email follow-up system to susan.obrien82@gmail.com that kept me "
            "engaged throughout. The right support at the right moments changes outcomes."
        ),
    '''),

    # ── Patient U — T2D New (Dr Nguyen, Ipswich, Zedoc) ──────────────────────
    (
        'I am grateful for the coordinated care between this clinic and Dr Nguyen at Ipswich."\n        ),\n    },',
        '''\
        "Month 7 — July (HbA1c Target Achieved)": (
            "My three-month HbA1c result came back at 6.9 — the first time I have "
            "been within the target range in four years. The diabetes educator "
            "celebrated with me at my July appointment and we reviewed the factors "
            "that drove the improvement: consistent evening walks, better injection "
            "technique, reduced carbohydrate loading at dinner. Dr Nguyen at Ipswich "
            "Hospital received the clinic letter and called me personally to "
            "congratulate me — a gesture I appreciated enormously given the long "
            "road to this result."
        ),
        "Month 8 — August (Maintaining Progress Through Summer)": (
            "Maintaining my exercise routine through the Queensland summer has been "
            "challenging — the heat makes evening walks uncomfortable and I have "
            "had to shift to early morning exercise. My glucose readings have remained "
            "stable despite the routine adjustment. The diabetes educator offered "
            "practical advice about hydration and monitoring during hot weather. "
            "I used the Zedoc portal to send a query and received a reply within two "
            "business days — a marked improvement from the difficulty I had navigating "
            "the system in February."
        ),
        "Month 9 — September (Insulin Dose Reduced)": (
            "My insulin dose has been reduced by fifteen percent this month — a direct "
            "result of the HbA1c improvement and the elimination of overnight "
            "hypoglycaemia. Reducing insulin after eleven years of progressive "
            "increases feels like a significant clinical reversal. The team was clear "
            "that this reflects genuine metabolic improvement rather than a medication "
            "adjustment, and that the lifestyle changes I have made are the mechanism. "
            "Dr Nguyen at Ipswich has been updated via the coordinated letter system."
        ),
        "Month 10 — October (Community Exercise Group)": (
            "The diabetes clinic runs a monthly community walk group and I attended "
            "my first session this month. Meeting others at different stages of "
            "diabetes management was more motivating than I expected — I was asked "
            "by a recently-diagnosed participant about my experience, and realising "
            "I had useful knowledge to share was a significant shift from my January "
            "feeling of helplessness. Peer connection had not been part of my diabetes "
            "care before this clinic."
        ),
        "Month 11 — November (Six-Month HbA1c at Target)": (
            "My six-month HbA1c result is 6.8 — stable within the target range for "
            "a second consecutive measurement. The diabetes team has moved me to "
            "quarterly reviews as my management is now well-established. I have been "
            "using the Zedoc portal for all bookings and messages for four months "
            "without difficulty. The rocky onboarding in February seems distant now. "
            "Dr Nguyen at Ipswich received the six-month summary and noted my case "
            "as a successful transition model for other referrals."
        ),
        "Month 12 — December (Annual Review — A Year of Change)": (
            "Twelve months ago Dr Nguyen referred me with an HbA1c of 9.2 and "
            "a decade of drifting diabetes management. My current reading is 6.8. "
            "The annual review included a diabetes distress screening for the first "
            "time — my scores reflected the transformation from overwhelmed to engaged. "
            "The team documented this as a model outcome for a late-stage intensification "
            "referral. I brought a written note of thanks to the diabetes educator "
            "and to reception. The year has been medically significant and personally "
            "transformative."
        ),
    '''),

    # ── Patient V — T2D Established (Nurse Rebecca Taylor, Dr Samantha Lee, Toowoomba) ──
    (
        'changed the trajectory of my health."\n        ),\n    },',
        '''\
        "Month 7 — July (HbA1c Reaches Target)": (
            "My HbA1c this month is 6.8 — within the target range and the best result "
            "I have had since my first year post-diagnosis. Nurse Rebecca printed the "
            "six-month trend chart and highlighted each inflection point, connecting "
            "it to a specific dietary or medication change. That visual representation "
            "of cause and effect was more motivating than any single number. Dr Lee "
            "at Toowoomba Medical Practice received the quarterly letter and called "
            "to express genuine pleasure at the outcome."
        ),
        "Month 8 — August (Quarterly Review Schedule)": (
            "I have been moved to quarterly specialist reviews given the stability of "
            "my HbA1c and insulin management. The transition from monthly to quarterly "
            "felt like a graduation rather than a reduction in care. Rebecca explained "
            "that my self-management skills are sufficient for longer intervals between "
            "specialist contact — but that I can always reach out between appointments "
            "if needed. Dr Lee at Toowoomba is managing my routine monitoring and "
            "communicates directly with Rebecca for anything requiring specialist input."
        ),
        "Month 9 — September (Dietary Adherence Over Spring)": (
            "Spring has brought more social engagements and I have navigated restaurant "
            "dining successfully using the carbohydrate counting skills I developed "
            "with the clinic dietitian in April. My glucose readings on event days "
            "have been consistently better than I managed on similar occasions before "
            "this year's intervention. The practical skill of estimating meal "
            "carbohydrate content has become second nature. Rebecca described this "
            "as 'embedded learning' at my last check-in — a phrase that resonated."
        ),
        "Month 10 — October (Peer Support Role)": (
            "Nurse Rebecca asked whether I would speak informally with a newly-referred "
            "patient resistant to insulin therapy — a barrier I had experienced myself. "
            "I agreed, and the conversation was briefly facilitated by Rebecca before "
            "she left us to talk. Being asked to contribute from my own experience was "
            "meaningful to me as a patient. My engagement with this clinic's program "
            "extends beyond my own outcomes — it has the potential to support others "
            "managing the same challenges."
        ),
        "Month 11 — November (Dr Lee Annual Review — Toowoomba)": (
            "My annual review at Toowoomba Medical Practice with Dr Lee was "
            "comprehensive — full bloods, renal function, lipid profile, retinal "
            "screening, and foot assessment. Every result was within the acceptable "
            "range or improved from last year. Dr Lee noted that my case represents "
            "the kind of successful diabetes reversal in management direction that is "
            "achievable with the right specialist support. She mentioned Rebecca by "
            "name when describing what had made the difference."
        ),
        "Month 12 — December (Year's Achievement — A Full Year of Control)": (
            "Twelve months ago my HbA1c was 8.9 and I was embarrassed about the "
            "deterioration after the Christmas holidays. Today it is 6.8 and I am "
            "the patient sharing my experience with others. Nurse Rebecca and Dr Lee "
            "at Toowoomba have been the anchors of a year that has genuinely changed "
            "my health trajectory. I have recommended this clinic to four friends. "
            "The forty-minute consultation in February, when Rebecca explained "
            "glycaemic index in a way that finally made sense, remains the turning "
            "point of my diabetes journey."
        ),
    '''),

    # ── Patient W — COPD Long-term (Dr Patel, granddaughter's wedding) ────────
    (
        'back confidence in my own ability to live well with a chronic condition."\n        ),\n    },',
        '''\
        "Month 7 — July (Wedding Month — Attended)": (
            "I attended my granddaughter's wedding this month — something Dr Patel "
            "and I had discussed at my February annual review when she asked whether "
            "I was managing well enough to attend. I walked my granddaughter down "
            "the aisle and danced once with my wife. I needed my reliever after "
            "the dancing but managed the full evening without distress. Dr Patel "
            "had helped me prepare a strategy including pre-event bronchodilator "
            "timing and a plan for the reception venue. Five years of good COPD "
            "management made this possible."
        ),
        "Month 8 — August (Post-Wedding Review)": (
            "Dr Patel asked at my August review how the wedding went and I told her "
            "everything — the aisle walk, the dancing, the reliever, and the pride. "
            "She was visibly pleased and noted in my record that the functional target "
            "we had discussed in February had been achieved. This is the kind of "
            "continuity that makes long-term care meaningful: a clinician who connects "
            "a patient's medical goals to the life events that give those goals their "
            "real significance. My lung function remains stable and my exacerbation "
            "rate for the year is the lowest in five."
        ),
        "Month 9 — September (Respiratory Stability Maintained)": (
            "My peak flow diary for September shows readings consistently above my "
            "personal best from four years ago — an improvement Dr Patel attributes "
            "to medication optimisation and sustained rehabilitation. I have also "
            "significantly reduced my exposure to cold air, one of my personal "
            "exacerbation triggers, by adjusting my morning walk timing. The patient "
            "portal message Dr Patel sent reviewing my diary was a model of "
            "personalised monitoring — I have been keeping the diary more consistently "
            "as a result."
        ),
        "Month 10 — October (Winter Preparation — Fifth Year)": (
            "For the fifth consecutive year I have prepared my COPD winter action "
            "plan with Dr Patel. The process is now familiar — vaccination status "
            "confirmed, standby antibiotic prescription renewed, peak flow targets "
            "recalibrated for the season. What was anxiety-provoking five years ago "
            "is now routine and reassuring. I know what to do when an exacerbation "
            "starts, who to call if it worsens, and what threshold means I need the "
            "emergency department. That knowledge removes panic from the equation."
        ),
        "Month 11 — November (Minor Infection — Action Plan Used Again)": (
            "I had a mild respiratory infection this month and followed my action "
            "plan for the second consecutive year without requiring hospitalisation. "
            "The standby antibiotics were effective and I contacted the clinic on "
            "day three to report the event as the plan requires. The nurse updated "
            "my record and arranged an earlier review with Dr Patel, who confirmed "
            "the infection had resolved. Four years ago this infection would have "
            "meant an emergency department visit. Good self-management education "
            "and a trusted action plan changed that."
        ),
        "Month 12 — December (Five-Year Milestone — Annual Review)": (
            "My December review with Dr Patel marks five years as her patient and "
            "twelve months since she was monitoring my preparations for my "
            "granddaughter's wedding. She printed a five-year lung function trend "
            "chart: stable FEV1, declining exacerbation frequency, no hospitalisations "
            "in three years. Then she asked about Christmas plans and whether my "
            "granddaughter would be visiting. Five years in and she still remembers "
            "what matters to me beyond the clinical numbers. That is what continuity "
            "of care means in practice."
        ),
    '''),

    # ── Patient X — Cardiac Elderly 81yo (Sarah Fitzpatrick, Medicare 2345 67890 1) ──
    (
        'alongside my clinical ones."\n        ),\n    },',
        '''\
        "Month 7 — June 2026 (Cardiac Monitoring — Stable)": (
            "My cardiac rhythm has remained stable for a full quarter and the "
            "cardiologist has extended my monitoring review to four-monthly. "
            "Sarah attended by telephone from Toowoomba — the clinic's willingness "
            "to include her by phone at every appointment has been one of the most "
            "supportive aspects of my care. At 81 with my daughter not always nearby, "
            "knowing she is included in clinical conversations gives us both confidence. "
            "The billing team confirmed Medicare number 2345 67890 1 has been "
            "correctly processed for all subsequent claims."
        ),
        "Month 8 — July 2026 (Sarah's Visit — Joint Appointment)": (
            "Sarah drove from Toowoomba this month and accompanied me in person for "
            "the first time since February. The cardiologist offered extra time in the "
            "appointment so Sarah could ask her questions directly. She had prepared "
            "a list — medication interactions, activity limits, emergency indicators "
            "— and the cardiologist addressed each one. Having that conversation on "
            "record and in front of both of us was more valuable than any letter or "
            "phone call. Sarah left feeling confident about managing my care remotely "
            "and I left feeling my concerns had been fully heard."
        ),
        "Month 9 — August 2026 (Winter Health — Managed Well)": (
            "The winter months have been well-managed. My blood pressure has been "
            "slightly elevated on cold mornings — a seasonal pattern my GP expected "
            "— but within acceptable parameters. The clinic arranged a telehealth "
            "check with the cardiologist in response to my GP's note, and the brief "
            "review confirmed no medication adjustment was needed. The proactive "
            "coordination between my GP and the cardiac clinic has removed the need "
            "for me to manage the flow of information myself — at 81, that burden "
            "reduction matters practically."
        ),
        "Month 10 — September 2026 (Annual Review Approaching)": (
            "My twelve-month cardiac review is scheduled for October. The "
            "administrative team has confirmed the larger-print letter format I "
            "requested last year will be used for all future correspondence — I "
            "received this month's reminder letter in the preferred format without "
            "having to request it. Sarah will attend by phone. We have prepared my "
            "question list together in a video call — it makes me feel less alone "
            "in preparing for appointments."
        ),
        "Month 11 — October 2026 (Annual Cardiac Assessment)": (
            "My twelve-month cardiac review confirmed my rhythm remains controlled "
            "and the medication combination is well-tolerated. The echocardiogram "
            "showed no change from baseline — stable and managed. Sarah joined by "
            "phone and the cardiologist walked through all her questions. I mentioned "
            "the billing error from January 2026 and the cardiologist confirmed it "
            "had been noted in the quality improvement record and used in a billing "
            "audit training session. My feedback contributed to something beyond "
            "my own care."
        ),
        "Month 12 — November 2026 (One Year Since Referral — Settled & Well)": (
            "One year since my GP referred me following that abnormal ECG at my "
            "annual health check. I am stable, on well-tolerated medications, and "
            "supported by a team that has consistently accommodated my practical "
            "needs as an 81-year-old managing without a carer on site. Sarah's phone "
            "participation at every appointment has been enabled rather than just "
            "permitted. The forms assistance policy from my January 2026 feedback "
            "is now standard. I came into this care relationship anxious. I leave "
            "this year settled, informed, and grateful."
        ),
    '''),

    # ── Patient Y — Pregnancy (Lisa, Jenny, George Street) ───────────────────
    (
        'I will remember with genuine gratitude rather than anxiety."\n        ),\n    },',
        '''\
        "Month 7 — April (Thriving at Three Months Postnatal)": (
            "My son is three months old and feeding well, sleeping in four-hour "
            "stretches, and growing exactly as expected at his GP checks. I attended "
            "the monthly parents' group at George Street again this month — the group "
            "has become a genuine community of five families who had similar due dates. "
            "Jenny stopped by the group session briefly and was greeted warmly by "
            "everyone. Her presence was symbolic as much as clinical — a reminder "
            "of the team who had cared for all of us through pregnancy."
        ),
        "Month 8 — May (Planning Return to Work)": (
            "I am planning to return to work in two months and attended a session "
            "at the centre on George Street about the emotional aspects of returning "
            "after maternity leave. Lisa had recommended this resource at my six-week "
            "postnatal review. The session addressed separation anxiety, managing "
            "guilt about childcare decisions, and maintaining breastfeeding after "
            "return — three topics I had been anxious about. Having access to this "
            "resource through the same midwifery service that supported my pregnancy "
            "provided welcome continuity."
        ),
        "Month 9 — June (Five Months Postnatal — Wellbeing Check)": (
            "My GP completed a five-month postnatal wellbeing check including the "
            "Edinburgh Postnatal Depression Scale. My scores were in the healthy "
            "range and my GP noted that the social connections from the George Street "
            "parents' group and the quality of my antenatal support had likely "
            "contributed to my resilience during the transition to parenthood. "
            "I thought of Lisa and Jenny when she said that. The foundation they "
            "built during my pregnancy extended well into my postnatal experience."
        ),
        "Month 10 — July (Returned to Work)": (
            "I returned to work part-time this month. My son started at a childcare "
            "centre near my workplace. The first week was hard — I cried on the way "
            "to work on Monday and had to sit in the car for five minutes. But by "
            "Friday it was manageable. The parents' group from George Street has a "
            "messaging group and I received several check-in messages that first week. "
            "A community built around antenatal care that extends into early parenthood "
            "is something I had not expected and am deeply grateful for."
        ),
        "Month 11 — August (Six-Month Maternal Health Review)": (
            "My six-month maternal health review was conducted at the George Street "
            "centre. The midwife who reviewed me had access to my complete care "
            "record and was fully briefed. The continuity of documentation rather "
            "than relying on continuity of person is good system design. My physical "
            "recovery is complete, my mental health is good, and I feel adequately "
            "supported as a working parent with a young infant."
        ),
        "Month 12 — September (One Year Journey — From Booking to Full Recovery)": (
            "One year ago I sat in the booking appointment at ten weeks gestation "
            "with a folder of information and a midwife who remembered my history. "
            "The year has taken me through twenty-eight weeks of antenatal care, "
            "a positive birth experience with Lisa present, six months of postnatal "
            "support, and a return to work with a healthy son and a strong support "
            "network. The midwifery team at George Street and the antenatal classes "
            "that prepared me for this transition deserve recognition as the foundation "
            "of a year I will always remember well."
        ),
    '''),

    # ── Patient Z — Postnatal Working Parent (Bright Horizons, Patricia Nakamura) ──
    (
        'Good care spreads by word of mouth."\n        ),\n    },',
        '''\
        "Month 6 — July (Late Slots Confirmed Permanent)": (
            "The clinic has formally announced that the 4:30pm Tuesday and Thursday "
            "appointment slots are a permanent addition to the schedule following the "
            "successful trial. I booked my next three appointments in the late slots "
            "immediately. Patricia Nakamura is now twenty weeks pregnant and the "
            "midwifery team have exceeded her already-elevated expectations. She "
            "called me last week to say she understood now exactly what I had told "
            "her about the quality of care. Referrals from satisfied patients create "
            "the feedback loop that sustains good services."
        ),
        "Month 7 — August (Returning to Full-Time Work)": (
            "I increased my hours at Bright Horizons Childcare to full-time this "
            "month after discussing the transition with my GP at my postnatal check. "
            "The clinic's flexible appointment times have meant I have not missed a "
            "single attendance since April. My GP noted that sustained healthcare "
            "engagement in the first twelve postnatal months is strongly associated "
            "with better long-term maternal mental health outcomes — something I "
            "would not have achieved without the evening appointment option."
        ),
        "Month 8 — September (Patricia Nakamura's Third Trimester)": (
            "Patricia Nakamura is in her third trimester and called me after her "
            "28-week appointment to describe her birth plan discussion with Jenny "
            "— the same midwife who had supported me. I was moved to hear my own "
            "experience described back to me through someone else's eyes. The quality "
            "of care I recommended to Patricia has been consistently delivered. "
            "I feel a particular responsibility for the trust she placed in my "
            "referral — and it has been fully vindicated."
        ),
        "Month 9 — October (Nine-Month Postnatal Check)": (
            "My nine-month postnatal check included a comprehensive wellbeing "
            "assessment. My scores on all domains — sleep, mood, social support, "
            "physical recovery — were in the healthy range. The midwife noted that "
            "patients who engage consistently with postnatal care have significantly "
            "better outcomes on these measures. The late appointment slots that "
            "enabled my consistent attendance were the structural enabler of that "
            "outcome. Patient feedback about practical barriers produces systemic "
            "changes that improve measurable health results."
        ),
        "Month 10 — November (Patricia Has Her Baby)": (
            "Patricia Nakamura gave birth to a healthy daughter this month. She "
            "messaged me from the postnatal ward to say Lisa had been on shift — "
            "the same midwife who attended my birth. I was unexpectedly emotional "
            "reading that message. The quality of care I had experienced and "
            "recommended had been delivered again, to someone I had sent with trust. "
            "Good clinical care compounds: one positive referral becomes two families "
            "who received excellent support."
        ),
        "Month 11 — December (Approaching Discharge from Postnatal Care)": (
            "My postnatal care is approaching the twelve-month discharge point. "
            "The clinic has arranged a brief final review for January. Patricia "
            "Nakamura is settling into new parenthood with the same support network "
            "I found after my birth — the parents' group, the flexible appointments, "
            "the consistent team. I am glad I raised the scheduling concern rather "
            "than simply tolerating it. The extended hours were not just for me — "
            "they were for every working parent who came after."
        ),
        "Month 12 — January (Discharged from Postnatal Care)": (
            "I was formally discharged from postnatal care today with a "
            "comprehensive wellbeing summary shared with my GP. My son is eleven "
            "months old, thriving, and starting to walk. I have fully returned to "
            "work at Bright Horizons Childcare and the logistics of managing two "
            "children alongside full-time employment has settled into a manageable "
            "rhythm. The clinic that advocated for working parents by introducing "
            "evening appointments has played a real role in this outcome. Patricia "
            "Nakamura and I have plans to attend the parents' group together "
            "next week."
        ),
    '''),

    # ── Patient AA — Haematology (Daniel Kim, Royal Brisbane Women's Hospital) ──
    (
        'and manner have removed one significant barrier to my healthcare engagement."\n        ),\n    },',
        '''\
        "Month 6 — July (Iron Treatment Progressing)": (
            "My iron supplementation has continued for three months and my ferritin "
            "levels are climbing steadily. My fatigue — the symptom that prompted "
            "my original GP referral — has continued to improve and I now complete "
            "a full work day without the mid-afternoon exhaustion that had become "
            "normalised. I attended for a follow-up blood draw this month and was "
            "relieved to find Daniel Kim available. His consistent approach means "
            "I can now attend blood collection without the anticipatory anxiety that "
            "previously disrupted my routine for days beforehand."
        ),
        "Month 7 — August (Hiatal Hernia Treatment Completed)": (
            "The hiatal hernia identified by gastroscopy in June has been treated "
            "endoscopically. The procedure was straightforward and the gastroenterologist "
            "confirmed no ongoing bleeding source. My haematologist anticipates that "
            "iron absorption will improve without the ongoing occult loss. Daniel Kim "
            "collected my pre-procedure and post-procedure bloods — the consistency "
            "of having the same skilled nurse for every draw has made each collection "
            "progressively less distressing."
        ),
        "Month 8 — September (Iron Levels Rising)": (
            "My haemoglobin is now within the normal range for the first time since "
            "my original GP referral. My ferritin is still below target but trending "
            "correctly. The haematologist is cautiously satisfied and has extended "
            "reviews to six-weekly. I have had four blood draws since February — all "
            "with Daniel Kim — and the last three were managed without the pre-draw "
            "anxiety that had made me walk out of collection centres in the past. "
            "Both the clinical and patient experience outcomes are tracking positively."
        ),
        "Month 9 — October (Haematology Discharge Planning)": (
            "My haematologist has indicated that discharge from specialist monitoring "
            "is likely at the next review if iron levels reach target. The prospect "
            "of returning to GP-only management no longer feels like abandonment — "
            "I have been given clear criteria for when to seek re-referral and a "
            "written summary of my iron deficiency history, its cause, and its "
            "resolution. I intend to request Daniel Kim by name for any future blood "
            "collections regardless of the referring team."
        ),
        "Month 10 — November (Iron Levels Normal — Discharged from Haematology)": (
            "My haematology review confirmed ferritin and haemoglobin are both "
            "within normal range. I have been formally discharged from specialist "
            "monitoring with a safety-net plan: annual iron studies via my GP, and "
            "a low-threshold re-referral criterion if fatigue or bruising recurs. "
            "The journey from needle-phobic patient who walked out of collection "
            "centres to someone who attends blood draws routinely has been driven "
            "almost entirely by one skilled nurse whose approach removed the barrier "
            "rather than working around it."
        ),
        "Month 11 — December (GP Follow-up — Year's Progress)": (
            "My GP reviewed my haematology discharge summary and updated my health "
            "record with the resolved iron deficiency diagnosis and the hiatal hernia "
            "treatment. She noted that the improvement in my healthcare engagement "
            "— specifically my willingness to attend blood collections — had been "
            "mentioned in the discharge letter. My GP said the right clinician at "
            "the right moment can change a patient's relationship with the health "
            "system in ways that last well beyond the specific episode."
        ),
        "Month 12 — January (One Year On — The Impact of One Skilled Nurse)": (
            "One year ago I attended a blood collection with significant apprehension, "
            "having walked out of two previous collection centres. Daniel Kim at the "
            "Royal Brisbane and Women's Hospital collected my bloods, explained every "
            "step, and used a butterfly needle without being asked. That single "
            "clinical interaction changed the trajectory of my healthcare engagement. "
            "I am now in normal haematological health, my hiatal hernia has been "
            "treated, and I attend blood collection appointments without distress. "
            "The skill of one nurse made all of it possible."
        ),
    '''),

    # ── Patient AB — Endocrinology (Dr Richardson, 07 3456 7891) ─────────────
    (
        'substantially since February."\n        ),\n    },',
        '''\
        "Month 6 — June (Twelve-Month Monitoring Plan Confirmed)": (
            "My endocrinology review confirmed the surveillance ultrasound at twelve "
            "months is scheduled and results will be communicated by phone before "
            "portal upload. I used the patient portal to send a query about the "
            "timing and received a response within two business days — a function "
            "I now use comfortably after the initial difficulties in February. "
            "The nurse who called after my May ultrasound used exactly the same "
            "format as the first call. Consistent execution of the new protocol matters."
        ),
        "Month 7 — July (Stable Between Reviews)": (
            "I have had no symptoms attributable to the thyroid nodule and my thyroid "
            "function tests — repeated by my GP as interim monitoring — are within "
            "normal limits. The twelve-month surveillance ultrasound approaches in "
            "September. I feel significantly less anxious about this investigation "
            "than I did about the original biopsy, largely because I trust the "
            "communication process that will follow. Knowing the result will be "
            "explained by phone before being uploaded has removed the primary source "
            "of my previous distress."
        ),
        "Month 8 — August (Preparing for Twelve-Month Scan)": (
            "I received my twelve-month surveillance ultrasound appointment letter "
            "this month. It included a clear explanation of the follow-up call "
            "process — a patient information insert clearly developed in response "
            "to feedback like mine. I called Dr Richardson's office at 07 3456 7891 "
            "to confirm the appointment and was answered within two rings. The phone "
            "reliability that concerned me in February has genuinely improved. "
            "I am approaching the scan with measured calm rather than acute anxiety."
        ),
        "Month 9 — September (Twelve-Month Surveillance Ultrasound)": (
            "I attended the twelve-month surveillance ultrasound. The radiographer "
            "was efficient and professional and I was in and out within thirty minutes. "
            "A nurse from Dr Richardson's office called me the following afternoon "
            "to report the preliminary result before it appeared on the portal — "
            "exactly as the protocol requires. Preliminary result: stable, no change "
            "from baseline. The call removed all anxiety from what had previously "
            "been a distressing wait for an uninterpreted online report."
        ),
        "Month 10 — October (Scan Results — No Change Confirmed)": (
            "Dr Richardson's office called to confirm the final ultrasound report: "
            "thyroid nodule unchanged from baseline at twelve months, benign "
            "surveillance criteria fully met. The report was uploaded to the portal "
            "after the call. I accessed the portal to view the document with context "
            "already provided — a completely different experience from February. "
            "Dr Richardson has extended surveillance to two-yearly intervals, "
            "reflecting the very low-risk nature of the finding."
        ),
        "Month 11 — November (Two-Year Monitoring Plan Established)": (
            "My endocrinology care is moving to a low-intensity two-yearly "
            "surveillance cycle. A care plan document has been sent to my GP "
            "outlining the monitoring schedule and criteria for earlier review. "
            "The journey from anxious patient who couldn't interpret a benign "
            "online report to someone who uses the portal comfortably and attends "
            "surveillance investigations without distress has been enabled by two "
            "things: a responsive clinic and a new protocol. My February feedback "
            "produced both."
        ),
        "Month 12 — December (Year's Progress — System Improved)": (
            "Twelve months ago I was calling Dr Richardson's office at 07 3456 7891 "
            "from anxiety after reading an unexplained biopsy result online. Today "
            "the clinic has a formal protocol ensuring every biopsy result is "
            "communicated by phone first, portal access is straightforward and "
            "supported, and the phone line is reliably answered. My thyroid "
            "surveillance is scheduled for two years hence. Patient feedback about "
            "a poor experience produced a system improvement that will benefit every "
            "patient who follows me."
        ),
    '''),

    # ── Patient AC — Gynaecology (Dr Patel, Nurse Rebecca, female practitioner) ──
    (
        'I feel genuinely well looked after."\n        ),\n    },',
        '''\
        "Month 7 — July (Six-Month Smear Scheduled)": (
            "My six-month follow-up smear is scheduled for August, as planned at "
            "my LLETZ discharge in June. I received the appointment letter confirming "
            "the appointment will be with a female practitioner — the note was "
            "included automatically, as my clinical record now permanently flags this "
            "requirement. That systematic documentation of my cultural need means "
            "I do not have to re-state or re-argue my request at every appointment. "
            "It is respected as a standing clinical instruction."
        ),
        "Month 8 — August (Six-Month Smear — Clear Result)": (
            "Dr Patel called me personally with the result of my six-month follow-up "
            "smear before the written report was posted — the same approach she has "
            "used for every significant result in my care. Result: clear. No residual "
            "CIN cells detected. The call was brief but warm and included the next "
            "steps: twelve-month smear in February, then return to routine three-yearly "
            "screening. Nurse Rebecca sent a brief portal message to say she was glad. "
            "These small gestures of genuine connection distinguish this clinic."
        ),
        "Month 9 — September (Community Impact — Wider Reach)": (
            "Two women in my community who attended gynaecological care at this clinic "
            "following my recommendation have described positive experiences with "
            "female practitioners and the respectful clinical environment. One had "
            "been avoiding cervical screening for six years due to previous experiences "
            "that had not accommodated her cultural needs. Her abnormal screening "
            "result — identified only because she finally attended — has been "
            "managed and resolved. Good care, when shared, reaches beyond the "
            "individual patient."
        ),
        "Month 10 — October (Continued Monitoring & Women's Health Education)": (
            "I remain symptom-free at four months post-LLETZ and my next formal "
            "review is the twelve-month smear in February. I attended the clinic's "
            "women's health information session this month — a new program open to "
            "all patients. The session covered HPV vaccination for daughters and "
            "family members, which I had not previously discussed with my GP. "
            "Dr Patel's team extends education beyond the direct clinical encounter "
            "in ways that respect the breadth of women's health needs."
        ),
        "Month 11 — November (Twelve-Month Approach — Prepared)": (
            "My twelve-month follow-up smear is approaching in February. I feel "
            "calm about this investigation in a way I would not have anticipated "
            "twelve months ago when my CIN 2 diagnosis first registered. The "
            "systematic way this clinic handled my cultural requirements, communicated "
            "results, and followed up care has built a foundation of trust that "
            "approaches clinical investigations as manageable rather than threatening. "
            "I have encouraged my daughters to be consistent with their own "
            "cervical screening."
        ),
        "Month 12 — December (Pathway Clear — A Year of Respectful Care)": (
            "My gynaecology care is approaching its planned conclusion: one more "
            "twelve-month smear in February, and if clear, return to routine GP-led "
            "screening. The clinical pathway is well-documented, including the "
            "permanent flag for female practitioners at all future examinations. "
            "Dr Patel noted in my last appointment that my case had been used as an "
            "example in a cultural safety training session for new staff. My "
            "experience — and the care that met it — is now part of how this clinic "
            "trains its people. That is a meaningful legacy."
        ),
    '''),

    # ── Patient AD — Geriatrics (Zahra Al-Rashid, PAT-91603, fatima.alrashid@outlook.com) ──
    (
        'age — but the response from the clinic has been thorough and genuine."\n        ),\n    },',
        '''\
        "Month 7 — August (Three-Month Cognitive Review)": (
            "My mother Zahra Al-Rashid (PAT-91603) attended her three-month cognitive "
            "review with a telephone Arabic interpreter booked in advance — confirmed "
            "48 hours prior as the new protocol requires. The geriatrician noted that "
            "her cognitive scores are stable: no acceleration of the mild impairment "
            "identified in April. Her engagement with the Arabic-speaking community "
            "support program has been identified as a protective factor. All "
            "correspondence continues to be sent to fatima.alrashid@outlook.com "
            "as agreed."
        ),
        "Month 8 — September (Community Program Engagement Deepening)": (
            "My mother has become a regular participant in the Arabic-speaking "
            "community support group and has developed several genuine social "
            "connections for the first time since arriving in Australia. Her GP "
            "has noted improved affect and reduced social isolation in the most "
            "recent assessment. The occupational therapist completed a home safety "
            "review and recommended two modifications — a grab rail in the bathroom "
            "and better lighting near the staircase — both of which have been "
            "installed. The holistic care approach has exceeded our expectations."
        ),
        "Month 9 — October (GP Coordination — Integrated Care)": (
            "My mother's GP has been fully briefed on the geriatrics care plan and "
            "is now the primary coordinator of her routine care, with the geriatrician "
            "maintaining six-monthly specialist oversight. The Arabic-speaking "
            "community worker identified by the clinic's social worker now accompanies "
            "my mother to GP appointments, providing both language support and social "
            "continuity. All letters are directed to fatima.alrashid@outlook.com. "
            "The system that initially failed my mother has been rebuilt around her "
            "actual needs."
        ),
        "Month 10 — November (Family Meeting — Planning Ahead)": (
            "Our family had difficult conversations this month about planning for "
            "increasing care needs over the coming years. The clinic's social worker "
            "facilitated a family meeting with an Arabic interpreter — my siblings and "
            "I, along with my mother, discussed the future openly. The geriatrician "
            "attended briefly to answer medical questions. Having a structured, "
            "culturally appropriate forum for these conversations removed the avoidance "
            "that had previously surrounded them. My mother felt heard and included "
            "rather than discussed about."
        ),
        "Month 11 — December (Holiday Safety Planning)": (
            "My mother will spend the Christmas period at my home. The occupational "
            "therapist provided guidance on managing in an unfamiliar environment "
            "— a brief assessment of my home and a written safety plan for the visit. "
            "The cognitive support worker called my mother at home to remind her of "
            "the visit plan and check her understanding, using Arabic. We received "
            "the visit plan at fatima.alrashid@outlook.com in both English and Arabic "
            "— a first. The Arabic document was produced on request and demonstrated "
            "genuine commitment to accessible communication."
        ),
        "Month 12 — January (Six-Month Cognitive Review — Stable)": (
            "My mother Zahra Al-Rashid (PAT-91603) attended her six-month cognitive "
            "review this month. The Arabic interpreter was booked ten days in advance "
            "— the booking confirmation was sent to fatima.alrashid@outlook.com as "
            "standard. The geriatrician's assessment found no significant change in "
            "cognitive function over the six-month period — a stable outcome in mild "
            "cognitive impairment, which represents the best plausible result at this "
            "stage. Ten months ago the interpreter failure set back her diagnosis by "
            "a month. Today the system that failed her has been rebuilt, and she is "
            "stable and well-supported."
        ),
    '''),

    # ── Patient AE — Mental Health FIFO (Dr Amanda Clarke, BHP, Mount Isa) ────
    (
        'care is not a luxury; for FIFO workers it is an occupational health imperative."\n        ),\n    },',
        '''\
        "Month 7 — March 2026 (Fortnightly Maintenance Sessions Continue)": (
            "My fortnightly telehealth sessions with Dr Clarke continue as a "
            "maintenance phase. The themes in our sessions have shifted from crisis "
            "management to longer-term resilience and career planning — a meaningful "
            "change in register that reflects genuine progress. I returned to my full "
            "FIFO roster at BHP Mitsubishi Alliance in Mount Isa with no modified "
            "duties requirement. The workplace psychological safety review I contributed "
            "to in September has produced several structural changes in how the site "
            "manages critical incidents."
        ),
        "Month 8 — April 2026 (FIFO Wellbeing Program — Participant)": (
            "BHP Mitsubishi Alliance has launched a structured wellbeing program for "
            "FIFO workers in Mount Isa, and I was invited to share my experience "
            "— anonymously — as a case study in the opening session. Dr Clarke and "
            "I discussed this opportunity in telehealth and she encouraged me to "
            "participate if it felt right. I agreed. Being able to contribute "
            "something to other workers facing similar challenges from my own "
            "experience felt like a natural extension of my recovery — from patient "
            "to participant in something larger."
        ),
        "Month 9 — May 2026 (Monthly Sessions — Gradual Reduction)": (
            "Dr Clarke and I have agreed to transition from fortnightly to monthly "
            "telehealth sessions. The decision felt natural and was mutually "
            "determined. I have the coping tools, the employer support, and the "
            "insight to manage independently between monthly contacts. Dr Clarke "
            "noted that my case represents a complete therapeutic arc from acute "
            "workplace incident to sustained recovery and community contribution. "
            "The telehealth model made this arc possible for someone working remotely."
        ),
        "Month 10 — June 2026 (Workplace Safety Culture — Sustained Change)": (
            "The workplace safety protocols introduced at BHP Mitsubishi Alliance "
            "following the original incident have now been in place for six months. "
            "I have observed the difference they make in the day-to-day handling "
            "of critical incidents and difficult conversations. A colleague "
            "experiencing his own mental health challenge approached me after "
            "recognising the wellbeing program participation — I directed him to "
            "the EAP and to Dr Clarke's practice. Peer support emerging from "
            "recovery is one of the most valuable outcomes of this journey."
        ),
        "Month 11 — July 2026 (Planning Formal Discharge)": (
            "Dr Clarke and I have begun planning my formal discharge from structured "
            "psychological support. She has prepared a relapse prevention plan "
            "tailored to the FIFO work environment, identifying the specific stressors "
            "that most challenged me and the strategies that have been most effective. "
            "I have a clear re-engagement pathway: if symptoms recur I contact "
            "Dr Clarke directly and she will offer a same-week telehealth session. "
            "The safety net is there without requiring active ongoing treatment."
        ),
        "Month 12 — August 2026 (Discharged — Stable & Resilient)": (
            "Dr Clarke formally discharged me from structured psychological support "
            "this month, eleven months after the September incident at BHP Mitsubishi "
            "Alliance in Mount Isa. The discharge summary notes full return to "
            "pre-incident functioning, active participation in workplace wellbeing "
            "initiatives, and peer support contribution to one colleague. Dr Clarke "
            "described my recovery as one of her most complete FIFO telehealth cases. "
            "The flexibility of telehealth enabled the continuity that made this "
            "outcome possible. I carry the tools she gave me into every shift."
        ),
    '''),

    # ── Patient AF — Mental Health Wait (referral 15 Nov 2025, first appt 8 Jan 2026) ──
    (
        'before the crisis deepens. The wait time is a patient safety issue."\n        ),\n    },',
        '''\
        "Month 7 — May 2026 (Monthly Sessions — Progress Sustained)": (
            "I have been attending monthly psychological sessions since my review "
            "in April confirmed I no longer require fortnightly contact. My functioning "
            "at work and at home has been sustained at the improved level since March. "
            "The psychologist commented that my recovery is more complete than many "
            "who present with similar severity — she attributes this partly to my "
            "own determination during the wait period and partly to the structured "
            "CBT work we completed together. I have submitted a second follow-up to "
            "the service director about the wait time review."
        ),
        "Month 8 — June 2026 (Service Review Response Received)": (
            "The mental health service director responded formally to my written "
            "feedback. The service is implementing a two-week maximum wait target "
            "for new GP referrals assessed as moderate severity, with a welfare "
            "check protocol for all patients waiting beyond three weeks. My "
            "feedback, along with twelve others, contributed to the evidence base "
            "for this policy change. Knowing that the eight weeks I waited will "
            "not be repeated for patients after me is the outcome I most wanted "
            "from submitting that feedback."
        ),
        "Month 9 — July 2026 (Summer Wellbeing — Managing Well)": (
            "The social engagement and structured activity recommended as protective "
            "factors through summer have been maintained. I am swimming three times "
            "per week, attending a book group, and managing work and family "
            "responsibilities without the signs of overwhelm that characterised "
            "last November. The contrast between this July and last November's "
            "referral moment is profound. Good mental health care, when accessed "
            "in time, does not just resolve the episode — it equips the person "
            "for what follows."
        ),
        "Month 10 — August 2026 (Service Review — Changes Implemented)": (
            "I received a letter from the mental health service confirming the new "
            "wait time policies are now in effect. The letter acknowledged patient "
            "feedback as the primary driver and described the two-week maximum "
            "target as a commitment rather than an aspiration. I shared this update "
            "with my GP, who had supported me with weekly check-in calls during "
            "the original wait. She was pleased and asked whether she could share "
            "my experience — anonymised — with other patients she was about to "
            "refer to the service."
        ),
        "Month 11 — September 2026 (Planning Discharge)": (
            "My psychologist and I have agreed on a discharge plan for October. "
            "The plan includes a written summary of the CBT techniques most "
            "effective for me, a relapse recognition checklist, and clear guidance "
            "on when to seek re-referral. My GP will provide monthly check-ins for "
            "three months post-discharge as a safety net. I feel ready. Ten months "
            "ago I was referred while unwell and waited eight weeks in increasing "
            "distress. Today I am choosing to conclude treatment from a position "
            "of stability."
        ),
        "Month 12 — October 2026 (Discharged — System Changed)": (
            "I was formally discharged from psychological treatment today, eleven "
            "months after my first appointment on 8 January 2026. My psychologist "
            "noted in the discharge letter that I had contributed meaningfully to "
            "a systemic improvement that would benefit future patients. The two-week "
            "wait target is in place. The welfare check protocol for waiting patients "
            "exists. And I am well — fully functioning, maintaining the gains from "
            "treatment, and clear about the support available if I need it again. "
            "Fifteen November 2025 to today: from referral in crisis to discharge "
            "with a changed system."
        ),
    '''),

    # ── Patient AG — Wound Care (nurse Jacinta) ───────────────────────────────
    (
        'equal measure. Jacinta has both."\n        ),\n    },',
        '''\
        "Month 6 — June (Post-Discharge Scar Management)": (
            "Jacinta's discharge letter to my GP included guidance on scar management "
            "during the remodelling phase — silicone gel and sun protection for the "
            "site. My GP implemented these recommendations at my follow-up and noted "
            "that the wound care documentation from Jacinta was unusually comprehensive. "
            "The scar is fading as expected. I have referred a neighbour to the wound "
            "clinic following her own surgical discharge — specifically mentioning "
            "Jacinta by name. Good clinical reputation spreads through patient "
            "experience."
        ),
        "Month 7 — July (GP Follow-up — Complete Healing Confirmed)": (
            "My GP completed a full assessment of the surgical wound site and "
            "confirmed complete healing with no concerns. She reviewed Jacinta's "
            "discharge summary and noted the twelve-year experience was evident "
            "in the quality of documentation and the staged patient education approach. "
            "The scar has reduced significantly in visibility over the past two months "
            "with the recommended treatment. I had not expected the recovery to be "
            "this complete at six months post-surgery."
        ),
        "Month 8 — August (Patient Experience Session)": (
            "The wound clinic contacted me to ask whether I would be willing to "
            "attend a patient experience session for new surgical patients preparing "
            "for discharge. I agreed. I described my initial anxiety about managing "
            "the wound at home, the confidence the written instructions gave me, "
            "and the way Jacinta's visual progress photographs had been motivating "
            "rather than distressing. Sharing that experience for the benefit of "
            "new patients felt like the right use of what I had been through."
        ),
        "Month 9 — September (Scar Continuing to Fade)": (
            "The scar is now significantly less visible than in May — the silicone "
            "gel and sun protection protocol recommended by Jacinta has been effective. "
            "My GP commented that the final cosmetic outcome is likely to be better "
            "than initial expectations for an abdominal wound of this size. Returning "
            "to my previous activities — including swimming in September — without "
            "self-consciousness about the scar is a quality of life marker that "
            "matters considerably."
        ),
        "Month 10 — October (Return to All Activities)": (
            "I have returned to all the physical activities I engaged in before my "
            "January surgery — swimming, bushwalking, and the community garden where "
            "I volunteer. The abdominal wound site is strong and the scar no longer "
            "limits any movement or causes discomfort. Ten months post-surgery the "
            "recovery is functionally complete. Jacinta's twelve years of wound care "
            "expertise, expressed through skilled technique and patient communication, "
            "produced an outcome I am genuinely grateful for."
        ),
        "Month 11 — November (Long-term Recovery — Year Approaching)": (
            "As the one-year anniversary of my surgery approaches, I reflect on the "
            "complete arc of recovery. From the January surgery and uncertain home "
            "management to May discharge and confident independence to October full "
            "return to all activities. The wound clinic — specifically Jacinta — "
            "was the clinical bridge between the surgical outcome and the functional "
            "recovery. Patient experience feedback submitted to the clinic manager "
            "highlighted Jacinta's approach by name. Recognition within an institution "
            "matters as much as patient gratitude."
        ),
        "Month 12 — December (One Year Since Surgery — Full Recovery)": (
            "One year since my abdominal surgery on 12 January 2026. My wound is "
            "fully healed, the scar is fading, and I am physically active in all "
            "the ways that matter to me. The discharge nurse's instructions, the "
            "wound clinic referral, and Jacinta's twelve years of skill delivered "
            "through three months of careful wound management have produced this "
            "outcome. I attended the patient experience session for new surgical "
            "patients again this month — my second time sharing. The right knowledge "
            "at the right time changes how recovery feels from the inside."
        ),
    '''),

    # ── Patient AH — Post-Surgical (David Tran, Logan Hospital 2 March 2026, 0437 123 456) ──
    (
        'the next platform update. Persistence does produce change."\n        ),\n    },',
        '''\
        "Month 7 — September 2026 (Full Return to Work)": (
            "I returned to work full-time this month, six months after my surgery at "
            "Logan Hospital on 2 March 2026. My energy levels and stamina are fully "
            "restored and I have had no post-surgical complications. David has been "
            "my constant support throughout recovery and attended every significant "
            "review appointment with me. The medication reconciliation error identified "
            "at transfer in March, which David helped flag with the ward nurse, has "
            "not recurred and my medication list has been accurate in every subsequent "
            "clinical encounter."
        ),
        "Month 8 — October 2026 (Pharmacist Checklist — Pilot Results)": (
            "The patient safety team contacted me with an update on the pharmacist-led "
            "transfer checklist piloted at Logan Hospital and this facility. Preliminary "
            "results show a forty percent reduction in medication discrepancies at "
            "inter-hospital transfers in the first three months. The lead clinician "
            "specifically thanked David and me for the clarity of our account in "
            "the review. A systemic change producing measurable harm reduction from "
            "a single patient's experience — that is the best outcome I could have "
            "hoped for from speaking up."
        ),
        "Month 9 — November 2026 (Six-Month Surgical Review)": (
            "My six-month post-surgical review confirmed complete recovery with no "
            "late complications. The surgical team reviewed the imaging from March "
            "and my current scans and confirmed the operative site is fully healed "
            "and normal. I raised the Zedoc SMS issue again — my third formal report "
            "— and was told the vendor update was being tested and would be deployed "
            "within the month. The clinical outcome has been excellent; the technical "
            "issue has been persistent. Both deserve continued attention."
        ),
        "Month 10 — December 2026 (Zedoc SMS Issue Finally Fixed)": (
            "The patient experience team contacted me to confirm that the Zedoc SMS "
            "sender identity has been updated — the clinic name now appears correctly "
            "on all survey invitations. David and I tested this by completing the "
            "December survey through my Samsung phone for the first time. It worked. "
            "The clinic name displayed correctly and the link opened without issue. "
            "Three formal reports over nine months produced a technical fix that will "
            "prevent other patients from dismissing legitimate survey requests as "
            "spam. Persistence does produce change."
        ),
        "Month 11 — January 2027 (Annual Health Check — Surgical Baseline)": (
            "My GP completed a comprehensive annual health check including a "
            "post-surgical baseline assessment. All results within normal limits. "
            "My GP reviewed the pharmacist checklist implementation letter I had "
            "shared with her and noted it in my health summary as a patient safety "
            "contribution. David and I have moved through the year since my March "
            "2026 surgery with the clarity that comes from having faced a genuine "
            "medication risk and resolved it. The health system is safer for our "
            "having been engaged patients."
        ),
        "Month 12 — February 2027 (One Year Since Surgery — Perspective)": (
            "One year since my surgery at Logan Hospital on 2 March 2026 — "
            "approximately. I am fully recovered, fully working, and fully engaged "
            "with the improvements that emerged from my care experience. The "
            "medication error at transfer resolved through David's vigilance and the "
            "ward nurse's responsiveness. The pharmacist checklist now reducing harm "
            "at two hospitals. The Zedoc SMS fix ensuring survey invitations reach "
            "every patient. And the Zedoc link on Samsung phones, finally working "
            "ten months after my first report. David says I am difficult to deter. "
            "He is right."
        ),
    '''),

    # ── Patient AI — Cardiology (Dr Richardson, 0478 234 567) ────────────────
    (
        'skill is rare and deserves recognition."\n        ),\n    },',
        '''\
        "Month 7 — July (Six-Month Stent Review)": (
            "My six-month post-stent review confirmed the stent is fully patent and "
            "my left ventricular function remains normal. Dr Richardson called at "
            "0478 234 567 before sending the written summary — his consistent approach "
            "throughout my care. He described the six-month result as 'textbook' and "
            "indicated my exercise tolerance has exceeded the median recovery for "
            "single-vessel PCI. Cardiac rehabilitation has been completed and my "
            "morning walks are now forty-five minutes without symptoms."
        ),
        "Month 8 — August (Extended Exercise Capacity)": (
            "I have progressed from thirty-minute daily walks to forty-five minutes, "
            "and this month attempted a sixty-minute walk that I completed without "
            "cardiac symptoms or unusual fatigue. The contrast with the exertional "
            "chest discomfort that prompted my January referral is striking. My wife "
            "has joined me for the Saturday walks, adding a social dimension to what "
            "began as a clinical obligation. Dr Richardson's personal communication "
            "approach has made the entire care episode feel managed rather than "
            "experienced passively."
        ),
        "Month 9 — September (Medication Review — One Step Reduction)": (
            "Dr Richardson reviewed my medication regime and reduced the beta-blocker "
            "dose — a step reflecting confidence in my cardiac recovery. He called "
            "at 0478 234 567 two days after the change to check whether I had noticed "
            "any symptoms associated with the adjustment. None were observed. That "
            "third proactive personal call — following the calls after my stress test "
            "and post-PCI discharge — confirms this is his consistent practice rather "
            "than a one-off response to complexity."
        ),
        "Month 10 — October (Annual Cardiac Assessment Preparation)": (
            "My annual cardiac review is scheduled for November. I received the "
            "appointment letter with clear instructions about the pre-assessment "
            "requirements — fasting bloods, walking ECG, and echocardiogram scheduled "
            "on the same day to minimise attendance burden. The administrative "
            "coordination behind that single-day arrangement requires planning that "
            "I appreciate. My two colleagues I referred to this clinic earlier in "
            "the year have both commenced care and report the same quality of "
            "experience I described."
        ),
        "Month 11 — November (Annual Cardiac Review — Excellent Outcome)": (
            "My annual cardiac review confirmed the stent is fully patent, left "
            "ventricular function is normal, and my exercise tolerance is in the "
            "healthy range for my age group. Dr Richardson called at 0478 234 567 "
            "with the results before the written report — his fourth personal call "
            "in the course of my care. He described the outcome as 'as good as it "
            "gets' for single-vessel disease. The family history that caused me such "
            "anxiety in January — my father and his brother's cardiac events in their "
            "sixties — has not repeated in my case."
        ),
        "Month 12 — December (One Year — Prompt Diagnosis Changed Everything)": (
            "One year ago I had exertional chest discomfort during morning walks. "
            "Today I walk sixty minutes daily without symptoms, with a patent stent "
            "and normal cardiac function confirmed this month. The diagnostic timeline "
            "— stress test within two weeks of referral, catheterisation within a "
            "month, PCI completed by April — reflects a healthcare system working "
            "as it should. Dr Richardson's proactive communication at every decision "
            "point removed the uncertainty that makes cardiac care frightening. "
            "I referred this clinic and this doctor to two colleagues. Both would "
            "say the same."
        ),
    '''),

    # ── Patient AJ — Cardiac Rehab (Dr Andrew Walsh Prince Charles, Dr Richardson, 20 March 2026) ──
    (
        'communication I benefited from will all feature in the formal survey I submit today."\n        ),\n    },',
        '''\
        "Month 7 — August 2026 (Post-Rehabilitation Monitoring Begins)": (
            "The first month of post-rehabilitation monitoring has been straightforward. "
            "My exercise program continues independently following the structured "
            "rehabilitation template. Dr Richardson and Dr Andrew Walsh at the Prince "
            "Charles Hospital have agreed a shared monitoring schedule — Walsh for "
            "annual imaging and Richardson for ongoing medication and functional "
            "reviews. This role clarity prevents duplication and contradiction — a "
            "feature of their coordination I had not previously encountered in my "
            "cardiac care history."
        ),
        "Month 8 — September 2026 (Six-Minute Walk Test — Independent)": (
            "I completed an independent six-minute walk test using the protocol "
            "provided at rehabilitation discharge. My distance was 540 metres — up "
            "from 490 at my last rehabilitation assessment and well above the 320 "
            "metres I managed at baseline in February. I reported this to Dr "
            "Richardson's office and received a brief message confirming the result "
            "was excellent. Dr Walsh received the same update through the coordination "
            "letter. Both specialists acknowledged the progress without either "
            "needing to claim it exclusively."
        ),
        "Month 9 — October 2026 (Mobility Permit Downgraded)": (
            "The temporary mobility permit issued after my cardiac event has been "
            "formally downgraded to a standard parking permit following assessment "
            "of my improving functional capacity. This was a goal I had discussed "
            "with the rehabilitation physiotherapist in May — the permit downgrade "
            "as a marker of recovery rather than a loss of privilege. The four "
            "additional disabled bays installed near the clinic entrance following "
            "my March feedback remain available and consistently occupied. The "
            "parking improvement I raised has served other patients throughout "
            "this year."
        ),
        "Month 10 — November 2026 (Joint Specialist Review — Walsh & Richardson)": (
            "Dr Walsh at the Prince Charles Hospital and Dr Richardson conducted "
            "a joint telephone review of my case — the first time both specialists "
            "spoke directly with me simultaneously. The conversation was organised, "
            "unhurried, and covered both the cardiac imaging that Walsh had reviewed "
            "and the medication management that Richardson coordinates. Neither "
            "specialist deferred unnecessarily to the other and both contributed "
            "meaningfully. This is what coordinated care looks like from the patient's "
            "perspective: one coherent plan delivered by two specialists working as "
            "a genuine team."
        ),
        "Month 11 — December 2026 (Approaching One-Year Anniversary)": (
            "My cardiac event occurred in late January 2026. Nearly one year on, "
            "I am walking sixty minutes daily, my functional capacity has exceeded "
            "the rehabilitation targets, and the dual-specialist coordination between "
            "Dr Walsh at the Prince Charles Hospital and Dr Richardson at this clinic "
            "has remained seamless throughout. The parking feedback I submitted in "
            "March produced bays that other patients continue to use. I have shared "
            "my experience with two other cardiac rehabilitation patients this month "
            "— both are now attending and engaged."
        ),
        "Month 12 — January 2027 (One-Year Milestone — Recovery Completed)": (
            "One year since my cardiac event and discharge from the Prince Charles "
            "Hospital under Dr Andrew Walsh's care. I am fully recovered by every "
            "clinical and functional measure. Dr Richardson conducted my twelve-month "
            "review and Dr Walsh reviewed the echocardiogram results independently "
            "before they spoke together and called me. That final call — both "
            "specialists, one clear message — summarised twelve months of coordinated "
            "care that made my recovery as complete as it has been. The parking issue "
            "raised on 20 March 2026, the clinical excellence throughout, and the "
            "dual-specialist communication that defined my care: all documented, "
            "all recognised, all worth sharing."
        ),
    '''),
]


def apply_insertions(content: str, insertions: list) -> str:
    for anchor, new_months in insertions:
        if anchor not in content:
            print(f"WARNING: Anchor not found:\n  {anchor[:80]!r}")
            continue
        # Build replacement: replace the closing `\n    },` of the patient dict
        # with the new months followed by the closing `    },`
        # new_months ends with `        ),\n    ` (8-space close + newline + 4 spaces)
        # so appending `},` gives the correct `    },` (4-space indent)
        replacement = anchor.replace(
            "\n    },",
            "\n" + new_months + "},"
        )
        content = content.replace(anchor, replacement, 1)
        print(f"OK: Inserted months after: {anchor[:60]!r}")
    return content


with open(APP_PATH, "r", encoding="utf-8") as f:
    original = f.read()

updated = apply_insertions(original, INSERTIONS)

if updated == original:
    print("\nNO CHANGES MADE — check anchors above.")
else:
    with open(APP_PATH, "w", encoding="utf-8") as f:
        f.write(updated)
    print(f"\nDone. Updated {APP_PATH}")
    orig_count = original.count('"Month ')
    new_count = updated.count('"Month ')
    print(f"Month entries: {orig_count} → {new_count} (+{new_count - orig_count})")
