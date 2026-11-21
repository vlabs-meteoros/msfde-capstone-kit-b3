# Lab environment card (Batch 3)

You sign in as **fdeuserN@justlabs.online** (your facilitator gives you N). Everything below is already provisioned for you.

| Item | Value |
|---|---|
| Foundry portal | https://ai.azure.com (make sure the **New Foundry** toggle is on) |
| Azure portal | https://portal.azure.com |
| Subscription | Microsoft Azure Sponsorship (`e68da77e-d26f-4da2-92d5-d5b490dc0014`) |
| Resource group | `rg-fde-capstone-b3` |
| Foundry resource | `fde-b3-foundry` (East US 2) |
| **Your project** | `proj-fdeuserN` |
| Project endpoint | `https://fde-b3-foundry-5tric.services.ai.azure.com/api/projects/proj-fdeuserN` |
| Chat model deployment | `gpt-5-mini` (shared) |
| Embedding deployment | `text-embedding-3-small` (shared, used by knowledge sources) |
| Azure AI Search (Foundry IQ) | `srch-fde-b3-5tric` (S2, East US): `https://srch-fde-b3-5tric.search.windows.net` |
| Storage account | `stfdeb35tric`, container **`docs-fdeuserN`** for your documents |
| Web knowledge source (Retail) | Enabled in this subscription |

## Naming rule: shared services

The search service and storage account are shared by about 60 people. Prefix everything you create with your user name:

- knowledge sources: `ks-fdeuserN-<usecase>-docs`, `ks-fdeuserN-rtl-web`
- knowledge base: `kb-fdeuserN-<usecase>`
- agent: `<usecase>-agent-fdeuserN` (the default in `agent_app.py` when `PARTICIPANT_ALIAS=fdeuserN`)
- knowledge-base connection: `kbconn-fdeuserN-<usecase>`. Connection names must be unique across the **whole** Foundry resource, not just your project.

**Don't touch anyone else's objects.** You technically can (shared service), and it would break their build.

## Your permissions (already assigned)

| On | Role |
|---|---|
| Resource group | Reader |
| Foundry resource | Foundry User |
| Your project `proj-fdeuserN` | Foundry Project Manager (lets you create the knowledge-base connection) |
| Search service | Search Service Contributor + Search Index Data Contributor |
| Storage account | Storage Blob Data Contributor |
| Your project's managed identity | Search Index Data Reader on the search service (so your agent can query your knowledge base) |

## First commands on the VM

```bash
az login            # sign in as fdeuserN@justlabs.online
az account set --subscription e68da77e-d26f-4da2-92d5-d5b490dc0014
copy .env.sample .env   # then replace every N with your number
python tools/validate_kit.py
python common/starter/agent_app.py doctor --usecase <manufacturing|retail|fmcg>
```

Upload your use case's documents to your container:

```bash
az storage blob upload-batch --account-name stfdeb35tric --auth-mode login -d docs-fdeuserN -s usecases/<usecase>/data/docs
```

(Retail: also upload `data/web-snapshots` into a folder or a second container if you use the snapshot fallback.)
