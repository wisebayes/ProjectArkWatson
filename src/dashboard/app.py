import json
import os
import sys
import asyncio
import time
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st
import pydeck as pdk
import plotly.graph_objects as go

# Allow importing workflow modules when running via Streamlit
sys.path.append(str(Path(__file__).resolve().parents[1]))
from workflows.integrated_orchestrator import IntegratedOrchestratorManagement  # type: ignore
from orchestrator.adapters import DetectionReActAdapter  # type: ignore

try:
    from langchain_ibm import WatsonxLLM  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    WatsonxLLM = None  # type: ignore


st.set_page_config(page_title="ArkWatson - Disaster Ops Center", layout="wide")


def inject_global_styles() -> None:
    """Inject subtle global styles and card aesthetics for a more premium UI."""
    st.markdown(
        """
        <style>
        /* Layout */
        .main .block-container {max-width: 1400px; padding-top: 1.2rem; padding-bottom: 2rem;}

        /* KPI metric cards - dark gradient */
        div.stMetric { 
            background: linear-gradient(135deg, #0b132b 0%, #1c2541 40%, #3a506b 100%);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px;
            padding: 14px 16px;
            box-shadow: 0 8px 24px rgba(16,16,16,0.22);
            color: #e6f4ff !important;
        }
        div.stMetric label, div.stMetric [data-testid="stMetricValue"] {color: #e6f4ff !important;}
        div.stMetric [data-testid="stMetricDelta"] { 
            background: rgba(255,255,255,0.08); 
            padding: 2px 8px; 
            border-radius: 999px; 
        }

        /* Badges */
        .aw-badge { display:inline-block; padding:6px 12px; border-radius:999px; font-weight:700; font-size:12px; letter-spacing: .2px; }
        .aw-primary { background:#1565c0; color:#ffffff; }
        .aw-danger { background:#b71c1c; color:#ffffff; }
        .aw-success { background:#2e7d32; color:#ffffff; }
        .aw-warning { background:#ef6c00; color:#ffffff; }
        .aw-neutral { background:#455a64; color:#ffffff; }
        .aw-magenta { background:#6a1b9a; color:#ffffff; }

        /* Hero - dark gradient */
        .aw-hero { 
            border-radius: 16px; 
            padding: 18px 20px; 
            background: linear-gradient(120deg,#0f2027 0%, #203a43 45%, #2c5364 100%);
            color: #eef7ff; 
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 10px 28px rgba(0,0,0,0.25);
        }
        .aw-hero h2 { margin: 0 0 8px 0; }

        /* Cards */
        .aw-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 14px; }
        
        /* Tabs spacing */
        .stTabs [data-baseweb="tab-list"] { gap: 4px; }
        .stTabs [data-baseweb="tab"] { background: rgba(255,255,255,0.04); border-radius: 10px; padding: 8px 12px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def load_latest_results() -> Dict[str, Any]:
    out_dir = Path(__file__).parents[2] / "integrated_demo_output"
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


def render_map(classification: Dict[str, Any], monitoring: Dict[str, Any], unique_key: str = ""):
    # Use San Francisco coordinates as default since that's where the population zones are
    lat = monitoring.get("summary", {}).get("center_lat") or monitoring.get("center_lat") or monitoring.get("lat") or 37.7749
    lon = monitoring.get("summary", {}).get("center_lon") or monitoring.get("center_lon") or monitoring.get("lon") or -122.4194
    
    # Load population zones to show affected areas on map
    data_dir = Path(__file__).parents[2] / "data"
    zones_file = data_dir / "population_zones.csv"
    
    map_data = []
    if zones_file.exists():
        try:
            zones_df = pd.read_csv(zones_file)
            pop_max = max(1.0, float(zones_df["population"].max())) if "population" in zones_df.columns else 1.0
            for _, zone in zones_df.iterrows():
                pop = float(zone.get("population", 0.0))
                # Radius in meters scaled by population (100m - 1000m)
                radius = 100.0 + 900.0 * (pop / pop_max) if pop_max > 0 else 200.0
                map_data.append({
                    "lat": zone["center_lat"],
                    "lon": zone["center_lon"],
                    "zone_name": zone["zone_name"],
                    "population": pop,
                    "radius": radius,
                })
        except Exception as e:
            st.warning(f"Could not load population zones: {e}")
    
    # If no zones loaded, show center point
    if not map_data:
        map_data = [{"lat": lat, "lon": lon, "zone_name": "Center", "population": 0, "radius": 300.0}]
    
    df = pd.DataFrame(map_data)
    view_state = pdk.ViewState(latitude=lat, longitude=lon, zoom=11)
    base_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["lon", "lat"],
        get_radius="radius",
        get_color=[8, 189, 186, 160],
        pickable=True,
    )
    layers = [base_layer]

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state, 
        tooltip={"text": "Zone: {zone_name}\nPopulation: {population}"}
    )
    st.pydeck_chart(deck, use_container_width=True, key=f"disaster_map_{unique_key}")


def render_bubbles(severity: Dict[str, Any], planning_result: Dict[str, Any], unique_key: str = ""):
    # Fixed data access path
    zones = planning_result.get("evacuation", {}).get("routes", {}).get("routes", [])
    if not zones:
        st.info("Run the integration with planning to see evacuation route capacity bubbles.")
        return
    df = pd.DataFrame([
        {
            "from_lat": r.get("from_location", [0, 0])[1],
            "from_lon": r.get("from_location", [0, 0])[0],
            "to_lat": r.get("to_location", [0, 0])[1],
            "to_lon": r.get("to_location", [0, 0])[0],
            "distance_km": r.get("distance_km", 0),
            "capacity_per_hour": r.get("capacity_per_hour", 0),
        }
        for r in zones
    ])
    fig = px.scatter(
        df,
        x="distance_km",
        y="capacity_per_hour",
        size="capacity_per_hour",
        color="distance_km",
        title="Evacuation Route Capacity vs Distance",
    )
    st.plotly_chart(fig, use_container_width=True, key=f"evacuation_bubbles_{unique_key}")


def _render_badge(text: str, color: str = "gray") -> None:
    colors = {
        "green": "#2e7d32",
        "red": "#b71c1c",
        "orange": "#ef6c00",
        "blue": "#1565c0",
        "gray": "#455a64",
        "purple": "#6a1b9a",
    }
    hex_color = colors.get(color, color)
    st.markdown(
        f"<span style='display:inline-block;padding:4px 10px;border-radius:999px;background:{hex_color};color:white;font-size:12px;font-weight:600'>{text}</span>",
        unsafe_allow_html=True,
    )


def render_classification_panel(classification: Dict[str, Any]):
    st.subheader("Classification")
    if not classification:
        st.info("No classification available yet.")
        return

    top_cols = st.columns([1, 1, 1])
    with top_cols[0]:
        st.metric("Disaster Type", classification.get("disaster_type", "unknown"))
    with top_cols[1]:
        st.metric("Confidence", f"{classification.get('confidence_score', 0)*100:.0f}%")
    with top_cols[2]:
        sev = classification.get("severity_level", "unknown")
        sev_color = "red" if sev in ["high", "critical", "extreme"] else ("orange" if sev == "moderate" else "green")
        _render_badge(f"Severity: {sev}", sev_color)

    confirm_cols = st.columns([1, 2])
    with confirm_cols[0]:
        requires_conf = classification.get("requires_confirmation", False)
        _render_badge("Needs Confirmation" if requires_conf else "No Confirmation Needed", "orange" if requires_conf else "green")
    with confirm_cols[1]:
        if classification.get("risk_factors"):
            st.write("Risk Factors")
            st.markdown("\n".join([f"- {rf}" for rf in classification.get("risk_factors", [])]))

    if classification.get("recommendations"):
        st.write("Recommendations")
        st.markdown("\n".join([f"- {rec}" for rec in classification.get("recommendations", [])]))

    with st.expander("Raw classification JSON"):
        st.code(json.dumps(classification, indent=2), language="json")


def render_severity_panel(severity: Dict[str, Any]):
    st.subheader("Severity")
    if not severity:
        st.info("No severity information available yet.")
        return

    level = severity.get("severity_level", "unknown")
    score = float(severity.get("severity_score", 0.0))

    cols = st.columns([1, 1])
    with cols[0]:
        st.metric("Severity Level", level)
        st.metric("Severity Score", f"{score:.2f}")
    with cols[1]:
        st.write("Risk Score")
        st.progress(min(max(int(score * 100), 0), 100))

    # Gauge visualization for severity (0-100)
    try:
        gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=float(min(max(score * 100.0, 0.0), 100.0)),
                number={"suffix": "%", "font": {"size": 28}},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#b71c1c"},
                    "steps": [
                        {"range": [0, 33], "color": "#2e7d32"},
                        {"range": [33, 66], "color": "#ef6c00"},
                        {"range": [66, 100], "color": "#b71c1c"},
                    ],
                },
                title={"text": "Severity Gauge"},
            )
        )
        gauge.update_layout(height=240, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(gauge, use_container_width=True, key=f"sev_gauge_{int(time.time()*1000)}")
    except Exception:
        pass

    factors = severity.get("severity_factors", {})
    if factors:
        st.write("Key Factors")
        factors_df = pd.DataFrame({"factor": list(factors.keys()), "detail": list(factors.values())})
        st.dataframe(factors_df, use_container_width=True, hide_index=True)

    impact = severity.get("impact_assessment", {})
    if impact:
        st.write("Impact Assessment")
        impact_cols = st.columns(len(impact) or 1)
        for idx, (k, v) in enumerate(impact.items()):
            with impact_cols[idx % max(1, len(impact_cols))]:
                _render_badge(f"{k.replace('_',' ').title()}: {'Yes' if v else 'No'}", "red" if v else "gray")

    if severity.get("recommendations"):
        st.write("Actions")
        st.markdown("\n".join([f"- {rec}" for rec in severity.get("recommendations", [])]))

    with st.expander("Raw severity JSON"):
        st.code(json.dumps(severity, indent=2), language="json")


def render_monitoring_summary(monitoring: Dict[str, Any]):
    st.subheader("Monitoring Summary")
    if not monitoring:
        st.info("No monitoring summary available yet.")
        return
    cols = st.columns(3)
    with cols[0]:
        st.metric("Sources", monitoring.get("total_sources", 0))
    with cols[1]:
        st.metric("Total Alerts", monitoring.get("total_alerts", 0))
    with cols[2]:
        _render_badge(f"Polled: {monitoring.get('polled_at', 'n/a')}", "blue")


def render_deployment_timeline(planning_result: Dict[str, Any], unique_key: str = ""):
    """Show deployment arrival timeline analysis."""
    deployments = planning_result.get("deployments", {}).get("deployments", [])
    if not deployments:
        return
    
    df = pd.DataFrame(deployments)
    if "estimated_arrival_minutes" in df.columns:
        # Create timeline visualization
        fig = px.scatter(
            df, 
            x="estimated_arrival_minutes", 
            y="priority_level",
            color="priority_level",
            size=[10] * len(df),  # Uniform size
            title="Team Deployment Timeline",
            labels={"estimated_arrival_minutes": "ETA (minutes)", "priority_level": "Priority Level"}
        )
        st.plotly_chart(fig, use_container_width=True, key=f"deploy_timeline_{unique_key}")
        
        # ETA distribution
        eta_fig = px.histogram(
            df, 
            x="estimated_arrival_minutes", 
            nbins=20,
            title="Deployment ETA Distribution",
            labels={"estimated_arrival_minutes": "ETA (minutes)", "count": "Number of Teams"}
        )
        st.plotly_chart(eta_fig, use_container_width=True, key=f"eta_dist_{unique_key}")


def render_capacity_analysis(planning_result: Dict[str, Any], unique_key: str = ""):
    """Show evacuation capacity analysis."""
    routes = planning_result.get("evacuation", {}).get("routes", {}).get("routes", [])
    if not routes:
        return
    
    df = pd.DataFrame(routes)
    if "capacity_per_hour" in df.columns and "distance_km" in df.columns:
        # Capacity efficiency chart
        df["capacity_efficiency"] = df["capacity_per_hour"] / df["distance_km"]
        
        cols = st.columns(2)
        with cols[0]:
            # Total capacity by distance ranges
            df["distance_range"] = pd.cut(df["distance_km"], bins=5, labels=["Very Close", "Close", "Medium", "Far", "Very Far"])
            capacity_by_distance = df.groupby("distance_range")["capacity_per_hour"].sum().reset_index()
            
            fig = px.bar(
                capacity_by_distance,
                x="distance_range",
                y="capacity_per_hour",
                title="Evacuation Capacity by Distance Range",
                labels={"capacity_per_hour": "Total Capacity (people/hour)", "distance_range": "Distance Range"}
            )
            st.plotly_chart(fig, use_container_width=True, key=f"capacity_distance_{unique_key}")
        
        with cols[1]:
            # Capacity efficiency
            efficiency_fig = px.scatter(
                df,
                x="distance_km",
                y="capacity_efficiency",
                size="capacity_per_hour",
                title="Route Efficiency (Capacity/Distance)",
                labels={"distance_km": "Distance (km)", "capacity_efficiency": "Efficiency (people/hour/km)"}
            )
            st.plotly_chart(efficiency_fig, use_container_width=True, key=f"capacity_efficiency_{unique_key}")


def render_severity_breakdown(severity: Dict[str, Any], unique_key: str = ""):
    """Show detailed severity factor analysis."""
    if not severity:
        return
    
    severity_factors = severity.get("severity_factors", {})
    if severity_factors:
        # Create radar chart-like visualization using bar chart
        factors_df = pd.DataFrame([
            {"factor": k.replace("_", " ").title(), "description": v}
            for k, v in severity_factors.items()
        ])
        
        # Extract numeric values where possible
        import re
        factors_df["numeric_value"] = factors_df["description"].apply(
            lambda x: float(re.search(r'[\d,]+\.?\d*', str(x).replace(',', '')).group()) if re.search(r'[\d,]+\.?\d*', str(x).replace(',', '')) else 1
        )
        
        fig = px.bar(
            factors_df,
            x="factor",
            y="numeric_value",
            title="Severity Factors Analysis",
            labels={"numeric_value": "Impact Level", "factor": "Risk Factor"},
            hover_data=["description"]
        )
        fig.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig, use_container_width=True, key=f"severity_factors_{unique_key}")
        
        # Show impact assessment
        impact_assessment = severity.get("impact_assessment", {})
        if impact_assessment:
            st.write("**Impact Assessment**")
            impact_cols = st.columns(len(impact_assessment))
            for i, (key, value) in enumerate(impact_assessment.items()):
                with impact_cols[i]:
                    color = "red" if value else "green"
                    _render_badge(f"{key.replace('_', ' ').title()}: {'Yes' if value else 'No'}", color)


def render_population_impact(data: Dict[str, Any], unique_key: str = ""):
    """Show population impact analysis."""
    severity = data.get("detection_summary", {}).get("severity", {})
    if not severity:
        return
    
    # Population metrics
    population_at_risk = severity.get("population_at_risk", 0)
    affected_area = severity.get("affected_area_km2", 0)
    critical_infrastructure = severity.get("critical_infrastructure_count", 0)
    
    if population_at_risk > 0:
        cols = st.columns(3)
        with cols[0]:
            st.metric("Population at Risk", f"{population_at_risk:,}")
        with cols[1]:
            st.metric("Affected Area", f"{affected_area:,.1f} km²")
        with cols[2]:
            st.metric("Critical Infrastructure", critical_infrastructure)
        
        # Population density impact
        if affected_area > 0:
            density = population_at_risk / affected_area
            st.metric("Population Density", f"{density:,.0f} people/km²")
            
            # Create impact visualization
            impact_data = [
                {"category": "Population at Risk", "value": population_at_risk},
                {"category": "Safe Population (Est.)", "value": max(0, population_at_risk * 0.3)},  # Estimated
                {"category": "Critical Infrastructure", "value": critical_infrastructure * 10000}  # Scale for visualization
            ]
            
            impact_df = pd.DataFrame(impact_data)
            fig = px.pie(
                impact_df,
                values="value",
                names="category",
                title="Impact Distribution",
            )
            st.plotly_chart(fig, use_container_width=True, key=f"population_impact_{unique_key}")


def render_routes_distribution(planning_result: Dict[str, Any], unique_key: str = ""):
    # Fixed data access path
    routes: List[Dict[str, Any]] = planning_result.get("evacuation", {}).get("routes", {}).get("routes", [])
    if not routes:
        st.info("No evacuation routes planned yet.")
        return
    df = pd.DataFrame([
        {
            "distance_km": r.get("distance_km", 0.0),
            "capacity_per_hour": r.get("capacity_per_hour", 0.0),
        }
        for r in routes
    ])
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.histogram(df, x="distance_km", nbins=30, title="Route Distance Distribution"), use_container_width=True, key=f"route_dist_{unique_key}")
    with c2:
        st.plotly_chart(px.histogram(df, x="capacity_per_hour", nbins=30, title="Route Capacity Distribution"), use_container_width=True, key=f"route_cap_{unique_key}")


def render_deployments(planning_result: Dict[str, Any], unique_key: str = ""):
    # Fixed data access path  
    deployments = planning_result.get("deployments", {}).get("deployments", [])
    if not deployments:
        st.info("No deployments generated yet.")
        return
    df = pd.DataFrame(deployments)
    # Metrics
    cols = st.columns(3)
    with cols[0]:
        st.metric("Total Deployments", len(df))
    with cols[1]:
        if "estimated_arrival_minutes" in df.columns:
            st.metric("Median ETA (min)", int(df["estimated_arrival_minutes"].median()))
    with cols[2]:
        st.metric("Priority Levels", df.get("priority_level", pd.Series(dtype=str)).nunique())

    # Priority distribution
    if "priority_level" in df.columns:
        pr_df = df["priority_level"].value_counts().reset_index()
        pr_df.columns = ["priority", "count"]
        st.plotly_chart(px.bar(pr_df, x="priority", y="count", title="Deployments by Priority"), use_container_width=True, key=f"dep_prio_{unique_key}")

    # Table preview
    view_cols = [c for c in ["team_id", "target_zone_id", "priority_level", "estimated_arrival_minutes", "coordination_instructions"] if c in df.columns]
    st.dataframe(df[view_cols].head(25), use_container_width=True)


def _run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)


def run_detection_only(lat: float, lon: float, radius_km: float, location_name: str, watsonx_config: Dict[str, Any], situation_description: str | None) -> Dict[str, Any]:
    detector = DetectionReActAdapter()
    result = _run_async(
        detector.run(
            lat=lat,
            lon=lon,
            radius_km=radius_km,
            location_name=location_name,
            watsonx_config=watsonx_config,
            situation_description=situation_description,
        )
    )
    return {
        "management_phase": "monitoring_only",
        "planning_triggered": False,
        "detection_summary": {
            "event_detected": bool(result.get("classification", {}).get("threat_detected", False)),
            "classification": result.get("classification", {}),
            "severity": result.get("severity", {}),
            "monitoring": result.get("monitoring_summary", {}),
        },
        "session_id": f"orch_{int(time.time())}",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def run_complete_response(lat: float, lon: float, radius_km: float, location_name: str, watsonx_config: Dict[str, Any], situation_description: str | None) -> Dict[str, Any]:
    manager = IntegratedOrchestratorManagement()
    results = _run_async(
        manager.run_complete_disaster_management(
            monitoring_regions=[{
                "name": location_name,
                "center_lat": lat,
                "center_lon": lon,
                "radius_km": radius_km,
            }],
            session_id=f"orch_{int(time.time())}",
            config={"watsonx_config": watsonx_config},
            situation_description=situation_description,
        )
    )
    return results


def summarize_for_chat(results: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    ds = results.get("detection_summary", {})
    c = ds.get("classification", {})
    s = ds.get("severity", {})
    lines.append(f"Threat: {'YES' if c.get('threat_detected') else 'NO'} | Type: {c.get('disaster_type','unknown')} | Confidence: {c.get('confidence_score',0):.2f} | Severity: {c.get('severity_level','low')}")
    if c.get("risk_factors"):
        lines.append("Risk Factors: " + ", ".join(c.get("risk_factors", [])[:3]))
    if s:
        lines.append(f"Severity Score: {s.get('severity_score', 0)} | Population At Risk: {s.get('population_at_risk', 0):,} | Critical Infra: {s.get('critical_infrastructure_count', 0)}")
        if s.get("recommendations"):
            lines.append("Actions: " + ", ".join(s.get("recommendations", [])[:3]))
    ps = results.get("planning_summary", {})
    if ps:
        lines.append(f"Planning: deployments={ps.get('deployments_created', 0)}, routes={ps.get('routes', 0)}")
    return lines


def summarize_with_watsonx(results: Dict[str, Any], model_id: str, watsonx_config: Dict[str, Any]) -> str:
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
        llm = WatsonxLLM(
            model_id=model_id,
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


def summarize_key_data(data: Dict[str, Any]):
    """Show high-level summary at the top of the right panel."""
    st.subheader("Executive Summary")
    
    cols = st.columns(4)
    with cols[0]:
        st.metric("Management Phase", data.get("management_phase", "unknown"))
    with cols[1]:
        _render_badge("Planning Active" if data.get("planning_triggered") else "Detection Only", 
                      "green" if data.get("planning_triggered") else "orange")
    with cols[2]:
        st.metric("Session", data.get("session_id", "unknown"))
    with cols[3]:
        ts = data.get("timestamp", "unknown")
        st.metric("Timestamp", ts if len(ts) < 12 else ts[:10])

    # Show detection results
    ds = data.get("detection_summary", {})
    if ds:
        classification = ds.get("classification", {})
        severity = ds.get("severity", {})
        if classification or severity:
            st.divider()
            render_classification_panel(classification)
            render_severity_panel(severity)
            render_monitoring_summary(ds.get("monitoring", {}))


def render_kpi_row(data: Dict[str, Any]) -> None:
    """Premium KPI row with emoji and styled metric cards."""
    ds = data.get("detection_summary", {})
    c = ds.get("classification", {})
    s = ds.get("severity", {})
    ps = data.get("planning_summary", {}) or {}
    pr = data.get("planning_result", {}) or {}

    # Derive counts from either summary or result
    routes_list = pr.get("evacuation", {}).get("routes", {}).get("routes", [])
    deployments_list = pr.get("deployments", {}).get("deployments", [])
    routes_count = ps.get("routes") if isinstance(ps.get("routes"), int) else len(routes_list)
    deployments_count = ps.get("deployments_created") if isinstance(ps.get("deployments_created"), int) else len(deployments_list)

    cols = st.columns(4)
    with cols[0]:
        st.metric("Phase", data.get("management_phase", "unknown"))
    with cols[1]:
        st.metric("Threat", "YES" if c.get("threat_detected") else "NO", delta=f"conf {int(c.get('confidence_score',0)*100)}%")
    with cols[2]:
        sev_score = float(s.get("severity_score", 0.0))
        st.metric("Severity", s.get("severity_level", "low").title(), delta=f"score {int(sev_score*100)}%")
    with cols[3]:
        st.metric("Operations", f"{deployments_count} deploy | {routes_count} routes")


def render_hero_header(data: Dict[str, Any]) -> None:
    ds = data.get("detection_summary", {})
    c = ds.get("classification", {})
    s = ds.get("severity", {})
    threat = "YES" if c.get("threat_detected") else "NO"
    sev = s.get("severity_level", "unknown").title()
    dtype = c.get("disaster_type", "Unknown").title()
    st.markdown(
        f"""
        <div class='aw-hero'>
            <h2>ArkWatson Situation Overview</h2>
            <div style='display:flex;gap:8px;flex-wrap:wrap;margin-top:6px;'>
                <span class='aw-badge aw-primary'>Type: {dtype}</span>
                <span class='aw-badge aw-danger'>Severity: {sev}</span>
                <span class='aw-badge aw-success'>Threat: {threat}</span>
                <span class='aw-badge aw-magenta'>Session: {data.get('session_id','n/a')}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_safe_zones_and_teams(data: Dict[str, Any]):
    """Show safe zones map and team deployments."""
    st.subheader("Geographic Overview")
    
    ds = data.get("detection_summary", {})
    classification = ds.get("classification", {})
    monitoring = ds.get("monitoring", {})
    
    # Show map
    if classification or monitoring:
        render_map(classification, monitoring, unique_key=data.get("session_id", "default"))
    
    # Show planning results if available  
    ps = data.get("planning_summary", {})
    if ps:
        st.divider()
        st.subheader("Response Planning")
        render_deployments(ps, unique_key=data.get("session_id", "default"))
        
        st.divider()
        st.subheader("Evacuation Analysis")
        render_routes_distribution(ps, unique_key=data.get("session_id", "default"))
        render_bubbles(ds.get("severity", {}), ps, unique_key=data.get("session_id", "default"))


def show_workflow_summary(data: Dict[str, Any]):
    """Show workflow execution timeline and results."""
    # Show watsonx summary if available
    watsonx_summary = data.get("watsonx_summary")
    if watsonx_summary:
        st.write("**AI Executive Summary:**")
        st.markdown(watsonx_summary)
    else:
        # Fallback to deterministic summary
        lines = summarize_for_chat(data)
        if lines:
            st.write("**Key Results:**")
            for line in lines:
                st.markdown(f"- {line}")


def render_chat_controls():
    """Render the chat interface controls (form elements)."""
    st.subheader("Chat-Orchestrate")
    
    # Initialize messages in session state
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Form controls (created once, outside refresh loop)
    model_id = st.selectbox(
        "Granite model",
        options=[
            "ibm/granite-3-8b-instruct",
            "ibm/granite-3-3-8b-instruct",
            "ibm/granite-13b-instruct-v2",
            "ibm/granite-13b-chat-v2",
            "ibm/granite-20b-multilingual",
        ],
        index=1,
        help="Model used for classification and final summary",
        key="granite_model_selector"
    )
    
    mode = st.radio(
        "Workflow",
        options=["Detection (ReAct)", "Complete Response (Plan-Act)"],
        index=1,
        horizontal=False,
        key="workflow_mode_selector"
    )
    
    region = st.text_input("Region", value="San Francisco Bay Area", key="region_input")
    lat = st.number_input("Lat", value=37.7749, format="%0.6f", key="lat_input")
    lon = st.number_input("Lon", value=-122.4194, format="%0.6f", key="lon_input")
    radius = st.number_input("Radius (km)", value=100.0, step=10.0, key="radius_input")
    
    with st.expander("Watsonx configuration"):
        api_key = st.text_input("API key", value=os.environ.get("WATSONX_APIKEY", ""), type="password", key="watsonx_api_key")
        url = st.text_input("URL", value=os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com"), key="watsonx_url")
        project_id = st.text_input("Project ID", value=os.environ.get("WATSONX_PROJECT_ID", ""), key="watsonx_project_id")

    return {
        "model_id": model_id,
        "mode": mode,
        "region": region,
        "lat": lat,
        "lon": lon,
        "radius": radius,
        "api_key": api_key,
        "url": url,
        "project_id": project_id
    }


def render_chat_interface(config: Dict[str, Any]):
    """Render the chat messages and input."""
    # Display chat messages
    for msg in st.session_state["messages"]:
        st.chat_message(msg["role"]).markdown(msg["content"])

    # Chat input
    prompt = st.chat_input("Describe the situation or ask to run a new analysis…", key="chat_input")
    if prompt:
        st.session_state["messages"].append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)

        with st.chat_message("assistant"):
            st.write("Running workflow…")
            watsonx_cfg = {
                "api_key": config["api_key"], 
                "url": config["url"], 
                "project_id": config["project_id"], 
                "model_id": config["model_id"]
            }
            
            if config["mode"].startswith("Detection"):
                results = run_detection_only(
                    config["lat"], config["lon"], float(config["radius"]), 
                    config["region"], watsonx_cfg, prompt
                )
            else:
                results = run_complete_response(
                    config["lat"], config["lon"], float(config["radius"]), 
                    config["region"], watsonx_cfg, prompt
                )

            # Persist results so right-hand visualizations update
            st.session_state["latest_results"] = results

            # Stage summaries
            for line in summarize_for_chat(results):
                st.markdown(f"- {line}")

            # Final LLM summary
            st.markdown("\n**Model Summary**")
            final_summary = summarize_with_watsonx(results, config["model_id"], watsonx_cfg)
            st.markdown(final_summary)
            st.session_state["messages"].append({"role": "assistant", "content": "\n".join(summarize_for_chat(results)) + "\n\n" + final_summary})


def render_status_panel():
    """Render the status panel showing current system state."""
    data = st.session_state.get("latest_results") or load_latest_results()
    if not data:
        return
    
    st.subheader("Status")
    st.metric("Phase", data.get("management_phase", "unknown"))
    st.metric("Planning Triggered", str(data.get("planning_triggered", False)))
    st.write("Session:", data.get("session_id"))
    st.write("Timestamp:", data.get("timestamp"))

    ds = data.get("detection_summary", {})
    classification = ds.get("classification", {})
    render_classification_panel(classification)

    severity = ds.get("severity", {})
    render_severity_panel(severity)

    monitoring = ds.get("monitoring", {})
    render_monitoring_summary(monitoring)


def render_data_display():
    """Render the data visualization panel (refreshing content)."""
    data = st.session_state.get("latest_results") or load_latest_results()
    if not data:
        st.info("No integrated results found yet. Run demo_orchestrator_integration.py to generate outputs.")
        return
    
    # Create unique key for this refresh cycle
    unique_key = str(int(time.time() * 1000))  # Use millisecond timestamp
    
    # Hero + KPI row
    render_hero_header(data)
    render_kpi_row(data)

    ds = data.get("detection_summary", {})
    classification = ds.get("classification", {})
    monitoring = ds.get("monitoring", {})
    planning_result = data.get("planning_result", {})
    severity = ds.get("severity", {})

    tab_overview, tab_map, tab_planning, tab_risk, tab_timeline, tab_raw = st.tabs([
        "Overview", "Map", "Planning", "Risk", "Timeline", "Raw"
    ])

    with tab_overview:
        summarize_key_data(data)

    with tab_map:
        render_map(classification, monitoring, unique_key)

    with tab_planning:
        st.subheader("Routes & Deployments")
        render_routes_distribution(planning_result, unique_key)
        render_deployments(planning_result, unique_key)
        st.divider()
        st.subheader("Evacuation Capacity Bubbles")
        render_bubbles(severity, planning_result, unique_key)
        st.divider()
        st.subheader("Deployment Analysis")
        render_deployment_timeline(planning_result, unique_key)
        render_capacity_analysis(planning_result, unique_key)

    with tab_risk:
        render_severity_breakdown(severity, unique_key)
        render_population_impact(data, unique_key)

    with tab_timeline:
        show_workflow_summary(data)

    with tab_raw:
        with st.expander("View JSON", expanded=True):
            st.json(data, expanded=False)


def main():
    st.title("ArkWatson - Disaster Operations Center")
    st.caption("Live monitoring, classification, and response planning dashboard")
    inject_global_styles()

    # Configure sidebar controls
    auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True, key="auto_refresh_checkbox")
    refresh_sec = st.sidebar.slider("Refresh interval (sec)", 5, 60, 10, key="refresh_interval_slider")

    # Create layout with two columns
    left_col, right_col = st.columns([1, 2])
    
    # Left column: Chat controls (static, no refresh)
    with left_col:
        config = render_chat_controls()
        render_chat_interface(config)
        render_status_panel()
    
    # Right column: Data display (with optional auto-refresh)
    with right_col:
        if auto_refresh:
            # Auto-refreshing content
            placeholder = st.empty()
            while True:
                with placeholder.container():
                    render_data_display()
                time.sleep(refresh_sec)
        else:
            # Static content when auto-refresh is off
            render_data_display()


if __name__ == "__main__":
    main()