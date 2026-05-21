"""
Gradio web interface for NLP Sentiment Analysis.

Architecture:
  src/preprocessor.py  → NLP preprocessing pipeline
  src/analyzer.py      → Transformer model inference
  src/models.py        → type definitions & model config
  ui/app.py            → this Gradio UI
"""

import os
import re
import sys
import tempfile

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from wordcloud import WordCloud
import plotly.graph_objects as go
import gradio as gr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import ModelType, SUPPORTED_MODELS, MODEL_LABEL_TO_TYPE, PreprocessResult
from src.preprocessor import preprocess_text, read_file_path, get_ner_html
from src.analyzer import analyze_sentiment, get_word_distribution
from src.openmed_pii_client import redact_pii

# ── Sample texts ──────────────────────────────────────────────────────────────
# Each patient's monthly responses to: "How have you been feeling physically
# and emotionally over the past month?"
PATIENT_SAMPLES = {
    "Patient A — Oncology": {
        "Month 1 — January (Diagnosis)": (
            "I honestly don't know how to process any of this. When the doctor told me "
            "the diagnosis I just went numb. I haven't been sleeping, I can barely eat, "
            "and every little ache makes me panic that something worse is happening. "
            "I feel completely lost and terrified about what comes next. "
            "My family is trying to help but I don't even know what to ask of them."
        ),
        "Month 2 — February (Lowest Point)": (
            "This has been the hardest month of my life. The side effects from the first "
            "round of treatment left me exhausted and nauseous for weeks. I feel hopeless "
            "most days and I've started to wonder whether any of this is even worth it. "
            "I cried almost every day. I stopped calling friends because I don't have the "
            "energy to explain how bad things are. I just feel utterly alone."
        ),
        "Month 3 — March (Turning Point)": (
            "Things are still difficult but something shifted a little this month. "
            "The nausea is not as constant as before and I managed to take a short walk "
            "a few times, which felt huge. I'm still anxious about the next scan results "
            "but my care team has been very supportive and I am starting to trust the process. "
            "I wouldn't say I feel hopeful yet, but I feel slightly less hopeless."
        ),
        "Month 4 — April (Cautious Progress)": (
            "The latest results came back better than expected and I actually cried tears of "
            "relief for once instead of fear. I still have low-energy days and I get tired "
            "quickly, but I cooked a real meal last week and it felt like a small victory. "
            "I'm starting to reconnect with a couple of close friends. There is a long road "
            "ahead but for the first time I can imagine getting through this."
        ),
        "Month 5 — May (Growing Optimism)": (
            "I feel genuinely better this month — not just physically but mentally too. "
            "My appetite is mostly back and I slept a full night without waking up anxious "
            "several times this week. I went back to a gentle yoga class and it felt wonderful "
            "to move my body again. I'm still cautious and I don't want to jinx anything, "
            "but I have real hope now. My family noticed the difference and that means a lot."
        ),
        "Month 6 — June (Recovery & Gratitude)": (
            "I can barely believe how far I have come since January. My energy is nearly back "
            "to normal and I returned to part-time work this week, which felt incredibly good. "
            "The follow-up appointment went well and my doctor used the word 'remission' for "
            "the first time. I feel grateful, relieved, and genuinely excited about the future. "
            "This experience changed how I see everything. I intend to make the most of every day."
        ),
        "Month 7 — July (Surveillance Begins)": (
            "My first post-treatment surveillance scan came back clear and I cried with relief in "
            "the car park. I am back at work full-time now and my colleagues have been welcoming. "
            "The physical tiredness from treatment is fading but I notice I have less patience for "
            "things that used to not bother me. My therapist says that is normal. "
            "I am learning to listen to my body in ways I never did before."
        ),
        "Month 8 — August (Post-Treatment Fatigue)": (
            "I hit a wall this month — the post-treatment fatigue that comes when the adrenaline "
            "of active treatment finally wears off. I found myself unexpectedly tearful and exhausted "
            "even though my body is technically healing. My doctor reminded me that emotional recovery "
            "takes longer than physical recovery. I went back to yoga twice a week which helped. "
            "I am trying to give myself the same compassion I would give someone else in this situation."
        ),
        "Month 9 — September (A Scare)": (
            "I noticed some discomfort near my treatment site and convinced myself the worst. "
            "My care team arranged an urgent review and the imaging showed nothing concerning. "
            "The relief was enormous but so was the realisation that I will probably carry "
            "this vigilance for years. Talking to a friend who had been through something similar "
            "helped more than I expected. Fear is part of this journey too."
        ),
        "Month 10 — October (Finding New Normal)": (
            "I think I have started to find my new normal. I am working full-time, exercising "
            "regularly, and genuinely enjoying things again — not just enduring them. I joined a "
            "cancer survivor wellness program at the community centre and the connections I have "
            "made there are meaningful. My follow-up appointment is next month and I feel calm "
            "rather than terrified, which feels like real progress."
        ),
        "Month 11 — November (One-Year Scan)": (
            "My twelve-month surveillance scan came back clear and my oncologist used the phrase "
            "'excellent long-term outlook'. I sat with those words for a long time after the "
            "appointment. A year ago I was numb with shock in a doctor's office. Today I walked "
            "home through the park and felt genuinely, uncomplicated happy. "
            "I am going to plant a garden in December — something I promised myself I would do."
        ),
        "Month 12 — December (Year's End Reflection)": (
            "The garden is planted and I am sitting in it as I write this. This time last year "
            "I had just received my diagnosis and the word 'cancer' had swallowed everything. "
            "Today I feel grateful, strong, and genuinely excited about the year ahead. "
            "My care team has been extraordinary. If I can say one thing to anyone starting this "
            "journey: the fear does not last forever, and the good days do come back."
        ),
    },
    "Patient B — Post-Surgical Recovery": {
        "Month 1 — January (Post-Op)": (
            "The surgery is done but the pain is constant and I can barely move my leg. "
            "I rely on my partner for everything and it is deeply frustrating. "
            "I knew recovery would be hard but I did not expect to feel this helpless. "
            "The physical therapist starts next week and I am dreading it honestly. "
            "I just want to walk normally again without thinking about every single step."
        ),
        "Month 2 — February (Physical Therapy Begins)": (
            "PT is painful and exhausting but I can see why it is necessary. "
            "I managed to walk to the kitchen and back without crutches yesterday, "
            "which sounds small but felt huge. The swelling is slowly going down. "
            "Some days I push too hard and pay for it the next morning. "
            "I am frustrated with how slow this is but I am trying to stay consistent."
        ),
        "Month 3 — March (Mixed Progress)": (
            "Progress has been uneven this month. I had a good week then overdid it "
            "on a longer walk and set myself back by a few days. It is demoralizing. "
            "My PT says I am actually ahead of the typical schedule but it does not "
            "feel that way when I am icing my knee at midnight. I am sleeping better "
            "though and the medication dose has been reduced, which feels like a win."
        ),
        "Month 4 — April (Building Confidence)": (
            "I walked to the corner shop and back on my own for the first time today. "
            "It took twice as long as it used to and I was exhausted after, but I did it. "
            "The pain is now manageable with just over-the-counter relief most days. "
            "I am feeling more like myself again and less like a patient. "
            "My PT sessions are down to twice a week and I am doing home exercises daily."
        ),
        "Month 5 — May (Back to Light Activity)": (
            "I went for a thirty-minute walk in the park this week without stopping. "
            "Six months ago I would not have believed that was possible so soon. "
            "I am back to driving short distances and returned to my desk job part-time. "
            "There is still some stiffness in the morning but it eases within the hour. "
            "I feel proud of how hard I have worked and genuinely optimistic about full recovery."
        ),
        "Month 6 — June (Full Recovery)": (
            "My surgeon signed me off this week and said the joint looks excellent on imaging. "
            "I completed a gentle five-kilometre walk last weekend and felt strong throughout. "
            "The chronic pain that pushed me toward surgery in the first place is completely gone. "
            "I wish I had not waited so long before having the procedure. "
            "Life feels normal again — actually better than normal. I am so relieved and grateful."
        ),
        "Month 7 — July (Building Strength)": (
            "My surgeon signed me off in June but I am still working on strength and endurance. "
            "I have started swimming twice a week, which the physio recommended as low-impact "
            "conditioning. The joint feels stable and my walking distance increases every week. "
            "I have a small ache after longer walks but it resolves within an hour and I am told "
            "that is expected at this stage."
        ),
        "Month 8 — August (Active Again)": (
            "I completed a five-kilometre fun run last weekend — walking the whole way — and it "
            "was the best Saturday I have had in as long as I can remember. I had a medal around "
            "my neck and my partner at my side and I thought about where I was eight months ago "
            "when I could not get off the couch unassisted. "
            "I signed up for the same event next year with the goal of actually running it."
        ),
        "Month 9 — September (Occasional Setbacks)": (
            "I overdid it on a long bush walk this month and paid for it with two days of stiffness "
            "and aching. It was a good reminder that recovery continues past the six-month discharge. "
            "My old physio gave me a top-up session and reassured me the joint is fine — "
            "I just pushed too hard. I am learning to balance ambition with patience, which has been "
            "one of the unexpected lessons of this whole experience."
        ),
        "Month 10 — October (New Goals)": (
            "I signed up for a community walking group that meets every Saturday morning and it has "
            "become one of the highlights of my week. The social aspect has been as valuable as the "
            "physical benefit. My knee is consistently strong now and I rarely think about the surgery "
            "unless I am doing something specifically demanding. I have started telling other people "
            "considering the same procedure that the recovery is absolutely worth the difficulty."
        ),
        "Month 11 — November (Milestone Moment)": (
            "I jogged — actually jogged — for the first time since before the surgery. Only about "
            "two hundred metres before I slowed back to a walk, but it was real forward motion and "
            "it felt extraordinary. My partner filmed it and I watched the video back three times. "
            "My physio had told me this would come around the ten-month mark and they were right. "
            "I feel like myself again in a way I had begun to think might not be fully possible."
        ),
        "Month 12 — December (Year Closed with Strength)": (
            "I completed a ten-kilometre walk in the city charity event last weekend and finished "
            "feeling strong. Twelve months ago I was immobilised in a hospital bed. This year has "
            "required more patience and discipline than anything I have previously experienced, "
            "but the outcome has surpassed every expectation I had at the start. "
            "I am physically stronger than I was before the surgery."
        ),
    },
    "Patient C — Mental Health (Depression)": {
        "Month 1 — January (Initial Assessment)": (
            "I have not felt like myself in months. Getting out of bed is a struggle and "
            "I have been calling in sick to work more than I should. Everything feels grey "
            "and pointless. I finally saw a psychiatrist today and talking about it helped "
            "a little but I also felt ashamed that things got this bad. "
            "I do not know if the medication she prescribed will help. I am skeptical."
        ),
        "Month 2 — February (Medication Adjustment)": (
            "The first two weeks on the medication were rough — headaches, nausea, insomnia. "
            "I nearly stopped taking it but my psychiatrist said to push through. "
            "I do not feel better yet, just different-bad instead of same-bad. "
            "I started weekly therapy and I cried through most of the first session. "
            "At least I am doing something. That feels marginally better than nothing."
        ),
        "Month 3 — March (Early Signs of Improvement)": (
            "Something shifted this month, though I am almost afraid to say it out loud. "
            "I had a full week where I made it to work every day and even stayed late once. "
            "The heavy fog has not lifted entirely but there are moments of clarity now. "
            "My therapist introduced a CBT framework and I have been journaling, which helps. "
            "I still have bad days but the bad days feel survivable rather than endless."
        ),
        "Month 4 — April (Rebuilding Routines)": (
            "I have been exercising three times a week, which I have not done in over a year. "
            "My sleep is more regular and I am waking up without that immediate sense of dread. "
            "I reached out to two friends I had been avoiding and those conversations went well. "
            "I still have moments of low mood but I can usually identify the trigger now. "
            "My psychiatrist says the medication level looks right and we will hold here."
        ),
        "Month 5 — May (Sustained Improvement)": (
            "I went an entire month without a mental health sick day, which is a first since last year. "
            "My manager commented that I seem more engaged and present, which meant a great deal. "
            "I have been cooking again, seeing friends weekly, and even planning a short holiday. "
            "Therapy is less crisis-focused now — we are working on longer-term patterns. "
            "I feel like myself again. Not a perfect version, but genuinely, recognisably me."
        ),
        "Month 6 — June (Stable & Forward-Looking)": (
            "Six months ago I could not have imagined writing this. I am stable, functioning well, "
            "and genuinely looking forward to things again. I booked that holiday and I am excited. "
            "We have tapered the medication slightly and the transition has been smooth. "
            "Therapy continues monthly now as maintenance rather than intensive support. "
            "I am proud of the work I have done. This was the hardest and most important thing "
            "I have ever done for myself."
        ),
        "Month 7 — July (Holiday & Rest)": (
            "I took the holiday I had been planning since May and it was genuinely restorative. "
            "I was away for ten days and managed the trip without anxiety dominating the experience. "
            "There were two difficult evenings but I used the CBT tools my therapist taught me "
            "and they worked. Coming home felt good too, not just the trip itself. "
            "I feel stable in a way that feels real now, not fragile."
        ),
        "Month 8 — August (Therapy Tapering)": (
            "My psychiatrist and I agreed to taper therapy sessions to monthly rather than "
            "fortnightly. Six months ago that would have felt terrifying. Now it feels like a "
            "graduation. I am managing my mood tracking independently and have not had a significant "
            "low episode since April. I still have days when motivation is harder, but I have "
            "the tools to recognise and address them before they escalate."
        ),
        "Month 9 — September (Work Recognition)": (
            "I was asked to lead a project at work this month — the first time I have been given "
            "that kind of responsibility since before my illness. I accepted it and have been "
            "managing it well. A year ago I was calling in sick and avoiding my manager's calls. "
            "Today I presented to the executive team and received positive feedback. "
            "I am proud. I am genuinely, straightforwardly proud of myself."
        ),
        "Month 10 — October (Brief Setback)": (
            "October brought a cluster of difficult days — a work deadline, a difficult family "
            "conversation, and the anniversary of when I first realised something was seriously wrong. "
            "I felt the old heaviness returning for about ten days. But I used my tools, called my "
            "psychiatrist earlier than scheduled, and did not let it become a spiral. "
            "I came through the other side without losing the ground I had gained."
        ),
        "Month 11 — November (Consolidation)": (
            "I have not missed a day of work due to mental health since April and my sleep has been "
            "consistently good for three months. My medication has been successfully tapered by a "
            "further step and I feel no different — which is the ideal outcome. My therapist and I "
            "have moved to two-monthly sessions. The work we have done together has given me a "
            "framework for the rest of my life, not just a fix for the crisis."
        ),
        "Month 12 — December (Year's End)": (
            "Twelve months ago I could not get out of bed most mornings. This December I organised "
            "a dinner for twelve people, cooked the whole meal, and felt nothing but joy throughout. "
            "My family noticed the change. My friends noticed the change. I notice the change. "
            "Mental illness is real and recovery from it takes sustained effort — but it is possible. "
            "I am proof. I am grateful for every clinician and every difficult session that brought me here."
        ),
    },
    "Patient D — Oncology (Breast Cancer)": {
        "Month 1 — February (Diagnosis Shock)": (
            "When Dr Nguyen called me at home on 0412 876 543 to confirm the diagnosis I sat down "
            "on the kitchen floor and just stared at the wall for an hour. Breast cancer. "
            "I had hoped I was worrying over nothing. Care coordinator Theresa Vong rang me the next "
            "day to go through the treatment plan step by step, which helped me feel less alone. "
            "My husband doesn't know how to react and neither do I. I have been emailing the team "
            "at margaret.oconnor1954@bigpond.com asking small questions because I don't know what else to do."
        ),
        "Month 2 — March (Treatment Begins)": (
            "The first round of chemotherapy started this week and I was more frightened of the clinic "
            "than the treatment itself. Dr Helen Nguyen sat with me for nearly twenty minutes before "
            "the infusion began, which settled my nerves considerably. The nausea that evening was severe "
            "and I barely slept. Theresa Vong called the next morning to check how I was managing, "
            "and just having someone acknowledge how hard it was made a real difference. "
            "I know there are many more cycles ahead but I feel fractionally less scared than last month."
        ),
        "Month 3 — April (Managing Side Effects)": (
            "The fatigue from the second cycle has been relentless. I had to cancel my garden club "
            "meeting twice and that upset me more than I expected, because it reminded me of what "
            "this disease is taking. My hair has started falling out and I cried for most of Saturday. "
            "Dr Nguyen adjusted my anti-nausea medication which has helped somewhat. Theresa Vong "
            "organised a peer support group and I attended once via Zoom — it was unexpectedly "
            "comforting to hear from others further along the journey. I am holding on."
        ),
        "Month 4 — May (Cautious Optimism)": (
            "The midpoint scans came back showing the tumour has reduced in size and Dr Nguyen rang "
            "me personally with the news. I wept on the phone, but this time with relief rather than despair. "
            "I still have three more cycles to go but knowing the treatment is working changes everything "
            "about how I approach each difficult day. I managed a short walk around the block yesterday "
            "for the first time in weeks. Theresa Vong has been arranging transport to appointments "
            "through a volunteer service, which has taken so much pressure off my family."
        ),
        "Month 5 — June (Responding Well)": (
            "I finished the fifth cycle and my energy levels are noticeably higher than two months ago. "
            "I slept through the night four times this week, which feels miraculous. Dr Nguyen says my "
            "markers continue to improve and the team is optimistic about the final outcome. I went back "
            "to my garden club meeting and my friends barely recognised me at first, but the warmth in "
            "that room meant everything. I am beginning to think about what my life might look like "
            "on the other side of all this."
        ),
        "Month 6 — July (Remission & Gratitude)": (
            "Dr Nguyen used the phrase 'complete response' at my final review and I had to ask her to "
            "repeat it twice because I could not quite believe it. The treatment has worked. "
            "I am overwhelmed with gratitude for the oncology team, for Theresa Vong who guided me "
            "through every step, and for the treatment centre that felt like a second home. "
            "I have written a letter to the clinic emailed from margaret.oconnor1954@bigpond.com "
            "and I hope it reaches everyone who helped me. I feel reborn."
        ),
        "Month 7 — August (Post-Treatment Recovery)": (
            "The physical fatigue from six cycles of chemotherapy has not lifted as quickly as "
            "I hoped. My oncologist Dr Nguyen assured me this is normal and could persist for "
            "several months. I rejoined my garden club and managed half a meeting before needing "
            "to rest. Theresa Vong connected me with a cancer wellness program starting in September. "
            "I am resting and trying to be patient with myself."
        ),
        "Month 8 — September (Wellness Program)": (
            "I began the post-treatment wellness program Theresa Vong recommended and it has been "
            "enormously helpful. I met four other women in similar circumstances and we have already "
            "exchanged numbers. Dr Nguyen reviewed my blood markers and everything is trending in "
            "the right direction. I walked to the local park and back without needing to rest, "
            "which I count as a victory."
        ),
        "Month 9 — October (First Surveillance Scan)": (
            "My first post-treatment surveillance scan was completed and the wait for results was "
            "among the most anxious days I have experienced. Dr Nguyen called me at 0412 876 543 "
            "the following morning with a clear result. I sat at my kitchen table and wept for "
            "twenty minutes. I am in complete remission with no sign of disease. "
            "I am learning to hold this good news without immediately fearing its loss."
        ),
        "Month 10 — November (Finding New Normal)": (
            "I am approaching something that feels like a new version of my normal life. "
            "I am back at my garden club, cooking regularly, and walking forty minutes most mornings. "
            "Theresa Vong forwarded a cancer survivors' social group notice to "
            "margaret.oconnor1954@bigpond.com and I attended the first meeting — the shared "
            "understanding in that room was profound."
        ),
        "Month 11 — December (Near One Year)": (
            "It is nearly twelve months since Dr Nguyen first called me with the diagnosis and I "
            "cannot hold both realities in my mind at the same time. Then, and now. My hair has "
            "grown back, my energy is largely restored, and I am planning Christmas with my family "
            "in a way I was not sure I would be able to last year. My surveillance scans remain clear."
        ),
        "Month 12 — January (One Year Later)": (
            "One year ago I received a phone call on 0412 876 543 that changed everything. "
            "Today I am cancer-free, physically well, and genuinely happy. The fear has not fully "
            "gone — probably it never will — but it sits alongside life rather than consuming it. "
            "Dr Helen Nguyen and Theresa Vong gave me not just treatment but dignity and hope "
            "throughout the hardest experience of my life."
        ),
    },
    "Patient E — Sports Injury Recovery (Teenager)": {
        "Month 1 — April (ED Visit)": (
            "Lachlan came off the field clutching his knee during training at Coorparoo Raiders and "
            "we drove straight to the emergency department. The triage wait was distressing — he was "
            "in significant pain for over two hours before Dr Singh was able to examine him. Once seen, "
            "Dr Singh was thorough and ordered imaging. Lachlan has been on crutches since and is "
            "struggling to accept the disruption to his training schedule. He is fourteen and "
            "this is his whole world right now."
        ),
        "Month 2 — May (Diagnosis & Imaging)": (
            "The MRI confirmed a partial anterior cruciate ligament tear. The physiotherapist "
            "explained the options — conservative management versus surgery — and we decided to try "
            "physiotherapy first before considering reconstruction. Lachlan was devastated to hear "
            "he would miss the rest of the football season. He has been quiet and withdrawn at home, "
            "which concerns me more than the physical injury. The Coorparoo Raiders coaching staff "
            "have been supportive and visit regularly, which has helped his mood."
        ),
        "Month 3 — June (Physiotherapy Begins)": (
            "Three weeks into physiotherapy and the structured sessions are giving Lachlan a sense "
            "of control over his recovery. He has responded well to the strengthening program and "
            "the physio is cautiously optimistic. He is still frustrated watching his teammates "
            "play on weekends, but he is committed to the exercises. His school has been "
            "accommodating with PE exemptions. The injury has matured him — he is more patient "
            "than I have ever seen him and takes his rehab very seriously."
        ),
        "Month 4 — July (Progress)": (
            "Lachlan walked to school independently this week without a brace, which felt like a "
            "milestone for our whole family. His physiotherapist cleared him for light running on "
            "straight lines and the joy on his face during that session was worth every difficult week. "
            "He has started helping with Coorparoo Raiders junior training as an assistant, which keeps "
            "him connected to the team while he recovers. He is still six to eight weeks from "
            "return-to-sport clearance but we can see the end of the tunnel."
        ),
        "Month 5 — August (Return to Training)": (
            "Lachlan was cleared for non-contact training with the squad this week and it was one of "
            "the best days our family has had in months. He is still wearing a support brace but his "
            "movement and confidence are close to pre-injury levels. The physio has given him a "
            "sport-specific program before his final assessment in September. His date of birth is "
            "14 June 2009 which means he is eligible for the under-16 development squad next season. "
            "We are now genuinely looking forward to what comes next."
        ),
        "Month 6 — September (Cleared for Sport)": (
            "Lachlan was formally cleared to return to full contact training with Coorparoo Raiders "
            "this month and the team celebrated in the change rooms. The physiotherapist signed off "
            "on all functional tests and his strength symmetry exceeds the minimum threshold for "
            "safe return. Dr Singh's early assessment and the physiotherapy team's diligence have "
            "made this outcome possible. I am deeply grateful for the care he received, even though "
            "our initial ED experience was frustrating. He is a happy, active teenager again."
        ),
        "Month 7 — October (Competition Season)": (
            "Lachlan played his first full competitive match back with Coorparoo Raiders last weekend "
            "and it was one of those days that stays with you. He was cautious in the first half and "
            "found his rhythm in the second. The physio watched from the sideline and gave him the "
            "all-clear at the end of the game. His date of birth is 14 June 2009 — he turned fifteen "
            "in June — and has grown enormously through this experience."
        ),
        "Month 8 — November (Full Season)": (
            "Lachlan is playing full games without restriction and his confidence on the field is back "
            "to where it was before the injury. His coach has commented on the maturity he now brings "
            "to training and he is being considered for the representative squad next year. "
            "The physiotherapist has discharged him from regular sessions but he follows his "
            "maintenance program without being reminded."
        ),
        "Month 9 — December (End of Season)": (
            "Coorparoo Raiders finished third in the competition this season and Lachlan played the "
            "final four rounds in top form. His physiotherapist confirms his knee strength is at "
            "one hundred percent symmetry. He was named in the year's most improved list at the club "
            "presentation night. I sat in that room and thought about the ED waiting room in April "
            "and felt almost overwhelmed by how far we have come."
        ),
        "Month 10 — January (Pre-Season Training)": (
            "Lachlan started pre-season training with Coorparoo Raiders this month and came home "
            "from the first session energised rather than sore. His fitness base from the "
            "rehabilitation program has served him well. He took it upon himself to speak to a "
            "younger player on the squad who had recently had a knee injury — offering encouragement "
            "from his own experience. The injury changed him in ways that will benefit him long after."
        ),
        "Month 11 — February (Representative Selection)": (
            "Lachlan was selected for the District Under-16 representative squad this month. "
            "The call from the coaching coordinator came through while he was at school and he "
            "rang me immediately. I had to step outside my office to compose myself. "
            "Nine months ago he was on crutches wondering if he would play again. "
            "Today he is playing at the highest junior level available to him."
        ),
        "Month 12 — March (One Year On)": (
            "It has been exactly one year since the injury at Coorparoo Raiders that sent us to "
            "the emergency department. Lachlan asked me this morning if I remembered that night "
            "and said he is glad it happened because of what he learned from recovering. "
            "He is playing representative football and conducting himself with more maturity "
            "than most adults I know. I am deeply proud."
        ),
    },
    "Patient F — Orthopaedic Hip Replacement": {
        "Month 1 — January (Pre-Op Preparation)": (
            "The surgery date is set for 3 February 2026 and I am anxious but also relieved — "
            "the pain has been limiting everything for two years. Nurse Deborah Hartley called me "
            "at home to go through the pre-admission checklist and that conversation was genuinely "
            "reassuring. She gave me the clinic's direct line at 07 3311 9820 to call with questions. "
            "I have been doing the pre-hab exercises she recommended. The wait feels both "
            "too long and too short."
        ),
        "Month 2 — February (Surgery & Recovery)": (
            "The operation with Dr Matthew Croft went smoothly. Waking up in recovery was disorienting "
            "and the pain was significant but managed. I noticed the discharge paperwork referred to "
            "my left hip when the procedure was on my right — I flagged this with the ward nurse "
            "immediately and it was corrected. Deborah Hartley checked in by phone two days "
            "post-discharge. The first week at home has been challenging — I rely entirely on my "
            "husband — but I can already feel that the deep grinding pain from before is gone."
        ),
        "Month 3 — March (Rehabilitation)": (
            "Physiotherapy started two weeks post-op and I am doing exercises three times a day. "
            "Progress is not linear — some days feel better and others feel like a setback. "
            "I called Deborah at 07 3311 9820 about some unexpected swelling and she arranged an "
            "urgent review which turned out to be nothing concerning. The physiotherapist says "
            "I am progressing normally but it does not always feel that way. My goal is to walk "
            "to the local park unaided by the end of the month."
        ),
        "Month 4 — April (Improving Mobility)": (
            "I walked to the corner park on my own last Tuesday and sat in the sun for twenty minutes. "
            "It was the first time in years I have done that without pain. Dr Croft reviewed my X-ray "
            "at the four-week check-up and said the joint alignment is excellent. I have moved from "
            "the walker to a single crutch and am managing the stairs independently. The stiffness "
            "in the mornings takes about thirty minutes to ease but is improving week by week. "
            "I feel increasingly optimistic that I made the right decision."
        ),
        "Month 5 — May (Near Full Function)": (
            "I am now walking indoors without any aid and using a cane only for longer outdoor distances. "
            "My physiotherapy sessions have reduced to once a week and I am managing the home "
            "program well. I returned to cooking full meals, which I had given up for months. "
            "Dr Croft's office confirmed my final review appointment for June. I have recommended "
            "Dr Croft to three people in my building who are considering the same procedure."
        ),
        "Month 6 — June (Discharge)": (
            "Dr Croft signed me off at the six-month review and the imaging shows perfect integration. "
            "I walked five kilometres along the river last weekend without any discomfort. "
            "The documentation error on my discharge paperwork was acknowledged and Dr Croft "
            "has noted it for the team's quality improvement process. Deborah Hartley remembered "
            "me by name when I called to confirm the appointment, which speaks to the care "
            "this practice provides. I am deeply grateful."
        ),
        "Month 7 — July (Active Summer)": (
            "It is summer and for the first time in years I did not dread it. I have been swimming "
            "at the local pool three times a week, which Dr Croft's team endorsed as excellent "
            "low-impact conditioning. The joint feels entirely natural now — I rarely think about "
            "it consciously. I recommended the clinic to my neighbour who is considering the same "
            "procedure and gave her Deborah Hartley's number at 07 3311 9820."
        ),
        "Month 8 — August (Milestone Travel)": (
            "My husband and I flew to Cairns for our anniversary — the first flight I have taken "
            "since before my mobility declined. I walked through rainforest walks and along the "
            "esplanade without pain or hesitation. The holiday I had put off for two years because "
            "of my hip is behind us and it was everything I hoped it would be. "
            "I thought about the pre-op call with Deborah at 07 3311 9820 and felt immensely grateful."
        ),
        "Month 9 — September (Returning to Gardening)": (
            "I have returned fully to gardening, which was the activity I missed most when my hip "
            "was at its worst. I spent four hours in the garden last weekend without any discomfort. "
            "The contrast to twelve months ago, when I could not kneel or bend without pain, "
            "is remarkable. I have referred three more people to Dr Croft since my discharge in June."
        ),
        "Month 10 — October (Nine-Month Check)": (
            "I had an informal nine-month check with Dr Croft's practice nurse last week. "
            "My reported function scores placed me in the top quartile for hip replacement outcomes "
            "at this stage, which she shared with visible satisfaction. I mentioned the documentation "
            "error from my discharge paperwork and was told a new double-check protocol had been "
            "introduced as a result. That follow-through demonstrates real commitment to patient experience."
        ),
        "Month 11 — November (Community Walking)": (
            "I joined the local walking group that meets twice weekly at the botanic gardens and it "
            "has become one of my favourite parts of the week. I walked eight kilometres last Saturday "
            "without stopping and felt nothing but pride. Before my surgery two years ago that would "
            "have been unimaginable. The gift of pain-free movement is one I will never take "
            "for granted again."
        ),
        "Month 12 — December (Year Reflection)": (
            "This December marks roughly one year since my hip replacement with Dr Matthew Croft. "
            "Pain-free movement. Independence. Travel. Gardening. The simple pleasure of walking "
            "to the shops. Deborah Hartley's pre-operative care and the post-operative support made "
            "the recovery possible. If you are hesitating about the procedure out of fear — "
            "please do not wait as long as I did. The other side is worth the journey."
        ),
    },
    "Patient G — Multiple Sclerosis (NDIS-Supported)": {
        "Month 1 — January (MS Relapse)": (
            "I have been living with multiple sclerosis since 2022 and this January brought one "
            "of my worst relapses in two years. My vision blurred for nearly a week and the fatigue "
            "made it impossible to work. Dr Farid Hosseini at the Neurosciences Clinic initiated "
            "IV steroids and the response was reasonable but slow. My NDIS plan coordinator "
            "Wendy Brookes at Inclusion Solutions rang me at home and arranged a support worker "
            "while I was incapacitated. Coordinated care makes all the difference between managing "
            "and falling apart."
        ),
        "Month 2 — February (Treatment Adjustment)": (
            "Dr Hosseini reviewed my medication regime and has recommended transitioning to a "
            "higher-efficacy disease-modifying therapy. The decision is not straightforward — "
            "there are greater side effect risks but the potential to reduce relapse frequency "
            "is meaningful. I have been calling Wendy Brookes at Inclusion Solutions on 07 3876 2200 "
            "to talk through what I have read, which helps me process it. My partner has been "
            "incredibly supportive but this disease affects our whole household and that weighs on me."
        ),
        "Month 3 — March (Stabilising)": (
            "The new medication started this month and I am closely monitoring how I feel. "
            "Side effects have been manageable — some fatigue and mild headaches in the first "
            "week but settling now. My vision has been stable for six weeks, the longest clear "
            "period I can recall. Dr Hosseini's clinic has a nurse specialist who calls fortnightly "
            "to check on my progress, which provides a safety net I value. Wendy Brookes has "
            "updated my NDIS plan to include additional support hours. I feel cautiously stable."
        ),
        "Month 4 — April (MRI Good News)": (
            "I had an MRI on 22 April 2026 and the results were uploaded to MyHealthRecord within "
            "48 hours as promised — that efficiency matters when you are waiting anxiously. "
            "Dr Hosseini called me directly to say there are no new lesions and existing ones "
            "show no progression. I am more relieved than I know how to express. The new medication "
            "appears to be working. Wendy Brookes is updating my NDIS goals and we are starting "
            "to think about returning to part-time work, which I had given up on."
        ),
        "Month 5 — May (Returning to Activity)": (
            "I worked three days this week for the first time since November. The fatigue is "
            "still present but manageable rather than overwhelming. I attended a MS Society "
            "information evening and spoke with others who have had similar experiences with "
            "the same medication, which was validating and encouraging. Dr Hosseini's team "
            "has been responsive to every query. Wendy Brookes on 07 3876 2200 has secured "
            "additional therapeutic supports that are making daily life significantly more manageable."
        ),
        "Month 6 — June (Stable & Well-Managed)": (
            "Six months ago I could barely get off the couch and now I am working regularly, "
            "socialising, and planning a weekend trip with my partner. Dr Hosseini describes "
            "my current status as clinically stable and well-controlled — words I have wanted "
            "to hear for a long time. I am on a six-month MRI schedule rather than three-monthly, "
            "which itself signals progress. Coordinated care between the neurology clinic, my NDIS "
            "supports, and my workplace has made this recovery possible."
        ),
        "Month 7 — July (Stable Summer)": (
            "I have now been relapse-free for six months — the longest stretch since my MS diagnosis "
            "in 2022. The summer heat is always a risk factor for MS symptoms so I am careful about "
            "hydration and avoiding the midday sun. Dr Hosseini's team has a heat protocol in place "
            "and Wendy Brookes at Inclusion Solutions adjusted my NDIS support hours for summer. "
            "I am working four days a week and managing the fifth day as a rest day."
        ),
        "Month 8 — August (Full Work Return)": (
            "I returned to a five-day working week this month for the first time since my January "
            "relapse. The fatigue is present but manageable rather than disabling. I have also "
            "started attending a monthly MS peer support group that Wendy Brookes identified, "
            "and the solidarity in that group is genuinely sustaining. "
            "My six-monthly MRI is scheduled for September."
        ),
        "Month 9 — September (MRI Results)": (
            "My six-monthly MRI came back showing continued stability — no new lesions, no "
            "progression of existing disease. Dr Hosseini was visibly pleased and said my response "
            "to the new therapy has been 'exceptional'. I called Wendy Brookes at Inclusion Solutions "
            "on 07 3876 2200 the same evening to share the news. "
            "The NDIS system at its best is what she represents."
        ),
        "Month 10 — October (NDIS Review)": (
            "My annual NDIS plan review was completed this month and Wendy Brookes facilitated "
            "the process with great skill. My goals have shifted significantly since January — "
            "from acute management to long-term participation. Increased funding for community "
            "participation and exercise physiology was approved. I feel that my NDIS plan is "
            "finally a document that describes my life as I am living it."
        ),
        "Month 11 — November (Ten Months Stable)": (
            "Ten consecutive months without a relapse. Dr Hosseini and I discussed this at my "
            "regular appointment and agreed the current medication regime and lifestyle adaptations "
            "are working optimally together. I have started volunteering with the MS Society one "
            "Saturday per month. I called Wendy Brookes at 07 3876 2200 to tell her and she "
            "was genuinely moved. This time last year I was at my worst."
        ),
        "Month 12 — December (Year-End Stability)": (
            "I am ending the year stable, employed, active, and more connected to my community "
            "than I have been since before my diagnosis. Dr Farid Hosseini's medical management, "
            "Wendy Brookes' NDIS coordination, and the peer networks I have found this year have "
            "together made the kind of life I now have possible. MS is not cured and it is not gone. "
            "But it is managed, and management is a genuinely good outcome with the right team."
        ),
    },
    "Patient H — Skin Cancer Scare (Dermatology)": {
        "Month 1 — February (GP Referral)": (
            "My GP noticed a mole on my back during a routine check-up and referred me urgently "
            "to the dermatology clinic. I had been ignoring it for months and now I cannot stop "
            "thinking about it. The waiting between the referral and the appointment was agonising. "
            "I found myself searching symptoms online at 2am which helped nothing. I called the "
            "clinic to ask about the waiting time and was told three to four weeks. "
            "Every day felt long."
        ),
        "Month 2 — March (Biopsy)": (
            "Dr Sofia Papadopoulos removed the suspicious lesion from my back on 11 March 2026. "
            "The procedure was quick and relatively painless. She explained clearly what she was "
            "removing and why, which helped me feel less frightened. The biopsy has been sent "
            "for pathology and results will take ten to fourteen days. The clinic has my contact "
            "email as henry.bartlett@optusnet.com.au if they need to reach me urgently. "
            "The waiting is the hardest part."
        ),
        "Month 3 — April (Benign Result)": (
            "The pathology results came back benign and I am still processing the relief — "
            "I had convinced myself it was going to be bad news. Dr Papadopoulos sent a follow-up "
            "letter confirming no further treatment was needed. However, I noticed my Medicare "
            "number 3876 54321 0 was printed incorrectly on my receipt — one digit was wrong. "
            "I emailed henry.bartlett@optusnet.com.au as a follow-up and the billing team "
            "corrected it within the week."
        ),
        "Month 4 — May (Sun Safety Awareness)": (
            "I attended a free skin health education session at the clinic this month following "
            "my experience in March. I learned a great deal about melanoma risk factors I wish "
            "I had known years ago. Dr Papadopoulos has recommended annual full-body skin checks "
            "going forward. I have started using SPF50 every day and bought a broad-brimmed hat. "
            "I feel motivated rather than anxious now — the close call in March has genuinely "
            "changed my habits. I want my family to be checked as well."
        ),
        "Month 5 — June (Follow-up Check)": (
            "My follow-up with Dr Papadopoulos confirmed the site has healed well with no "
            "concerning changes. She also identified two other lesions she wants to monitor "
            "at a twelve-month review. Knowing what I know now I do not find that alarming — "
            "it is simply good preventive care. My partner attended the appointment with me "
            "and we both feel confident in how this practice manages ongoing skin surveillance. "
            "I have referred two colleagues to Dr Papadopoulos for their own checks."
        ),
        "Month 6 — July (Peace of Mind)": (
            "Six months since the initial referral and I feel entirely different about my health. "
            "What could have been a serious diagnosis was caught early, managed professionally, "
            "and resolved. The billing correction was handled efficiently. Dr Papadopoulos is "
            "knowledgeable and straightforward, which suits me — I need to be informed, not "
            "just reassured. I have a twelve-month skin check booked and I intend to keep it. "
            "I am grateful for the attentive GP who spotted the mole."
        ),
        "Month 7 — August (Family Checks)": (
            "Following my experience in March, I encouraged my brother and sister to book skin "
            "checks with Dr Sofia Papadopoulos. Both attended appointments in August. My brother "
            "had one lesion removed for biopsy — it came back benign — and my sister was given "
            "the all-clear. Dr Papadopoulos commented that family history is an important risk "
            "factor and that proactive screening in relatives is exactly the right approach."
        ),
        "Month 8 — September (Sun Safety at Work)": (
            "I gave a brief talk at my workplace about skin cancer awareness and the importance "
            "of annual checks. It was not something I would have imagined doing six months ago, "
            "but the experience has made me an advocate. Several colleagues have since booked "
            "appointments. I have been consistently applying SPF50 daily since April "
            "and the habits formed out of fear have become routine without effort."
        ),
        "Month 9 — October (Six-Month Follow-up)": (
            "I had my six-month follow-up with Dr Papadopoulos and the two additional lesions "
            "she identified in June show no change — exactly the expected outcome for benign "
            "monitoring spots. The biopsy site from March has healed completely. I mentioned the "
            "Medicare billing discrepancy and was told the Medicare number 3876 54321 0 correction "
            "had been made and a new quality check introduced for the clinic's billing process."
        ),
        "Month 10 — November (Routine Established)": (
            "My annual skin check routine is now firmly established. I have a twelve-month review "
            "booked for March and in the meantime do a monthly self-check as Dr Papadopoulos "
            "recommended. The anxiety that dominated February and March has been replaced by "
            "calm, informed vigilance. The billing team can be reached at henry.bartlett@optusnet.com.au "
            "and has always responded promptly to my queries."
        ),
        "Month 11 — December (Healthy Habits)": (
            "This is the first December in at least a decade where I have worn a hat consistently "
            "throughout summer. It sounds like a small thing but it represents a genuine change in "
            "how I think about my health. The close call in March changed my relationship with "
            "preventive care in a way that I suspect will be permanent. I am also eating better "
            "and exercising more — the skin cancer scare triggered a broader health reflection."
        ),
        "Month 12 — January (Twelve-Month Clear)": (
            "My twelve-month review with Dr Papadopoulos confirmed all monitored lesions are stable "
            "and the overall skin assessment found no new concerns. She noted the biopsy scar is "
            "barely visible. I left the clinic feeling calm and grateful — a complete contrast to "
            "how I felt arriving at my very first appointment in February last year. "
            "I will see Dr Papadopoulos again in twelve months and I look forward to it without dread."
        ),
    },
    "Patient I — Urology (Diagnostic Journey)": {
        "Month 1 — January (Referral & Waiting)": (
            "My name is Victor Papadimitriou, born 23 September 1948, and I was referred to "
            "urology by Dr Kenneth Marsh at Sunnybank Hills Family Practice on 9 January 2026 "
            "following the discovery of blood in my urine. The referral was marked urgent. "
            "I waited two weeks without contact and called 07 3240 6600 to ask about my appointment. "
            "I was placed on hold each time and the third call was disconnected. At my age, "
            "haematuria is not something one ignores."
        ),
        "Month 2 — February (Still Waiting)": (
            "I have now been waiting six weeks since my urgent referral and still have no appointment. "
            "I called Dr Marsh's rooms and his nurse contacted urology on my behalf. Apparently my "
            "referral had not been triaged correctly into the urgent category. This was alarming. "
            "Dr Marsh was apologetic and has escalated the matter. My wife is worried and I find "
            "I cannot reassure her because I share her concern. I have submitted a written complaint "
            "to the hospital."
        ),
        "Month 3 — March (Finally Seen)": (
            "I was finally seen in the urology clinic on 14 March 2026 — ten weeks after Dr Marsh's "
            "urgent referral. The urologist was thorough and did not dismiss the wait time as "
            "acceptable. He ordered a cystoscopy and CT urogram and said results would be available "
            "within two weeks. The relief of being seen was enormous, even before any results. "
            "A phone call to acknowledge my referral had been received would have meant a great deal "
            "during those anxious weeks."
        ),
        "Month 4 — April (Diagnosis)": (
            "The cystoscopy showed no malignancy — the haematuria was caused by a kidney stone "
            "in my left ureter. The relief I felt was profound. The urologist explained treatment "
            "options and has recommended ureteroscopy to remove the stone. A date has been set "
            "for early May. Dr Marsh was contacted directly and called me the same afternoon. "
            "The coordinated communication between the specialist and my GP this time was exactly "
            "what had been missing in January."
        ),
        "Month 5 — May (Procedure)": (
            "The ureteroscopy was completed on 8 May 2026 without complications. I was admitted "
            "in the morning and discharged the same afternoon. The procedure was far less "
            "uncomfortable than I had anticipated. The stone has been removed and the urologist "
            "confirmed there are no other concerning findings on my imaging. I need to increase "
            "my fluid intake and return for a follow-up in three months. My wife Eleni drove me home "
            "and we stopped for a quiet lunch together — the first time we have felt relaxed in months."
        ),
        "Month 6 — June (Recovery & Resolution)": (
            "My follow-up review confirmed the stone has not recurred and my kidney function "
            "is normal. The haematuria has completely resolved. Looking back, January and February "
            "were among the most anxious months I have experienced in a long time, and the "
            "communication failures at the referral stage made them harder than they needed to be. "
            "I have submitted feedback to the hospital outlining my experience, not out of anger "
            "but because I hope it leads to process improvement."
        ),
        "Month 7 — July (Dietary Changes)": (
            "My urologist recommended increasing my daily fluid intake to two-and-a-half litres "
            "and reducing oxalate-rich foods to minimise stone recurrence risk. My wife Eleni "
            "has been very supportive, adjusting our cooking and keeping a water jug on the bench. "
            "Dr Marsh at Sunnybank Hills reviewed my follow-up letter from the urology team and "
            "called me to ensure I understood all the dietary guidance."
        ),
        "Month 8 — August (Three-Month Review)": (
            "The three-month follow-up ultrasound confirmed no new stone formation and my kidneys "
            "appear entirely normal. The urologist's nurse called with the results, which avoided "
            "another anxious wait. The haematuria has not returned. My blood pressure, which had "
            "elevated during the diagnostic period, has also normalised. "
            "I am feeling well for the first time in a year."
        ),
        "Month 9 — September (Feedback Acknowledged)": (
            "I received a written response from the hospital's patient experience team acknowledging "
            "my complaint about the ten-week wait following my urgent referral. The letter described "
            "process changes including a 48-hour contact protocol for all urgent urology referrals. "
            "They thanked me for raising the issue. I was born 23 September 1948 — today is my "
            "birthday — and I mark it feeling well and vindicated."
        ),
        "Month 10 — October (Back to Normal)": (
            "I have resumed all my usual activities, including my Tuesday bowling club and Saturday "
            "morning walks I had abandoned when my health was uncertain. Eleni and I celebrated "
            "our fifty-third wedding anniversary with a dinner at our favourite restaurant. "
            "Dr Marsh at Sunnybank Hills sends a quarterly health summary which keeps all my "
            "conditions in one coordinated picture. I feel well-looked-after."
        ),
        "Month 11 — November (Preventive Focus)": (
            "I attended a community health talk on kidney disease prevention and recognised several "
            "points from my own experience. I spoke to the presenter afterwards and mentioned that "
            "the communication failures during my referral in January had made a frightening situation "
            "worse. She encouraged me to share that experience more broadly and I am considering "
            "submitting it to the hospital's patient advisory group."
        ),
        "Month 12 — December (Year Closes Well)": (
            "I finish the year in good health and good spirits. The kidney stone has been removed "
            "and has not returned. My urologist at 07 3240 6600 has been reachable and thorough "
            "in follow-up. Dr Marsh continues to provide coordinated primary care. "
            "Eleni and I are having our family for Christmas dinner — all four children and six "
            "grandchildren. I could not ask for more."
        ),
    },
    "Patient J — Paediatric Cerebral Palsy (Parent Journal)": {
        "Month 1 — November (Initial Assessment)": (
            "Our daughter Isabelle is four years old and was diagnosed with mild cerebral palsy "
            "eighteen months ago. We attended our initial assessment and Grace Ngo took time to "
            "understand not just Isabelle's clinical needs but our hopes and concerns as parents. "
            "My husband Tom Mortimer and I had been to several services that felt clinical and "
            "impersonal. Grace was different — she got on the floor with Isabelle and made the "
            "session feel like play. We left cautiously hopeful for the first time in a long time."
        ),
        "Month 2 — December (Therapy Starts)": (
            "Isabelle has had four sessions with Grace Ngo now and is already more willing to "
            "engage than we expected. Grace explained that children with cerebral palsy often "
            "respond well when therapeutic activities are embedded in play. Tom and I have been "
            "given a home exercise program to do with Isabelle each morning and evening — about "
            "twenty minutes. Isabelle treats them as part of her routine now. We feel like active "
            "partners in her therapy rather than observers."
        ),
        "Month 3 — January (First Milestones)": (
            "Isabelle walked unassisted for a measured distance at Grace Ngo's session last week "
            "and we all stopped before anyone spoke. It was about four metres — small, but "
            "independent and deliberate. Tom and I cried in the car on the way home. Grace is "
            "careful not to over-promise but told us Isabelle is responding very well and that "
            "her engagement with the exercises is a key factor. We have decided to increase "
            "sessions to twice a week for the next two months."
        ),
        "Month 4 — February (Growing Confidence)": (
            "Isabelle climbed three steps at the playground last week holding the rail — "
            "something she was unable to do six months ago. Her peer interactions are improving "
            "too, which Grace says often happens alongside physical progress as children gain "
            "confidence. Grace referred us to the Early Childhood Early Intervention team at "
            "Stafford and the referral was accepted. Tom and I feel like a team now — managing "
            "Isabelle's therapy, home program, and upcoming ECEI enrollment feels organised "
            "rather than overwhelming."
        ),
        "Month 5 — March (ECEI Enrolled)": (
            "Isabelle started with the Early Childhood Early Intervention team at Stafford "
            "this month and the handover from Grace Ngo was seamless. Both services communicate "
            "directly with each other, which means Isabelle's program is consistent and progressive "
            "rather than fragmented. Tom and I attended an ECEI parent information session and met "
            "other families in similar situations — that community aspect has been unexpectedly "
            "important. Isabelle told us last week that she likes her exercises, which is the "
            "best thing we have ever heard."
        ),
        "Month 6 — April (Transformation)": (
            "Looking back at where we were in November compared to today is genuinely moving. "
            "Isabelle is walking consistently across most indoor surfaces, climbing stairs with "
            "support, and engaging confidently with her peers at daycare. Grace Ngo's approach "
            "has been the foundation of this progress. The ECEI team at Stafford, which Grace "
            "recommended, has added another layer of support. Tom and I feel equipped to be "
            "Isabelle's advocates in a way we did not before. We are building toward a future "
            "for our daughter."
        ),
        "Month 7 — May (School Preparation)": (
            "Isabelle turns five in June and school preparations are underway. Grace Ngo has "
            "completed a school readiness assessment and provided a report to the education "
            "department to inform Isabelle's enrolment plan. Tom and I visited the school and "
            "met with the inclusion coordinator, who was warm and experienced with children "
            "with disability. We left feeling hopeful rather than apprehensive."
        ),
        "Month 8 — June (School Begins)": (
            "Isabelle started school this month and the first week went better than either Tom "
            "or I dared hope. She walked into her classroom independently on day one and her "
            "teacher reported that she engaged confidently with the other children. Grace Ngo "
            "visited the school in the third week to observe and consult with the teacher. "
            "Isabelle came home on Friday with a drawing she had made for 'my fisso Grace' — we framed it."
        ),
        "Month 9 — July (School Settling)": (
            "Two months into school and Isabelle is settled, happy, and making friends. She has "
            "a peer buddy who helps her navigate the playground. The school's occupational therapist "
            "has introduced simple adaptations to Isabelle's writing materials and she is managing "
            "at the same pace as her class. Tom and I check in with Grace Ngo monthly now, "
            "down from weekly visits at the start of the year."
        ),
        "Month 10 — August (Independence Growing)": (
            "Isabelle dressed herself completely independently for the first time this morning. "
            "It took twenty minutes and the shirt was slightly inside out, but she did it entirely "
            "on her own and the look on her face when she came to show us was something I will carry "
            "for the rest of my life. Grace Ngo's home program, which Tom and I have done every "
            "single morning for ten months, is behind this."
        ),
        "Month 11 — September (One-Year Review)": (
            "We attended Isabelle's one-year review with Grace Ngo and the ECEI team at Stafford. "
            "The progress documented in that report — from where she was in November to today — "
            "moved both Tom and me to tears. Walking distances, stair use, peer interaction, fine "
            "motor function — all showing significant improvement. Grace recommended transitioning "
            "to termly rather than monthly physiotherapy sessions."
        ),
        "Month 12 — October (Thriving)": (
            "Isabelle performed in her school's concert last week — she walked onto the stage with "
            "her classmates, stood in line, and sang every word of the song. Tom filmed it and I "
            "have watched it every day since. One year ago we were attending a first assessment "
            "appointment with a four-year-old who could not reliably walk four metres. Today she "
            "is a school-age child who performs on stage and makes friends. Grace Ngo and the ECEI "
            "team at Stafford changed our family's life."
        ),
    },
    "Patient K — Stroke Recovery (OT & NDIS)": {
        "Month 1 — March (Stroke & Hospitalisation)": (
            "I had a stroke on 6 March 2026. There are gaps in what I remember from the first hours. "
            "My family tells me I was admitted within ninety minutes of the first symptoms and that "
            "response time likely made a significant difference to my recovery. I have weakness on "
            "my left side and struggle to speak quickly. I live alone at 88 Rode Road, Wavell Heights, "
            "and my family was frightened about how I would manage. I was too."
        ),
        "Month 2 — April (Home Assessment)": (
            "Occupational therapist Sandra Yuen came to my home at 88 Rode Road, Wavell Heights "
            "on 14 April 2026 and spent two hours assessing the space and my functional needs. "
            "She had already arranged for grab rails and a shower seat to be installed before "
            "her visit ended. My NDIS support coordinator Brian Leung at Able Future Services, "
            "reachable on 0401 558 772, coordinated equipment delivery within days. The transition "
            "from hospital to home felt supported rather than abandoned."
        ),
        "Month 3 — May (NDIS Supports in Place)": (
            "My NDIS supports are now fully in place. I have a support worker three mornings a week "
            "for personal care and meal preparation, and a speech pathologist visits fortnightly. "
            "Sandra Yuen checks in monthly to review my home environment as my function changes. "
            "Brian Leung at Able Future Services has been responsive to every adjustment request. "
            "I am beginning to walk the length of the hallway unaided and my speech has improved "
            "more quickly than the hospital team predicted."
        ),
        "Month 4 — June (Progress)": (
            "I walked to the letterbox and back on my own yesterday, which sounds modest but felt "
            "like returning from a very long journey. My left hand grip is improving and I can now "
            "make myself a sandwich independently. My speech is slow but clear. Sandra Yuen "
            "assessed that I no longer need the shower seat for every session — a real milestone. "
            "I have started using a walking frame for short outdoor distances. Brian Leung is "
            "reviewing my NDIS plan to reflect my improving needs."
        ),
        "Month 5 — July (Independence)": (
            "I cooked dinner for my daughter this week. She cried. I was quite pleased with myself. "
            "The improvements over four months have been steady and the team around me — Sandra Yuen, "
            "Brian Leung at Able Future Services on 0401 558 772, my speech pathologist — have made "
            "the journey manageable. I am now walking outside with just a cane for half an hour "
            "each morning. My occupational therapy sessions have moved to fortnightly as my "
            "independence increases."
        ),
        "Month 6 — August (Gratitude & Looking Forward)": (
            "Five months after a stroke that could have been much more serious, I am living "
            "independently, cooking, walking outside daily, and speaking fluently. Sandra Yuen's "
            "home assessment in April was the turning point — having the right equipment and supports "
            "in place from the start prevented falls and built my confidence. Brian Leung at "
            "0401 558 772 managed the NDIS coordination with professionalism and genuine care. "
            "I have now reduced to one support worker morning per week. Life has been given back to me."
        ),
        "Month 7 — September (Support Phasing Out)": (
            "My NDIS support worker is now down to two mornings per week, reduced from five at "
            "the start of my recovery. Brian Leung at Able Future Services on 0401 558 772 has "
            "been managing this transition thoughtfully, reviewing my needs each fortnight. "
            "Sandra Yuen's last monthly review confirmed that my home environment is now fully "
            "safe and functional. I feel the independence I feared might be gone returning steadily."
        ),
        "Month 8 — October (Driving)": (
            "I passed my driving assessment this month and am back behind the wheel. The first "
            "solo drive to the shops from 88 Rode Road, Wavell Heights was a fifteen-minute journey "
            "that felt like an expedition. The freedom of independent movement after seven months "
            "of reliance on others is almost impossible to describe. "
            "I called Brian Leung at 0401 558 772 to tell him and he was genuinely delighted."
        ),
        "Month 9 — November (Community)": (
            "I have returned to my Tuesday bowls club at the local recreation centre — the first "
            "time since my stroke on 6 March 2026. My left side grip is ninety percent of what it "
            "was and improving. Sandra Yuen attended one session to observe my function in a social "
            "physical context and was satisfied with what she saw. She has discharged me from regular "
            "OT contact with a final written summary for my GP."
        ),
        "Month 10 — December (Nine Months Well)": (
            "Nine months since my stroke and I am living fully independently at 88 Rode Road, "
            "Wavell Heights. I cooked Christmas lunch for my daughter and her family — a full roast "
            "— and felt nothing but pleasure throughout. Brian Leung at Able Future Services has "
            "prepared a final NDIS review noting my exit from intensive support and my transition "
            "to a self-management model."
        ),
        "Month 11 — January (Stroke Anniversary Reflection)": (
            "It has been nearly ten months since the stroke. The neurologist's one-year review "
            "is scheduled for next month. I walk forty-five minutes each morning along the street "
            "from 88 Rode Road, something I could not have imagined doing in March. My speech is "
            "fully restored and my left-side strength is at about ninety-five percent. "
            "The NDIS supports have now concluded. I live alone and I manage."
        ),
        "Month 12 — February (One-Year Review)": (
            "My one-year neurological review confirms an excellent recovery by every clinical "
            "measure. The neurologist used the word 'remarkable' and said my return to independent "
            "function places me in the best-outcome category for strokes of my type. The early "
            "response time, Sandra Yuen's home assessment, and Brian Leung's NDIS coordination "
            "were all cited in my notes as contributing factors. I am well."
        ),
    },
    "Patient L — Crohn's Disease (Gastroenterology)": {
        "Month 1 — November (Diagnosis)": (
            "I was diagnosed with Crohn's disease in November 2025 after months of unexplained "
            "symptoms. Dr Paul Brennan at the gastroenterology clinic was direct and thorough "
            "in explaining the condition and what treatment might involve. I work at Queensland Rail "
            "and managing a chronic illness alongside shift work is a genuine challenge that I raised "
            "with him from the outset. He acknowledged the practical reality of my situation, "
            "which I appreciated. I was overwhelmed but glad to finally have an answer."
        ),
        "Month 2 — December (First Treatment)": (
            "I started on first-line immunomodulator therapy in early December and the adjustment "
            "period has been harder than expected. The joint pain in the first fortnight was "
            "significant and my energy was very low. I had to take sick leave from Queensland Rail "
            "which created additional stress. Dr Brennan's nurse specialist called to check on me "
            "during Christmas week, which I did not expect but was genuinely grateful for. "
            "I do not think my family fully understands how debilitating the fatigue can be."
        ),
        "Month 3 — January (Biologics Start)": (
            "Dr Brennan recommended transitioning to biological therapy starting January 2026. "
            "I began infusions at the day unit and the difference was noticeable within three weeks. "
            "The deep abdominal cramping that had become constant background noise began to ease. "
            "I returned to Queensland Rail part-time in the third week of January and managed a "
            "full shift without needing to leave early — something that had been impossible for months. "
            "I feel hopeful in a way I have not since this all began."
        ),
        "Month 4 — February (Significant Improvement)": (
            "February has been the best month in over a year. I have completed four biologic "
            "infusions and the improvement in my symptoms has been consistent. My energy is "
            "significantly better, I have returned to full-time work at Queensland Rail, and I "
            "attended my nephew's birthday party last weekend — the first social event I have "
            "felt well enough to enjoy since my diagnosis. Dr Brennan is cautiously optimistic "
            "about achieving sustained remission. I sleep through the night now."
        ),
        "Month 5 — March (Infusion Cancellation Issue)": (
            "My infusion appointment on 30 April 2026 was cancelled by SMS from 0488 900 123 "
            "with only three hours notice. Rescheduling required an additional day off at "
            "Queensland Rail which I cannot always arrange on short notice. I understand "
            "cancellations happen but the brevity of the notice was genuinely difficult. I have "
            "raised this with Dr Brennan's rooms and requested at least 48 hours notice for future "
            "cancellations. My overall care has been excellent and I hope this feedback leads "
            "to a practical change."
        ),
        "Month 6 — April (Remission)": (
            "Dr Brennan confirmed at my six-month review that my inflammatory markers are in the "
            "normal range for the first time and he is comfortable using the word remission. "
            "I am on a maintenance infusion schedule every eight weeks and managing this alongside "
            "my Queensland Rail roster has become routine. The cancellation issue in March was "
            "acknowledged by the clinic and they have updated their protocol. I feel stable, "
            "informed, and confident in my care team."
        ),
        "Month 7 — May (Maintenance Established)": (
            "Six months into biologic therapy and my maintenance infusion schedule is working "
            "smoothly. Dr Paul Brennan reviewed my inflammatory markers and said they are "
            "'textbook normal'. My roster at Queensland Rail has been adjusted to accommodate "
            "my infusion days and the clinic now provides 72-hour notice for schedule changes "
            "following my March complaint."
        ),
        "Month 8 — June (Dietary Freedom)": (
            "My dietitian has progressively reintroduced foods I had avoided during active disease "
            "and I have tolerated all of them without symptom recurrence. I ate a full restaurant "
            "meal last week for the first time in eighteen months. Food restriction is one of the "
            "aspects of Crohn's that most affects quality of life, and regaining that freedom "
            "matters enormously."
        ),
        "Month 9 — July (Colonoscopy Review)": (
            "My six-monthly colonoscopy showed significant mucosal healing compared to the baseline "
            "taken at diagnosis. Dr Brennan described the result as 'deep remission' and explained "
            "that this is the goal of biologic therapy — not just symptom control but actual healing "
            "of the bowel wall. I called my mother after the appointment to share the news. "
            "The relief in her voice meant as much to me as the clinical result."
        ),
        "Month 10 — August (IBD Community)": (
            "I have started volunteering with an IBD patient support group that Dr Brennan's "
            "practice co-ordinates. I attend fortnightly and speak with newly diagnosed patients "
            "about what the early months are like and what improvements are possible. "
            "My manager at Queensland Rail organised a morning tea when I mentioned I would be "
            "doing this work. My experience has found a purpose beyond my own recovery."
        ),
        "Month 11 — September (Ten Months Well)": (
            "I have now been in clinical remission for ten months. My infusion appointments are "
            "managed without disruption, Queensland Rail knows my schedule, and the condition has "
            "receded to a manageable background element rather than a defining feature. Dr Brennan "
            "called me this month to say my case would be presented at a conference as an example "
            "of optimal treatment response to biologics."
        ),
        "Month 12 — October (Year-End)": (
            "One year after my Crohn's diagnosis in November 2025, I am in deep remission and "
            "living a full life. The arc has been one of steady improvement thanks to Dr Paul Brennan "
            "and his team. My maintenance infusion schedule, coordinated around my Queensland Rail "
            "shifts, works reliably. I have stopped dreading the SMS from 0488 900 123 — "
            "it now just means my appointment is confirmed."
        ),
    },
    "Patient M — Breast Screening Recall": {
        "Month 1 — April (Routine Screening)": (
            "I attended the BreastScreen Queensland mobile clinic at Carindale on 8 April 2026 "
            "for my routine two-yearly screening — my third. Radiographer Patrice Delacroix "
            "was professional and considerate, explaining each step clearly. The visit took about "
            "twenty minutes. I live at 3 Banksia Court, Carindale QLD 4152 and my results are also "
            "copied to Dr Michelle Tan at Carindale Family Health on 07 3398 7700. "
            "I expected a normal result letter within ten days as on previous occasions."
        ),
        "Month 2 — May (Recall Letter)": (
            "I received a letter asking me to return for further imaging and I can barely describe "
            "the state that put me in. I know intellectually that recalls do not necessarily mean "
            "anything serious — the letter said so — but rationally knowing something and emotionally "
            "believing it are two different things. I called Dr Michelle Tan at 07 3398 7700 and she "
            "spoke with me for fifteen minutes explaining what the recall process involves. "
            "That conversation helped. I have the additional imaging appointment booked for late May."
        ),
        "Month 3 — June (Further Imaging)": (
            "The additional mammogram and ultrasound identified a small area the radiologist wants "
            "to investigate further. A core needle biopsy has been recommended. A breast care nurse "
            "sat with me for thirty minutes after the appointment, and her calmness was something "
            "I genuinely needed. Patrice Delacroix was at the recall clinic and remembered me "
            "from my April appointment, which felt oddly reassuring. I have told my husband "
            "and my closest friend. The waiting is the worst part of all of this."
        ),
        "Month 4 — July (Biopsy)": (
            "The biopsy was completed on 3 July 2026 and the results were expected within "
            "five to seven working days. The breast care nurse called me on the morning of "
            "the procedure to confirm the time and check that I had someone to drive me home. "
            "Results will be posted to 3 Banksia Court and a copy sent to Dr Michelle Tan "
            "at Carindale Family Health. I have been occupying myself with gardening and walking "
            "and trying not to read medical journals online, which serves no useful purpose."
        ),
        "Month 5 — August (Benign Result)": (
            "The biopsy results came back showing a benign fibroadenoma. The breast care nurse "
            "called me at home with the result and I sat down on the kitchen floor and laughed "
            "and then cried, in that order. Dr Michelle Tan rang as well, which I did not expect, "
            "and we spoke for a few minutes. The relief is physical — I can feel the tension "
            "leaving my body. BreastScreen Queensland will schedule a six-month follow-up to "
            "confirm stability of the lesion."
        ),
        "Month 6 — September (Follow-up & Peace of Mind)": (
            "The six-month follow-up imaging showed no change in the fibroadenoma — the best "
            "possible result. The entire BreastScreen team conducted themselves with exceptional "
            "professionalism and compassion throughout what was the most frightening four months "
            "of my life. Dr Michelle Tan at 07 3398 7700 has arranged annual screening given "
            "my recall history. I have spoken to three friends who have been putting off their "
            "screenings and encouraged them to book. Early detection changed everything in my case."
        ),
        "Month 7 — October (Returning to Normal)": (
            "It is now one month since I received the benign biopsy result and I am beginning to "
            "feel like myself again. I had coffee with two friends last week and we talked about "
            "the screening experience openly. One of them admitted she had been putting off her "
            "own overdue screening. I booked the appointment for her online before we left the cafe. "
            "If one good thing comes from those frightening months it is that."
        ),
        "Month 8 — November (Supporting Others)": (
            "Three friends have now attended BreastScreen Queensland appointments following "
            "conversations with me about my recall experience. Two have already received clear "
            "results and one is awaiting hers. I told each of them about Patrice Delacroix and "
            "the professionalism of the clinic, and about Dr Michelle Tan at Carindale Family "
            "Health on 07 3398 7700 who supported me through every stage."
        ),
        "Month 9 — December (Six-Month Stability Review)": (
            "BreastScreen Queensland conducted my six-month imaging review and the fibroadenoma "
            "is completely stable with no change in size or characteristics. The radiologist "
            "confirmed this is the expected trajectory and I am now on an annual review schedule. "
            "I sent thank-you letters to the clinic team and to Dr Michelle Tan. I feel that "
            "the people who held me steady deserve to know the outcome has been good."
        ),
        "Month 10 — January (New Year Well)": (
            "The new year began with a clear conscience and a clean bill of health. The postal "
            "results letter arrived at 3 Banksia Court as promised and confirmed the December "
            "imaging outcome. Dr Michelle Tan reviewed both letters at my January check-up and "
            "updated my health record accordingly. I feel entirely differently about medical "
            "appointments now — not as inconveniences but as the system working as it should."
        ),
        "Month 11 — February (Reflection)": (
            "Seven months since my benign result and the anxiety has not returned. I think about "
            "the recall period sometimes — the waiting, the biopsy on 3 July, the phone call from "
            "the breast care nurse — but I think about it as a story that ended well. Patrice "
            "Delacroix and the BreastScreen team gave me an experience of the health system at "
            "its most compassionate."
        ),
        "Month 12 — March (Twelve Months On)": (
            "Exactly twelve months since the BreastScreen mobile clinic visited Carindale on "
            "8 April 2026. The screening that triggered months of anxiety has also led to a year "
            "of closer self-attention and more meaningful conversations with Dr Michelle Tan "
            "at 07 3398 7700. I will attend my next BreastScreen appointment without hesitation. "
            "The experience frightened me, but it also showed me that the system, when it works, "
            "works with genuine care."
        ),
    },
    "Patient N — Continence Clinic (Elderly Patient)": {
        "Month 1 — February (First Appointment)": (
            "I turned 76 last month and attended the continence clinic on 18 February 2026 "
            "with some reluctance. Nurse Margaret Skelton was discreet and put me entirely at ease "
            "within the first few minutes. She did not make me feel embarrassed, which I had been "
            "dreading. Because I do not use a computer, she arranged to send follow-up information "
            "to my son at christopher.skelton@gmail.com. I live alone at 12 Coronation Drive, "
            "Nundah QLD 4012 and the clinic is close to my train station, which matters at my age."
        ),
        "Month 2 — March (Treatment Begins)": (
            "Nurse Skelton prescribed a pelvic floor rehabilitation program and provided written "
            "materials that my son Christopher printed out for me. I have been doing the exercises "
            "each morning and evening as instructed. She also reviewed my fluid intake, which I "
            "had been restricting to manage symptoms — counterproductively, she explained. "
            "Making that simple change has already shown some improvement. My son joined me for "
            "the second appointment, which helped me remember the advice given."
        ),
        "Month 3 — April (Early Improvements)": (
            "Three months in and the frequency of episodes has reduced noticeably. I have not "
            "had a significant accident in three weeks, which is the longest stretch since this "
            "began. Nurse Skelton emailed christopher.skelton@gmail.com a questionnaire about "
            "my progress and he helped me complete it. I have also been using the accessible "
            "toilet on the ground floor of the clinic — could you please ensure it remains "
            "unlocked during clinic hours as it was unavailable at my last appointment."
        ),
        "Month 4 — May (Gaining Confidence)": (
            "I managed a two-hour bus journey to visit my sister in Chermside last week — "
            "something I had not attempted in over a year because of my continence concerns. "
            "I felt confident and managed without any difficulty. The combination of the pelvic "
            "floor exercises and the adjusted fluid intake has made a significant practical "
            "difference to my daily life. Nurse Skelton has suggested I reduce to monthly "
            "check-ins from fortnightly, which feels like a milestone."
        ),
        "Month 5 — June (Restored Independence)": (
            "I attended my local garden club meeting last Thursday, which I had not felt able to "
            "do in over eighteen months. Being able to sit through a two-hour gathering without "
            "anxiety has restored a social confidence I thought I had lost. Nurse Skelton's "
            "monthly updates to christopher.skelton@gmail.com keep us both informed. "
            "I have now mastered the pelvic floor exercises completely and do them automatically "
            "as part of my morning routine. I am going to continue attending the clinic for "
            "my six-month review."
        ),
        "Month 6 — July (Discharge & Gratitude)": (
            "My six-month review confirmed my continence has improved substantially and I now "
            "qualify to be discharged to self-management with an annual check-in. Nurse Skelton "
            "was warm and thorough in our final structured session and gave me written guidance "
            "for what to do if symptoms recur. I live independently at 12 Coronation Drive, "
            "Nundah, and at 76 I intend to remain independent for as long as possible. "
            "The support from this clinic, and from my son Christopher, has made that "
            "ambition feel realistic again."
        ),
        "Month 7 — August (Self-Managing)": (
            "It has been one month since I was discharged to self-management and the transition "
            "has been smooth. I have had no significant episodes since before my discharge and "
            "my daily routine — including the exercises and fluid management — is established. "
            "My son Christopher has been calling twice a week, which I appreciate even though "
            "I do not need the practical support I needed earlier in the year."
        ),
        "Month 8 — September (Travelling)": (
            "I made an overnight trip to visit my daughter in Ipswich last weekend — the first "
            "time I have stayed away from home overnight in over two years. I packed Nurse "
            "Skelton's written guidance notes and had no difficulties throughout the entire visit. "
            "My daughter commented that I seemed relaxed and happy in a way I had not been in a "
            "long time. The clinic returned something I had stopped noticing I had lost."
        ),
        "Month 9 — October (Minor Setback Managed)": (
            "I had a brief recurrence of symptoms during a week of unusually hot weather — "
            "I had not been drinking enough fluid and the dehydration triggered some urgency. "
            "I referred to Nurse Skelton's written guidance, increased my fluid intake, and "
            "returned to the pelvic floor programme at full intensity for a week. The symptoms "
            "resolved within five days without any clinic contact."
        ),
        "Month 10 — November (Social Engagement)": (
            "I have been fully socially active this quarter in ways I had not been for over two years. "
            "I attend garden club weekly, the book group at the Nundah library fortnightly, and I "
            "hosted a morning tea at 12 Coronation Drive last month for the first time in years. "
            "Christopher confirmed my annual check-in appointment has been booked for January "
            "at christopher.skelton@gmail.com."
        ),
        "Month 11 — December (Christmas Plans)": (
            "I am hosting Christmas this year — something I had not done since my continence "
            "symptoms became significant two years ago. All three of my children and seven "
            "grandchildren are coming to 12 Coronation Drive, Nundah. Nurse Skelton gave me back "
            "more than just physical function — she gave me the confidence to participate in "
            "my own life again."
        ),
        "Month 12 — January (Annual Check-in)": (
            "I attended my annual check-in at the continence clinic last week. Nurse Margaret "
            "Skelton reviewed my self-monitoring diary and confirmed that my continence function "
            "is well-maintained with no indicators of deterioration. I told her how Christmas went "
            "and she laughed warmly. I am 77 now, living independently at 12 Coronation Drive, "
            "Nundah QLD 4012, and in better health than I was at 74. That is something to celebrate."
        ),
    },
    "Patient O — Post-Surgical Recovery (Inter-Hospital Transfer)": {
        "Month 1 — March (Surgery & Transfer)": (
            "I had surgery at Logan Hospital on 2 March 2026 and was transferred to this "
            "facility two days post-operatively for ongoing care. The handover was difficult — "
            "when I arrived my medication list was not updated correctly and I was nearly given "
            "a medication I had already been switched from. I recognised the error myself and "
            "raised it with the ward nurse. My husband David Tran stayed through the admission "
            "process and helped flag the discrepancy. I also received an SMS from 0437 123 456 "
            "asking me to complete a survey, but the link did not work on my phone."
        ),
        "Month 2 — April (Discharge)": (
            "I was discharged home in mid-April after a longer stay than expected due to a wound "
            "healing complication. The discharge process was better coordinated than the admission "
            "— my medications were checked and reconciled by a pharmacist before I left. David "
            "helped me set up my recovery space at home. Our GP received a clear discharge summary "
            "within 24 hours, which I confirmed when I called the practice. "
            "I am fatigued but relieved to be home."
        ),
        "Month 3 — May (Home Recovery)": (
            "Recovery at home has been slow but steady. My surgical wound has healed well and "
            "I no longer need the district nurse to visit. David has been managing most of the "
            "household responsibilities and his support has been crucial. I submitted the survey "
            "via his iPhone after the Zedoc link didn't work on my Samsung. The SMS from "
            "0437 123 456 used no clinic name, which initially worried me it was spam. "
            "A clearer sender identity for survey messages would help patients trust the process."
        ),
        "Month 4 — June (Medication Resolved)": (
            "I attended a follow-up with my GP this month and we reviewed my complete medication "
            "list together. The error that occurred at the time of my transfer from Logan Hospital "
            "has been fully resolved and my GP has updated my MyHealthRecord accordingly. "
            "The incident was reported to the hospital patient safety team, which was the right "
            "outcome. I feel confident that my current medication regime is correct. David drove "
            "me and stayed for the discussion, which helped us both feel informed."
        ),
        "Month 5 — July (Improving)": (
            "My energy has improved significantly this month and I managed a short return "
            "to my usual routine last week. The post-surgical fatigue has mostly lifted and I "
            "can manage a full day independently without needing to rest. David says I seem "
            "much more like myself again. I have been reflecting on my experience since March "
            "and while there were significant system failures at the handover, the care I received "
            "once things were stabilised has been genuinely good."
        ),
        "Month 6 — August (Fully Recovered)": (
            "I am fully recovered and returned to work on reduced hours last week. The medication "
            "error from the Logan Hospital transfer has stayed with me as a reminder of how "
            "important it is for patients to be active participants in their own care. David "
            "has been extraordinary throughout this process. I hope the incident feedback has "
            "contributed to an improved transfer protocol between Logan Hospital and this service. "
            "I feel well. That is what matters most."
        ),
        "Month 7 — September (Work Return)": (
            "I returned to work full-time this month and was welcomed back warmly. The post-surgical "
            "fatigue is behind me and I am managing a full workday without difficulty. My husband "
            "David Tran has gradually returned to his own schedule after months of carrying most of "
            "our household responsibilities. I have maintained contact with my GP to ensure my "
            "medication list continues to be accurately recorded after the Logan Hospital error."
        ),
        "Month 8 — October (Patient Safety Advocacy)": (
            "I was contacted by the hospital's patient safety team following up on the medication "
            "error at my transfer from Logan Hospital on 2 March 2026. They asked if I would be "
            "willing to participate in a patient experience interview to inform a new inter-hospital "
            "medication reconciliation protocol. I agreed immediately. David supported me in "
            "preparing for the conversation."
        ),
        "Month 9 — November (Interview Completed)": (
            "The patient safety interview was completed this month and I found it genuinely "
            "cathartic. Describing what happened clearly and having it heard seriously was more "
            "meaningful than I anticipated. The clinician explained that a new protocol requiring "
            "pharmacist sign-off for all transfers is already in pilot. The Zedoc survey link "
            "issue from the SMS sent to my Samsung from 0437 123 456 was also noted."
        ),
        "Month 10 — December (Back to Full Health)": (
            "David and I are ending the year in good health and good spirits. My recovery from "
            "surgery is complete, the medication error from the Logan Hospital transfer is fully "
            "resolved, and my GP has confirmed my records are accurate. We had a quiet Christmas "
            "at home — a deliberate choice after a year of medical uncertainty. "
            "I feel deep gratitude for the clinical care that was provided once the handover issues were resolved."
        ),
        "Month 11 — January (Follow-up Survey)": (
            "The patient safety team sent a follow-up survey to check on my wellbeing after the "
            "medication error incident. I completed it promptly. I noted that the SMS survey from "
            "0437 123 456 still does not identify itself as coming from the hospital. David helped "
            "me complete the online portion, which this time worked correctly on both our phones. "
            "Progress, if small."
        ),
        "Month 12 — February (One Year On)": (
            "It is almost exactly one year since my surgery at Logan Hospital on 2 March 2026. "
            "I am fully recovered, back at work, and actively engaged in improving the system that "
            "failed me. David has been magnificent. The clinicians who corrected the errors gave me "
            "back my health. The safety team who took my feedback seriously gave me back my "
            "confidence in the system. I am grateful for both."
        ),
    },
    "Patient P — Cardiac Rehabilitation": {
        "Month 1 — January (Cardiac Event)": (
            "I suffered a significant cardiac event in early January 2026. The cardiac team's "
            "response was swift and professional — I was in the catheterisation lab within ninety "
            "minutes of arriving. Dr Richardson coordinated my care from the acute phase and has "
            "remained my primary cardiologist. My cardiologist at the Prince Charles Hospital, "
            "Dr Andrew Walsh, was contacted immediately and the two doctors spoke directly about "
            "my management plan. I am 68 years old and this event has changed my perspective "
            "on almost everything."
        ),
        "Month 2 — February (Rehab Starts)": (
            "I commenced the cardiac rehabilitation program in February and the team has been "
            "exceptional. The physiotherapist is knowledgeable and the exercise sessions are "
            "appropriately paced. Dr Richardson called me at home on 0478 234 567 to discuss "
            "my stress test results before my next outpatient appointment, which I did not expect "
            "but found deeply reassuring. That kind of proactive communication is genuinely rare. "
            "The coordination between Dr Richardson and Dr Andrew Walsh at Prince Charles "
            "is seamless."
        ),
        "Month 3 — March (Progress & Accessibility Issue)": (
            "The rehabilitation program is going well and my exercise tolerance is measurably "
            "improving. However, I struggled to find a disabled parking bay on 20 March 2026 — "
            "I hold a temporary mobility permit after my cardiac event and the spaces allocated "
            "near the clinic entrance are insufficient. I had to park significantly further away, "
            "which was difficult given my current limitations. I raised this at my next appointment "
            "and was told it has been flagged before. Please address this as a patient safety issue."
        ),
        "Month 4 — April (Improving Fitness)": (
            "My cardiac rehab assessment showed a meaningful improvement in exercise capacity "
            "and my resting heart rate has stabilised in the target range. I have been walking "
            "forty minutes daily without symptoms and my blood pressure readings are consistently "
            "within goal. Dr Richardson used the phrase 'very good recovery trajectory' which I "
            "have repeated to my wife at least twice a week since. The parking issue in March "
            "has not recurred — it appears the bay allocation was adjusted."
        ),
        "Month 5 — May (Gaining Confidence)": (
            "I returned to light gardening this month, which I had been told to avoid since January. "
            "The cardiac rehab physiotherapist cleared me for moderate activity and the confidence "
            "that clearance gave me was enormous. I attended my grandson's school concert last week — "
            "a meaningful test of my progress that I passed comfortably. Dr Walsh and Dr Richardson "
            "remain in close contact about my ongoing management. The dual-specialist coordination "
            "has removed the anxiety I used to feel about receiving conflicting advice."
        ),
        "Month 6 — June (Back to Full Life)": (
            "My six-month cardiac review confirms I have made an excellent recovery. Dr Richardson "
            "was thorough and encouraging. He and Dr Andrew Walsh have agreed on a maintenance plan "
            "involving annual reviews and continued medication management. I walked five kilometres "
            "last Saturday without any discomfort or symptoms, which felt impossible six months ago. "
            "The proactive phone call from Dr Richardson in February — to 0478 234 567 — remains "
            "the single moment that gave me the most confidence my care team was truly paying "
            "attention. I am grateful to be well."
        ),
        "Month 7 — July (Summer Activity)": (
            "Summer arrived and I navigate it carefully — the heat can be a trigger for cardiac "
            "symptoms and Dr Richardson advised me to exercise in the early morning. I have settled "
            "into a 6am walking routine that has become one of the best parts of my day. "
            "Dr Andrew Walsh at the Prince Charles Hospital reviewed my most recent ECG and "
            "forwarded his assessment directly to Dr Richardson — the dual-specialist communication "
            "continues seamlessly."
        ),
        "Month 8 — August (Charity Walk)": (
            "I completed a five-kilometre charity walk in aid of the Heart Foundation last weekend "
            "with my son and two grandchildren. Seven months ago I was admitted with a significant "
            "cardiac event. This morning I walked five kilometres in the winter sunshine and crossed "
            "the finish line with two eight-year-olds pulling my hands. Dr Richardson had approved "
            "the walk at my last appointment and I stayed well below the heart rate threshold."
        ),
        "Month 9 — September (Excellent Review)": (
            "My nine-month cardiac review was completed and Dr Richardson described the results as "
            "'better than projected at the time of the event'. My ejection fraction has improved "
            "and my stress test performance exceeds the benchmark for my age group. He called me "
            "at home on 0478 234 567 to discuss the results in detail before sending the written "
            "summary — the same thoughtful approach that has characterised his care from the beginning."
        ),
        "Month 10 — October (Parking Improvement)": (
            "I attended my October review and noted with satisfaction that there are now four clearly "
            "marked disabled bays near the clinic entrance, up from two. I asked at reception whether "
            "this was a result of patient feedback and was told it had been. My temporary mobility "
            "permit has been reviewed and may be transitioned to a permanent permit given my "
            "ongoing cardiac monitoring."
        ),
        "Month 11 — November (Life Fully Resumed)": (
            "I attended my grandson's school graduation, watched my daughter's birthday dinner, "
            "and travelled to the Gold Coast for a weekend with my wife — all in November. Each of "
            "those things felt impossible in January. Dr Richardson's proactive phone calls and "
            "Dr Walsh's attentive monitoring have given me back a life that briefly felt very uncertain. "
            "I am 68 years old and I intend to have a great many more Novembers."
        ),
        "Month 12 — December (Year Closes Strongly)": (
            "One year ago I nearly died. Today I am healthy, active, and planning a holiday to "
            "New Zealand with my wife in March. Dr Richardson has scheduled my annual review for "
            "January and Dr Andrew Walsh has confirmed our six-monthly coordination call for February. "
            "The proactive phone call on 0478 234 567 in February remains the most memorable moment "
            "of my medical care this year. I am deeply grateful. And I am well."
        ),
    },
}

PATIENT_NAMES = list(PATIENT_SAMPLES.keys())

MODEL_CHOICES = list(MODEL_LABEL_TO_TYPE.keys())

SENTIMENT_COLORS = {
    "POSITIVE": "#27ae60",
    "NEGATIVE": "#e74c3c",
    "NEUTRAL":  "#f39c12",
    "ANGER":    "#e74c3c",
    "DISGUST":  "#e74c3c",
    "FEAR":     "#e74c3c",
    "SADNESS":  "#e74c3c",
    "JOY":      "#27ae60",
    "SURPRISE": "#27ae60",
    # Star-rating model (BERT Multilingual)
    "1 STAR":   "#8B0000",
    "2 STARS":  "#e74c3c",
    "3 STARS":  "#f39c12",
    "4 STARS":  "#27ae60",
    "5 STARS":  "#1B5E20",
}

EMOTION_EMOJI = {
    "ANGER":    "🤬",
    "DISGUST":  "🤢",
    "FEAR":     "😨",
    "JOY":      "😀",
    "NEUTRAL":  "😐",
    "SADNESS":  "😭",
    "SURPRISE": "😲",
}

# ── Sentiment colormap: dark-red → yellow → blue → dark-green ────────────────
_SENTIMENT_CMAP = LinearSegmentedColormap.from_list(
    "sentiment",
    [(0.00, "#8B0000"), (0.33, "#FFD700"), (0.67, "#1565C0"), (1.00, "#1B5E20")],
)

# Score in [0, 1] for each sentiment category (0 = most negative, 1 = most positive)
_CATEGORY_SCORE = {
    "negative": 0.00,
    "anger":    0.04,
    "disgust":  0.08,
    "fear":     0.12,
    "sadness":  0.18,
    "neutral":  0.50,
    "surprise": 0.65,
    "joy":      0.92,
    "positive": 1.00,
}

# ── Time-series helpers ───────────────────────────────────────────────────────

def _parse_month_sections(text):
    """Split text on [label] headers → [(label, body), ...]."""
    parts = re.split(r'\[([^\]]+)\]', text.strip())
    sections = []
    for i in range(1, len(parts) - 1, 2):
        label = parts[i].strip()
        body  = parts[i + 1].strip()
        if body:
            sections.append((label, body))
    return sections


def _ts_line_chart(months, scores_by_label, model_label):
    """Multi-line score chart per label + polynomial forecast for 2 future months."""
    fig = go.Figure()
    _fallback_colors = ["#f39c12", "#8e44ad", "#16a085", "#d35400", "#2563eb"]
    x = np.arange(len(months))

    for idx, (label, scores) in enumerate(scores_by_label.items()):
        color = SENTIMENT_COLORS.get(label.upper(),
                                     _fallback_colors[idx % len(_fallback_colors)])
        fig.add_trace(go.Scatter(
            x=months, y=scores, mode="lines+markers",
            name=label, line=dict(color=color, width=2.5),
            marker=dict(size=8),
        ))
        if len(scores) >= 2:
            deg = min(2, len(scores) - 1)
            coeffs = np.polyfit(x, scores, deg)
            poly = np.poly1d(coeffs)
            x_fut = np.arange(len(months), len(months) + 2)
            y_fut = list(np.clip(poly(x_fut), 0.0, 1.0))
            fut_labels = [f"Forecast +{i+1}" for i in range(2)]
            fig.add_trace(go.Scatter(
                x=months + fut_labels, y=list(scores) + y_fut,
                mode="lines", name=f"{label} (forecast)",
                line=dict(color=color, width=1.5, dash="dot"),
                showlegend=True,
            ))

    if len(months) > 0:
        fig.add_vline(
            x=len(months) - 0.5,
            line=dict(color="#6b7280", width=1, dash="dash"),
            annotation_text="forecast →",
            annotation_position="top right",
        )

    fig.update_layout(
        title=dict(text=f"Sentiment Score Timeline — {model_label}",
                   font=dict(size=18, color="#000", family="Arial Black, Arial")),
        xaxis=dict(title="Month", tickangle=-30),
        yaxis=dict(title="Probability", range=[0, 1.05]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="#f8fafc", paper_bgcolor="#ffffff",
        margin=dict(t=80, b=60),
        height=420,
    )
    return fig


def _ts_category_chart(months, dominant_labels):
    """Colored bar showing dominant sentiment label per month."""
    colors = [SENTIMENT_COLORS.get(l.upper(), "#7f8c8d") for l in dominant_labels]
    fig = go.Figure(go.Bar(
        x=months, y=[1] * len(months),
        marker_color=colors,
        text=dominant_labels,
        textposition="inside",
        textfont=dict(size=13, color="#ffffff", family="Arial Black, Arial"),
    ))
    fig.update_layout(
        title=dict(text="Dominant Sentiment per Month",
                   font=dict(size=18, color="#000", family="Arial Black, Arial")),
        xaxis=dict(title="Month", tickangle=-30),
        yaxis=dict(visible=False),
        plot_bgcolor="#f8fafc", paper_bgcolor="#ffffff",
        margin=dict(t=80, b=60),
        height=280,
    )
    return fig


def _ts_delta_chart(months, primary_scores):
    """Month-over-month change in primary sentiment score."""
    if len(primary_scores) < 2:
        return None
    deltas = [round(primary_scores[i] - primary_scores[i-1], 4)
              for i in range(1, len(primary_scores))]
    delta_months = months[1:]
    bar_colors = ["#27ae60" if d >= 0 else "#e74c3c" for d in deltas]
    fig = go.Figure(go.Bar(
        x=delta_months, y=deltas,
        marker_color=bar_colors,
        text=[f"{d:+.1%}" for d in deltas],
        textposition="outside",
        textfont=dict(size=11, color="#000", family="Arial Black, Arial"),
    ))
    fig.add_hline(y=0, line=dict(color="#6b7280", width=1))
    fig.update_layout(
        title=dict(text="Month-over-Month Sentiment Change",
                   font=dict(size=18, color="#000", family="Arial Black, Arial")),
        xaxis=dict(title="Month", tickangle=-30),
        yaxis=dict(title="Δ Score", tickformat=".0%"),
        plot_bgcolor="#f8fafc", paper_bgcolor="#ffffff",
        margin=dict(t=80, b=60),
        height=320,
    )
    return fig


def _build_ts_html_report(sections, months, scores_by_label, dominant_labels,
                          model_label, line_fig, cat_fig, delta_fig):
    """Generate a self-contained HTML report for a time-series sentiment analysis."""
    import base64, html as _html, tempfile
    from datetime import datetime

    now      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    labels   = list(scores_by_label.keys())

    def _esc(s):
        return _html.escape(str(s))

    def _fig_div(fig):
        return fig.to_html(full_html=False, include_plotlyjs=False) if fig else ""

    line_div  = _fig_div(line_fig)
    cat_div   = _fig_div(cat_fig)
    delta_div = _fig_div(delta_fig) if delta_fig else ""

    # ── Score table ──────────────────────────────────────────────────────────
    header_cols = "".join(f"<th>{_esc(l)}</th>" for l in labels)
    score_rows  = ""
    for i, (m, d) in enumerate(zip(months, dominant_labels)):
        color      = SENTIMENT_COLORS.get(d.upper(), "#555")
        score_cols = "".join(
            f"<td class='num'>{scores_by_label[l][i]:.1%}</td>" for l in labels
        )
        score_rows += (
            f"<tr><td>{_esc(m)}</td>"
            f"<td><b style='color:{color}'>{_esc(d)}</b></td>"
            f"{score_cols}</tr>"
        )

    # ── Month text sections ──────────────────────────────────────────────────
    month_sections_html = ""
    for month_label, body in sections:
        month_sections_html += (
            f"<div class='month-block'>"
            f"<div class='month-title'>{_esc(month_label)}</div>"
            f"<p class='month-body'>{_esc(body)}</p>"
            f"</div>"
        )

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Time-Series Sentiment Report — {_esc(model_label)}</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#f4f6f9;color:#1a1a2e;padding:32px 20px}}
  .container{{max-width:1100px;margin:0 auto;background:#fff;border-radius:12px;
              box-shadow:0 4px 24px rgba(0,0,0,.1);overflow:hidden}}
  .header{{background:linear-gradient(135deg,#1e3a5f,#2563eb);color:#fff;padding:36px 40px}}
  .header h1{{font-size:1.7rem;font-weight:700;margin-bottom:6px}}
  .header .meta{{font-size:0.88rem;opacity:.85;margin-top:4px}}
  .badge{{display:inline-block;background:rgba(255,255,255,.18);border-radius:20px;
          padding:3px 14px;font-size:0.8rem;margin-top:10px}}
  .body{{padding:36px 40px}}
  h2{{font-size:1.15rem;font-weight:700;color:#1e3a5f;margin:32px 0 14px;
      border-left:4px solid #2563eb;padding-left:12px}}
  h2:first-of-type{{margin-top:0}}
  .chart-wrap{{background:#f8fafc;border-radius:8px;padding:12px;margin-bottom:8px}}
  table{{width:100%;border-collapse:collapse;font-size:0.88rem;margin-top:4px}}
  thead tr{{background:#1e3a5f;color:#fff}}
  th,td{{padding:8px 12px;text-align:left}}
  tbody tr:nth-child(even){{background:#f0f4ff}}
  .num{{text-align:right;font-variant-numeric:tabular-nums}}
  .month-block{{background:#f8fafc;border-left:4px solid #2563eb;border-radius:6px;
                padding:14px 18px;margin-bottom:12px}}
  .month-title{{font-weight:700;color:#1e3a5f;margin-bottom:6px;font-size:0.92rem}}
  .month-body{{font-size:0.87rem;color:#374151;line-height:1.6;white-space:pre-wrap}}
  .footer{{text-align:center;font-size:0.78rem;color:#9ca3af;
           border-top:1px solid #e5e7eb;padding:18px 40px}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>Time-Series &amp; Forecast Report</h1>
    <div class="meta">Model: <b>{_esc(model_label)}</b> &nbsp;|&nbsp; Generated: {now}</div>
    <div class="meta">Months analysed: <b>{len(months)}</b> &nbsp;|&nbsp;
      Forecast: <b>+2 months (polynomial extrapolation)</b></div>
    <span class="badge">HIPAA-aware · PII redacted before inference</span>
  </div>

  <div class="body">

    <h2>Sentiment Score Timeline &amp; Forecast</h2>
    <div class="chart-wrap">{line_div}</div>

    <h2>Dominant Sentiment per Month</h2>
    <div class="chart-wrap">{cat_div}</div>

    {"<h2>Month-over-Month Change</h2><div class='chart-wrap'>" + delta_div + "</div>" if delta_div else ""}

    <h2>Score Summary Table</h2>
    <table>
      <thead><tr><th>Month</th><th>Dominant</th>{header_cols}</tr></thead>
      <tbody>{score_rows}</tbody>
    </table>

    <h2>Source Text (by Month)</h2>
    {month_sections_html}

  </div>
  <div class="footer">
    HIPAA-Aware Time-Series Sentiment Forecasting (1pMq) &nbsp;·&nbsp; {now}
  </div>
</div>
</body>
</html>"""

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8",
        prefix="ts_sentiment_report_",
    )
    tmp.write(html_out)
    tmp.close()
    return tmp.name


def run_timeseries(text_input, model_label):
    """Parse month sections and run per-month sentiment inference."""
    import traceback

    def _err(msg):
        html = f"<p style='color:#e74c3c;font-weight:600;'>{msg}</p>"
        return None, None, None, html, None

    try:
        sections = _parse_month_sections(text_input or "")
        if len(sections) < 2:
            return _err(
                "Please load at least 2 months of text using the patient / month "
                "selectors above, then click <b>Run Time-Series Analysis</b>."
            )

        model_type = MODEL_LABEL_TO_TYPE.get(model_label, ModelType.DEFAULT)
        config     = SUPPORTED_MODELS[model_type]
        labels     = config["labels"]

        months, scores_by_label, dominant_labels = [], {l: [] for l in labels}, []

        for month_label, body in sections:
            redacted, _ = redact_pii(body)
            _, probs = analyze_sentiment(redacted, model_type)
            while len(probs) < len(labels):
                probs.append(0.0)
            months.append(month_label)
            dominant_labels.append(labels[int(np.argmax(probs))])
            for lbl, p in zip(labels, probs):
                scores_by_label[lbl].append(round(p, 4))

        primary_label  = labels[0]
        primary_scores = scores_by_label[primary_label]

        line_fig  = _ts_line_chart(months, scores_by_label, model_label)
        cat_fig   = _ts_category_chart(months, dominant_labels)
        delta_fig = _ts_delta_chart(months, primary_scores)

        def _score_cell(i):
            return "  ".join(
                f"{lbl}: {scores_by_label[lbl][i]:.1%}" for lbl in labels
            )

        def _row(i, m, d):
            color = SENTIMENT_COLORS.get(d.upper(), "#555")
            return (
                f"<tr>"
                f"<td style='padding:5px 10px;'>{m}</td>"
                f"<td style='padding:5px 10px;'><b style='color:{color}'>{d}</b></td>"
                f"<td style='padding:5px 10px;font-size:0.82rem;'>{_score_cell(i)}</td>"
                f"</tr>"
            )

        rows = "".join(
            _row(i, m, d)
            for i, (m, d) in enumerate(zip(months, dominant_labels))
        )
        summary_html = (
            f"<div style='font-family:sans-serif;margin-top:8px;'>"
            f"<b>Model:</b> {model_label} &nbsp;|&nbsp; "
            f"<b>Months analysed:</b> {len(months)}<br>"
            f"<table style='border-collapse:collapse;width:100%;margin-top:8px;font-size:0.88rem;'>"
            f"<thead><tr style='background:#1e3a5f;color:#fff;'>"
            f"<th style='padding:6px 10px;'>Month</th>"
            f"<th style='padding:6px 10px;'>Dominant</th>"
            f"<th style='padding:6px 10px;'>All scores</th>"
            f"</tr></thead><tbody>{rows}</tbody></table></div>"
        )

        html_path = _build_ts_html_report(
            sections, months, scores_by_label, dominant_labels,
            model_label, line_fig, cat_fig, delta_fig,
        )
        return line_fig, cat_fig, delta_fig, summary_html, html_path

    except Exception as exc:
        return _err(f"Time-series error: {exc}<br><pre>{traceback.format_exc()}</pre>")


# ── Chart helpers ─────────────────────────────────────────────────────────────

def _prob_chart(probabilities, labels, display_labels=None):
    if display_labels is None:
        display_labels = labels
    colors = [SENTIMENT_COLORS.get(l, "#95a5a6") for l in labels]
    fig = go.Figure(go.Bar(
        x=probabilities,
        y=display_labels,
        orientation="h",
        marker_color=colors,
        text=[f"{p:.1%}" for p in probabilities],
        textposition="outside",
        textfont=dict(size=11, color="#000000", family="Arial Black, Arial, sans-serif"),
    ))
    fig.update_layout(
        title=dict(text="Prediction Confidence", font=dict(size=20, color="#000000", family="Arial Black, Arial, sans-serif")),
        xaxis=dict(
            title=dict(text="Confidence", standoff=12),
            range=[0, 1.25], tickformat=".0%",
        ),
        height=max(240, len(labels) * 58),
        margin=dict(l=20, r=60, t=55, b=50),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(size=13, color="#000000", family="Arial Black, Arial, sans-serif"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(0,0,0,0.12)")
    return fig


def _wordcloud_fig(text, word_dist=None):
    # Build word → score mapping from the distribution
    word_score: dict = {}
    if word_dist:
        for category, words in word_dist.word_lists.items():
            score = _CATEGORY_SCORE.get(category.lower(), 0.5)
            for word in words:
                word_score[word.lower()] = score

    def _color_func(word, font_size, position, orientation, random_state=None, **kwargs):
        score = word_score.get(word.lower(), 0.5)
        r, g, b, _ = _SENTIMENT_CMAP(score)
        return f"rgb({int(r * 255)}, {int(g * 255)}, {int(b * 255)})"

    wc_obj = WordCloud(
        width=900, height=360, background_color="white",
        color_func=_color_func, max_words=100,
    ).generate(text)

    fig, (ax_wc, ax_cb) = plt.subplots(
        2, 1, figsize=(9, 4.4),
        gridspec_kw={"height_ratios": [10, 1]},
    )
    ax_wc.imshow(wc_obj, interpolation="bilinear")
    ax_wc.axis("off")

    # Colorbar legend
    gradient = np.linspace(0, 1, 256).reshape(1, -1)
    ax_cb.imshow(gradient, aspect="auto", cmap=_SENTIMENT_CMAP)
    ax_cb.set_xticks([0, 85, 170, 255])
    ax_cb.set_xticklabels(["Most Negative", "Neutral", "Positive", "Most Positive"], fontsize=8)
    ax_cb.set_yticks([])
    ax_cb.spines[:].set_visible(False)

    plt.tight_layout(pad=0.5)
    return fig


def _dist_chart(distribution, display_labels=None):
    labels = [k.upper() for k in distribution]
    if display_labels is None:
        display_labels = labels
    values = list(distribution.values())
    colors = [SENTIMENT_COLORS.get(l, "#95a5a6") for l in labels]
    fig = go.Figure(go.Bar(
        x=display_labels,
        y=values,
        marker_color=colors,
        text=values,
        textposition="outside",
        textfont=dict(size=11, color="#000000", family="Arial Black, Arial, sans-serif"),
    ))
    fig.update_layout(
        title=dict(text="Per-word Sentiment Distribution", font=dict(size=20, color="#000000", family="Arial Black, Arial, sans-serif")),
        yaxis=dict(title=dict(text="Word count", standoff=12), range=[0, max(values) + 5]),
        xaxis=dict(title=dict(text="", standoff=12)),
        height=370,
        margin=dict(l=60, r=40, t=55, b=90),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(size=13, color="#000000", family="Arial Black, Arial, sans-serif"),
    )
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.12)")
    return fig


# ── Token chip renderer ───────────────────────────────────────────────────────

def _tokens_html(words, info=""):
    chips = "".join(
        f'<span style="background:#0d2680;color:#ffffff;border-radius:50px;'
        f'padding:4px 14px;font-size:0.82rem;display:inline-block;'
        f'margin:3px 2px;white-space:nowrap;">{word}</span>'
        for word in words
    )
    return f'<div style="display:flex;flex-wrap:wrap;gap:2px;padding:4px 0;">{chips}</div>'


# ── Report builder ────────────────────────────────────────────────────────────

def _fig_to_png_bytes(fig):
    """Return a BytesIO PNG of a matplotlib or Plotly figure, or None if fig is None."""
    if fig is None:
        return None
    from io import BytesIO
    if hasattr(fig, "to_image"):  # Plotly figure
        return BytesIO(fig.to_image(format="png", width=900, height=400, scale=1.5))
    buf = BytesIO()             # Matplotlib figure
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    buf.seek(0)
    return buf


def _build_pdf_report(text, sentiment, model_label, probabilities, labels, preprocess, word_dist, prob_fig, wc_fig, dist_fig):
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image as RLImage, HRFlowable,
    )

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        rightMargin=0.75 * inch, leftMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()

    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=18, spaceAfter=4, alignment=TA_CENTER)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12, spaceBefore=12, spaceAfter=4,
                        textColor=colors.HexColor("#2c3e50"))
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9, leading=14)
    mono = ParagraphStyle("mono", parent=styles["Code"], fontSize=8, leading=12, leftIndent=12)
    caption = ParagraphStyle("caption", parent=styles["Normal"], fontSize=8, textColor=colors.gray, alignment=TA_CENTER)

    def section(title):
        return [
            Spacer(1, 6),
            Paragraph(title, h2),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#bdc3c7"), spaceAfter=4),
        ]

    story = []

    # ── Title ──────────────────────────────────────────────────────────────────
    story.append(Paragraph("NLP Sentiment Analysis Report", h1))
    story.append(Spacer(1, 4))
    from datetime import datetime
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", caption))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2980b9"), spaceAfter=10))

    # ── Summary table ──────────────────────────────────────────────────────────
    story += section("Summary")
    sent_color = colors.HexColor(SENTIMENT_COLORS.get(sentiment, "#7f8c8d"))
    conf_str = "  |  ".join(f"{l}: {p:.1%}" for l, p in zip(labels, probabilities))
    table_data = [
        [Paragraph("<b>Model</b>", body), Paragraph(model_label, body)],
        [Paragraph("<b>Sentiment</b>", body),
         Paragraph(f'<font color="{SENTIMENT_COLORS.get(sentiment, "#7f8c8d")}"><b>{sentiment}</b></font>', body)],
        [Paragraph("<b>Confidence</b>", body), Paragraph(conf_str, body)],
    ]
    tbl = Table(table_data, colWidths=[1.4 * inch, 5.5 * inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ecf0f1")),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#bdc3c7")),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(tbl)

    # ── Original text ──────────────────────────────────────────────────────────
    story += section("Original Text")
    story.append(Paragraph(text.replace("\n", "<br/>"), body))

    # ── Preprocessing ──────────────────────────────────────────────────────────
    story += section("Preprocessing Pipeline")
    preproc_rows = [
        ("Cleaned",    preprocess.cleaned_text),
        ("Removed",    preprocess.removed_text),
        ("Normalized", preprocess.normalized_text),
        ("Tokenized",  ", ".join(preprocess.tokenized_text)),
        ("Stemmed",    " ".join(preprocess.stemmed_text)),
        ("Lemmatized", " ".join(preprocess.lemmatized_text)),
        ("Word count", str(len(preprocess.tokenized_text))),
    ]
    pre_data = [[Paragraph(f"<b>{k}</b>", body), Paragraph(v, mono)] for k, v in preproc_rows]
    pre_tbl = Table(pre_data, colWidths=[1.1 * inch, 5.8 * inch])
    pre_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8f9fa")),
        ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#dee2e6")),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(pre_tbl)

    # ── Charts ────────────────────────────────────────────────────────────────
    usable_width = doc.width  # points between margins

    story += section("Charts")
    for fig, title in [(prob_fig, "Confidence Scores"), (wc_fig, "Word Cloud"), (dist_fig, "Per-word Distribution")]:
        img_bytes = _fig_to_png_bytes(fig)
        if img_bytes:
            img = RLImage(img_bytes, width=usable_width, height=usable_width * 0.42)
            story.append(img)
            story.append(Paragraph(title, caption))
            story.append(Spacer(1, 8))

    # ── NER ───────────────────────────────────────────────────────────────────
    story += section("Named Entities (NER)")
    if preprocess.ner:
        ner_data = [[Paragraph("<b>Entity</b>", body), Paragraph("<b>Label</b>", body)]]
        ner_data += [[Paragraph(e[0], mono), Paragraph(e[1], body)] for e in preprocess.ner]
        ner_tbl = Table(ner_data, colWidths=[3.35 * inch, 3.55 * inch])
        ner_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2980b9")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#bdc3c7")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(ner_tbl)
    else:
        story.append(Paragraph("No named entities found.", body))

    # ── POS tags ──────────────────────────────────────────────────────────────
    story += section("POS Tags")
    if preprocess.pos:
        pos_data = [[Paragraph("<b>Word</b>", body), Paragraph("<b>POS</b>", body)]]
        pos_data += [[Paragraph(w, mono), Paragraph(t, body)] for w, t in preprocess.pos]
        pos_tbl = Table(pos_data, colWidths=[3.35 * inch, 3.55 * inch])
        pos_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#27ae60")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#bdc3c7")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(pos_tbl)
    else:
        story.append(Paragraph("No POS tags available.", body))

    # ── Word distribution ─────────────────────────────────────────────────────
    story += section("Word-level Distribution")
    dist_data = [[Paragraph("<b>Category</b>", body), Paragraph("<b>Count</b>", body), Paragraph("<b>Words</b>", body)]]
    for label, words in word_dist.word_lists.items():
        dist_data.append([
            Paragraph(label.upper(), body),
            Paragraph(str(len(words)), body),
            Paragraph(", ".join(words) or "—", mono),
        ])
    dist_tbl = Table(dist_data, colWidths=[1.2 * inch, 0.7 * inch, 5.0 * inch])
    dist_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8e44ad")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#bdc3c7")),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(dist_tbl)

    doc.build(story)
    buf.seek(0)

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(buf.read())
    tmp.close()
    return tmp.name


def _build_html_report(text, sentiment, model_label, probabilities, labels, preprocess, word_dist, prob_fig, wc_fig, dist_fig):
    import base64
    import html as _html
    from io import BytesIO
    from datetime import datetime

    # Plotly chart divs (CDN loaded in <head>)
    prob_div = prob_fig.to_html(full_html=False, include_plotlyjs=False) if prob_fig else ""
    dist_div = dist_fig.to_html(full_html=False, include_plotlyjs=False) if dist_fig else ""

    # Word-cloud → base64 PNG
    wc_html = ""
    if wc_fig:
        buf = BytesIO()
        wc_fig.savefig(buf, format="png", dpi=96, bbox_inches="tight")
        buf.seek(0)
        wc_b64 = base64.b64encode(buf.read()).decode()
        wc_html = f"<img src='data:image/png;base64,{wc_b64}' style='width:100%;border-radius:8px;' alt='Word Cloud'>"

    sent_color = SENTIMENT_COLORS.get(sentiment, "#7f8c8d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _esc(s):
        return _html.escape(str(s))

    # Confidence score rows with inline bars
    conf_rows = "".join(
        f"<tr><td>{_esc(l)}</td><td class='num'>{p:.1%}</td>"
        f"<td><div style='background:#eef2fa;border-radius:4px;height:16px;overflow:hidden;'>"
        f"<div style='background:{SENTIMENT_COLORS.get(l.upper(), '#95a5a6')};"
        f"height:16px;width:{p*100:.1f}%;'></div></div></td></tr>"
        for l, p in zip(labels, probabilities)
    )

    # NER table
    if preprocess.ner:
        ner_rows = "".join(f"<tr><td>{_esc(e[0])}</td><td>{_esc(e[1])}</td></tr>" for e in preprocess.ner)
        ner_section = (
            f"<table><thead><tr><th>Entity</th><th>Label</th></tr></thead>"
            f"<tbody>{ner_rows}</tbody></table>"
        )
    else:
        ner_section = "<p class='small'>No named entities found.</p>"

    # POS table
    if preprocess.pos:
        pos_rows = "".join(f"<tr><td>{_esc(w)}</td><td>{_esc(t)}</td></tr>" for w, t in preprocess.pos)
        pos_section = (
            f"<table><thead><tr><th>Word</th><th>POS</th></tr></thead>"
            f"<tbody>{pos_rows}</tbody></table>"
        )
    else:
        pos_section = "<p class='small'>No POS tags found.</p>"

    # Word-distribution table
    dist_rows = "".join(
        f"<tr><td>{_esc(k.upper())}</td><td class='num'>{len(v)}</td>"
        f"<td>{_esc(', '.join(v)) or '&mdash;'}</td></tr>"
        for k, v in word_dist.word_lists.items()
    )

    html_out = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NLP Sentiment Report &mdash; {_esc(sentiment)}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  :root {{
    --navy:#002185; --navy-2:#1e2761; --navy-deep:#001054; --navy-ink:#0f172a;
    --ice:#cadcfc; --ice-soft:#eaf1ff; --ice-deeper:#c8d6f0;
    --gold:#ffb81c; --gold-soft:#fff4d1; --gold-deep:#b88200;
    --bg:#f6f8fc; --paper:#ffffff; --rule:#d7e0ee; --muted:#5b6b82;
    --green:#0f8a5f; --green-soft:#e8f6f0; --green-deep:#0a6244;
    --red:#b8312a; --red-soft:#fdecea;
    --amber:#b06b00; --amber-soft:#fff4dc;
    --shadow-md:0 1px 2px rgba(11,27,69,.04),0 8px 24px rgba(11,27,69,.05);
  }}
  *{{box-sizing:border-box;}}
  html{{scroll-behavior:smooth;}}
  body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Helvetica Neue",Arial,sans-serif;
        color:var(--navy-ink);background:var(--bg);line-height:1.6;font-size:15.5px;}}
  .wrap{{max-width:1080px;margin:0 auto;padding:28px 32px 80px;}}
  a{{color:var(--navy);}}

  .topbar{{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.93);
           backdrop-filter:saturate(140%) blur(8px);border-bottom:1px solid var(--rule);
           margin:-28px -32px 20px;padding:10px 32px;display:flex;align-items:center;gap:12px;font-size:13px;}}
  .topbar .logo{{font-family:Cambria,Georgia,serif;color:var(--navy);font-weight:700;font-size:16px;
                 display:flex;align-items:center;gap:8px;}}
  .topbar .logo::before{{content:"";width:18px;height:18px;background:var(--navy);border-radius:3px;}}
  .topbar .spacer{{flex:1;}}
  .topbar .stamp{{color:var(--muted);}}
  .topbar button{{appearance:none;border:1px solid var(--rule);background:white;color:var(--navy);
                  padding:6px 14px;border-radius:999px;font-family:inherit;font-size:12.5px;cursor:pointer;}}
  .topbar button:hover{{background:var(--ice-soft);border-color:var(--navy);}}
  .topbar button.primary{{background:var(--navy);color:white;border-color:var(--navy);}}

  .hero{{background:linear-gradient(140deg,var(--navy-deep),var(--navy) 55%,var(--navy-2));
         color:white;border-radius:16px;padding:44px 44px 36px;
         position:relative;overflow:hidden;box-shadow:var(--shadow-md);}}
  .hero::after{{content:"";position:absolute;right:-100px;top:-100px;width:320px;height:320px;
                background:radial-gradient(circle,rgba(255,184,28,.32) 0%,rgba(255,184,28,0) 70%);}}
  .hero .eyebrow{{font-size:11px;letter-spacing:4px;text-transform:uppercase;
                  color:var(--gold);font-weight:700;margin:0 0 14px;}}
  .hero h1{{font-size:34px;line-height:1.15;margin:0 0 14px;
            font-family:Cambria,Georgia,serif;font-weight:700;}}
  .hero .subtitle{{font-size:17px;color:var(--ice);max-width:820px;margin:0 0 22px;}}
  .gold-stripe{{width:56px;height:4px;background:var(--gold);border-radius:2px;margin-bottom:16px;}}
  .hero .meta{{display:flex;flex-wrap:wrap;gap:14px 28px;padding-top:18px;
               border-top:1px solid rgba(255,255,255,.18);font-size:13.5px;color:var(--ice);}}
  .hero .meta b{{color:white;}}

  section{{margin:38px 0;scroll-margin-top:70px;}}
  h2{{font-family:Cambria,Georgia,serif;font-size:26px;color:var(--navy);margin:0 0 8px;
      display:flex;align-items:baseline;gap:14px;}}
  h2 .num{{font-size:12px;letter-spacing:3px;color:var(--gold-deep);font-weight:700;font-family:-apple-system,sans-serif;}}
  h3{{font-family:Cambria,Georgia,serif;font-size:20px;color:var(--navy-2);margin:28px 0 10px;}}
  h4{{font-size:13.5px;color:var(--navy);text-transform:uppercase;letter-spacing:1.5px;margin:16px 0 8px;}}
  p{{margin:8px 0 14px;}}
  .small{{font-size:13px;color:var(--muted);}}

  .card{{background:var(--paper);border:1px solid var(--rule);border-radius:12px;
         padding:22px 26px;box-shadow:var(--shadow-md);}}
  .card.tone-warn{{background:var(--amber-soft);border-color:#f4d99a;}}
  .card.tone-info{{background:var(--ice-soft);border-color:var(--ice-deeper);}}

  table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:14px;
         background:var(--paper);border:1px solid var(--rule);border-radius:8px;overflow:hidden;}}
  th{{background:var(--navy);color:white;text-align:left;padding:10px 12px;
      font-size:12px;letter-spacing:.6px;text-transform:uppercase;}}
  td{{padding:10px 12px;border-top:1px solid var(--rule);vertical-align:top;color:#000000;}}
  tr:nth-child(even) td{{background:#fbfcfe;}}
  td.num{{font-variant-numeric:tabular-nums;font-family:ui-monospace,Menlo,monospace;}}

  .callout{{border-left:4px solid var(--gold);background:var(--gold-soft);
            border-radius:0 12px 12px 0;padding:14px 20px;margin:18px 0;}}
  .callout strong{{color:var(--navy);}}
  .callout.warn{{border-color:var(--amber);background:var(--amber-soft);}}
  .callout.info{{border-color:var(--navy);background:var(--ice-soft);}}

  .plot-card{{background:var(--paper);border:1px solid var(--rule);
              border-radius:14px;padding:24px;margin:16px 0;box-shadow:var(--shadow-md);}}

  .toc{{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:18px 22px;}}
  .toc ol{{margin:8px 0 0;padding-left:22px;}}
  .toc a{{text-decoration:none;}}
  .toc a:hover{{text-decoration:underline;}}

  pre{{background:#0b1b45;color:#e9efff;padding:14px 16px;border-radius:8px;overflow-x:auto;
       font-size:13px;line-height:1.5;border-left:3px solid var(--gold);margin:10px 0;
       font-family:ui-monospace,Menlo,monospace;white-space:pre-wrap;word-break:break-word;}}

  footer{{margin-top:48px;padding:20px 0 0;border-top:1px solid var(--rule);
          font-size:13px;color:var(--muted);}}
  footer b{{color:var(--navy);}}

  @media print{{
    body{{background:white;}} .topbar{{display:none!important;}}
    .hero,.card,.plot-card{{box-shadow:none;break-inside:avoid;}}
    section{{break-inside:avoid-page;}}
  }}
  @media(max-width:760px){{
    .hero{{padding:28px 22px;}} .hero h1{{font-size:24px;}}
    .wrap{{padding:18px 16px 50px;}}
  }}
</style>
</head>
<body>
<div class="wrap">

<nav class="topbar" aria-label="Document actions">
  <div class="logo">NLP Sentiment Analysis</div>
  <span class="spacer"></span>
  <span class="stamp">Generated: {now}</span>
  <button type="button" onclick="window.print()" class="primary">Download / Print PDF</button>
</nav>

<header class="hero">
  <div class="gold-stripe"></div>
  <p class="eyebrow">OpenMed HIPAA-Aware &middot; Patient Report Measures &middot; NLP Sentiment Analysis</p>
  <h1>Sentiment: <span style="color:{sent_color};">{_esc(sentiment)}</span></h1>
  <p class="subtitle">Full NLP preprocessing pipeline with PHI redaction, transformer inference, and word-level sentiment distribution.</p>
  <div class="meta">
    <div><b>Model</b> &middot; {_esc(model_label)}</div>
    <div><b>Words</b> &middot; {len(preprocess.tokenized_text)}</div>
    <div><b>Generated</b> &middot; {now}</div>
  </div>
</header>

<aside class="toc" style="margin-top:20px" aria-label="Contents">
  <h4 style="margin:0 0 4px;color:var(--navy);font-size:13.5px;text-transform:uppercase;letter-spacing:1px;">Contents</h4>
  <ol>
    <li><a href="#summary">Summary</a></li>
    <li><a href="#pii">PII Redaction (OpenMed)</a></li>
    <li><a href="#preprocessing">Preprocessing Pipeline</a></li>
    <li><a href="#charts">Charts</a></li>
    <li><a href="#ner">Named Entities (NER)</a></li>
    <li><a href="#pos">POS Tags</a></li>
    <li><a href="#distribution">Word-level Distribution</a></li>
  </ol>
</aside>

<section id="summary">
  <h2><span class="num">01</span> Summary</h2>
  <table>
    <thead><tr><th>Field</th><th>Value</th></tr></thead>
    <tbody>
      <tr><td>Model</td><td>{_esc(model_label)}</td></tr>
      <tr><td>Sentiment</td><td><b style="color:{sent_color};">{_esc(sentiment)}</b></td></tr>
      <tr><td>Word count</td><td>{len(preprocess.tokenized_text)}</td></tr>
      <tr><td>Generated</td><td>{now}</td></tr>
    </tbody>
  </table>
  <h3>Confidence Scores</h3>
  <table>
    <thead><tr><th>Label</th><th>Score</th><th>Bar</th></tr></thead>
    <tbody>{conf_rows}</tbody>
  </table>
</section>

<section id="pii">
  <h2><span class="num">02</span> PII Redaction (OpenMed)</h2>
  <div class="callout warn">
    <strong>PHI was redacted by the OpenMed PII De-identification API before any analysis.</strong>
    All downstream results are based on the redacted text shown below.
  </div>
  <pre>{_esc(preprocess.original_text)}</pre>
</section>

<section id="preprocessing">
  <h2><span class="num">03</span> Preprocessing Pipeline</h2>
  <table>
    <thead><tr><th>Stage</th><th>Output</th></tr></thead>
    <tbody>
      <tr><td><b>Cleaned</b></td><td>{_esc(preprocess.cleaned_text)}</td></tr>
      <tr><td><b>Removed</b></td><td>{_esc(preprocess.removed_text)}</td></tr>
      <tr><td><b>Normalized</b></td><td>{_esc(preprocess.normalized_text)}</td></tr>
      <tr><td><b>Tokenized</b></td><td>{_esc(', '.join(preprocess.tokenized_text))}</td></tr>
      <tr><td><b>Stemmed</b></td><td>{_esc(' '.join(preprocess.stemmed_text))}</td></tr>
      <tr><td><b>Lemmatized</b></td><td>{_esc(' '.join(preprocess.lemmatized_text))}</td></tr>
    </tbody>
  </table>
</section>

<section id="charts">
  <h2><span class="num">04</span> Charts</h2>
  <div class="plot-card">{prob_div}</div>
  <div class="plot-card">
    <h4>Word Cloud</h4>
    {wc_html if wc_html else "<p class='small'>Word cloud not available.</p>"}
  </div>
  <div class="plot-card">{dist_div}</div>
</section>

<section id="ner">
  <h2><span class="num">05</span> Named Entities (NER)</h2>
  {ner_section}
</section>

<section id="pos">
  <h2><span class="num">06</span> POS Tags</h2>
  {pos_section}
</section>

<section id="distribution">
  <h2><span class="num">07</span> Word-level Distribution</h2>
  <table>
    <thead><tr><th>Category</th><th>Count</th><th>Words</th></tr></thead>
    <tbody>{dist_rows}</tbody>
  </table>
</section>

<footer>
  <p>Generated by <b>NLP Sentiment Analysis</b> &middot; OpenMed HIPAA-aware pipeline &middot;
     Model: <b>{_esc(model_label)}</b> &middot; {now}</p>
</footer>

</div>
<script>
document.querySelectorAll('a[href^="#"]').forEach(el => {{
  el.addEventListener("click", e => {{
    const t = document.querySelector(el.getAttribute("href"));
    if (!t) return;
    e.preventDefault();
    t.scrollIntoView({{ behavior: "smooth", block: "start" }});
  }});
}});
</script>
</body>
</html>"""

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8")
    tmp.write(html_out)
    tmp.close()
    return tmp.name


def _build_report(text, sentiment, model_label, probabilities, labels, preprocess, word_dist):
    conf_str = "  |  ".join(f"{l}: {p:.1%}" for l, p in zip(labels, probabilities))
    ner_str = ", ".join(f"{e[0]} ({e[1]})" for e in preprocess.ner) or "None"
    pos_str = ", ".join(f"{w} ({t})" for w, t in preprocess.pos)

    lines = [
        "NLP SENTIMENT ANALYSIS REPORT",
        "=" * 60,
        f"Model:     {model_label}",
        f"Sentiment: {sentiment}",
        f"Scores:    {conf_str}",
        "",
        "ORIGINAL TEXT",
        "-" * 40,
        text,
        "",
        "PREPROCESSING PIPELINE",
        "-" * 40,
        f"Cleaned:    {preprocess.cleaned_text}",
        f"Removed:    {preprocess.removed_text}",
        f"Normalized: {preprocess.normalized_text}",
        f"Tokenized:  {', '.join(preprocess.tokenized_text)}",
        f"Stemmed:    {' '.join(preprocess.stemmed_text)}",
        f"Lemmatized: {' '.join(preprocess.lemmatized_text)}",
        f"Total words: {len(preprocess.tokenized_text)}",
        "",
        "NAMED ENTITIES (NER)",
        "-" * 40,
        ner_str,
        "",
        "POS TAGS",
        "-" * 40,
        pos_str,
        "",
        "WORD-LEVEL DISTRIBUTION",
        "-" * 40,
    ]
    for label, words in word_dist.word_lists.items():
        lines.append(f"  {label.upper()} ({len(words)}): {', '.join(words) or '-'}")

    return "\n".join(lines)


# ── Main analysis callback ────────────────────────────────────────────────────

_N_OUTPUTS = 16  # must match outputs list below


def run_analysis(text_input, file_obj, model_label):
    # 16 outputs: sentiment_html, prob_fig, wc_fig, dist_fig,
    #             redacted_html,
    #             cleaned, removed, normalized, tokenized, stemmed, lemmatized,
    #             ner_html, pos_str, txt_path, pdf_path, html_path
    empty = ("", None, None, None, "", "", "", "", "", "", "", "", "", None, None, None)

    def _err(msg):
        return (f"<p style='color:red'>{msg}</p>",) + empty[1:]

    # Resolve input
    file_text = None
    if file_obj is not None:
        path = file_obj if isinstance(file_obj, str) else getattr(file_obj, "path", getattr(file_obj, "name", None))
        if path:
            file_text = read_file_path(path)
    text = (file_text or text_input or "").strip()

    if not text:
        return _err("Please provide text or upload a file.")

    wc_count = len(text.split())
    if wc_count < 4:
        return _err("Please provide at least 4 words.")
    if wc_count > 100000:
        return _err("Input exceeds 100,000-word limit.")

    try:
        # ── Step 1: Redact PII via OpenMed API ────────────────────────────
        redacted_text, pii_count = redact_pii(text)
        if pii_count > 0:
            redacted_html = (
                f"<div style='background:#fff8e1;border-left:4px solid #f39c12;"
                f"padding:10px 14px;border-radius:4px;font-family:monospace;white-space:pre-wrap;'>"
                f"<b style='color:#e67e22;'>⚠ {pii_count} PII entity/entities redacted before analysis</b><br><br>"
                f"<span style='color:#000000;'>{redacted_text}</span>"
                f"</div>"
            )
        else:
            redacted_html = (
                "<div style='background:#f0fff4;border-left:4px solid #27ae60;"
                "padding:10px 14px;border-radius:4px;'>"
                "<b style='color:#27ae60;'>✓ No PII detected — text passed through unchanged</b>"
                "</div>"
            )

        # Use redacted text for all downstream analysis
        text = redacted_text

        model_type = MODEL_LABEL_TO_TYPE.get(model_label, ModelType.DEFAULT)
        config = SUPPORTED_MODELS[model_type]
        labels = config["labels"]

        # Preprocess
        cleaned, removed, normalized, tokenized, stemmed, lemmatized, ner, pos = preprocess_text(text)
        preprocess = PreprocessResult(
            original_text=text, cleaned_text=cleaned, removed_text=removed,
            normalized_text=normalized, tokenized_text=tokenized,
            stemmed_text=stemmed, lemmatized_text=lemmatized, ner=ner, pos=pos,
        )

        lemmatized_str = " ".join(lemmatized)

        # Sentiment inference on original text to preserve negations and context
        sentiment, probabilities = analyze_sentiment(text, model_type)
        while len(probabilities) < len(labels):
            probabilities.append(0.0)

        # Word distribution
        word_dist = get_word_distribution(lemmatized, model_type)

        # Emoji display labels for emotion model
        if model_type == ModelType.EMOTION:
            display_labels = [f"{l} {EMOTION_EMOJI.get(l, '')}" for l in labels]
            dist_display_labels = [
                f"{k.upper()} {EMOTION_EMOJI.get(k.upper(), '')}"
                for k in word_dist.distribution
            ]
            sentiment_display = f"{sentiment} {EMOTION_EMOJI.get(sentiment, '')}"
        else:
            display_labels = labels
            dist_display_labels = None
            sentiment_display = sentiment

        # Charts
        prob_fig = _prob_chart(probabilities, labels, display_labels)
        wc_fig = _wordcloud_fig(lemmatized_str, word_dist) if lemmatized_str.strip() else None
        dist_fig = _dist_chart(word_dist.distribution, dist_display_labels)

        # Sentiment card HTML
        color = SENTIMENT_COLORS.get(sentiment, "#7f8c8d")
        sentiment_html = f"""
<div style="text-align:center;padding:20px;border-radius:10px;
            background:{color}18;border:2px solid {color};margin:4px 0">
  <div style="font-size:2rem;font-weight:700;color:{color}">{sentiment_display}</div>
  <div style="color:#666;margin-top:6px">{config['display']} &nbsp;·&nbsp; {len(tokenized)} words</div>
</div>"""

        # Preprocessing text outputs
        ner_html = get_ner_html(text)
        pos_str  = "".join(
            f'<span style="display:inline-block;margin:3px 4px;padding:3px 10px;'
            f'background:#2563eb;color:#fff;border-radius:20px;font-size:0.82rem;">'
            f'{w} <span style="opacity:0.75;font-size:0.75rem;">({t})</span></span>'
            for w, t in pos
        ) or "<p style='color:#6b7280;font-style:italic;'>No POS tags found.</p>"

        # Build downloadable reports (text + PDF)
        report_text = _build_report(
            text, sentiment, model_label, probabilities, labels, preprocess, word_dist
        )
        txt_tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
        txt_tmp.write(report_text)
        txt_tmp.close()

        pdf_path = _build_pdf_report(
            text, sentiment, model_label, probabilities, labels, preprocess, word_dist,
            prob_fig, wc_fig, dist_fig,
        )

        html_path = _build_html_report(
            text, sentiment, model_label, probabilities, labels, preprocess, word_dist,
            prob_fig, wc_fig, dist_fig,
        )

        return (
            sentiment_html,
            prob_fig,
            wc_fig,
            dist_fig,
            redacted_html,
            _tokens_html(cleaned.split()),
            _tokens_html(removed.split()),
            _tokens_html(normalized.split()),
            _tokens_html(tokenized, "Breaks text into individual words (tokens) for word-by-word analysis"),
            _tokens_html(stemmed,   "Reduces words to their root forms to group similar meanings together"),
            _tokens_html(lemmatized,"Reduces words to their root forms to group similar meanings together"),
            ner_html,
            pos_str,
            txt_tmp.name,
            pdf_path,
            html_path,
        )

    except Exception as exc:
        import traceback
        return _err(f"Analysis failed: {exc}<br><pre>{traceback.format_exc()}</pre>")


def get_month_names(patient):
    return list(PATIENT_SAMPLES.get(patient, {}).keys())


def update_months(patient):
    months = get_month_names(patient)
    return gr.CheckboxGroup(choices=months, value=months[:1])


def load_sample(patient, names):
    if not patient or not names:
        return ""
    if isinstance(names, str):
        names = [names]
    samples = PATIENT_SAMPLES.get(patient, {})
    parts = [f"[{n}]\n{samples[n]}" for n in names if n in samples]
    return "\n\n".join(parts)


# ── Gradio layout ─────────────────────────────────────────────────────────────

_CSS = """
.gradio-container { max-width: 1280px !important; margin: 0 auto; }
.tab-nav button { font-size: 0.92rem; }
"""

_default_patient = PATIENT_NAMES[0]
_default_months  = get_month_names(_default_patient)

with gr.Blocks(title="NLP Sentiment Analysis") as demo:

    gr.Markdown("""
# NLP Sentiment Analysis

Full NLP preprocessing pipeline + pretrained Transformer inference.
Covers cleaning · tokenisation · stemming · lemmatisation · NER · POS tagging · word cloud.

**Input limit:** 4 – 100,000 words &nbsp;|&nbsp; **File upload:** `.txt`, `.csv`
""")

    with gr.Row():
        patient_dd = gr.Dropdown(
            choices=PATIENT_NAMES, value=_default_patient,
            label="Select a patient to load", scale=4,
        )
    with gr.Row():
        sample_dd = gr.CheckboxGroup(
            choices=_default_months, value=[_default_months[0]],
            label="Select month(s) to load",
        )
    with gr.Row():
        load_btn = gr.Button("Load selected month(s)", variant="secondary")

    gr.Markdown("---")

    with gr.Tabs():

        # ── Tab 1: Analyze ────────────────────────────────────────────────
        with gr.TabItem("Analyze"):
            with gr.Row(equal_height=False):
                with gr.Column(scale=1):
                    text_input = gr.Textbox(
                        label="Text input",
                        placeholder=(
                            "Enter one patient's feedback across months, e.g.:\n\n"
                            "[Month 1 — January]\n"
                            "I feel exhausted and overwhelmed. The diagnosis has left me anxious and unable to sleep.\n\n"
                            "[Month 2 — February]\n"
                            "Still struggling, but the care team is supportive. Some days are harder than others.\n\n"
                            "[Month 3 — March]\n"
                            "I noticed a small improvement this week. Feeling cautiously hopeful about the treatment.\n\n"
                            "— or use the checkboxes above to load sample months —"
                        ),
                        lines=11, max_lines=22,
                    )
                    file_input = gr.File(
                        label="Or upload file (.txt / .csv)",
                        file_types=[".txt", ".csv"],
                    )
                    model_dd = gr.Dropdown(
                        choices=MODEL_CHOICES, value=MODEL_CHOICES[0],
                        label="Model",
                    )
                    analyze_btn = gr.Button("Analyze", variant="primary")

                with gr.Column(scale=1):
                    sentiment_out = gr.HTML(label="Overall Sentiment")
                    prob_plot = gr.Plot(show_label=False)

            with gr.Row():
                wc_plot   = gr.Plot(show_label=False)
                dist_plot = gr.Plot(show_label=False)

            with gr.Accordion("PII Redaction (OpenMed)", open=True):
                gr.HTML(
                    '<span style="background:#e67e22;color:#ffffff;border-radius:20px;'
                    'padding:3px 12px;font-size:0.85rem;font-weight:600;display:inline-block;">'
                    'Redacted Text</span>'
                    '<div style="font-size:0.75rem;color:#ffffff;margin-top:4px;margin-left:4px;">'
                    'PHI redacted by the OpenMed PII API before sentiment analysis</div>'
                )
                redacted_out = gr.HTML()

            with gr.Accordion("Preprocessing Pipeline", open=False):
                with gr.Row():
                    with gr.Column():
                        gr.HTML('<span style="background:#2563eb;color:#ffffff;border-radius:20px;padding:3px 12px;font-size:0.85rem;font-weight:600;display:inline-block;">Cleaned</span><div style="font-size:0.75rem;color:#6b7280;margin-top:4px;margin-left:4px;">Removes special characters, extra spaces, and unwanted elements to prepare clean text for analysis</div>')
                        cleaned_out = gr.HTML()
                    with gr.Column():
                        gr.HTML('<span style="background:#2563eb;color:#ffffff;border-radius:20px;padding:3px 12px;font-size:0.85rem;font-weight:600;display:inline-block;">Removed (stop words / punct)</span>')
                        removed_out = gr.HTML()
                with gr.Row():
                    with gr.Column():
                        gr.HTML('<span style="background:#2563eb;color:#ffffff;border-radius:20px;padding:3px 12px;font-size:0.85rem;font-weight:600;display:inline-block;">Normalized</span><div style="font-size:0.75rem;color:#6b7280;margin-top:4px;margin-left:4px;">Converts text to lowercase and standardizes formatting for consistent analysis</div>')
                        normalized_out = gr.HTML()
                    with gr.Column():
                        gr.HTML('<span style="background:#2563eb;color:#ffffff;border-radius:20px;padding:3px 12px;font-size:0.85rem;font-weight:600;display:inline-block;">Tokenized</span><div style="font-size:0.75rem;color:#6b7280;margin-top:4px;margin-left:4px;">Breaks text into individual words (tokens) for word-by-word analysis</div>')
                        tokenized_out = gr.HTML()
                with gr.Row():
                    with gr.Column():
                        gr.HTML('<span style="background:#2563eb;color:#ffffff;border-radius:20px;padding:3px 12px;font-size:0.85rem;font-weight:600;display:inline-block;">Stemmed</span><div style="font-size:0.75rem;color:#6b7280;margin-top:4px;margin-left:4px;">Reduces words to their root forms to group similar meanings together</div>')
                        stemmed_out = gr.HTML()
                    with gr.Column():
                        gr.HTML('<span style="background:#2563eb;color:#ffffff;border-radius:20px;padding:3px 12px;font-size:0.85rem;font-weight:600;display:inline-block;">Lemmatized</span><div style="font-size:0.75rem;color:#6b7280;margin-top:4px;margin-left:4px;">Reduces words to their root forms to group similar meanings together</div>')
                        lemmatized_out = gr.HTML()

            with gr.Accordion("NER & POS Tags", open=False):
                with gr.Row():
                    with gr.Column():
                        gr.HTML('<span style="background:#2563eb;color:#ffffff;border-radius:20px;padding:3px 12px;font-size:0.85rem;font-weight:600;display:inline-block;">Named Entities (NER)</span>')
                        ner_out = gr.HTML()
                    with gr.Column():
                        gr.HTML('<span style="background:#2563eb;color:#ffffff;border-radius:20px;padding:3px 12px;font-size:0.85rem;font-weight:600;display:inline-block;">POS Tags</span>')
                        pos_out = gr.HTML()

            with gr.Row():
                report_file      = gr.File(label="Download Report (.txt)", interactive=False)
                report_file_pdf  = gr.File(label="Download Report (.pdf)", interactive=False)
                report_file_html = gr.File(label="Download Report (.html)", interactive=False)

        # ── Tab 2: Time-Series & Forecast ─────────────────────────────────
        with gr.TabItem("Time-Series & Forecast (1pMq)"):
            gr.Markdown(
                "Select a patient and months above, click **Load selected month(s)**, "
                "choose a model below, then click **Run Time-Series Analysis**."
            )
            with gr.Row():
                ts_model_dd = gr.Dropdown(
                    choices=MODEL_CHOICES, value=MODEL_CHOICES[0],
                    label="Sentiment model",
                    scale=3,
                )
                ts_btn = gr.Button("Run Time-Series Analysis", variant="primary", scale=1)
            ts_summary  = gr.HTML()
            with gr.Row():
                ts_line_plot = gr.Plot(show_label=False)
            with gr.Row():
                ts_cat_plot   = gr.Plot(show_label=False)
                ts_delta_plot = gr.Plot(show_label=False)
            with gr.Row():
                ts_report_file = gr.File(
                    label="Download Time-Series Report (.html)",
                    interactive=False,
                )

        # ── Tab 3: About ──────────────────────────────────────────────────
        with gr.TabItem("About"):
            gr.Markdown("""
## Models

| Key | HuggingFace model | Labels |
|-----|-------------------|--------|
| `default` | `distilbert-base-uncased-finetuned-sst-2-english` | POSITIVE / NEGATIVE |
| `roberta` | `cardiffnlp/twitter-roberta-base-sentiment` | NEGATIVE / NEUTRAL / POSITIVE |
| `emotion` | `j-hartmann/emotion-english-distilroberta-base` | ANGER · DISGUST · FEAR · JOY · NEUTRAL · SADNESS · SURPRISE |

## NLP Pipeline (per request)

1. **Clean** — strip stop words, punctuation, URLs, emails (spaCy `en_core_web_md`)
2. **Normalise** — lowercase
3. **Tokenise** — NLTK word tokeniser
4. **Stem** — Porter Stemmer
5. **Lemmatise** — spaCy lemmatiser
6. **NER** — spaCy named-entity recognition
7. **POS tag** — spaCy part-of-speech tagger
8. **Inference** — HuggingFace pipeline on the lemmatised text
9. **Word-level** — each lemma is scored individually to build the distribution chart

## Project Structure

```
src/
  models.py        # type definitions & model config
  preprocessor.py  # NLP preprocessing pipeline
  analyzer.py      # transformer inference
api/
  main.py          # FastAPI app
  routes.py        # REST endpoints
  schemas.py       # Pydantic request/response models
ui/
  app.py           # this Gradio interface
examples/
  basic_usage.py   # standalone script example
```
""")

    # ── Event wiring ──────────────────────────────────────────────────────────
    patient_dd.change(fn=update_months, inputs=[patient_dd], outputs=[sample_dd])
    load_btn.click(fn=load_sample, inputs=[patient_dd, sample_dd], outputs=[text_input])
    ts_btn.click(
        fn=run_timeseries,
        inputs=[text_input, ts_model_dd],
        outputs=[ts_line_plot, ts_cat_plot, ts_delta_plot, ts_summary, ts_report_file],
    )

    _outputs = [
        sentiment_out, prob_plot, wc_plot, dist_plot,
        redacted_out,
        cleaned_out, removed_out, normalized_out,
        tokenized_out, stemmed_out, lemmatized_out,
        ner_out, pos_out, report_file, report_file_pdf, report_file_html,
    ]
    analyze_btn.click(
        fn=run_analysis,
        inputs=[text_input, file_input, model_dd],
        outputs=_outputs,
    )


# ── Launch ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    _on_spaces = os.getenv("SPACE_ID") is not None
    demo.launch(
        server_name="0.0.0.0" if not _on_spaces else None,
        server_port=int(os.getenv("GRADIO_PORT", 7860)) if not _on_spaces else None,
        share=os.getenv("GRADIO_SHARE", "false").lower() == "true",
        ssr_mode=False,
        theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate"),
        css=_CSS,
    )
