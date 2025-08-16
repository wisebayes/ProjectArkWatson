# LangGraph Agentic Workflows — A Concise How-To

This guide distills the key patterns from your code into a crisp reference for building agentic pipelines with **LangGraph** (what you called “laggraph”).

---

## Core ideas

* **State-first design.** Define a single `TypedDict` (or Pydantic model) for your graph state. Each node reads the state and **returns a partial update** (a dict you `**`-merge into state).
* **Nodes are pure functions.** A node is `Callable[GState -> GState]`. Keep side effects inside tools or services.
* **Edges define execution.** Normal edges = sequence, **conditional edges = branching**, and **multiple outgoing edges** enable **parallel** work when there are no data hazards.
* **Human-in-the-loop.** Use `interrupt()` to pause, then resume with `Command(resume=...)`.
* **Persistence & scale.** Attach a checkpointer (e.g., `RedisSaver`) so you can resume, branch, and run with multiple workers.

---

## 1) Define your state

```python
from typing import TypedDict, List, Dict, Any, Optional, Set

class GState(TypedDict):
    # Inputs
    immutable_claims: List[Claim]
    guidelines: List[str]
    slot_definitions: List[SlotDefinition]
    user_query: Dict[str, Any]

    # Planning & control
    plan: List[SlotPlanItem]
    current_slot_plan_index: int
    citations: Set[str]

    # Per-slot working vars
    current_slot_id: Optional[str]
    current_slot_description: Optional[str]
    current_slot_max_tokens: Optional[int]
    picked_claim_ids_for_current_slot: List[int]
    draft_for_current_slot: Optional[str]
    flags_for_current_slot: List[str]
    refine_iterations_left_for_current_slot: int

    # Accumulated results
    approved_slot_content: Dict[str, str]

    # HTML mode (optional)
    html_template: Optional[str]
    current_html_output: Optional[str]
    is_html_mode: bool

    # User feedback loop
    user_query_for_edit: Optional[str]
    parsed_user_edit_request: Optional[UserEditRequest]
    multiple_user_edit_requests: Optional[List[UserEditRequest]]
    user_interaction_count: int
    max_user_interactions: int
    is_finalized: bool
    validation_issues_from_user_changes: Optional[List[str]]
    recently_changed_slots: Optional[List[str]]

    # Status / outputs
    final_rendered_output: Optional[str]
    global_error_message: Optional[str]
    last_operation_status: Optional[str]
```

**Tips**

* Return only the keys you change; LangGraph merges them into the global state.
* Keep long-lived results (e.g., `approved_slot_content`) separate from per-slot scratch fields.

---

## 2) Tools with `@tool`

Use LangChain’s `@tool` to wrap any callable you want nodes to use. Your code shows three common patterns:

1. **Planner / selector** (decide order or pick IDs):

```python
from langchain_core.tools import tool

@tool(return_direct=True)
def slot_order_planner(slot_definitions_json: str, user_query_json: dict) -> str:
    # May call an LLM, else a rule-based fallback
    return json.dumps({"planned_order": [...]})
```

2. **Generator** (produce content from inputs):

```python
@tool(return_direct=True)
def draft_copy(slot_id: str, slot_desc: str, claim_ids: List[int], ... ) -> str:
    # LLM-backed drafting; strip HTML if needed
    return json.dumps({"draft": "..."})
```

3. **Evaluator / editor** (scan, rewrite, validate):

```python
@tool(return_direct=True)
def guideline_scan(text: str, rules: List[str], existing_content, slot_id: str, slot_desc: str) -> str:
    # LLM or rule-based checks
    return json.dumps({"risk_flags": [...]})
```

**Usage inside nodes**: call `.invoke({...})`, parse JSON, update state.

---

## 3) Nodes (the work units)

Each node is a function `state -> updated_state`.

```python
def start_node(state: GState) -> GState:
    return {
        **state,
        "plan": [],
        "approved_slot_content": {},
        "is_html_mode": bool(state["user_query"].get("html_template")),
        "current_html_output": state["user_query"].get("html_template"),
    }
```

Examples from your graph:

* **planning\_node** → computes `plan` via `slot_order_planner`.
* **select\_slot\_node** → loads the next `SlotPlanItem` into per-slot fields.
* **claim\_picker\_node** / **draft\_copy\_node** → create candidate content.
* **guideline\_scan\_node** → detect issues; **rewrite\_copy\_node** → fix & loop.
* **accept\_slot\_node** → persist successful draft.
* **merge\_node** → render final output (HTML or templated string).
* **await\_user\_feedback\_node** → `interrupt(...)` to collect human edits.
* **process\_user\_feedback\_node** / **apply\_user\_changes\_node** / **validate\_user\_changes\_node** → edit cycle with compliance re-scan.
* **finalize\_content\_node** → save & mark `is_finalized=True`.

---

## 4) Building the graph

```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(GState)

# Register nodes
workflow.add_node("start_node", start_node)
workflow.add_node("planning_node", planning_node)
# ... add all node functions ...

# Entry point (REQUIRED)
workflow.set_entry_point("start_node")
```

### Sequential edges

```python
workflow.add_edge("start_node", "planning_node")
workflow.add_edge("planning_node", "select_slot_node")
workflow.add_edge("claim_picker_node", "draft_copy_node")
workflow.add_edge("draft_copy_node", "guideline_scan_node")
```

### Conditional edges (branching)

A **router** returns a *label*, which you map to next nodes:

```python
def decide_after_scan_router(state: GState) -> str:
    flags = state["flags_for_current_slot"]
    left = state["refine_iterations_left_for_current_slot"]
    if not flags:
        return "accept_slot_node"
    if left > 0:
        return "rewrite_copy_node"
    return "accept_slot_node"

workflow.add_conditional_edges(
    "guideline_scan_node",
    decide_after_scan_router,
    {
        "accept_slot_node": "accept_slot_node",
        "rewrite_copy_node": "rewrite_copy_node",
    }
)
```

> **Gotcha:** The router should return **mapping keys** (labels), not raw node names—unless your mapping uses those exact strings.

### Ending a path

Route to `END` to terminate:

```python
workflow.add_edge("finalize_content_node", END)
# or in a conditional mapping: { "TERMINATE": END }
```

---

## 5) Parallel execution

LangGraph schedules any **independent** downstream nodes concurrently. You get parallelism by **fanning out edges** from a node to multiple next nodes that don’t depend on each other.

```python
# A -> (B and C in parallel) -> D
workflow.add_edge("A", "B")
workflow.add_edge("A", "C")
workflow.add_edge("B", "D")
workflow.add_edge("C", "D")
```

**Notes**

* Ensure B and C **don’t write the same state keys** (or design deterministic merge rules).
* D will run once both B and C have advanced the state sufficiently for D to proceed.
* Actual concurrency depends on the runtime and executors; LangGraph will orchestrate readiness and allow workers to process ready nodes in parallel.

---

## 6) Start & End requirements

* **Required:** `workflow.set_entry_point("...")`
* **At least one path to an end:** Use `END` or a node that leads to `END`.
* Cycles (loops) are allowed (e.g., iterate slots or rewrite passes); control them via counters (e.g., `refine_iterations_left_for_current_slot`) and routers.

---

## 7) Human-in-the-loop (`interrupt`)

Pause a run and surface context to the user:

```python
from langgraph.types import interrupt, Command

def await_user_feedback_node(state: GState) -> GState:
    payload = {
        "content_preview": "...",
        "prompt_message": "What would you like to change?"
    }
    user_input = interrupt(payload)  # pauses and returns on resume
    return { **state, "user_query_for_edit": user_input }
```

Resume the graph by streaming a `Command`:

```python
from langchain_core.runnables.config import RunnableConfig
config = RunnableConfig(configurable={"thread_id": "my-run"}, recursion_limit=500)

# First call with initial inputs...
# On interrupt, resume:
app.stream(Command(resume="shorten headline"), config=config, stream_mode="values")
```

---

## 8) Persistence, streaming, and multi-worker

Attach a checkpointer (Redis) so state is durable and workers can pick up where others left off:

```python
from langgraph.checkpoint.redis import RedisSaver

with RedisSaver.from_conn_string(os.environ["CELERY_BROKER_URL"]) as cp:
    cp.setup()
    app = workflow.compile(checkpointer=cp)

# Streaming execution (emits state snapshots)
for event_state in app.stream(initial_state, config=config, stream_mode="values"):
    ...
```

**Tips**

* One `thread_id` per logical conversation/run.
* If you see Redis errors, ensure `CELERY_BROKER_URL` is set and modules are loaded server-side.

---

## 9) HTML templating pattern

* Put raw HTML in `user_query["html_template"]` with placeholders like `|--- slot_key ---|`.
* Generate plain text in nodes, then replace via a small **HTML filler tool**.
* `merge_node` iterates `approved_slot_content` and fills the HTML template.

```python
@tool(return_direct=True)
def html_content_filler(current_html: str, slot_id: str, content: Any, current_content: Optional[str]=None) -> str:
    return _fill_html_placeholder(current_html, slot_id, content, current_content)
```

---

## 10) Common patterns you used (and you should reuse)

* **Plan → Select → Produce → Check → Fix → Accept → Next** for each unit of work.
* **Router functions** to keep branching logic out of nodes.
* **Multiple conditional routers** around feedback & validation cycles.
* **Graceful fallbacks** (LLM errors → rule-based).
* **Mermaid** rendering for fast visual checks: `app.get_graph().draw_mermaid()`.

---

## Minimal “Hello, Parallel World” example

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class S(TypedDict):
    a: int
    b: int
    c: int
    d: int

def start(s: S) -> S:
    return {**s, "a": 1}

def work_b(s: S) -> S:
    return {**s, "b": s["a"] + 1}

def work_c(s: S) -> S:
    return {**s, "c": s["a"] + 2}

def merge_d(s: S) -> S:
    return {**s, "d": s["b"] + s["c"]}

g = StateGraph(S)
g.add_node("start", start)
g.add_node("work_b", work_b)
g.add_node("work_c", work_c)
g.add_node("merge_d", merge_d)
g.set_entry_point("start")

# Fan out = parallelizable
g.add_edge("start", "work_b")
g.add_edge("start", "work_c")

# Join
g.add_edge("work_b", "merge_d")
g.add_edge("work_c", "merge_d")

g.add_edge("merge_d", END)
app = g.compile()
```

---

## Troubleshooting checklist

* **Router keys mismatch?** Ensure the router returns **labels used in the mapping**.
* **Infinite loop?** Guard with counters (e.g., `refine_iterations_left...`) and branch to acceptance/END.
* **State collisions in parallel?** Avoid writing the same keys from multiple parallel nodes, or design a deterministic merge.
* **HTML shows old values?** When editing, pass `current_content` to your filler so replacements find prior text.

---

## What to copy from your codebase (as a starter kit)

* `@tool` patterns: planner, picker, draft, scan, rewrite, edit, html filler.
* Node catalog and the **plan → select → draft → scan → rewrite → accept** loop.
* Feedback interrupt + `Command(resume=...)` resume flow.
* Redis checkpointer + streaming wrapper.
* `merge_node` split for **HTML** and **string-template** modes.

Use this skeleton to author new agents: swap your domain tools, redefine the state keys, keep the graph structure.
