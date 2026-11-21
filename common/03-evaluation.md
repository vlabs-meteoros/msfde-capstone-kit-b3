# 03 · Evaluation

"It answered my demo question" isn't evidence. The panel wants to see that you **measured** the agent against a fixed question set, found weaknesses, changed something, and measured again.

## The loop

```
deploy (version N) -> batch run -> evaluate -> read failures -> change prompt / tools / KB -> deploy (N+1) -> repeat
```

Keep every run file and report in `runs/`. **Before/after evidence** between two agent versions is the strongest thing you can show.

## Your evaluation set

`usecases/<uc>/eval/test-questions.jsonl` has 10 questions with:

| Field | Meaning |
|---|---|
| `category` | `document`, `structured`, `combined`, `web` (Retail), `out_of_scope` |
| `ground_truth` | Reference answer written by the business SME |
| `must_include` | Facts or numbers a correct answer must contain |
| `must_not_include` | Content that signals a wrong source (for example a superseded SOP value) |
| `expected_sources` | `semantic:<measure/entity>`, a document id, or `web:<domain>` |
| `expect_refusal` | The agent should decline |

**Challenge:** add at least **5 questions of your own**, including one tricky multi-part question and one adversarial one (prompt injection, a request for PII, a request outside policy). Panel members also bring hidden questions on Day 4.

## Running it

```bash
python common/starter/agent_app.py batch --usecase <uc>                  # writes runs/<uc>-<timestamp>.jsonl
python common/starter/evaluate.py runs/<uc>-<timestamp>.jsonl            # local checks -> .eval.md report
python common/starter/evaluate.py runs/<uc>-<timestamp>.jsonl --cloud    # + Foundry built-in evaluators
```

## Metrics

| Metric | Source | What good looks like |
|---|---|---|
| **Fact recall** | local: `must_include` present | ≥ 0.8 average |
| **Source hit rate** | local: expected tool or document actually used | ≥ 0.8; combined questions must use **both** tool types |
| **Correct refusals** | local | all out-of-scope questions declined |
| **Forbidden content** | local: `must_not_include` | 0 |
| **Groundedness** | Foundry evaluator: is the answer supported by the retrieved context? | majority pass; investigate every fail |
| **Relevance / task adherence** | Foundry evaluators | majority pass |
| **Latency** | batch run | report the average and the slowest question; explain the trade-off with retrieval effort |

The Foundry evaluators run on the stored responses by response ID. Results appear in the Foundry portal under **Evaluations**. Take screenshots for your submission. You can also start an evaluation from the portal on your agent with a dataset uploaded from the JSONL. Either route is fine as long as you have the evidence.

<details><summary>Hint: the cloud evaluation fails or shows no results</summary>

- The judge model is your `MODEL_DEPLOYMENT_NAME`. Pass a different one with `--model` if your deployment has low quota.
- Response-based evaluation needs stored responses (the default). If it still fails, use the portal: **Evaluations → Create → Agent**, pick your agent, upload the questions file, and select Groundedness, Relevance and Task adherence.
- Record the error message in your evaluation notes. A documented limitation is acceptable evidence; silence isn't.
</details>

## Reading failures: a quick diagnosis table

| Symptom in the report | Likely cause | Typical fix |
|---|---|---|
| Missing numbers, no semantic calls | Agent didn't call `query_metrics` | Instructions: "always use query_metrics for any number"; better measure descriptions |
| Wrong number | Wrong filter or dimension, or the agent did arithmetic itself | Add the needed measure to the model instead of letting the model compute; give the date-range convention in instructions |
| Document question answered from general knowledge | No KB call | Instructions: "use the knowledge base for any policy, procedure or contract question"; check the MCP tool is attached |
| Cites a superseded document | Retrieval returns both revisions | Instructions about document status; metadata in the doc title; KB retrieval instructions |
| Answers out-of-scope questions | No refusal rule | Explicit scope and refusal section in instructions |
| Very slow | Many tool rounds, high retrieval effort | Fewer, broader tool calls; `low` effort; smaller output |

## Evaluation evidence for submission (Day 3, mandatory)

1. The final eval report (`.eval.md`) and the earlier one you improved on.
2. Screenshot(s) of the Foundry evaluation results.
3. A short table: *change made → metric before → metric after*.
4. Limitations: questions it still fails and why.
