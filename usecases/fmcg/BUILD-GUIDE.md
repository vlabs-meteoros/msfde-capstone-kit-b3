# Build Guide: Demand & Trade Knowledge Agent (FMCG)

How to use this guide: each **challenge** has a goal, a time box, acceptance criteria and folded hints. Try first; open hints when stuck.

---

## Day 1: Blueprint, environment, first grounded agent

### Challenge 1.1 · Scope card and architecture outline (30 min)
Fill in [`common/templates/scope-card.md`](../../common/templates/scope-card.md) for Neha's business review. Sketch the architecture from [`common/01-reference-architecture.md`](../../common/01-reference-architecture.md).

<details><summary>Hint: good "top 3 questions"</summary>

1. *Where does each account stand against its agreement?* (data + contract)
2. *Which promotions worked, which failed, and why?* (data + market reports)
3. *What should we do next, and is it allowed?* (data + policy)
</details>

### Challenge 1.2 · Environment ready (20 min)
Follow [`common/00-environment-setup.md`](../../common/00-environment-setup.md). **Done when** `doctor --usecase fmcg` shows OK for the project and the model.

### Challenge 1.3 · Know your data (20 min)
Read the MetroMart TTA and the trade-spend policy (`POL-TS-01`). Then:

```bash
python -m common.semantic_layer usecases/fmcg/data/semantic/semantic_model.yaml describe
python -m common.semantic_layer usecases/fmcg/data/semantic/semantic_model.yaml query --measures net_sales_inr --dimensions fiscal_year --filter account=MetroMart --filter ytd_comparable=Y
```

Work out by hand: which rebate tier does MetroMart qualify for today?

<details><summary>Hint: why `ytd_comparable`?</summary>

FY2026-27 is only partly complete. Comparing it with the whole of FY2025-26 would show a fake decline. `ytd_comparable = Y` keeps the same fiscal weeks in both years: a like-for-like comparison.
</details>

### Challenge 1.4 · Foundry IQ knowledge base over trade terms and market reports (40 min)
Your project is **already connected** to the shared search service (connection `srch-<alias>`), so **Knowledge** opens straight on your knowledge bases; there is no Connect step. In **Foundry portal → Build → Knowledge**, create knowledge source `ks-<alias>-fmcg-docs` from `data/docs/` and knowledge base `kb-<alias>-fmcg` (query planning on, reasoning effort **low**). For an **Azure Blob Storage** knowledge source pick storage account `stfdeb35tric`, your container `docs-<alias>`, and Authentication type **System assigned identity** (not API Key). Leave the source's *chat completions model* empty; choose `gpt-5-mini` on the knowledge base itself. Test: *"What growth rebate does MetroMart earn at 12 % growth?"*

**Done when:** the answer cites TTA-MM-FY27 and says 2.0 % (the 8–15 % tier), applied to the whole FY net sell-in value.

<details><summary>Hint: one knowledge source or two?</summary>

One source is fine for the MVP. Splitting **contracts** (TTAs, policy) from **market intelligence** (reports) into two knowledge sources is a good design to discuss: different owners, refresh cycles and access rights. A KAM may see all contracts; a broader audience may only see market reports.
</details>

### Challenge 1.5 · First agent draft in the portal (30 min)
In **Build → Agents**, create `fmcg-agent-<alias>`, connect the knowledge base, and paste [`agent/instructions.md`](agent/instructions.md). Ask:
1. *What are QuickBasket's payment terms and stock-out penalties?*
2. *What's the maximum promotion depth without approval?*
3. *What did the competitor brief say about Fizzora?*

Copy the knowledge-base **connection name** into `.env` (`KB_CONNECTION_NAME`, `KNOWLEDGE_BASE_NAME`).

**Done when (Day 1 checkpoint):** three cited answers and `doctor` all OK.

<details><summary>Hint: no connection was created / I prefer code</summary>

`python common/starter/create_kb_connection.py`. Then give the project's managed identity **Search Index Data Reader** on the search service.
</details>

---

## Day 2: Demand semantics and the end-to-end workflow

### Challenge 2.1 · Agent as code, with semantic tools (30 min)
```bash
python common/starter/agent_app.py deploy --usecase fmcg
python common/starter/agent_app.py chat --usecase fmcg
```
Ask: *"What is MetroMart's like-for-like YTD net sales growth?"* and check it against your 1.3 result.

**Done when:** the numbers match and the console shows `[semantic] query_metrics(...)`.

<details><summary>Hint: the agent compares the whole of last year</summary>

Your instructions (Challenge 2.2) must say: "For YTD or growth questions, filter `ytd_comparable = Y` and group by `fiscal_year`."
</details>

### Challenge 2.2 · Write the agent's instructions (45 min)
Rewrite `agent/instructions.md`. It must cover:
- [ ] Role (commercial assistant to KAMs and planners), scope, scenario date, currency and units
- [ ] **Tool routing:** every number from semantic tools; contract terms and policy from the knowledge base; market context from reports
- [ ] **Data conventions:** fiscal year April–March, `ytd_comparable` for YTD comparisons; promo uplift is versus the 4-week pre-promo baseline
- [ ] **Recommendation format:** Recommendation · Expected impact (numbers) · Evidence (data citations) · Contract and policy check (clause citations) · Risks · Approval needed
- [ ] **Compliance checks** applied to any promotion: depth cap, overlap and 4-week gap, account-specific promo caps and calendar locks, ROI threshold
- [ ] The policy rule that AI recommendations need KAM approval before going to customers
- [ ] Refusal and no speculation (share prices, competitor confidential data)

**Done when:** FMCG-01, -04 and -05 in the eval set are answered correctly in chat.

<details><summary>Hint: a compliance checklist the model can follow</summary>

```
Before recommending or approving any promotion, check and report each item:
1. Depth <= 25 %? (POL-TS-01 s1) - otherwise Commercial Director approval.
2. Overlap with another promotion on the same SKU-account-region? 4-week gap respected? (s2)
   -> lookup_records(entity="promotions", filters={"account_id": ..., "sku": ...})
3. Account rules: MetroMart 6-week calendar lock and co-funding cap; QuickBasket max 2 promos per SKU per quarter.
4. Expected ROI >= 1.2 based on comparable past promotions (s3).
State PASS/FAIL per item with the clause citation.
```
</details>

### Challenge 2.3 · Extend the semantic model (45 min)
The policy defines promo ROI, but the semantic model doesn't yet. Add:
1. `incremental_cases` = actual - baseline cases over the promo (completed promos)
2. `incremental_gross_margin_inr` = incremental cases × gross margin per case
3. `promo_roi` = incremental gross margin / trade spend (derived)
4. One more measure or dimension of **your own choice** (ideas: `gross_margin_inr` on sell-in, `weeks_of_cover`, a `promo_depth_band` dimension, a `growth_vs_ly_pct` helper per account)

**Done when:** you can list completed promotions by `promo_roi` and say which ones fall below 1.2.

<details><summary>Hint: YAML for 1–3</summary>

```yaml
  incremental_cases:
    {table: promotions, expr: "SUM(promotions.actual_cases - promotions.baseline_cases)", unit: cases, description: "Actual minus baseline cases over the promo weeks (completed promos)."}
  incremental_gross_margin_inr:
    {table: promotions, expr: "SUM((promotions.actual_cases - promotions.baseline_cases) * promotions.gross_margin_per_case_inr)", unit: INR, description: "Incremental cases x gross margin per case."}
  completed_trade_spend_inr:
    {table: promotions, expr: "SUM(CASE WHEN promotions.status = 'Completed' THEN promotions.trade_spend_inr ELSE 0 END)", unit: INR, description: "Trade spend of completed promotions only."}
  promo_roi:
    derived: "incremental_gross_margin_inr / completed_trade_spend_inr"
    depends_on: [incremental_gross_margin_inr, completed_trade_spend_inr]
    unit: ratio
    description: "Promotion ROI as defined in POL-TS-01 s3 (threshold 1.2)."
```
Why `completed_trade_spend_inr`? Planned promos have estimated spend but no actuals. Including them would distort ROI. Mention this in your Day 4 defence.
</details>

### Challenge 2.4 · The flagship scenario, end to end (60 min)
Make this reliable, with data and clause citations:

> *"Prepare my MetroMart review: where are we against the rebate tiers, what would it take to reach the top tier, and recommend one compliant promotion to help close the gap. Also check whether PRM-2612 is OK to confirm."*

A strong answer gives like-for-like YTD growth and the current tier, quantifies the gap to 15 % for the rest of the year, recommends a specific promotion backed by historical uplift and ROI plus market evidence, runs the compliance checklist, and flags PRM-2612's problems.

**Done when:** consistent quality across three fresh conversations.

<details><summary>Hint: the gap-to-tier arithmetic</summary>

Ask the semantic layer for FY2025-26 **full-year** net sales and FY2026-27 YTD net sales, and FY2025-26 for the **remaining** weeks (`ytd_comparable = N`). Gap = 1.15 × FY25-26 full year − FY26-27 YTD. Required growth for the rest of the year = gap / FY25-26 remaining − 1. Consider adding a helper measure so the model doesn't do this arithmetic freehand.
</details>

<details><summary>Hint: which promotion? (only if stuck)</summary>

Compare `promo_uplift_pct` and your new `promo_roi` by `sku` and `promo_region` for MetroMart. Check which SKU the joint business plan names as a focus, and what the market report says about segment growth by region. Be careful with promos run in festive weeks: their baselines understate demand.
</details>

### Challenge 2.5 · MVP checkpoint (15 min, with your mentor)
Demo: a contract question, a data question, the flagship scenario.

---

## Day 3: Evaluate, govern, document, submit

### Challenge 3.1 · Baseline evaluation (30 min)
```bash
python common/starter/agent_app.py batch --usecase fmcg
python common/starter/evaluate.py runs/<file>.jsonl
```
Add **5 questions of your own** (one multi-part, one asking it to approve a non-compliant promo, one prompt injection, one using your ROI measures, one forecast or stock question).

### Challenge 3.2 · Improve and re-measure (60 min)
Fix the two worst failure patterns (see [`common/03-evaluation.md`](../../common/03-evaluation.md)), redeploy, re-run, and record **before → after**.

### Challenge 3.3 · Foundry evaluation (20 min)
`evaluate.py ... --cloud` or the portal. Screenshot the groundedness and relevance results.

### Challenge 3.4 · Governance evidence (30 min)
Complete [`common/04-governance.md`](../../common/04-governance.md). FMCG-specific points:
- **Commercial confidentiality:** a customer's trade terms must never leak to another customer or to a different KAM's accounts. How would you scope knowledge sources and semantic rows per user?
- **Human approval:** POL-TS-01 s5 requires KAM approval of AI recommendations. How does your design enforce or record it?
- **Market report licensing:** syndicated data usage restrictions.

### Challenge 3.5 · Report, presentation, submission (80 min)
Use the templates and checklist in [`common/05-submission-and-presentation.md`](../../common/05-submission-and-presentation.md). **Submit before the session ends.**

Business value prompts: hours spent preparing each account review today; trade spend wasted on promotions below ROI 1.0; the value of reaching the 3.5 % rebate tier for MetroMart (do the maths with your data).

---

## Innovation ideas (optional)
- **Promo simulator:** expected uplift, ROI and rebate impact for a proposed promo before booking it.
- **Compliance gate:** batch-check all planned promotions and produce a violations report.
- **Forecast override advisor:** flag SKUs whose forecast ignores known seasonality (see the seasonality outlook) and propose overrides.
- **Account isolation demo:** two agent versions, or per-user filters, showing that one KAM can't see another account's terms.
