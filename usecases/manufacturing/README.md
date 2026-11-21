# Manufacturing: Quality-Insights Knowledge Agent

## Business context

**Kestrel Motion Systems** (fictional) makes hydraulic pump housings, brake caliper brackets and valve covers at Plant KMS-P2. When a quality issue appears, a quality engineer has to join **unstructured knowledge** (SOPs, supplier specifications, past CAPA/8D reports, maintenance notes) with **structured data** (defects, production batches, process parameters, material lots, complaints). Today that join is manual, slow, and depends on who does it.

## Persona

**Ravi, Quality Engineer, Line 2.** On Monday morning, Ravi sees a third leak complaint from a key customer. Before the 10:00 quality review he needs to know: *is this real, how big is it, what changed, have we seen it before, and what do we do now?*

## What your agent must do

Return a **grounded, cited root-cause hypothesis** that uses **meaningful defect metrics**:

- Quantify the issue with governed measures (PPM, scrap cost, complaint units) from the semantic layer
- Find the relevant procedure limits, supplier specs and prior CAPAs through Foundry IQ
- Combine both into a hypothesis with evidence, recommended containment and corrective actions, and confidence
- Cite every claim: `semantic://` citations for numbers, document references for procedures
- Prefer **current** documents over superseded revisions
- Decline questions the sources can't answer

## Your data

| Folder | Contents |
|---|---|
| `data/docs/` (12 files) | SOPs (incl. one **superseded** revision), supplier specs, three CAPA reports, quality manual, control plan, maintenance notes |
| `data/semantic/` | `production_batches` (Jun–Oct 2026, with degassing time and density index), `defects`, `defect_codes`, `parts`, `lines`, `supplier_lots` (certificate values), `suppliers`, `customer_complaints` + `semantic_model.yaml` |
| `eval/test-questions.jsonl` | 10 evaluation questions with ground truth |

## Success criteria (MVP)

- [ ] Answers document-only, data-only and combined questions with citations
- [ ] Produces a root-cause hypothesis for the current top quality issue that a quality manager would accept
- [ ] Semantic model extended with at least two new measures or dimensions
- [ ] Evaluation: fact recall ≥ 0.8, all refusals correct, groundedness evidence
- [ ] Governance notes complete

Start with [BUILD-GUIDE.md](BUILD-GUIDE.md).
