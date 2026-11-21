# Retail: Unified Customer-Context Grounding Agent

## Business context

**Harbor & Pine** (fictional) is an omnichannel home and lifestyle retailer: 6 US stores and an online shop. Its service assistants give weak answers because they ground on **one source at a time**: product docs *or* order data, never both, and they can't see current manufacturer or regulatory information. Customers get generic and often wrong answers about returns, warranties and recalls.

## Persona

**Jess, Customer Care Associate (chat and phone).** A customer is on the line. Jess has the customer ID and a vague complaint. She needs one answer that combines **who the customer is and what they bought** (tier, delivery date, lot number) with **what our policy says** and **what the manufacturer says right now**, and tells her what to do next.

## What your agent must do

Return a **unified, cited answer** across sources:

- Customer and transaction context from the semantic layer (tier, purchase history, days since delivery, serial or lot, protection plan)
- Policy and product knowledge from Foundry IQ (returns, price match, loyalty, warranty, recall notice, product guides)
- **Approved web** context from Foundry IQ (manufacturer pages, regulators) through a Web knowledge source with an allow-list, plus curated **web snapshots** of manufacturer pages
- A clear decision (eligible / not eligible / route to warranty / recall procedure), next steps for the associate, and citations
- Protect customer data: never reveal payment card details; minimum PII

Scenario date ("today") is **2026-11-20**.

## Your data

| Folder | Contents |
|---|---|
| `data/docs/` (9 files) | Returns and refunds policy, price-match policy, loyalty terms, protection plan and warranty guide, shipping policy, recall notice, 3 product guides |
| `data/web-snapshots/` (3 files) | Captured manufacturer web pages (warranty claim process, recall page, descaling guide) |
| `data/approved-web-domains.txt` | Allow-list for the live Web knowledge source |
| `data/semantic/` | `customers` (606), `orders`, `order_lines`, `returns`, `support_tickets`, `products`, `stores`, and the `purchase_history` view + `semantic_model.yaml` |
| `eval/test-questions.jsonl` | 10 evaluation questions with ground truth |

## Success criteria (MVP)

- [ ] Correct eligibility decisions that combine customer data with policy rules (tiers, return classes, trial rules, recall override)
- [ ] Uses web grounding (live or snapshot) with citations
- [ ] Semantic model extended with at least two new measures or dimensions
- [ ] Evaluation: fact recall ≥ 0.8, all refusals correct (including PII requests), groundedness evidence
- [ ] Governance notes complete, including the web data-boundary decision

Start with [BUILD-GUIDE.md](BUILD-GUIDE.md).
