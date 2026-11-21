"""
Capstone agent runner - deploys and talks to YOUR Foundry agent.

  python common/starter/agent_app.py doctor  --usecase manufacturing   # check environment
  python common/starter/agent_app.py deploy  --usecase manufacturing   # create a new agent version
  python common/starter/agent_app.py chat    --usecase manufacturing   # interactive chat
  python common/starter/agent_app.py ask     --usecase manufacturing "question"
  python common/starter/agent_app.py batch   --usecase manufacturing   # run eval/test-questions.jsonl

What lives where
  * The AGENT (model, instructions, tools) lives in Azure AI Foundry Agent Service. `deploy`
    creates a new version from usecases/<uc>/agent/instructions.md - you can inspect, test and
    trace it in the Foundry portal.
  * Foundry IQ (document / web grounding) is attached as an MCP tool pointing at your knowledge
    base. Retrieval runs server-side; you write no RAG code.
  * The local semantic layer (Fabric IQ stand-in) is attached as three FUNCTION tools. Function
    tools execute on the client, which is why chat/batch run here: when the agent asks for
    query_metrics, this script runs it against the CSVs and returns the JSON result.

Settings are read from the .env file in the repo root (copy .env.sample).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from common.semantic_layer import SemanticModel  # noqa: E402

load_dotenv(ROOT / ".env")

KB_API_VERSION = os.getenv("KB_API_VERSION", "2026-11-01-preview")
MAX_TOOL_ROUNDS = 8


# --------------------------------------------------------------------------- config
def cfg(usecase: str) -> dict:
    alias = os.getenv("PARTICIPANT_ALIAS", "me").lower().replace(" ", "-")
    c = {
        "usecase": usecase,
        "project_endpoint": os.getenv("FOUNDRY_PROJECT_ENDPOINT", ""),
        "model": os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5-mini"),
        "agent_name": os.getenv("AGENT_NAME") or f"{usecase}-agent-{alias}",
        "search_endpoint": os.getenv("SEARCH_ENDPOINT", "").rstrip("/"),
        "kb_name": os.getenv("KNOWLEDGE_BASE_NAME", ""),
        "kb_connection": os.getenv("KB_CONNECTION_NAME", ""),
        "uc_dir": ROOT / "usecases" / usecase,
    }
    c["semantic_model"] = c["uc_dir"] / "data" / "semantic" / "semantic_model.yaml"
    c["instructions"] = c["uc_dir"] / "agent" / "instructions.md"
    if c["search_endpoint"] and c["kb_name"]:
        c["kb_mcp_url"] = f"{c['search_endpoint']}/knowledgebases/{c['kb_name']}/mcp?api-version={KB_API_VERSION}"
    else:
        c["kb_mcp_url"] = ""
    return c


def clients(c: dict):
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    if not c["project_endpoint"]:
        sys.exit("FOUNDRY_PROJECT_ENDPOINT is not set - copy .env.sample to .env and fill it in.")
    cred = DefaultAzureCredential()
    project = AIProjectClient(endpoint=c["project_endpoint"], credential=cred)
    return cred, project, project.get_openai_client()


# --------------------------------------------------------------------------- deploy
def build_tools(c: dict, semantic: SemanticModel) -> list:
    from azure.ai.projects.models import FunctionTool, MCPTool

    tools = []
    if c["kb_mcp_url"] and c["kb_connection"]:
        tools.append(MCPTool(
            server_label="knowledge-base",
            server_url=c["kb_mcp_url"],
            require_approval="never",
            allowed_tools=["knowledge_base_retrieve"],
            project_connection_id=c["kb_connection"],
        ))
    else:
        print("WARNING: SEARCH_ENDPOINT / KNOWLEDGE_BASE_NAME / KB_CONNECTION_NAME not set - "
              "deploying WITHOUT Foundry IQ grounding.")
    for t in semantic.tool_definitions():
        tools.append(FunctionTool(name=t["name"], description=t["description"], parameters=t["parameters"], strict=False))
    return tools


def deploy(c: dict) -> None:
    from azure.ai.projects.models import PromptAgentDefinition

    instructions = c["instructions"].read_text(encoding="utf-8")
    semantic = SemanticModel(c["semantic_model"])
    _, project, _ = clients(c)
    agent = project.agents.create_version(
        agent_name=c["agent_name"],
        definition=PromptAgentDefinition(model=c["model"], instructions=instructions, tools=build_tools(c, semantic)),
        description=f"Capstone {c['usecase']} agent ({os.getenv('PARTICIPANT_ALIAS', 'participant')})",
    )
    print(f"Deployed agent '{agent.name}' version {agent.version} on model {c['model']}")
    print("Open the Foundry portal -> Agents to inspect it. Run `chat` to talk to it.")


# --------------------------------------------------------------------------- run
def _annotations(response) -> list[str]:
    cites = []
    for item in response.output:
        if getattr(item, "type", "") == "message":
            for block in item.content:
                for a in getattr(block, "annotations", None) or []:
                    label = getattr(a, "title", None) or getattr(a, "url", None) or getattr(a, "filename", None) or str(a)
                    if label not in cites:
                        cites.append(label)
    return cites


def run_turn(openai, c: dict, semantic: SemanticModel, conversation_id: str, user_input: str, verbose: bool = True) -> dict:
    """Send one user message; keep answering function calls until the agent produces a final message."""
    agent_ref = {"agent_reference": {"name": c["agent_name"], "type": "agent_reference"}}
    t0 = time.time()
    response = openai.responses.create(conversation=conversation_id, input=user_input, extra_body=agent_ref)
    response_ids, tool_calls, kb_calls = [response.id], [], 0
    for _ in range(MAX_TOOL_ROUNDS):
        outputs = []
        for item in response.output:
            itype = getattr(item, "type", "")
            if itype == "function_call":
                result = semantic.call_tool(item.name, item.arguments)
                tool_calls.append({"name": item.name, "arguments": json.loads(item.arguments or "{}"),
                                   "citation": json.loads(result).get("citation"), "error": json.loads(result).get("error")})
                if verbose:
                    print(f"  [semantic] {item.name}({item.arguments})")
                outputs.append({"type": "function_call_output", "call_id": item.call_id, "output": result})
            elif itype in ("mcp_call", "mcp_tool_call"):
                kb_calls += 1
                if verbose:
                    print(f"  [foundry-iq] {getattr(item, 'name', 'knowledge_base_retrieve')}")
        if not outputs:
            break
        response = openai.responses.create(conversation=conversation_id, input=outputs, extra_body=agent_ref)
        response_ids.append(response.id)
    return {
        "answer": response.output_text,
        "citations": _annotations(response),
        "response_id": response.id,
        "response_ids": response_ids,
        "semantic_calls": tool_calls,
        "kb_calls": kb_calls,
        "latency_s": round(time.time() - t0, 2),
    }


def chat(c: dict) -> None:
    semantic = SemanticModel(c["semantic_model"])
    _, _, openai = clients(c)
    conv = openai.conversations.create()
    print(f"Chatting with '{c['agent_name']}'. Type 'exit' to quit, 'new' for a new conversation.\n")
    while True:
        try:
            q = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in ("exit", "quit"):
            break
        if q.lower() == "new":
            conv = openai.conversations.create()
            print("(new conversation)")
            continue
        if not q:
            continue
        r = run_turn(openai, c, semantic, conv.id, q)
        print(f"\nagent> {r['answer']}\n")
        if r["citations"]:
            print("  citations: " + "; ".join(r["citations"]))
        print(f"  ({r['latency_s']} s, {r['kb_calls']} Foundry IQ calls, {len(r['semantic_calls'])} semantic calls, response {r['response_id']})\n")


def ask(c: dict, question: str) -> None:
    semantic = SemanticModel(c["semantic_model"])
    _, _, openai = clients(c)
    conv = openai.conversations.create()
    r = run_turn(openai, c, semantic, conv.id, question)
    print(json.dumps(r, indent=2, default=str))


def batch(c: dict, questions: Path, out: Path) -> None:
    semantic = SemanticModel(c["semantic_model"])
    _, _, openai = clients(c)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(line) for line in questions.read_text(encoding="utf-8").splitlines() if line.strip()]
    with open(out, "w", encoding="utf-8") as fh:
        for q in rows:
            print(f"{q['id']}: {q['question'][:90]}")
            conv = openai.conversations.create()
            try:
                r = run_turn(openai, c, semantic, conv.id, q["question"], verbose=False)
            except Exception as exc:  # keep going - a failed question is evaluation evidence too
                r = {"answer": "", "error": str(exc), "citations": [], "semantic_calls": [], "kb_calls": 0, "response_id": None, "response_ids": []}
            fh.write(json.dumps({**q, **r, "agent_name": c["agent_name"], "conversation_id": conv.id}, default=str) + "\n")
    print(f"\nSaved {len(rows)} results to {out}. Next: python common/starter/evaluate.py {out}")


# --------------------------------------------------------------------------- doctor
def doctor(c: dict) -> None:
    ok = True

    def line(flag: bool, msg: str):
        nonlocal ok
        ok &= flag
        print(("  OK   " if flag else "  FAIL ") + msg)

    print(f"Use case: {c['usecase']}   agent name: {c['agent_name']}")
    for k in ("project_endpoint", "model", "search_endpoint", "kb_name", "kb_connection"):
        line(bool(c[k]), f"{k} = {c[k] or '(not set)'}")
    line(c["instructions"].exists(), f"instructions file {c['instructions'].relative_to(ROOT)}")
    try:
        sm = SemanticModel(c["semantic_model"])
        line(True, f"semantic model '{sm.name}' loaded ({len(sm.measures)} measures, {len(sm.dimensions)} dimensions)")
    except Exception as exc:
        line(False, f"semantic model failed to load: {exc}")
    try:
        cred, project, _ = clients(c)
        deps = [d.name for d in project.deployments.list()]
        line(c["model"] in deps, f"model deployment '{c['model']}' found in project (have: {', '.join(deps) or 'none'})")
    except Exception as exc:
        line(False, f"cannot reach Foundry project: {exc}")
        cred = None
    if cred and c["search_endpoint"] and c["kb_name"]:
        try:
            import requests

            tok = cred.get_token("https://search.azure.com/.default").token
            r = requests.get(f"{c['search_endpoint']}/knowledgebases/{c['kb_name']}?api-version={KB_API_VERSION}",
                             headers={"Authorization": f"Bearer {tok}"}, timeout=20)
            line(r.status_code == 200, f"knowledge base '{c['kb_name']}' reachable (HTTP {r.status_code})")
        except Exception as exc:
            line(False, f"knowledge base check failed: {exc}")
    print("\nAll good." if ok else "\nFix the FAIL lines above (see common/00-environment-setup.md).")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["doctor", "deploy", "chat", "ask", "batch"])
    p.add_argument("question", nargs="?")
    p.add_argument("--usecase", required=True, choices=["manufacturing", "retail", "fmcg"])
    p.add_argument("--questions", help="JSONL file for batch (default: usecases/<uc>/eval/test-questions.jsonl)")
    p.add_argument("--out", help="Output JSONL for batch (default: runs/<uc>-<timestamp>.jsonl)")
    a = p.parse_intermixed_args()
    c = cfg(a.usecase)
    if a.command == "doctor":
        doctor(c)
    elif a.command == "deploy":
        deploy(c)
    elif a.command == "chat":
        chat(c)
    elif a.command == "ask":
        if not a.question:
            sys.exit('Usage: ask --usecase <uc> "your question"')
        ask(c, a.question)
    else:
        q = Path(a.questions) if a.questions else c["uc_dir"] / "eval" / "test-questions.jsonl"
        out = Path(a.out) if a.out else ROOT / "runs" / f"{a.usecase}-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
        batch(c, q, out)


if __name__ == "__main__":
    main()
