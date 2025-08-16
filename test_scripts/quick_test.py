#!/usr/bin/env python3
"""
Quick System Verification for DisasterShield
Run this before your demo to make sure everything works
"""

import os
import sys
import requests
import json
from datetime import datetime, timedelta

def check_env_file():
    """Check if .env file exists and has required variables"""
    print("1. Checking environment configuration...")
    
    if not os.path.exists('.env'):
        print("   ❌ .env file not found!")
        print("   📝 Create .env file with your IBM watsonx credentials")
        return False
    
    required_vars = ['WATSONX_API_KEY', 'WATSONX_PROJECT_ID', 'WATSONX_URL']
    missing = []
    
    from dotenv import load_dotenv
    load_dotenv()
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"   ❌ Missing environment variables: {missing}")
        return False
    
    print("   ✅ Environment configuration OK")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    print("2. Checking Python dependencies...")
    
    required_packages = [
        'ibm_watsonx_ai',
        'requests', 
        'pandas',
        'aiohttp'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"   ❌ Missing packages: {missing}")
        print("   💡 Run: pip install -r requirements.txt")
        return False
    
    print("   ✅ All dependencies installed")
    return True

def test_watsonx_connection():
    """Test IBM watsonx.ai connection"""
    print("3. Testing IBM watsonx.ai connection...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        credentials = {
            'url': os.getenv('WATSONX_URL'),
            'apikey': os.getenv('WATSONX_API_KEY'),
            'project_id': os.getenv('WATSONX_PROJECT_ID')
        }
        
        from ibm_watsonx_ai.foundation_models import Model
        from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
        
        model = Model(
            model_id="ibm/granite-3.2-8b-instruct",
            params={
                GenParams.DECODING_METHOD: "greedy",
                GenParams.MAX_NEW_TOKENS: 50,
                GenParams.TEMPERATURE: 0.1
            },
            credentials=credentials,
            project_id=credentials['project_id']
        )
        
        # Quick test
        response = model.generate_text("Test: What is 2+2?")
        
        print("   ✅ watsonx.ai connection successful")
        print(f"   🤖 Model response: {response[:50]}...")
        return True
        
    except Exception as e:
        print(f"   ❌ watsonx.ai connection failed: {e}")
        print("   💡 Check your API key and project ID in .env file")
        return False

def test_external_apis():
    """Test external data source APIs"""
    print("4. Testing external data sources...")
    
    success_count = 0
    total_tests = 3
    
    # Test USGS
    try:
        url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
        params = {
            'format': 'geojson',
            'starttime': (datetime.utcnow() - timedelta(days=1)).isoformat(),
            'minmagnitude': 4.0,
            'limit': 5
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"   ✅ USGS Earthquakes: {len(data['features'])} recent events")
        success_count += 1
    except Exception as e:
        print(f"   ⚠️  USGS API issue: {e}")
    
    # Test NOAA
    try:
        url = "https://api.weather.gov/alerts/active"
        headers = {'User-Agent': 'DisasterShield/1.0 (test@example.com)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"   ✅ NOAA Weather: {len(data.get('features', []))} active alerts")
        success_count += 1
    except Exception as e:
        print(f"   ⚠️  NOAA API issue: {e}")
    
    # Test NASA Worldview (just URL construction)
    try:
        base_url = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"
        params = {
            'REQUEST': 'GetSnapshot',
            'TIME': datetime.utcnow().strftime("%Y-%m-%d"),
            'BBOX': '-122.5,37.0,-121.5,38.0',
            'LAYERS': 'MODIS_Terra_CorrectedReflectance_TrueColor',
            'FORMAT': 'image/jpeg'
        }
        from urllib.parse import urlencode
        test_url = f"{base_url}?{urlencode(params)}"
        print("   ✅ NASA Worldview: URL construction OK")
        success_count += 1
    except Exception as e:
        print(f"   ⚠️  NASA Worldview issue: {e}")
    
    print(f"   📊 Data sources: {success_count}/{total_tests} working")
    return success_count >= 2  # At least 2 out of 3 should work

def test_disaster_agents():
    """Test the main disaster agents module"""
    print("5. Testing DisasterShield agents...")
    
    try:
        from disaster_agents import DisasterShieldOrchestrator
        from config import WATSONX_CREDENTIALS
        
        # Initialize orchestrator
        orchestrator = DisasterShieldOrchestrator(WATSONX_CREDENTIALS)
        
        # Test system status
        status = orchestrator.get_system_status()
        
        if status['system_health']['core_ai_models'] == 'OPERATIONAL':
            print("   ✅ DisasterShield agents initialized successfully")
            print(f"   🎯 System health: {status['system_health']['core_ai_models']}")
            return True
        else:
            print("   ❌ DisasterShield agents not fully operational")
            return False
            
    except Exception as e:
        print(f"   ❌ DisasterShield agents failed: {e}")
        print("   💡 Check that disaster_agents.py and config.py are in the same directory")
        return False

def main():
    """Run all verification tests"""
    print("🛡️ DisasterShield System Verification")
    print("🎯 Pre-Demo Checklist")
    print("=" * 50)
    
    tests = [
        check_env_file,
        check_dependencies, 
        test_watsonx_connection,
        test_external_apis,
        test_disaster_agents
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"   ❌ Test failed with error: {e}")
            results.append(False)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("🏁 VERIFICATION SUMMARY")
    print("-" * 30)
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL SYSTEMS GO! You're ready for the demo!")
        print("🚀 Run: python run_demo.py")
        return 0
    elif passed >= 3:
        print("⚠️  Minor issues detected, but demo should work")
        print("🚀 Run: python run_demo.py")
        return 0
    else:
        print("❌ Critical issues found. Fix these before demo:")
        for i, (test, result) in enumerate(zip(tests, results), 1):
            if not result:
                print(f"   {i}. {test.__name__}")
        return 1

if __name__ == "__main__":
    sys.exit(main())