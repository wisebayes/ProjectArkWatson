Seismic and Geohazards

- USGS Earthquake Catalog (FDSN/ComCat)
    - Purpose: Real-time and historical earthquakes (detection, aftershocks, AOI filtering)
    - Usage: /fdsnws/event/1/query (time, bbox, mag, format=geojson), /count for quick checks; realtime GeoJSON feeds for stream-like polling
    - Auth/Rate: No auth; respectful polling (e.g., 30–60s)
    - Notes: Normalize to GeoJSON; fields: id, mag, place, time, geometry; use updatedAfter for incremental pulls
    - References:[earthquake.usgs+1](https://earthquake.usgs.gov/fdsnws/event/1/)
- Xweather Earthquakes (optional)
    - Purpose: USGS-backed aggregator with convenient spatial queries
    - Usage: Endpoints: within, closest, affects; JSON
    - Auth/Rate: API key
    - Notes: Use only if you need their advanced query patterns
    - References:[xweather](https://www.xweather.com/docs/weather-api/endpoints/earthquakes)

Meteorology, Forecasts, and Alerts

- National Weather Service (NOAA) API
    - Purpose: U.S. forecasts, observations, grids; official Watches/Warnings/Advisories (Alerts)
    - Usage: /points/{lat,lon} → follow links (gridpoints, forecast, stations); Alerts: /alerts and /alerts/active with filters (area, point, zone, event, status)
    - Formats: JSON/GeoJSON, alerts also in CAP XML
    - Auth/Rate: No auth; strong User-Agent required; be gentle (≤1 request/30s for certain endpoints, cache aggressively)
    - Notes: Use geolocation guide for county/zone vs point filtering; CAP is canonical text, GeoJSON for geofences
    - References:[weather+3](https://www.weather.gov/documentation/services-web-api)
- OpenWeatherMap (global augmentation)
    - Purpose: Global current/forecast outside the U.S. or as a secondary source
    - Usage: /data/2.5/weather, /forecast, One Call; filter by bbox/city ids to reduce calls
    - Formats: JSON
    - Auth/Rate: API key; free tier ~60 req/min
    - Notes: Use as fallback where NWS lacks coverage

Satellite Imagery and Disaster Mapping

- NASA Worldview Snapshots
    - Purpose: Rapid imagery snapshots for AOI/time/layers (smoke, floods, fire, cloud)
    - Usage: /api/v1/snapshot with bbox, layers, time, CRS, format
    - Formats: Raster images (PNG/JPEG/GeoTIFF for some)
    - Auth/Rate: Earthdata login for some layers
    - Notes: Cache tiles; keep layer list minimal; use for before/after overlays
- Copernicus EMS (Emergency Management Service)
    - Purpose: Event-specific mapping products: flood extent, fire perimeters, damage grading
    - Usage: Browse mission pages; download vector/raster products
    - Formats: GeoTIFF, Shapefile/GeoPackage, PDFs
    - Auth/Rate: Free access; attribution required
    - Notes: Ideal for scenario overlays and evaluation
    - References:[mapping.emergency.copernicus](https://mapping.emergency.copernicus.eu/)

Mobility, Routing, and Points of Interest

- OpenStreetMap Overpass
    - Purpose: Road network, POIs (hospitals, fire stations, schools), barriers
    - Usage: Overpass QL/JSON; query highways, amenity=hospital, emergency=*, shelter-related tags
    - Formats: JSON/XML; convert to GeoJSON
    - Auth/Rate: No auth; throttle; prefer mirrored endpoints/caching
    - Notes: Limit AOI; pre-warm queries; store stable POIs locally
- Routing Engine (choose one)
    - OSRM (self-host): Car/foot routing on OSM; fastest setup via Docker
    - OpenRouteService (hosted): Routing, isochrones, matrix; avoids polygons
    - Usage: Compute evac routes with avoid-polygons from hazard layers (flood/fire/closures)
    - Auth/Rate: OSRM none; ORS requires API key
    - Notes: For hackathon, ORS hosted is quickest; for offline demo, ship OSRM with pre-cut region

Disasters, Declarations, and Recovery

- FEMA OpenFEMA (core)
    - Purpose: Disaster declarations, assistance programs, mission assignments, IPAWS archives, IA/PA stats
    - Usage: REST JSON with $filter, $select, $orderby; pagination via $skip; datasets have versioned names
    - Formats: JSON, CSV
    - Auth/Rate: No auth
    - Notes: Use DisasterDeclarationsSummaries for historical validation and to label scenarios; GIS hub provides layers
    - References:[fema+3](https://www.fema.gov/about/openfema/data-sets)
- FEMA Disaster Declarations (Data.gov mirror)
    - Purpose: Catalog view and direct dataset access
    - Usage: Download or API; join to admin boundaries for maps
    - Notes: Align fields with OpenFEMA
    - References:[catalog.data](https://catalog.data.gov/dataset/disaster-declarations-summaries-nemis)
- EM-DAT Global Disaster Database
    - Purpose: Macro-level historical benchmarking and impact metrics (global)
    - Usage: Download access per terms; not real-time
    - Notes: Use for presentation baselines and cross-country comparisons
    - References:[emdat](https://www.emdat.be/)
- Humanitarian Data Exchange (HDX)
    - Purpose: Crisis-relevant datasets: admin boundaries, population, shelters, health facilities
    - Usage: Search dataset API; verify currency and licensing
    - Notes: Great for international AOIs
    - References:[data.humdata](https://data.humdata.org/dataset)

Hydrology, Wildfire, Tropical Cyclones (add if in scope)

- NOAA National Water Model/AHPS
    - Purpose: River forecasts, flood stages, inundation guidance
    - Usage: Pull station forecasts and flood categories
    - Notes: Use to derive flood polygons for “avoid” routing
- NASA FIRMS (VIIRS/MODIS)
    - Purpose: Active fire detections
    - Usage: REST/tiles per AOI/time window
    - Notes: Convert hotspots to perimeters cautiously; combine with NWS red flag warnings
- NHC (National Hurricane Center) and SPC (Storm Prediction Center)
    - Purpose: Tropical tracks/advisories; convective outlooks/tornado watches
    - Usage: JSON/KML products and shapefiles
    - Notes: Use for hurricane and severe convective scenario playback

Citizen Communications and Alerts

- IPAWS Archive via OpenFEMA
    - Purpose: Historical WEA/EAS messages for demo playback
    - Usage: Query message metadata/content where available
    - Notes: Operational IPAWS needs authorization; for demo use NWS alerts + your messaging provider
    - References:[fema+1](https://www.fema.gov/about/reports-and-data/openfema)
- Messaging providers (Twilio, SendGrid)
    - Purpose: SMS/email/app push channels
    - Usage: API for templated, geo-targeted sends; rate-limit to avoid throttling
    - Notes: Maintain opt-out and delivery logging

Geospatial Base Layers and Admin Boundaries

- FEMA Geospatial Resource Center
    - Purpose: FEMA-curated layers (flood zones, boundaries, facilities)
    - Usage: ArcGIS Hub services; WMS/FeatureServer endpoints
    - Notes: Useful authoritative overlays
    - References:[gis-fema.hub.arcgis](https://gis-fema.hub.arcgis.com/pages/data-catalog)
- HDX/UN OCHA Admin Boundaries
    - Purpose: Global admin levels (ADM0–ADM3)
    - Usage: GeoPackage/GeoJSON; standardize to WGS84
    - Notes: Essential for joins and geo-targeting
    - References:[data.humdata](https://data.humdata.org/dataset)

Developer and Implementation References

- NWS API Docs and Alerts Reference
    - What: Endpoints, headers, examples; alerts structure, CAP mapping
    - Key: Always set User-Agent; use /alerts/active with point/area filters; respect caching headers
    - References:[weather+2](https://www.weather.gov/documentation/services-web-alerts)
- NWS Alerts Geolocation Primer
    - What: Correct use of county vs zone vs point filters
    - Key: For per-user guidance, prefer ?point=lat,lon to avoid over-alerting
    - References:[weather](https://www.weather.gov/media/documentation/docs/NWS_Geolocation.pdf)
- USGS ComCat Docs
    - What: Field meanings, query parameters, feed cadence
    - Key: Use updatedAfter for deltas; prefer GeoJSON; understand depth and mag types
    - References:[earthquake.usgs+1](https://earthquake.usgs.gov/data/comcat/)
- FEMA OpenFEMA Docs and Data Sets
    - What: Dataset catalog, versioning, API query semantics
    - Key: Use $filter and pagination; datasets change over time—pin versions
    - References:[dhs+2](https://www.dhs.gov/xlibrary/assets/digital-strategy/data.xlsx)

Implementation cheat sheet by table

- Real-time detection
    - USGS FDSN /query GeoJSON for quakes[earthquake.usgs+1](https://earthquake.usgs.gov/fdsnws/event/1/)
    - NWS /alerts/active with ?point=lat,lon for WWA[weather+1](https://www.weather.gov/documentation/services-web-api)
- Forecast context
    - NWS /points → /gridpoints for tailored forecasts[weather](https://www.weather.gov/documentation/services-web-api)
    - OpenWeatherMap One Call for global AOIs
- Mapping and situational awareness
    - NASA Worldview snapshots for before/after imagery
    - Copernicus EMS vector/raster overlays for floods/fires[mapping.emergency.copernicus](https://mapping.emergency.copernicus.eu/)
    - FEMA GIS hub layers for authoritative overlays[gis-fema.hub.arcgis](https://gis-fema.hub.arcgis.com/pages/data-catalog)
- Routing and POIs
    - OSM Overpass for roads and critical facilities
    - ORS/OSRM for evac routes with avoid-polygons
- Historical validation and benchmarking
    - FEMA OpenFEMA Declarations, IA/PA datasets[fema+2](https://www.fema.gov/about/openfema/data-sets)
    - EM‑DAT global benchmarking[emdat](https://www.emdat.be/)
    - HDX boundaries/population for joins[data.humdata](https://data.humdata.org/dataset)
- Citizen communication
    - NWS alert text (CAP) → templates
    - IPAWS archived messages for demo playback[fema+1](https://www.fema.gov/about/reports-and-data/openfema)
    - Twilio/SendGrid for actual sends

Practical usage guidelines

- Headers: For api.weather.gov, always include a descriptive User-Agent with contact URL/email; honor ETag/Last-Modified for caching.[weather-gov.github+1](https://weather-gov.github.io/api/general-faqs)
- Polling cadence: Quakes 30–60s; alerts 30–60s; forecasts hourly; imagery on-demand and cached per scenario.
- Geo models: Use WGS84; compute convex hulls for alert polygons if needed; buffer hazards by road class sensitivity.
- Data contracts: Normalize all feeds to internal GeoJSON with a consistent schema: source, id, geometry, when, severity, confidence.
- Backoff: Implement exponential backoff with jitter; respect 429s and Retry-After.
- Persistence: Store raw + normalized; index by time and AOI; precompute tiles for map.
- Testing: Use small AOIs and time windows during development; widen for demo day.

Would you like me to generate:

- A machine-readable catalog (CSV/JSON) of these sources with fields: name, category, base_url, key_endpoints, format, auth, rate_limit, sample_request, license
- Ready-to-run curl/Python snippets per source
- A minimal ETL scaffold (Python) to hydrate a PostGIS or SQLite/Parquet store for your demo

Citations for referenced items

- NWS API and alerts docs, geolocation primer, FAQs/OpenAPI[weather+3](https://www.weather.gov/documentation/services-web-alerts)
- USGS FDSN Earthquake Catalog and ComCat docs[earthquake.usgs+1](https://earthquake.usgs.gov/data/comcat/)
- FEMA OpenFEMA datasets, overview, DHS listing, FEMA GIS hub; Data.gov declaration summaries[dhs+4](https://www.dhs.gov/xlibrary/assets/digital-strategy/data.xlsx)
- Copernicus EMS mapping portal[mapping.emergency.copernicus](https://mapping.emergency.copernicus.eu/)
- EM‑DAT; HDX[emdat+1](https://www.emdat.be/)
1. https://earthquake.usgs.gov/fdsnws/event/1/
2. https://earthquake.usgs.gov/data/comcat/
3. https://www.xweather.com/docs/weather-api/endpoints/earthquakes
4. https://www.weather.gov/documentation/services-web-api
5. https://www.weather.gov/documentation/services-web-alerts
6. https://www.weather.gov/media/documentation/docs/NWS_Geolocation.pdf
7. https://weather-gov.github.io/api/general-faqs
8. [https://mapping.emergency.copernicus.eu](https://mapping.emergency.copernicus.eu/)
9. https://www.fema.gov/about/openfema/data-sets
10. https://www.fema.gov/about/reports-and-data/openfema
11. https://www.dhs.gov/xlibrary/assets/digital-strategy/data.xlsx
12. https://gis-fema.hub.arcgis.com/pages/data-catalog
13. https://catalog.data.gov/dataset/disaster-declarations-summaries-nemis
14. [https://www.emdat.be](https://www.emdat.be/)
15. https://data.humdata.org/dataset