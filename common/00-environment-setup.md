# 00 · Environment setup (Day 1)

> **Batch 3:** all the values below (project, endpoints, storage container, roles) are already provisioned and listed in [LAB-ENVIRONMENT.md](LAB-ENVIRONMENT.md). Roles are pre-assigned, so you can skip section 5.

Target: in about 45 minutes you can sign in, reach your Foundry project, and run `agent_app.py doctor` with every line OK except the knowledge base (you create that in the build guide).

## 1. What should already be on your Windows VM

| Tool | Check | If missing |
|---|---|---|
| Python 3.10+ | `python --version` | Install from python.org (tick "Add to PATH") |
| Git | `git --version` | git-scm.com |
| Azure CLI | `az version` | `winget install Microsoft.AzureCLI` |
| VS Code (optional) | | code.visualstudio.com |
| Browser access to `https://ai.azure.com` and `https://portal.azure.com` | | Ask your facilitator |

## 2. What your facilitator provides

Write these down. You need them in `.env`.

| Item | Example | Where it goes |
|---|---|---|
| Azure subscription and resource group | `rg-fde-capstone-b3` | |
| Foundry resource and **your own project** | `fde-b3-foundry` / `proj-<alias>` | `FOUNDRY_PROJECT_ENDPOINT`, `PROJECT_RESOURCE_ID` |
| Model deployment (chat model) | `gpt-5-mini` | `MODEL_DEPLOYMENT_NAME` |
| Azure AI Search service (Foundry IQ), Basic tier or higher, semantic ranker on | `srch-fde-b3` | `SEARCH_ENDPOINT` |
| (Optional) Storage account + container for documents | `stfdeb3` / `docs-<alias>` | used when you create a blob knowledge source |
| (Optional) Embedding deployment | `text-embedding-3-small` | used by the knowledge source wizard |

**Naming rule (shared services):** prefix everything you create with your alias, e.g. `ks-asha-mfg-docs`, `kb-asha-mfg`, `mfg-agent-asha`.

## 3. Sign in and install

```bash
az login                         # use the lab account
az account set --subscription "<subscription name or id>"
git clone <repo-url> && cd msfde-capstone-kit
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.sample .env
```

Fill in `.env`: `PARTICIPANT_ALIAS`, `FOUNDRY_PROJECT_ENDPOINT`, `PROJECT_RESOURCE_ID`, `MODEL_DEPLOYMENT_NAME`, `SEARCH_ENDPOINT`. Leave the knowledge-base fields empty for now.

- **Project endpoint:** Foundry portal → your project → **Overview** → *Project endpoint*.
- **Project resource ID:** Azure portal → the Foundry resource → **Projects** → your project → **JSON View** → `id`. Or run:
  `az resource list -g <rg> --resource-type Microsoft.CognitiveServices/accounts/projects --query "[].id" -o tsv`

## 4. Verify

```bash
python tools/validate_kit.py                                   # data kit, no Azure needed
python common/starter/agent_app.py doctor --usecase <your-usecase>
```

Expected: the project and model-deployment lines are OK. The knowledge-base lines FAIL until Day 1 Challenge 1.4.

## 5. Permissions you need (and who grants them)

Agents only work if the identities can reach each other. If something returns 401 or 403, check this table first.

| Who | Needs | On | Why |
|---|---|---|---|
| You | **Foundry User** (formerly Azure AI User) | Foundry resource | create agents, use models |
| You | **Foundry Project Manager** (formerly Azure AI Project Manager) | Foundry resource | create the knowledge-base connection (or ask the facilitator to) |
| You | **Search Service Contributor** + **Search Index Data Contributor** | Search service | create knowledge sources and bases |
| Your **project's managed identity** | **Search Index Data Reader** | Search service | the agent's MCP tool reads the knowledge base |
| The **search service's managed identity** | **Cognitive Services User** | Foundry resource | the knowledge base calls the model for query planning and answer synthesis |
| The **search service's managed identity** | **Storage Blob Data Reader** | Storage account | only if you use a blob knowledge source |

Facilitators usually pre-assign these. If you have rights to do it yourself:

```bash
# project managed identity -> search reader
az role assignment create --assignee <project-MI-principal-id> --role "Search Index Data Reader" --scope <search-resource-id>
```

## 6. Common Day 1 blockers

| Symptom | Likely cause | Fix |
|---|---|---|
| `DefaultAzureCredential failed` | Not logged in, or wrong tenant | `az login --tenant <tenant-id>` |
| `doctor`: model deployment not found | Wrong deployment name (not model name) | Foundry portal → Models + endpoints → copy the **deployment** name |
| Knowledge base: 403 from search | Project managed identity lacks Search Index Data Reader | Section 5 |
| Agent answers with no citations or says "I don't know" for everything | Knowledge source still indexing, or MCP connection points at the wrong KB | Wait for indexing; check `KB_CONNECTION_NAME` and the target URL |
