"""
Integrated disaster management using IBM watsonx Orchestrator agent styles.

This module bypasses LangGraph and runs:
- Detection via a ReAct-style adapter (poll → classify → confirm → assess)
- Planning via a Plan-Act-style adapter (deployments → routes → capacity)

It is intended as an alternative runner for environments adopting Orchestrator.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd

from ..core.state import ResponseTeam, PopulationZone
from ..orchestrator.adapters import DetectionReActAdapter, PlanningPlanActAdapter


logger = logging.getLogger(__name__)


class IntegratedOrchestratorManagement:
    """Alternative integrated workflow using Orchestrator-style agents."""

    def __init__(self):
        self._detection = DetectionReActAdapter()
        self._planning = PlanningPlanActAdapter()

    async def run_complete_disaster_management(
        self,
        monitoring_regions: List[Dict[str, Any]],
        session_id: str,
        config: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Run detection (ReAct) and planning (Plan-Act) using local adapters.

        Args:
            monitoring_regions: List with at least one region dict having keys
                name, center_lat, center_lon, radius_km
            session_id: Unique session identifier
            config: Optional configuration (provides watsonx_config)

        Returns:
            Dict with detection and, if triggered, planning summaries
        """
        if not monitoring_regions:
            return {"error": "No monitoring regions provided", "session_id": session_id}

        region = monitoring_regions[0]
        lat = float(region.get("center_lat", 40.7128))
        lon = float(region.get("center_lon", -74.0060))
        radius_km = float(region.get("radius_km", 100))
        location_name = region.get("name", "monitored area")

        watsonx_config = (config or {}).get("watsonx_config", {})

        logger.info("Orchestrator: running detection (ReAct)")
        detection = await self._detection.run(
            lat=lat,
            lon=lon,
            radius_km=radius_km,
            location_name=location_name,
            watsonx_config=watsonx_config,
        )

        classification = detection.get("classification", {})
        severity = detection.get("severity", {})
        threat_detected = bool(classification.get("threat_detected", False))
        severity_level = classification.get("severity_level", "low")
        escalate = severity.get("escalation_required", False) or severity_level in [
            "high",
            "critical",
            "extreme",
        ]

        if not threat_detected:
            logger.info("Orchestrator: no threat detected; returning detection-only result")
            return {
                "management_phase": "monitoring_only",
                "planning_triggered": False,
                "detection_summary": {
                    "event_detected": False,
                    "classification": classification,
                    "severity": severity,
                    "monitoring": detection.get("monitoring_summary", {}),
                },
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
            }

        if not escalate:
            logger.info("Orchestrator: moderate severity; returning detection summary without planning")
            return {
                "management_phase": "monitoring_only",
                "planning_triggered": False,
                "detection_summary": {
                    "event_detected": True,
                    "classification": classification,
                    "severity": severity,
                    "monitoring": detection.get("monitoring_summary", {}),
                },
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
            }

        # Planning required
        logger.info("Orchestrator: running planning (Plan-Act)")
        teams, zones, centers = self._load_planning_inputs()

        planning = await self._planning.run(
            disaster_type=classification.get("disaster_type", "unknown"),
            severity_level=severity_level,
            teams_data=teams,
            population_zones=zones,
            evacuation_centers=centers,
        )

        return {
            "management_phase": "complete_response",
            "planning_triggered": True,
            "detection_summary": {
                "event_detected": True,
                "classification": classification,
                "severity": severity,
                "monitoring": detection.get("monitoring_summary", {}),
            },
            "planning_summary": {
                "deployments_created": len(planning.get("deployments", {}).get("deployments", [])),
                "routes": planning.get("evacuation", {}).get("routes", {}).get("total_routes", 0),
            },
            "planning_result": planning,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
        }

    def _load_planning_inputs(self) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]], list[Dict[str, Any]]]:
        """Load teams, population zones, and evacuation centers from CSVs."""
        data_dir = Path(__file__).parent.parent.parent / "data"

        teams: list[Dict[str, Any]] = []
        zones: list[Dict[str, Any]] = []
        centers: list[Dict[str, Any]] = []

        try:
            teams_path = data_dir / "response_teams.csv"
            if teams_path.exists():
                teams_df = pd.read_csv(teams_path)
                for _, row in teams_df.iterrows():
                    teams.append(
                        {
                            "team_id": row.get("team_id"),
                            "team_name": row.get("team_name"),
                            "team_type": row.get("team_type"),
                            "specialization": row.get("specialization"),
                            "capacity": int(row.get("capacity", 0)),
                            "response_time_minutes": int(row.get("response_time_minutes", 15)),
                            "equipment_level": row.get("equipment_level", "medium"),
                            "base_lat": float(row.get("base_lat", 0.0)),
                            "base_lon": float(row.get("base_lon", 0.0)),
                            "availability_status": row.get("availability_status", "available"),
                        }
                    )
        except Exception as e:
            logger.warning(f"Could not load teams CSV: {e}")

        try:
            zones_path = data_dir / "population_zones.csv"
            if zones_path.exists():
                zones_df = pd.read_csv(zones_path)
                for _, row in zones_df.iterrows():
                    zones.append(
                        {
                            "zone_id": row.get("zone_id"),
                            "zone_name": row.get("zone_name"),
                            "center_lat": float(row.get("center_lat", 0.0)),
                            "center_lon": float(row.get("center_lon", 0.0)),
                            "radius_km": float(row.get("radius_km", 0.0)),
                            "population": int(row.get("population", 0)),
                            "population_density_per_km2": int(row.get("population_density_per_km2", 0)),
                            "vulnerability_score": row.get("vulnerability_score", "medium"),
                            "demographics": row.get("demographics", ""),
                            "special_needs_population": int(row.get("special_needs_population", 0)),
                        }
                    )
        except Exception as e:
            logger.warning(f"Could not load population zones CSV: {e}")

        try:
            centers_path = data_dir / "evacuation_zones.csv"
            if centers_path.exists():
                centers_df = pd.read_csv(centers_path)
                centers = centers_df.to_dict("records")
        except Exception as e:
            logger.warning(f"Could not load evacuation centers CSV: {e}")

        return teams, zones, centers


__all__ = ["IntegratedOrchestratorManagement"]


