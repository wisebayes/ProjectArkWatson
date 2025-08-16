#!/usr/bin/env python3
"""
DisasterShield Configuration
Handles all environment variables and settings
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# IBM watsonx.ai Configuration
WATSONX_CREDENTIALS = {
    'url': os.getenv('WATSONX_URL', 'https://us-south.ml.cloud.ibm.com'),
    'apikey': os.getenv('WATSONX_API_KEY'),
    'project_id': os.getenv('WATSONX_PROJECT_ID')
}

# Validate required credentials
required_vars = ['WATSONX_API_KEY', 'WATSONX_PROJECT_ID']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f"⚠️  Missing required environment variables: {missing_vars}")
    print("📝 Create a .env file with:")
    print("WATSONX_API_KEY=your_api_key_here")
    print("WATSONX_PROJECT_ID=your_project_id_here")
    print("WATSONX_URL=https://us-south.ml.cloud.ibm.com")
else:
    print("✅ Configuration loaded successfully")

# Optional API keys
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

# Enhanced watsonx.ai model configuration for hackathon
ENHANCED_WATSONX_MODELS = {
    'decision_model': 'ibm/granite-3-2-8b-instruct',      # Primary decisions
    'strategy_model': 'ibm/granite-3-8b-instruct',        # Complex analysis  
    'guardian_model': 'ibm/granite-guardian-3-8b',        # Safety validation
    'vision_model': 'ibm/granite-vision-3-2-2b',          # Satellite imagery
    'code_model': 'ibm/granite-8b-code-instruct',         # Automation scripts
    'quick_model': 'ibm/granite-3-2b-instruct'            # Fast responses
}

# Judge demonstration settings
JUDGE_DEMO_CONFIG = {
    'voice_enabled': True,
    'multi_model_showcase': True,
    'orchestrate_workflows': True,
    'predictive_analytics': True,
    'conversation_ai': True,
    'presentation_mode': True
}

# Default Demo Scenarios
SCENARIOS = {
    'san_francisco': {
        'name': 'San Francisco M6.2 Earthquake',
        'bbox': (-122.5, 37.0, -121.5, 38.0),
        'center': (37.7749, -122.4194),
        'population': 875000,
        'description': 'Major earthquake striking San Francisco during rush hour'
    },
    'los_angeles': {
        'name': 'Los Angeles Wildfire',
        'bbox': (-118.5, 33.5, -117.5, 34.5),
        'center': (34.0522, -118.2437),
        'population': 650000,
        'description': 'Fast-moving wildfire threatening suburban communities'
    },
    'miami': {
        'name': 'Miami Hurricane Elena',
        'bbox': (-80.5, 25.0, -79.5, 26.0),
        'center': (25.7617, -80.1918),
        'population': 450000,
        'description': 'Category 4 hurricane making landfall'
    }
}

# Default scenario for demo
DEFAULT_SCENARIO = SCENARIOS['san_francisco']
DEFAULT_REGION_BBOX = DEFAULT_SCENARIO['bbox']
DEFAULT_CENTER = DEFAULT_SCENARIO['center']
DEFAULT_POPULATION = DEFAULT_SCENARIO['population']

# Application Settings
APP_SETTINGS = {
    'max_threats_to_process': 10,
    'response_timeout_seconds': 300,
    'enable_satellite_imagery': True,
    'enable_real_time_data': True,
    'demo_mode': True  # Set to False for production
}

# API Rate Limits and Timeouts
API_CONFIG = {
    'usgs_timeout': 30,
    'noaa_timeout': 30,
    'nasa_timeout': 45,
    'request_retry_count': 3,
    'rate_limit_delay': 1.0
}

# Communication Channels Configuration  
COMMUNICATION_CHANNELS = {
    'SMS': {
        'enabled': True,
        'max_length': 160,
        'delivery_rate': 0.98,
        'latency_seconds': 5
    },
    'Push_Notification': {
        'enabled': True,
        'max_length': 200,
        'delivery_rate': 0.94,
        'latency_seconds': 2
    },
    'Emergency_Broadcast': {
        'enabled': True,
        'max_length': 1000,
        'delivery_rate': 0.99,
        'latency_seconds': 1
    },
    'Social_Media': {
        'enabled': True,
        'max_length': 280,
        'delivery_rate': 0.85,
        'latency_seconds': 10
    },
    'Email': {
        'enabled': True,
        'max_length': 2000,
        'delivery_rate': 0.96,
        'latency_seconds': 15
    }
}

# Logging Configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'save_to_file': True,
    'log_file': 'disastershield.log'
}

def get_scenario(name: str = None):
    """Get scenario configuration by name"""
    if name is None:
        return DEFAULT_SCENARIO
    return SCENARIOS.get(name, DEFAULT_SCENARIO)

def validate_config():
    """Validate configuration and return status"""
    issues = []
    
    if not WATSONX_CREDENTIALS['apikey']:
        issues.append("Missing WATSONX_API_KEY")
    
    if not WATSONX_CREDENTIALS['project_id']:
        issues.append("Missing WATSONX_PROJECT_ID")
    
    return len(issues) == 0, issues

if __name__ == "__main__":
    # Test configuration when run directly
    print("🛡️ DisasterShield Configuration Test")
    print("=" * 40)
    
    valid, issues = validate_config()
    
    if valid:
        print("✅ Configuration is valid")
        print(f"📍 Default scenario: {DEFAULT_SCENARIO['name']}")
        print(f"🌐 watsonx.ai URL: {WATSONX_CREDENTIALS['url']}")
        print(f"🔑 API key: {'*' * 20}...{WATSONX_CREDENTIALS['apikey'][-4:] if WATSONX_CREDENTIALS['apikey'] else 'MISSING'}")
        print(f"📋 Project ID: {WATSONX_CREDENTIALS['project_id'][:8] if WATSONX_CREDENTIALS['project_id'] else 'MISSING'}...")
    else:
        print("❌ Configuration issues found:")
        for issue in issues:
            print(f"   - {issue}")
        print("\n📝 Create .env file with required variables")