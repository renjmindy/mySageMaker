# Elicitation Techniques
- Show the site grid heatmap and ask "what do you see that is wrong / expected?"
- Walk the screenshot (Contactor Select) together to confirm blue/grey semantics.
- Ask for the last three maintenance events and check them against detected events.
- Confirm each rule in writing (assumptions log id).

## Using the generated guide
- Ask by role, in the guide's order of impact: decisions that block a deliverable first (A11 blocks OEE; A13 blocks any physical-cause statement), owners and facts next.
- Show the closed-now report (`site_heatmap.py`) and the ranked list when asking about repairs or events; ask for a screenshot or maintenance record to check them against.
- After each answer: update the assumptions log (decision) or the deliverable's open marker (fact), run `open_questions.py --write`, and watch the item leave the list. A question that keeps coming back means the answer was not recorded.
- Never ask a stakeholder to confirm a rule they do not own; route it to the role that does.
