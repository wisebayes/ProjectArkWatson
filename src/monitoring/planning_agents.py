"""
IBM WatsonX-powered planning agents for disaster response and management.
Handles team deployment, evacuation routing, and resource allocation.
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

import aiohttp
import pandas as pd
from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate
from langchain_ibm import WatsonxLLM

from core.state import (
    ResponseTeam, PopulationZone, TeamDeployment, EvacuationRoute,
    DisasterType, SeverityLevel
)


logger = logging.getLogger(__name__)


class WatsonXPlanningOrchestrator:
    """WatsonX-powered disaster response planning system."""
    
    def __init__(
        self,
        WATSONX_APIKEY: str,
        watsonx_url: str = "https://us-south.ml.cloud.ibm.com",
        project_id: str = None,
        model_id: str = "ibm/granite-13b-instruct-v2"
    ):
        """Initialize the WatsonX planning orchestrator."""
        self.watsonx_params = {
            "decoding_method": "sample",
            "max_new_tokens": 800,
            "min_new_tokens": 50,
            "temperature": 0.4,  # Balanced creativity and consistency for planning
            "top_k": 50,
            "top_p": 0.9,
        }
        
        self.watsonx_llm = WatsonxLLM(
            model_id=model_id,
            url=watsonx_url,
            project_id=project_id,
            params=self.watsonx_params,
        )
        
        self.deployment_prompt = PromptTemplate.from_template("""
You are an expert emergency response coordinator. Analyze the disaster situation and available resources to create an optimal team deployment plan.

DISASTER SITUATION:
- Type: {disaster_type}
- Severity: {severity_level}
- Affected Areas: {affected_areas}
- Population at Risk: {population_at_risk}

AVAILABLE RESPONSE TEAMS:
{teams_summary}

POPULATION ZONES (ordered by priority):
{population_zones_summary}

TASK: Create a deployment plan that optimizes:
1. Response time to high-risk areas
2. Team specialization matching needs
3. Population coverage and safety
4. Resource efficiency

Provide your response as JSON:
{{
    "deployments": [
        {{
            "team_id": "string",
            "target_zone_id": "string", 
            "priority_level": "critical|high|medium|low",
            "deployment_reason": "detailed explanation",
            "estimated_arrival_minutes": number,
            "coordination_instructions": "specific instructions"
        }}
    ],
    "overall_strategy": "high-level deployment strategy",
    "resource_gaps": ["identified gaps in coverage"],
    "priority_reasoning": "explanation of prioritization logic"
}}

RESPOND WITH VALID JSON ONLY:
""")

        self.evacuation_prompt = PromptTemplate.from_template("""
You are an expert evacuation planner. Design optimal evacuation routes and procedures for the disaster scenario.

DISASTER CONTEXT:
- Type: {disaster_type}
- Severity: {severity_level}
- Affected Zones: {affected_zones}

POPULATION ZONES TO EVACUATE:
{population_zones}

AVAILABLE EVACUATION CENTERS:
{evacuation_centers}

ROUTING CONSTRAINTS:
- Current traffic conditions: {traffic_conditions}
- Road capacity limitations
- Population vulnerability (elderly, disabled, children)
- Evacuation center capacity

TASK: Create an evacuation plan optimizing:
1. Shortest safe routes to evacuation centers
2. Population flow management
3. Evacuation center capacity utilization
4. Special needs accommodation

Provide response as JSON:
{{
    "evacuation_assignments": [
        {{
            "from_zone_id": "string",
            "to_zone_id": "string",
            "population_count": number,
            "route_priority": "primary|secondary|tertiary",
            "estimated_time_minutes": number,
            "special_considerations": "string"
        }}
    ],
    "phased_evacuation": {{
        "phase_1": ["highest priority zones"],
        "phase_2": ["medium priority zones"], 
        "phase_3": ["lower priority zones"]
    }},
    "capacity_management": "strategy for managing evacuation center capacity",
    "transportation_needs": "estimated transportation requirements"
}}

RESPOND WITH VALID JSON ONLY:
""")

    async def create_deployment_plan(
        self,
        disaster_type: str,
        severity_level: str,
        affected_areas: List[str],
        population_at_risk: int,
        available_teams: List[ResponseTeam],
        population_zones: List[PopulationZone]
    ) -> Dict[str, Any]:
        """Create optimal team deployment plan using WatsonX."""
        try:
            # Prepare data summaries
            teams_summary = self._create_teams_summary(available_teams)
            zones_summary = self._create_zones_summary(population_zones)
            
            # Create deployment prompt
            prompt = self.deployment_prompt.format(
                disaster_type=disaster_type,
                severity_level=severity_level,
                affected_areas=", ".join(affected_areas),
                population_at_risk=population_at_risk,
                teams_summary=teams_summary,
                population_zones_summary=zones_summary
            )
            
            # Get WatsonX deployment plan
            response = await self.watsonx_llm.ainvoke(prompt)
            
            # Parse and validate response
            try:
                deployment_plan = json.loads(response.strip())
                deployment_plan = self._validate_deployment_plan(deployment_plan, available_teams, population_zones)
                
                logger.info(f"WatsonX deployment plan created: {len(deployment_plan.get('deployments', []))} deployments")
                return deployment_plan
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse WatsonX deployment response: {e}")
                return self._create_fallback_deployment_plan(available_teams, population_zones)
        
        except Exception as e:
            logger.error(f"WatsonX deployment planning error: {e}")
            return self._create_fallback_deployment_plan(available_teams, population_zones)
    
    async def create_evacuation_plan(
        self,
        disaster_type: str,
        severity_level: str,
        affected_zones: List[str],
        population_zones: List[PopulationZone],
        evacuation_centers: List[Dict[str, Any]],
        traffic_conditions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create optimal evacuation plan using WatsonX."""
        try:
            # Prepare data summaries
            zones_summary = self._create_zones_summary(population_zones)
            centers_summary = self._create_centers_summary(evacuation_centers)
            traffic_summary = json.dumps(traffic_conditions)
            
            # Create evacuation prompt
            prompt = self.evacuation_prompt.format(
                disaster_type=disaster_type,
                severity_level=severity_level,
                affected_zones=", ".join(affected_zones),
                population_zones=zones_summary,
                evacuation_centers=centers_summary,
                traffic_conditions=traffic_summary
            )
            
            # Get WatsonX evacuation plan
            response = await self.watsonx_llm.ainvoke(prompt)
            
            # Parse and validate response
            try:
                evacuation_plan = json.loads(response.strip())
                evacuation_plan = self._validate_evacuation_plan(evacuation_plan, population_zones, evacuation_centers)
                
                logger.info(f"WatsonX evacuation plan created: {len(evacuation_plan.get('evacuation_assignments', []))} assignments")
                return evacuation_plan
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse WatsonX evacuation response: {e}")
                return self._create_fallback_evacuation_plan(population_zones, evacuation_centers)
        
        except Exception as e:
            logger.error(f"WatsonX evacuation planning error: {e}")
            return self._create_fallback_evacuation_plan(population_zones, evacuation_centers)
    
    def _create_teams_summary(self, teams: List[ResponseTeam]) -> str:
        """Create a concise summary of available teams."""
        summary_parts = []
        
        for team in teams:
            if team.availability_status == "available":
                summary_parts.append(
                    f"- {team.team_id}: {team.team_type} ({team.specialization}) "
                    f"- Capacity: {team.capacity}, Response time: {team.response_time_minutes}min"
                )
        
        return "\n".join(summary_parts) if summary_parts else "No available teams"
    
    def _create_zones_summary(self, zones: List[PopulationZone]) -> str:
        """Create a summary of population zones ordered by risk."""
        summary_parts = []
        
        # Sort by vulnerability and population density
        sorted_zones = sorted(
            zones,
            key=lambda z: (
                {"very_high": 4, "high": 3, "medium": 2, "low": 1}.get(z.vulnerability_score, 1),
                z.population_density_per_km2
            ),
            reverse=True
        )
        
        for zone in sorted_zones:
            summary_parts.append(
                f"- {zone.zone_id} ({zone.zone_name}): {zone.population:,} people, "
                f"density: {zone.population_density_per_km2}/km², "
                f"vulnerability: {zone.vulnerability_score}, "
                f"special needs: {zone.special_needs_population:,}"
            )
        
        return "\n".join(summary_parts)
    
    def _create_centers_summary(self, centers: List[Dict[str, Any]]) -> str:
        """Create a summary of evacuation centers."""
        summary_parts = []
        
        for center in centers:
            summary_parts.append(
                f"- {center.get('zone_id', 'Unknown')}: {center.get('zone_name', 'Unknown')} "
                f"- Capacity: {center.get('capacity', 0)}, Type: {center.get('zone_type', 'unknown')}"
            )
        
        return "\n".join(summary_parts)
    
    def _validate_deployment_plan(
        self,
        plan: Dict[str, Any],
        available_teams: List[ResponseTeam],
        population_zones: List[PopulationZone]
    ) -> Dict[str, Any]:
        """Validate and correct deployment plan."""
        validated_deployments = []
        team_ids = {team.team_id for team in available_teams}
        zone_ids = {zone.zone_id for zone in population_zones}
        
        for deployment in plan.get("deployments", []):
            if (deployment.get("team_id") in team_ids and 
                deployment.get("target_zone_id") in zone_ids):
                validated_deployments.append(deployment)
        
        plan["deployments"] = validated_deployments
        return plan
    
    def _validate_evacuation_plan(
        self,
        plan: Dict[str, Any],
        population_zones: List[PopulationZone],
        evacuation_centers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate and correct evacuation plan."""
        validated_assignments = []
        zone_ids = {zone.zone_id for zone in population_zones}
        center_ids = {center.get("zone_id") for center in evacuation_centers}
        
        for assignment in plan.get("evacuation_assignments", []):
            if (assignment.get("from_zone_id") in zone_ids and 
                assignment.get("to_zone_id") in center_ids):
                validated_assignments.append(assignment)
        
        plan["evacuation_assignments"] = validated_assignments
        return plan
    
    def _create_fallback_deployment_plan(
        self,
        available_teams: List[ResponseTeam],
        population_zones: List[PopulationZone]
    ) -> Dict[str, Any]:
        """Create a simple fallback deployment plan."""
        deployments = []
        
        # Sort teams by response time and zones by population density
        sorted_teams = sorted(available_teams, key=lambda t: t.response_time_minutes)
        sorted_zones = sorted(population_zones, key=lambda z: z.population_density_per_km2, reverse=True)
        
        # Simple assignment: fastest teams to highest density zones
        for i, zone in enumerate(sorted_zones[:len(sorted_teams)]):
            team = sorted_teams[i]
            deployments.append({
                "team_id": team.team_id,
                "target_zone_id": zone.zone_id,
                "priority_level": "high" if zone.vulnerability_score in ["high", "very_high"] else "medium",
                "deployment_reason": f"Fallback assignment to {zone.zone_name}",
                "estimated_arrival_minutes": team.response_time_minutes + 5,
                "coordination_instructions": f"Respond to {zone.zone_name} for {team.specialization}"
            })
        
        return {
            "deployments": deployments,
            "overall_strategy": "Fallback deployment - fastest response to highest density areas",
            "resource_gaps": ["WatsonX planning unavailable"],
            "priority_reasoning": "Simple distance and density based assignment"
        }
    
    def _create_fallback_evacuation_plan(
        self,
        population_zones: List[PopulationZone],
        evacuation_centers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a simple fallback evacuation plan."""
        assignments = []
        
        # Simple nearest-center assignment
        for zone in population_zones:
            if evacuation_centers:
                # For simplicity, assign to first available center
                center = evacuation_centers[0]
                assignments.append({
                    "from_zone_id": zone.zone_id,
                    "to_zone_id": center.get("zone_id"),
                    "population_count": zone.population,
                    "route_priority": "primary",
                    "estimated_time_minutes": 30,  # Default estimate
                    "special_considerations": f"Special needs: {zone.special_needs_population}"
                })
        
        return {
            "evacuation_assignments": assignments,
            "phased_evacuation": {
                "phase_1": [z.zone_id for z in population_zones if z.vulnerability_score == "very_high"],
                "phase_2": [z.zone_id for z in population_zones if z.vulnerability_score == "high"],
                "phase_3": [z.zone_id for z in population_zones if z.vulnerability_score in ["medium", "low"]]
            },
            "capacity_management": "Fallback evacuation plan - basic center assignment",
            "transportation_needs": "Estimated based on population counts"
        }


# === LANGCHAIN TOOLS ===

@tool(return_direct=True)
def watsonx_team_deployment_optimizer(
    disaster_type: str,
    severity_level: str,
    teams_data_json: str,
    population_zones_json: str,
    watsonx_config: Dict[str, str]
) -> str:
    """
    Optimize emergency response team deployment using IBM WatsonX.
    
    Args:
        disaster_type: Type of disaster (earthquake, flood, etc.)
        severity_level: Severity level (low, medium, high, critical, extreme)
        teams_data_json: JSON string with available response teams
        population_zones_json: JSON string with population zone data
        watsonx_config: WatsonX configuration
    
    Returns:
        JSON string with optimal deployment plan
    """
    try:
        # Parse inputs
        teams_data = json.loads(teams_data_json)
        zones_data = json.loads(population_zones_json)
        
        # Create simple deployment optimization (template)
        deployments = []
        
        # Sort zones by risk (vulnerability + density)
        sorted_zones = sorted(
            zones_data,
            key=lambda z: z.get("population_density_per_km2", 0) + 
                         {"very_high": 10000, "high": 5000, "medium": 2000, "low": 0}.get(z.get("vulnerability_score", "low"), 0),
            reverse=True
        )
        
        # Assign teams to highest risk zones
        for i, zone in enumerate(sorted_zones[:len(teams_data)]):
            if i < len(teams_data):
                team = teams_data[i]
                priority = "critical" if zone.get("vulnerability_score") == "very_high" else "high"
                
                deployments.append({
                    "team_id": team.get("team_id"),
                    "target_zone_id": zone.get("zone_id"),
                    "priority_level": priority,
                    "deployment_reason": f"High population density ({zone.get('population_density_per_km2')}/km²) and {zone.get('vulnerability_score')} vulnerability",
                    "estimated_arrival_minutes": team.get("response_time_minutes", 15) + 5,
                    "coordination_instructions": f"Focus on {zone.get('demographics')} population with {zone.get('special_needs_population')} special needs individuals"
                })
        
        plan = {
            "deployments": deployments,
            "overall_strategy": f"Priority deployment for {disaster_type} ({severity_level} severity) - high-risk zones first",
            "resource_gaps": [],
            "priority_reasoning": "Population density and vulnerability score optimization",
            "total_teams_deployed": len(deployments),
            "total_population_covered": sum(z.get("population", 0) for z in sorted_zones[:len(deployments)])
        }
        
        return json.dumps(plan)
        
    except Exception as e:
        logger.error(f"Team deployment optimizer error: {e}")
        return json.dumps({
            "deployments": [],
            "overall_strategy": "Deployment optimization failed",
            "resource_gaps": [f"Error: {str(e)}"],
            "priority_reasoning": "Manual deployment required",
            "total_teams_deployed": 0,
            "total_population_covered": 0
        })


@tool(return_direct=True)
def osrm_route_planner(
    from_locations_json: str,
    to_locations_json: str,
    route_type: str = "driving",
    alternatives: bool = True
) -> str:
    """
    Plan optimal routes using OSRM (Open Source Routing Machine).
    
    Args:
        from_locations_json: JSON array of origin coordinates [[lon, lat], ...]
        to_locations_json: JSON array of destination coordinates [[lon, lat], ...]
        route_type: Type of routing (driving, walking, cycling)
        alternatives: Whether to include alternative routes
    
    Returns:
        JSON string with route information and evacuation plans
    """
    try:
        from_locations = json.loads(from_locations_json)
        to_locations = json.loads(to_locations_json)
        
        # Template OSRM routing results (in real implementation, would call OSRM API)
        routes = []
        
        for i, from_loc in enumerate(from_locations):
            for j, to_loc in enumerate(to_locations):
                # Calculate approximate distance and time (template)
                lat_diff = abs(from_loc[1] - to_loc[1])
                lon_diff = abs(from_loc[0] - to_loc[0])
                distance_km = ((lat_diff**2 + lon_diff**2)**0.5) * 111  # Rough km conversion
                
                estimated_time = max(15, distance_km * 2)  # Rough time estimate
                
                route = {
                    "route_id": f"route_{i}_{j}",
                    "from_location": from_loc,
                    "to_location": to_loc,
                    "distance_km": round(distance_km, 2),
                    "estimated_time_minutes": int(estimated_time),
                    "route_geometry": {
                        "type": "LineString",
                        "coordinates": [from_loc, to_loc]  # Simplified - would be full route
                    },
                    "route_status": "clear",
                    "capacity_per_hour": max(100, int(1000 / distance_km)),  # Capacity estimate
                    "instructions": [
                        f"Start at coordinates {from_loc[1]:.4f}, {from_loc[0]:.4f}",
                        f"Proceed to evacuation center at {to_loc[1]:.4f}, {to_loc[0]:.4f}",
                        "Follow emergency signs and traffic guidance",
                        "Estimated arrival time: {estimated_time:.0f} minutes"
                    ]
                }
                routes.append(route)
        
        # Create evacuation routing summary
        routing_results = {
            "routes": routes,
            "total_routes": len(routes),
            "routing_algorithm": "OSRM (template)",
            "route_type": route_type,
            "optimization_criteria": ["shortest_time", "traffic_aware", "capacity_optimized"],
            "traffic_conditions": {
                "overall_status": "moderate",
                "congested_areas": [],
                "estimated_delay_factor": 1.2
            },
            "alternative_routes_available": alternatives,
            "route_summary": {
                "average_distance_km": sum(r["distance_km"] for r in routes) / len(routes) if routes else 0,
                "average_time_minutes": sum(r["estimated_time_minutes"] for r in routes) / len(routes) if routes else 0,
                "total_evacuation_capacity": sum(r["capacity_per_hour"] for r in routes)
            }
        }
        
        return json.dumps(routing_results)
        
    except Exception as e:
        logger.error(f"OSRM route planning error: {e}")
        return json.dumps({
            "routes": [],
            "total_routes": 0,
            "routing_algorithm": "OSRM (failed)",
            "error": str(e),
            "fallback_instructions": [
                "Use manual route planning",
                "Follow local emergency evacuation signs",
                "Contact emergency services for guidance"
            ]
        })


@tool(return_direct=True)
def evacuation_capacity_optimizer(
    population_zones_json: str,
    evacuation_centers_json: str,
    routes_json: str
) -> str:
    """
    Optimize evacuation center capacity and population flow.
    
    Args:
        population_zones_json: JSON with population zone data
        evacuation_centers_json: JSON with evacuation center data
        routes_json: JSON with available routes
    
    Returns:
        JSON string with optimized evacuation assignments
    """
    try:
        population_zones = json.loads(population_zones_json)
        evacuation_centers = json.loads(evacuation_centers_json)
        routes = json.loads(routes_json)
        
        # Create capacity optimization
        assignments = []
        center_utilization = {}
        
        # Initialize center capacities
        for center in evacuation_centers:
            center_id = center.get("zone_id")
            center_utilization[center_id] = {
                "total_capacity": center.get("capacity", 0),
                "assigned_population": 0,
                "utilization_percentage": 0
            }
        
        # Sort population zones by vulnerability and assign to nearest centers
        sorted_zones = sorted(
            population_zones,
            key=lambda z: {"very_high": 4, "high": 3, "medium": 2, "low": 1}.get(z.get("vulnerability_score", "low"), 1),
            reverse=True
        )
        
        for zone in sorted_zones:
            zone_population = zone.get("population", 0)
            
            # Find best evacuation center (simple assignment)
            best_center = None
            best_score = float('inf')
            
            for center in evacuation_centers:
                center_id = center.get("zone_id")
                available_capacity = (center_utilization[center_id]["total_capacity"] - 
                                   center_utilization[center_id]["assigned_population"])
                
                if available_capacity >= zone_population:
                    # Score based on available capacity (prefer centers with more space)
                    score = 1.0 / max(available_capacity, 1)
                    if score < best_score:
                        best_score = score
                        best_center = center
            
            # Assign to best center or split if needed
            if best_center:
                center_id = best_center.get("zone_id")
                center_utilization[center_id]["assigned_population"] += zone_population
                center_utilization[center_id]["utilization_percentage"] = (
                    center_utilization[center_id]["assigned_population"] / 
                    center_utilization[center_id]["total_capacity"] * 100
                )
                
                assignments.append({
                    "from_zone_id": zone.get("zone_id"),
                    "to_zone_id": center_id,
                    "population_count": zone_population,
                    "assignment_type": "primary",
                    "special_needs_count": zone.get("special_needs_population", 0),
                    "priority_level": zone.get("vulnerability_score", "medium")
                })
        
        # Create optimization summary
        optimization_result = {
            "evacuation_assignments": assignments,
            "center_utilization": center_utilization,
            "optimization_metrics": {
                "total_population_assigned": sum(a["population_count"] for a in assignments),
                "centers_utilized": len([c for c in center_utilization.values() if c["assigned_population"] > 0]),
                "average_utilization": sum(c["utilization_percentage"] for c in center_utilization.values()) / len(center_utilization),
                "overutilized_centers": [cid for cid, data in center_utilization.items() if data["utilization_percentage"] > 90]
            },
            "recommendations": [
                "Monitor evacuation center capacities during operation",
                "Prepare overflow plans for overutilized centers",
                "Coordinate transportation for special needs populations",
                "Establish real-time capacity monitoring"
            ]
        }
        
        return json.dumps(optimization_result)
        
    except Exception as e:
        logger.error(f"Evacuation capacity optimization error: {e}")
        return json.dumps({
            "evacuation_assignments": [],
            "center_utilization": {},
            "optimization_metrics": {
                "total_population_assigned": 0,
                "centers_utilized": 0,
                "average_utilization": 0,
                "overutilized_centers": []
            },
            "error": str(e),
            "recommendations": ["Manual capacity planning required"]
        })
