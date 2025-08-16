"""
State schema for the disaster detection and management workflow.
Based on LangGraph patterns for agentic workflows.
"""

from typing import TypedDict, List, Dict, Any, Optional, Set
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
import geojson


class DisasterType(Enum):
    """Types of disasters we can detect and manage."""
    EARTHQUAKE = "earthquake"
    WILDFIRE = "wildfire"
    FLOOD = "flood"
    HURRICANE = "hurricane"
    TORNADO = "tornado"
    SEVERE_WEATHER = "severe_weather"
    VOLCANIC = "volcanic"
    LANDSLIDE = "landslide"
    UNKNOWN = "unknown"


class SeverityLevel(Enum):
    """Disaster severity classification."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"
    EXTREME = "extreme"


class AlertStatus(Enum):
    """Status of disaster alerts."""
    MONITORING = "monitoring"
    DETECTED = "detected"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class APISource(Enum):
    """Available data sources."""
    USGS_EARTHQUAKE = "usgs_earthquake"
    NOAA_WEATHER = "noaa_weather"
    FEMA_OPEN = "fema_open"
    NASA_WORLDVIEW = "nasa_worldview"
    OSM_OVERPASS = "osm_overpass"


class DisasterEvent(BaseModel):
    """Represents a detected disaster event."""
    id: str
    disaster_type: DisasterType
    severity: SeverityLevel
    status: AlertStatus
    location: Dict[str, Any]  # GeoJSON-like structure
    magnitude: Optional[float] = None
    confidence: float
    source_apis: List[APISource]
    detected_at: datetime
    last_updated: datetime
    description: str
    affected_area_km2: Optional[float] = None
    estimated_impact: Optional[Dict[str, Any]] = None


class SafeZone(BaseModel):
    """Represents a safe zone for evacuation."""
    id: str
    name: str
    location: Dict[str, Any]  # GeoJSON Point
    capacity: int
    available_capacity: int
    zone_type: str  # shelter, hospital, school, etc.
    contact_info: Optional[Dict[str, str]] = None


class ResponseTeam(BaseModel):
    """Represents an emergency response team."""
    team_id: str
    team_name: str
    team_type: str  # fire_rescue, medical, police, etc.
    base_location: Dict[str, Any]  # GeoJSON Point
    capacity: int
    specialization: str
    availability_status: str  # available, deployed, offline
    response_time_minutes: int
    equipment_level: str  # low, medium, high, very_high
    current_assignment: Optional[str] = None


class PopulationZone(BaseModel):
    """Represents a population zone with density data."""
    zone_id: str
    zone_name: str
    center_location: Dict[str, Any]  # GeoJSON Point
    radius_km: float
    population: int
    population_density_per_km2: int
    vulnerability_score: str  # low, medium, high, very_high
    demographics: str
    special_needs_population: int


class EvacuationRoute(BaseModel):
    """Represents an evacuation route from a zone to a safe area."""
    route_id: str
    from_zone_id: str
    to_zone_id: str
    route_geometry: Dict[str, Any]  # GeoJSON LineString
    distance_km: float
    estimated_time_minutes: int
    capacity_per_hour: int
    route_status: str  # clear, congested, blocked
    alternative_routes: List[str] = []


class TeamDeployment(BaseModel):
    """Represents a team deployment decision."""
    deployment_id: str
    team_id: str
    target_zone_id: str
    priority_level: str  # low, medium, high, critical
    deployment_reason: str
    estimated_arrival_time: datetime
    deployment_duration_hours: int
    coordination_instructions: str


class MonitoringData(BaseModel):
    """Data from API monitoring sources."""
    source: APISource
    timestamp: datetime
    data: Dict[str, Any]
    location_bounds: Optional[Dict[str, Any]] = None  # bbox
    alerts_count: int = 0
    raw_response: Optional[Dict[str, Any]] = None


# Main LangGraph State Schema
class DisasterDetectionState(TypedDict):
    """
    Main state for the disaster detection and management workflow.
    Following LangGraph patterns for state-first design.
    """
    
    # === CONFIGURATION ===
    monitoring_regions: List[Dict[str, Any]]  # Geographic bounds to monitor
    monitoring_interval_seconds: int
    confidence_threshold: float
    severity_escalation_rules: Dict[str, Any]
    
    # === MONITORING DATA ===
    current_monitoring_data: Dict[APISource, MonitoringData]
    monitoring_history: List[MonitoringData]
    last_api_poll_times: Dict[APISource, datetime]
    api_error_counts: Dict[APISource, int]
    
    # === DETECTED EVENTS ===
    active_events: List[DisasterEvent]
    event_history: List[DisasterEvent]
    current_event_id: Optional[str]  # Currently processing event
    
    # === WATSONX CLASSIFICATION ===
    classification_prompt: str
    watsonx_model_id: str
    classification_results: Dict[str, Any]
    prediction_confidence: float
    disaster_type_probabilities: Dict[DisasterType, float]
    
    # === WEB SEARCH CONFIRMATION ===
    search_queries: List[str]
    search_results: List[Dict[str, Any]]
    confirmation_status: AlertStatus
    confirmation_confidence: float
    news_articles_found: List[Dict[str, Any]]
    
    # === GEOSPATIAL ANALYSIS ===
    affected_areas: List[Dict[str, Any]]  # GeoJSON polygons
    population_at_risk: Optional[int]
    critical_infrastructure: List[Dict[str, Any]]  # Hospitals, schools, etc.
    safe_zones: List[SafeZone]
    
    # === SEVERITY ASSESSMENT ===
    severity_factors: Dict[str, float]
    severity_score: float
    escalation_required: bool
    impact_assessment: Dict[str, Any]
    
    # === WORKFLOW CONTROL ===
    workflow_phase: str  # "monitoring", "detection", "confirmation", "planning"
    next_action: str
    processing_errors: List[str]
    retry_count: int
    max_retries: int
    
    # === PLANNING WORKFLOW TRIGGER ===
    planning_workflow_triggered: bool
    planning_workflow_id: Optional[str]
    management_actions_needed: List[str]
    emergency_contacts: List[Dict[str, Any]]
    
    # === COMMUNICATION ===
    alert_messages: List[Dict[str, Any]]
    notification_sent: bool
    stakeholder_notifications: Dict[str, bool]
    
    # === PLANNING WORKFLOW DATA ===
    available_response_teams: List[ResponseTeam]
    population_zones: List[PopulationZone]
    evacuation_zones: List[Dict[str, Any]]  # From CSV data
    team_deployments: List[TeamDeployment]
    evacuation_routes: List[EvacuationRoute]
    
    # === PLANNING DECISIONS ===
    deployment_plan: Dict[str, Any]
    evacuation_plan: Dict[str, Any]
    resource_allocation: Dict[str, Any]
    coordination_instructions: List[str]
    
    # === OSRM ROUTING ===
    routing_results: Dict[str, Any]
    route_optimization_status: str
    traffic_conditions: Dict[str, Any]
    
    # === NOTIFICATION SYSTEM ===
    notification_messages: List[Dict[str, Any]]
    authority_contacts: List[Dict[str, str]]
    notification_status: Dict[str, bool]
    
    # === METADATA ===
    workflow_start_time: datetime
    last_update_time: datetime
    session_id: str
    debug_mode: bool


# Helper function to create initial state
def create_initial_state(
    monitoring_regions: List[Dict[str, Any]],
    session_id: str,
    confidence_threshold: float = 0.7,
    monitoring_interval: int = 60
) -> DisasterDetectionState:
    """Create initial state for disaster detection workflow."""
    now = datetime.now()
    
    return DisasterDetectionState(
        # Configuration
        monitoring_regions=monitoring_regions,
        monitoring_interval_seconds=monitoring_interval,
        confidence_threshold=confidence_threshold,
        severity_escalation_rules={
            "auto_escalate_severity": ["HIGH", "CRITICAL", "EXTREME"],
            "require_confirmation": ["MODERATE", "HIGH"],
            "immediate_action": ["CRITICAL", "EXTREME"]
        },
        
        # Monitoring
        current_monitoring_data={},
        monitoring_history=[],
        last_api_poll_times={},
        api_error_counts={source: 0 for source in APISource},
        
        # Events
        active_events=[],
        event_history=[],
        current_event_id=None,
        
        # WatsonX
        classification_prompt="",
        watsonx_model_id="ibm/granite-13b-instruct-v2",
        classification_results={},
        prediction_confidence=0.0,
        disaster_type_probabilities={},
        
        # Search confirmation
        search_queries=[],
        search_results=[],
        confirmation_status=AlertStatus.MONITORING,
        confirmation_confidence=0.0,
        news_articles_found=[],
        
        # Geospatial
        affected_areas=[],
        population_at_risk=None,
        critical_infrastructure=[],
        safe_zones=[],
        
        # Severity
        severity_factors={},
        severity_score=0.0,
        escalation_required=False,
        impact_assessment={},
        
        # Workflow
        workflow_phase="monitoring",
        next_action="poll_apis",
        processing_errors=[],
        retry_count=0,
        max_retries=3,
        
        # Planning trigger
        planning_workflow_triggered=False,
        planning_workflow_id=None,
        management_actions_needed=[],
        emergency_contacts=[],
        
        # Communication
        alert_messages=[],
        notification_sent=False,
        stakeholder_notifications={},
        
        # Planning workflow data
        available_response_teams=[],
        population_zones=[],
        evacuation_zones=[],
        team_deployments=[],
        evacuation_routes=[],
        
        # Planning decisions
        deployment_plan={},
        evacuation_plan={},
        resource_allocation={},
        coordination_instructions=[],
        
        # OSRM routing
        routing_results={},
        route_optimization_status="pending",
        traffic_conditions={},
        
        # Notification system
        notification_messages=[],
        authority_contacts=[],
        notification_status={},
        
        # Metadata
        workflow_start_time=now,
        last_update_time=now,
        session_id=session_id,
        debug_mode=False
    )
