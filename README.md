# ProjectArkWatson (PAW)
IBM Hackathon Submission

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

