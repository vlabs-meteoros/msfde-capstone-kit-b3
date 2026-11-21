"""
Command-line access to the local semantic layer, so you can test measures
before the agent uses them.

Examples (run from the repo root):

  python -m common.semantic_layer usecases/manufacturing/data/semantic/semantic_model.yaml describe
  python -m common.semantic_layer usecases/manufacturing/data/semantic/semantic_model.yaml query \
      --measures defect_rate_ppm units_produced --dimensions line --filter "part_number=HX-220"
  python -m common.semantic_layer usecases/retail/data/semantic/semantic_model.yaml lookup customers \
      --filter customer_id=C-10482
"""
import argparse
import json
import sys

from .engine import SemanticModel


def _parse_filter(text: str) -> dict:
    # dimension=value | dimension>=value | dimension<=value | dimension~value (contains)
    for token, op in ((">=", "gte"), ("<=", "lte"), ("!=", "neq"), ("~", "contains"), ("=", "eq")):
        if token in text:
            dim, val = text.split(token, 1)
            if op == "eq" and "," in val:
                return {"dimension": dim.strip(), "op": "in", "value": [v.strip() for v in val.split(",")]}
            return {"dimension": dim.strip(), "op": op, "value": val.strip()}
    raise SystemExit(f"Cannot parse filter: {text}")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="python -m common.semantic_layer")
    p.add_argument("model")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("describe")
    q = sub.add_parser("query")
    q.add_argument("--measures", nargs="+", required=True)
    q.add_argument("--dimensions", nargs="*", default=[])
    q.add_argument("--filter", action="append", default=[])
    q.add_argument("--order-by")
    q.add_argument("--ascending", action="store_true")
    q.add_argument("--limit", type=int, default=50)
    q.add_argument("--show-sql", action="store_true")
    lk = sub.add_parser("lookup")
    lk.add_argument("entity")
    lk.add_argument("--filter", action="append", default=[])
    lk.add_argument("--limit", type=int, default=20)
    a = p.parse_args(argv)

    model = SemanticModel(a.model)
    if a.cmd == "describe":
        out = model.describe()
    elif a.cmd == "query":
        out = model.query_metrics(
            measures=a.measures,
            dimensions=a.dimensions,
            filters=[_parse_filter(f) for f in a.filter],
            order_by=a.order_by,
            descending=not a.ascending,
            limit=a.limit,
        )
        if not a.show_sql:
            out.pop("sql", None)
    else:
        filters = {}
        for f in a.filter:
            k, v = f.split("=", 1)
            filters[k.strip()] = v.strip()
        out = model.lookup_records(a.entity, filters, a.limit)
    json.dump(out, sys.stdout, indent=2, default=str)
    print()


if __name__ == "__main__":
    main()
