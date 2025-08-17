# ProjectArkWatson (PAW)
The Noah's Ark of AI. An Agentic Framework for Disaster Management using IBM Watsonx.
(IBM Hackathon submission)

## Description
- ArkWatson leverages agentic capabilities for end-to-end disaster management scenarios of various types, including continous monitoring, alerts, predictions and planning.
- Leveraing open source APIs for live data collation along with IBM's cloud services for Watsonx agents with tool calling workflows and scraping for best effort prediction/planning/management of disaster scenarios.

## IBM watsonx Orchestrator (ReAct and Plan-Act) Integration

This project includes an optional integration with IBM watsonx Orchestrator to replace LangGraph-driven workflows with native agents:

- ReAct agent for detection: `orchestrator_agents/detection_react.yaml`
- Plan-Act agent for planning: `orchestrator_agents/planning_plan_act.yaml`

Python tools exposed for Orchestrator are implemented in `src/orchestrator/tools.py` and mirror existing functionality in `src/monitoring/`.

Local adapters allow running the agent logic without the Orchestrator control plane:

- `DetectionReActAdapter` and `PlanningPlanActAdapter` in `src/orchestrator/adapters.py`

These keep the current LangGraph flows intact while enabling progressive migration.

## Agentic Workflow Diagrams

### Detection (ReAct-style)


Mermaid source:

```mermaid
graph TD
subgraph Monitoring
  A["API Monitoring"]
end
subgraph Data Analysis
  B["Data Analysis"]
end
subgraph Classification
  C["WatsonX Classification"]
end
subgraph Confirmation
  D["Web Search Confirmation"]
  FP["Log False Positive"]
end
subgraph "Severity & Safe Zones"
  E["Severity Assessment"]
  F["Safe Zone Analysis"]
end
subgraph "Event & Escalation"
  G["Create Event Record"]
  H["Trigger Planning Workflow"]
end
subgraph "Loop Control"
  I["Wait Interval"]
end
A -->|OK| B
A -->|Error| I
A -.->|Retry| A
B -->|Threat suspected| C
B -->|No signal| I
C -->|Needs confirmation| D
C -->|Confident / ongoing| E
C -->|No threat| I
D -->|Confirmed| E
D -->|Not confirmed| FP
FP --> I
E -->|Escalation required| F
E -->|Moderate| G
F --> G
G -->|Trigger planning| H
G -->|No trigger| I
H --> I
I --> A
```

Source file: `detection.mmd`

### Planning (Plan-Act-style)

Mermaid source:

```mermaid
graph TD
subgraph "Initialization"
  A["Load Planning Data"]
end
subgraph "Assessment"
  B["Assess Planning Requirements"]
end
subgraph "Planning"
  C["Create Deployment Plan"]
  D["Create Evacuation Plan"]
end
subgraph "Coordination"
  E["Coordinate Resources"]
end
subgraph "Notifications"
  F["Generate Notifications"]
  G["Send Notifications"]
end
subgraph "Completion"
  H["Planning Complete"]
  X["Planning Error Handling"]
  Z["End"]
end
A -->|"Success"| B
A -->|"Failure"| X
B --> C
C --> D
D --> E
E --> F
F --> G
G --> H
H --> Z
X --> Z
```

Source file: `planning.mmd`

## Orchestrator-Style Integrated Demo

Run the local integrated flow:

```bash
python demo_orchestrator_integration.py --region "San Francisco Bay Area" --lat 37.7749 --lon -122.4194 --radius 100
```

To force planning for an ongoing event via prompt, pass a situation description containing ongoing keywords:

```bash
python demo_orchestrator_integration.py \
  --region "San Francisco Bay Area" \
  --lat 37.7749 --lon -122.4194 --radius 100 \
  --situation "There is an ongoing wildfire impacting the East Bay currently"
```

Environment configuration (loaded from `.env`):

- `WATSONX_APIKEY`: IBM watsonx.ai API key
- `WATSONX_URL`: IBM watsonx.ai base URL (default `https://us-south.ml.cloud.ibm.com`)
- `WATSONX_PROJECT_ID`: watsonx.ai project ID
- `WATSONX_MODEL_ID`: model ID (e.g., `ibm/granite-13b-instruct-v2`)

You can start from the provided template at `ProjectArkWatson/config_template.env` and copy it to `.env`.

## IBM Technology Highlights

- IBM watsonx Orchestrator (ADK):
  - Native agents using ReAct and Plan-Act styles, with Python tools mapped to our monitoring and planning functions
  - YAML agent definitions: `orchestrator_agents/detection_react.yaml`, `orchestrator_agents/planning_plan_act.yaml`
- IBM watsonx.ai LLMs via `langchain-ibm` and `ibm-watsonx-ai`:
  - Granite family (e.g., `ibm/granite-13b-instruct-v2`) for classification and planning prompts
  - Tool-centric reasoning for classification, severity assessment, and optimization
- Optional integration path to import agents into watsonx Orchestrate and register tools for production use

