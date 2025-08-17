"""
IBM WatsonX-powered agents for disaster detection and classification.
Uses LangChain tools with WatsonX models for intelligent analysis.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate
from langchain_ibm import WatsonxLLM
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

from core.state import (
    DisasterType, SeverityLevel, AlertStatus, MonitoringData, 
    DisasterEvent, APISource
)


logger = logging.getLogger(__name__)


class WatsonXDisasterClassifier:
    """WatsonX-powered disaster classification system."""
    
    def __init__(
        self,
        watsonx_api_key: str,
        watsonx_url: str = "https://us-south.ml.cloud.ibm.com",
        project_id: str = None,
        model_id: str = "ibm/granite-13b-instruct-v2"
    ):
        """Initialize the WatsonX disaster classifier.

        LLM client is created lazily to avoid auth errors when config is missing.
        """
        self.watsonx_params = {
            "decoding_method": "sample",
            "max_new_tokens": 500,
            "min_new_tokens": 10,
            "temperature": 0.3,  # Lower temperature for more consistent classification
            "top_k": 50,
            "top_p": 0.9,
        }

        # Defer LLM creation until first use to avoid triggering auth setup
        self._watsonx_model_id = model_id
        self._watsonx_url = watsonx_url
        self._watsonx_project_id = project_id
        self._watsonx_api_key = watsonx_api_key
        self.watsonx_llm: Optional[WatsonxLLM] = None

        def _make_llm() -> WatsonxLLM:
            api_key = self._watsonx_api_key or os.environ.get("WATSONX_APIKEY")
            kwargs = {
                "model_id": self._watsonx_model_id,
                "url": self._watsonx_url,
                "params": self.watsonx_params,
            }
            if api_key:
                kwargs["apikey"] = api_key
            if self._watsonx_project_id:
                kwargs["project_id"] = self._watsonx_project_id
            return WatsonxLLM(**kwargs)  # type: ignore[arg-type]

        self._create_watsonx_llm = _make_llm
        
        # Set up web search for confirmation
        search_wrapper = DuckDuckGoSearchAPIWrapper(
            time="d",  # Search from last day
            max_results=5
        )
        self.web_search = DuckDuckGoSearchRun(api_wrapper=search_wrapper)
        
        self.classification_prompt = PromptTemplate.from_template("""
You are an expert disaster detection and classification system. Analyze the provided monitoring data and determine if there are signs of potential disasters.

MONITORING DATA:
{monitoring_data_summary}

LOCATION: {location_info}

TASK: Analyze this data and provide a JSON response with the following structure:

{{
    "threat_detected": true/false,
    "disaster_type": "earthquake|wildfire|flood|hurricane|tornado|severe_weather|volcanic|landslide|unknown",
    "confidence_score": 0.0-1.0,
    "severity_level": "low|moderate|high|critical|extreme",
    "risk_factors": ["list", "of", "specific", "factors"],
    "recommendations": ["immediate", "actions", "needed"],
    "requires_confirmation": true/false,
    "reasoning": "detailed explanation of analysis"
}}

ANALYSIS GUIDELINES:
1. EARTHQUAKE: Look for magnitude ≥3.0, depth patterns, swarm activity
2. SEVERE WEATHER: Check for tornado/hurricane/storm warnings, wind speeds
3. FLOOD: Monitor precipitation rates, river levels, flash flood warnings
4. WILDFIRE: Track fire weather warnings, drought conditions, hotspot detections
5. Consider data recency, spatial clustering, and escalating patterns
6. Set requires_confirmation=true for moderate+ severity events

RESPOND WITH VALID JSON ONLY:
""")

    async def classify_monitoring_data(
        self,
        monitoring_data: List[MonitoringData],
        location: Dict[str, float]
    ) -> Dict[str, Any]:
        """Classify monitoring data for disaster threats using WatsonX."""
        try:
            # Prepare monitoring data summary
            data_summary = self._create_monitoring_summary(monitoring_data)
            location_info = f"Latitude: {location.get('lat', 'Unknown')}, Longitude: {location.get('lon', 'Unknown')}"
            
            # Create prompt
            prompt = self.classification_prompt.format(
                monitoring_data_summary=data_summary,
                location_info=location_info
            )
            
            # Ensure LLM is initialized lazily
            if self.watsonx_llm is None:
                self.watsonx_llm = self._create_watsonx_llm()

            # Get WatsonX classification
            response = await self.watsonx_llm.ainvoke(prompt)
            
            # Parse JSON response
            try:
                classification = json.loads(response.strip())
                
                # Validate and normalize response
                classification = self._validate_classification(classification)
                
                logger.info(f"WatsonX classification completed: {classification.get('disaster_type', 'unknown')} with confidence {classification.get('confidence_score', 0)}")
                
                return classification
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse WatsonX JSON response: {e}")
                logger.error(f"Raw response: {response}")
                
                # Fallback classification
                return self._create_fallback_classification(monitoring_data)
        
        except Exception as e:
            logger.error(f"WatsonX classification error: {e}")
            return self._create_fallback_classification(monitoring_data)
    
    def _create_monitoring_summary(self, monitoring_data: List[MonitoringData]) -> str:
        """Create a concise summary of monitoring data for classification."""
        summary_parts = []
        
        for data in monitoring_data:
            if data.alerts_count > 0:
                source_name = data.source.value.replace("_", " ").title()
                summary_parts.append(f"{source_name}: {data.alerts_count} alerts detected")
                
                # Add specific details based on source
                if data.source == APISource.USGS_EARTHQUAKE:
                    earthquakes = data.data.get("features", [])
                    if earthquakes:
                        max_mag = max([eq["properties"]["mag"] for eq in earthquakes if eq["properties"]["mag"]])
                        summary_parts.append(f"  - Max magnitude: {max_mag}")
                        
                elif data.source == APISource.NOAA_WEATHER:
                    alerts = data.data.get("features", [])
                    if alerts:
                        alert_types = [alert["properties"]["event"] for alert in alerts]
                        summary_parts.append(f"  - Alert types: {', '.join(set(alert_types))}")
                        
                elif data.source == APISource.FEMA_OPEN:
                    declarations = data.data.get("DisasterDeclarationsSummaries", [])
                    if declarations:
                        incident_types = [d["incidentType"] for d in declarations]
                        summary_parts.append(f"  - Recent incidents: {', '.join(set(incident_types))}")
        
        if not summary_parts:
            summary_parts.append("No significant alerts detected across monitored sources")
        
        return "\n".join(summary_parts)
    
    def _validate_classification(self, classification: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize the classification response."""
        validated = {
            "threat_detected": bool(classification.get("threat_detected", False)),
            "disaster_type": classification.get("disaster_type", "unknown"),
            "confidence_score": min(max(float(classification.get("confidence_score", 0.0)), 0.0), 1.0),
            "severity_level": classification.get("severity_level", "low"),
            "risk_factors": classification.get("risk_factors", []),
            "recommendations": classification.get("recommendations", []),
            "requires_confirmation": bool(classification.get("requires_confirmation", True)),
            "reasoning": classification.get("reasoning", "No reasoning provided")
        }
        
        # Validate enum values
        disaster_types = [dt.value for dt in DisasterType]
        if validated["disaster_type"] not in disaster_types:
            validated["disaster_type"] = "unknown"
            
        severity_levels = [sl.value for sl in SeverityLevel]
        if validated["severity_level"] not in severity_levels:
            validated["severity_level"] = "low"
        
        return validated
    
    def _create_fallback_classification(self, monitoring_data: List[MonitoringData]) -> Dict[str, Any]:
        """Create a fallback classification when WatsonX fails."""
        total_alerts = sum(data.alerts_count for data in monitoring_data)
        
        # Simple rule-based fallback
        threat_detected = total_alerts > 0
        confidence = min(total_alerts * 0.2, 0.8)  # Max 0.8 for fallback
        
        # Determine disaster type based on sources with alerts
        disaster_type = "unknown"
        for data in monitoring_data:
            if data.alerts_count > 0:
                if data.source == APISource.USGS_EARTHQUAKE:
                    disaster_type = "earthquake"
                    break
                elif data.source == APISource.NOAA_WEATHER:
                    disaster_type = "severe_weather"
                    break
        
        return {
            "threat_detected": threat_detected,
            "disaster_type": disaster_type,
            "confidence_score": confidence,
            "severity_level": "moderate" if total_alerts > 2 else "low",
            "risk_factors": [f"Fallback analysis: {total_alerts} total alerts"],
            "recommendations": ["Investigate alerts manually", "Monitor situation closely"],
            "requires_confirmation": threat_detected,
            "reasoning": "Fallback classification due to WatsonX processing error"
        }


@tool(return_direct=True)
def watsonx_disaster_classifier(
    monitoring_data_json: str = None,
    location_json: str = None,
    watsonx_config: Dict[str, str] = None,
    situation_description: Optional[str] = None,
) -> str:
    """
    Classify monitoring data for disaster threats using IBM WatsonX.
    
    Args:
        monitoring_data_json: JSON string of monitoring data
        location_json: JSON string with lat/lon
        watsonx_config: Configuration for WatsonX connection
    
    Returns:
        JSON string with classification results
    """
    try:
        # Parse inputs
        monitoring_data = json.loads(monitoring_data_json)
        location = json.loads(location_json)
        
        # Create classifier (in real implementation, this would be a singleton)
        classifier = WatsonXDisasterClassifier(
            watsonx_api_key=watsonx_config.get("api_key"),
            watsonx_url=watsonx_config.get("url", "https://us-south.ml.cloud.ibm.com"),
            project_id=watsonx_config.get("project_id"),
            model_id=watsonx_config.get("model_id", "ibm/granite-13b-instruct-v2")
        )
        
        # Note: This tool function can't be async, so we'd need to handle this differently
        # For now, return a template response with optional ongoing override

        # Detect ongoing situation from prompt
        ongoing = False
        detected_type = "unknown"
        if situation_description:
            text = situation_description.lower()
            ongoing = any(k in text for k in [
                "ongoing", "currently", "happening now", "in progress", "actively", "right now"
            ])
            keyword_type_map = {
                "earthquake": ["earthquake", "seismic", "aftershock"],
                "wildfire": ["wildfire", "bushfire", "fire front", "forest fire"],
                "flood": ["flood", "flooding", "inundation", "river overflow"],
                "hurricane": ["hurricane", "cyclone", "typhoon"],
                "tornado": ["tornado", "twister", "funnel cloud"],
                "severe_weather": ["storm", "hail", "wind warning", "blizzard"],
                "landslide": ["landslide", "mudslide"],
            }
            for dtype, keywords in keyword_type_map.items():
                if any(k in text for k in keywords):
                    detected_type = dtype
                    break

        response = {
            "threat_detected": True,
            "disaster_type": detected_type if detected_type != "unknown" else "earthquake",
            "confidence_score": 0.85 if ongoing else 0.75,
            "severity_level": "high" if ongoing else "moderate",
            "risk_factors": [
                "Ongoing situation indicated in prompt" if ongoing else "Template response from WatsonX tool"
            ],
            "recommendations": [
                "Activate response plan" if ongoing else "Monitor situation",
                "Prepare evacuation procedures" if ongoing else "Prepare for potential confirmation"
            ],
            "requires_confirmation": False if ongoing else True,
            "reasoning": "Ongoing override based on situation description" if ongoing else "This is a template response - implement async handling",
        }
        if ongoing:
            response["ongoing"] = True
        return json.dumps(response)
        
    except Exception as e:
        logger.error(f"WatsonX classifier tool error: {e}")
        return json.dumps({
            "threat_detected": False,
            "disaster_type": "unknown",
            "confidence_score": 0.0,
            "severity_level": "low",
            "risk_factors": [f"Classification error: {str(e)}"],
            "recommendations": ["Check tool configuration"],
            "requires_confirmation": False,
            "reasoning": "Tool execution failed"
        })


@tool(return_direct=True)
def web_search_disaster_confirmation(
    disaster_type: str,
    location_name: str,
    severity_level: str,
    time_window: str = "24h"
) -> str:
    """
    Search the web for confirmation of detected disaster events.
    
    Args:
        disaster_type: Type of disaster (earthquake, flood, etc.)
        location_name: Human-readable location name
        severity_level: Severity level of the event
        time_window: Time window for search (24h, 48h, etc.)
    
    Returns:
        JSON string with search results and confirmation status
    """
    try:
        # Set up search
        search_wrapper = DuckDuckGoSearchAPIWrapper(
            time="d" if time_window == "24h" else "w",
            max_results=10
        )
        web_search = DuckDuckGoSearchRun(api_wrapper=search_wrapper)
        
        # Create search queries
        queries = [
            f"{disaster_type} {location_name} {datetime.now().strftime('%Y')}",
            f"{disaster_type} alert {location_name}",
            f"disaster {location_name} today",
            f"{severity_level} {disaster_type} {location_name}"
        ]
        
        all_results = []
        confirmed_sources = []
        
        for query in queries[:2]:  # Limit to avoid rate limiting
            try:
                results = web_search.run(query)
                all_results.append({
                    "query": query,
                    "results": results
                })
                
                # Simple confirmation logic
                if any(keyword in results.lower() for keyword in [
                    disaster_type.lower(), "emergency", "alert", "warning"
                ]):
                    confirmed_sources.append(query)
                    
            except Exception as e:
                logger.error(f"Web search error for query '{query}': {e}")
        
        # Determine confirmation status
        confirmation_confidence = len(confirmed_sources) / len(queries) if queries else 0
        confirmed = confirmation_confidence > 0.3  # 30% threshold
        
        return json.dumps({
            "confirmed": confirmed,
            "confirmation_confidence": confirmation_confidence,
            "sources_found": len(confirmed_sources),
            "search_queries": queries[:2],
            "search_results": all_results,
            "confirmed_sources": confirmed_sources,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Web search confirmation error: {e}")
        return json.dumps({
            "confirmed": False,
            "confirmation_confidence": 0.0,
            "sources_found": 0,
            "search_queries": [],
            "search_results": [],
            "confirmed_sources": [],
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })


@tool(return_direct=True)
def severity_impact_analyzer(
    disaster_type: str,
    magnitude_or_intensity: str,
    affected_area_km2: float,
    population_density: int,
    critical_infrastructure_count: int
) -> str:
    """
    Analyze the severity and potential impact of a detected disaster.
    
    Args:
        disaster_type: Type of disaster
        magnitude_or_intensity: Magnitude (for earthquakes) or intensity measure
        affected_area_km2: Estimated affected area in square kilometers
        population_density: Population density per km2
        critical_infrastructure_count: Number of critical facilities in area
    
    Returns:
        JSON string with severity assessment and impact analysis
    """
    try:
        # Calculate impact factors
        population_at_risk = int(affected_area_km2 * population_density)
        
        # Disaster-specific severity calculation
        severity_score = 0.0
        severity_factors = {}
        
        if disaster_type == "earthquake":
            try:
                magnitude = float(magnitude_or_intensity)
                if magnitude >= 6.0:
                    severity_score += 0.4
                    severity_factors["magnitude"] = f"High magnitude: {magnitude}"
                elif magnitude >= 4.0:
                    severity_score += 0.2
                    severity_factors["magnitude"] = f"Moderate magnitude: {magnitude}"
            except:
                pass
        
        # Population impact
        if population_at_risk > 10000:
            severity_score += 0.3
            severity_factors["population"] = f"High population at risk: {population_at_risk:,}"
        elif population_at_risk > 1000:
            severity_score += 0.15
            severity_factors["population"] = f"Moderate population at risk: {population_at_risk:,}"
        
        # Critical infrastructure
        if critical_infrastructure_count > 10:
            severity_score += 0.2
            severity_factors["infrastructure"] = f"Many critical facilities: {critical_infrastructure_count}"
        elif critical_infrastructure_count > 0:
            severity_score += 0.1
            severity_factors["infrastructure"] = f"Some critical facilities: {critical_infrastructure_count}"
        
        # Area impact
        if affected_area_km2 > 100:
            severity_score += 0.1
            severity_factors["area"] = f"Large affected area: {affected_area_km2:.1f} km²"
        
        # Determine severity level
        if severity_score >= 0.8:
            severity_level = "extreme"
        elif severity_score >= 0.6:
            severity_level = "critical"
        elif severity_score >= 0.4:
            severity_level = "high"
        elif severity_score >= 0.2:
            severity_level = "moderate"
        else:
            severity_level = "low"
        
        # Generate recommendations
        recommendations = []
        if severity_level in ["critical", "extreme"]:
            recommendations.extend([
                "Immediate evacuation planning",
                "Activate emergency response teams",
                "Issue public warnings",
                "Coordinate with emergency services"
            ])
        elif severity_level == "high":
            recommendations.extend([
                "Prepare evacuation plans",
                "Alert emergency services",
                "Monitor situation closely",
                "Issue public advisories"
            ])
        else:
            recommendations.extend([
                "Continue monitoring",
                "Prepare contingency plans",
                "Inform relevant authorities"
            ])
        
        return json.dumps({
            "severity_level": severity_level,
            "severity_score": round(severity_score, 2),
            "severity_factors": severity_factors,
            "population_at_risk": population_at_risk,
            "affected_area_km2": affected_area_km2,
            "critical_infrastructure_count": critical_infrastructure_count,
            "impact_assessment": {
                "immediate_risk": severity_level in ["critical", "extreme"],
                "evacuation_needed": severity_score > 0.5,
                "emergency_response_required": severity_score > 0.6
            },
            "recommendations": recommendations,
            "escalation_required": severity_level in ["high", "critical", "extreme"],
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Severity analysis error: {e}")
        return json.dumps({
            "severity_level": "unknown",
            "severity_score": 0.0,
            "severity_factors": {},
            "population_at_risk": 0,
            "affected_area_km2": affected_area_km2,
            "critical_infrastructure_count": critical_infrastructure_count,
            "impact_assessment": {
                "immediate_risk": False,
                "evacuation_needed": False,
                "emergency_response_required": False
            },
            "recommendations": ["Manual assessment required"],
            "escalation_required": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })


@tool(return_direct=True)
def safe_zone_identifier(
    affected_area_geojson: str,
    infrastructure_data_json: str,
    disaster_type: str,
    evacuation_radius_km: float = 10.0
) -> str:
    """
    Identify safe zones and evacuation routes for disaster response.
    
    Args:
        affected_area_geojson: GeoJSON of affected area
        infrastructure_data_json: JSON of critical infrastructure locations
        disaster_type: Type of disaster for risk assessment
        evacuation_radius_km: Radius to search for safe zones
    
    Returns:
        JSON string with safe zones, evacuation routes, and capacity estimates
    """
    try:
        # Parse inputs
        affected_area = json.loads(affected_area_geojson)
        infrastructure_data = json.loads(infrastructure_data_json)
        
        # Identify potential safe zones based on infrastructure
        safe_zones = []
        evacuation_routes = []
        
        # Process infrastructure data
        for facility in infrastructure_data.get("elements", []):
            tags = facility.get("tags", {})
            amenity = tags.get("amenity", "")
            
            # Determine if facility can serve as safe zone
            if amenity in ["hospital", "school", "fire_station", "police"]:
                # Estimate capacity based on facility type
                capacity = {
                    "hospital": 100,
                    "school": 500,
                    "fire_station": 50,
                    "police": 30
                }.get(amenity, 50)
                
                # Get coordinates
                if "lat" in facility and "lon" in facility:
                    lat, lon = facility["lat"], facility["lon"]
                elif "center" in facility:
                    lat, lon = facility["center"]["lat"], facility["center"]["lon"]
                else:
                    continue
                
                safe_zone = {
                    "id": f"safe_zone_{facility['id']}",
                    "name": tags.get("name", f"{amenity.title()} {facility['id']}"),
                    "type": amenity,
                    "location": {"lat": lat, "lon": lon},
                    "capacity": capacity,
                    "available_capacity": capacity,  # Assume full availability initially
                    "distance_from_disaster": 0.0,  # Would calculate actual distance
                    "accessibility": {
                        "wheelchair_accessible": tags.get("wheelchair") == "yes",
                        "has_parking": "parking" in tags,
                        "public_transport": "public_transport" in tags
                    }
                }
                safe_zones.append(safe_zone)
        
        # Generate basic evacuation routes (template)
        for i, zone in enumerate(safe_zones[:3]):  # Limit to top 3
            route = {
                "id": f"evacuation_route_{i+1}",
                "destination_safe_zone": zone["id"],
                "route_type": "primary" if i == 0 else "secondary",
                "estimated_travel_time_minutes": 15 + (i * 5),  # Template times
                "route_status": "clear",
                "waypoints": [
                    {"lat": zone["location"]["lat"], "lon": zone["location"]["lon"]}
                ],
                "instructions": [
                    f"Proceed to {zone['name']}",
                    "Follow emergency signs",
                    "Stay calm and assist others"
                ]
            }
            evacuation_routes.append(route)
        
        # Calculate summary statistics
        total_capacity = sum(zone["capacity"] for zone in safe_zones)
        zones_by_type = {}
        for zone in safe_zones:
            zone_type = zone["type"]
            zones_by_type[zone_type] = zones_by_type.get(zone_type, 0) + 1
        
        return json.dumps({
            "safe_zones": safe_zones,
            "evacuation_routes": evacuation_routes,
            "summary": {
                "total_safe_zones": len(safe_zones),
                "total_capacity": total_capacity,
                "zones_by_type": zones_by_type,
                "primary_routes": len([r for r in evacuation_routes if r["route_type"] == "primary"])
            },
            "recommendations": [
                "Verify safe zone availability before directing evacuees",
                "Monitor route conditions in real-time",
                "Coordinate with emergency services",
                "Establish communication with safe zone managers"
            ],
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Safe zone identification error: {e}")
        return json.dumps({
            "safe_zones": [],
            "evacuation_routes": [],
            "summary": {
                "total_safe_zones": 0,
                "total_capacity": 0,
                "zones_by_type": {},
                "primary_routes": 0
            },
            "recommendations": ["Manual safe zone assessment required"],
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })
