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
import requests

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
    "Patient Q — COPD (Respiratory Medicine)": {
        "Month 1 — January (GP Referral)": (
            "My GP referred me to the respiratory clinic after several months of worsening shortness "
            "of breath and a persistent productive cough. I was anxious about the referral because "
            "COPD runs in my family and I had been putting off seeking help. The referral letter "
            "was sent electronically and the clinic called me within three days to arrange an appointment. "
            "I am 67 years old and still working part-time, so managing this condition matters "
            "enormously to my quality of life."
        ),
        "Month 2 — February (First Clinic Visit)": (
            "Dr Priya Patel in the respiratory clinic was absolutely wonderful. She took time to "
            "explain my COPD management plan and made sure I understood every step. The nurse on "
            "reception, Karen Thompson, was also very welcoming. Dr Patel explained the difference "
            "between my reliever and preventer inhalers clearly and gave me a written action plan "
            "for exacerbations. I left feeling informed and supported rather than frightened."
        ),
        "Month 3 — March (Inhaler Review)": (
            "I returned for a technique check with the respiratory nurse and was grateful for the "
            "correction — I had been holding my breath for too short a time after each puff. "
            "Dr Patel had asked the nurse to follow up specifically on this and the proactive "
            "approach made a real difference. My peak flow readings have improved since January "
            "and I have not needed my reliever more than twice this week."
        ),
        "Month 4 — April (Pulmonary Rehab Begins)": (
            "I started the six-week pulmonary rehabilitation program this month. The physiotherapist "
            "explained breathing techniques I had never been shown before and the group setting "
            "made the exercises more motivating than I expected. Karen Thompson at reception "
            "remembered my name when I arrived which sounds small but matters. Dr Patel reviewed "
            "my spirometry results and says the trend is cautiously positive."
        ),
        "Month 5 — May (Measurable Improvement)": (
            "I completed pulmonary rehabilitation and my six-minute walk test improved by over "
            "forty metres compared to the baseline. I have also managed two consecutive weeks "
            "without a significant breathless episode. Dr Patel was visibly pleased at my review "
            "and described the improvement as meaningful given the severity of my baseline readings. "
            "I feel more confident managing my condition day to day."
        ),
        "Month 6 — June (Stable Management)": (
            "Six months since my first appointment and COPD feels like something I am managing "
            "rather than something that is managing me. Dr Patel has moved me to three-monthly "
            "reviews, which itself signals stability. Karen Thompson rang to reschedule my next "
            "appointment when a clinic cancellation freed an earlier slot — that small act of "
            "consideration reflects the culture of this clinic. I am grateful to have found this team."
        ),
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
    },
    "Patient R — Musculoskeletal Pain (Elderly, Access Issues)": {
        "Month 1 — January (Referral)": (
            "I was referred to the specialist clinic at 45 Albert Street following persistent "
            "lower back and hip pain that has limited my mobility for the past year. I am 74 years "
            "old and live alone since my husband passed. Getting to appointments requires careful "
            "planning and usually involves either a taxi or my neighbour driving me. "
            "I am looking forward to seeing a specialist but already concerned about the journey."
        ),
        "Month 2 — February (Access Complaint)": (
            "The parking at 45 Albert Street is very limited. I had to walk from the Westfield "
            "car park which is difficult at my age. By the time I reached the clinic I was in "
            "significant pain and needed to sit for several minutes before I could speak clearly "
            "to reception. The consultation itself was helpful but I left exhausted rather than "
            "reassured. I understand parking in the city is difficult but the clinic needs to "
            "communicate this to patients in advance so we can plan accordingly."
        ),
        "Month 3 — March (Transport Arranged)": (
            "I contacted the clinic before my March appointment and was told about a free patient "
            "transport service I had not been aware of. The volunteer driver collected me from my "
            "home and waited while I attended. This made a transformative difference to my "
            "experience. The specialist adjusted my pain medication this month and I have had "
            "noticeably more comfortable days since. I wish someone had mentioned the transport "
            "service at my first appointment."
        ),
        "Month 4 — April (Pain Management Improving)": (
            "My pain levels have been consistently lower this month and I have started attending "
            "the hydrotherapy sessions recommended by the physiotherapist. Getting into the pool "
            "is effortful but worthwhile — I slept better than I have in months after the first "
            "session. The volunteer transport service has made every appointment manageable. "
            "I remain concerned about other elderly patients who may not know about the service "
            "and continue to struggle with parking at 45 Albert Street."
        ),
        "Month 5 — May (Functional Gains)": (
            "I walked to the letterbox and back without my walking stick for the first time in "
            "nearly two years. My physio says my core strength and hip flexibility have improved "
            "measurably since February. I attended my review appointment via patient transport "
            "and arrived calm and on time, which allowed for a much better consultation than my "
            "first visit. Progress at 74 is still progress."
        ),
        "Month 6 — June (Sustained Improvement)": (
            "My six-month review confirmed genuine functional improvement and the specialist "
            "reduced my pain medication by one step. Hydrotherapy continues weekly and I intend "
            "to keep attending. The access issue at 45 Albert Street that so affected my first "
            "appointment has been partially resolved — a call-ahead parking bay is now available "
            "for patients with mobility limitations. I am told patient feedback contributed to "
            "that change. I am glad I said something."
        ),
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
    },
    "Patient S — Rheumatoid Arthritis (Medication Review)": {
        "Month 1 — December 2025 (Flare-Up)": (
            "My rheumatoid arthritis flared severely in December after I missed two doses of my "
            "methotrexate during a family holiday. I called my GP's after-hours line and was "
            "advised to contact the specialist clinic when it reopened in January. The pain in "
            "my hands and wrists was the worst it has been in three years and I was genuinely "
            "frightened about the long-term impact. My wife Angela Chen has been managing most "
            "household tasks while I recover."
        ),
        "Month 2 — January (Poor Consultation Experience)": (
            "I had my appointment on 15 January 2026 at 2pm and wasn't seen until after 3:15pm. "
            "Dr James Richardson seemed rushed and didn't listen to my concerns about the "
            "medication side effects. I called the clinic at 07 3456 7890 twice before my "
            "appointment to ask about preparation and nobody answered. My wife Angela Chen had "
            "a much better experience at the Chermside Day Surgery last month. I left feeling "
            "dismissed and more anxious than when I arrived."
        ),
        "Month 3 — February (Second Opinion)": (
            "Angela encouraged me to request a different specialist for my February appointment. "
            "The clinical coordinator was understanding and arranged for me to see Dr Patel instead. "
            "The contrast was immediate — Dr Patel reviewed my medication history carefully, "
            "acknowledged the side effects I had described, and adjusted my dosing schedule "
            "accordingly. I wish I had felt empowered to raise this concern earlier."
        ),
        "Month 4 — March (Medication Stabilised)": (
            "The adjusted methotrexate schedule has significantly reduced the nausea and fatigue "
            "I had been experiencing as side effects. My hand function has improved and I have "
            "had only one minor flare this month, compared to four in January. Angela says she "
            "has her husband back. I continue to find the clinic's phone line unreliable — "
            "I called 07 3456 7890 again on two occasions and went to voicemail both times. "
            "Email or patient portal contact would be a worthwhile alternative."
        ),
        "Month 5 — April (Improved Function)": (
            "I attended a joint protection workshop run by the occupational therapist this month "
            "and learned techniques for protecting my wrists during daily activities. The "
            "practical advice on modified grips and task sequencing has reduced my pain during "
            "household chores considerably. Dr Patel reviewed my inflammatory markers at my "
            "monthly check-in and said the trend is clearly positive. Angela attended the "
            "workshop with me and found it useful for supporting me at home."
        ),
        "Month 6 — May (Stable & Positive)": (
            "Six months after the January flare I am in a stable and manageable phase. "
            "My inflammatory markers are within the acceptable range and Dr Patel has extended "
            "my review intervals to every two months. Angela and I attended a restaurant for "
            "the first time in months last week and I managed the whole evening without pain "
            "dominating my experience. The experience in January with the rushed appointment "
            "still sits with me, but it led me to advocate for better care and I am glad I did."
        ),
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
    },
    "Patient T — Post-Knee Surgery (Physiotherapy)": {
        "Month 1 — January (Surgery)": (
            "I underwent a right knee total replacement at the hospital on 8 January 2026. "
            "The surgical team was professional and the post-operative pain management was "
            "well-handled. I was discharged after three days with a referral for outpatient "
            "physiotherapy. I live alone so my recovery at home has required careful planning — "
            "my neighbour has been helping with shopping and meals. The swelling has been "
            "significant but expected according to the discharge nurse."
        ),
        "Month 2 — February (Physiotherapy Begins)": (
            "The physiotherapist Michael was great. He gave me a detailed home exercise program "
            "after my knee surgery and followed up via email at susan.obrien82@gmail.com to check "
            "on my progress. Very impressed with that level of care. The exercises are challenging "
            "but Michael explained the purpose of each one clearly, which makes me more motivated "
            "to complete them. My flexion is improving week by week and the swelling has reduced "
            "to a manageable level."
        ),
        "Month 3 — March (Steady Progress)": (
            "Michael emailed me again at susan.obrien82@gmail.com after my second session to "
            "check on a particular exercise I had found difficult. That proactive follow-up "
            "meant I corrected my technique before developing a bad habit. I walked to the end "
            "of my street and back without crutches for the first time this month, which felt "
            "extraordinary. The progress is slower than I had hoped but Michael keeps reminding "
            "me that knee replacement recovery is measured in months, not weeks."
        ),
        "Month 4 — April (Building Confidence)": (
            "I graduated from crutches to a single walking stick this month and have been "
            "navigating my home independently for most activities. Michael assessed my gait "
            "and identified a slight compensatory lean that we have been working on in sessions. "
            "The home exercise program has become part of my daily routine. I emailed Michael "
            "a question about a new ache on a Sunday evening and received a considered reply "
            "on Monday morning — that responsiveness builds real trust."
        ),
        "Month 5 — May (Approaching Full Recovery)": (
            "Michael cleared me to walk on uneven surfaces this month, which means I can return "
            "to my garden — something I had missed enormously. My flexion has reached 110 degrees "
            "and is still improving. The pain is now managed with paracetamol only on active days. "
            "Michael says I am ahead of the average recovery curve for my age group, which is "
            "gratifying. His email follow-ups have been one of the most valued aspects of my care."
        ),
        "Month 6 — June (Discharge from Physiotherapy)": (
            "Michael has discharged me from regular sessions with a maintenance program to follow "
            "independently. He emailed a final summary of my progress and recommended exercises "
            "to susan.obrien82@gmail.com and I have printed it for reference. My knee is functional, "
            "largely pain-free, and stronger than before the surgery. I would not hesitate to "
            "recommend Michael to anyone facing the same procedure. His follow-up emails made "
            "the recovery feel supervised rather than solitary."
        ),
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
    },
    "Patient U — Type 2 Diabetes (New Referral via Ipswich)": {
        "Month 1 — January (Referral from Ipswich Hospital)": (
            "I was referred to this clinic by Dr Nguyen at the Ipswich Hospital following a "
            "significant deterioration in my HbA1c over the past six months. I have had type 2 "
            "diabetes for eleven years and this is the first time my GP and specialist have "
            "agreed a more intensive management approach is needed. The referral transition from "
            "Ipswich was described as smooth by the admin team and my records arrived in full "
            "before my first appointment."
        ),
        "Month 2 — February (Booking System Difficulty)": (
            "The online booking system could be easier to use. I ended up calling reception to "
            "book because I couldn't figure out the Zedoc portal. I was referred by Dr Nguyen "
            "at the Ipswich Hospital and the transition was smooth. However, having to call "
            "instead of booking online added a step that could deter patients less comfortable "
            "with phone calls. The receptionist was helpful and patient once I got through. "
            "A clearer Zedoc onboarding guide sent with the initial referral letter would help."
        ),
        "Month 3 — March (First Diabetes Clinic Appointment)": (
            "My first appointment at the diabetes clinic was thorough and constructive. The "
            "diabetes educator spent forty minutes reviewing my food diary and my insulin "
            "injection technique, identifying several opportunities for improvement I had not "
            "known about. My HbA1c at 9.2 is too high but the team's plan is evidence-based "
            "and clear. I have been given a continuous glucose monitor for the next four weeks "
            "to establish a baseline. Dr Nguyen's referral letter was clearly read before the "
            "appointment, which made the transition feel genuinely coordinated."
        ),
        "Month 4 — April (Glucose Monitoring Data)": (
            "The glucose monitor data revealed several overnight hypoglycaemic episodes that "
            "I had not been aware of, and the diabetes team adjusted my insulin timing accordingly. "
            "I have managed to navigate the Zedoc portal successfully this month after a helpful "
            "phone tutorial from reception. My eating patterns have improved and I have added "
            "a twenty-minute walk after dinner each night. The team feels optimistic about "
            "reaching a target HbA1c within six months."
        ),
        "Month 5 — May (HbA1c Improving)": (
            "My three-month HbA1c came back at 8.1, down from 9.2 in January — a meaningful "
            "improvement. The diabetes educator was encouraging and we reviewed the factors "
            "that contributed: improved injection technique, better carbohydrate distribution, "
            "and the evening walks. I feel more engaged with my diabetes management than I have "
            "in years. The coordination with Dr Nguyen at Ipswich continues — he receives "
            "copies of all clinic letters which avoids the duplication of my previous care."
        ),
        "Month 6 — June (Target in Sight)": (
            "Six months after my Ipswich Hospital referral I feel genuinely in control of my "
            "diabetes for the first time in several years. My HbA1c is trending toward the "
            "target range and my overnight hypoglycaemia has resolved completely with the "
            "insulin timing adjustment. I now use the Zedoc portal for all bookings and "
            "message reminders. The rocky start with the online system is behind me. "
            "I am grateful for the coordinated care between this clinic and Dr Nguyen at Ipswich."
        ),
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
    },
    "Patient V — Type 2 Diabetes (Established, Insulin Adjustment)": {
        "Month 1 — January (HbA1c Deterioration)": (
            "My HbA1c came back at 8.9 this month after a period of poor dietary adherence "
            "during the Christmas holidays. My GP Dr Samantha Lee at the Toowoomba Medical "
            "Practice arranged an urgent referral to the diabetes clinic. I have been managing "
            "type 2 diabetes for seven years but my insulin management has drifted and I know "
            "I need more structured support. I feel embarrassed about the deterioration but "
            "Dr Lee was non-judgemental and encouraging about seeking help."
        ),
        "Month 2 — February (Diabetes Clinic Review)": (
            "Nurse Rebecca Taylor in the diabetes clinic was exceptional. She spent over "
            "40 minutes with me going through my HbA1c results and adjusting my insulin plan. "
            "She also coordinated with my GP Dr Samantha Lee at the Toowoomba Medical Practice "
            "to ensure consistent care. Rebecca explained the glycaemic index concept in a way "
            "that finally made sense to me after years of not fully understanding it. "
            "I left the appointment feeling informed, not ashamed."
        ),
        "Month 3 — March (Early Improvement)": (
            "My glucose readings at home have been consistently better since the insulin plan "
            "adjustment Nurse Rebecca made in February. I have reduced my post-dinner spikes "
            "significantly by shifting my injection timing. Dr Lee at Toowoomba received "
            "Rebecca's coordination letter and rang me to say she was pleased with the plan. "
            "Having the two clinicians communicate directly removes the anxiety of managing "
            "the information gap myself."
        ),
        "Month 4 — April (Dietary Changes)": (
            "I attended a group session on carbohydrate counting run by the clinic dietitian "
            "this month and found it transformative. I had been systematically underestimating "
            "my carbohydrate intake and the correction has made a visible difference to my "
            "post-meal glucose readings. Nurse Rebecca followed up with a brief phone call "
            "to check how I was implementing the changes — the ongoing support is exactly what "
            "I needed after years of drifting without accountability."
        ),
        "Month 5 — May (HbA1c Improving)": (
            "My repeat HbA1c is now 7.4, down from 8.9 in January — the biggest single "
            "improvement I have seen in several years. Dr Lee called from Toowoomba Medical "
            "Practice to congratulate me, having received the clinic letter. Rebecca celebrated "
            "with me at my May appointment and adjusted my targets upward to reflect my "
            "improving baseline. I feel in genuine control of my diabetes for the first "
            "time since my initial diagnosis."
        ),
        "Month 6 — June (Sustained Progress)": (
            "Six months of structured support from this clinic have produced results I did not "
            "think were achievable. My HbA1c is approaching the target range and my insulin "
            "regimen is stable. Nurse Rebecca and Dr Lee at Toowoomba continue to communicate "
            "directly, which spares me the burden of being the go-between for my own care. "
            "I have recommended this clinic to two friends with diabetes who have been "
            "struggling with management. Rebecca's forty-minute consultation in February "
            "changed the trajectory of my health."
        ),
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
    },
    "Patient W — COPD (Long-term, Valued Continuity of Care)": {
        "Month 1 — January (Annual Review Preparation)": (
            "I have been attending the respiratory clinic for four years for my COPD management. "
            "My annual review is scheduled for this month and I am bringing a list of questions "
            "about adjusting my long-acting bronchodilator as the current dose has left me with "
            "more morning tightness than before. I have learned to come to each appointment "
            "prepared because it makes the time with the doctor more productive. "
            "I look forward to seeing Dr Patel."
        ),
        "Month 2 — February (Annual Review)": (
            "Dr Patel is always thorough and patient. She remembers details from previous visits "
            "which makes me feel valued. She recalled that I had mentioned my granddaughter's "
            "wedding in September without me prompting her, and asked whether I was managing "
            "my COPD well enough to attend. That kind of continuity is rare in a busy clinic "
            "and it motivates me to follow my management plan carefully. She adjusted my "
            "bronchodilator as I had hoped."
        ),
        "Month 3 — March (Medication Improvement)": (
            "The adjusted bronchodilator has made a noticeable difference to my morning "
            "tightness, which was my primary complaint at the February review. I have been "
            "able to complete my morning walk without stopping twice, compared to stopping "
            "three or four times before the adjustment. Dr Patel sent a brief note via the "
            "patient portal confirming she had reviewed my peak flow diary — the personal "
            "attention to detail continues outside appointments."
        ),
        "Month 4 — April (Stable Winter Preparation)": (
            "Dr Patel reminded me at my March appointment to ensure my influenza and "
            "pneumococcal vaccinations were up to date before winter. Both were administered "
            "by my GP this month. I have also prepared a written COPD action plan for the "
            "colder months, which Dr Patel helped me draft last year. Knowing what to do "
            "during an exacerbation without having to call in a panic has removed a layer "
            "of anxiety from my winter preparations."
        ),
        "Month 5 — May (Winter Management)": (
            "I had a mild respiratory infection in early May but followed my action plan and "
            "avoided hospital. Dr Patel had told me exactly when to start the standby "
            "antibiotics and steroids, and the plan worked as intended. I called the clinic "
            "to report the event and the nurse updated my record accordingly. Four years ago "
            "the same kind of infection would have sent me to the emergency department. "
            "Good management changes outcomes."
        ),
        "Month 6 — June (Positive Trajectory)": (
            "My mid-year review with Dr Patel confirmed that my lung function is stable and "
            "my exacerbation rate is the lowest in four years. She attributed this to consistent "
            "medication adherence and good self-management. I mentioned the granddaughter's "
            "wedding again and she smiled — she had not forgotten. This clinic has given me "
            "back confidence in my own ability to live well with a chronic condition."
        ),
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
    },
    "Patient X — Cardiac Disease (Elderly, Billing & Forms Assistance)": {
        "Month 1 — December 2025 (Referral)": (
            "I am 81 years old and my GP referred me to the cardiac clinic following an "
            "abnormal ECG result at my annual health check. My daughter Sarah Fitzpatrick "
            "usually accompanies me to medical appointments and helps me with forms and paperwork "
            "but she lives in Toowoomba and cannot always travel. I am hoping the clinic can "
            "accommodate my needs as I struggle with small print and complex documents. "
            "I am anxious about the referral but trying to remain calm."
        ),
        "Month 2 — January (Forms & Billing Difficulties)": (
            "I'm 81 years old and find the forms quite difficult to fill in. My daughter "
            "Sarah Fitzpatrick usually helps me but she wasn't available this time. Could you "
            "offer some assistance at the front desk for elderly patients? Also my Medicare "
            "number is 2345 67890 1 and I think there was a billing error on my last visit "
            "on 28 January 2026. I noticed an unfamiliar item number on the receipt and "
            "would like it checked before I pay. The clinical staff were kind but the "
            "administrative experience added unnecessary stress."
        ),
        "Month 3 — February (Issues Resolved)": (
            "Sarah was able to attend my February appointment and helped me raise the billing "
            "query from January. The billing team reviewed the item number against Medicare "
            "number 2345 67890 1 and confirmed an error had been made — a duplicate item had "
            "been submitted. It was corrected within the week. The clinic has also agreed to "
            "provide a reception staff member to assist with forms for any patient who requests "
            "it. That policy change will help many elderly patients beyond myself."
        ),
        "Month 4 — March (Cardiac Assessment)": (
            "My full cardiac workup was completed this month — echocardiogram, stress test, "
            "and Holter monitor. Sarah attended and we both took notes. The cardiologist "
            "explained each test clearly and printed a summary for me to take home. "
            "The identified abnormality is mild and manageable with medication. "
            "Knowing what I am dealing with is less frightening than not knowing. "
            "Sarah was relieved and so was I."
        ),
        "Month 5 — April (Medication Commenced)": (
            "I started a low-dose blood thinner and a beta-blocker this month. Sarah helped "
            "me set up a medication reminder system on my phone that speaks the medication "
            "names aloud so I do not confuse them. The clinic sent my medication summary "
            "to my GP and to Sarah at her email address so everyone has the same information. "
            "Coordinated communication between the clinic, my GP, and my daughter has made "
            "managing my cardiac condition feel manageable rather than overwhelming."
        ),
        "Month 6 — May (Settled & Well-Supported)": (
            "My three-month medication review showed the beta-blocker is well-tolerated and "
            "my cardiac rhythm has stabilised. Sarah attended by phone this time as she could "
            "not travel, and the cardiologist was happy to include her in the conversation. "
            "The billing team contacted me proactively to confirm the Medicare number "
            "2345 67890 1 issue had been fully resolved and no further action was required. "
            "At 81, I am grateful for a care team that takes my practical needs seriously "
            "alongside my clinical ones."
        ),
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
    },
    "Patient Y — Pregnancy (Antenatal & Midwifery)": {
        "Month 1 — October (Booking Appointment)": (
            "I attended my first booking appointment at ten weeks gestation. The midwife "
            "reviewed my complete obstetric and medical history and explained the care "
            "pathway clearly. I was given a folder of information including the schedule "
            "of antenatal appointments and details of the classes available at the centre "
            "on George Street. This is my second pregnancy and I feel more informed than "
            "I did the first time around. I am looking forward to meeting the broader "
            "midwifery team over the coming months."
        ),
        "Month 2 — November (Midwifery Team — Exceptional Care)": (
            "The midwifery team, especially Lisa and Jenny, were amazing throughout my "
            "pregnancy. They made me feel safe and supported. The antenatal classes at the "
            "centre on George Street were also excellent. Lisa noticed I was anxious about "
            "a previous complication and arranged an extra scan for reassurance without me "
            "having to ask. Jenny remembered details about my family situation from our first "
            "appointment. This level of personalised care is exactly what expectant mothers need."
        ),
        "Month 3 — December (Third Trimester Preparation)": (
            "Lisa and Jenny have continued to be the anchors of my antenatal experience. "
            "At my 28-week appointment Jenny talked me through the birth plan options and "
            "made sure I understood that plans can change without that being a failure. "
            "The George Street classes covered infant feeding and settling, both of which "
            "I had found difficult after my first baby. Having this preparation earlier "
            "this time has reduced my anxiety considerably."
        ),
        "Month 4 — January (Birth)": (
            "I gave birth to a healthy boy on 19 January 2026. Lisa was on shift and was "
            "present for the active phase of labour and the birth. Her calm presence and "
            "clear communication throughout made the experience as positive as it could be. "
            "The postnatal ward team continued the same high standard of care. "
            "I am home now, tired but well, and grateful for every member of the midwifery "
            "team at George Street who supported me."
        ),
        "Month 5 — February (Postnatal)": (
            "Jenny called me at home one week after discharge to check on my recovery and "
            "the baby's feeding. The call was brief but meaningful — knowing the team was "
            "still thinking about me in that early, exhausting period mattered enormously. "
            "My son is feeding well and gaining weight as expected. I have been attending "
            "the new parents' group at George Street and the connections I have made there "
            "are a genuine support network already forming."
        ),
        "Month 6 — March (Six-Week Review)": (
            "My six-week postnatal review confirmed that my physical recovery is complete "
            "and I was discharged back to my GP for ongoing care. Lisa was on duty and "
            "said goodbye warmly — she had followed my care for the final trimester and "
            "been present at the birth. The antenatal classes at George Street and the "
            "continuity provided by Lisa and Jenny have made this pregnancy an experience "
            "I will remember with genuine gratitude rather than anxiety."
        ),
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
    },
    "Patient Z — Postnatal (Working Parent, Scheduling)": {
        "Month 1 — February (Initial Appointment)": (
            "I attended my eight-week postnatal check following the birth of my second child. "
            "I work full-time at Bright Horizons Childcare and managing appointments around "
            "my roster is a significant logistical challenge. My employer is generally "
            "supportive but flexibility is not always possible given minimum staffing ratios "
            "in childcare. I am hoping the clinic can offer some later appointment times "
            "so I do not have to use annual leave for every attendance."
        ),
        "Month 2 — March (Scheduling Difficulty)": (
            "It would be nice to have later appointment slots. As a working mum I find it "
            "hard to attend before 4pm. My employer at Bright Horizons Childcare is not "
            "always flexible with time off. I recommended this clinic to my sister-in-law "
            "Patricia Nakamura who is expecting in July. Patricia had a complicated first "
            "pregnancy and I told her the midwifery team here was outstanding. "
            "I hope the scheduling situation improves — the clinical care makes the "
            "inconvenience worth managing."
        ),
        "Month 3 — April (Extended Hours Trial)": (
            "I was contacted by the clinic to say they are trialling a 4:30pm slot on "
            "Tuesdays and Thursdays for working parents. I was offered one of these slots "
            "for my April review and it made an enormous difference — I attended straight "
            "from work without requesting any leave. Patricia Nakamura has booked her first "
            "antenatal appointment and is already impressed with the team. I am glad I "
            "raised the scheduling concern rather than just tolerating it."
        ),
        "Month 4 — May (Ongoing Support)": (
            "I have been using the Tuesday late slot consistently and my attendance has "
            "been uninterrupted for the first time since returning to work at Bright Horizons. "
            "My six-month postnatal check showed my recovery is proceeding well and my "
            "GP has noted I am managing the return to work without signs of post-natal "
            "depression — an outcome I attribute partly to the continuity of this clinic's "
            "support. Patricia Nakamura had her twelve-week scan this month and is doing well."
        ),
        "Month 5 — June (Thriving)": (
            "I feel completely well and am managing work, a toddler, and a baby with the "
            "support that comes from having access to a clinic that respects my reality as "
            "a working parent. The extended hours trial appears to have become a permanent "
            "feature — I asked at reception and was told demand justified keeping it. "
            "Patricia Nakamura tells me she has already developed the same trust in the "
            "midwifery team that I described to her. Good care spreads by word of mouth."
        ),
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
    },
    "Patient AA — Haematology (Blood Collection, Skilled Nursing)": {
        "Month 1 — February (Referral for Bloods)": (
            "My GP referred me for a full blood panel following symptoms of persistent "
            "fatigue and unexplained bruising over the past two months. I have a significant "
            "needle phobia and previous blood draws have been distressing — I have walked "
            "out of collection centres on two occasions. My GP wrote a note in the referral "
            "asking the collection staff to be aware of my anxiety. I attended with considerable "
            "apprehension."
        ),
        "Month 2 — March (Excellent Collection Experience)": (
            "The new blood collection nurse, Daniel Kim, was very skilled. Best blood draw "
            "I've had — barely felt it. He mentioned he previously worked at the Royal Brisbane "
            "and Women's Hospital. Daniel explained each step before doing it, used a butterfly "
            "needle without me having to ask, and maintained a calm conversation throughout "
            "that genuinely distracted me. I left with my bloods collected and my anxiety "
            "about future draws reduced substantially. That is not a small thing for someone "
            "with a needle phobia."
        ),
        "Month 3 — April (Results Review)": (
            "My haematology results showed mild iron deficiency anaemia, explaining the fatigue "
            "and bruising. My GP started me on an iron supplement and referred me to the "
            "gastroenterology team to investigate the underlying cause. I returned for a "
            "repeat blood draw this month and was relieved to find Daniel Kim on duty again. "
            "His technique remains exceptional. I have told two friends with needle phobias "
            "about him specifically."
        ),
        "Month 4 — May (Monitoring)": (
            "My iron levels are responding well to supplementation and my fatigue has "
            "noticeably improved. The gastroenterology investigation is scheduled for next "
            "month. I have now had three blood draws since February and each has been "
            "manageable. Daniel's approach — explaining each step, warm towels, butterfly "
            "needle as default — has reframed my experience of blood collection entirely. "
            "Experience of a skilled clinician can change a patient's relationship with "
            "healthcare more broadly."
        ),
        "Month 5 — June (Cause Identified)": (
            "The gastroscopy identified a small hiatal hernia causing occult bleeding — "
            "the source of my iron deficiency. A treatment plan is in place and my "
            "haematologist is satisfied the iron deficiency will resolve once the underlying "
            "cause is managed. I required another blood draw for pre-procedure bloods and "
            "specifically requested Daniel Kim, who was available. His consistent skill "
            "and manner have removed one significant barrier to my healthcare engagement."
        ),
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
    },
    "Patient AB — Endocrinology (Results Portal, Communication)": {
        "Month 1 — January (Thyroid Investigation)": (
            "I was referred to the endocrinology clinic following an incidental finding of "
            "an enlarged thyroid nodule on imaging. My GP ordered a comprehensive thyroid "
            "panel and FNA biopsy was recommended at my first specialist appointment. "
            "I was told results would be uploaded to the patient portal within ten days "
            "of the procedure. I am not experienced with online health portals and was "
            "already anxious about the biopsy results without adding a technology barrier."
        ),
        "Month 2 — February (Results Portal Confusion)": (
            "The results portal is confusing. I had to call Dr Richardson's office at "
            "07 3456 7891 to get my pathology explained because I couldn't understand "
            "the online report. The staff were helpful when I called but I had to wait "
            "on hold for eleven minutes. The result itself — benign — was a relief, but "
            "learning it from a confusing online report rather than a clinician explanation "
            "was unnecessarily stressful. A brief call to confirm benign results before "
            "uploading would improve patient experience significantly."
        ),
        "Month 3 — March (Feedback Acknowledged)": (
            "Dr Richardson's office called me proactively this month to say that my feedback "
            "about the results portal had been noted and that the clinic was implementing a "
            "policy requiring a clinical phone call for all biopsy results before portal upload. "
            "That response to patient feedback was prompt and meaningful. My thyroid nodule "
            "remains under surveillance with an ultrasound scheduled in six months. "
            "Knowing the process will be handled differently next time has reduced my anxiety."
        ),
        "Month 4 — April (Six-Month Monitoring Plan)": (
            "I attended my three-month endocrinology review this month. The thyroid function "
            "tests are within normal limits and the nodule remains unchanged from the "
            "baseline measurement. Dr Richardson confirmed the surveillance ultrasound is "
            "scheduled and that results will be communicated by phone first. I now understand "
            "the patient portal better after a brief tutorial from the receptionist — the "
            "clinic offered this to all patients who had raised similar difficulties."
        ),
        "Month 5 — May (Stable & Informed)": (
            "My six-month surveillance ultrasound showed no change in the nodule — the "
            "ideal outcome in this monitoring pathway. A nurse called me before the report "
            "was uploaded to the portal, exactly as the new protocol requires. That phone "
            "call removed all the anxiety I had carried last time. Dr Richardson has "
            "extended the monitoring interval to twelve months, which reflects confidence "
            "in the benign nature of the finding. My experience of this clinic has improved "
            "substantially since February."
        ),
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
    },
    "Patient AC — Gynaecology (Cultural & Religious Needs)": {
        "Month 1 — January (Referral & Cultural Request)": (
            "I was referred to gynaecology following an abnormal cervical screening result. "
            "I am a practicing Muslim and it is very important to me that I am examined by "
            "a female practitioner. I raised this clearly in the referral letter from my GP "
            "and in the pre-appointment phone call with the clinic. I was reassured that "
            "a female doctor would be available but wanted to confirm this again at the "
            "time of booking. Clear, documented communication of cultural needs is essential."
        ),
        "Month 2 — February (Respectful Appointment)": (
            "Dr Patel and Nurse Rebecca were both excellent. They were respectful of my "
            "cultural needs and ensured a female practitioner was available for my examination. "
            "This was very important to me. Dr Patel explained the colposcopy procedure "
            "clearly and checked my understanding at every stage. Nurse Rebecca's presence "
            "throughout the examination was calming. I left feeling respected and cared for "
            "as a whole person, not just as a patient with a clinical problem."
        ),
        "Month 3 — March (Biopsy Results)": (
            "The biopsy results came back as CIN 2 — significant enough to require treatment "
            "but not cancer. Dr Patel called me personally to explain the result before the "
            "letter arrived, which I had not expected. She confirmed that the LLETZ treatment "
            "procedure would also be performed by a female clinician. That commitment to "
            "my cultural and religious needs being consistently honoured throughout my care "
            "has been deeply reassuring."
        ),
        "Month 4 — April (LLETZ Treatment)": (
            "The LLETZ procedure was completed by Dr Patel with Nurse Rebecca assisting. "
            "Both women spoke to me in warm, professional terms throughout and I was never "
            "made to feel that my request for female-only care was an inconvenience. "
            "The procedure itself was straightforward and well-managed. I have follow-up "
            "smears scheduled at six and twelve months. I have recommended this clinic "
            "to two friends in my community who face similar barriers to gynaecological care."
        ),
        "Month 5 — May (Recovery & Follow-up Plan)": (
            "My recovery from the LLETZ procedure has been uncomplicated. Nurse Rebecca "
            "called to check on me one week after the procedure — a simple courtesy that "
            "felt significant. My six-month smear is booked for August. I have shared my "
            "positive experience with several women in my community who have been reluctant "
            "to attend gynaecological care due to cultural concerns. The way this clinic "
            "handled my needs may encourage others to seek care they have been avoiding."
        ),
        "Month 6 — June (Stable Outcome)": (
            "My discharge summary confirmed the LLETZ treatment is expected to have been "
            "curative and the surveillance pathway is now in place. Dr Patel sent a brief "
            "note summarising the follow-up schedule and confirming that my clinical record "
            "flags the requirement for a female practitioner for all future examinations. "
            "That systematic recording of my cultural needs is the right way to ensure "
            "continuity of respectful care across appointments and clinicians. "
            "I feel genuinely well looked after."
        ),
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
    },
    "Patient AD — Geriatrics (Language & Interpreter Access)": {
        "Month 1 — February (Referral for Elderly Mother)": (
            "I am writing on behalf of my mother Zahra Al-Rashid, who was referred to "
            "the geriatrics clinic following a fall at home and increasing confusion that "
            "concerned our family. My mother is a native Arabic speaker with limited English "
            "and has never managed a health system appointment independently in Australia. "
            "I specifically requested an Arabic interpreter be booked when I called to "
            "confirm the March appointment. I was told this would be arranged."
        ),
        "Month 2 — March (Interpreter Not Available)": (
            "The interpreter service was not available on 4 March 2026 when my mother "
            "attended. She speaks Arabic and struggled to communicate her symptoms. Please "
            "ensure interpreters are booked in advance. My mother Zahra Al-Rashid "
            "(patient ID PAT-91603) would like to provide feedback separately. Can someone "
            "contact her at fatima.alrashid@outlook.com to arrange an Arabic-language survey? "
            "The consultation was of limited value without interpretation and we left feeling "
            "the appointment had been largely wasted."
        ),
        "Month 3 — April (Interpreter Provided, Assessment Completed)": (
            "The clinic arranged a telephone Arabic interpreter for my mother's April "
            "appointment. The difference was immediate and profound — my mother was able "
            "to describe her symptoms clearly for the first time and the geriatrician "
            "completed a thorough assessment that had not been possible in March. "
            "The cognitive assessment identified mild cognitive impairment. Early identification "
            "is important and the delay caused by the interpreter failure in March set back "
            "this diagnosis by a month. We were contacted at fatima.alrashid@outlook.com "
            "to complete the Arabic-language feedback survey as requested."
        ),
        "Month 4 — May (Support Plan Established)": (
            "My mother Zahra Al-Rashid (PAT-91603) now has a care plan that includes "
            "regular cognitive monitoring, occupational therapy for home safety, and "
            "a referral to the Arabic-speaking community support worker identified by "
            "the clinic's social worker. All correspondence is sent to "
            "fatima.alrashid@outlook.com as agreed. The proactive effort to find an "
            "Arabic-speaking support worker has made an enormous difference to my mother's "
            "willingness to engage with the care plan."
        ),
        "Month 5 — June (Progress)": (
            "My mother is settled into her support routines and has responded well to the "
            "structured social engagement offered by the Arabic-speaking community program. "
            "Her GP has been updated on the cognitive impairment diagnosis and the care "
            "plan is documented in MyHealthRecord. The clinic has since implemented a "
            "protocol requiring interpreter bookings to be confirmed 48 hours in advance "
            "for all patients with documented language needs. We were informed of this "
            "change and are glad our experience led to a systemic improvement."
        ),
        "Month 6 — July (Family Reassured)": (
            "My mother Zahra Al-Rashid (PAT-91603) is stable and well-supported. "
            "The cognitive decline has not accelerated over the past three months and "
            "her quality of life has improved since the support program commenced. "
            "We receive all correspondence at fatima.alrashid@outlook.com and the "
            "communication has been consistent and timely. The interpreter failure in "
            "March remains a regret — a month's delay in diagnosis matters at my mother's "
            "age — but the response from the clinic has been thorough and genuine."
        ),
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
    },
    "Patient AE — Mental Health (FIFO Worker, Telehealth)": {
        "Month 1 — September 2025 (Workplace Incident)": (
            "I experienced a significant workplace incident at BHP Mitsubishi Alliance "
            "in Mount Isa that left me unable to return to my FIFO roster for three weeks. "
            "My employer's Employee Assistance Program arranged an initial counselling session "
            "which helped me recognise that I needed more structured psychological support "
            "than a short-term EAP could provide. My GP referred me to a psychologist "
            "and we discussed the challenges of accessing mental health care while working "
            "FIFO in remote Queensland."
        ),
        "Month 2 — October 2025 (Telehealth Begins)": (
            "Outstanding mental health support from psychologist Dr Amanda Clarke. She helped "
            "me develop coping strategies after my workplace incident at BHP Mitsubishi Alliance "
            "in Mount Isa last year. The telehealth option made it possible to continue sessions "
            "when I was FIFO. Dr Clarke adapted her approach to the specific stressors of "
            "remote and isolated work environments in ways that felt genuinely relevant to "
            "my experience rather than generic. Having consistent access to the same "
            "psychologist regardless of my roster was essential to building therapeutic trust."
        ),
        "Month 3 — November 2025 (Progress on Roster)": (
            "I returned to my FIFO roster with a modified duties plan agreed between my "
            "employer, my GP, and Dr Clarke. Telehealth sessions continued during my fly-in "
            "periods, scheduled around shift changeover times. The coordination between the "
            "clinical team and my workplace was more structured than I had expected from "
            "an EAP referral. My anxiety has reduced to manageable levels and I am sleeping "
            "significantly better than in September."
        ),
        "Month 4 — December 2025 (Sustained Improvement)": (
            "Dr Clarke and I reviewed my progress after three months of structured sessions. "
            "The coping strategies she developed with me — grounding techniques specific to "
            "the mine site environment, communication scripts for difficult interactions with "
            "supervisors — have been genuinely practical. I am back on full duties at "
            "BHP Mitsubishi Alliance and managing the psychological demands of the work "
            "and the isolation without the acute distress I experienced in September."
        ),
        "Month 5 — January 2026 (Maintenance Phase)": (
            "I have moved to fortnightly telehealth sessions with Dr Clarke as a "
            "maintenance phase rather than intensive treatment. The transition felt natural "
            "and mutually agreed. I was not discharged; I graduated. My employer at BHP "
            "Mitsubishi Alliance conducted a workplace review following the original incident "
            "and has implemented additional psychological safety protocols for remote workers. "
            "I submitted a statement supporting those changes."
        ),
        "Month 6 — February 2026 (Stable & Resilient)": (
            "Six months after the incident at Mount Isa I am stable, working, and equipped "
            "with a set of psychological tools that will serve me beyond this particular "
            "situation. Dr Clarke's telehealth model made sustained care possible for someone "
            "in my situation — without that flexibility I would almost certainly have "
            "disengaged from treatment when my roster restarted. Accessible mental health "
            "care is not a luxury; for FIFO workers it is an occupational health imperative."
        ),
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
    },
    "Patient AF — Mental Health (Excessive Wait Time)": {
        "Month 1 — November 2025 (Referral Made)": (
            "My GP referred me to the mental health team on 15 November 2025 following "
            "several weeks of worsening depression and increasing difficulty maintaining "
            "my work and family responsibilities. I was assessed as requiring specialist "
            "input beyond what the GP could provide. I was told the wait for an initial "
            "appointment might be several weeks. I left the GP surgery feeling both "
            "relieved to have taken the step and apprehensive about how I would manage "
            "in the meantime."
        ),
        "Month 2 — December 2025 (Still Waiting)": (
            "I am still waiting for my first mental health appointment after my referral "
            "on 15 November 2025. I called the mental health intake team twice this month "
            "and was told I am on the waiting list but no timeframe could be given. "
            "The weeks between referral and first contact are often the most dangerous "
            "for people in crisis. I am managing but only just. My GP has been providing "
            "weekly check-in calls which have been a genuine lifeline."
        ),
        "Month 3 — January 2026 (Finally Seen)": (
            "The mental health waiting list is too long. I was referred on 15 November 2025 "
            "and didn't get my first appointment until 8 January 2026. That's nearly 8 weeks. "
            "The psychologist I finally saw was skilled and the session was genuinely helpful. "
            "But the eight weeks of waiting while unwell is not acceptable. I want to be clear: "
            "the care I received on 8 January was excellent. The system failure was the "
            "gap between referral and first contact, not the clinician's quality."
        ),
        "Month 4 — February 2026 (Treatment Commenced)": (
            "I am now seeing the psychologist fortnightly and the structured CBT approach "
            "is producing meaningful results. My sleep has improved and I have returned "
            "to work on reduced hours. The frustration about the eight-week wait has not "
            "diminished — I have been encouraged by my psychologist to document my experience "
            "and submit it as feedback to the service. I plan to do so. Systems improve "
            "when patients who waited too long say so clearly."
        ),
        "Month 5 — March 2026 (Sustained Progress)": (
            "My depression has lifted to the point where I am managing full working hours "
            "again and have resumed activities I had withdrawn from during the worst period. "
            "My psychologist has noted my recovery as meaningful given the severity of "
            "presentation in November. I submitted formal written feedback about the "
            "eight-week wait to the mental health service director. I was acknowledged "
            "and told it would be used in a service review. Raising this matters."
        ),
        "Month 6 — April 2026 (Thriving)": (
            "I attended my three-month review and my psychologist considers my progress "
            "exceptional. We are moving to monthly sessions. I think often about the "
            "eight weeks between 15 November and 8 January — what might have happened "
            "without my GP's weekly calls and my own determination to hold on. "
            "Good mental health care works. But it only works if people can access it "
            "before the crisis deepens. The wait time is a patient safety issue."
        ),
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
    },
    "Patient AG — Post-Surgical Wound Care": {
        "Month 1 — January (Surgery & Initial Wound Management)": (
            "I underwent an abdominal surgery on 12 January 2026 and was discharged "
            "after four days with a referral to the wound care clinic for post-surgical "
            "management. The discharge nurse explained the signs of wound infection and "
            "gave me clear written instructions for the days before my first wound clinic "
            "appointment. The wound itself is larger than I had anticipated from the "
            "pre-operative conversation and managing it at home in the first days required "
            "more confidence than I felt I had."
        ),
        "Month 2 — February (Wound Clinic — Excellent Care)": (
            "The wound care nurse Jacinta was thorough and gentle. She explained the "
            "healing process for my post-surgical wound clearly and gave me written "
            "instructions to take home. Jacinta examined the wound without causing "
            "unnecessary discomfort and described exactly what she was seeing at each "
            "stage of the examination. The written instructions she provided were "
            "specific to my wound rather than generic, which gave me confidence in "
            "following them independently between appointments."
        ),
        "Month 3 — March (Wound Progressing Well)": (
            "Jacinta reviewed my wound this month and described the granulation tissue "
            "as 'excellent progress'. She updated my written care instructions for the "
            "next stage of healing and showed me photographs of the wound at first "
            "presentation and now to demonstrate the improvement visually. That "
            "comparative view was genuinely motivating. I have had no signs of infection "
            "and my dressing technique has improved with each review. "
            "Jacinta's patience with my questions has been consistent."
        ),
        "Month 4 — April (Near Closure)": (
            "The wound is nearly fully closed this month and Jacinta expects to discharge "
            "me at the next appointment. I have been managing dressing changes independently "
            "for three weeks without difficulty. The written instructions Jacinta provided "
            "in February have been my guide throughout. She mentioned she has been a wound "
            "care nurse for twelve years and it shows — her confidence and expertise in "
            "explaining what is happening at each healing stage has removed my anxiety "
            "about the process entirely."
        ),
        "Month 5 — May (Discharged from Wound Care)": (
            "Jacinta confirmed the wound has fully closed at my May appointment and "
            "discharged me from wound clinic care. She wrote a brief summary for my "
            "GP noting the complete healing and no complications. I have a small scar "
            "that will fade over time. Jacinta was warm in our final session and I "
            "expressed my genuine gratitude for the way she had managed my care. "
            "Good wound care requires technical skill and patient communication in "
            "equal measure. Jacinta has both."
        ),
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
    },
    "Patient AH — Post-Surgical Recovery (Inter-Hospital Transfer, Medication Safety)": {
        "Month 1 — March (Surgery at Logan Hospital & Transfer)": (
            "I received a reminder SMS from Zedoc to complete this survey but the link "
            "didn't work on my Samsung phone. I had to use my husband David Tran's iPhone "
            "instead. The SMS came from number 0437 123 456. I was transferred from Logan "
            "Hospital after my surgery there on 2 March 2026. The handover between hospitals "
            "could have been smoother — my medication list wasn't updated correctly. "
            "I identified the error myself when I recognised the medication name was one "
            "I had been switched from three months earlier. David flagged it with the ward nurse."
        ),
        "Month 2 — April (Medication Error Resolved)": (
            "The medication error identified at transfer has been fully investigated and "
            "my correct medication list was updated in MyHealthRecord within the week. "
            "The ward pharmacist reviewed all my medications before discharge and provided "
            "a printed reconciliation I could share with my GP. David collected me and we "
            "reviewed the list together with the GP at my first post-discharge appointment. "
            "Having an engaged family member present at high-risk handover moments matters — "
            "David's presence likely prevented a preventable harm."
        ),
        "Month 3 — May (Home Recovery)": (
            "Recovery at home has been steady. The surgical site is healing well and I "
            "have not required the district nurse since mid-April. I submitted the Zedoc "
            "survey through David's iPhone as the link remained broken on my Samsung — "
            "the SMS from 0437 123 456 still does not display the clinic name as the sender "
            "which initially caused me to dismiss it as spam. I have asked the patient "
            "experience team to update the sender identity on all survey SMS messages."
        ),
        "Month 4 — June (Patient Safety Involvement)": (
            "I was contacted by the hospital patient safety team to participate in a review "
            "of inter-hospital medication reconciliation processes following my report of the "
            "March 2026 error. David and I prepared together and I described the sequence of "
            "events clearly. The team was receptive and the lead clinician confirmed that a "
            "pharmacist-led transfer checklist is now in development. Contributing to a "
            "systemic change from my own experience of harm has been meaningful."
        ),
        "Month 5 — July (Fully Recovered)": (
            "I am fully recovered from the surgery and returned to work on reduced hours "
            "last month. The experience since March has reinforced for me that medication "
            "safety at hospital boundaries requires active patient participation — I am "
            "glad I knew my medication list well enough to recognise the error. "
            "David's support throughout the recovery and the advocacy process has been "
            "extraordinary. The Zedoc survey link still does not work on my Samsung; "
            "I have reported this three times now."
        ),
        "Month 6 — August (Feedback Acknowledged)": (
            "The hospital has implemented a new transfer protocol for medication reconciliation "
            "following the patient safety review in which I participated. A letter from the "
            "clinical governance team acknowledged my contribution and confirmed the pharmacist "
            "checklist is now in pilot at Logan Hospital and this facility. The Zedoc SMS "
            "sender identity issue has also been raised with the vendor — I received a "
            "confirmation from the patient experience team that this will be corrected in "
            "the next platform update. Persistence does produce change."
        ),
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
    },
    "Patient AI — Cardiology (Proactive Communication, Stress Test)": {
        "Month 1 — January (Referral & Stress Test)": (
            "I was referred to the cardiology clinic following my GP's concern about "
            "exertional chest discomfort during my morning walks. The clinic arranged a "
            "stress test within two weeks of my referral, which I found reassuringly prompt. "
            "I am 62 years old and have a strong family history of cardiac disease — "
            "both my father and his brother had significant cardiac events in their "
            "sixties. The stress test itself was well-managed and the technician explained "
            "each phase clearly."
        ),
        "Month 2 — February (Proactive Call from Dr Richardson)": (
            "The entire cardiology team is first-rate. Dr Richardson personally called me "
            "at home on 0478 234 567 to discuss my stress test results. That kind of "
            "proactive communication is rare and very reassuring. Dr Richardson explained "
            "the findings — a mild perfusion deficit on the lateral wall — in accessible "
            "language and outlined the next steps including a cardiac catheterisation. "
            "The fact that he called before sending the formal letter meant I was informed "
            "rather than anxious when the written results arrived."
        ),
        "Month 3 — March (Catheterisation & Diagnosis)": (
            "The cardiac catheterisation confirmed a single-vessel disease affecting the "
            "left circumflex artery. Dr Richardson met with me and my wife immediately "
            "after the procedure to explain the findings and recommend a percutaneous "
            "coronary intervention. His clear explanation and calm manner in what was a "
            "frightening moment gave us confidence in the plan. The procedure was "
            "scheduled for the following week."
        ),
        "Month 4 — April (PCI Procedure)": (
            "The stent procedure was completed without complication on 8 April 2026. "
            "I was discharged the following day with a comprehensive medication pack and "
            "written instructions. Dr Richardson called me at 0478 234 567 the evening "
            "after discharge to confirm I was well and had no concerns with the medications. "
            "That second personal call — following the stress test call in February — "
            "confirmed for me that the proactive communication was a consistent part of "
            "Dr Richardson's practice, not a one-off gesture."
        ),
        "Month 5 — May (Cardiac Rehabilitation)": (
            "I commenced cardiac rehabilitation this month and the structured exercise "
            "program has been well-calibrated to my post-procedure capacity. I have been "
            "walking thirty minutes daily without symptoms. Dr Richardson reviewed my "
            "six-week post-procedure ECG and described the results as 'very clean'. "
            "The contrast between the chest discomfort I experienced in January and my "
            "current exercise capacity is remarkable. The prompt diagnosis and treatment "
            "timeline has made a material difference to my outcome."
        ),
        "Month 6 — June (Excellent Recovery)": (
            "My three-month cardiac review confirmed the stent is patent and my left "
            "ventricular function has normalised. Dr Richardson called at 0478 234 567 "
            "before sending the written summary — the same approach he has used consistently "
            "throughout my care. I have referred two colleagues with cardiac concerns to "
            "this clinic. The combination of clinical excellence and genuine communication "
            "skill is rare and deserves recognition."
        ),
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
    },
    "Patient AJ — Cardiac Rehabilitation (Accessibility, Dual-Specialist Coordination)": {
        "Month 1 — February (Post-Cardiac Event, Rehab Referral)": (
            "I experienced a significant cardiac event in late January and was admitted to "
            "the Prince Charles Hospital where my cardiologist Dr Andrew Walsh managed my "
            "acute care. On discharge I was referred to this clinic's cardiac rehabilitation "
            "program for the ongoing recovery phase. Dr Walsh has been communicating directly "
            "with Dr Richardson here, which has ensured my management plan was consistent "
            "from the moment I arrived. I hold a temporary mobility permit as a result of "
            "my cardiac event and will need accessible parking for all my appointments."
        ),
        "Month 2 — March (Rehab Progress & Parking Issue)": (
            "The car park needs more disabled bays. I have a temporary mobility permit "
            "after my cardiac rehab and struggled to find a spot on 20 March 2026. "
            "My cardiologist at the Prince Charles Hospital, Dr Andrew Walsh, also "
            "coordinates with Dr Richardson here which gives me great confidence in my "
            "care plan. The rehabilitation program itself has been excellent — the "
            "physiotherapist has been precise about exercise intensity and I have had "
            "no adverse cardiac symptoms during any session. The parking difficulty is "
            "the one aspect that needs urgent attention."
        ),
        "Month 3 — April (Parking Improved)": (
            "I am pleased to report that two additional disabled bays have been added near "
            "the clinic entrance following my March feedback. I attended my April session "
            "and parked without difficulty — the new bays are clearly marked and appropriately "
            "close to the entrance. Dr Richardson confirmed in our appointment that the "
            "parking improvement was a direct response to patient safety feedback. "
            "Dr Walsh at the Prince Charles Hospital received my updated rehabilitation "
            "report and contacted Dr Richardson directly with additional recommendations. "
            "The dual-specialist coordination continues to reassure me."
        ),
        "Month 4 — May (Measurable Improvement)": (
            "My six-minute walk test distance has increased from 320 metres at baseline "
            "to 490 metres this month — a meaningful improvement that reflects genuine "
            "functional recovery. Dr Richardson shared this result with Dr Andrew Walsh "
            "at the Prince Charles Hospital and both specialists agreed to extend the "
            "rehabilitation phase by four weeks to consolidate the gains. "
            "Having two cardiologists working in genuine coordination without duplicating "
            "or contradicting each other is something I did not take for granted after "
            "previous fragmented care experiences."
        ),
        "Month 5 — June (Approaching Discharge)": (
            "The rehabilitation team has recommended a six-month post-discharge monitoring "
            "plan that will be jointly managed by Dr Richardson and Dr Walsh. My temporary "
            "mobility permit is under review and may be downgraded given my improving "
            "functional capacity — a sign of recovery I am proud of. The four additional "
            "disabled bays installed in April have been consistently available. "
            "I have spoken to three other cardiac rehabilitation patients about the "
            "parking feedback process and encouraged them to raise their own concerns."
        ),
        "Month 6 — July (Discharged from Rehabilitation)": (
            "I was formally discharged from the cardiac rehabilitation program this month "
            "with an excellent functional outcome assessment. Dr Richardson conducted "
            "the discharge review and Dr Walsh reviewed the summary letter from the "
            "Prince Charles Hospital. The coordination between these two specialists "
            "has been the defining feature of my cardiac care — neither deferred to the "
            "other unnecessarily and both contributed meaningfully to my recovery plan. "
            "I am walking sixty minutes daily without symptoms. The parking issue I raised "
            "in March, the clinical excellence I experienced throughout, and the dual-specialist "
            "communication I benefited from will all feature in the formal survey I submit today."
        ),
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
    },
}

# ── Ward assignments: patient → [ward per month in chronological order] ───────
PATIENT_WARDS = {
    "Patient A — Oncology": [
        "Oncology Clinic", "Chemotherapy Day Unit", "Chemotherapy Day Unit",
        "Chemotherapy Day Unit", "Chemotherapy Day Unit", "Oncology Outpatient",
        "Oncology Outpatient", "Oncology Outpatient", "Oncology Outpatient",
        "Cancer Wellness Centre", "Oncology Outpatient", "Community Care",
    ],
    "Patient B — Post-Surgical Recovery": [
        "Surgical Ward", "Physiotherapy Unit", "Physiotherapy Unit",
        "Orthopaedic Outpatient", "Orthopaedic Outpatient", "Orthopaedic Outpatient",
        "Orthopaedic Outpatient", "Orthopaedic Outpatient", "Orthopaedic Outpatient",
        "Orthopaedic Outpatient", "Orthopaedic Outpatient", "Community Care",
    ],
    "Patient C — Mental Health (Depression)": [
        "Psychiatry Outpatient", "Psychiatry Outpatient", "Psychiatry Outpatient",
        "Community Mental Health", "Community Mental Health", "Community Mental Health",
        "Community Mental Health", "Community Mental Health", "Community Mental Health",
        "Psychiatry Outpatient", "Psychiatry Outpatient", "Psychiatry Outpatient",
    ],
    "Patient D — Oncology (Breast Cancer)": [
        "Breast Cancer Clinic", "Breast Cancer Clinic", "Chemotherapy Day Unit",
        "Chemotherapy Day Unit", "Chemotherapy Day Unit", "Oncology Outpatient",
        "Oncology Outpatient", "Cancer Wellness Centre", "Oncology Outpatient",
        "Oncology Outpatient", "Oncology Outpatient", "Oncology Outpatient",
    ],
    "Patient E — Sports Injury Recovery (Teenager)": [
        "Emergency Department", "Radiology / Orthopaedic Clinic", "Physiotherapy Unit",
        "Physiotherapy Unit", "Physiotherapy Unit", "Sports Medicine Outpatient",
        "Sports Medicine Outpatient", "Sports Medicine Outpatient", "Sports Medicine Outpatient",
        "Sports Medicine Outpatient", "Sports Medicine Outpatient", "Sports Medicine Outpatient",
    ],
    "Patient F — Orthopaedic Hip Replacement": [
        "Orthopaedic Outpatient", "Orthopaedic Surgical Ward", "Rehabilitation Unit",
        "Rehabilitation Unit", "Orthopaedic Outpatient", "Orthopaedic Outpatient",
        "Orthopaedic Outpatient", "Orthopaedic Outpatient", "Orthopaedic Outpatient",
        "Orthopaedic Outpatient", "Community Care", "Community Care",
    ],
    "Patient G — Multiple Sclerosis (NDIS-Supported)": [
        "Neurology Ward", "Neurology Outpatient", "Neurology Outpatient",
        "Neurology Outpatient", "Neurology Outpatient", "Neurology Outpatient",
        "Neurology Outpatient", "Neurology Outpatient", "Neurology Outpatient",
        "NDIS Community Support", "NDIS Community Support", "NDIS Community Support",
    ],
    "Patient H — Skin Cancer Scare (Dermatology)": [
        "Dermatology Clinic", "Dermatology Clinic", "Dermatology Clinic",
        "Dermatology Clinic", "Dermatology Clinic", "Dermatology Clinic",
        "Dermatology Clinic", "Dermatology Clinic", "Dermatology Clinic",
        "Dermatology Clinic", "Dermatology Clinic", "Dermatology Clinic",
    ],
    "Patient I — Urology (Diagnostic Journey)": [
        "Urology Clinic", "Urology Clinic", "Urology Clinic",
        "Urology Clinic", "Urology Ward", "Urology Outpatient",
        "Urology Outpatient", "Urology Outpatient", "Urology Outpatient",
        "Urology Outpatient", "Urology Outpatient", "Urology Outpatient",
    ],
    "Patient J — Paediatric Cerebral Palsy (Parent Journal)": [
        "Paediatric Ward", "Paediatric Ward", "Developmental Services",
        "Developmental Services", "Developmental Services", "Developmental Services",
        "Developmental Services", "Paediatric Outpatient", "Paediatric Outpatient",
        "Paediatric Outpatient", "Paediatric Outpatient", "Paediatric Outpatient",
    ],
    "Patient K — Stroke Recovery (OT & NDIS)": [
        "Stroke Unit", "Stroke Unit", "Neurology Ward",
        "Rehabilitation Unit", "Rehabilitation Unit", "Rehabilitation Unit",
        "Rehabilitation Unit", "Rehabilitation Unit", "Community Rehab",
        "NDIS Community Support", "NDIS Community Support", "NDIS Community Support",
    ],
    "Patient L — Crohn's Disease (Gastroenterology)": [
        "Gastroenterology Ward", "Gastroenterology Ward", "Gastroenterology Outpatient",
        "Gastroenterology Outpatient", "Gastroenterology Outpatient", "Gastroenterology Outpatient",
        "Gastroenterology Outpatient", "Gastroenterology Outpatient", "Gastroenterology Outpatient",
        "Gastroenterology Outpatient", "Gastroenterology Outpatient", "Gastroenterology Outpatient",
    ],
    "Patient M — Breast Screening Recall": [
        "Breast Clinic", "Breast Clinic", "Breast Clinic",
        "Breast Cancer Unit", "Chemotherapy Day Unit", "Chemotherapy Day Unit",
        "Oncology Outpatient", "Oncology Outpatient", "Oncology Outpatient",
        "Oncology Outpatient", "Oncology Outpatient", "Oncology Outpatient",
    ],
    "Patient N — Continence Clinic (Elderly Patient)": [
        "Continence & Urology Clinic", "Continence & Urology Clinic", "Continence & Urology Clinic",
        "Continence & Urology Clinic", "Continence & Urology Clinic", "Continence & Urology Clinic",
        "Geriatric Outpatient", "Geriatric Outpatient", "Geriatric Outpatient",
        "Geriatric Outpatient", "Geriatric Outpatient", "Geriatric Outpatient",
    ],
    "Patient O — Post-Surgical Recovery (Inter-Hospital Transfer)": [
        "Surgical Ward / ICU", "Surgical Ward", "Surgical Ward",
        "Rehabilitation Unit", "Rehabilitation Unit", "Rehabilitation Unit",
        "Orthopaedic Outpatient", "Orthopaedic Outpatient", "Orthopaedic Outpatient",
        "Orthopaedic Outpatient", "Orthopaedic Outpatient", "Community Care",
    ],
    "Patient P — Cardiac Rehabilitation": [
        "Cardiac Ward", "Cardiac Rehabilitation Unit", "Cardiac Rehabilitation Unit",
        "Cardiac Rehabilitation Unit", "Cardiac Rehabilitation Unit", "Cardiac Rehabilitation Unit",
        "Cardiology Outpatient", "Cardiology Outpatient", "Cardiology Outpatient",
        "Cardiology Outpatient", "Cardiology Outpatient", "Cardiology Outpatient",
    ],
    "Patient Q — COPD (Respiratory Medicine)": [
        "Respiratory Ward", "Respiratory Ward", "Respiratory Outpatient",
        "Respiratory Outpatient", "Respiratory Outpatient", "Respiratory Outpatient",
        "Respiratory Outpatient", "Respiratory Outpatient", "Respiratory Outpatient",
        "Respiratory Outpatient", "Respiratory Outpatient", "Respiratory Outpatient",
    ],
    "Patient R — Musculoskeletal Pain (Elderly, Access Issues)": [
        "Physiotherapy Unit", "Physiotherapy Unit", "Physiotherapy Unit",
        "Rheumatology Outpatient", "Rheumatology Outpatient", "Rheumatology Outpatient",
        "Physiotherapy Unit", "Physiotherapy Unit", "Physiotherapy Unit",
        "Rheumatology Outpatient", "Rheumatology Outpatient", "Community Care",
    ],
    "Patient S — Rheumatoid Arthritis (Medication Review)": [
        "Rheumatology Clinic", "Rheumatology Clinic", "Rheumatology Clinic",
        "Rheumatology Clinic", "Rheumatology Clinic", "Rheumatology Clinic",
        "Rheumatology Clinic", "Rheumatology Clinic", "Rheumatology Clinic",
        "Rheumatology Clinic", "Rheumatology Clinic", "Rheumatology Clinic",
    ],
    "Patient T — Post-Knee Surgery (Physiotherapy)": [
        "Orthopaedic Surgical Ward", "Physiotherapy Unit", "Physiotherapy Unit",
        "Physiotherapy Unit", "Physiotherapy Unit", "Physiotherapy Unit",
        "Sports Medicine Outpatient", "Sports Medicine Outpatient", "Orthopaedic Outpatient",
        "Orthopaedic Outpatient", "Orthopaedic Outpatient", "Community Care",
    ],
    "Patient U — Type 2 Diabetes (New Referral via Ipswich)": [
        "Diabetes Clinic", "Diabetes Clinic", "Diabetes Clinic",
        "Diabetes Clinic", "Diabetes Clinic", "Diabetes Clinic",
        "Diabetes Clinic", "Diabetes Clinic", "Diabetes Clinic",
        "Diabetes Clinic", "Diabetes Clinic", "Endocrinology Outpatient",
    ],
    "Patient V — Type 2 Diabetes (Established, Insulin Adjustment)": [
        "Diabetes Clinic", "Diabetes Clinic", "Diabetes Clinic",
        "Diabetes Clinic", "Diabetes Clinic", "Diabetes Clinic",
        "Diabetes Clinic", "Diabetes Clinic", "Diabetes Clinic",
        "Diabetes Clinic", "Endocrinology Outpatient", "Endocrinology Outpatient",
    ],
    "Patient W — COPD (Long-term, Valued Continuity of Care)": [
        "Respiratory Outpatient", "Respiratory Outpatient", "Respiratory Outpatient",
        "Respiratory Outpatient", "Respiratory Outpatient", "Respiratory Outpatient",
        "Respiratory Outpatient", "Respiratory Outpatient", "Respiratory Outpatient",
        "Respiratory Outpatient", "Respiratory Outpatient", "Respiratory Outpatient",
    ],
    "Patient X — Cardiac Disease (Elderly, Billing & Forms Assistance)": [
        "Cardiology Outpatient", "Cardiology Outpatient", "Cardiology Outpatient",
        "Cardiac Ward", "Cardiac Ward", "Cardiology Outpatient",
        "Cardiology Outpatient", "Cardiology Outpatient", "Cardiology Outpatient",
        "Cardiology Outpatient", "Cardiology Outpatient", "Cardiology Outpatient",
    ],
    "Patient Y — Pregnancy (Antenatal & Midwifery)": [
        "Antenatal Clinic", "Antenatal Clinic", "Antenatal Clinic",
        "Labour Ward / Maternity", "Postnatal Ward", "Postnatal Outpatient",
        "Postnatal Outpatient", "Postnatal Outpatient", "Postnatal Outpatient",
        "Community Midwifery", "Community Midwifery", "Community Midwifery",
    ],
    "Patient Z — Postnatal (Working Parent, Scheduling)": [
        "Postnatal Outpatient", "Postnatal Outpatient", "Postnatal Outpatient",
        "Postnatal Outpatient", "Postnatal Outpatient", "Postnatal Outpatient",
        "Postnatal Outpatient", "Antenatal Clinic", "Antenatal Clinic",
        "Labour Ward / Maternity", "Postnatal Ward", "Community Midwifery",
    ],
    "Patient AA — Haematology (Blood Collection, Skilled Nursing)": [
        "Haematology Outpatient", "Haematology Outpatient", "Haematology Outpatient",
        "Haematology Outpatient", "Haematology Outpatient", "Haematology Outpatient",
        "Haematology Outpatient", "Haematology Outpatient", "Haematology Outpatient",
        "Haematology Outpatient", "Haematology Outpatient", "Community Care",
    ],
    "Patient AB — Endocrinology (Results Portal, Communication)": [
        "Endocrinology Outpatient", "Endocrinology Outpatient", "Endocrinology Outpatient",
        "Endocrinology Outpatient", "Endocrinology Outpatient", "Endocrinology Outpatient",
        "Endocrinology Outpatient", "Endocrinology Outpatient", "Endocrinology Outpatient",
        "Endocrinology Outpatient", "Endocrinology Outpatient", "Endocrinology Outpatient",
    ],
    "Patient AC — Gynaecology (Cultural & Religious Needs)": [
        "Gynaecology Clinic", "Gynaecology Clinic", "Gynaecology Clinic",
        "Gynaecology Ward", "Gynaecology Outpatient", "Gynaecology Outpatient",
        "Gynaecology Outpatient", "Gynaecology Outpatient", "Gynaecology Outpatient",
        "Gynaecology Outpatient", "Gynaecology Outpatient", "Gynaecology Outpatient",
    ],
    "Patient AD — Geriatrics (Language & Interpreter Access)": [
        "Geriatric Assessment Unit", "Geriatric Assessment Unit", "Geriatric Assessment Unit",
        "Geriatric Ward", "Geriatric Outpatient", "Geriatric Outpatient",
        "Geriatric Outpatient", "Community Aged Care", "Community Aged Care",
        "Community Aged Care", "Community Aged Care", "Community Aged Care",
    ],
    "Patient AE — Mental Health (FIFO Worker, Telehealth)": [
        "Psychiatry Outpatient", "Telehealth Mental Health", "Telehealth Mental Health",
        "Telehealth Mental Health", "Telehealth Mental Health", "Telehealth Mental Health",
        "Telehealth Mental Health", "Telehealth Mental Health", "Telehealth Mental Health",
        "Telehealth Mental Health", "Community Mental Health", "Community Mental Health",
    ],
    "Patient AF — Mental Health (Excessive Wait Time)": [
        "Psychiatry Outpatient", "Psychiatry Outpatient", "Psychiatry Outpatient",
        "Psychiatry Outpatient", "Community Mental Health", "Community Mental Health",
        "Community Mental Health", "Community Mental Health", "Community Mental Health",
        "Community Mental Health", "Community Mental Health", "Community Mental Health",
    ],
    "Patient AG — Post-Surgical Wound Care": [
        "Surgical Ward", "Wound Care Clinic", "Wound Care Clinic",
        "Wound Care Clinic", "Wound Care Clinic", "Community Wound Care",
        "Orthopaedic Outpatient", "Orthopaedic Outpatient", "Community Care",
        "Community Care", "Community Care", "Community Care",
    ],
    "Patient AH — Post-Surgical Recovery (Inter-Hospital Transfer, Medication Safety)": [
        "Surgical Ward / ICU", "Surgical Ward", "Community Care",
        "Community Care", "Community Care", "Community Care",
        "Community Care", "Community Care", "Community Care",
        "Community Care", "Orthopaedic Outpatient", "Orthopaedic Outpatient",
    ],
    "Patient AI — Cardiology (Proactive Communication, Stress Test)": [
        "Cardiology Outpatient", "Cardiology Outpatient", "Cardiac Catheterisation Lab",
        "Cardiac Ward", "Cardiac Rehabilitation Unit", "Cardiology Outpatient",
        "Cardiology Outpatient", "Cardiology Outpatient", "Cardiology Outpatient",
        "Cardiology Outpatient", "Cardiology Outpatient", "Cardiology Outpatient",
    ],
    "Patient AJ — Cardiac Rehabilitation (Accessibility, Dual-Specialist Coordination)": [
        "Cardiac Ward", "Cardiac Rehabilitation Unit", "Cardiac Rehabilitation Unit",
        "Cardiac Rehabilitation Unit", "Cardiac Rehabilitation Unit", "Cardiac Rehabilitation Unit",
        "Cardiology Outpatient", "Cardiology Outpatient", "Cardiology Outpatient",
        "Cardiology Outpatient", "Cardiology Outpatient", "Cardiology Outpatient",
    ],
}

_SPECIALTY_WARD_DEFAULTS = {
    "oncology": "Oncology Outpatient", "cancer": "Oncology Outpatient",
    "surgical": "Surgical Ward", "post-surgical": "Surgical Ward",
    "mental health": "Psychiatry Outpatient", "depression": "Community Mental Health",
    "sports injury": "Physiotherapy Unit", "orthopaedic": "Orthopaedic Outpatient",
    "multiple sclerosis": "Neurology Outpatient", "stroke": "Neurology Ward",
    "dermatology": "Dermatology Clinic", "urology": "Urology Outpatient",
    "paediatric": "Paediatric Ward", "crohn": "Gastroenterology Outpatient",
    "cardiac": "Cardiology Outpatient", "copd": "Respiratory Outpatient",
    "respiratory": "Respiratory Outpatient", "diabetes": "Diabetes Clinic",
    "pregnancy": "Maternity Ward", "postnatal": "Postnatal Ward",
    "haematology": "Haematology Outpatient", "endocrinology": "Endocrinology Outpatient",
    "gynaecology": "Gynaecology Clinic", "geriatric": "Geriatric Assessment Unit",
    "rheumatoid": "Rheumatology Clinic", "musculoskeletal": "Physiotherapy Unit",
    "continence": "Continence & Urology Clinic", "wound care": "Wound Care Clinic",
}


def get_ward(patient_name, month_key):
    """Return the ward label for a given patient and month key."""
    ward_list   = PATIENT_WARDS.get(patient_name, [])
    month_keys  = list(PATIENT_SAMPLES.get(patient_name, {}).keys())
    try:
        idx = month_keys.index(month_key)
        if idx < len(ward_list):
            return ward_list[idx]
    except ValueError:
        pass
    # Fallback: derive from patient specialty
    pname_lower = patient_name.lower()
    for spec, ward in _SPECIALTY_WARD_DEFAULTS.items():
        if spec in pname_lower:
            return ward
    return "General Ward"


PATIENT_NAMES = list(PATIENT_SAMPLES.keys())

# Peer group: Queensland HHS classification (4 : 3 : 4 : 5 over 16 HHSs).
# Proportionally expanded to 36 patients as 9 : 7 : 9 : 11 with a fixed seed.
_PG_LABELS  = ["Large metro", "Outer metro", "Regional", "Outer regional / rural / remote"]
_PG_COUNTS  = [9, 7, 9, 11]
_pg_pool    = [lbl for lbl, n in zip(_PG_LABELS, _PG_COUNTS) for _ in range(n)]
import random as _rng; _rng.seed(42); _rng.shuffle(_pg_pool)
PATIENT_PEER_GROUP: dict[str, str] = dict(zip(PATIENT_NAMES, _pg_pool))

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

        model_type = MODEL_LABEL_TO_TYPE.get(model_label, ModelType.BERT_HC_V2)
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

    def _trunc_str(s, max_chars=600):
        """Truncate plain text so no single PDF row exceeds page height."""
        if len(s) <= max_chars:
            return s
        return s[:max_chars] + f"  … ({len(s) - max_chars} chars omitted)"

    def _tok_str(lst, max_n=50):
        """Truncate token lists so no single PDF row exceeds page height."""
        if len(lst) <= max_n:
            return ", ".join(lst)
        return ", ".join(lst[:max_n]) + f"  … (+{len(lst) - max_n} more)"

    preproc_rows = [
        ("Cleaned",    _trunc_str(preprocess.cleaned_text)),
        ("Removed",    _trunc_str(preprocess.removed_text)),
        ("Normalized", _trunc_str(preprocess.normalized_text)),
        ("Tokenized",  _tok_str(preprocess.tokenized_text)),
        ("Stemmed",    _tok_str(preprocess.stemmed_text)),
        ("Lemmatized", _tok_str(preprocess.lemmatized_text)),
        ("Word count", str(len(preprocess.tokenized_text))),
    ]
    # Each row is its own mini-table so it becomes an independent flowable.
    # This lets ReportLab start any oversized row on a fresh page rather than
    # failing because a multi-row table can't be split mid-cell.
    pre_row_style = TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), colors.HexColor("#f8f9fa")),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#dee2e6")),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ])
    for k, v in preproc_rows:
        row_tbl = Table(
            [[Paragraph(f"<b>{k}</b>", body), Paragraph(v, mono)]],
            colWidths=[1.1 * inch, 5.8 * inch],
        )
        row_tbl.setStyle(pre_row_style)
        story.append(row_tbl)

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
    # Header row as its own table
    hdr_tbl = Table(
        [[Paragraph("<b>Category</b>", body), Paragraph("<b>Count</b>", body), Paragraph("<b>Words</b>", body)]],
        colWidths=[1.2 * inch, 0.7 * inch, 5.0 * inch],
    )
    hdr_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#8e44ad")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#bdc3c7")),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]))
    story.append(hdr_tbl)
    # One mini-table per category row so each is an independent flowable
    dist_row_style = TableStyle([
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#bdc3c7")),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ])
    for label, words in word_dist.word_lists.items():
        word_str = _tok_str(words, max_n=50) if words else "—"
        row_tbl = Table(
            [[Paragraph(label.upper(), body), Paragraph(str(len(words)), body), Paragraph(word_str, mono)]],
            colWidths=[1.2 * inch, 0.7 * inch, 5.0 * inch],
        )
        row_tbl.setStyle(dist_row_style)
        story.append(row_tbl)

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

        model_type = MODEL_LABEL_TO_TYPE.get(model_label, ModelType.BERT_HC_V2)
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

        # Emoji display labels for emotion model; all other models use standard labels
        if model_type == ModelType.EMOTION:
            display_labels = [f"{l} {EMOTION_EMOJI.get(l, '')}" for l in labels]
            dist_display_labels = [
                f"{k.upper()} {EMOTION_EMOJI.get(k.upper(), '')}"
                for k in word_dist.distribution
            ]
            sentiment_display = f"{sentiment} {EMOTION_EMOJI.get(sentiment, '')}"
        else:
            display_labels      = labels
            dist_display_labels = None
            sentiment_display   = sentiment

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
  <div style="color:#ffffff;margin-top:6px">{config['display']} &nbsp;·&nbsp; {len(tokenized)} words</div>
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


# ── Topic & Theme Analytics ───────────────────────────────────────────────────
_TOPIC_API_BASE       = "https://5kzn638wee.execute-api.ap-southeast-2.amazonaws.com/prod"
_TOPIC_API_KEY        = os.getenv("TOPIC_API_KEY", "5aDXnKHdCTXNVh10c27oadWkkZrAfqT2EAqQHTI6")
_TOPIC_MODELS         = ["bertopic_mini", "bertopic_mpnet", "lda", "lsi", "hdp", "nmf"]
_TOPIC_MODEL_DISPLAY  = {
    "bertopic_mini":  "BERTopic (MiniLM)",
    "bertopic_mpnet": "BERTopic (MPNet)",
    "lda": "LDA", "lsi": "LSI", "hdp": "HDP", "nmf": "NMF",
}
_TOPIC_MODEL_CHOICES  = [_TOPIC_MODEL_DISPLAY[m] for m in _TOPIC_MODELS]
_TOPIC_DISPLAY_TO_KEY = {v: k for k, v in _TOPIC_MODEL_DISPLAY.items()}

_SENTIMENT_LABEL_COLORS = {
    "NEGATIVE":  "#e74c3c",
    "NEUTRAL":   "#95a5a6",
    "POSITIVE":  "#27ae60",
    "ANGER":     "#c0392b",
    "DISGUST":   "#8e44ad",
    "FEAR":      "#e67e22",
    "JOY":       "#27ae60",
    "SADNESS":   "#2980b9",
    "SURPRISE":  "#f1c40f",
    "1 STAR":    "#e74c3c",
    "2 STARS":   "#e67e22",
    "3 STARS":   "#f39c12",
    "4 STARS":   "#2ecc71",
    "5 STARS":   "#27ae60",
}


def _build_topic_pie_chart(topics, top_n, topic_model_label):
    slices = topics[:top_n]
    labels = [t["topic_name"] for t in slices]
    values = [round(t["score"] * 100, 2) for t in slices]
    colors = [
        "#8e44ad", "#3498db", "#27ae60", "#e67e22",
        "#e74c3c", "#1abc9c", "#f39c12", "#2980b9",
    ][:len(slices)]
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.35,
        marker=dict(colors=colors, line=dict(color="#fff", width=2)),
        textinfo="label+percent",
        textposition="outside",
        textfont=dict(size=11, color="#000000"),
        outsidetextfont=dict(size=11, color="#000000"),
        hovertemplate="<b>%{label}</b><br>Score: %{value:.1f}%<br>Portion: %{percent}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(
            text=f"Top {len(slices)} Topics — {topic_model_label}",
            x=0.5, font=dict(size=14),
        ),
        showlegend=False,
        margin=dict(t=60, b=20, l=20, r=20),
        paper_bgcolor="#f0fff4",
        height=400,
    )
    return fig


def _compute_quality_score(probs, labels):
    """Map sentiment probabilities → healthcare quality score 1–10."""
    lu = [l.upper() for l in labels]
    _pos = {"POSITIVE", "JOY", "4 STARS", "5 STARS"}
    _neu = {"NEUTRAL", "SURPRISE", "3 STARS"}
    _neg = {"NEGATIVE", "ANGER", "DISGUST", "FEAR", "SADNESS", "1 STAR", "2 STARS"}
    pos = sum(p for l, p in zip(lu, probs) if l in _pos)
    neu = sum(p for l, p in zip(lu, probs) if l in _neu)
    neg = sum(p for l, p in zip(lu, probs) if l in _neg)
    total = pos + neu + neg
    if total < 1e-6:
        return 5.0
    weighted = (pos * 1.0 + neu * 0.5 + neg * 0.0) / total
    return round(max(1.0, min(10.0, 1 + 9 * weighted)), 1)


def _compute_risk_label(sentiment, score):
    """Assign risk level based solely on quality score."""
    if score <= 3.0:
        return "High"
    if 4.0 <= score <= 7.0:
        return "Medium"
    if score >= 8.0:
        return "Low"
    return "Medium"  # fallback for 3.0 < score < 4.0 or 7.0 < score < 8.0


def _build_monthly_summary_table(months, wards, sentiments, scores, risk_labels):
    """HTML table showing Month, Ward, Sentiment, Score, Risk as separate columns."""
    _risk_bg = {"High": "#fdecea", "Medium": "#fff3e0", "Low": "#e8f5e9"}
    rows = ""
    for i, (m, w, s, sc, r) in enumerate(zip(months, wards, sentiments, scores, risk_labels)):
        bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
        rows += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:8px 12px;font-weight:700;color:#000;">{m}</td>'
            f'<td style="padding:8px 12px;color:#000;">{w}</td>'
            f'<td style="padding:8px 12px;color:#000;">{s}</td>'
            f'<td style="padding:8px 12px;text-align:center;font-weight:700;color:#000;">{sc:.1f}</td>'
            f'<td style="padding:8px 12px;text-align:center;background:{_risk_bg.get(r,"#fff")};'
            f'font-weight:700;color:#000;">{r}</td>'
            f'</tr>'
        )
    header_style = "padding:8px 12px;background:#2c3e50;color:#fff;text-align:left;"
    return (
        '<div style="overflow-x:auto;margin-top:12px;">'
        '<table style="width:100%;border-collapse:collapse;font-size:0.88rem;">'
        '<thead><tr>'
        f'<th style="{header_style}">Month</th>'
        f'<th style="{header_style}">Ward</th>'
        f'<th style="{header_style}">Sentiment</th>'
        f'<th style="{header_style}text-align:center;">Score (1–10)</th>'
        f'<th style="{header_style}text-align:center;">Risk</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
    )


def _build_ward_risk_chart(wards, risk_labels):
    """Horizontal stacked bar: risk_label distribution across unique wards."""
    from collections import defaultdict
    _risk_order  = ["High", "Medium", "Low"]
    _risk_colors = {"High": "#e74c3c", "Medium": "#e67e22", "Low": "#27ae60"}

    ward_risk = defaultdict(lambda: defaultdict(int))
    for w, r in zip(wards, risk_labels):
        ward_risk[w][r] += 1

    unique_wards = list(dict.fromkeys(wards))

    fig = go.Figure()
    for risk in _risk_order:
        counts = [ward_risk[w][risk] for w in unique_wards]
        fig.add_trace(go.Bar(
            name=risk,
            y=unique_wards,
            x=counts,
            orientation="h",
            marker_color=_risk_colors[risk],
            text=[str(c) if c > 0 else "" for c in counts],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="white", size=11),
            hovertemplate=(
                "<b>%{y}</b><br>"
                f"Risk: {risk}<br>"
                "Months: %{x}"
                "<extra></extra>"
            ),
        ))

    fig.update_layout(
        barmode="stack",
        title=dict(text="Risk Distribution Across Wards", x=0.5, font=dict(size=14)),
        xaxis=dict(title="Number of Months", dtick=1),
        yaxis=dict(title=""),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        height=max(300, len(unique_wards) * 65 + 140),
        margin=dict(l=20, r=20, t=80, b=40),
        paper_bgcolor="#f0fff4",
        plot_bgcolor="#f0fff4",
    )
    return fig


def _build_topic_risk_chart(monthly_all_topics, risk_labels, top_n_names):
    """Horizontal stacked bar: risk distribution across Top-N topics.
    Each month contributes a count for every topic in its top-N list (rank #1, #2, #3…).
    """
    from collections import defaultdict
    _risk_order  = ["High", "Medium", "Low"]
    _risk_colors = {"High": "#e74c3c", "Medium": "#e67e22", "Low": "#27ae60"}

    topic_risk = defaultdict(lambda: defaultdict(int))
    for topics_in_month, risk in zip(monthly_all_topics, risk_labels):
        for topic in topics_in_month:
            if topic in top_n_names:
                topic_risk[topic][risk] += 1

    # Always show all Top-N topics in order
    unique_topics = list(top_n_names)

    fig = go.Figure()
    for risk in _risk_order:
        counts = [topic_risk[t][risk] for t in unique_topics]
        fig.add_trace(go.Bar(
            name=risk,
            y=unique_topics,
            x=counts,
            orientation="h",
            marker_color=_risk_colors[risk],
            text=[str(c) if c > 0 else "" for c in counts],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="white", size=11),
            hovertemplate=(
                "<b>%{y}</b><br>"
                f"Risk: {risk}<br>"
                "Months: %{x}"
                "<extra></extra>"
            ),
        ))

    fig.update_layout(
        barmode="stack",
        title=dict(text="Risk Distribution Across Top Topics", x=0.5, font=dict(size=14)),
        xaxis=dict(title="Number of Months", dtick=1),
        yaxis=dict(title=""),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        height=max(300, len(unique_topics) * 65 + 140),
        margin=dict(l=20, r=20, t=80, b=40),
        paper_bgcolor="#f0fff4",
        plot_bgcolor="#f0fff4",
    )
    return fig


def _build_quality_score_chart(months, scores, risk_labels, wards, sentiment_model_label):
    _risk_color = {"High": "#e74c3c", "Medium": "#e67e22", "Low": "#27ae60"}
    bar_colors  = [_risk_color[r] for r in risk_labels]
    bar_text    = [f"{s:.1f}  [{r}]" for s, r in zip(scores, risk_labels)]
    x_labels    = [f"{m}<br><sub>{w}</sub>" for m, w in zip(months, wards)]
    hover_text = [
        f"<b>%{{x}}</b><br>Score: {s:.1f} / 10<br>Risk: <b>{r}</b>"
        for s, r in zip(scores, risk_labels)
    ]
    fig = go.Figure(go.Bar(
        x=x_labels,
        y=scores,
        marker_color=bar_colors,
        text=bar_text,
        textposition="outside",
        textfont=dict(size=11, color="#000"),
        customdata=list(zip(risk_labels, wards)),
        hovertemplate="<b>%{x}</b><br>Ward: %{customdata[1]}<br>Score: %{y:.1f} / 10<br>Risk: <b>%{customdata[0]}</b><extra></extra>",
    ))
    fig.update_layout(
        title=dict(
            text=f"Monthly Healthcare Quality Score & Risk  ·  {sentiment_model_label}",
            x=0.5, font=dict(size=14),
        ),
        xaxis=dict(title="Month", tickangle=-30),
        yaxis=dict(title="Score (1 – 10)", range=[0, 12]),
        showlegend=False,
        height=400,
        margin=dict(l=20, r=20, t=60, b=80),
        paper_bgcolor="#f0fff4",
        plot_bgcolor="#f0fff4",
    )
    return fig


def _build_monthly_topic_chart(sections, topic_model_key, topic_model_label, top_n):
    from concurrent.futures import ThreadPoolExecutor

    _palette = [
        "#8e44ad", "#3498db", "#27ae60", "#e67e22", "#e74c3c",
        "#1abc9c", "#f39c12", "#2980b9", "#c0392b", "#16a085",
        "#d35400", "#7f8c8d", "#2c3e50", "#6c3483", "#117a65",
    ]

    def _fetch(args):
        label, body = args
        try:
            r = requests.post(
                f"{_TOPIC_API_BASE}/classify",
                headers={"x-api-key": _TOPIC_API_KEY, "Content-Type": "application/json"},
                json={"text": body, "models": [topic_model_key], "top_n": top_n},
                timeout=20,
            )
            r.raise_for_status()
            cls   = r.json()["results"][0]["classifications"].get(topic_model_key, {})
            topics = cls.get("top_topics", [])
            return label, topics
        except Exception:
            return label, []

    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(_fetch, sections))

    def _short(lbl):
        m = re.match(r'(Month\s*\d+)', lbl, re.IGNORECASE)
        return m.group(1) if m else lbl.split("—")[0].strip()

    months = [_short(r[0]) for r in results]

    # Assign stable topic colors across all months
    all_topic_names = list(dict.fromkeys(
        t["topic_name"]
        for _, topics in results
        for t in topics
    ))
    color_map = {name: _palette[i % len(_palette)] for i, name in enumerate(all_topic_names)}

    # Add traces in REVERSE rank order so rank-1 ends up on top of the stack
    fig = go.Figure()
    for rank_idx in range(top_n - 1, -1, -1):
        y_scores, topic_names, bar_colors = [], [], []
        for _, topics in results:
            if rank_idx < len(topics):
                t = topics[rank_idx]
                y_scores.append(round(t["score"] * 100, 1))
                topic_names.append(t["topic_name"])
                bar_colors.append(color_map[t["topic_name"]])
            else:
                y_scores.append(0.0)
                topic_names.append("—")
                bar_colors.append("#eeeeee")

        fig.add_trace(go.Bar(
            name=f"Rank #{rank_idx + 1}",
            x=months,
            y=y_scores,
            marker_color=bar_colors,
            customdata=topic_names,
            text=topic_names,
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(size=10, color="#fff"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                f"<b>Rank:</b> #{rank_idx + 1}<br>"
                "<b>Topic:</b> %{customdata}<br>"
                "<b>Score:</b> %{y:.1f}%"
                "<extra></extra>"
            ),
        ))

    fig.update_layout(
        title=dict(
            text=f"Monthly Top-{top_n} Topic Distribution — {topic_model_label}",
            x=0.5, font=dict(size=14),
        ),
        xaxis=dict(title="Month", tickangle=-30),
        yaxis=dict(title="Confidence Score (%)"),
        barmode="stack",
        showlegend=False,
        height=480,
        margin=dict(l=20, r=20, t=60, b=40),
        paper_bgcolor="#f0fff4",
        plot_bgcolor="#f0fff4",
    )
    # All top-N topic names per month (for risk-per-topic chart)
    monthly_all_topics = [
        [t["topic_name"] for t in r[1]] if r[1] else []
        for r in results
    ]
    return fig, monthly_all_topics


def _build_topic_stacked_chart(topics, sentiment_model_type, labels, top_n):
    topic_names = [t["topic_name"] for t in topics[:top_n]]
    all_probs   = []
    for name in topic_names:
        try:
            _, probs = analyze_sentiment(name, sentiment_model_type)
            all_probs.append([p * 100 for p in probs])
        except Exception:
            all_probs.append([0.0] * len(labels))

    # Reorder labels: Positive → Neutral → Negative (left to right)
    _pos_l = {"POSITIVE", "JOY", "4 STARS", "5 STARS"}
    _neu_l = {"NEUTRAL", "SURPRISE", "3 STARS"}
    def _rank(lbl):
        u = lbl.upper()
        if u in _pos_l: return 0
        if u in _neu_l: return 1
        return 2
    ordered_idx = sorted(range(len(labels)), key=lambda i: _rank(labels[i]))

    # Build stacked horizontal bars — reverse so rank #1 is at the top
    y_names = topic_names[::-1]
    fig = go.Figure()
    for i in ordered_idx:
        label = labels[i]
        x_vals = [all_probs[j][i] for j in range(len(topic_names))][::-1]
        color      = _SENTIMENT_LABEL_COLORS.get(label, f"hsl({i*45},65%,50%)")
        raw_scores = [v / 100 for v in x_vals]
        fig.add_trace(go.Bar(
            name=label,
            y=y_names,
            x=x_vals,
            orientation="h",
            marker_color=color,
            text=[f"{v:.1f}%" for v in x_vals],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="white", size=11),
            customdata=raw_scores,
            hovertemplate=(
                "<b>Topic:</b> %{y}<br>"
                "<b>Sentiment:</b> %{fullData.name}<br>"
                "<b>Portion:</b> %{x:.1f}%<br>"
                "<b>Score:</b> %{customdata:.3f}"
                "<extra></extra>"
            ),
        ))

    fig.update_layout(
        barmode="stack",
        height=max(320, len(topic_names) * 70 + 120),
        title=dict(text="Sentiment Distribution Across Top Topics", x=0.5, font=dict(size=14)),
        xaxis=dict(title="Sentiment probability (%)", range=[0, 100]),
        yaxis=dict(title=""),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=20, r=20, t=80, b=40),
        paper_bgcolor="#f0fff4",
        plot_bgcolor="#f0fff4",
    )
    return fig


def _build_topic_html_report(text, topics, consensus_topic, sent_model_label,
                              topic_model_label, labels, all_probs, top_n, elapsed):
    from datetime import datetime
    topic_rows = "".join(
        f'<tr><td style="padding:6px 10px;font-weight:700;">#{i+1}</td>'
        f'<td style="padding:6px 14px;">{t["topic_name"]}</td>'
        f'<td style="padding:6px 12px;text-align:center;">{t["score"]*100:.1f}%</td></tr>'
        for i, t in enumerate(topics[:top_n])
    )
    sent_rows = "".join(
        f'<tr><td style="padding:6px 10px;">{topics[j]["topic_name"]}</td>'
        + "".join(
            f'<td style="padding:6px 12px;text-align:center;">{all_probs[j][i]*100:.1f}%</td>'
            for i in range(len(labels))
        ) + "</tr>"
        for j in range(min(top_n, len(topics)))
    )
    label_ths = "".join(f'<th style="background:#2980b9;color:#fff;padding:8px 12px;">{l}</th>' for l in labels)
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Topic &amp; Theme Analysis Report</title>
<style>body{{font-family:Arial,sans-serif;max-width:960px;margin:40px auto;padding:0 20px;}}
h1{{color:#8e44ad;}} h2{{color:#6c3483;border-bottom:2px solid #d7bde2;padding-bottom:4px;}}
table{{border-collapse:collapse;width:100%;margin-bottom:20px;}} th,td{{border:1px solid #d7bde2;}}
.badge{{display:inline-block;background:#27ae60;color:#fff;border-radius:20px;padding:5px 16px;font-weight:700;}}
</style></head><body>
<h1>Topic &amp; Theme Analysis Report</h1>
<p style="color:#888;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} &nbsp;|&nbsp;
Topic model: <b>{topic_model_label}</b> &nbsp;|&nbsp; Sentiment model: <b>{sent_model_label}</b> &nbsp;|&nbsp;
Elapsed: {elapsed:.1f}s</p>
<h2>Input Text</h2>
<pre style="background:#f4ecf7;padding:12px;border-radius:6px;white-space:pre-wrap;">{text[:1000]}{"…" if len(text)>1000 else ""}</pre>
<h2>Top Topic</h2>
<p><span class="badge">{consensus_topic}</span></p>
<h2>Top {top_n} Topics</h2>
<table><thead><tr>
<th style="background:#8e44ad;color:#fff;padding:8px 10px;">Rank</th>
<th style="background:#8e44ad;color:#fff;padding:8px 14px;">Topic</th>
<th style="background:#8e44ad;color:#fff;padding:8px 12px;">Score</th>
</tr></thead><tbody>{topic_rows}</tbody></table>
<h2>Sentiment Distribution per Topic</h2>
<table><thead><tr>
<th style="background:#2980b9;color:#fff;padding:8px 14px;">Topic</th>{label_ths}
</tr></thead><tbody>{sent_rows}</tbody></table>
</body></html>"""
    tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
    tmp.write(html)
    tmp.close()
    return tmp.name


def run_topic_analysis(text_input, patient_name, topic_model_label, sentiment_model_label, top_n):
    if not text_input or not text_input.strip():
        err = ('<span style="background:#e74c3c;color:#fff;border-radius:20px;'
               'padding:4px 14px;font-size:0.85rem;font-weight:600;">'
               '⚠ No text loaded — please load patient data first</span>')
        return err, "", "", None, None, None, None, None, None, ""
    if len(text_input.strip().split()) < 4:
        err = ('<span style="background:#e74c3c;color:#fff;border-radius:20px;'
               'padding:4px 14px;font-size:0.85rem;font-weight:600;">'
               '⚠ Text too short (minimum 4 words)</span>')
        return err, "", "", None, None, None, None, None, None, ""

    topic_model_key  = _TOPIC_DISPLAY_TO_KEY.get(topic_model_label, "bertopic_mini")
    sentiment_type   = MODEL_LABEL_TO_TYPE.get(sentiment_model_label, "bert_hc_v2")
    sentiment_labels = SUPPORTED_MODELS[sentiment_type]["labels"]

    try:
        resp = requests.post(
            f"{_TOPIC_API_BASE}/classify",
            headers={"x-api-key": _TOPIC_API_KEY, "Content-Type": "application/json"},
            json={"text": text_input.strip(), "models": [topic_model_key], "top_n": int(top_n)},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        err = (f'<span style="background:#e74c3c;color:#fff;border-radius:20px;'
               f'padding:4px 14px;font-size:0.85rem;font-weight:600;">'
               f'⚠ API error: {str(exc)[:120]}</span>')
        return err, "", "", None, None, None, None, None, None, ""

    classifications = data["results"][0]["classifications"]
    elapsed  = data.get("elapsed_sec", 0)
    topics       = classifications.get(topic_model_key, {}).get("top_topics", [])[:int(top_n)]
    top_n_names  = [t["topic_name"] for t in topics]

    status_html = (
        f'<span style="background:#27ae60;color:#fff;border-radius:20px;'
        f'padding:4px 14px;font-size:0.85rem;font-weight:600;">'
        f'✓ Complete — {elapsed:.1f}s &nbsp;|&nbsp; '
        f'Topic: <b>{topic_model_label}</b> &nbsp;|&nbsp; Sentiment: <b>{sentiment_model_label}</b></span>'
    )

    top1 = topics[0]["topic_name"] if topics else "—"
    consensus_html = (
        f'<div style="margin:10px 0;">'
        f'<span style="font-size:0.85rem;color:#6b7280;margin-right:8px;font-weight:600;">Top topic:</span>'
        f'<span style="background:#27ae60;color:#fff !important;border-radius:20px;'
        f'padding:5px 18px;font-size:1rem;font-weight:700;">{top1}</span>'
        f'<span style="font-size:0.82rem;color:#fff !important;margin-left:10px;'
        f'background:#27ae60;border-radius:12px;padding:2px 10px;">'
        f'{topics[0]["score"]*100:.1f}% confidence</span></div>'
        if topics else ""
    )

    table_html = _build_topic_pie_chart(topics, int(top_n), topic_model_label)
    fig        = _build_topic_stacked_chart(topics, sentiment_type, sentiment_labels, int(top_n))

    # Collect probs for report
    all_probs = []
    for t in topics:
        try:
            _, probs = analyze_sentiment(t["topic_name"], sentiment_type)
            all_probs.append(probs)
        except Exception:
            all_probs.append([0.0] * len(sentiment_labels))

    report = _build_topic_html_report(
        text_input, topics, top1, sentiment_model_label,
        topic_model_label, sentiment_labels, all_probs, int(top_n), elapsed,
    )

    # Per-month analysis — only when ≥2 month sections are present
    sections = _parse_month_sections(text_input)

    monthly_fig        = None
    quality_fig        = None
    monthly_all_topics = []
    wards              = []
    risk_labels        = []
    sentiments         = []
    quality_scores     = []
    summary_table      = ""
    if len(sections) >= 2:
        monthly_fig, monthly_all_topics = _build_monthly_topic_chart(
            sections, topic_model_key, topic_model_label, int(top_n)
        )
        def _short_m(lbl):
            m = re.match(r'(Month\s*\d+)', lbl, re.IGNORECASE)
            return m.group(1) if m else lbl.split("—")[0].strip()
        month_labels   = [_short_m(s[0]) for s in sections]
        quality_scores = []
        risk_labels    = []
        sentiments     = []
        wards          = [get_ward(patient_name, s[0]) for s in sections]
        for _, body in sections:
            try:
                redacted_body, _ = redact_pii(body)
                dominant_sent, month_probs = analyze_sentiment(redacted_body, sentiment_type)
                score = _compute_quality_score(month_probs, sentiment_labels)
                quality_scores.append(score)
                risk_labels.append(_compute_risk_label(dominant_sent, score))
                sentiments.append(dominant_sent)
            except Exception:
                quality_scores.append(5.0)
                risk_labels.append("Low")
                sentiments.append("—")
        quality_fig   = _build_quality_score_chart(
            month_labels, quality_scores, risk_labels, wards, sentiment_model_label
        )
        summary_table = _build_monthly_summary_table(
            month_labels, wards, sentiments, quality_scores, risk_labels
        )

    has_months     = len(sections) >= 2
    ward_risk_fig  = _build_ward_risk_chart(wards, risk_labels) if has_months else None
    topic_risk_fig = _build_topic_risk_chart(monthly_all_topics, risk_labels, top_n_names) if has_months else None
    return status_html, consensus_html, table_html, fig, ward_risk_fig, topic_risk_fig, report, monthly_fig, quality_fig, summary_table if len(sections) >= 2 else ""


# ── Statewide Sentiment & HHS Profile ────────────────────────────────────────
_SENTIMENT_CATEGORY = {
    "POSITIVE": "Positive", "JOY": "Positive", "4 STARS": "Positive", "5 STARS": "Positive",
    "NEGATIVE": "Negative", "ANGER": "Negative", "DISGUST": "Negative",
    "FEAR": "Negative", "SADNESS": "Negative", "1 STAR": "Negative", "2 STARS": "Negative",
    "NEUTRAL": "Neutral", "SURPRISE": "Neutral", "3 STARS": "Neutral",
}
_CAT_COLORS = {"Positive": "#27ae60", "Negative": "#c0392b", "Neutral": "#7f8c8d"}
_ALL_MODEL_TYPES = list(ModelType)


def _build_statewide_kpi_html(pcts, total):
    cards = [
        ("Positive", pcts.get("Positive", 0), "#27ae60"),
        ("Negative", pcts.get("Negative", 0), "#c0392b"),
        ("Neutral",  pcts.get("Neutral",  0), "#7f8c8d"),
    ]
    items = ""
    for label, pct, color in cards:
        items += (
            f'<div style="flex:1;min-width:180px;background:#fff;border-radius:12px;'
            f'padding:24px 20px;box-shadow:0 2px 8px rgba(0,0,0,0.08);text-align:center;margin:6px;">'
            f'<div style="font-size:2.6rem;font-weight:800;color:{color};">{pct}%</div>'
            f'<div style="font-size:0.82rem;font-weight:700;letter-spacing:0.08em;'
            f'color:{color};margin-top:6px;">{label.upper()}</div>'
            f'</div>'
        )
    subtitle = (
        f'<div style="font-size:0.78rem;color:#fff;margin-top:4px;">'
        f'Based on {total:,} sentiment classifications '
        f'({len(PATIENT_NAMES)} patients × {len(list(PATIENT_SAMPLES.values())[0])} months)'
        f'</div>'
    )
    return (
        f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin:12px 0;">{items}</div>'
        f'{subtitle}'
    )


def _build_statewide_bar_chart(pcts, model_label=""):
    cats   = ["Positive", "Negative", "Neutral"]
    values = [pcts.get(c, 0) for c in cats]
    colors = [_CAT_COLORS[c] for c in cats]
    fig = go.Figure()
    for cat, val, col in zip(cats, values, colors):
        fig.add_trace(go.Bar(
            name=f"{cat} ({val}%)",
            x=[val], y=["Statewide"],
            orientation="h",
            marker_color=col,
            text=f"{val}%" if val >= 4 else "",
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="white", size=13, family="Arial Black"),
            hovertemplate=f"<b>{cat}</b>: {val}%<extra></extra>",
        ))
    model_str = f"  ·  {model_label}" if model_label else ""
    fig.update_layout(
        barmode="stack",
        title=dict(
            text=f"Statewide Sentiment Distribution — All Months · All {len(PATIENT_NAMES)} Patients{model_str}",
            x=0.5, font=dict(size=13),
        ),
        xaxis=dict(range=[0, 100], showticklabels=False, showgrid=False),
        yaxis=dict(showticklabels=False),
        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
        height=200,
        margin=dict(l=20, r=20, t=60, b=70),
        paper_bgcolor="#f8f9fa",
        plot_bgcolor="#f8f9fa",
    )
    return fig


def _build_per_patient_chart(patient_pcts, model_label=""):
    """Horizontal stacked bar per anonymised HHS showing Pos/Neu/Neg %."""
    cats   = ["Positive", "Neutral", "Negative"]
    colors = [_CAT_COLORS[c] for c in cats]
    suffix = f"  ({model_label})" if model_label else ""
    letters = (list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                + [f"A{c}" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"])
    hhs_labels = [f"HHS {letters[i]}" for i in range(len(patient_pcts))]

    fig = go.Figure()
    for cat, col in zip(cats, colors):
        x_vals = [pp.get(cat, 0) for pp in patient_pcts]
        fig.add_trace(go.Bar(
            name=cat + suffix,
            y=hhs_labels,
            x=x_vals,
            orientation="h",
            marker_color=col,
            text=[f"{v}%" if v >= 8 else "" for v in x_vals],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="white", size=10),
            hovertemplate="<b>%{y}</b><br>" + cat + ": %{x}%<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack",
        title=dict(text=f"Sentiment Profile by HHS (Anonymised)  ·  {model_label}", x=0.5, font=dict(size=14)),
        xaxis=dict(title="% of model×month classifications", range=[0, 100]),
        yaxis=dict(autorange="reversed"),
        showlegend=False,
        height=max(500, len(patient_pcts) * 26 + 140),
        margin=dict(l=20, r=20, t=80, b=40),
        paper_bgcolor="#f8f9fa",
        plot_bgcolor="#f8f9fa",
    )
    return fig


def _build_ward_table_html(ward_data):
    """HTML table: Ward | Comments | Positive% | Negative% | Mixed% | Neutral% | Red Flags."""
    th_style = ("padding:10px 14px;text-align:left;font-size:0.78rem;font-weight:700;"
                "letter-spacing:0.06em;color:#1a3a5c;background:#eaf1fb;border-bottom:2px solid #c3d4e8;")
    # Sort by Red Flags descending
    rows_data = sorted(ward_data.items(), key=lambda x: x[1]["red_flags"], reverse=True)
    rows = ""
    for i, (ward, d) in enumerate(rows_data):
        bg = "#f8fbff" if i % 2 == 0 else "#ffffff"
        rf_color = "#c0392b" if d["red_flags"] > 0 else "#27ae60"
        rows += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:9px 14px;color:#1a3a5c;font-weight:500;">{ward}</td>'
            f'<td style="padding:9px 14px;text-align:right;color:#333;">{d["total"]:,}</td>'
            f'<td style="padding:9px 14px;text-align:right;color:#27ae60;font-weight:600;">{d["pos_pct"]}</td>'
            f'<td style="padding:9px 14px;text-align:right;color:#c0392b;font-weight:600;">{d["neg_pct"]}</td>'
            f'<td style="padding:9px 14px;text-align:right;color:#2980b9;font-weight:600;">{d["mix_pct"]}</td>'
            f'<td style="padding:9px 14px;text-align:right;color:#7f8c8d;font-weight:600;">{d["neu_pct"]}</td>'
            f'<td style="padding:9px 14px;text-align:right;color:{rf_color};font-weight:700;">{d["red_flags"]}</td>'
            f'</tr>'
        )
    return (
        '<div style="overflow-x:auto;margin-top:16px;">'
        '<h3 style="font-size:1rem;font-weight:700;color:#ffffff;margin-bottom:8px;">'
        'Ward-level sentiment profile (statewide)</h3>'
        '<table style="width:100%;border-collapse:collapse;font-size:0.88rem;">'
        '<thead><tr>'
        f'<th style="{th_style}">WARD</th>'
        f'<th style="{th_style}text-align:right;">COMMENTS</th>'
        f'<th style="{th_style}text-align:right;">POSITIVE %</th>'
        f'<th style="{th_style}text-align:right;">NEGATIVE %</th>'
        f'<th style="{th_style}text-align:right;">MIXED %</th>'
        f'<th style="{th_style}text-align:right;">NEUTRAL %</th>'
        f'<th style="{th_style}text-align:right;">RED FLAGS</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
    )


def _build_peer_group_table_html(pg_data):
    """HTML table: Peer Group | Patients | Positive% | Negative% | Mixed% | Neutral% | Red Flags."""
    th_style = ("padding:10px 14px;text-align:left;font-size:0.78rem;font-weight:700;"
                "letter-spacing:0.06em;color:#1a3a5c;background:#eaf1fb;border-bottom:2px solid #c3d4e8;")
    # Fixed display order matching peer-group hierarchy
    order = _PG_LABELS
    rows = ""
    for i, pg in enumerate(order):
        if pg not in pg_data:
            continue
        d   = pg_data[pg]
        bg  = "#f8fbff" if i % 2 == 0 else "#ffffff"
        rf_color = "#c0392b" if d["red_flags"] > 0 else "#27ae60"
        rows += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:9px 14px;color:#1a3a5c;font-weight:500;">{pg}</td>'
            f'<td style="padding:9px 14px;text-align:right;color:#333;">{d["n_patients"]}</td>'
            f'<td style="padding:9px 14px;text-align:right;color:#333;">{d["total"]:,}</td>'
            f'<td style="padding:9px 14px;text-align:right;color:#27ae60;font-weight:600;">{d["pos_pct"]}</td>'
            f'<td style="padding:9px 14px;text-align:right;color:#c0392b;font-weight:600;">{d["neg_pct"]}</td>'
            f'<td style="padding:9px 14px;text-align:right;color:#2980b9;font-weight:600;">{d["mix_pct"]}</td>'
            f'<td style="padding:9px 14px;text-align:right;color:#7f8c8d;font-weight:600;">{d["neu_pct"]}</td>'
            f'<td style="padding:9px 14px;text-align:right;color:{rf_color};font-weight:700;">{d["red_flags"]}</td>'
            f'</tr>'
        )
    return (
        '<div style="overflow-x:auto;margin-top:24px;">'
        '<h3 style="font-size:1rem;font-weight:700;color:#ffffff;margin-bottom:8px;">'
        'Peer-group sentiment profile (statewide)</h3>'
        '<table style="width:100%;border-collapse:collapse;font-size:0.88rem;">'
        '<thead><tr>'
        f'<th style="{th_style}">PEER GROUP</th>'
        f'<th style="{th_style}text-align:right;">PATIENTS</th>'
        f'<th style="{th_style}text-align:right;">COMMENTS</th>'
        f'<th style="{th_style}text-align:right;">POSITIVE %</th>'
        f'<th style="{th_style}text-align:right;">NEGATIVE %</th>'
        f'<th style="{th_style}text-align:right;">MIXED %</th>'
        f'<th style="{th_style}text-align:right;">NEUTRAL %</th>'
        f'<th style="{th_style}text-align:right;">RED FLAGS</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
    )


def _build_hhs_rollup_table_html(rows_data, sw_neg_pct, sw_q4_neg_pct, sw_red_flags, sw_total):
    """HHS rollup with peer-group benchmark table (matches screenshot layout)."""
    th = ("padding:10px 14px;font-size:0.78rem;font-weight:700;letter-spacing:0.06em;"
          "color:#1a3a5c;background:#eaf1fb;border-bottom:2px solid #c3d4e8;")
    th_r = th + "text-align:right;"

    def _delta_cell(val, favorable_direction="down"):
        """Render a Δ cell: green if movement is in the favorable direction, red otherwise."""
        if val is None:
            return '<td style="padding:9px 14px;text-align:right;color:#888;">—</td>'
        sign   = "+" if val > 0 else ""
        color  = ("#27ae60" if (favorable_direction == "down" and val < 0)
                             or (favorable_direction == "up"   and val > 0)
                  else "#c0392b" if val != 0 else "#888")
        return (f'<td style="padding:9px 14px;text-align:right;'
                f'font-weight:600;color:{color};">{sign}{val:.1f}</td>')

    # Identify outliers: |Δ vs peer| > 3.5 pp
    outliers_above = [r["hhs"] for r in rows_data if r["delta_peer"] is not None and r["delta_peer"] >  3.5]
    outliers_below = [r["hhs"] for r in rows_data if r["delta_peer"] is not None and r["delta_peer"] < -3.5]

    html_rows = ""
    for i, r in enumerate(rows_data):
        bg = "#f8fbff" if i % 2 == 0 else "#ffffff"
        rf_color = "#c0392b" if r["red_flags"] > 0 else "#27ae60"
        peer_med_cell = (f'<td style="padding:9px 14px;text-align:right;color:#555;">'
                         f'{r["peer_median"]:.1f}</td>'
                         if r["peer_median"] is not None
                         else '<td style="padding:9px 14px;text-align:right;color:#888;">—</td>')
        html_rows += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:9px 14px;color:#1a3a5c;font-weight:600;">{r["hhs"]}</td>'
            f'<td style="padding:9px 14px;color:#555;">{r["peer_group"]}</td>'
            f'<td style="padding:9px 14px;text-align:right;color:#333;">{r["total"]:,}</td>'
            f'<td style="padding:9px 14px;text-align:right;color:#c0392b;font-weight:600;">{r["neg_pct"]:.0f}</td>'
            + peer_med_cell
            + _delta_cell(r["delta_peer"], "down")
            + _delta_cell(r["delta_q4"],   "down")
            + f'<td style="padding:9px 14px;text-align:right;color:{rf_color};font-weight:700;">{r["red_flags"]}</td>'
            f'</tr>'
        )

    # Statewide summary row
    sw_q4_delta = round(sw_neg_pct - sw_q4_neg_pct, 1) if sw_q4_neg_pct is not None else None
    html_rows += (
        '<tr style="background:#1a3a5c;font-weight:700;">'
        '<td style="padding:10px 14px;color:#fff;">Statewide</td>'
        '<td style="padding:10px 14px;color:#aac;">—</td>'
        f'<td style="padding:10px 14px;text-align:right;color:#fff;">{sw_total:,}</td>'
        f'<td style="padding:10px 14px;text-align:right;color:#f8a;">{sw_neg_pct:.0f}</td>'
        '<td style="padding:10px 14px;text-align:right;color:#aac;">—</td>'
        '<td style="padding:10px 14px;text-align:right;color:#aac;">—</td>'
        + (f'<td style="padding:10px 14px;text-align:right;color:{"#6f6" if sw_q4_delta is not None and sw_q4_delta < 0 else "#f88"};">'
           f'{"+" if sw_q4_delta and sw_q4_delta > 0 else ""}{sw_q4_delta:.1f}</td>'
           if sw_q4_delta is not None else
           '<td style="padding:10px 14px;text-align:right;color:#aac;">—</td>')
        + f'<td style="padding:10px 14px;text-align:right;color:#f88;">{sw_red_flags}</td>'
        '</tr>'
    )

    # Footnote
    outlier_parts = []
    if outliers_above:
        outlier_parts.append(f"{', '.join(outliers_above)} above peer median")
    if outliers_below:
        outlier_parts.append(f"{', '.join(outliers_below)} below peer median")
    footnote_body = (
        f"HHSs more than ±3.5 pp from peer median are visual outliers this period"
        + (f" ({'; '.join(outlier_parts)})" if outlier_parts else "")
        + ". Below-median Negative % is the favourable direction. "
        "Outliers warrant local context before any inference."
    )

    return (
        '<div style="overflow-x:auto;margin-top:28px;">'
        '<h3 style="font-size:1rem;font-weight:700;color:#ffffff;margin-bottom:4px;">'
        'HHS rollup with peer-group benchmark</h3>'
        '<p style="font-size:0.76rem;color:#ccc;margin:0 0 10px;">'
        'HHSs are anonymised. Peer groups: Large metro (4), Outer metro (3), Regional (4), '
        'Outer regional / rural / remote (5). '
        'Negative % is the share of months classified as negative sentiment. '
        'Δ VS Q4 2025 uses the first half of each patient\'s journey as baseline.</p>'
        '<table style="width:100%;border-collapse:collapse;font-size:0.88rem;">'
        '<thead><tr>'
        f'<th style="{th}">HHS</th>'
        f'<th style="{th}">PEER GROUP</th>'
        f'<th style="{th_r}">COMMENTS</th>'
        f'<th style="{th_r}">NEGATIVE %</th>'
        f'<th style="{th_r}">PEER MEDIAN</th>'
        f'<th style="{th_r}">Δ VS PEER</th>'
        f'<th style="{th_r}">Δ VS Q4 2025</th>'
        f'<th style="{th_r}">RED FLAGS</th>'
        '</tr></thead>'
        f'<tbody>{html_rows}</tbody></table>'
        f'<p style="font-size:0.73rem;color:#aaa;margin-top:8px;font-style:italic;">{footnote_body}</p>'
        '</div>'
    )


def run_statewide_analysis(sentiment_model_label):
    """Run selected model across all months × all 36 patients and aggregate Pos/Neg/Neu."""
    from concurrent.futures import ThreadPoolExecutor
    from collections import Counter, defaultdict

    sentiment_type = MODEL_LABEL_TO_TYPE.get(sentiment_model_label, "bert_hc_v2")
    n_months = len(list(PATIENT_SAMPLES.values())[0])

    # Flatten: (patient_idx, month_idx, month_key, text)
    tasks = []
    for pidx, pname in enumerate(PATIENT_NAMES):
        month_items = list(PATIENT_SAMPLES.get(pname, {}).items())
        for m_idx, (month_key, text) in enumerate(month_items):
            tasks.append((pidx, m_idx, month_key, text[:400].strip()))

    def _infer(args):
        pidx, m_idx, month_key, text = args
        if not text:
            return pidx, m_idx, month_key, "Neutral"
        try:
            dominant, _ = analyze_sentiment(text, sentiment_type)
            cat = _SENTIMENT_CATEGORY.get(dominant.upper(), "Neutral")
            return pidx, m_idx, month_key, cat
        except Exception:
            return pidx, m_idx, month_key, "Neutral"

    with ThreadPoolExecutor(max_workers=12) as ex:
        results = list(ex.map(_infer, tasks))

    total = len(results)

    # Global aggregate
    global_counts = Counter(cat for _, _, _, cat in results)
    pcts = {k: round(global_counts.get(k, 0) / total * 100) for k in ["Positive", "Negative", "Neutral"]}

    # Per-patient percentages
    patient_counts = [Counter() for _ in PATIENT_NAMES]
    patient_totals = [0] * len(PATIENT_NAMES)
    for pidx, _, _, cat in results:
        patient_counts[pidx][cat] += 1
        patient_totals[pidx] += 1
    patient_pcts = [
        {k: round(patient_counts[i].get(k, 0) / max(patient_totals[i], 1) * 100)
         for k in ["Positive", "Negative", "Neutral"]}
        for i in range(len(PATIENT_NAMES))
    ]

    # Per-ward aggregation — months from a patient who showed BOTH Positive AND Negative
    # in the same ward are reclassified as "Mixed".
    ward_patient_months = defaultdict(lambda: defaultdict(list))
    for pidx, m_idx, month_key, cat in results:
        pname = PATIENT_NAMES[pidx]
        ward  = get_ward(pname, month_key)
        ward_patient_months[ward][pidx].append(cat)

    ward_data = {}
    for ward, patient_months in ward_patient_months.items():
        pos_c = neg_c = neu_c = mix_c = 0
        for _, cats in patient_months.items():
            cat_set = set(cats)
            if "Positive" in cat_set and "Negative" in cat_set:
                mix_c += len(cats)
            else:
                for cat in cats:
                    if cat == "Positive":
                        pos_c += 1
                    elif cat == "Negative":
                        neg_c += 1
                    else:
                        neu_c += 1
        wt = pos_c + neg_c + neu_c + mix_c
        ward_data[ward] = {
            "total":    wt,
            "pos_pct":  round(pos_c / wt * 100) if wt else 0,
            "neg_pct":  round(neg_c / wt * 100) if wt else 0,
            "mix_pct":  round(mix_c / wt * 100) if wt else 0,
            "neu_pct":  round(neu_c / wt * 100) if wt else 0,
            "red_flags": neg_c + mix_c,
        }

    # Per-peer-group aggregation — Mixed defined at patient level:
    # if a patient has BOTH Positive AND Negative across ALL their months, all
    # their months count as Mixed for the peer group breakdown.
    pg_patient_months = defaultdict(lambda: defaultdict(list))
    for pidx, _, _, cat in results:
        pname = PATIENT_NAMES[pidx]
        pg    = PATIENT_PEER_GROUP.get(pname, "Unknown")
        pg_patient_months[pg][pidx].append(cat)

    pg_data = {}
    for pg, patient_months in pg_patient_months.items():
        pos_c = neg_c = neu_c = mix_c = 0
        for pidx, cats in patient_months.items():
            cat_set = set(cats)
            if "Positive" in cat_set and "Negative" in cat_set:
                mix_c += len(cats)
            else:
                for cat in cats:
                    if cat == "Positive":
                        pos_c += 1
                    elif cat == "Negative":
                        neg_c += 1
                    else:
                        neu_c += 1
        wt = pos_c + neg_c + neu_c + mix_c
        n_pat = sum(1 for p in PATIENT_NAMES if PATIENT_PEER_GROUP.get(p) == pg)
        pg_data[pg] = {
            "n_patients": n_pat,
            "total":      wt,
            "pos_pct":    round(pos_c / wt * 100) if wt else 0,
            "neg_pct":    round(neg_c / wt * 100) if wt else 0,
            "mix_pct":    round(mix_c / wt * 100) if wt else 0,
            "neu_pct":    round(neu_c / wt * 100) if wt else 0,
            "red_flags":  neg_c + mix_c,
        }

    # ── HHS rollup with peer-group benchmark ─────────────────────────────────
    # Per-patient: collect (m_idx, cat) to compute overall and Q4-baseline neg%.
    patient_month_results = defaultdict(list)   # pidx → [(m_idx, cat), ...]
    for pidx, m_idx, _, cat in results:
        patient_month_results[pidx].append((m_idx, cat))

    letters = (list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
               + [f"A{c}" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"])

    hhs_rows = []
    for pidx, pname in enumerate(PATIENT_NAMES):
        month_cats = sorted(patient_month_results[pidx], key=lambda x: x[0])
        n_m = len(month_cats)
        if n_m == 0:
            continue
        all_neg  = sum(1 for _, c in month_cats if c == "Negative")
        neg_pct  = all_neg / n_m * 100
        red_flags = all_neg

        # Q4 2025 baseline = first half of the journey
        half     = max(1, n_m // 2)
        q4_cats  = month_cats[:half]
        cur_cats = month_cats[half:]
        q4_neg_pct  = sum(1 for _, c in q4_cats  if c == "Negative") / len(q4_cats)  * 100
        cur_neg_pct = sum(1 for _, c in cur_cats if c == "Negative") / len(cur_cats) * 100 if cur_cats else None
        delta_q4 = round(cur_neg_pct - q4_neg_pct, 1) if cur_neg_pct is not None else None

        hhs_rows.append({
            "hhs":        f"HHS {letters[pidx]}",
            "peer_group": PATIENT_PEER_GROUP.get(pname, "Unknown"),
            "total":      n_m,
            "neg_pct":    neg_pct,
            "q4_neg_pct": q4_neg_pct,
            "delta_q4":   delta_q4,
            "red_flags":  red_flags,
            "peer_median": None,   # filled in below
            "delta_peer":  None,
        })

    # Compute peer-group medians and per-HHS Δ vs peer
    import statistics
    for pg_label in _PG_LABELS:
        pg_negs = [r["neg_pct"] for r in hhs_rows if r["peer_group"] == pg_label]
        if not pg_negs:
            continue
        median_neg = statistics.median(pg_negs)
        for r in hhs_rows:
            if r["peer_group"] == pg_label:
                r["peer_median"] = round(median_neg, 1)
                r["delta_peer"]  = round(r["neg_pct"] - median_neg, 1)

    # Sort by peer group order, then by neg_pct descending within group
    pg_order = {pg: i for i, pg in enumerate(_PG_LABELS)}
    hhs_rows.sort(key=lambda r: (pg_order.get(r["peer_group"], 99), -r["neg_pct"]))

    # Statewide aggregates for summary row
    sw_total_comments = sum(r["total"]    for r in hhs_rows)
    sw_neg_pct_all    = sum(r["neg_pct"] * r["total"] for r in hhs_rows) / sw_total_comments if sw_total_comments else 0
    sw_q4_neg_pct_all = sum(r["q4_neg_pct"] * r["total"] for r in hhs_rows) / sw_total_comments if sw_total_comments else None
    sw_red_flags_all  = sum(r["red_flags"] for r in hhs_rows)

    done_status = (
        f'<span style="background:#27ae60;color:#fff;border-radius:20px;'
        f'padding:4px 14px;font-size:0.85rem;font-weight:600;">'
        f'✓ {total:,} classifications — {len(PATIENT_NAMES)} patients × {n_months} months'
        f'  ·  {sentiment_model_label}</span>'
    )
    kpi_html           = _build_statewide_kpi_html(pcts, total)
    statewide_fig      = _build_statewide_bar_chart(pcts, sentiment_model_label)
    per_patient_fig    = _build_per_patient_chart(patient_pcts, sentiment_model_label)
    ward_table_html    = _build_ward_table_html(ward_data)
    pg_table_html      = _build_peer_group_table_html(pg_data)
    hhs_rollup_html    = _build_hhs_rollup_table_html(
                             hhs_rows, sw_neg_pct_all, sw_q4_neg_pct_all,
                             sw_red_flags_all, sw_total_comments)

    report_path = _write_statewide_report(
        model_label      = sentiment_model_label,
        total            = total,
        statewide_fig    = statewide_fig,
        per_patient_fig  = per_patient_fig,
        kpi_html         = kpi_html,
        ward_table_html  = ward_table_html,
        pg_table_html    = pg_table_html,
        hhs_rollup_html  = hhs_rollup_html,
    )

    return done_status, kpi_html, statewide_fig, per_patient_fig, ward_table_html, pg_table_html, hhs_rollup_html, report_path


def _write_statewide_report(model_label, total,
                             statewide_fig, per_patient_fig,
                             kpi_html, ward_table_html, pg_table_html, hhs_rollup_html):
    """Build a self-contained HTML report and write it to a temp file; return the path."""
    import re, tempfile
    import plotly.io as pio
    from datetime import date as _date

    today = _date.today().strftime("%d %B %Y")

    chart1 = pio.to_html(statewide_fig,   full_html=False, include_plotlyjs="cdn",
                          config={"displayModeBar": False})
    chart2 = pio.to_html(per_patient_fig, full_html=False, include_plotlyjs=False,
                          config={"displayModeBar": False})

    def _patch(html):
        """Recolour dark-UI elements so they read on a white background."""
        html = re.sub(r'(<h3\b[^>]*style="[^"]*?)color:#ffffff', r'\1color:#1a3a5c', html)
        html = re.sub(r'(<p\b[^>]*style="[^"]*?)color:#ccc\b',   r'\1color:#555',   html)
        html = re.sub(r'(<p\b[^>]*style="[^"]*?)color:#aaa\b',   r'\1color:#666',   html)
        html = html.replace('font-size:0.78rem;color:#fff;margin-top:4px;',
                            'font-size:0.78rem;color:#555;margin-top:4px;')
        return html

    report = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Statewide Sentiment Report — Q1 2026</title>
  <style>
    *,*::before,*::after{{box-sizing:border-box}}
    body{{font-family:Arial,Helvetica,sans-serif;background:#f0f4f8;margin:0;padding:32px 16px;color:#222}}
    .rpt{{max-width:1120px;margin:0 auto;background:#fff;border-radius:14px;
          padding:36px 40px;box-shadow:0 4px 24px rgba(0,0,0,.10)}}
    .rpt-header{{border-bottom:2px solid #c3d4e8;padding-bottom:16px;margin-bottom:28px}}
    .rpt-header h1{{color:#1a3a5c;font-size:1.55rem;margin:0 0 4px}}
    .rpt-header p{{color:#666;font-size:0.84rem;margin:0}}
    section{{margin-bottom:36px}}
    h3{{color:#1a3a5c !important}}
  </style>
</head>
<body>
<div class="rpt">
  <div class="rpt-header">
    <h1>Statewide Sentiment &amp; HHS Profile</h1>
    <p>Generated: {today} &nbsp;·&nbsp; Model: {model_label} &nbsp;·&nbsp;
       {total:,} classifications across {len(PATIENT_NAMES)} patients</p>
  </div>
  <section>{_patch(kpi_html)}</section>
  <section>{chart1}</section>
  <section>{chart2}</section>
  <section>{_patch(ward_table_html)}</section>
  <section>{_patch(pg_table_html)}</section>
  <section>{_patch(hhs_rollup_html)}</section>
</div>
</body>
</html>"""

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html",
                                      prefix="statewide_report_")
    tmp.write(report.encode("utf-8"))
    tmp.close()
    return tmp.name


def update_months(patient):
    months = get_month_names(patient)
    return gr.CheckboxGroup(choices=months, value=months[:1])


def load_sample(patient, names):
    if not patient or not names:
        return "", (
            '<span style="background:#e67e22;color:#fff;border-radius:20px;'
            'padding:4px 14px;font-size:0.85rem;font-weight:600;">'
            '⚠ No months selected</span>'
        )
    if isinstance(names, str):
        names = [names]
    samples = PATIENT_SAMPLES.get(patient, {})
    parts = [f"[{n}]\n{samples[n]}" for n in names if n in samples]
    text = "\n\n".join(parts)
    n = len(parts)
    status = (
        f'<span style="background:#27ae60;color:#fff;border-radius:20px;'
        f'padding:4px 14px;font-size:0.85rem;font-weight:600;">'
        f'✓ {n} month{"s" if n != 1 else ""} loaded for {patient}</span>'
    )
    return text, status


# ── Recurring Semantic Themes ─────────────────────────────────────────────────

_SEMANTIC_THEMES = {
    "ED waiting and updates": [
        "wait", "waiting", "emergency department", " ed ", "triage",
        "hours", "delay", "queue", "update", "informed us", "told us",
    ],
    "Discharge and post-discharge care": [
        "discharg", "discharge", "sent home", "follow-up", "follow up",
        "aftercare", "after care", "post-discharge", "leaving hospital",
        "community care", "transition", "handover",
    ],
    "Night-time noise and sleep": [
        "noise", "noisy", "sleep", "night-time", "night time", " night ",
        "loud", "disturb", "rest", "awake", "woken", "beeping", "alarm",
    ],
    "Medication information": [
        "medication", "medicine", "drug", "prescription", "dosage",
        "side effect", "pharmacy", "pharmacist", "tablet", "dose",
        "medication error", "reconciliation",
    ],
    "Cleanliness and infection prevention": [
        "clean", "cleanliness", "hygiene", "infection", "sterile",
        "dirty", "hand washing", "hand wash", "sanitise", "sanitize",
        "tidy", "germ", "bacteria",
    ],
    "Communication and explanations": [
        "explain", "explanation", "communicated", "communication",
        "told me", "informed", "understand", "understanding",
        "information", "clarity", "question", "listen", "discuss",
    ],
    "Cultural safety, accessibility and language": [
        "interpreter", "interpretation", "cultural", "culture",
        "language", "accessibility", "ndis", "disability",
        "translation", "indigenous", "religious", "diverse",
    ],
    "Food and hydration": [
        "food", "meal", "water", "hydration", "nutrition", "diet",
        "hungry", "thirst", "eat ", "drink", "breakfast", "lunch",
        "dinner", "snack",
    ],
    "Administration and appointments": [
        "appointment", "admin", "schedule", "scheduling", "booking",
        "referral", "paperwork", "form", "waiting list", "waitlist",
        "outpatient", "reception", "registration", "billing",
    ],
    "Family and carer involvement": [
        "family", "carer", "partner", "spouse", "relative", "visitor",
        "support person", "husband", "wife", " parent", "child",
        "involve", "inclusion",
    ],
}

_THEME_AHPEQS_ANCHOR = {
    "ED waiting and updates":                     "AHPEQS Q4, Q8 · NSQHS 6",
    "Discharge and post-discharge care":           "AHPEQS Q4, Q5 · NSQHS 6",
    "Night-time noise and sleep":                 "AHPEQS Q2 · NSQHS 5",
    "Medication information":                      "AHPEQS Q4, Q9 · NSQHS 4",
    "Cleanliness and infection prevention":        "NSQHS 3",
    "Communication and explanations":              "AHPEQS Q1, Q4, Q5 · NSQHS 6",
    "Cultural safety, accessibility and language": "AHPEQS Q1 · NSQHS 1, 2",
    "Food and hydration":                          "NSQHS 5",
    "Administration and appointments":             "—",
    "Family and carer involvement":                "AHPEQS Q5 · NSQHS 2",
}

_THEME_CLINICAL_SEVERITY = {
    "ED waiting and updates":                     "Medium",
    "Discharge and post-discharge care":           "Medium",
    "Night-time noise and sleep":                 "Medium",
    "Medication information":                      "High",
    "Cleanliness and infection prevention":        "High",
    "Communication and explanations":              "Medium",
    "Cultural safety, accessibility and language": "Medium",
    "Food and hydration":                          "Low",
    "Administration and appointments":             "Low",
    "Family and carer involvement":                "Low",
}

_THEME_CLINICAL_RELEVANCE = {
    "ED waiting and updates": (
        "The strongest opportunity is to reduce information asymmetry during escalated waits "
        "rather than focusing solely on reducing wait times."
    ),
    "Discharge and post-discharge care": (
        "A structured discharge checklist and a direct clinical-pharmacist handover can address "
        "the gap between care provided and care understood."
    ),
    "Night-time noise and sleep": (
        "A ward-level improvement opportunity: targeted quiet-hours protocols have delivered "
        "measurable reductions in negative sleep-related comments in comparable facilities."
    ),
    "Medication information": (
        "Requires a safety-sensitive workflow. Medication comments should be triaged to pharmacy "
        "or a clinical pharmacist before being reviewed by the treating physician."
    ),
    "Cleanliness and infection prevention": (
        "Infection-prevention perceptions directly affect patient trust. Visible hand-hygiene "
        "compliance and proactive ward-cleanliness communication are highest-yield interventions."
    ),
    "Communication and explanations": (
        "Communication is a cross-cutting strategic priority. The report surfaces patient-perceived "
        "gaps in information-sharing that highlight opportunities for structured bedside rounding."
    ),
    "Cultural safety, accessibility and language": (
        "A concern regardless of volume. The report surfaces disparities for patients from "
        "culturally and linguistically diverse backgrounds requiring targeted interpreter access."
    ),
    "Food and hydration": (
        "Nutrition and hydration directly affect recovery outcomes. Proactive meal-round "
        "checks and patient-preference documentation are low-cost, high-impact interventions."
    ),
    "Administration and appointments": (
        "Administrative friction erodes patient trust before clinical contact begins. "
        "Streamlined booking and clear referral pathways are the highest-yield system improvements."
    ),
    "Family and carer involvement": (
        "Carer exclusion compounds patient anxiety. Structured visiting policies and "
        "carer-inclusive communication protocols are recommended under NSQHS Standard 2."
    ),
}

_THEME_NEG_WORDS = {
    "pain", "concern", "problem", "issue", "worse", "bad", "poor",
    "difficult", "frustrat", "angry", "disappoint", "fail", "lack",
    "neglect", "error", "mistake", "confusion", "unclear", "delay",
    "long wait", "inadequate", "insufficient", "missing", "ignored",
    "dismissed", "rude", "unhelpful", "overcrowded", "under-staffed",
}
_THEME_POS_WORDS = {
    "good", "excellent", "great", "wonderful", "helpful", "kind",
    "professional", "thorough", "responsive", "fantastic",
    "appreciate", "thank", "satisfied", "happy", "impressed",
    "supportive", "caring", "attentive", "prompt",
}


def _compute_theme_impact():
    """Score each AHPEQS-aligned theme by volume × severity × trend, normalised to 0–100."""
    # Flatten all patient-months with positional index (used for trend split)
    all_months = []
    for pname, months in PATIENT_SAMPLES.items():
        month_items = list(months.items())
        n = len(month_items)
        for m_idx, (_, text) in enumerate(month_items):
            all_months.append({"m_idx": m_idx, "n": n, "text": text.lower()})
    total = len(all_months)
    if total == 0:
        return {}

    results = {}
    for theme, keywords in _SEMANTIC_THEMES.items():
        # Volume: months that mention at least one keyword
        mentions = [m for m in all_months if any(kw in m["text"] for kw in keywords)]
        volume   = len(mentions) / total * 100

        # Severity: ratio of negative-word hits to total sentiment-word hits
        neg_hits = sum(sum(1 for w in _THEME_NEG_WORDS if w in m["text"]) for m in mentions)
        pos_hits = sum(sum(1 for w in _THEME_POS_WORDS if w in m["text"]) for m in mentions)
        severity = neg_hits / max(neg_hits + pos_hits, 1)   # 0 = all positive, 1 = all negative

        # Trend: is this theme mentioned MORE in the second half of journeys?
        early  = [m for m in mentions if m["m_idx"] <  m["n"] // 2]
        recent = [m for m in mentions if m["m_idx"] >= m["n"] // 2]
        denom  = max(total / 2, 1)
        trend  = (len(recent) - len(early)) / denom   # positive = growing concern
        trend_factor = 1.0 + 0.25 * max(trend, 0)

        raw = volume * (0.4 + 0.6 * severity) * trend_factor
        results[theme] = {"raw": raw, "volume": volume, "severity": severity, "trend": trend}

    # Normalise so the highest score = 100
    max_raw = max(s["raw"] for s in results.values()) or 1
    for theme in results:
        results[theme]["impact"] = round(results[theme]["raw"] / max_raw * 100)

    return results


def _build_theme_impact_chart(theme_scores, topic_model_label=""):
    """Horizontal bar chart matching the screenshot style."""
    sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1]["impact"], reverse=True)
    labels  = [t for t, _ in sorted_themes]
    scores  = [s["impact"] for _, s in sorted_themes]

    def _color(score):
        if score >= 75: return "#8B1A1A"   # dark red
        if score >= 65: return "#B5651D"   # dark orange-brown
        return "#1a3a5c"                    # dark blue

    colors = [_color(s) for s in scores]

    fig = go.Figure(go.Bar(
        x=scores, y=labels, orientation="h",
        marker_color=colors,
        text=[str(s) for s in scores],
        textposition="outside",
        textfont=dict(size=12, color="#222"),
        hovertemplate="<b>%{y}</b><br>Impact score: %{x}<extra></extra>",
        cliponaxis=False,
    ))
    fig.update_layout(
        title=dict(
            text=("Impact score by semantic theme — statewide, Q1 2026"
                  + (f"  ·  {topic_model_label}" if topic_model_label else "")),
            x=0.5, font=dict(size=14, family="Arial"),
        ),
        xaxis=dict(
            range=[0, 115],
            title="Impact score = f(volume × severity × trend)",
            showgrid=True, gridcolor="#e0e0e0",
            zeroline=False,
        ),
        yaxis=dict(autorange="reversed"),
        height=500,
        margin=dict(l=320, r=80, t=60, b=70),
        paper_bgcolor="#f8f9fa",
        plot_bgcolor="#ffffff",
        showlegend=False,
    )
    return fig


def _build_theme_breakdown_table_html(theme_scores):
    """HTML table: THEME | VOLUME % | SEVERITY | TREND FACTOR | NORM. IMPACT SCORE."""
    th = ("padding:10px 14px;font-size:0.78rem;font-weight:700;letter-spacing:0.06em;"
          "color:#1a3a5c;background:#eaf1fb;border-bottom:2px solid #c3d4e8;")
    th_r = th + "text-align:right;"

    sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1]["impact"], reverse=True)

    def _impact_badge(score):
        if score >= 75:
            color = "#8B1A1A"
        elif score >= 65:
            color = "#B5651D"
        else:
            color = "#1a3a5c"
        return (f'<span style="background:{color};color:#fff;border-radius:4px;'
                f'padding:2px 10px;font-weight:700;">{score}</span>')

    def _bar_mini(pct, color):
        """Inline mini progress bar for Volume %."""
        return (f'<div style="display:flex;align-items:center;gap:6px;">'
                f'<div style="width:80px;background:#e8edf3;border-radius:3px;height:8px;">'
                f'<div style="width:{min(pct,100):.0f}%;background:{color};height:8px;border-radius:3px;"></div>'
                f'</div>'
                f'<span style="font-size:0.82rem;color:#333;">{pct:.1f}%</span>'
                f'</div>')

    def _severity_bar(sev):
        """Inline severity bar: 0=green → 1=red."""
        pct = sev * 100
        color = ("#c0392b" if sev >= 0.6 else "#e67e22" if sev >= 0.4 else "#27ae60")
        return (f'<div style="display:flex;align-items:center;gap:6px;">'
                f'<div style="width:80px;background:#e8edf3;border-radius:3px;height:8px;">'
                f'<div style="width:{pct:.0f}%;background:{color};height:8px;border-radius:3px;"></div>'
                f'</div>'
                f'<span style="font-size:0.82rem;color:#333;">{sev:.2f}</span>'
                f'</div>')

    def _trend_cell(trend, tf):
        arrow = "▲" if trend > 0.01 else ("▼" if trend < -0.01 else "→")
        t_color = "#c0392b" if trend > 0.01 else ("#27ae60" if trend < -0.01 else "#888")
        return (f'<span style="color:{t_color};font-weight:600;">{arrow}</span>'
                f'&nbsp;<span style="color:#333;font-size:0.82rem;">{tf:.3f}</span>')

    rows = ""
    for i, (theme, s) in enumerate(sorted_themes):
        bg = "#f8fbff" if i % 2 == 0 else "#ffffff"
        vol_color = ("#8B1A1A" if s["impact"] >= 75 else
                     "#B5651D" if s["impact"] >= 65 else "#1a3a5c")
        tf = 1.0 + 0.25 * max(s["trend"], 0)
        rows += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:9px 14px;color:#1a3a5c;font-weight:500;">{theme}</td>'
            f'<td style="padding:9px 14px;">{_bar_mini(s["volume"], vol_color)}</td>'
            f'<td style="padding:9px 14px;">{_severity_bar(s["severity"])}</td>'
            f'<td style="padding:9px 14px;">{_trend_cell(s["trend"], tf)}</td>'
            f'<td style="padding:9px 14px;text-align:center;">{_impact_badge(s["impact"])}</td>'
            f'</tr>'
        )

    footnote = (
        "<b>Volume %</b>: share of all patient-months containing at least one theme keyword. "
        "<b>Severity</b>: negative-word hits ÷ (negative + positive word hits) in theme-matching texts "
        "(0&nbsp;=&nbsp;all positive, 1&nbsp;=&nbsp;all negative). "
        "<b>Trend factor</b>: 1&nbsp;+&nbsp;0.25&nbsp;×&nbsp;max(trend,&nbsp;0) where trend compares "
        "second-half vs first-half journey mention rates "
        "(▲&nbsp;growing concern adds penalty, ▼&nbsp;declining gets no bonus). "
        "<b>Norm. Impact</b>: raw&nbsp;=&nbsp;volume&nbsp;×&nbsp;(0.4&nbsp;+&nbsp;0.6&nbsp;×&nbsp;severity)&nbsp;"
        "×&nbsp;trend_factor, then rescaled so the top theme&nbsp;=&nbsp;100."
    )

    return (
        '<div style="overflow-x:auto;margin-top:24px;">'
        '<h3 style="font-size:1rem;font-weight:700;color:#ffffff;margin-bottom:4px;">'
        'Theme impact — component breakdown</h3>'
        '<p style="font-size:0.76rem;color:#ccc;margin:0 0 10px;">'
        'Sorted by normalised impact score (descending). '
        'Bars scale to the maximum observed value within each column.</p>'
        '<table style="width:100%;border-collapse:collapse;font-size:0.88rem;">'
        '<thead><tr>'
        f'<th style="{th}">THEME</th>'
        f'<th style="{th}">VOLUME %</th>'
        f'<th style="{th}">SEVERITY</th>'
        f'<th style="{th}">TREND FACTOR</th>'
        f'<th style="{th_r}">NORM. IMPACT SCORE</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        f'<p style="font-size:0.73rem;color:#aaa;margin-top:10px;">{footnote}</p>'
        '</div>'
    )


def _build_theme_prevalence_table_html(theme_scores):
    """HTML table matching the 'Theme prevalence and characteristics' screenshot."""
    all_months = []
    for months in PATIENT_SAMPLES.values():
        for text in months.values():
            all_months.append(text.lower())
    total = max(len(all_months), 1)

    stats = {}
    for theme, keywords in _SEMANTIC_THEMES.items():
        mentions = [t for t in all_months if any(kw in t for kw in keywords)]
        n = len(mentions)
        neg_ratios, mixed_count = [], 0
        for text in mentions:
            neg = sum(1 for w in _THEME_NEG_WORDS if w in text)
            pos = sum(1 for w in _THEME_POS_WORDS if w in text)
            if neg + pos > 0:
                neg_ratios.append(neg / (neg + pos))
            if neg > 0 and pos > 0:
                mixed_count += 1
        stats[theme] = {
            "n":        n,
            "neg_pct":  round(sum(neg_ratios) / max(len(neg_ratios), 1) * 100),
            "mixed_pct": round(mixed_count / max(n, 1) * 100),
        }

    sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1]["impact"], reverse=True)

    def _severity_badge(label):
        color = {"High": "#c0392b", "Medium": "#e67e22", "Low": "#27ae60"}.get(label, "#888")
        return (f'<span style="background:{color};color:#fff;border-radius:12px;'
                f'padding:3px 13px;font-size:0.78rem;font-weight:600;">{label}</span>')

    def _delta_cell(trend):
        pp = round(trend * 100)
        if pp > 0:
            return f'<span style="color:#27ae60;font-weight:600;">+{pp}</span>'
        if pp < 0:
            return f'<span style="color:#c0392b;font-weight:600;">{pp}</span>'
        return '<span style="color:#888;">0</span>'

    th   = ("padding:10px 14px;font-size:0.78rem;font-weight:700;letter-spacing:0.06em;"
            "color:#1a3a5c;background:#eaf1fb;border-bottom:2px solid #c3d4e8;white-space:nowrap;")
    th_r = th + "text-align:right;"
    th_c = th + "text-align:center;"

    rows = ""
    for i, (theme, s) in enumerate(sorted_themes):
        bg  = "#f8fbff" if i % 2 == 0 else "#ffffff"
        st  = stats.get(theme, {})
        rows += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:9px 14px;color:#1a3a5c;font-weight:500;">{theme}</td>'
            f'<td style="padding:9px 14px;text-align:right;color:#000;">{st.get("n", 0):,}</td>'
            f'<td style="padding:9px 14px;text-align:right;color:#000;">{s["volume"]:.0f}%</td>'
            f'<td style="padding:9px 14px;text-align:right;color:#000;">{st.get("neg_pct", 0)}</td>'
            f'<td style="padding:9px 14px;text-align:right;color:#000;">{st.get("mixed_pct", 0)}</td>'
            f'<td style="padding:9px 14px;text-align:center;">'
            f'{_severity_badge(_THEME_CLINICAL_SEVERITY.get(theme, "Medium"))}</td>'
            f'<td style="padding:9px 14px;text-align:center;">{_delta_cell(s["trend"])}</td>'
            f'<td style="padding:9px 14px;color:#555;font-size:0.82rem;">'
            f'{_THEME_AHPEQS_ANCHOR.get(theme, "—")}</td>'
            f'</tr>'
        )

    footnote = (
        "Themes are non-exclusive; the % of comments column does not sum to 100%. "
        "Impact score is computed from volume × severity × directional trend and is reported in Section 4 above."
    )

    return (
        '<div style="overflow-x:auto;margin-top:28px;">'
        '<h3 style="font-size:1.05rem;font-weight:700;color:#ffffff;margin-bottom:6px;">'
        'Theme prevalence and characteristics</h3>'
        '<table style="width:100%;border-collapse:collapse;font-size:0.88rem;">'
        '<thead><tr>'
        f'<th style="{th}">THEME</th>'
        f'<th style="{th_r}">COMMENTS</th>'
        f'<th style="{th_r}">% OF COMMENTS</th>'
        f'<th style="{th_r}">NEGATIVE %</th>'
        f'<th style="{th_r}">MIXED %</th>'
        f'<th style="{th_c}">SEVERITY</th>'
        f'<th style="{th_c}">Δ VS Q4 (PP)</th>'
        f'<th style="{th}">AHPEQS / NSQHS ANCHOR</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        f'<p style="font-size:0.73rem;color:#aaa;margin-top:10px;">{footnote}</p>'
        '</div>'
    )


def _build_top6_impact_cards_html(theme_scores):
    """3×2 grid of detail cards for the top-6 impact-score themes."""
    import re as _re
    import html as _html_mod

    sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1]["impact"], reverse=True)
    top6 = sorted_themes[:6]

    def _extract_quote(keywords):
        best, best_score = "", 0
        for months in PATIENT_SAMPLES.values():
            for text in months.values():
                for sent in _re.split(r"(?<=[.!?])\s+", text):
                    s = sent.lower()
                    score = sum(1 for kw in keywords if kw.strip() in s)
                    word_count = len(sent.split())
                    if score > best_score and 8 <= word_count <= 55:
                        best_score, best = score, sent.strip()
        if not best:
            return "No representative comment found."
        words = best.split()
        raw = (" ".join(words[:40]) + "…") if len(words) > 40 else best
        return _html_mod.escape(raw)

    def _tags_html(keywords):
        shown = [kw.strip() for kw in keywords[:5] if len(kw.strip()) > 2]
        return "".join(
            f'<span style="background:#e8f2fc;color:#1a6fa8;border-radius:20px;'
            f'padding:2px 10px;font-size:0.74rem;font-weight:600;white-space:nowrap;">'
            f'{kw}</span>'
            for kw in shown
        )

    cards = ""
    for theme, s in top6:
        keywords   = _SEMANTIC_THEMES.get(theme, [])
        quote      = _extract_quote(keywords)
        tags       = _tags_html(keywords)
        pct        = f'{s["volume"]:.0f}'
        relevance  = _THEME_CLINICAL_RELEVANCE.get(theme, "")
        anchor     = _THEME_AHPEQS_ANCHOR.get(theme, "—")
        cards += (
            '<div style="border:1px solid #d1e5f7;border-radius:10px;padding:16px;'
            'background:#fafcff;display:flex;flex-direction:column;">'

            '<div style="display:flex;justify-content:space-between;'
            'align-items:flex-start;margin-bottom:10px;">'
            f'<span style="font-weight:700;color:#1a3a5c;font-size:0.95rem;">{theme}</span>'
            f'<span style="color:#1a6fa8;font-size:0.81rem;font-weight:600;'
            f'white-space:nowrap;margin-left:8px;">{pct}% of comments</span>'
            '</div>'

            f'<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;">{tags}</div>'

            f'<p style="font-style:italic;color:#444;font-size:0.83rem;margin:0 0 10px;'
            f'border-left:3px solid #c3d4e8;padding-left:10px;">"{quote}"</p>'

            f'<p style="font-size:0.81rem;color:#333;margin:0 0 10px;flex-grow:1;">'
            f'<span style="font-weight:700;">Clinical or operational relevance:</span> '
            f'{relevance}</p>'

            f'<div style="font-size:0.74rem;color:#1a6fa8;border-top:1px solid #e0eaf5;'
            f'padding-top:8px;margin-top:auto;">{anchor}</div>'
            '</div>'
        )

    return (
        '<div style="margin-top:24px;">'
        '<h3 style="font-size:1.05rem;font-weight:700;color:#ffffff;margin-bottom:12px;">'
        'Top-6 Impact Score Topics</h3>'
        '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;">'
        + cards +
        '</div></div>'
    )


def run_theme_impact_analysis(topic_model_label=""):
    scores = _compute_theme_impact()
    chart  = _build_theme_impact_chart(scores, topic_model_label)
    try:
        top6_cards = _build_top6_impact_cards_html(scores)
    except Exception:
        top6_cards = ""
    table      = _build_theme_breakdown_table_html(scores)
    prevalence = _build_theme_prevalence_table_html(scores)
    return chart, top6_cards, table, prevalence


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
    load_status = gr.HTML()

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
                    with gr.Row():
                        analyze_btn = gr.Button("Analyze", variant="primary", scale=3)
                        clear_btn   = gr.Button("🔄 New Patient", variant="secondary", scale=1)

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
                ts_btn       = gr.Button("Run Time-Series Analysis", variant="primary", scale=2)
                ts_clear_btn = gr.Button("🔄 New Patient", variant="secondary", scale=1)
            ts_summary  = gr.HTML()
            ts_report_file = gr.File(
                label="Download Time-Series Report (.html)",
                interactive=False,
            )
            with gr.Row():
                ts_line_plot = gr.Plot(show_label=False)
            with gr.Row():
                ts_cat_plot   = gr.Plot(show_label=False)
                ts_delta_plot = gr.Plot(show_label=False)

        # ── Tab 3: Topic & Theme Analytics ────────────────────────────────
        with gr.TabItem("Topic & Theme Analytics (1pMq)"):
            gr.Markdown(
                "Select a **topic model** and a **sentiment model**, choose Top-N topics, "
                "then click **Run Topic Analysis**. The chart shows the sentiment distribution "
                "across each top topic. Load patient data above first."
            )
            with gr.Row():
                topic_model_dd    = gr.Dropdown(
                    choices=_TOPIC_MODEL_CHOICES, value=_TOPIC_MODEL_CHOICES[0],
                    label="Topic model", scale=2,
                )
                topic_sent_dd     = gr.Dropdown(
                    choices=MODEL_CHOICES, value=MODEL_CHOICES[0],
                    label="Sentiment model", scale=2,
                )
                topic_top_n       = gr.Slider(minimum=1, maximum=5, value=3, step=1,
                                              label="Top N topics", scale=1)
            with gr.Row():
                topic_run_btn   = gr.Button("Run Topic Analysis", variant="primary", scale=3)
                topic_clear_btn = gr.Button("🔄 New Patient", variant="secondary", scale=1)
            topic_status    = gr.HTML()
            topic_report    = gr.File(label="Download Topic Report (.html)", interactive=False)
            topic_consensus = gr.HTML()
            with gr.Row():
                topic_table = gr.Plot(show_label=False)
                topic_chart = gr.Plot(show_label=False)
            with gr.Row():
                topic_ward_risk_chart  = gr.Plot(show_label=False)
                topic_risk_chart       = gr.Plot(show_label=False)
            with gr.Row():
                topic_monthly_chart = gr.Plot(show_label=False)
            with gr.Row():
                topic_score_chart = gr.Plot(show_label=False)
            topic_summary_table = gr.HTML(label="Monthly Summary")

        # ── Tab 4: Statewide Sentiment & HHS Profile ──────────────────────
        with gr.TabItem("Statewide Sentiment & HHS Profile (MpMq)"):
            gr.Markdown(
                "The statewide sentiment mix and an anonymised HHS rollup across all "
                f"**{len(PATIENT_NAMES)} patients**. HHSs are de-identified (HHS A–AJ); "
                "only aggregated percentages are shown. Select a sentiment model and click "
                "**Run Statewide Analysis** to compute."
            )
            with gr.Row():
                sw_model_dd = gr.Dropdown(
                    choices=MODEL_CHOICES, value=MODEL_CHOICES[0],
                    label="Sentiment model", scale=4,
                )
                sw_run_btn = gr.Button("Run Statewide Analysis", variant="primary", scale=1)
            sw_status           = gr.HTML()
            sw_download         = gr.File(label="Download Report (.html)", visible=True)
            sw_kpi              = gr.HTML()
            sw_bar_chart        = gr.Plot(show_label=False)
            sw_patient_chart    = gr.Plot(show_label=False)
            sw_ward_table       = gr.HTML()
            sw_peer_group_table = gr.HTML()
            sw_hhs_rollup_table = gr.HTML()

        # ── Tab 5: Recurring Semantic Themes ──────────────────────────────
        with gr.TabItem("Recurring Semantic Themes (MpMq)"):
            gr.Markdown(
                "Themes are derived from aspect-level keyword classification across all "
                f"**{len(PATIENT_NAMES)} patients**. A single comment may map to multiple themes; "
                "theme prevalence is therefore reported as *share of comments that mention this theme* "
                "and values do not sum to 100%. Each theme is anchored to relevant **AHPEQS** items "
                "and **NSQHS** standards where applicable. "
                "Impact score = f(volume × severity × trend)."
            )
            with gr.Row():
                theme_topic_model_dd = gr.Dropdown(
                    choices=_TOPIC_MODEL_CHOICES, value=_TOPIC_MODEL_CHOICES[0],
                    label="Topic model", scale=4,
                )
                theme_run_btn = gr.Button("Run Theme Analysis", variant="primary", scale=1)
            theme_impact_plot    = gr.Plot(show_label=False)
            theme_top6_cards     = gr.HTML()
            theme_breakdown_tbl  = gr.HTML()
            theme_prevalence_tbl = gr.HTML()

        # ── Tab 6: About ──────────────────────────────────────────────────
        with gr.TabItem("About"):
            gr.Markdown("""
## Models (13 total)

### Fine-tuned Healthcare Models (cjen1008)

| Key | HuggingFace model | Labels |
|-----|-------------------|--------|
| `bert_hc_v2` | `cjen1008/bert-healthcare-sentiment_v2` | NEGATIVE / NEUTRAL / POSITIVE |
| `distilroberta_hc_v2` | `cjen1008/distilroberta-healthcare-sentiment_v2` | NEGATIVE / NEUTRAL / POSITIVE |
| `distilbert_hc_v2` | `cjen1008/distilbert-healthcare-sentiment_v2` | NEGATIVE / NEUTRAL / POSITIVE |
| `bert_hc` | `cjen1008/bert-healthcare-sentiment` | NEGATIVE / NEUTRAL / POSITIVE |
| `distilbert_hc` | `cjen1008/distilbert-healthcare-sentiment` | NEGATIVE / NEUTRAL / POSITIVE |
| `distilroberta_hc` | `cjen1008/distilroberta-healthcare-sentiment` | NEGATIVE / NEUTRAL / POSITIVE |

### Pretrained General-Purpose Models

| Key | HuggingFace model | Labels |
|-----|-------------------|--------|
| `default` | `distilbert-base-uncased-finetuned-sst-2-english` | POSITIVE / NEGATIVE |
| `roberta` | `nlptown/bert-base-multilingual-uncased-sentiment` | 1–5 star rating |
| `emotion` | `j-hartmann/emotion-english-distilroberta-base` | ANGER · DISGUST · FEAR · JOY · NEUTRAL · SADNESS · SURPRISE |
| `amazon` | `sohan-ai/sentiment-analysis-model-amazon-reviews` | POSITIVE / NEGATIVE |
| `twitter` | `cardiffnlp/twitter-roberta-base-sentiment-latest` | NEGATIVE / NEUTRAL / POSITIVE |
| `sst2` | `textattack/bert-base-uncased-SST-2` | POSITIVE / NEGATIVE |
| `zeroshot` | `facebook/bart-large-mnli` | POSITIVE / NEGATIVE / NEUTRAL (zero-shot) |

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
    load_btn.click(fn=load_sample, inputs=[patient_dd, sample_dd], outputs=[text_input, load_status])
    theme_run_btn.click(fn=run_theme_impact_analysis, inputs=[theme_topic_model_dd], outputs=[theme_impact_plot, theme_top6_cards, theme_breakdown_tbl, theme_prevalence_tbl])
    sw_run_btn.click(
        fn=run_statewide_analysis,
        inputs=[sw_model_dd],
        outputs=[sw_status, sw_kpi, sw_bar_chart, sw_patient_chart, sw_ward_table, sw_peer_group_table, sw_hhs_rollup_table, sw_download],
    )
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

    # Clear all inputs + outputs and reset for a new patient
    _html_out = [sentiment_out, redacted_out, cleaned_out, removed_out,
                 normalized_out, tokenized_out, stemmed_out, lemmatized_out,
                 ner_out, pos_out]
    _plot_out  = [prob_plot, wc_plot, dist_plot]
    _file_out  = [report_file, report_file_pdf, report_file_html]
    _topic_outputs = [topic_status, topic_consensus, topic_table, topic_chart, topic_ward_risk_chart, topic_risk_chart, topic_report, topic_monthly_chart, topic_score_chart, topic_summary_table]

    topic_run_btn.click(
        fn=run_topic_analysis,
        inputs=[text_input, patient_dd, topic_model_dd, topic_sent_dd, topic_top_n],
        outputs=_topic_outputs,
    )

    _shared_reset  = [text_input, file_input, sample_dd, load_status]
    _topic_reset   = ["", "", None, None, None, None, None, None, None, ""]

    clear_btn.click(
        fn=lambda: ("", None, [], "",
                    *[""] * len(_html_out),
                    *[None] * len(_plot_out),
                    *[None] * len(_file_out),
                    *_topic_reset),
        outputs=_shared_reset + _html_out + _plot_out + _file_out + _topic_outputs,
    )

    ts_clear_btn.click(
        fn=lambda: ("", None, [], "", "", None, None, None, None, *_topic_reset),
        outputs=_shared_reset + [ts_summary, ts_line_plot, ts_cat_plot, ts_delta_plot, ts_report_file] + _topic_outputs,
    )

    topic_clear_btn.click(
        fn=lambda: ("", None, [], "", *_topic_reset),
        outputs=_shared_reset + _topic_outputs,
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
