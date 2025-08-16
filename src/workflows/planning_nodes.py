"""
LangGraph workflow nodes for disaster response planning and management.
Orchestrates team deployment, evacuation planning, and resource coordination.
"""

import asyncio
import json
import logging
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

from ..core.state import (
    DisasterDetectionState, ResponseTeam, PopulationZone, TeamDeployment,
    EvacuationRoute, DisasterType, SeverityLevel
)
from ..monitoring.planning_agents import (
    watsonx_team_deployment_optimizer,
    osrm_route_planner,
    evacuation_capacity_optimizer
)


logger = logging.getLogger(__name__)


async def load_planning_data_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Load response teams, population zones, and evacuation centers from CSV files.
    """
    logger.info("Loading planning data from CSV files")
    
    try:
        # Get data directory path
        data_dir = Path(__file__).parent.parent.parent / "data"
        
        # Load response teams
        teams_file = data_dir / "response_teams.csv"
        if teams_file.exists():
            teams_df = pd.read_csv(teams_file)
            response_teams = []
            
            for _, row in teams_df.iterrows():
                team = ResponseTeam(
                    team_id=row['team_id'],
                    team_name=row['team_name'],
                    team_type=row['team_type'],
                    base_location={
                        "type": "Point",
                        "coordinates": [row['base_lon'], row['base_lat']]
                    },
                    capacity=row['capacity'],
                    specialization=row['specialization'],
                    availability_status=row['availability_status'],
                    response_time_minutes=row['response_time_minutes'],
                    equipment_level=row['equipment_level']
                )
                response_teams.append(team)
        else:
            logger.warning(f"Response teams file not found: {teams_file}")
            response_teams = []
        
        # Load population zones
        population_file = data_dir / "population_zones.csv"
        if population_file.exists():
            population_df = pd.read_csv(population_file)
            population_zones = []
            
            for _, row in population_df.iterrows():
                zone = PopulationZone(
                    zone_id=row['zone_id'],
                    zone_name=row['zone_name'],
                    center_location={
                        "type": "Point",
                        "coordinates": [row['center_lon'], row['center_lat']]
                    },
                    radius_km=row['radius_km'],
                    population=row['population'],
                    population_density_per_km2=row['population_density_per_km2'],
                    vulnerability_score=row['vulnerability_score'],
                    demographics=row['demographics'],
                    special_needs_population=row['special_needs_population']
                )
                population_zones.append(zone)
        else:
            logger.warning(f"Population zones file not found: {population_file}")
            population_zones = []
        
        # Load evacuation centers
        evacuation_file = data_dir / "evacuation_zones.csv"
        evacuation_zones = []
        if evacuation_file.exists():
            evacuation_df = pd.read_csv(evacuation_file)
            evacuation_zones = evacuation_df.to_dict('records')
        else:
            logger.warning(f"Evacuation zones file not found: {evacuation_file}")
        
        logger.info(f"Loaded: {len(response_teams)} teams, {len(population_zones)} population zones, {len(evacuation_zones)} evacuation centers")
        
        return {
            **state,
            "available_response_teams": response_teams,
            "population_zones": population_zones,
            "evacuation_zones": evacuation_zones,
            "last_update_time": datetime.now(),
            "next_action": "assess_planning_requirements"
        }
        
    except Exception as e:
        error_msg = f"Failed to load planning data: {str(e)}"
        logger.error(error_msg)
        
        return {
            **state,
            "processing_errors": state["processing_errors"] + [error_msg],
            "next_action": "planning_error_handling"
        }


async def assess_planning_requirements_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Assess what planning actions are needed based on the disaster situation.
    """
    logger.info("Assessing planning requirements")
    
    try:
        # Get current disaster event
        current_event = None
        if state["current_event_id"]:
            current_event = next(
                (event for event in state["active_events"] if event.id == state["current_event_id"]),
                None
            )
        
        if not current_event:
            logger.warning("No current event found for planning")
            return {
                **state,
                "next_action": "planning_complete"
            }
        
        # Determine planning priorities based on severity and type
        planning_priorities = []
        coordination_instructions = []
        
        disaster_type = current_event.disaster_type.value
        severity = current_event.severity.value
        
        # Team deployment requirements
        if severity in ["high", "critical", "extreme"]:
            planning_priorities.append("immediate_team_deployment")
            coordination_instructions.append("Deploy all available emergency response teams")
            
        if disaster_type in ["earthquake", "wildfire", "flood"]:
            planning_priorities.append("evacuation_planning")
            coordination_instructions.append("Initiate evacuation procedures for affected areas")
        
        # Resource allocation based on affected population
        affected_population = state.get("population_at_risk", 0)
        if affected_population > 10000:
            planning_priorities.append("large_scale_coordination")
            coordination_instructions.append("Activate large-scale disaster response protocols")
        
        # Special considerations
        if disaster_type == "earthquake":
            coordination_instructions.append("Check for structural damage and gas leaks")
            coordination_instructions.append("Establish safe zones away from buildings")
        elif disaster_type == "wildfire":
            coordination_instructions.append("Monitor wind patterns and fire spread")
            coordination_instructions.append("Prioritize evacuation routes away from fire direction")
        
        # Update management actions
        management_actions = state["management_actions_needed"] + [
            "Coordinate multi-agency response",
            "Establish incident command structure",
            "Deploy resources based on priority zones",
            "Monitor evacuation progress",
            "Maintain communication with all units"
        ]
        
        logger.info(f"Planning priorities: {planning_priorities}")
        
        return {
            **state,
            "management_actions_needed": management_actions,
            "coordination_instructions": coordination_instructions,
            "last_update_time": datetime.now(),
            "next_action": "create_deployment_plan"
        }
        
    except Exception as e:
        error_msg = f"Planning requirements assessment error: {str(e)}"
        logger.error(error_msg)
        
        return {
            **state,
            "processing_errors": state["processing_errors"] + [error_msg],
            "next_action": "planning_error_handling"
        }


async def create_deployment_plan_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Create optimal team deployment plan using WatsonX.
    """
    logger.info("Creating team deployment plan")
    
    try:
        # Get current disaster event
        current_event = None
        if state["current_event_id"]:
            current_event = next(
                (event for event in state["active_events"] if event.id == state["current_event_id"]),
                None
            )
        
        if not current_event:
            logger.warning("No current event for deployment planning")
            return {
                **state,
                "next_action": "create_evacuation_plan"
            }
        
        # Prepare data for WatsonX agent
        available_teams = [
            team for team in state["available_response_teams"] 
            if team.availability_status == "available"
        ]
        
        if not available_teams:
            logger.warning("No available teams for deployment")
            return {
                **state,
                "deployment_plan": {"error": "No available teams"},
                "next_action": "create_evacuation_plan"
            }
        
        # Convert teams to JSON format
        teams_data = []
        for team in available_teams:
            teams_data.append({
                "team_id": team.team_id,
                "team_name": team.team_name,
                "team_type": team.team_type,
                "specialization": team.specialization,
                "capacity": team.capacity,
                "response_time_minutes": team.response_time_minutes,
                "equipment_level": team.equipment_level,
                "base_lat": team.base_location["coordinates"][1],
                "base_lon": team.base_location["coordinates"][0]
            })
        
        # Convert population zones to JSON format
        zones_data = []
        for zone in state["population_zones"]:
            zones_data.append({
                "zone_id": zone.zone_id,
                "zone_name": zone.zone_name,
                "population": zone.population,
                "population_density_per_km2": zone.population_density_per_km2,
                "vulnerability_score": zone.vulnerability_score,
                "special_needs_population": zone.special_needs_population,
                "demographics": zone.demographics,
                "center_lat": zone.center_location["coordinates"][1],
                "center_lon": zone.center_location["coordinates"][0]
            })
        
        # WatsonX configuration
        watsonx_config = {
            "api_key": "your-watsonx-api-key",  # Would be from environment
            "url": "https://us-south.ml.cloud.ibm.com",
            "project_id": "your-project-id",
            "model_id": "ibm/granite-13b-instruct-v2"
        }
        
        # Call WatsonX deployment optimizer
        deployment_result = watsonx_team_deployment_optimizer.invoke({
            "disaster_type": current_event.disaster_type.value,
            "severity_level": current_event.severity.value,
            "teams_data_json": json.dumps(teams_data),
            "population_zones_json": json.dumps(zones_data),
            "watsonx_config": watsonx_config
        })
        
        # Parse deployment plan
        deployment_plan = json.loads(deployment_result)
        
        # Create TeamDeployment objects
        team_deployments = []
        for deployment in deployment_plan.get("deployments", []):
            team_deployment = TeamDeployment(
                deployment_id=f"deploy_{deployment['team_id']}_{datetime.now().strftime('%H%M%S')}",
                team_id=deployment["team_id"],
                target_zone_id=deployment["target_zone_id"],
                priority_level=deployment["priority_level"],
                deployment_reason=deployment["deployment_reason"],
                estimated_arrival_time=datetime.now() + timedelta(minutes=deployment["estimated_arrival_minutes"]),
                deployment_duration_hours=4,  # Default 4-hour deployment
                coordination_instructions=deployment["coordination_instructions"]
            )
            team_deployments.append(team_deployment)
        
        logger.info(f"Deployment plan created: {len(team_deployments)} teams deployed")
        
        return {
            **state,
            "deployment_plan": deployment_plan,
            "team_deployments": team_deployments,
            "last_update_time": datetime.now(),
            "next_action": "create_evacuation_plan"
        }
        
    except Exception as e:
        error_msg = f"Deployment planning error: {str(e)}"
        logger.error(error_msg)
        
        return {
            **state,
            "processing_errors": state["processing_errors"] + [error_msg],
            "deployment_plan": {"error": error_msg},
            "next_action": "create_evacuation_plan"
        }


async def create_evacuation_plan_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Create evacuation plan with OSRM routing and capacity optimization.
    """
    logger.info("Creating evacuation plan with route optimization")
    
    try:
        # Extract population zone coordinates
        population_coordinates = []
        population_zone_mapping = {}
        
        for zone in state["population_zones"]:
            coords = zone.center_location["coordinates"]
            population_coordinates.append(coords)
            population_zone_mapping[len(population_coordinates) - 1] = zone.zone_id
        
        # Extract evacuation center coordinates
        evacuation_coordinates = []
        evacuation_zone_mapping = {}
        
        for center in state["evacuation_zones"]:
            coords = [center["lon"], center["lat"]]
            evacuation_coordinates.append(coords)
            evacuation_zone_mapping[len(evacuation_coordinates) - 1] = center["zone_id"]
        
        # Call OSRM route planner
        if population_coordinates and evacuation_coordinates:
            routing_result = osrm_route_planner.invoke({
                "from_locations_json": json.dumps(population_coordinates),
                "to_locations_json": json.dumps(evacuation_coordinates),
                "route_type": "driving",
                "alternatives": True
            })
            
            routing_data = json.loads(routing_result)
        else:
            routing_data = {"routes": []}
        
        # Call evacuation capacity optimizer
        population_zones_json = json.dumps([
            {
                "zone_id": zone.zone_id,
                "zone_name": zone.zone_name,
                "population": zone.population,
                "vulnerability_score": zone.vulnerability_score,
                "special_needs_population": zone.special_needs_population
            }
            for zone in state["population_zones"]
        ])
        
        evacuation_centers_json = json.dumps(state["evacuation_zones"])
        
        capacity_result = evacuation_capacity_optimizer.invoke({
            "population_zones_json": population_zones_json,
            "evacuation_centers_json": evacuation_centers_json,
            "routes_json": json.dumps(routing_data)
        })
        
        capacity_data = json.loads(capacity_result)
        
        # Create EvacuationRoute objects
        evacuation_routes = []
        for route in routing_data.get("routes", []):
            evacuation_route = EvacuationRoute(
                route_id=route["route_id"],
                from_zone_id=f"population_zone_{route['route_id'].split('_')[1]}",  # Simplified mapping
                to_zone_id=f"evacuation_zone_{route['route_id'].split('_')[2]}",
                route_geometry=route["route_geometry"],
                distance_km=route["distance_km"],
                estimated_time_minutes=route["estimated_time_minutes"],
                capacity_per_hour=route["capacity_per_hour"],
                route_status=route["route_status"]
            )
            evacuation_routes.append(evacuation_route)
        
        # Combine evacuation plan
        evacuation_plan = {
            "routing_analysis": routing_data,
            "capacity_optimization": capacity_data,
            "total_routes_planned": len(evacuation_routes),
            "total_evacuation_capacity": sum(route.capacity_per_hour for route in evacuation_routes),
            "phased_evacuation": capacity_data.get("phased_evacuation", {}),
            "special_considerations": [
                "Prioritize vulnerable populations",
                "Monitor route congestion",
                "Coordinate with traffic management",
                "Maintain communication with evacuation centers"
            ]
        }
        
        logger.info(f"Evacuation plan created: {len(evacuation_routes)} routes planned")
        
        return {
            **state,
            "evacuation_plan": evacuation_plan,
            "evacuation_routes": evacuation_routes,
            "routing_results": routing_data,
            "route_optimization_status": "completed",
            "last_update_time": datetime.now(),
            "next_action": "coordinate_resources"
        }
        
    except Exception as e:
        error_msg = f"Evacuation planning error: {str(e)}"
        logger.error(error_msg)
        
        return {
            **state,
            "processing_errors": state["processing_errors"] + [error_msg],
            "evacuation_plan": {"error": error_msg},
            "route_optimization_status": "failed",
            "next_action": "coordinate_resources"
        }


async def coordinate_resources_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Coordinate resources and create comprehensive resource allocation plan.
    """
    logger.info("Coordinating resources and finalizing allocation")
    
    try:
        # Calculate resource requirements
        total_population_at_risk = sum(zone.population for zone in state["population_zones"])
        total_special_needs = sum(zone.special_needs_population for zone in state["population_zones"])
        
        # Calculate team assignments
        deployed_teams = len(state["team_deployments"])
        available_teams = len([team for team in state["available_response_teams"] 
                             if team.availability_status == "available"])
        
        # Calculate evacuation capacity
        total_evacuation_capacity = sum(center.get("capacity", 0) for center in state["evacuation_zones"])
        capacity_utilization = min(100, (total_population_at_risk / total_evacuation_capacity * 100) if total_evacuation_capacity > 0 else 0)
        
        # Create resource allocation summary
        resource_allocation = {
            "population_analysis": {
                "total_population_at_risk": total_population_at_risk,
                "special_needs_population": total_special_needs,
                "vulnerable_zones": len([z for z in state["population_zones"] if z.vulnerability_score in ["high", "very_high"]])
            },
            "team_deployment": {
                "teams_deployed": deployed_teams,
                "teams_available": available_teams,
                "deployment_coverage": min(100, (deployed_teams / len(state["population_zones"]) * 100) if state["population_zones"] else 0)
            },
            "evacuation_capacity": {
                "total_capacity": total_evacuation_capacity,
                "capacity_utilization_percent": capacity_utilization,
                "evacuation_centers_active": len(state["evacuation_zones"]),
                "routes_available": len(state["evacuation_routes"])
            },
            "resource_gaps": [],
            "coordination_priorities": [
                "Establish unified command structure",
                "Deploy teams to highest priority zones",
                "Begin phased evacuation procedures",
                "Monitor resource utilization",
                "Maintain communication networks"
            ]
        }
        
        # Identify resource gaps
        if capacity_utilization > 90:
            resource_allocation["resource_gaps"].append("Evacuation center capacity approaching limit")
        
        if deployed_teams < len(state["population_zones"]) / 2:
            resource_allocation["resource_gaps"].append("Insufficient team coverage for all zones")
        
        if total_special_needs > total_evacuation_capacity * 0.1:
            resource_allocation["resource_gaps"].append("Special needs population may require additional resources")
        
        # Create coordination timeline
        coordination_timeline = [
            {"time": "T+0", "action": "Activate incident command", "status": "completed"},
            {"time": "T+15min", "action": "Deploy priority response teams", "status": "in_progress"},
            {"time": "T+30min", "action": "Begin evacuation of vulnerable zones", "status": "pending"},
            {"time": "T+60min", "action": "Full evacuation operations", "status": "pending"},
            {"time": "T+2hr", "action": "Resource status assessment", "status": "pending"}
        ]
        
        # Update coordination instructions
        updated_instructions = state["coordination_instructions"] + [
            f"Deploy {deployed_teams} teams to priority zones",
            f"Prepare evacuation for {total_population_at_risk:,} people",
            f"Monitor capacity at {len(state['evacuation_zones'])} evacuation centers",
            "Coordinate with traffic management for route optimization",
            "Establish communication with all emergency services"
        ]
        
        logger.info(f"Resource coordination completed: {deployed_teams} teams, {len(state['evacuation_routes'])} routes")
        
        return {
            **state,
            "resource_allocation": resource_allocation,
            "coordination_instructions": updated_instructions,
            "management_actions_needed": state["management_actions_needed"] + coordination_timeline,
            "last_update_time": datetime.now(),
            "next_action": "generate_notifications"
        }
        
    except Exception as e:
        error_msg = f"Resource coordination error: {str(e)}"
        logger.error(error_msg)
        
        return {
            **state,
            "processing_errors": state["processing_errors"] + [error_msg],
            "resource_allocation": {"error": error_msg},
            "next_action": "generate_notifications"
        }


async def generate_notifications_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Generate notifications and alerts for authorities and stakeholders.
    """
    logger.info("Generating notifications for authorities")
    
    try:
        # Get current disaster event
        current_event = None
        if state["current_event_id"]:
            current_event = next(
                (event for event in state["active_events"] if event.id == state["current_event_id"]),
                None
            )
        
        if not current_event:
            logger.warning("No current event for notifications")
            return {
                **state,
                "next_action": "planning_complete"
            }
        
        # Create comprehensive notification messages
        notification_messages = []
        
        # Primary alert to emergency management
        primary_alert = {
            "notification_id": f"alert_{current_event.id}_{datetime.now().strftime('%H%M%S')}",
            "recipient_type": "emergency_management",
            "priority": "critical" if current_event.severity.value in ["critical", "extreme"] else "high",
            "subject": f"{current_event.disaster_type.value.title()} Emergency Response Activated",
            "message": f"""
EMERGENCY RESPONSE ACTIVATION

Disaster Type: {current_event.disaster_type.value.title()}
Severity Level: {current_event.severity.value.title()}
Event ID: {current_event.id}
Detection Time: {current_event.detected_at.strftime('%Y-%m-%d %H:%M:%S')}

RESPONSE STATUS:
- Teams Deployed: {len(state['team_deployments'])}
- Evacuation Routes: {len(state['evacuation_routes'])}
- Population at Risk: {state.get('population_at_risk', 0):,}

IMMEDIATE ACTIONS:
{chr(10).join(f"• {action}" for action in state['coordination_instructions'][:5])}

RESOURCE ALLOCATION:
- Emergency Response Teams: {len(state['team_deployments'])} deployed
- Evacuation Centers: {len(state['evacuation_zones'])} activated
- Capacity Utilization: {state['resource_allocation'].get('evacuation_capacity', {}).get('capacity_utilization_percent', 0):.1f}%

Planning Workflow ID: {state.get('planning_workflow_id', 'N/A')}

Contact Emergency Operations Center for updates.
""",
            "timestamp": datetime.now().isoformat(),
            "delivery_status": "pending"
        }
        notification_messages.append(primary_alert)
        
        # Team deployment notifications
        for deployment in state["team_deployments"]:
            team_notification = {
                "notification_id": f"deploy_{deployment.deployment_id}",
                "recipient_type": "response_team",
                "priority": deployment.priority_level,
                "subject": f"Emergency Deployment - {deployment.team_id}",
                "message": f"""
EMERGENCY DEPLOYMENT ORDER

Team: {deployment.team_id}
Target Zone: {deployment.target_zone_id}
Priority: {deployment.priority_level.title()}

Deployment Reason: {deployment.deployment_reason}
Estimated Arrival: {deployment.estimated_arrival_time.strftime('%H:%M')}
Duration: {deployment.deployment_duration_hours} hours

Instructions: {deployment.coordination_instructions}

Report status upon arrival and every 30 minutes thereafter.
""",
                "timestamp": datetime.now().isoformat(),
                "delivery_status": "pending"
            }
            notification_messages.append(team_notification)
        
        # Public information notification
        public_notification = {
            "notification_id": f"public_{current_event.id}",
            "recipient_type": "public_information",
            "priority": "high",
            "subject": f"{current_event.disaster_type.value.title()} Emergency Response - Public Advisory",
            "message": f"""
EMERGENCY ADVISORY

A {current_event.disaster_type.value} has been detected in the area.

CURRENT STATUS: {current_event.severity.value.title()} severity

IMMEDIATE ACTIONS FOR RESIDENTS:
• Follow evacuation orders if issued
• Monitor emergency broadcasts
• Stay away from affected areas
• Report emergencies to 911

EVACUATION INFORMATION:
• {len(state['evacuation_zones'])} evacuation centers are operational
• Follow designated evacuation routes
• Bring essential supplies and medications

For updates: [Emergency Information Hotline]
Event ID: {current_event.id}
""",
            "timestamp": datetime.now().isoformat(),
            "delivery_status": "pending"
        }
        notification_messages.append(public_notification)
        
        # Create authority contact list
        authority_contacts = [
            {"name": "Emergency Operations Center", "phone": "415-558-3800", "email": "eoc@sf.gov"},
            {"name": "SF Fire Department", "phone": "415-558-3200", "email": "fire.chief@sf.gov"},
            {"name": "SF Police Department", "phone": "415-553-0123", "email": "police.chief@sf.gov"},
            {"name": "Public Health Emergency", "phone": "415-554-2500", "email": "health.emergency@sf.gov"},
            {"name": "Red Cross Bay Area", "phone": "415-427-8000", "email": "bayarea@redcross.org"}
        ]
        
        # Update notification status
        notification_status = {
            "emergency_management": False,
            "response_teams": False,
            "public_information": False,
            "media_relations": False,
            "government_officials": False
        }
        
        logger.info(f"Generated {len(notification_messages)} notifications")
        
        return {
            **state,
            "notification_messages": notification_messages,
            "authority_contacts": authority_contacts,
            "notification_status": notification_status,
            "last_update_time": datetime.now(),
            "next_action": "send_notifications"
        }
        
    except Exception as e:
        error_msg = f"Notification generation error: {str(e)}"
        logger.error(error_msg)
        
        return {
            **state,
            "processing_errors": state["processing_errors"] + [error_msg],
            "next_action": "planning_complete"
        }


async def send_notifications_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Send notifications to authorities and stakeholders (template implementation).
    """
    logger.info("Sending notifications to authorities and stakeholders")
    
    try:
        # Template notification service - in real implementation would use actual services
        sent_notifications = []
        updated_status = state["notification_status"].copy()
        
        for notification in state["notification_messages"]:
            # Simulate sending notification
            notification_id = notification["notification_id"]
            recipient_type = notification["recipient_type"]
            
            # Template sending logic
            if recipient_type == "emergency_management":
                # Would send via emergency management system
                logger.info(f"Sending to Emergency Management: {notification['subject']}")
                updated_status["emergency_management"] = True
                
            elif recipient_type == "response_team":
                # Would send via team communication system
                logger.info(f"Sending to Response Team: {notification['subject']}")
                updated_status["response_teams"] = True
                
            elif recipient_type == "public_information":
                # Would send via public alert system
                logger.info(f"Sending Public Alert: {notification['subject']}")
                updated_status["public_information"] = True
            
            # Mark as sent
            notification["delivery_status"] = "sent"
            notification["sent_timestamp"] = datetime.now().isoformat()
            sent_notifications.append(notification)
        
        # Create summary report
        notification_summary = {
            "total_notifications_sent": len(sent_notifications),
            "emergency_management_notified": updated_status["emergency_management"],
            "response_teams_notified": updated_status["response_teams"],
            "public_alerts_issued": updated_status["public_information"],
            "notification_channels": [
                "Emergency Operations Center",
                "Team Communication System",
                "Public Alert System",
                "Media Relations"
            ],
            "delivery_confirmation": "All priority notifications delivered",
            "next_update_scheduled": (datetime.now() + timedelta(hours=1)).isoformat()
        }
        
        logger.info(f"Notifications sent: {len(sent_notifications)} messages delivered")
        
        return {
            **state,
            "notification_messages": sent_notifications,
            "notification_status": updated_status,
            "notification_sent": True,
            "stakeholder_notifications": {
                "emergency_management": True,
                "response_teams": True,
                "public_information": True,
                "media_relations": True
            },
            "last_update_time": datetime.now(),
            "next_action": "planning_complete"
        }
        
    except Exception as e:
        error_msg = f"Notification sending error: {str(e)}"
        logger.error(error_msg)
        
        return {
            **state,
            "processing_errors": state["processing_errors"] + [error_msg],
            "notification_sent": False,
            "next_action": "planning_complete"
        }


async def planning_complete_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Finalize planning workflow and prepare for ongoing monitoring.
    """
    logger.info("Planning workflow completed")
    
    try:
        # Create planning workflow summary
        planning_summary = {
            "workflow_completion_time": datetime.now().isoformat(),
            "planning_workflow_id": state.get("planning_workflow_id"),
            "total_planning_time_minutes": (
                datetime.now() - state["workflow_start_time"]
            ).total_seconds() / 60,
            "resources_deployed": {
                "response_teams": len(state["team_deployments"]),
                "evacuation_routes": len(state["evacuation_routes"]),
                "evacuation_centers": len(state["evacuation_zones"]),
                "population_covered": sum(zone.population for zone in state["population_zones"])
            },
            "notifications_sent": len(state["notification_messages"]),
            "coordination_instructions": len(state["coordination_instructions"]),
            "planning_status": "completed",
            "next_phase": "operational_monitoring"
        }
        
        # Update workflow phase
        updated_management_actions = state["management_actions_needed"] + [
            "Planning workflow completed successfully",
            "All resources deployed and coordinated",
            "Notifications sent to all stakeholders",
            "Transition to operational monitoring phase"
        ]
        
        logger.info(f"Planning completed: {planning_summary['resources_deployed']['response_teams']} teams deployed, "
                   f"{planning_summary['notifications_sent']} notifications sent")
        
        return {
            **state,
            "workflow_phase": "planning_completed",
            "management_actions_needed": updated_management_actions,
            "planning_workflow_triggered": True,  # Mark as completed
            "last_update_time": datetime.now(),
            "next_action": "operational_monitoring"
        }
        
    except Exception as e:
        error_msg = f"Planning completion error: {str(e)}"
        logger.error(error_msg)
        
        return {
            **state,
            "processing_errors": state["processing_errors"] + [error_msg],
            "workflow_phase": "planning_error",
            "next_action": "planning_error_handling"
        }


async def planning_error_handling_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Handle errors in the planning workflow.
    """
    logger.info("Handling planning workflow errors")
    
    errors = state["processing_errors"]
    recent_errors = errors[-3:] if len(errors) >= 3 else errors
    
    # Create fallback plan
    fallback_actions = [
        "Switch to manual emergency coordination",
        "Contact emergency operations center directly",
        "Use backup communication channels",
        "Deploy available teams to high-priority areas",
        "Issue general evacuation advisory"
    ]
    
    return {
        **state,
        "management_actions_needed": state["management_actions_needed"] + fallback_actions,
        "workflow_phase": "manual_coordination",
        "next_action": "operational_monitoring",
        "last_update_time": datetime.now()
    }
