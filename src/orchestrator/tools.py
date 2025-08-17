"""
Python tools compatible with IBM watsonx Orchestrator agent builder.

These wrap existing functionality from monitoring and planning modules so the
agents (ReAct for detection, Plan-Act for planning) can call them as tools.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any

from langchain_core.tools import tool

from monitoring.api_clients import DisasterMonitoringService, predict_disaster_risk
from monitoring.watsonx_agents import (
    watsonx_disaster_classifier,
    web_search_disaster_confirmation,
    severity_impact_analyzer,
    safe_zone_identifier,
)
from monitoring.planning_agents import (
    watsonx_team_deployment_optimizer,
    osrm_route_planner,
    evacuation_capacity_optimizer,
)


logger = logging.getLogger(__name__)


@tool(return_direct=True)
def poll_monitoring_sources(lat: float, lon: float, radius_km: float = 100) -> str:
    """
    Poll USGS, NOAA, FEMA, NASA, OSM for monitoring signals near a location.

    Returns: JSON with a list of MonitoringData-like dicts and simple summary.
    """
    async def _run() -> Dict[str, Any]:
        async with DisasterMonitoringService() as svc:
            responses = await svc.poll_all_sources(lat, lon, radius_km)
            data = svc.convert_to_monitoring_data(responses)
            return {
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
                },
            }

    try:
        # Execute nested coroutine in a best-effort way for tool sync interface
        import asyncio

        result = asyncio.run(_run())
        return json.dumps(result)
    except RuntimeError:
        # Already inside an event loop; create task and gather
        import asyncio

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_run())
        return json.dumps(result)
    except Exception as e:
        logger.error(f"poll_monitoring_sources error: {e}")
        return json.dumps({"error": str(e)})


# Re-export existing tools under Orchestrator-friendly names

@tool(return_direct=True)
def classify_disaster_with_watsonx(monitoring_data_json: str, location_json: str, watsonx_config: Dict[str, str], situation_description: str | None = None) -> str:
    """
    Classify potential disasters using watsonx AI based on monitoring data.
    
    Args:
        monitoring_data_json: JSON string containing monitoring signals
        location_json: JSON string with location information
        watsonx_config: Configuration dictionary for watsonx service
        
    Returns: JSON string with disaster classification results
    """
    return watsonx_disaster_classifier.invoke({  # type: ignore
        "monitoring_data_json": monitoring_data_json,
        "location_json": location_json,
        "watsonx_config": watsonx_config,
        "situation_description": situation_description or "",
    })


@tool(return_direct=True)
def confirm_disaster_via_web(disaster_type: str, location_name: str, severity_level: str, time_window: str = "24h") -> str:
    """
    Confirm disaster occurrence through web search and news sources.
    
    Args:
        disaster_type: Type of disaster to confirm
        location_name: Name of the affected location
        severity_level: Expected severity level
        time_window: Time window for search (default: "24h")
        
    Returns: JSON string with confirmation results
    """
    return web_search_disaster_confirmation.invoke({  # type: ignore
        "disaster_type": disaster_type,
        "location_name": location_name,
        "severity_level": severity_level,
        "time_window": time_window,
    })


@tool(return_direct=True)
def assess_severity(disaster_type: str, magnitude_or_intensity: str, affected_area_km2: float, population_density: int, critical_infrastructure_count: int) -> str:
    """
    Assess disaster severity and potential impact.
    
    Args:
        disaster_type: Type of disaster
        magnitude_or_intensity: Magnitude or intensity measurement
        affected_area_km2: Affected area in square kilometers
        population_density: Population density in affected area
        critical_infrastructure_count: Number of critical infrastructure elements
        
    Returns: JSON string with severity assessment
    """
    return severity_impact_analyzer.invoke({  # type: ignore
        "disaster_type": disaster_type,
        "magnitude_or_intensity": magnitude_or_intensity,
        "affected_area_km2": affected_area_km2,
        "population_density": population_density,
        "critical_infrastructure_count": critical_infrastructure_count,
    })


@tool(return_direct=True)
def identify_safe_zones(affected_area_geojson: str, infrastructure_data_json: str, disaster_type: str, evacuation_radius_km: float = 10.0) -> str:
    """
    Identify safe zones for evacuation based on disaster type and infrastructure.
    
    Args:
        affected_area_geojson: GeoJSON string of affected area
        infrastructure_data_json: JSON string with infrastructure data
        disaster_type: Type of disaster
        evacuation_radius_km: Evacuation radius in kilometers (default: 10.0)
        
    Returns: JSON string with safe zone locations
    """
    return safe_zone_identifier.invoke({  # type: ignore
        "affected_area_geojson": affected_area_geojson,
        "infrastructure_data_json": infrastructure_data_json,
        "disaster_type": disaster_type,
        "evacuation_radius_km": evacuation_radius_km,
    })


@tool(return_direct=True)
def plan_team_deployments(disaster_type: str, severity_level: str, teams_data_json: str, population_zones_json: str, watsonx_config: Dict[str, str]) -> str:
    """
    Optimize emergency team deployments using watsonx AI.
    
    Args:
        disaster_type: Type of disaster
        severity_level: Severity level of disaster
        teams_data_json: JSON string with available teams data
        population_zones_json: JSON string with population zone information
        watsonx_config: Configuration dictionary for watsonx service
        
    Returns: JSON string with optimized deployment plan
    """
    return watsonx_team_deployment_optimizer.invoke({  # type: ignore
        "disaster_type": disaster_type,
        "severity_level": severity_level,
        "teams_data_json": teams_data_json,
        "population_zones_json": population_zones_json,
        "watsonx_config": watsonx_config,
    })


@tool(return_direct=True)
def plan_routes(from_locations_json: str, to_locations_json: str, route_type: str = "driving", alternatives: bool = True) -> str:
    """
    Plan optimal routes between locations using OSRM routing service.
    
    Args:
        from_locations_json: JSON string with origin locations
        to_locations_json: JSON string with destination locations
        route_type: Type of routing (default: "driving")
        alternatives: Whether to include alternative routes (default: True)
        
    Returns: JSON string with route plans
    """
    return osrm_route_planner.invoke({  # type: ignore
        "from_locations_json": from_locations_json,
        "to_locations_json": to_locations_json,
        "route_type": route_type,
        "alternatives": alternatives,
    })


@tool(return_direct=True)
def optimize_evacuation_capacity(population_zones_json: str, evacuation_centers_json: str, routes_json: str) -> str:
    """
    Optimize evacuation capacity allocation across centers and routes.
    
    Args:
        population_zones_json: JSON string with population zone data
        evacuation_centers_json: JSON string with evacuation center information
        routes_json: JSON string with available routes
        
    Returns: JSON string with optimized capacity allocation
    """
    return evacuation_capacity_optimizer.invoke({  # type: ignore
        "population_zones_json": population_zones_json,
        "evacuation_centers_json": evacuation_centers_json,
        "routes_json": routes_json,
    })


__all__ = [
    "poll_monitoring_sources",
    "classify_disaster_with_watsonx",
    "confirm_disaster_via_web",
    "assess_severity",
    "identify_safe_zones",
    "plan_team_deployments",
    "plan_routes",
    "optimize_evacuation_capacity",
]

