"""
Local adapters to run Orchestrator-style agents (ReAct / Plan-Act) in-process.

These provide a bridge so existing tests and demos can execute agent logic
without needing the Orchestrator control plane. They call tools in a
deterministic sequence that mirrors the agent styles.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List

from .tools import (
    classify_disaster_with_watsonx,
    confirm_disaster_via_web,
    assess_severity,
    identify_safe_zones,
    plan_team_deployments,
    plan_routes,
    optimize_evacuation_capacity,
)
from monitoring.api_clients import DisasterMonitoringService


logger = logging.getLogger(__name__)


class DetectionReActAdapter:
    """Simulates a ReAct-style agent for detection."""

    async def run(self, lat: float, lon: float, radius_km: float, location_name: str, watsonx_config: Dict[str, str], situation_description: str | None = None) -> Dict[str, Any]:
        # Think: poll monitoring sources (run async directly to avoid nested event loops)
        async with DisasterMonitoringService() as svc:
            responses = await svc.poll_all_sources(lat, lon, radius_km)
            data = svc.convert_to_monitoring_data(responses)
        monitoring = {
            "monitoring_data": [
                {
                    "source": d.source.value,
                    "timestamp": d.timestamp.isoformat(),
                    "alerts_count": d.alerts_count,
                    "data": d.data,
                    "location_bounds": d.location_bounds,
                }
                for d in data
            ],
            "summary": {
                "total_sources": len(data),
                "total_alerts": sum(d.alerts_count for d in data),
                "polled_at": datetime.now().isoformat(),
                "center_lat": lat,
                "center_lon": lon,
                "radius_km": radius_km,
                "location_name": location_name,
            },
        }

        # Act: classify
        monitoring_data_json = json.dumps([
            {
                "source": d.get("source"),
                "timestamp": d.get("timestamp"),
                "alerts_count": d.get("alerts_count"),
                "data_summary": str(d.get("data"))[:500],
            }
            for d in monitoring.get("monitoring_data", [])
        ])
        location_json = json.dumps({"lat": lat, "lon": lon})
        classification_json = classify_disaster_with_watsonx.invoke({
            "monitoring_data_json": monitoring_data_json,
            "location_json": location_json,
            "watsonx_config": watsonx_config,
            "situation_description": situation_description or "",
        })
        classification = json.loads(classification_json)

        # Observe/Think: confirm if needed
        confirmation = None
        # Skip confirmation if ongoing is indicated
        if classification.get("requires_confirmation") and not classification.get("ongoing", False):
            confirmation_json = confirm_disaster_via_web.invoke({
                "disaster_type": classification.get("disaster_type", "unknown"),
                "location_name": location_name,
                "severity_level": classification.get("severity_level", "low"),
                "time_window": "24h",
            })
            confirmation = json.loads(confirmation_json)

        # Act: assess severity
        severity_json = assess_severity.invoke({
            "disaster_type": classification.get("disaster_type", "unknown"),
            "magnitude_or_intensity": "5.0",
            "affected_area_km2": float(radius_km) ** 2 * 3.14159,
            "population_density": 1000,
            "critical_infrastructure_count": 5,
        })
        severity = json.loads(severity_json)

        return {
            "monitoring_summary": monitoring.get("summary", {}),
            "classification": classification,
            "confirmation": confirmation,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
        }


class PlanningPlanActAdapter:
    """Simulates a Plan-Act-style agent for planning."""

    async def run(
        self,
        disaster_type: str,
        severity_level: str,
        teams_data: List[Dict[str, Any]],
        population_zones: List[Dict[str, Any]],
        evacuation_centers: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        # Plan step 1: team deployments
        deployments_json = plan_team_deployments.invoke({
            "disaster_type": disaster_type,
            "severity_level": severity_level,
            "teams_data_json": json.dumps(teams_data),
            "population_zones_json": json.dumps(population_zones),
            "watsonx_config": {},
        })
        deployments = json.loads(deployments_json)

        # Plan step 2: routing
        from_locations = [
            [z.get("center_lon", 0), z.get("center_lat", 0)] for z in population_zones
        ]
        to_locations = [
            [c.get("lon", 0), c.get("lat", 0)] for c in evacuation_centers
        ]
        routes_json = plan_routes.invoke({
            "from_locations_json": json.dumps(from_locations),
            "to_locations_json": json.dumps(to_locations),
            "route_type": "driving",
            "alternatives": True,
        })
        routes = json.loads(routes_json)

        # Plan step 3: capacity optimization
        capacity_json = optimize_evacuation_capacity.invoke({
            "population_zones_json": json.dumps(population_zones),
            "evacuation_centers_json": json.dumps(evacuation_centers),
            "routes_json": json.dumps(routes),
        })
        capacity = json.loads(capacity_json)

        return {
            "deployments": deployments,
            "evacuation": {"routes": routes, "capacity": capacity},
            "resources": {
                "teams": len(teams_data),
                "zones": len(population_zones),
                "centers": len(evacuation_centers),
            },
            "summary": {
                "total_deployments": len(deployments.get("deployments", [])),
                "total_routes": len(routes.get("routes", [])),
            },
        }


__all__ = [
    "DetectionReActAdapter",
    "PlanningPlanActAdapter",
]


