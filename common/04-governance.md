# 04 · Governance: identity, access scoping, audit

Your agent needs a governance story the panel can check. You produce:

1. **Evidence** of the controls Foundry gives you, and
2. A **governance design** for running the agent in production.

Deliver this as the *Governance* section of your project report (template in `templates/project-report-template.md`).

## A. Identity: who is the agent?

| Question | Where to find the evidence |
|---|---|
| What identity does the agent use when it calls tools? | Foundry portal → your agent → details. Record whether an **agent identity (Microsoft Entra Agent ID)** is shown. For the Foundry IQ MCP tool, the project connection uses the **project's managed identity** (`ProjectManagedIdentity` auth). Note its principal ID. |
| Which human identities can change the agent? | Foundry resource → Access control (IAM): who has Foundry Owner, Project Manager or User |
| How are users authenticated? | Lab: your Entra account through `DefaultAzureCredential`. Production: describe Entra sign-in in the client app. |

## B. Access scoping: what can it touch?

Make a least-privilege table for **your** agent:

| Resource | Principal | Role / permission | Why it's needed | Could it be narrower? |
|---|---|---|---|---|
| Search service (knowledge base) | Project MI | Search Index Data Reader | Retrieval | Scope to the specific index (preview), per-user trimming |
| Foundry model | Search MI | Cognitive Services User | KB query planning | |
| Semantic layer | Client app | Read-only; whitelisted measures and entities only, parameterised SQL | Metrics | Row-level filters per user role |
| Web (Retail) | Search service | Bing via Web knowledge source, allow-listed domains only | Approved web | Snapshot-only mode |

Also cover:

- **Data minimisation:** what the agent may and may not reveal (for example no payment card data in Retail, no unit cost as selling price in Manufacturing, KAM approval for customer-facing recommendations in FMCG).
- **Guardrails:** Foundry content filters / guardrails on the model deployment; prompt-injection resistance (one of your eval questions should test this).
- **Human in the loop:** which outputs are decision support and need a human before action.

## C. Audit: can we reconstruct what happened?

| Evidence | How |
|---|---|
| Conversation and tool-call trace | Foundry portal → Agents → your agent → **Traces / Monitor** (needs Application Insights connected to the project; ask your facilitator). Screenshot one trace showing the MCP call and the function calls. |
| Agent version history | Each `deploy` creates a new version. List the versions and what changed (prompt, tools). |
| Evaluation history | Your `runs/*.eval.md` reports and Foundry evaluation runs |
| Data lineage for numbers | `semantic://` citations in answers + `sql` in the tool result (log it) |

Add the client-side log from `agent_app.py ask` as supporting evidence (it prints response IDs, tool calls and citations).

## D. Production governance design

| Governance need | Lab evidence (today) | Production design |
|---|---|---|
| Inventory and ownership | Agent name, version, owner in report | Register the agent in the enterprise agent inventory with owner, purpose and data classification |
| Identity | Project MI / agent identity | Microsoft Entra Agent ID; lifecycle (create, rotate, disable) |
| Access policies | RBAC table above | Central access policies and conditional access for agents; least-privilege templates |
| Observability and audit | Foundry traces, eval reports | Central activity and audit views, alerts on anomalous tool use |
| Lifecycle | Versioned deploys, eval before promote | Approval workflow to publish; decommissioning |
| Risk | Guardrails, refusal tests | Policy-based blocking, risk reports |

> Present production controls as **planned design**. Don't claim you configured something you didn't; the panel will ask.

## E. Five questions the panel will probably ask

1. If a user asks for data they shouldn't see, what stops the agent?
2. What happens if the knowledge base returns a superseded document?
3. How would you know the agent started giving worse answers after a prompt change?
4. Which outbound calls leave your Azure boundary? (Retail: Bing web.)
5. How do you take the agent offline in an incident?
