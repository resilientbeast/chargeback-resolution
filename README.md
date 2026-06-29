# 🛡️ Chargeback Resolution Automation Solution

This repository contains an end-to-end automated solution for handling e-commerce chargebacks and payment disputes. Built on the **UiPath Platform** utilizing **Maestro Case Management** and **Python-based Coded Agents (LangGraph)**, this solution orchestrates the entire dispute lifecycle from initial evidence gathering to outcome monitoring.

## 📖 Table of Contents
1. [Overview & Architecture](#overview--architecture)
2. [Maestro Case Management Lifecycle](#maestro-case-management-lifecycle)
3. [Coded Agents Architecture](#coded-agents-architecture)
4. [Agent Deep Dives](#agent-deep-dives)
5. [Data Flow & Integration](#data-flow--integration)
6. [Deployment & Solution Packaging](#deployment--solution-packaging)
7. [Troubleshooting & Quirks](#troubleshooting--quirks)

---

## 🏗️ Overview & Architecture

When a chargeback is initiated (e.g., in Stripe), significant manual effort is traditionally required to cross-reference order data, analyze the dispute reason code, and draft a rebuttal. This solution automates the heavy lifting:
- **Case Management (Maestro):** Acts as the state machine and orchestrator, routing data between different AI Agents and Human-in-the-loop steps.
- **Coded Agents (Python):** Specialized microservices built using LangGraph. Each agent is responsible for a single domain (e.g., fetching data from an API, using an LLM to score evidence, or drafting a rebuttal).
- **Human-in-the-Loop:** At critical junctures (like submitting the final response to the bank), the system suspends execution and assigns an Action Center task to a human analyst.

---

## 🛤️ Maestro Case Management Lifecycle

The orchestration is defined in `chargeback-resolution/caseplan.json` and is broken down into distinct stages. The Case receives the initial payload (e.g., `wooOrderId` and `stripeChargeId`) and routes it through the following pipeline:

### Stage 1: Evidence Gathering
*Collects transaction records, order data, and supporting documents.*
- **Fetch WooCommerce Order:** Triggers the `woo-evidence-agent` to pull down customer metadata, shipping info, and line items.
- **Fetch Stripe Evidence:** Triggers the `stripe-evidence-agent` to pull down the dispute reason code, charge amount, and payment intent metadata.
- **Score Evidence Quality:** Triggers the `scorer-agent` to cross-reference both datasets and assign a "Quality Score" based on how complete the evidence is.

### Stage 2: Strategy
*Determines the optimal defense strategy based on reason code and evidence.*
- **Analyze Dispute Strategy:** Triggers the `strategy-agent` to generate a recommended approach (e.g., "Argue product was delivered," "Argue friendly fraud").
- **Calculate Win Probability:** Triggers the `probability-agent` to estimate the likelihood of winning the dispute.

### Stage 3: Response Drafting
*Drafts the formal rebuttal letter and compiles the evidence package.*
- **Draft Rebuttal Letter:** Triggers the `drafter-agent` to dynamically generate a formal response tailored to the specific reason code, injecting the factual evidence gathered in Stage 1.
- **Package Evidence Bundle:** Compiles the drafted letter and the raw API JSON data into a unified evidence package.

### Stage 4: Human Review
*Analyst reviews AI-drafted response and approves or requests changes.*
- Pauses the automation and creates a task in **UiPath Action Center**.
- A human analyst reads the `rebuttalDraft`, reviews the `evidenceSummary`, and either approves the submission, edits the draft, or rejects it.

### Stage 5: Submission
*Submits the finalized evidence to the payment gateway.*
- Automatically pushes the human-approved rebuttal and evidence package back to Stripe via API.

### Stage 6: Outcome Monitoring
*Monitors the dispute status and closes the case.*
- Periodically polls the payment gateway to see if the bank ruled in our favor (Won) or against us (Lost), and updates the internal Case Status accordingly.

---

## 🤖 Coded Agents Architecture

Unlike traditional RPA workflows built in UiPath Studio (XAML), this solution utilizes **Python-based Coded Agents**. 

Each Agent is a self-contained Python project with the following structure:
- `pyproject.toml` and `uv.lock`: Dependency management (using `uv`).
- `uipath.json` and `project.uiproj`: UiPath project definitions mapping the Python entry points.
- `langgraph.json`: Instructs the UiPath Solution Packager to treat this as an Agent (not a basic Function).
- `main.py`: The core LangGraph state graph definition. It defines the Nodes, Edges, and the compiled graph instance.
- `agent.json` / `entry-points.json`: Maps the required Case inputs (e.g., `wooOrderId`) to the Agent's state schema, and maps the Agent's outputs (e.g., `order_data_json`) back to the Maestro Case variables.

---

## 🔍 Agent Deep Dives

### 1. `woo-evidence-agent`
- **Purpose:** Connects to the WooCommerce REST API.
- **Input:** `wooOrderId`
- **Output:** `wooOrderDetails` (JSON representation of the order, customer IP, billing/shipping address).

### 2. `stripe-evidence-agent`
- **Purpose:** Connects to the Stripe REST API.
- **Input:** `stripeChargeId`
- **Output:** `stripeDisputeDetails` (JSON representation of the dispute reason, amount, currency, and payment intent).

### 3. `scorer-agent`
- **Purpose:** Evaluates evidence completeness.
- **Input:** `wooOrderDetails`, `stripeDisputeDetails`
- **Output:** `evidenceQualityScore` (0-100), `evidenceSummary`

### 4. `strategy-agent`
- **Purpose:** Recommends dispute strategy.
- **Input:** `wooOrderDetails`, `stripeDisputeDetails`, `evidenceQualityScore`, `evidenceSummary`
- **Output:** `strategyRecommendation`, `confidenceLevel`, `requiresHumanReview`

### 5. `probability-agent`
- **Purpose:** Estimates win probability using historical patterns.
- **Input:** Evidence and Strategy parameters.
- **Output:** `winProbability` (Float percentage).

### 6. `drafter-agent`
- **Purpose:** Uses an LLM to write the dispute rebuttal.
- **Input:** All prior data points.
- **Output:** `rebuttalDraft` (Formatted string).

---

## 🔄 Data Flow & Integration

The system uses **Maestro Global Variables** to pass state between isolated agents.
For example:
1. `woo-evidence-agent` sets its output to the Maestro variable `wooOrderDetails`.
2. Maestro holds `wooOrderDetails` in its case state.
3. When `scorer-agent` spins up, Maestro passes the value of `wooOrderDetails` into the agent's LangGraph state as an input parameter.

This decoupled architecture ensures that agents can be developed, tested, and versions upgraded independently.

---

## 🚀 Deployment & Solution Packaging

This project relies on the **UiPath CLI (`uip`)** for deployment.
Because multiple interconnected agents are involved, we use the `uip solution pack` approach via a `.uipx` solution definition file.

### Deployment Commands:
```bash
# 1. Package the entire solution into a .zip file
uip solution pack ./ ./dist --version 2.1.3

# 2. Publish the package to Orchestrator
uip solution publish ./dist/chargeback-solution_2.1.3.zip --output json

# 3. Deploy the published package to a specific Orchestrator Folder
uip solution deploy run --name ChargebackV5 --package-name chargeback-solution --package-version 2.1.3 --folder-name ChargebackV5 --parent-folder-path Shared --output json
```

---

## ⚠️ Troubleshooting & Quirks (The "Undefined Process" Bug)

If you encounter a `"Failure to start the Orchestrator job (170007) - Undefined process"` error in the Maestro Case Manager execution trail, it is likely due to a misalignment between how the Agents are packaged and how the Case Plan tries to bind them.

### The Root Cause
If Coded Agents were initially scaffolded as standard "Functions", the UiPath platform may still aggressively try to treat them as such. 

**For a Coded Agent to work in Maestro, three conditions MUST be met:**
1. **`langgraph.json`**: The agent's root directory must contain a `langgraph.json` file. This signals to the packager that it is a Graph/Agent, not a standard code Function.
2. **`.uipx` Solution Definition**: In `chargeback-solution.uipx`, the `Type` field for the project must be explicitly set to `"Agent"` (not `"Function"`).
   ```json
   {
     "Type": "Agent",
     "ProjectRelativePath": "woo-evidence-agent/project.uiproj",
     "Id": "woo-evidence-agent"
   }
   ```
3. **`caseplan.json` Bindings**: In the Case Plan definition, the bindings mapping the Maestro task to the Orchestrator process MUST explicitly include `"resourceSubType": "Agent"`.
   ```json
   {
       "id": "bEvWcName",
       "name": "name",
       "type": "string",
       "resource": "process",
       "resourceSubType": "Agent",
       "resourceKey": "Shared/ChargebackV5.woo-evidence-agent",
       "default": "woo-evidence-agent",
       "propertyAttribute": "name"
   }
   ```
*If `"resourceSubType": "Agent"` is omitted, Maestro will search Orchestrator's "Functions" list for your process. Since your process was deployed as an "Agent", it won't find it and will throw the `Undefined process` error!*

### Fixing Orchestrator Conflicts
If you deploy an Agent with the same name as a previously deployed Function, Orchestrator will silently reject the "Type change" during deployment, or Maestro will get confused.
You must manually delete the old Function bindings via CLI before redeploying the Agents:
```bash
# List all processes in the folder
uip or processes list --folder-name ChargebackV5

# Delete the conflicting function processes
uip or processes delete --folder-name ChargebackV5 --key <PROCESS_KEY>
```