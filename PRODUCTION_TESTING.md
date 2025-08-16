# ProjectArkWatson Production Testing Guide

This guide explains how to run production tests with real API keys and services.

## 🔧 Setup Instructions

### 1. Copy Environment Template
```bash
cp config_template.env .env
```

### 2. Configure API Keys

Edit `.env` file with your actual API keys:

#### **Required (Essential for Testing)**
```bash
# IBM WatsonX (REQUIRED)
WATSONX_API_KEY=your_actual_watsonx_api_key
WATSONX_PROJECT_ID=your_actual_project_id
```

#### **Optional (Enhanced Features)**
```bash
# OSRM Routing (Optional - defaults to public server)
OSRM_SERVER_URL=http://router.project-osrm.org

# Redis (Optional - for state persistence)
REDIS_URL=redis://localhost:6379

# Google Search (Optional - for web confirmation)
GOOGLE_SEARCH_API_KEY=your_google_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id

# Notifications (Optional - for real alerts)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
SENDGRID_API_KEY=your_sendgrid_key
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## 🚀 Running Production Tests

### Run Complete Test Suite
```bash
python test_production_system.py
```

### Run Specific Tests
```bash
# Test only API monitoring
python test_production_system.py --test api

# Test only WatsonX integration
python test_production_system.py --test watsonx

# Test only detection workflow
python test_production_system.py --test detection

# Test only planning workflow
python test_production_system.py --test planning

# Test complete integrated system
python test_production_system.py --test integrated
```

### Use Custom Configuration File
```bash
python test_production_system.py --config my_config.env
```

## 📊 Test Results

### Success Indicators
- **✅ API Monitoring**: Real data from USGS, NOAA, FEMA, NASA, OSM
- **✅ WatsonX Integration**: Successful deployment plan generation
- **✅ Detection Workflow**: Complete threat assessment pipeline
- **✅ Planning Workflow**: Team deployment and evacuation planning
- **✅ Integrated System**: Full detection → planning → response

### Output Files
- `production_test_results_[session_id].json` - Detailed test results
- `production_test_[session_id].log` - Complete execution log

## 🔑 Getting API Keys

### IBM WatsonX (Required)
1. Sign up for [IBM Cloud](https://cloud.ibm.com)
2. Create a WatsonX.ai service instance
3. Get your API key from IBM Cloud console
4. Create a project and note the project ID

### Google Search API (Optional)
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Enable Custom Search API
3. Create credentials (API key)
4. Set up Custom Search Engine

### Twilio (Optional)
1. Sign up for [Twilio](https://www.twilio.com)
2. Get Account SID and Auth Token
3. Purchase a phone number

### SendGrid (Optional)
1. Sign up for [SendGrid](https://sendgrid.com)
2. Create API key
3. Verify sender email

## 🔍 Test Details

### API Monitoring Test
- Tests real API connections to disaster data sources
- Validates data parsing and normalization
- Checks error handling for failed sources

### WatsonX Integration Test
- Tests IBM WatsonX API connectivity
- Validates deployment plan generation
- Checks Granite model responses

### Detection Workflow Test
- Tests complete detection pipeline
- Validates state management
- Checks event creation and classification

### Planning Workflow Test
- Tests resource allocation logic
- Validates evacuation route planning
- Checks notification generation

### Integrated System Test
- Tests complete detection → planning pipeline
- Validates workflow transitions
- Checks end-to-end coordination

## 🔧 Troubleshooting

### Common Issues

#### WatsonX Authentication Errors
```
Error: WatsonX API authentication failed
Solution: Verify WATSONX_API_KEY and WATSONX_PROJECT_ID in .env
```

#### Missing Dependencies
```
Error: Module 'python-dotenv' not found
Solution: pip install python-dotenv
```

#### CSV Data Not Found
```
Warning: Could not load sample teams/zones
Solution: Ensure data/ directory contains CSV files
```

#### Redis Connection Failed
```
Warning: Redis checkpointing failed
Solution: Start Redis server or remove REDIS_URL from .env
```

### Debug Mode
Set `DEBUG_MODE=true` in `.env` for verbose logging:
```bash
DEBUG_MODE=true
```

## 📋 Minimum Requirements for Testing

**Essential for Basic Testing:**
- IBM WatsonX API key and Project ID
- Internet connection for API calls
- CSV data files in `data/` directory

**Recommended for Full Testing:**
- Redis server for state persistence
- Google Search API for web confirmation
- Notification service accounts

## 🎯 Expected Results

With proper configuration, you should see:
- **5/5 API sources** responding successfully
- **WatsonX deployment plans** with 8+ team assignments
- **Detection workflow** completing with event classification
- **Planning workflow** generating evacuation routes
- **Integrated system** coordinating complete response

Success rate should be **90-100%** with proper API keys.

## 📞 Support

If you encounter issues:
1. Check the log files for detailed errors
2. Verify API keys are correct
3. Ensure all dependencies are installed
4. Test with demo scripts first to verify installation

The production testing system provides comprehensive validation of all ProjectArkWatson components with real-world data and services.
