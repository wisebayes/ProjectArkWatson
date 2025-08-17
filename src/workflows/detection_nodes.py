"""
LangGraph workflow nodes for disaster detection and prediction pipeline.
Orchestrates API monitoring, WatsonX classification, and confirmation workflows.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from core.state import (
    DisasterDetectionState, DisasterEvent, MonitoringData, 
    DisasterType, SeverityLevel, AlertStatus, SafeZone
)
from monitoring.api_clients import DisasterMonitoringService, predict_disaster_risk
from monitoring.watsonx_agents import (
    watsonx_disaster_classifier, web_search_disaster_confirmation,
    severity_impact_analyzer, safe_zone_identifier
)


logger = logging.getLogger(__name__)


async def api_monitoring_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Poll all configured API sources for disaster-related data.
    Updates the state with fresh monitoring data.
    """
    logger.info("Starting API monitoring node")
    
    try:
        # Use the first monitoring region as the primary location
        if not state["monitoring_regions"]:
            logger.error("No monitoring regions configured")
            return {
                **state,
                "processing_errors": state["processing_errors"] + ["No monitoring regions configured"],
                "next_action": "error_handling"
            }
        
        primary_region = state["monitoring_regions"][0]
        lat = primary_region.get("center_lat", 40.7128)  # Default to NYC
        lon = primary_region.get("center_lon", -74.0060)
        radius_km = primary_region.get("radius_km", 100)
        
        # Poll all data sources
        async with DisasterMonitoringService() as monitoring_service:
            api_responses = await monitoring_service.poll_all_sources(lat, lon, radius_km)
            monitoring_data = monitoring_service.convert_to_monitoring_data(api_responses)
        
        # Update API poll times
        now = datetime.now()
        updated_poll_times = state["last_api_poll_times"].copy()
        updated_error_counts = state["api_error_counts"].copy()
        
        for source, response in api_responses.items():
            updated_poll_times[source] = now
            if not response.success:
                updated_error_counts[source] = updated_error_counts.get(source, 0) + 1
            else:
                updated_error_counts[source] = 0  # Reset on success
        
        # Update current monitoring data
        current_data = {}
        for data in monitoring_data:
            current_data[data.source] = data
        
        # Add to monitoring history (keep last 100 entries)
        updated_history = state["monitoring_history"] + monitoring_data
        if len(updated_history) > 100:
            updated_history = updated_history[-100:]
        
        logger.info(f"API monitoring completed: {len(monitoring_data)} sources polled")
        
        return {
            **state,
            "current_monitoring_data": current_data,
            "monitoring_history": updated_history,
            "last_api_poll_times": updated_poll_times,
            "api_error_counts": updated_error_counts,
            "last_update_time": now,
            "next_action": "data_analysis"
        }
        
    except Exception as e:
        error_msg = f"API monitoring error: {str(e)}"
        logger.error(error_msg)
        
        return {
            **state,
            "processing_errors": state["processing_errors"] + [error_msg],
            "retry_count": state["retry_count"] + 1,
            "next_action": "error_handling" if state["retry_count"] >= state["max_retries"] else "api_monitoring"
        }


async def data_analysis_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Analyze monitoring data for anomalies and potential threats.
    Prepares data for WatsonX classification.
    """
    logger.info("Starting data analysis node")
    
    try:
        monitoring_data = list(state["current_monitoring_data"].values())
        
        if not monitoring_data:
            logger.warning("No monitoring data available for analysis")
            return {
                **state,
                "next_action": "wait_interval"
            }
        
        # Calculate total alerts across all sources
        total_alerts = sum(data.alerts_count for data in monitoring_data)
        
        # Extract location from monitoring regions
        primary_region = state["monitoring_regions"][0] if state["monitoring_regions"] else {}
        location = {
            "lat": primary_region.get("center_lat", 40.7128),
            "lon": primary_region.get("center_lon", -74.0060)
        }
        
        # Run disaster prediction model
        prediction_result = await predict_disaster_risk(monitoring_data, location)
        
        # Update state with analysis results
        updated_state = {
            **state,
            "prediction_confidence": prediction_result["confidence"],
            "disaster_type_probabilities": {
                dt: 0.1 for dt in prediction_result.get("predicted_disasters", [])
            },
            "last_update_time": datetime.now()
        }
        
        # Determine next action based on analysis
        if total_alerts > 0 or prediction_result["risk_score"] > state["confidence_threshold"]:
            updated_state["next_action"] = "watsonx_classification"
            logger.info(f"Potential threat detected: {total_alerts} alerts, risk score: {prediction_result['risk_score']}")
        else:
            updated_state["next_action"] = "wait_interval"
            logger.info("No significant threats detected")
        
        return updated_state
        
    except Exception as e:
        error_msg = f"Data analysis error: {str(e)}"
        logger.error(error_msg)
        
        return {
            **state,
            "processing_errors": state["processing_errors"] + [error_msg],
            "next_action": "wait_interval"
        }


async def watsonx_classification_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Use IBM WatsonX to classify potential disaster threats.
    """
    logger.info("Starting WatsonX classification node")
    
    try:
        monitoring_data = list(state["current_monitoring_data"].values())
        
        # Prepare data for WatsonX classification
        monitoring_data_json = json.dumps([
            {
                "source": data.source.value,
                "timestamp": data.timestamp.isoformat(),
                "alerts_count": data.alerts_count,
                "data_summary": str(data.data)[:500]  # Truncate for prompt
            }
            for data in monitoring_data
        ])
        
        primary_region = state["monitoring_regions"][0] if state["monitoring_regions"] else {}
        location_json = json.dumps({
            "lat": primary_region.get("center_lat", 40.7128),
            "lon": primary_region.get("center_lon", -74.0060)
        })
        
        # WatsonX configuration (would come from environment in real implementation)
        watsonx_config = {
            "api_key": "your-watsonx-api-key",  # Would be from env
            "url": "https://us-south.ml.cloud.ibm.com",
            "project_id": "your-project-id",  # Would be from env
            "model_id": state["watsonx_model_id"]
        }
        
        # Call WatsonX classification tool
        classification_result = watsonx_disaster_classifier.invoke({
            "monitoring_data_json": monitoring_data_json,
            "location_json": location_json,
            "watsonx_config": watsonx_config,
            # Situation description can be passed via state later if integrated
        })
        
        # Parse classification result
        classification = json.loads(classification_result)
        
        # Update state with classification results
        updated_state = {
            **state,
            "classification_results": classification,
            "prediction_confidence": classification["confidence_score"],
            "last_update_time": datetime.now()
        }
        
        # Determine next action based on classification
        if classification["threat_detected"]:
            if classification.get("requires_confirmation") and not classification.get("ongoing", False):
                updated_state["next_action"] = "web_search_confirmation"
            else:
                updated_state["next_action"] = "severity_assessment"
            
            logger.info(f"WatsonX detected threat: {classification['disaster_type']} (confidence: {classification['confidence_score']})")
        else:
            updated_state["next_action"] = "wait_interval"
            logger.info("WatsonX: No threat detected")
        
        return updated_state
        
    except Exception as e:
        error_msg = f"WatsonX classification error: {str(e)}"
        logger.error(error_msg)
        
        return {
            **state,
            "processing_errors": state["processing_errors"] + [error_msg],
            "next_action": "wait_interval"
        }


async def web_search_confirmation_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Use web search to confirm detected disaster events.
    """
    logger.info("Starting web search confirmation node")
    
    try:
        classification = state["classification_results"]
        
        if not classification:
            logger.error("No classification results available for confirmation")
            return {
                **state,
                "next_action": "wait_interval"
            }
        
        # Determine location name for search
        primary_region = state["monitoring_regions"][0] if state["monitoring_regions"] else {}
        location_name = primary_region.get("name", "unknown location")
        
        # Perform web search confirmation
        confirmation_result = web_search_disaster_confirmation.invoke({
            "disaster_type": classification["disaster_type"],
            "location_name": location_name,
            "severity_level": classification["severity_level"],
            "time_window": "24h"
        })
        
        # Parse confirmation result
        confirmation = json.loads(confirmation_result)
        
        # Update state with confirmation results
        updated_state = {
            **state,
            "search_results": confirmation["search_results"],
            "confirmation_confidence": confirmation["confirmation_confidence"],
            "confirmation_status": AlertStatus.CONFIRMED if confirmation["confirmed"] else AlertStatus.FALSE_POSITIVE,
            "last_update_time": datetime.now()
        }
        
        # Determine next action based on confirmation
        if confirmation["confirmed"]:
            updated_state["next_action"] = "severity_assessment"
            logger.info(f"Event confirmed via web search (confidence: {confirmation['confirmation_confidence']})")
        else:
            updated_state["next_action"] = "log_false_positive"
            logger.info("Event not confirmed via web search - likely false positive")
        
        return updated_state
        
    except Exception as e:
        error_msg = f"Web search confirmation error: {str(e)}"
        logger.error(error_msg)
        
        return {
            **state,
            "processing_errors": state["processing_errors"] + [error_msg],
            "next_action": "severity_assessment"  # Proceed without confirmation
        }


async def severity_assessment_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Assess the severity and potential impact of confirmed disaster events.
    """
    logger.info("Starting severity assessment node")
    
    try:
        classification = state["classification_results"]
        primary_region = state["monitoring_regions"][0] if state["monitoring_regions"] else {}
        
        # Extract parameters for severity analysis
        disaster_type = classification["disaster_type"]
        magnitude_or_intensity = "5.0"  # Would extract from monitoring data
        affected_area_km2 = primary_region.get("radius_km", 100) ** 2 * 3.14159  # Rough circle area
        population_density = primary_region.get("population_density", 1000)  # People per km2
        
        # Count critical infrastructure from monitoring data
        osm_data = state["current_monitoring_data"].get("osm_overpass")
        critical_infrastructure_count = osm_data.alerts_count if osm_data else 5  # Default
        
        # Perform severity assessment
        severity_result = severity_impact_analyzer.invoke({
            "disaster_type": disaster_type,
            "magnitude_or_intensity": magnitude_or_intensity,
            "affected_area_km2": affected_area_km2,
            "population_density": population_density,
            "critical_infrastructure_count": critical_infrastructure_count
        })
        
        # Parse severity result
        severity = json.loads(severity_result)
        
        # Update state with severity assessment
        updated_state = {
            **state,
            "severity_factors": severity["severity_factors"],
            "severity_score": severity["severity_score"],
            "escalation_required": severity["escalation_required"],
            "impact_assessment": severity["impact_assessment"],
            "population_at_risk": severity["population_at_risk"],
            "last_update_time": datetime.now()
        }
        
        # Determine next action based on severity
        if severity["escalation_required"]:
            updated_state["next_action"] = "safe_zone_analysis"
            logger.info(f"High severity event detected: {severity['severity_level']} (score: {severity['severity_score']})")
        else:
            updated_state["next_action"] = "create_event_record"
            logger.info(f"Moderate severity event: {severity['severity_level']}")
        
        return updated_state
        
    except Exception as e:
        error_msg = f"Severity assessment error: {str(e)}"
        logger.error(error_msg)
        
        return {
            **state,
            "processing_errors": state["processing_errors"] + [error_msg],
            "next_action": "create_event_record"
        }


async def safe_zone_analysis_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Identify safe zones and evacuation routes for disaster response.
    """
    logger.info("Starting safe zone analysis node")
    
    try:
        classification = state["classification_results"]
        primary_region = state["monitoring_regions"][0] if state["monitoring_regions"] else {}
        
        # Create affected area GeoJSON (simplified)
        center_lat = primary_region.get("center_lat", 40.7128)
        center_lon = primary_region.get("center_lon", -74.0060)
        radius_km = primary_region.get("radius_km", 10)
        
        affected_area_geojson = json.dumps({
            "type": "Feature",
            "geometry": {
                "type": "Point",  # Simplified - would create actual polygon
                "coordinates": [center_lon, center_lat]
            },
            "properties": {
                "radius_km": radius_km
            }
        })
        
        # Get infrastructure data from OSM monitoring
        osm_data = state["current_monitoring_data"].get("osm_overpass")
        infrastructure_data_json = json.dumps(osm_data.data if osm_data else {"elements": []})
        
        # Identify safe zones
        safe_zone_result = safe_zone_identifier.invoke({
            "affected_area_geojson": affected_area_geojson,
            "infrastructure_data_json": infrastructure_data_json,
            "disaster_type": classification["disaster_type"],
            "evacuation_radius_km": radius_km
        })
        
        # Parse safe zone result
        safe_zone_analysis = json.loads(safe_zone_result)
        
        # Convert to SafeZone objects
        safe_zones = []
        for zone_data in safe_zone_analysis["safe_zones"]:
            safe_zone = SafeZone(
                id=zone_data["id"],
                name=zone_data["name"],
                location=zone_data["location"],
                capacity=zone_data["capacity"],
                available_capacity=zone_data["available_capacity"],
                zone_type=zone_data["type"]
            )
            safe_zones.append(safe_zone)
        
        # Update state with safe zone analysis
        updated_state = {
            **state,
            "safe_zones": safe_zones,
            "evacuation_routes": safe_zone_analysis["evacuation_routes"],
            "next_action": "create_event_record",
            "last_update_time": datetime.now()
        }
        
        logger.info(f"Safe zone analysis completed: {len(safe_zones)} zones identified")
        
        return updated_state
        
    except Exception as e:
        error_msg = f"Safe zone analysis error: {str(e)}"
        logger.error(error_msg)
        
        return {
            **state,
            "processing_errors": state["processing_errors"] + [error_msg],
            "next_action": "create_event_record"
        }


async def create_event_record_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Create a DisasterEvent record for confirmed events.
    """
    logger.info("Starting create event record node")
    
    try:
        classification = state["classification_results"]
        
        if not classification:
            logger.error("No classification results to create event record")
            return {
                **state,
                "next_action": "wait_interval"
            }
        
        # Create disaster event
        primary_region = state["monitoring_regions"][0] if state["monitoring_regions"] else {}
        now = datetime.now()
        
        event = DisasterEvent(
            id=f"event_{now.strftime('%Y%m%d_%H%M%S')}",
            disaster_type=DisasterType(classification["disaster_type"]),
            severity=SeverityLevel(classification["severity_level"]),
            status=state.get("confirmation_status", AlertStatus.DETECTED),
            location={
                "type": "Point",
                "coordinates": [
                    primary_region.get("center_lon", -74.0060),
                    primary_region.get("center_lat", 40.7128)
                ]
            },
            confidence=classification["confidence_score"],
            source_apis=[
                source for source, data in state["current_monitoring_data"].items()
                if data.alerts_count > 0
            ],
            detected_at=now,
            last_updated=now,
            description=f"{classification['disaster_type'].title()} event detected via monitoring systems",
            affected_area_km2=state.get("impact_assessment", {}).get("affected_area_km2"),
            estimated_impact={
                "population_at_risk": state.get("population_at_risk", 0),
                "severity_score": state.get("severity_score", 0.0),
                "escalation_required": state.get("escalation_required", False)
            }
        )
        
        # Add to active events
        updated_active_events = state["active_events"] + [event]
        
        # Update event history
        updated_event_history = state["event_history"] + [event]
        if len(updated_event_history) > 50:  # Keep last 50 events
            updated_event_history = updated_event_history[-50:]
        
        # Update state
        updated_state = {
            **state,
            "active_events": updated_active_events,
            "event_history": updated_event_history,
            "current_event_id": event.id,
            "last_update_time": now
        }
        
        # Determine if planning workflow should be triggered
        if state.get("escalation_required", False) or classification["severity_level"] in ["high", "critical", "extreme"]:
            updated_state["planning_workflow_triggered"] = True
            updated_state["next_action"] = "trigger_planning_workflow"
            logger.info(f"Event created and planning workflow triggered: {event.id}")
        else:
            updated_state["next_action"] = "wait_interval"
            logger.info(f"Event created: {event.id}")
        
        return updated_state
        
    except Exception as e:
        error_msg = f"Create event record error: {str(e)}"
        logger.error(error_msg)
        
        return {
            **state,
            "processing_errors": state["processing_errors"] + [error_msg],
            "next_action": "wait_interval"
        }


async def trigger_planning_workflow_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Trigger the planning/management workflow for high-severity events.
    """
    logger.info("Starting trigger planning workflow node")
    
    try:
        current_event = None
        if state["current_event_id"]:
            current_event = next(
                (event for event in state["active_events"] if event.id == state["current_event_id"]),
                None
            )
        
        if not current_event:
            logger.error("No current event to trigger planning workflow")
            return {
                **state,
                "next_action": "wait_interval"
            }
        
        # Generate planning workflow ID
        planning_workflow_id = f"planning_{current_event.id}_{datetime.now().strftime('%H%M%S')}"
        
        # Define management actions needed
        management_actions = [
            "Coordinate emergency response teams",
            "Establish communication channels",
            "Manage evacuation operations",
            "Monitor situation updates",
            "Coordinate with local authorities"
        ]
        
        if current_event.severity in [SeverityLevel.CRITICAL, SeverityLevel.EXTREME]:
            management_actions.extend([
                "Deploy federal resources",
                "Coordinate media communications",
                "Activate disaster recovery operations"
            ])
        
        # Create alert messages
        alert_messages = [
            {
                "type": "emergency_alert",
                "severity": current_event.severity.value,
                "message": f"{current_event.disaster_type.value.title()} detected in {state['monitoring_regions'][0].get('name', 'monitored area')}",
                "timestamp": datetime.now().isoformat(),
                "event_id": current_event.id
            }
        ]
        
        # Update state
        updated_state = {
            **state,
            "planning_workflow_triggered": True,
            "planning_workflow_id": planning_workflow_id,
            "management_actions_needed": management_actions,
            "alert_messages": state["alert_messages"] + alert_messages,
            "notification_sent": True,
            "next_action": "continue_monitoring",
            "last_update_time": datetime.now()
        }
        
        logger.info(f"Planning workflow triggered: {planning_workflow_id} for event {current_event.id}")
        
        return updated_state
        
    except Exception as e:
        error_msg = f"Trigger planning workflow error: {str(e)}"
        logger.error(error_msg)
        
        return {
            **state,
            "processing_errors": state["processing_errors"] + [error_msg],
            "next_action": "wait_interval"
        }


async def wait_interval_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Wait for the configured monitoring interval before next polling cycle.
    """
    logger.info(f"Waiting {state['monitoring_interval_seconds']} seconds before next monitoring cycle")
    
    # In a real implementation, this would use a scheduler
    # For now, just update the state to continue monitoring
    
    return {
        **state,
        "next_action": "api_monitoring",
        "last_update_time": datetime.now()
    }


async def log_false_positive_node(state: DisasterDetectionState) -> DisasterDetectionState:
    """
    Log false positive detections for model improvement.
    """
    logger.info("Logging false positive detection")
    
    classification = state.get("classification_results", {})
    
    # In a real implementation, this would log to a database or file for analysis
    false_positive_log = {
        "timestamp": datetime.now().isoformat(),
        "classification": classification,
        "confirmation_confidence": state.get("confirmation_confidence", 0.0),
        "monitoring_data_summary": len(state["current_monitoring_data"])
    }
    
    logger.info(f"False positive logged: {false_positive_log}")
    
    return {
        **state,
        "next_action": "wait_interval",
        "last_update_time": datetime.now()
    }
