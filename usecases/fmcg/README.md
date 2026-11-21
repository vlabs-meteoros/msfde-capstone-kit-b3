# FMCG: Demand & Trade Knowledge Agent

## Business context

**Verdant Consumer Brands** (fictional) sells beverages (ZingUp energy, Citrus Fizz, Coco Pure) and snacks (Masala Crunch, Oat Bite) in India through modern trade, quick commerce, e-commerce and general-trade distributors. Planners and key account managers (KAMs) have to combine **trade-terms agreements** and **market reports** with **demand data** (sell-in, sell-out, promotions, forecasts). Today that synthesis is manual and inconsistent, and it misses how trade terms interact with demand: rebate tiers, promo caps, penalties.

## Persona

**Neha, Key Account Manager for MetroMart and QuickBasket.** She is preparing the monthly business review. She needs to know where the accounts stand against their agreements, which promotions worked or failed and why, and what to recommend next, compliant with policy and backed by data.

## What your agent must do

Return a **cited demand and trade recommendation**:

- Demand context from the semantic layer: net sales, YTD growth, sell-out trends, promo uplift, stock-outs, forecast accuracy
- Trade terms and market context from Foundry IQ: rebate tiers, co-funding, penalties, promo policy, market and competitor reports
- Recommendations that **comply** with the trade-spend policy and agreements, show the numbers, and cite the clauses
- Flag non-compliant plans; decline speculation outside the sources

Currency is INR, quantities are cases, the fiscal year runs April–March, actuals run through the week of 2026-11-09, and the scenario date is **2026-11-20**.

## Your data

| Folder | Contents |
|---|---|
| `data/docs/` (8 files) | MetroMart TTA, QuickBasket commercial terms, distributor agreement, trade-spend policy, Q3 market pulse, competitor brief, seasonality outlook, MetroMart joint business plan |
| `data/semantic/` | `sell_in`, `sell_out` (with closing stock), `promotions` (completed and planned), `forecast`, `calendar` (fiscal), `products`, `accounts` + `semantic_model.yaml` |
| `eval/test-questions.jsonl` | 10 evaluation questions with ground truth |

## Success criteria (MVP)

- [ ] Correct like-for-like YTD growth vs rebate tiers, with clause citations
- [ ] Explains promo performance using data **and** market or competitor documents
- [ ] Detects policy violations in planned promotions
- [ ] Semantic model extended with promo ROI and at least one more item
- [ ] Evaluation: fact recall ≥ 0.8, refusals correct, groundedness evidence
- [ ] Governance notes complete

Start with [BUILD-GUIDE.md](BUILD-GUIDE.md).
