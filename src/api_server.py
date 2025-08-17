import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd

# Ensure local src imports (e.g., `core`, `workflows`, `orchestrator`) resolve
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from workflows.integrated_orchestrator import IntegratedOrchestratorManagement
from orchestrator.adapters import DetectionReActAdapter

try:  # Optional at runtime
    from langchain_ibm import WatsonxLLM  # type: ignore
except Exception:  # pragma: no cover
    WatsonxLLM = None  # type: ignore


class WatsonxConfig(BaseModel):
    api_key: Optional[str] = Field(default_factory=lambda: os.environ.get("WATSONX_APIKEY"))
    url: Optional[str] = Field(default_factory=lambda: os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com"))
    project_id: Optional[str] = Field(default_factory=lambda: os.environ.get("WATSONX_PROJECT_ID"))
    model_id: Optional[str] | None = None


class DetectionRequest(BaseModel):
    lat: float
    lon: float
    radius_km: float = 100.0
    location_name: str = "monitored area"
    watsonx_config: WatsonxConfig = Field(default_factory=WatsonxConfig)
    situation_description: Optional[str] = None


class CompleteResponseRequest(BaseModel):
    lat: float
    lon: float
    radius_km: float = 100.0
    location_name: str = "monitored area"
    watsonx_config: WatsonxConfig = Field(default_factory=WatsonxConfig)
    situation_description: Optional[str] = None


app = FastAPI(title="ArkWatson API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)


def _persist_results(results: Dict[str, Any]) -> None:
    try:
        out_dir = Path(__file__).resolve().parents[1] / "integrated_demo_output"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"integrated_orchestrator_results_orch_{ts}.json"
        out_path.write_text(json.dumps(results, indent=2))
    except Exception:
        pass


def summarize_for_chat(results: Dict[str, Any]) -> list[str]:
    lines: list[str] = []
    ds = results.get("detection_summary", {})
    c = ds.get("classification", {})
    s = ds.get("severity", {})
    lines.append(
        f"Threat: {'YES' if c.get('threat_detected') else 'NO'} | Type: {c.get('disaster_type','unknown')} | Confidence: {c.get('confidence_score',0)} | Severity: {c.get('severity_level','low')}"
    )
    if c.get("risk_factors"):
        if isinstance(c.get("risk_factors"), list):
            lines.append("Risk Factors: " + ", ".join(c.get("risk_factors", [])[:3]))
    if s:
        lines.append(
            f"Severity Score: {s.get('severity_score', 0)} | Population At Risk: {s.get('population_at_risk', 0)} | Critical Infra: {s.get('critical_infrastructure_count', 0)}"
        )
        if s.get("recommendations"):
            if isinstance(s.get("recommendations"), list):
                lines.append("Actions: " + ", ".join(s.get("recommendations", [])[:3]))
    ps = results.get("planning_summary", {})
    if ps:
        lines.append(f"Planning: deployments={ps.get('deployments_created', 0)}, routes={ps.get('routes', 0)}")
    return lines


def summarize_with_watsonx(results: Dict[str, Any], model_id: str | None, watsonx_config: dict) -> str:
    try:
        if WatsonxLLM is None:
            raise RuntimeError("WatsonxLLM not available")
        params = {
            "decoding_method": "sample",
            "max_new_tokens": 300,
            "temperature": 0.3,
            "top_p": 0.9,
            "top_k": 50,
        }
        llm = WatsonxLLM(  # type: ignore
            model_id=model_id or watsonx_config.get("model_id") or "ibm/granite-3-3-8b-instruct",
            url=watsonx_config.get("url") or os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
            apikey=watsonx_config.get("api_key") or os.environ.get("WATSONX_APIKEY"),
            project_id=watsonx_config.get("project_id") or os.environ.get("WATSONX_PROJECT_ID"),
            params=params,
        )
        prompt = (
            "You are an incident commander assistant. Summarize the following disaster management JSON into 6-8 concise bullet points for executives. "
            "Include: current phase, threat type and confidence, severity level and key drivers, whether planning was triggered, deployments/routes counts, and immediate recommended actions.\n\nJSON:\n"
            + json.dumps(results)[:15000]
        )
        return str(llm.invoke(prompt))
    except Exception as e:  # Fallback deterministic summary
        return "\n".join(summarize_for_chat(results)) + f"\n(Note: model summary unavailable: {e})"


def _add_summary(results: Dict[str, Any], model_id: str | None, watsonx_cfg: dict) -> Dict[str, Any]:
    try:
        summary = summarize_with_watsonx(results, model_id, watsonx_cfg)
        results["watsonx_summary"] = summary
    except Exception:
        pass
    return results


def _data_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data"


@app.get("/geo/population_zones")
def get_population_zones() -> Dict[str, Any]:
    zones_path = _data_dir() / "population_zones.csv"
    items: list[dict[str, Any]] = []
    try:
        if zones_path.exists():
            df = pd.read_csv(zones_path)
            items = df.to_dict("records")
    except Exception:
        items = []
    return {"zones": items}


@app.get("/geo/evacuation_centers")
def get_evacuation_centers() -> Dict[str, Any]:
    centers_path = _data_dir() / "evacuation_zones.csv"
    items: list[dict[str, Any]] = []
    try:
        if centers_path.exists():
            df = pd.read_csv(centers_path)
            items = df.to_dict("records")
    except Exception:
        items = []
    return {"centers": items}


class SummaryRequest(BaseModel):
    results: Dict[str, Any]
    model_id: Optional[str] = None
    watsonx_config: WatsonxConfig = Field(default_factory=WatsonxConfig)


@app.post("/summary")
def generate_summary(req: SummaryRequest) -> Dict[str, Any]:
    text = summarize_with_watsonx(req.results, req.model_id, req.watsonx_config.model_dump())
    return {"summary": text}

@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/latest")
def latest() -> Dict[str, Any]:
    out_dir = Path(__file__).resolve().parents[1] / "integrated_demo_output"
    if not out_dir.exists():
        return {}
    latest_file = None
    latest_mtime = 0
    for f in out_dir.glob("integrated_orchestrator_results_*.json"):
        mtime = f.stat().st_mtime
        if mtime > latest_mtime:
            latest_mtime = mtime
            latest_file = f
    if not latest_file:
        return {}
    try:
        return json.loads(latest_file.read_text())
    except Exception:
        return {}


@app.post("/detect")
def detect(req: DetectionRequest, persist: bool = Query(default=True)) -> Dict[str, Any]:
    detector = DetectionReActAdapter()
    result = _run_async(
        detector.run(
            lat=req.lat,
            lon=req.lon,
            radius_km=req.radius_km,
            location_name=req.location_name,
            watsonx_config=req.watsonx_config.model_dump(),
            situation_description=req.situation_description,
        )
    )
    payload = {
        "management_phase": "monitoring_only",
        "planning_triggered": False,
        "detection_summary": {
            "event_detected": bool(result.get("classification", {}).get("threat_detected", False)),
            "classification": result.get("classification", {}),
            "severity": result.get("severity", {}),
            "monitoring": result.get("monitoring_summary", {}),
        },
        "session_id": f"orch_{int(datetime.now().timestamp())}",
        "timestamp": datetime.now().isoformat(),
    }
    payload = _add_summary(payload, req.watsonx_config.model_id, req.watsonx_config.model_dump())
    if persist:
        _persist_results(payload)
    return payload


@app.post("/complete_response")
def complete_response(req: CompleteResponseRequest, persist: bool = Query(default=True)) -> Dict[str, Any]:
    manager = IntegratedOrchestratorManagement()
    results = _run_async(
        manager.run_complete_disaster_management(
            monitoring_regions=[{
                "name": req.location_name,
                "center_lat": req.lat,
                "center_lon": req.lon,
                "radius_km": req.radius_km,
            }],
            session_id=f"orch_{int(datetime.now().timestamp())}",
            config={"watsonx_config": req.watsonx_config.model_dump()},
            situation_description=req.situation_description,
        )
    )
    results = _add_summary(results, req.watsonx_config.model_id, req.watsonx_config.model_dump())
    if persist:
        _persist_results(results)
    return results


# Dev: conda run -n ibm_disaster_mgmt uvicorn src.api_server:app --reload --port 8080


