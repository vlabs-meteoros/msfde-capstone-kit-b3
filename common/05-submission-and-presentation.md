# 05 · Submission (end of Day 3) and presentation (Day 4)

## Submission checklist: due before the Day 3 session closes

Put everything in a folder named `submission-<alias>-<usecase>/` (zip it or push a branch, whichever your facilitator asks for).

| # | Item | Contents | ✔ |
|---|---|---|---|
| 1 | **Project report** | Completed `templates/project-report-template.md` (Markdown or exported to PDF/DOCX) | ☐ |
| 2 | **Agent definition** | Final `agent/instructions.md`, agent name and version, model deployment | ☐ |
| 3 | **Semantic model** | Your extended `semantic_model.yaml` and a list of what you added | ☐ |
| 4 | **Foundry IQ configuration** | Knowledge source and knowledge base names, source types, retrieval settings (screenshots or JSON) | ☐ |
| 5 | **Evaluation evidence** | Final and earlier `runs/*.eval.md`, your added questions, Foundry evaluation screenshots, before/after table | ☐ |
| 6 | **Governance notes** | Identity, scoping, audit, Agent 365 mapping (the report section is enough) | ☐ |
| 7 | **Reproducibility** | Prerequisites, `.env` keys (no secrets), steps to redeploy in under 15 minutes | ☐ |
| 8 | **Presentation draft** | Slides or an outline following the structure below | ☐ |

**Never submit** `.env`, keys or tokens.

## Presentation: 5 minutes per participant, strictly timed

About 60 participants present, so each slot is **4 minutes of presentation + 1 minute of panel questions**. Some slots may move to the second half of Day 3. Be ready by the start of Day 3's second half.

| Time | Section | Tips |
|---|---|---|
| 0:30 | Business problem and user | One persona, one painful moment, one number |
| 0:45 | Architecture | One diagram; name the substitutes (semantic layer for Fabric IQ, governance design for Agent 365) in one sentence |
| 2:00 | **Live demo** | Exactly **two** questions: one **combined doc + data** question (your flagship) and one refusal or edge case. Show the citations. Keep a screenshot backup ready. |
| 0:45 | Evidence and value | One slide: eval metrics + before/after, governance in 3 bullets, the business value number |
| 1:00 | Panel Q&A | Expect a hidden question run live against your agent |

Have the chat window open and **already warmed up** (one question asked) before your slot starts. There's no time to log in during your slot.

## How the panel scores (from the capstone brief)

| Dimension | What earns marks | Evidence |
|---|---|---|
| **Solution Design & Architecture** | Fit to the business need; sound tool and source choices; security and scalability reasoning | Diagram, decision table |
| **Technical Implementation** | Working agent; both grounding types integrated; extended semantic model; clean prompts | Live demo, config, code |
| **Deployment Readiness** | Reproducible; runbook; limitations stated; governance approach; honest about substitutes | Report sections 7–9 |
| **Business Value Realization** | Quantified outcome (time, cost, risk), adoption path | Business case slide |
| **Innovation** | Something beyond the baseline: e.g. confidence scoring, proactive alerts, multi-turn clarification, extra measures, an evaluator you wrote | Demo, report |
| **Presentation & Defense** | Clear story; handles hidden questions and "what if" probes | Q&A |

## Demo-day reliability tips

- Deploy your final version the evening of Day 3 and **don't change it** on Day 4.
- Warm up: run one question 5 minutes before your slot.
- Keep `runs/` output from a good batch as backup evidence if the network fails.
