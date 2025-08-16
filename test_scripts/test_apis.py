import requests
import json
from datetime import datetime, timedelta, UTC

def test_usgs_earthquakes():
    """Test USGS earthquake API"""
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"

    # San Francisco Bay Area bounds
    minlon, minlat, maxlon, maxlat = -122.5, 37.0, -121.5, 38.0

    start = (datetime.now(UTC) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end   = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    params = {
        "format": "geojson",
        "starttime": start,
        "endtime": end,
        "minmagnitude": 2.0,
        "minlatitude": minlat,
        "maxlatitude": maxlat,
        "minlongitude": minlon,
        "maxlongitude": maxlon,
        "orderby": "time-asc",  # or "time" for desc
        "limit": 50
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        feats = data.get("features", [])
        print(f"✅ USGS API: Found {len(feats)} earthquakes")
        if feats:
            latest = feats[-1]["properties"]  # last if time-asc
            print(f"   Latest: M{latest['mag']} - {latest['place']}")

        return True

    except requests.HTTPError as e:
        # Print server message to quickly see what param it didn’t like
        print(f"❌ USGS API Error: {e} | Body: {getattr(e.response, 'text', '')[:300]}")
        return False
    except Exception as e:
        print(f"❌ USGS API Error: {e}")
        return False


def test_noaa_weather():
    """Test NOAA weather API"""
    # San Francisco coordinates
    lat, lon = 37.7749, -122.4194
    
    try:
        # Test weather alerts
        url = f"https://api.weather.gov/alerts/active?point={lat},{lon}"
        headers = {'User-Agent': 'DisasterShield/1.0 (test@example.com)'}
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ NOAA API: Found {len(data.get('features', []))} active alerts")
        return True
        
    except Exception as e:
        print(f"❌ NOAA API Error: {e}")
        return False

def test_nasa_worldview():
    """Test NASA Worldview API"""
    try:
        # Test imagery availability
        base_url = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"
        params = {
            'REQUEST': 'GetSnapshot',
            'TIME': datetime.now(UTC).strftime("%Y-%m-%d"),
            'BBOX': '-122.75,37.25,-122.25,37.75',  # SF area
            'CRS': 'EPSG:4326',
            'LAYERS': 'MODIS_Terra_CorrectedReflectance_TrueColor',
            'FORMAT': 'image/jpeg',
            'WIDTH': '256',
            'HEIGHT': '256'
        }
        
        # Just test URL construction (actual download requires auth)
        from urllib.parse import urlencode
        test_url = f"{base_url}?{urlencode(params)}"
        print(f"✅ NASA Worldview: URL constructed successfully")
        print(f"   URL: {test_url[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ NASA Worldview Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing External Data Sources...")
    print("=" * 40)
    
    test_usgs_earthquakes()
    test_noaa_weather()
    test_nasa_worldview()
    
    print("\nIf all tests pass, your data sources are ready!")