# Microsoft FDE Capstone: Microsoft IQ Agents (Batch 3)

Wipro AI Academy · Microsoft FDE · L200–L300 developers · 4 days × 4 hours · individual build

Over three days you build an enterprise knowledge agent in **Azure AI Foundry**. It grounds answers in documents through **Foundry IQ**, pulls governed business metrics from a **semantic layer**, gets evaluated, and ships with a governance design. On Day 4 you demo and defend it.

Pick **one** of the three use cases:

| Track | Agent | It must combine… | Folder |
|---|---|---|---|
| Manufacturing | **Quality-Insights Knowledge Agent** | SOPs, supplier specs and past CAPA reports **+** defect and process data, to give a cited root-cause hypothesis | [usecases/manufacturing](usecases/manufacturing/README.md) |
| Retail | **Unified Customer-Context Grounding Agent** | Product and policy docs **+** approved web **+** customer and transaction data, to give a cited service answer | [usecases/retail](usecases/retail/README.md) |
| FMCG | **Demand & Trade Knowledge Agent** | Trade-terms agreements and market reports **+** demand, promotion and forecast data, to give a cited commercial recommendation | [usecases/fmcg](usecases/fmcg/README.md) |

All companies, people, products and numbers in this repo are synthetic.

---

## What the lab environment gives you, and what stands in for the rest

| Capability in the brief | In this lab | Why |
|---|---|---|
| Azure AI Foundry agent | ✅ Foundry Agent Service (portal + Python SDK) | |
| Foundry IQ grounding | ✅ Foundry IQ knowledge base on Azure AI Search | |
| Approved web (Retail) | ✅ Foundry IQ **Web** knowledge source with a domain allow-list, **or** the provided web snapshots if Web is disabled | Web grounding costs extra, sends queries outside the Azure boundary, and an admin may have turned it off |
| Fabric IQ semantics | 🔁 **Local semantic layer** ([common/semantic_layer](common/semantic_layer)): a YAML semantic model over CSVs, exposed to the agent as function tools | No Fabric capacity in the lab tenant. The contract is the same as Fabric IQ's: governed measures, dimensions and entities, never raw SQL. |
| Evaluation | ✅ Local checks + Foundry built-in evaluators | |
| Agent 365 governance | 🔁 **Governance design + evidence** from what Foundry already gives you (identity, RBAC, tracing, guardrails), mapped to Agent 365 controls | Agent 365 isn't enabled in the lab tenant |

When you present, say plainly which pieces are substitutes and how you would swap in the real service. The panel scores that under *Deployment Readiness*.

---

## The four days

| Day | Hours | You will… | Checkpoint (mentor signs off) |
|---|---|---|---|
| **1** | 1.5 h briefing + 2.5 h build | Choose a use case, outline the architecture, set up the environment, build a **first agent grounded on documents** | Use-case and scope card · architecture outline · first cited answer |
| **2** | 4 h build | Wire in the **semantic layer**, extend it, complete the **end-to-end workflow** with combined doc + data answers | **Working MVP**: demo one combined cited answer |
| **3** | 4 h build + submit | Fix gaps, **evaluate**, write the **governance** notes, write up the project, **submit by end of session** | Submission package received |
| **4** | 4 h | Present (5-minute slots: 4 min demo + 1 min Q&A), defend in Q&A. With ~60 participants, some slots start in the **second half of Day 3** | Panel scores |

Each use-case `BUILD-GUIDE.md` breaks the days into **challenges**. Every challenge has a goal, acceptance criteria and folded **hints** (open them only when you need them). You build the agent yourself; the hints keep you from getting stuck.

---

## Repo map

```
README.md                         <- you are here
.env.sample                       <- copy to .env
requirements.txt                  <- participant Python packages
common/
  LAB-ENVIRONMENT.md              <- your account, project, endpoints, naming rules (read first)
  00-environment-setup.md         <- Day 1: VM, Azure access, Foundry, Foundry IQ
  01-reference-architecture.md    <- the target architecture and what's substituted
  02-semantic-layer.md            <- how the Fabric IQ stand-in works and how to extend it
  03-evaluation.md                <- evaluation approach, metrics, evidence
  04-governance.md                <- identity, scoping, audit (Agent 365 mapping)
  05-submission-and-presentation.md
  semantic_layer/                 <- the local semantic layer engine (Python)
  starter/                        <- agent_app.py (deploy/chat/batch), evaluate.py, create_kb_connection.py
  templates/                      <- scope card, project report and presentation templates
usecases/<track>/
  README.md                       <- business brief, persona, success criteria
  BUILD-GUIDE.md                  <- day-by-day challenges with hints
  agent/instructions.md           <- your agent's system prompt (starts minimal, you improve it)
  data/docs/                      <- knowledge documents for Foundry IQ (PDF/DOCX)
  data/semantic/                  <- CSVs + semantic_model.yaml (Fabric IQ stand-in)
  data/web-snapshots/             <- (Retail only) fallback for approved web
  eval/test-questions.jsonl       <- evaluation set with ground truth
facilitator/                      <- NOT for participants (answer keys, planted signals, run-of-show)
tools/                            <- data generator and kit validator
```

## Quick start

```bash
git clone <this repo> && cd msfde-capstone-kit
python -m venv .venv && .venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.sample .env                                  # then fill it in
az login
python tools/validate_kit.py                           # checks the data kit (no Azure needed)
python common/starter/agent_app.py doctor --usecase manufacturing
```

Then open your use case's `BUILD-GUIDE.md`.

## Evaluation dimensions (Day 4 panel)

Solution Design & Architecture · Technical Implementation · Deployment Readiness · Business Value Realization · Innovation · Presentation & Defense. See [common/05-submission-and-presentation.md](common/05-submission-and-presentation.md) for what evidence scores well on each.
