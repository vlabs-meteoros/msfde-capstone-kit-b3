"""
Semantic layer.

Gives an agent *business meaning* on top of raw tables: named entities,
relationships, dimensions and governed measures (for example "defect rate
in PPM" always means the same calculation). It consists of:

  * semantic_model.yaml  - declares tables, relationships, dimensions, measures
  * CSV files            - the data (loaded into an in-memory SQLite database)
  * three agent tools    - describe_semantic_model, query_metrics, lookup_records

The agent never writes SQL. It asks for measures by name, sliced by dimensions
and filtered by dimension values. The engine builds safe, parameterised SQL,
avoids fan-out when measures come from different fact tables, and returns a
`citation` you can show to the user.

Only the Python standard library and PyYAML are required.
"""
from __future__ import annotations

import ast
import csv
import json
import operator
import re
import sqlite3
from collections import deque
from pathlib import Path
from typing import Any

import yaml

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FILTER_OPS = {
    "eq": "=",
    "neq": "!=",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
    "in": "IN",
    "between": "BETWEEN",
    "contains": "LIKE",
}
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


class SemanticLayerError(ValueError):
    """Raised for invalid requests. The message is safe to return to the agent."""


def _coerce(value: str) -> Any:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _safe_eval(expr: str, env: dict[str, float | None]) -> float | None:
    """Evaluate a derived-measure expression: numbers, names, + - * / and parentheses."""

    def _eval(node: ast.AST) -> float | None:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id not in env:
                raise SemanticLayerError(f"Unknown measure '{node.id}' in derived expression")
            return env[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            left, right = _eval(node.left), _eval(node.right)
            if left is None or right is None:
                return None
            if isinstance(node.op, ast.Div) and right == 0:
                return None
            return _BIN_OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            v = _eval(node.operand)
            return None if v is None else -v
        raise SemanticLayerError(f"Unsupported syntax in derived expression: {expr}")

    return _eval(ast.parse(expr, mode="eval"))


class SemanticModel:
    def __init__(self, model_path: str | Path):
        self.path = Path(model_path)
        with open(self.path, encoding="utf-8") as fh:
            self.spec = yaml.safe_load(fh)
        self.name: str = self.spec["name"]
        self.tables: dict[str, dict] = self.spec["tables"]
        self.dimensions: dict[str, dict] = self.spec.get("dimensions", {})
        self.measures: dict[str, dict] = self.spec.get("measures", {})
        self.relationships: list[dict] = self.spec.get("relationships", [])
        self._validate()
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._columns: dict[str, list[str]] = {}
        self._load_tables()

    # ------------------------------------------------------------------ setup
    def _validate(self) -> None:
        for t in self.tables:
            if not _IDENT.match(t):
                raise SemanticLayerError(f"Invalid table name {t}")
        for name, m in self.measures.items():
            if not _IDENT.match(name):
                raise SemanticLayerError(f"Invalid measure name {name}")
            if "derived" not in m and m.get("table") not in self.tables:
                raise SemanticLayerError(f"Measure {name} references unknown table {m.get('table')}")
        for name, d in self.dimensions.items():
            if d.get("table") not in self.tables:
                raise SemanticLayerError(f"Dimension {name} references unknown table {d.get('table')}")
        for r in self.relationships:
            if True in r:  # YAML 1.1 reads an unquoted `on:` key as boolean True
                r["on"] = r.pop(True)
            if r["from"] not in self.tables or r["to"] not in self.tables:
                raise SemanticLayerError(f"Relationship references unknown table: {r}")

    def _load_tables(self) -> None:
        base = self.path.parent
        for tname, tdef in self.tables.items():
            with open(base / tdef["file"], encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                cols = reader.fieldnames or []
                for c in cols:
                    if not _IDENT.match(c):
                        raise SemanticLayerError(f"Invalid column name {c} in {tdef['file']}")
                rows = [[_coerce(r[c]) for c in cols] for r in reader]
            self._columns[tname] = cols
            self.db.execute(f'CREATE TABLE "{tname}" ({", ".join(cols)})')
            self.db.executemany(
                f'INSERT INTO "{tname}" VALUES ({", ".join("?" for _ in cols)})', rows
            )
        self.db.commit()

    # --------------------------------------------------------------- helpers
    def _join_path(self, start: str, target: str) -> list[dict]:
        """Shortest many-to-one path from a fact table to the table holding a dimension."""
        if start == target:
            return []
        queue: deque[tuple[str, list[dict]]] = deque([(start, [])])
        seen = {start}
        while queue:
            node, path = queue.popleft()
            for rel in self.relationships:
                if rel["from"] == node and rel["to"] not in seen:
                    new_path = path + [rel]
                    if rel["to"] == target:
                        return new_path
                    seen.add(rel["to"])
                    queue.append((rel["to"], new_path))
        raise SemanticLayerError(f"No relationship path from '{start}' to '{target}'")

    def _try_path(self, start: str, target: str) -> list[dict] | None:
        try:
            return self._join_path(start, target)
        except SemanticLayerError:
            return None

    def _base_measures(self, names: list[str]) -> list[str]:
        out: list[str] = []

        def visit(n: str, depth: int = 0) -> None:
            if depth > 10:
                raise SemanticLayerError("Derived measure nesting too deep")
            if n not in self.measures:
                raise SemanticLayerError(
                    f"Unknown measure '{n}'. Available: {', '.join(sorted(self.measures))}"
                )
            m = self.measures[n]
            if "derived" in m:
                for dep in m.get("depends_on", []):
                    visit(dep, depth + 1)
            elif n not in out:
                out.append(n)

        for n in names:
            visit(n)
        return out

    def _compute_derived(self, name: str, values: dict[str, Any], depth: int = 0) -> Any:
        m = self.measures[name]
        if "derived" not in m:
            return values.get(name)
        env = {d: self._compute_derived(d, values, depth + 1) for d in m.get("depends_on", [])}
        return _safe_eval(m["derived"], env)

    # ----------------------------------------------------------------- tools
    def describe(self) -> dict:
        return {
            "model": self.name,
            "description": self.spec.get("description", ""),
            "measures": {
                n: {
                    "description": m.get("description", ""),
                    "unit": m.get("unit", ""),
                    **({"formula": m["derived"]} if "derived" in m else {}),
                }
                for n, m in self.measures.items()
            },
            "dimensions": {
                n: {
                    "description": d.get("description", ""),
                    **({"examples": d["examples"]} if "examples" in d else {}),
                }
                for n, d in self.dimensions.items()
            },
            "entities": {
                t: {
                    "description": d.get("description", ""),
                    "key": d.get("primary_key"),
                    "columns": self._columns[t],
                }
                for t, d in self.tables.items()
                if d.get("lookup", True)
            },
            "filter_operators": list(_FILTER_OPS),
            "notes": self.spec.get("notes", []),
        }

    def query_metrics(
        self,
        measures: list[str],
        dimensions: list[str] | None = None,
        filters: list[dict] | None = None,
        order_by: str | None = None,
        descending: bool = True,
        limit: int = 50,
    ) -> dict:
        if not measures:
            raise SemanticLayerError("Provide at least one measure")
        dimensions = dimensions or []
        filters = filters or []
        limit = max(1, min(int(limit or 50), 500))
        for d in dimensions:
            if d not in self.dimensions:
                raise SemanticLayerError(
                    f"Unknown dimension '{d}'. Available: {', '.join(sorted(self.dimensions))}"
                )
        for f in filters:
            if f.get("dimension") not in self.dimensions:
                raise SemanticLayerError(f"Unknown filter dimension '{f.get('dimension')}'")
            if f.get("op", "eq") not in _FILTER_OPS:
                raise SemanticLayerError(f"Unknown filter op '{f.get('op')}'")

        base = self._base_measures(measures)
        by_fact: dict[str, list[str]] = {}
        for b in base:
            by_fact.setdefault(self.measures[b]["table"], []).append(b)

        sql_log: list[str] = []
        notes: list[str] = []
        per_fact: list[tuple[list[str], dict[tuple, dict[str, Any]]]] = []
        for fact, fact_measures in by_fact.items():
            # A dimension or filter only applies to a fact if a relationship path exists.
            # Otherwise it is ignored for that fact (e.g. units_produced is not filtered by
            # defect_code, so defect_rate_ppm for one defect code uses all units produced).
            fact_dims, joins = [], []
            # tables referenced inside measure expressions (e.g. parts.unit_cost_usd)
            for m in fact_measures:
                for tbl in set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\.[A-Za-z_]", self.measures[m]["expr"])):
                    if tbl != fact and tbl in self.tables:
                        joins += [r for r in self._join_path(fact, tbl) if r not in joins]
            for d in dimensions:
                path = self._try_path(fact, self.dimensions[d]["table"])
                if path is None:
                    notes.append(f"Dimension '{d}' does not apply to {', '.join(fact_measures)}; values repeated across it.")
                    continue
                fact_dims.append(d)
                joins += [r for r in path if r not in joins]
            fact_filters = []
            for f in filters:
                path = self._try_path(fact, self.dimensions[f["dimension"]]["table"])
                if path is None:
                    notes.append(f"Filter on '{f['dimension']}' does not apply to {', '.join(fact_measures)}; ignored for it.")
                    continue
                fact_filters.append(f)
                joins += [r for r in path if r not in joins]
            join_sql = "".join(f' LEFT JOIN "{r["to"]}" ON {r["on"]}' for r in joins)
            dim_sql = [f'{self.dimensions[d]["expr"]} AS "{d}"' for d in fact_dims]
            mea_sql = [f'{self.measures[m]["expr"]} AS "{m}"' for m in fact_measures]
            where, params = [], []
            for f in fact_filters:
                expr = self.dimensions[f["dimension"]]["expr"]
                op = f.get("op", "eq")
                val = f.get("value")
                if op == "in":
                    vals = val if isinstance(val, list) else [val]
                    vals = [_coerce(v) if isinstance(v, str) else v for v in vals]
                    where.append(f"{expr} IN ({', '.join('?' for _ in vals)})")
                    params += vals
                elif op == "between":
                    if not isinstance(val, list) or len(val) != 2:
                        raise SemanticLayerError("'between' needs a two-item list value")
                    where.append(f"{expr} BETWEEN ? AND ?")
                    params += [_coerce(v) if isinstance(v, str) else v for v in val]
                elif op == "contains":
                    where.append(f"LOWER({expr}) LIKE ?")
                    params.append(f"%{str(val).lower()}%")
                else:
                    where.append(f"{expr} {_FILTER_OPS[op]} ?")
                    params.append(_coerce(val) if isinstance(val, str) else val)
            fact_filter = self.tables[fact].get("filter")
            if fact_filter:
                where.append(fact_filter)
            sql = f'SELECT {", ".join(dim_sql + mea_sql)} FROM "{fact}"{join_sql}'
            if where:
                sql += " WHERE " + " AND ".join(where)
            if fact_dims:
                sql += " GROUP BY " + ", ".join(str(i + 1) for i in range(len(fact_dims)))
            sql_log.append(sql)
            result = {}
            for row in self.db.execute(sql, params).fetchall():
                result[tuple(row[d] for d in fact_dims)] = {m: row[m] for m in fact_measures}
            per_fact.append((fact_dims, result))

        full = [res for fd, res in per_fact if len(fd) == len(dimensions)]
        if not full:
            raise SemanticLayerError(
                "No single measure in this request supports all requested dimensions together; "
                "split the request into separate queries."
            )
        keys: list[tuple] = []
        for res in full:
            keys += [k for k in res if k not in keys]
        rows = []
        for key in keys:
            vals: dict[str, Any] = dict(zip(dimensions, key))
            for fact_dims, res in per_fact:
                proj = tuple(key[dimensions.index(d)] for d in fact_dims)
                vals.update(res.get(proj, {}))
            out = {d: vals.get(d) for d in dimensions}
            for m in measures:
                v = self._compute_derived(m, vals)
                out[m] = round(v, 4) if isinstance(v, float) else v
            rows.append(out)

        sort_key = order_by if order_by in measures + dimensions else (measures[0] if measures else None)
        if sort_key:
            present = [r for r in rows if r.get(sort_key) is not None]
            missing = [r for r in rows if r.get(sort_key) is None]
            present.sort(key=lambda r: r[sort_key], reverse=bool(descending))
            rows = present + missing
        truncated = len(rows) > limit
        rows = rows[:limit]

        filt = "&".join(
            f'{f["dimension"]}{"" if f.get("op", "eq") == "eq" else ":" + f["op"]}={json.dumps(f.get("value"))}'
            for f in filters
        )
        return {
            "rows": rows,
            "row_count": len(rows),
            "truncated": truncated,
            "measure_definitions": {
                m: self.measures[m].get("description", "") for m in measures
            },
            "citation": f"semantic://{self.name}/{'+'.join(measures)}"
            + (f"?by={','.join(dimensions)}" if dimensions else "")
            + (("&" if dimensions else "?") + filt if filt else ""),
            "notes": sorted(set(notes)),
            "sql": sql_log,
        }

    def lookup_records(self, entity: str, filters: dict | None = None, limit: int = 20) -> dict:
        if entity not in self.tables or not self.tables[entity].get("lookup", True):
            raise SemanticLayerError(
                f"Unknown entity '{entity}'. Available: "
                + ", ".join(t for t, d in self.tables.items() if d.get("lookup", True))
            )
        filters = filters or {}
        cols = self._columns[entity]
        where, params = [], []
        for col, val in filters.items():
            if col not in cols:
                raise SemanticLayerError(f"Unknown column '{col}' on {entity}. Columns: {', '.join(cols)}")
            vals = val if isinstance(val, list) else [val]
            vals = [_coerce(v) if isinstance(v, str) else v for v in vals]
            where.append(f'"{col}" IN ({", ".join("?" for _ in vals)})')
            params += vals
        limit = max(1, min(int(limit or 20), 200))
        sql = f'SELECT * FROM "{entity}"' + (" WHERE " + " AND ".join(where) if where else "")
        sql += f" LIMIT {limit + 1}"
        rows = [dict(r) for r in self.db.execute(sql, params).fetchall()]
        key = self.tables[entity].get("primary_key", "")
        return {
            "entity": entity,
            "rows": rows[:limit],
            "row_count": min(len(rows), limit),
            "truncated": len(rows) > limit,
            "citation": f"semantic://{self.name}/{entity}"
            + ("?" + "&".join(f"{k}={v}" for k, v in filters.items()) if filters else ""),
            "primary_key": key,
        }

    # ----------------------------------------------------- agent integration
    def tool_definitions(self) -> list[dict]:
        """JSON-schema function definitions to register on a Foundry agent."""
        measure_names = sorted(self.measures)
        dim_names = sorted(self.dimensions)
        entities = sorted(t for t, d in self.tables.items() if d.get("lookup", True))
        return [
            {
                "name": "describe_semantic_model",
                "description": (
                    f"Describe the '{self.name}' semantic model: available business measures "
                    "(with definitions), dimensions, entities and filter operators. Call this "
                    "first if you are unsure which measure or dimension to use."
                ),
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
            {
                "name": "query_metrics",
                "description": (
                    "Compute governed business measures from structured data, optionally grouped "
                    "by dimensions and filtered by dimension values. Always prefer this over "
                    "estimating numbers. Returns rows plus a citation string to quote."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "measures": {
                            "type": "array",
                            "items": {"type": "string", "enum": measure_names},
                            "description": "One or more measure names.",
                        },
                        "dimensions": {
                            "type": "array",
                            "items": {"type": "string", "enum": dim_names},
                            "description": "Dimensions to group by. Empty for a grand total.",
                        },
                        "filters": {
                            "type": "array",
                            "description": "Filters on dimension values.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "dimension": {"type": "string", "enum": dim_names},
                                    "op": {"type": "string", "enum": list(_FILTER_OPS)},
                                    "value": {
                                        "description": "Scalar, or list for 'in'/'between'.",
                                        "anyOf": [
                                            {"type": "string"},
                                            {"type": "number"},
                                            {"type": "array", "items": {"type": ["string", "number"]}},
                                        ],
                                    },
                                },
                                "required": ["dimension", "op", "value"],
                            },
                        },
                        "order_by": {"type": "string", "description": "Measure or dimension to sort by."},
                        "descending": {"type": "boolean"},
                        "limit": {"type": "integer", "description": "Max rows (default 50)."},
                    },
                    "required": ["measures"],
                },
            },
            {
                "name": "lookup_records",
                "description": (
                    "Fetch raw records for a business entity by exact column values, e.g. a "
                    "customer profile, an order, a supplier lot or a promotion. Returns a citation."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity": {"type": "string", "enum": entities},
                        "filters": {
                            "type": "object",
                            "description": "Column -> value (or list of values) exact-match filters.",
                            "additionalProperties": True,
                        },
                        "limit": {"type": "integer"},
                    },
                    "required": ["entity"],
                },
            },
        ]

    def call_tool(self, name: str, arguments: dict | str) -> str:
        """Dispatch a tool call from the agent. Always returns a JSON string (errors included)."""
        if isinstance(arguments, str):
            arguments = json.loads(arguments or "{}")
        try:
            if name == "describe_semantic_model":
                result = self.describe()
            elif name == "query_metrics":
                result = self.query_metrics(**arguments)
            elif name == "lookup_records":
                result = self.lookup_records(**arguments)
            else:
                raise SemanticLayerError(f"Unknown tool {name}")
        except (SemanticLayerError, TypeError, sqlite3.Error) as exc:
            result = {"error": str(exc)}
        return json.dumps(result, default=str)
