"""
Create the Foundry project connection that lets your agent call your Foundry IQ knowledge base (MCP).

  python common/starter/create_kb_connection.py

Needs in .env: PROJECT_RESOURCE_ID, SEARCH_ENDPOINT, KNOWLEDGE_BASE_NAME, KB_CONNECTION_NAME.
Needs the 'Foundry Project Manager' (formerly Azure AI Project Manager) role on the Foundry resource.

If the portal already created a connection for you when you attached the knowledge base to an agent,
you can reuse that connection name instead and skip this script.
"""
import os
import sys
from pathlib import Path

import requests
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

API_VERSION = "2025-10-01-preview"
KB_API_VERSION = os.getenv("KB_API_VERSION", "2026-11-01-preview")


def main() -> None:
    missing = [k for k in ("PROJECT_RESOURCE_ID", "SEARCH_ENDPOINT", "KNOWLEDGE_BASE_NAME", "KB_CONNECTION_NAME") if not os.getenv(k)]
    if missing:
        sys.exit(f"Set these in .env first: {', '.join(missing)}")
    resource_id = os.environ["PROJECT_RESOURCE_ID"].strip()
    name = os.environ["KB_CONNECTION_NAME"].strip()
    target = f"{os.environ['SEARCH_ENDPOINT'].rstrip('/')}/knowledgebases/{os.environ['KNOWLEDGE_BASE_NAME']}/mcp?api-version={KB_API_VERSION}"

    token = get_bearer_token_provider(DefaultAzureCredential(), "https://management.azure.com/.default")()
    r = requests.put(
        f"https://management.azure.com{resource_id}/connections/{name}?api-version={API_VERSION}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "type": "Microsoft.MachineLearningServices/workspaces/connections",
            "properties": {
                "authType": "ProjectManagedIdentity",
                "category": "RemoteTool",
                "target": target,
                "isSharedToAll": False,
                "audience": "https://search.azure.com/",
                "metadata": {"ApiType": "Azure"},
            },
        },
        timeout=60,
    )
    if r.status_code >= 300:
        sys.exit(f"Failed ({r.status_code}): {r.text}")
    print(f"Connection '{name}' -> {target} created/updated.")
    print("Reminder: the project's managed identity needs 'Search Index Data Reader' on the search service.")


if __name__ == "__main__":
    main()
