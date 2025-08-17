"""
API clients for disaster monitoring data sources.
Implements clients for USGS, NOAA, FEMA, NASA and other data sources.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import aiohttp
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
import geojson

from core.state import APISource, MonitoringData, DisasterType


logger = logging.getLogger(__name__)


@dataclass
class APIResponse:
    """Standardized API response container."""
    source: APISource
    success: bool
    data: Dict[str, Any]
    error_message: Optional[str] = None
    timestamp: datetime = None
    location_bounds: Optional[Dict[str, Any]] = None
    alerts_count: int = 0

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class USGSEarthquakeClient:
    """Client for USGS Earthquake Catalog (FDSN/ComCat)."""
    
    BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1"
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.source = APISource.USGS_EARTHQUAKE
    
    async def get_recent_earthquakes(
        self,
        lat: float,
        lon: float,
        radius_km: float = 100,
        min_magnitude: float = 2.0,
        hours_back: int = 24
    ) -> APIResponse:
        """Get recent earthquakes near a location."""
        try:
            # Calculate time window
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours_back)
            
            params = {
                "format": "geojson",
                "latitude": lat,
                "longitude": lon,
                "maxradiuskm": radius_km,
                "minmagnitude": min_magnitude,
                "starttime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "endtime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "orderby": "time-asc"
            }
            
            async with self.session.get(
                f"{self.BASE_URL}/query",
                params=params,
                headers={"User-Agent": "ProjectArkWatson-DisasterMonitoring/1.0"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract bounding box from features
                    bbox = self._extract_bbox(data.get("features", []))
                    
                    return APIResponse(
                        source=self.source,
                        success=True,
                        data=data,
                        location_bounds=bbox,
                        alerts_count=len(data.get("features", []))
                    )
                else:
                    error_msg = f"USGS API error: {response.status}"
                    logger.error(error_msg)
                    return APIResponse(
                        source=self.source,
                        success=False,
                        data={},
                        error_message=error_msg
                    )
                    
        except Exception as e:
            error_msg = f"USGS client error: {str(e)}"
            logger.error(error_msg)
            return APIResponse(
                source=self.source,
                success=False,
                data={},
                error_message=error_msg
            )
    
    def _extract_bbox(self, features: List[Dict]) -> Optional[Dict[str, Any]]:
        """Extract bounding box from earthquake features."""
        if not features:
            return None
        
        lons = [f["geometry"]["coordinates"][0] for f in features]
        lats = [f["geometry"]["coordinates"][1] for f in features]
        
        return {
            "min_lon": min(lons),
            "max_lon": max(lons),
            "min_lat": min(lats),
            "max_lat": max(lats)
        }


class NOAAWeatherClient:
    """Client for NOAA National Weather Service API."""
    
    BASE_URL = "https://api.weather.gov"
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.source = APISource.NOAA_WEATHER
    
    async def get_active_alerts(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        area: Optional[str] = None
    ) -> APIResponse:
        """Get active weather alerts for a location or area."""
        try:
            params = {}
            if lat is not None and lon is not None:
                params["point"] = f"{lat},{lon}"
            elif area:
                params["area"] = area
            
            params["status"] = "actual"
            params["message_type"] = "alert"
            
            async with self.session.get(
                f"{self.BASE_URL}/alerts/active",
                params=params,
                headers={
                    "User-Agent": "ProjectArkWatson-DisasterMonitoring/1.0 (contact@arkwatson.dev)"
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract alert geometries for bbox
                    bbox = self._extract_alert_bbox(data.get("features", []))
                    
                    return APIResponse(
                        source=self.source,
                        success=True,
                        data=data,
                        location_bounds=bbox,
                        alerts_count=len(data.get("features", []))
                    )
                else:
                    error_msg = f"NOAA API error: {response.status}"
                    logger.error(error_msg)
                    return APIResponse(
                        source=self.source,
                        success=False,
                        data={},
                        error_message=error_msg
                    )
                    
        except Exception as e:
            error_msg = f"NOAA client error: {str(e)}"
            logger.error(error_msg)
            return APIResponse(
                source=self.source,
                success=False,
                data={},
                error_message=error_msg
            )
    
    async def get_forecast(self, lat: float, lon: float) -> APIResponse:
        """Get weather forecast for a location."""
        try:
            # First get the grid point
            async with self.session.get(
                f"{self.BASE_URL}/points/{lat},{lon}",
                headers={
                    "User-Agent": "ProjectArkWatson-DisasterMonitoring/1.0 (contact@arkwatson.dev)"
                }
            ) as response:
                if response.status != 200:
                    return APIResponse(
                        source=self.source,
                        success=False,
                        data={},
                        error_message=f"Failed to get grid point: {response.status}"
                    )
                
                point_data = await response.json()
                forecast_url = point_data["properties"]["forecast"]
            
            # Get the forecast
            async with self.session.get(
                forecast_url,
                headers={
                    "User-Agent": "ProjectArkWatson-DisasterMonitoring/1.0 (contact@arkwatson.dev)"
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return APIResponse(
                        source=self.source,
                        success=True,
                        data=data,
                        location_bounds={"lat": lat, "lon": lon}
                    )
                else:
                    return APIResponse(
                        source=self.source,
                        success=False,
                        data={},
                        error_message=f"Failed to get forecast: {response.status}"
                    )
                    
        except Exception as e:
            error_msg = f"NOAA forecast error: {str(e)}"
            logger.error(error_msg)
            return APIResponse(
                source=self.source,
                success=False,
                data={},
                error_message=error_msg
            )
    
    def _extract_alert_bbox(self, features: List[Dict]) -> Optional[Dict[str, Any]]:
        """Extract bounding box from alert features."""
        if not features:
            return None
        
        all_coords = []
        for feature in features:
            geometry = feature.get("geometry")
            if geometry and geometry.get("coordinates"):
                # Handle different geometry types
                if geometry["type"] == "Polygon":
                    all_coords.extend(geometry["coordinates"][0])
                elif geometry["type"] == "MultiPolygon":
                    for polygon in geometry["coordinates"]:
                        all_coords.extend(polygon[0])
        
        if not all_coords:
            return None
        
        lons = [coord[0] for coord in all_coords]
        lats = [coord[1] for coord in all_coords]
        
        return {
            "min_lon": min(lons),
            "max_lon": max(lons),
            "min_lat": min(lats),
            "max_lat": max(lats)
        }


class FEMAOpenDataClient:
    """Client for FEMA OpenFEMA data."""
    
    BASE_URL = "https://www.fema.gov/api/open"
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.source = APISource.FEMA_OPEN
    
    async def get_recent_declarations(
        self,
        days_back: int = 30,
        state: Optional[str] = None
    ) -> APIResponse:
        """Get recent disaster declarations."""
        try:
            # Calculate date filter
            since_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            
            params = {
                "$filter": f"declarationDate ge '{since_date}'",
                "$orderby": "declarationDate desc",
                "$select": "disasterNumber,declarationDate,incidentType,declarationTitle,state,femaRegion",
                "$top": "100"
            }
            
            if state:
                params["$filter"] += f" and state eq '{state}'"
            
            async with self.session.get(
                f"{self.BASE_URL}/v2/DisasterDeclarationsSummaries",
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return APIResponse(
                        source=self.source,
                        success=True,
                        data=data,
                        alerts_count=len(data.get("DisasterDeclarationsSummaries", []))
                    )
                else:
                    error_msg = f"FEMA API error: {response.status}"
                    logger.error(error_msg)
                    return APIResponse(
                        source=self.source,
                        success=False,
                        data={},
                        error_message=error_msg
                    )
                    
        except Exception as e:
            error_msg = f"FEMA client error: {str(e)}"
            logger.error(error_msg)
            return APIResponse(
                source=self.source,
                success=False,
                data={},
                error_message=error_msg
            )


class NASAWorldviewClient:
    """Client for NASA Worldview Snapshots."""
    
    BASE_URL = "https://wvs.earthdata.nasa.gov/api/v1"
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.source = APISource.NASA_WORLDVIEW
    
    async def get_snapshot_info(
        self,
        bbox: Tuple[float, float, float, float],  # (min_lon, min_lat, max_lon, max_lat)
        layers: List[str] = None,
        date: Optional[str] = None
    ) -> APIResponse:
        """Get satellite imagery snapshot information (not the actual image)."""
        try:
            if layers is None:
                # Default layers for disaster monitoring
                layers = [
                    "MODIS_Aqua_CorrectedReflectance_TrueColor",
                    "VIIRS_SNPP_DayNightBand_ENCC",
                    "MODIS_Fires_All"
                ]
            
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")
            
            params = {
                "REQUEST": "GetMap",
                "LAYERS": ",".join(layers),
                "BBOX": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
                "CRS": "EPSG:4326",
                "TIME": date,
                "WIDTH": "512",
                "HEIGHT": "512",
                "FORMAT": "image/png"
            }
            
            # For now, just return the request parameters without downloading
            # In a full implementation, you'd download and process the image
            
            return APIResponse(
                source=self.source,
                success=True,
                data={
                    "snapshot_params": params,
                    "bbox": bbox,
                    "date": date,
                    "layers": layers,
                    "url": f"{self.BASE_URL}/snapshot?" + "&".join([f"{k}={v}" for k, v in params.items()])
                },
                location_bounds={
                    "min_lon": bbox[0],
                    "min_lat": bbox[1],
                    "max_lon": bbox[2],
                    "max_lat": bbox[3]
                }
            )
                    
        except Exception as e:
            error_msg = f"NASA Worldview client error: {str(e)}"
            logger.error(error_msg)
            return APIResponse(
                source=self.source,
                success=False,
                data={},
                error_message=error_msg
            )


class OSMOverpassClient:
    """Client for OpenStreetMap Overpass API."""
    
    BASE_URL = "https://overpass-api.de/api"
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.source = APISource.OSM_OVERPASS
    
    async def get_critical_infrastructure(
        self,
        bbox: Tuple[float, float, float, float],  # (min_lat, min_lon, max_lat, max_lon)
        amenity_types: List[str] = None
    ) -> APIResponse:
        """Get critical infrastructure (hospitals, fire stations, etc.) in an area."""
        try:
            if amenity_types is None:
                amenity_types = ["hospital", "fire_station", "police", "school"]
            
            # Build Overpass QL query
            amenity_filter = "|".join(amenity_types)
            query = f"""
            [out:json][timeout:25];
            (
              node["amenity"~"^({amenity_filter})$"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
              way["amenity"~"^({amenity_filter})$"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
              relation["amenity"~"^({amenity_filter})$"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
            );
            out center meta;
            """
            
            async with self.session.post(
                f"{self.BASE_URL}/interpreter",
                data=query
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return APIResponse(
                        source=self.source,
                        success=True,
                        data=data,
                        location_bounds={
                            "min_lat": bbox[0],
                            "min_lon": bbox[1],
                            "max_lat": bbox[2],
                            "max_lon": bbox[3]
                        },
                        alerts_count=len(data.get("elements", []))
                    )
                else:
                    error_msg = f"OSM Overpass API error: {response.status}"
                    logger.error(error_msg)
                    return APIResponse(
                        source=self.source,
                        success=False,
                        data={},
                        error_message=error_msg
                    )
                    
        except Exception as e:
            error_msg = f"OSM Overpass client error: {str(e)}"
            logger.error(error_msg)
            return APIResponse(
                source=self.source,
                success=False,
                data={},
                error_message=error_msg
            )


class DisasterMonitoringService:
    """Coordinated service for monitoring multiple data sources."""
    
    def __init__(self):
        self.session = None
        self.clients = {}
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        self.clients = {
            APISource.USGS_EARTHQUAKE: USGSEarthquakeClient(self.session),
            APISource.NOAA_WEATHER: NOAAWeatherClient(self.session),
            APISource.FEMA_OPEN: FEMAOpenDataClient(self.session),
            APISource.NASA_WORLDVIEW: NASAWorldviewClient(self.session),
            APISource.OSM_OVERPASS: OSMOverpassClient(self.session)
        }
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def poll_all_sources(
        self,
        lat: float,
        lon: float,
        radius_km: float = 100
    ) -> Dict[APISource, APIResponse]:
        """Poll all available data sources for a location."""
        tasks = []
        
        # USGS Earthquakes
        tasks.append(
            self.clients[APISource.USGS_EARTHQUAKE].get_recent_earthquakes(
                lat, lon, radius_km
            )
        )
        
        # NOAA Weather Alerts
        tasks.append(
            self.clients[APISource.NOAA_WEATHER].get_active_alerts(lat, lon)
        )
        
        # FEMA Declarations (national)
        tasks.append(
            self.clients[APISource.FEMA_OPEN].get_recent_declarations()
        )
        
        # NASA Worldview (satellite imagery info)
        bbox = (
            lon - radius_km/111,  # rough km to degrees conversion
            lat - radius_km/111,
            lon + radius_km/111,
            lat + radius_km/111
        )
        tasks.append(
            self.clients[APISource.NASA_WORLDVIEW].get_snapshot_info(bbox)
        )
        
        # OSM Critical Infrastructure
        osm_bbox = (
            lat - radius_km/111,
            lon - radius_km/111,
            lat + radius_km/111,
            lon + radius_km/111
        )
        tasks.append(
            self.clients[APISource.OSM_OVERPASS].get_critical_infrastructure(osm_bbox)
        )
        
        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Map results back to sources
        sources = [
            APISource.USGS_EARTHQUAKE,
            APISource.NOAA_WEATHER,
            APISource.FEMA_OPEN,
            APISource.NASA_WORLDVIEW,
            APISource.OSM_OVERPASS
        ]
        
        response_map = {}
        for source, result in zip(sources, results):
            if isinstance(result, Exception):
                logger.error(f"Error polling {source}: {result}")
                response_map[source] = APIResponse(
                    source=source,
                    success=False,
                    data={},
                    error_message=str(result)
                )
            else:
                response_map[source] = result
        
        return response_map
    
    def convert_to_monitoring_data(
        self,
        api_responses: Dict[APISource, APIResponse]
    ) -> List[MonitoringData]:
        """Convert API responses to monitoring data objects."""
        monitoring_data = []
        
        for source, response in api_responses.items():
            data = MonitoringData(
                source=source,
                timestamp=response.timestamp,
                data=response.data,
                location_bounds=response.location_bounds,
                alerts_count=response.alerts_count,
                raw_response=response.data if response.success else None
            )
            monitoring_data.append(data)
        
        return monitoring_data


# Template disaster prediction model function
async def predict_disaster_risk(
    monitoring_data: List[MonitoringData],
    location: Dict[str, float]  # {"lat": lat, "lon": lon}
) -> Dict[str, Any]:
    """
    Template function for disaster prediction model.
    In a real implementation, this would use ML models to predict disaster risk.
    """
    # Placeholder implementation
    risk_score = 0.0
    risk_factors = []
    predicted_disasters = []
    
    for data in monitoring_data:
        if data.source == APISource.USGS_EARTHQUAKE and data.alerts_count > 0:
            risk_score += 0.3
            risk_factors.append("Recent seismic activity detected")
            
        elif data.source == APISource.NOAA_WEATHER and data.alerts_count > 0:
            risk_score += 0.4
            risk_factors.append("Active weather alerts in area")
            
        elif data.source == APISource.FEMA_OPEN and data.alerts_count > 0:
            risk_score += 0.2
            risk_factors.append("Recent disaster declarations nearby")
    
    # Determine predicted disaster types based on data
    if any("earthquake" in rf.lower() or "seismic" in rf.lower() for rf in risk_factors):
        predicted_disasters.append(DisasterType.EARTHQUAKE)
    if any("weather" in rf.lower() or "storm" in rf.lower() for rf in risk_factors):
        predicted_disasters.append(DisasterType.SEVERE_WEATHER)
    
    return {
        "risk_score": min(risk_score, 1.0),  # Cap at 1.0
        "risk_factors": risk_factors,
        "predicted_disasters": predicted_disasters,
        "confidence": 0.7,  # Template confidence
        "model_version": "template_v1.0",
        "location": location,
        "timestamp": datetime.now().isoformat()
    }
