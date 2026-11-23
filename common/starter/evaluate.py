"""
Evaluate a batch run of your agent.

  python common/starter/evaluate.py runs/manufacturing-20261124-101500.jsonl          # local checks
  python common/starter/evaluate.py runs/manufacturing-20261124-101500.jsonl --cloud  # + Foundry evaluation

Local checks (deterministic, free):
  * fact_recall   - share of `must_include` facts present in the answer
  * forbidden     - any `must_not_include` text present (e.g. a superseded SOP value)
  * source_hit    - expected sources used: semantic:* -> a function tool was called;
                    document ids -> appear in the answer or its citations; web:* -> a URL citation
  * refusal       - out-of-scope questions should be declined, not answered
Cloud evaluation (Foundry, LLM-judged, uses your model deployment):
  * groundedness, relevance, task adherence ... on the stored responses, visible in the
    Foundry portal under Evaluations.

Writes a Markdown report next to the run file - attach it to your Day 3 submission.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# Windows consoles default to a legacy code page; answers contain characters such as 【】 and en dashes.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REFUSAL_PATTERNS = re.compile(
    r"(don't know|do not know|not available|no information|unable to|can't|cannot|not able to|outside (of )?(my|the) scope|not in (the|my) (sources|knowledge))",
    re.I,
)


def _norm(text: str) -> str:
    return re.sub(r"(?<=\d),(?=\d)", "", (text or "")).lower()


def local_eval(row: dict) -> dict:
    answer = _norm(row.get("answer", ""))
    haystack = answer + " " + _norm(" ".join(row.get("citations", [])))
    must = row.get("must_include", [])
    hits = [m for m in must if _norm(m) in answer]
    forbidden = [m for m in row.get("must_not_include", []) if _norm(m) in answer]
    used_fns = {c["name"] for c in row.get("semantic_calls", [])}
    src_results = []
    for s in row.get("expected_sources", []):
        if s.startswith("semantic:"):
            src_results.append(bool(used_fns & {"query_metrics", "lookup_records"}))
        elif s.startswith("web:"):
            src_results.append(s[4:].lower() in haystack or "http" in haystack)
        else:
            src_results.append(_norm(s.split(" ")[0]) in haystack or (row.get("kb_calls", 0) > 0 and _norm(s.split("_")[0]) in haystack))
    refused = bool(REFUSAL_PATTERNS.search(row.get("answer", "")))
    return {
        "fact_recall": round(len(hits) / len(must), 2) if must else None,
        "missing_facts": [m for m in must if m not in hits],
        "forbidden": forbidden,
        "source_hit": round(sum(src_results) / len(src_results), 2) if src_results else None,
        "refusal_ok": refused if row.get("expect_refusal") else None,
        "error": row.get("error"),
    }


def cloud_eval(rows: list[dict], model: str) -> str | None:
    """Run Foundry built-in evaluators over the stored agent responses (by response id)."""
    from azure.ai.projects import AIProjectClient
    from azure.ai.projects.models import TestingCriterionAzureAIEvaluator
    from azure.identity import DefaultAzureCredential
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    ids = [r["response_id"] for r in rows if r.get("response_id")]
    if not ids:
        print("No response ids in this run - nothing to evaluate in the cloud.")
        return None
    project = AIProjectClient(endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"], credential=DefaultAzureCredential())
    openai = project.get_openai_client()
    criteria = [
        TestingCriterionAzureAIEvaluator(type="azure_ai_evaluator", name=n, evaluator_name=f"builtin.{n}",
                                         initialization_parameters={"deployment_name": model, "model": model})
        for n in ("groundedness", "relevance", "coherence", "task_adherence")
    ]
    ev = openai.evals.create(name=f"capstone-{rows[0].get('agent_name', 'agent')}",
                             data_source_config={"type": "azure_ai_source", "scenario": "responses"},
                             testing_criteria=criteria)
    run = openai.evals.runs.create(
        eval_id=ev.id,
        name=f"run-{time.strftime('%Y%m%d-%H%M%S')}",
        data_source={
            "type": "azure_ai_responses",
            "item_generation_params": {
                "type": "response_retrieval",
                "data_mapping": {"response_id": "{{item.resp_id}}"},
                "source": {"type": "file_content", "content": [{"item": {"resp_id": i}} for i in ids]},
            },
        },
    )
    print(f"Cloud evaluation started: eval {ev.id} run {run.id}. Waiting (this can take a few minutes)...")
    for _ in range(90):
        run = openai.evals.runs.retrieve(run_id=run.id, eval_id=ev.id)
        if run.status in ("completed", "failed", "canceled"):
            break
        time.sleep(10)
    print(f"Status: {run.status}")
    lines = [f"\n## Foundry cloud evaluation\n\nEval `{ev.id}`, run `{run.id}`, status **{run.status}**.",
             f"Report: {getattr(run, 'report_url', '(open Foundry portal -> Evaluations)')}\n"]
    if getattr(run, "result_counts", None):
        lines.append(f"Result counts: {run.result_counts}\n")
    if getattr(run, "per_testing_criteria_results", None):
        lines.append("| Evaluator | Passed | Failed |\n|---|---|---|")
        for r in run.per_testing_criteria_results:
            lines.append(f"| {r.testing_criteria} | {r.passed} | {r.failed} |")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run_file")
    p.add_argument("--cloud", action="store_true", help="Also run Foundry built-in evaluators")
    p.add_argument("--model", default=os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5-mini"), help="Judge model deployment")
    a = p.parse_args()

    run_path = Path(a.run_file)
    rows = [json.loads(l) for l in run_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    results = [(r, local_eval(r)) for r in rows]

    def avg(key):
        vals = [e[key] for _, e in results if e[key] is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    refusals = [e["refusal_ok"] for _, e in results if e["refusal_ok"] is not None]
    md = [f"# Evaluation report - {run_path.name}", "",
          f"Agent: `{rows[0].get('agent_name', '?')}`  |  Questions: {len(rows)}", "",
          "| Metric | Score |", "|---|---|",
          f"| Fact recall (avg) | {avg('fact_recall')} |",
          f"| Expected-source hit rate (avg) | {avg('source_hit')} |",
          f"| Correct refusals | {sum(refusals)}/{len(refusals)} |",
          f"| Answers with forbidden content | {sum(1 for _, e in results if e['forbidden'])} |",
          f"| Errors | {sum(1 for _, e in results if e['error'])} |",
          f"| Avg latency (s) | {round(sum(r.get('latency_s', 0) for r in rows) / len(rows), 1)} |", "",
          "| ID | Category | Fact recall | Source hit | Refusal | Missing facts | Semantic calls | Foundry IQ calls |",
          "|---|---|---|---|---|---|---|---|"]
    for r, e in results:
        md.append(f"| {r['id']} | {r.get('category', '')} | {e['fact_recall']} | {e['source_hit']} | {e['refusal_ok']} | "
                  f"{', '.join(e['missing_facts']) or '-'} | {len(r.get('semantic_calls', []))} | {r.get('kb_calls', 0)} |")
    md += ["", "## Answers", ""]
    for r, e in results:
        md += [f"### {r['id']} - {r['question']}", "", r.get("answer") or f"_error: {r.get('error')}_", "",
               f"_Citations:_ {'; '.join(r.get('citations', [])) or 'none'}", ""]
    if a.cloud:
        section = cloud_eval(rows, a.model)
        if section:
            md.append(section)
    out = run_path.with_suffix(".eval.md")
    out.write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md[:12]))
    print(f"\nFull report: {out}")


if __name__ == "__main__":
    main()
