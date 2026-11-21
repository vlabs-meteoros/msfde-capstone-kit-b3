# Build Guide: Quality-Insights Knowledge Agent (Manufacturing)

How to use this guide: each **challenge** has a goal, a time box, acceptance criteria and folded hints. Try first; open hints when stuck. Timings assume Day 1 has 2.5 h of build time after the briefing.

---

## Day 1: Blueprint, environment, first grounded agent

### Challenge 1.1 · Scope card and architecture outline (30 min)
Fill in [`common/templates/scope-card.md`](../../common/templates/scope-card.md) for Ravi's problem (see [README](README.md)). Sketch the architecture from [`common/01-reference-architecture.md`](../../common/01-reference-architecture.md).

**Done when:** your mentor has seen the scope card and diagram.

<details><summary>Hint: good "top 3 questions"</summary>

Think about what Ravi needs before the 10:00 review:
1. *How big is the issue and since when?* (data)
2. *What do our procedures and specs say should happen?* (documents)
3. *What is the most likely cause, and have we seen it before?* (combined)
</details>

### Challenge 1.2 · Environment ready (20 min)
Follow [`common/00-environment-setup.md`](../../common/00-environment-setup.md).

**Done when:** `python common/starter/agent_app.py doctor --usecase manufacturing` shows OK for the project and the model deployment.

### Challenge 1.3 · Know your data (20 min)
Skim the 12 documents in `data/docs/` and explore the semantic model:

```bash
python -m common.semantic_layer usecases/manufacturing/data/semantic/semantic_model.yaml describe
```

Answer these yourself with the CLI (you'll compare later with what the agent says):
- Which part has the highest gas-porosity (`POR-GAS`) PPM, and in which month?
- What is the average degassing time by shift on Line 2?

**Done when:** you can name the part, month and line where something looks wrong.

<details><summary>Hint: CLI queries</summary>

```bash
python -m common.semantic_layer usecases/manufacturing/data/semantic/semantic_model.yaml query --measures defect_rate_ppm --dimensions part_number month --filter defect_code=POR-GAS --order-by defect_rate_ppm
python -m common.semantic_layer usecases/manufacturing/data/semantic/semantic_model.yaml query --measures avg_degas_minutes --dimensions month shift --filter line=L2 --order-by month --ascending
```
</details>

### Challenge 1.4 · Foundry IQ knowledge base over the quality documents (40 min)
In the **Foundry portal (new Foundry) → Build → Knowledge**, connect the shared search service and create:
- a **knowledge source** with all files from `data/docs/` (name: `ks-<alias>-mfg-docs`)
- a **knowledge base** `kb-<alias>-mfg` that uses it, with an LLM for query planning (your chat deployment) and retrieval reasoning effort **low**

Test it in the knowledge base's test pane: *"What is the minimum degassing time per ladle?"*

**Done when:** the test returns an answer that cites **SOP-PRD-210 Rev D** (12 minutes), not Rev C (10 minutes).

<details><summary>Hint: which knowledge source type?</summary>

- **Azure Blob**: upload the files to your container (`az storage blob upload-batch -d docs-<alias> -s usecases/manufacturing/data/docs --account-name <storage> --auth-mode login`) and point the source at it. Foundry IQ builds the indexer, chunking and embeddings for you.
- **File** (direct upload) works too if no storage account was provided.
- Either way, wait for indexing to finish (the source shows document counts) before testing.
</details>

<details><summary>Hint: the test cites the superseded Rev C</summary>

Both revisions are in the index on purpose: real document libraries contain old versions. You'll fix this in the agent instructions (Challenge 2.2). If your knowledge base has a *retrieval instructions* field, you can also add: "Prefer documents marked current; ignore documents marked SUPERSEDED unless asked about history."
</details>

### Challenge 1.5 · First agent draft in the portal (30 min)
In **Build → Agents**, create an agent `mfg-agent-<alias>` on your model deployment, **connect your knowledge base**, and paste the starter instructions from [`agent/instructions.md`](agent/instructions.md). In the playground, ask:
1. *What does the current die-casting SOP require for degassing and density index?*
2. *What corrective actions came out of CAPA-2025-014?*
3. *What is the hydrogen limit for A356 ingot?*

Then find the **connection name** the portal created for the knowledge base (project → **Connected resources / Connections**, category Remote tool). Put it in `.env` as `KB_CONNECTION_NAME`, along with `KNOWLEDGE_BASE_NAME`.

**Done when (Day 1 checkpoint):** three cited answers, blockers logged, `.env` complete, and `doctor` shows all OK.

<details><summary>Hint: no connection was created / I prefer code</summary>

Run `python common/starter/create_kb_connection.py` (needs `PROJECT_RESOURCE_ID` and the Foundry Project Manager role). Then make sure the project's managed identity has **Search Index Data Reader** on the search service.
</details>

---

## Day 2: Semantic context and the end-to-end workflow

### Challenge 2.1 · Agent as code, with semantic tools (30 min)
The portal agent can only read documents. To give it governed defect metrics, deploy it from code with the semantic-layer function tools:

```bash
python common/starter/agent_app.py deploy --usecase manufacturing
python common/starter/agent_app.py chat --usecase manufacturing
```

Ask: *"What was the POR-GAS PPM for HX-220 by month?"* and check it against your CLI result from 1.3.

**Done when:** the answer matches the CLI numbers and the console shows `[semantic] query_metrics(...)`.

<details><summary>Hint: what is deploy doing?</summary>

Read `common/starter/agent_app.py` → `build_tools()`. It attaches **one MCP tool** (your Foundry IQ knowledge base, through the project connection) and **three function tools** generated from `semantic_model.yaml`. Each deploy creates a **new agent version** in Foundry; the portal shows the history. Function tools run on your machine: when the model asks for `query_metrics`, `run_turn()` executes it and sends the JSON result back.
</details>

<details><summary>Hint: the agent guesses numbers instead of calling the tool</summary>

Your instructions must tell it when to use which tool. That's Challenge 2.2. For now, try "Use the query_metrics tool to…" in the question to confirm the wiring works.
</details>

### Challenge 2.2 · Write the agent's instructions (45 min)
`agent/instructions.md` is deliberately minimal. Rewrite it so the agent behaves like a senior quality engineer. Redeploy after every meaningful change (`deploy` is cheap and versioned).

Your instructions must cover:
- [ ] Role, user and scope (what's in and out)
- [ ] **Tool routing:** numbers only from `query_metrics` / `lookup_records`; procedures, specs and CAPA history only from the knowledge base; combined questions use both
- [ ] **Document precedence:** current revision over superseded; say which revision you used
- [ ] **Answer structure** for root-cause questions (see below)
- [ ] **Citations:** document references for document claims, the `citation` string from tool results for numbers
- [ ] **Refusal:** say what isn't in the sources instead of guessing (for example selling prices)
- [ ] Data conventions: months are `YYYY-MM`, weeks are `week_start` Mondays; don't do arithmetic you can ask the semantic layer for

Suggested root-cause answer format:
```
Summary (2 lines)
Evidence from data   - metric, trend, comparison  [semantic://...]
Evidence from documents - limits, specs, prior CAPA  [doc]
Hypothesis and confidence (High/Medium/Low) - and what would confirm it
Recommended actions - containment now / corrective / preventive, with owners
Gaps and caveats
```

**Done when:** a document-only, a data-only and a refusal question all behave correctly.

<details><summary>Hint: an instructions skeleton</summary>

```markdown
# Role
You are the Quality-Insights assistant for Kestrel Motion Systems Plant KMS-P2...

# Tools - when to use which
- knowledge_base_retrieve: SOPs, control plans, supplier specifications, CAPA/8D reports, quality manual, maintenance notes.
- describe_semantic_model / query_metrics / lookup_records: ANY number (PPM, quantities, costs, process parameters, lots, complaints).
- For "why" or "what should we do" questions, use BOTH...

# Rules
- Never estimate or compute a metric yourself if a measure exists...
- If two document revisions conflict, use the one marked current/effective...

# Answer format
...

# Out of scope
...
```
</details>

<details><summary>Hint: citations from the knowledge base look odd</summary>

The Foundry IQ tool returns references with source names. Ask the agent to "list sources at the end as: [n] document name - section". Check the `citations:` line that `agent_app.py chat` prints.
</details>

### Challenge 2.3 · Extend the semantic model (45 min)
Ravi's managers talk about **first-pass yield** and **cost of poor quality**, which the model doesn't define yet. Add to `data/semantic/semantic_model.yaml`:

1. `first_pass_yield_pct`: share of units produced without a defect (derived measure)
2. `rework_cost_usd` and `cost_of_poor_quality_usd`: scrap cost + rework cost (`parts.rework_cost_usd`)
3. A dimension `lot_h2_status` (`in-spec` / `out-of-spec` against the 0.15 ml/100 g hydrogen limit from the supplier spec)
4. One more measure or dimension of **your own choice** that helps root-cause analysis (ideas: `density_hold_count`, batches with density index > 4.0, `degas_below_sop` flag)

Test each with the CLI, then redeploy.

**Done when:** `query_metrics` returns sensible values for all four, and you can show PPM by `lot_h2_status` × `shift`.

<details><summary>Hint: YAML for 1 and 2</summary>

```yaml
  rework_qty:       {table: defects, expr: "SUM(defects.rework_qty)", unit: units, description: "Defective units reworked."}
  rework_cost_usd:  {table: defects, expr: "ROUND(SUM(defects.rework_qty * parts.rework_cost_usd), 2)", unit: USD, description: "Rework quantity x part rework cost."}
  cost_of_poor_quality_usd:
    derived: "scrap_cost_usd + rework_cost_usd"
    depends_on: [scrap_cost_usd, rework_cost_usd]
    unit: USD
    description: "Internal cost of poor quality = scrap cost + rework cost."
  first_pass_yield_pct:
    derived: "100 - defect_qty * 100 / units_produced"
    depends_on: [defect_qty, units_produced]
    unit: "%"
    description: "Approximate first-pass yield: % of units produced without a recorded defect."
```
`parts` is reachable from `defects` via `production_batches`, so the join is automatic.
</details>

<details><summary>Hint: YAML for 3</summary>

```yaml
  lot_h2_status:
    table: supplier_lots
    expr: "CASE WHEN supplier_lots.hydrogen_ml_per_100g > 0.15 THEN 'out-of-spec' WHEN supplier_lots.hydrogen_ml_per_100g IS NULL THEN 'n/a' ELSE 'in-spec' END"
    description: "Material lot hydrogen vs the A356 spec limit (0.15 ml/100 g, SUP-SPEC-ALV-A356 Rev 4)."
```
Discussion point for Day 4: the 0.15 limit now lives in two places (spec document and semantic model). How would you govern that?
</details>

### Challenge 2.4 · The flagship scenario, end to end (60 min)
Make this work reliably, with citations from both sources:

> *"We have three leak complaints from Orion on HX-220. Give me a root-cause hypothesis with evidence and recommended actions."*

A strong answer quantifies the spike (when, how big, which shift), connects it to material and process evidence, checks it against procedure limits and the history of similar issues, and recommends containment per the quality manual. Iterate on instructions, tool descriptions and the semantic model until the answer is something you'd take to the quality review.

**Done when:** you get the same quality of answer on three runs in fresh conversations.

<details><summary>Hint: the agent stops after one tool call</summary>

Tell it to **plan first** in the instructions: "For root-cause questions: (1) quantify the defect trend by week and shift, (2) check process parameters and material lots for the affected period, (3) retrieve the relevant SOP limits, supplier spec and prior CAPAs, (4) compare and conclude." You can also raise `MAX_TOOL_ROUNDS` in `agent_app.py`.
</details>

<details><summary>Hint: where to look in the data (only if you're stuck)</summary>

Slice POR-GAS PPM by `week_start` and `shift` for HX-220. Then for those weeks look at `avg_degas_minutes`, `max_density_index` and `material_lot`. Then `lookup_records` on `supplier_lots`. One of the documents was written by maintenance, not quality.
</details>

### Challenge 2.5 · MVP checkpoint (15 min, with your mentor)
Demo: one document question, one data question, the flagship scenario. Agree your Day 3 fix list.

---

## Day 3: Evaluate, govern, document, submit

### Challenge 3.1 · Baseline evaluation (30 min)
```bash
python common/starter/agent_app.py batch --usecase manufacturing
python common/starter/evaluate.py runs/<file>.jsonl
```
Then add **5 questions of your own** to `eval/test-questions.jsonl` (one multi-part, one adversarial or prompt injection, one about the superseded SOP, one using your new measures).

### Challenge 3.2 · Improve and re-measure (60 min)
Pick the two worst failure patterns from the report (see the diagnosis table in [`common/03-evaluation.md`](../../common/03-evaluation.md)), fix them, redeploy, re-run. Record a **before → after** table.

### Challenge 3.3 · Foundry evaluation (20 min)
`python common/starter/evaluate.py runs/<file>.jsonl --cloud`, or run the evaluation from the portal. Screenshot groundedness and relevance results.

### Challenge 3.4 · Governance evidence (30 min)
Complete the identity, scoping, audit and Agent 365 mapping from [`common/04-governance.md`](../../common/04-governance.md). Manufacturing-specific points to address:
- The agent is **decision support**: CAPA decisions and customer communication stay with humans.
- Supplier and customer data sensitivity (supplier quality performance is commercially sensitive).
- Who may extend the semantic model (measure definitions are quality-system controlled documents).

### Challenge 3.5 · Report, presentation, submission (80 min)
Use [`common/templates/project-report-template.md`](../../common/templates/project-report-template.md) and the checklist in [`common/05-submission-and-presentation.md`](../../common/05-submission-and-presentation.md). **Submit before the session ends.**

Business value prompts: how long does a manual root-cause investigation take today (hours to days)? What does one customer escape cost? How quickly would the agent have flagged the spike from the weekly data?

---

## Innovation ideas (optional, scored under *Innovation*)
- **Proactive watch:** a script that checks the weekly POR-GAS PPM against the SOP-QA-101 trend threshold (3,000 PPM) and asks the agent to draft an investigation brief.
- **8D drafter:** the agent fills D2–D4 of an 8D template from its findings.
- **Recurrence detector:** compare a new issue's signature with past CAPAs automatically.
- **Confidence scoring:** the agent states which evidence would raise or lower its confidence and asks a clarifying question when evidence conflicts.
- **Custom evaluator:** check that every number in an answer appears in a tool result.
