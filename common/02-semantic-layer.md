# 02 · The local semantic layer (Fabric IQ stand-in)

## Why it exists

Fabric IQ gives agents **business meaning** on top of raw tables: named entities, relationships and *governed* measures. "Defect rate", "return rate" or "net sales" always mean one agreed calculation. The lab tenant has no Fabric capacity, so this kit ships a small engine with the same contract:

| Fabric IQ concept | Local equivalent |
|---|---|
| Semantic model / ontology | `usecases/<uc>/data/semantic/semantic_model.yaml` |
| Lakehouse tables | CSV files next to the YAML (loaded into in-memory SQLite) |
| Measures (DAX) | `measures:` (SQL aggregate or a `derived:` formula over other measures) |
| Dimensions and attributes | `dimensions:` |
| Relationships | `relationships:` (many-to-one, `from` → `to`) |
| Data agent / ontology query | Three agent tools: `describe_semantic_model`, `query_metrics`, `lookup_records` |

The agent **never writes SQL**. It asks for measures by name, grouped by dimensions and filtered by dimension values. The engine builds parameterised SQL, avoids double-counting when measures come from different fact tables, and returns a **citation** string to quote in the answer.

## Try it from the command line first

```bash
python -m common.semantic_layer usecases/manufacturing/data/semantic/semantic_model.yaml describe
python -m common.semantic_layer usecases/manufacturing/data/semantic/semantic_model.yaml query ^
    --measures defect_rate_ppm defect_qty units_produced --dimensions month ^
    --filter part_number=HX-220 --filter defect_code=POR-GAS
python -m common.semantic_layer usecases/retail/data/semantic/semantic_model.yaml lookup purchase_history ^
    --filter customer_id=C-10482
```

Filter syntax on the CLI: `dim=value`, `dim=a,b` (in), `dim>=value`, `dim<=value`, `dim!=value`, `dim~text` (contains). Add `--show-sql` to see the generated SQL.

## The three tools the agent gets

| Tool | Use it for | Example call |
|---|---|---|
| `describe_semantic_model` | Discover measures and dimensions (the agent should call this when unsure) | `{}` |
| `query_metrics` | Aggregates and trends | `{"measures":["defect_rate_ppm"],"dimensions":["week_start"],"filters":[{"dimension":"part_number","op":"eq","value":"HX-220"}]}` |
| `lookup_records` | Raw entity rows: a customer, an order line, a lot, a promotion | `{"entity":"supplier_lots","filters":{"lot_id":["ALV-2611","ALV-2612"]}}` |

`agent_app.py` registers these as **function tools** on your Foundry agent and runs them when the agent calls them.

## How cross-fact measures behave (important for correct answers)

A measure belongs to one fact table. When a filter or dimension doesn't apply to a measure's table, the engine **ignores it for that measure** and says so in `notes`. Example: `defect_rate_ppm` by `defect_code`. The numerator (`defect_qty`) is split by defect code; the denominator (`units_produced`) is total production for the slice. That is the correct PPM definition, and the note makes the behaviour transparent.

## Extending the model (Day 2 challenge)

Add a measure:

```yaml
measures:
  # simple aggregate on one fact table
  rework_qty: {table: defects, expr: "SUM(defects.rework_qty)", unit: units, description: "Defective units reworked."}
  # derived from other measures (only + - * / and parentheses)
  scrap_share_pct:
    derived: "scrap_qty * 100 / defect_qty"
    depends_on: [scrap_qty, defect_qty]
    unit: "%"
    description: "Share of defective units that were scrapped."
```

Add a dimension:

```yaml
dimensions:
  lot_h2_status:
    table: supplier_lots
    expr: "CASE WHEN supplier_lots.hydrogen_ml_per_100g > 0.15 THEN 'out-of-spec' ELSE 'in-spec' END"
    description: "Whether the material lot's hydrogen exceeds the A356 spec limit (0.15 ml/100 g)."
```

Rules:

- Measure `expr` must be an aggregate (`SUM`, `COUNT`, `AVG`, `MAX`...). It may reference columns of tables reachable from its fact table; joins are added automatically.
- Write **good descriptions**. The agent reads them through `describe_semantic_model` and the tool schema. Vague descriptions cause wrong tool calls.
- After editing, re-run the CLI to test, then `agent_app.py deploy` (the tool schema lists measure names, so the agent needs a new version).

## Talking about it on Day 4

- Explain that the definitions are **governed** and the agent can't invent a formula.
- Show the `semantic://` citation in an answer and the matching SQL (`--show-sql`).
- Explain the swap to Fabric IQ: the YAML maps to a Fabric semantic model or ontology, and the tools map to a Fabric data agent (Foundry has a Fabric data agent tool) or a Fabric Ontology knowledge source in Foundry IQ.
