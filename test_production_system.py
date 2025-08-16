#!/usr/bin/env python3
"""
Production testing script for ProjectArkWatson disaster management system.
Tests real system functionality with actual API keys and services.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import pandas as pd
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.workflows.planning_workflow import (
    IntegratedDisasterManagement,
    DisasterPlanningWorkflow
)
from src.workflows.detection_workflow import (
    DisasterDetectionWorkflow,
    get_sample_monitoring_regions
)
from src.core.state import create_initial_state, DisasterDetectionState
from src.monitoring.api_clients import DisasterMonitoringService
from src.monitoring.planning_agents import WatsonXPlanningOrchestrator


class ProductionTestSuite:
    """
    Comprehensive test suite for production disaster management system.
    """
    
    def __init__(self, config_file: str = ".env"):
        """Initialize the test suite with environment configuration."""
        self.config_file = config_file
        self.test_results = {}
        self.test_session_id = f"{os.getenv('TEST_SESSION_PREFIX', 'test')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Load environment configuration
        self._load_configuration()
        
        # Set up logging
        self._setup_logging()
        
        # Validate required environment variables
        self._validate_configuration()
    
    def _load_configuration(self):
        """Load configuration from environment file."""
        # Try to load from .env file
        env_path = Path(self.config_file)
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✅ Loaded configuration from {self.config_file}")
        else:
            print(f"⚠️ Configuration file {self.config_file} not found. Using environment variables.")
        
        # Load configuration
        self.config = {
            # IBM WatsonX
            "WATSONX_APIKEY": os.getenv("WATSONX_APIKEY"),
            "watsonx_url": os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
            "watsonx_project_id": os.getenv("WATSONX_PROJECT_ID"),
            "watsonx_model_id": os.getenv("WATSONX_MODEL_ID", "ibm/granite-13b-instruct-v2"),
            
            # OSRM Routing
            "osrm_server_url": os.getenv("OSRM_SERVER_URL", "http://router.project-osrm.org"),
            
            # Redis
            "redis_url": os.getenv("REDIS_URL"),
            
            # Google Search
            "google_search_api_key": os.getenv("GOOGLE_SEARCH_API_KEY"),
            "google_search_engine_id": os.getenv("GOOGLE_SEARCH_ENGINE_ID"),
            
            # Notifications
            "twilio_account_sid": os.getenv("TWILIO_ACCOUNT_SID"),
            "twilio_auth_token": os.getenv("TWILIO_AUTH_TOKEN"),
            "twilio_phone_number": os.getenv("TWILIO_PHONE_NUMBER"),
            "sendgrid_api_key": os.getenv("SENDGRID_API_KEY"),
            "sendgrid_from_email": os.getenv("SENDGRID_FROM_EMAIL"),
            
            # Monitoring
            "monitoring_interval": int(os.getenv("MONITORING_INTERVAL_SECONDS", "60")),
            "confidence_threshold": float(os.getenv("CONFIDENCE_THRESHOLD", "0.7")),
            "debug_mode": os.getenv("DEBUG_MODE", "true").lower() == "true",
            
            # Test Configuration
            "test_region_lat": float(os.getenv("TEST_REGION_LAT", "37.7749")),
            "test_region_lon": float(os.getenv("TEST_REGION_LON", "-122.4194")),
            "test_region_radius": float(os.getenv("TEST_REGION_RADIUS_KM", "50"))
        }
    
    def _setup_logging(self):
        """Set up comprehensive logging."""
        log_level = logging.DEBUG if self.config["debug_mode"] else logging.INFO
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(f'production_test_{self.test_session_id}.log')
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Production test session started: {self.test_session_id}")
    
    def _validate_configuration(self):
        """Validate required configuration."""
        required_keys = ["WATSONX_APIKEY", "watsonx_project_id"]
        missing_keys = [key for key in required_keys if not self.config.get(key)]
        
        if missing_keys:
            print(f"❌ Missing required configuration: {', '.join(missing_keys)}")
            print(f"📄 Please set these in your {self.config_file} file")
            print(f"📋 Template available in: config_template.env")
            sys.exit(1)
        
        print("✅ Configuration validation passed")
    
    async def test_api_monitoring(self) -> Dict[str, Any]:
        """Test real API monitoring functionality."""
        print("\n🔍 TESTING API MONITORING")
        print("-" * 40)
        
        test_result = {
            "test_name": "api_monitoring",
            "start_time": datetime.now().isoformat(),
            "success": False,
            "details": {}
        }
        
        try:
            # Test with real monitoring service
            async with DisasterMonitoringService() as monitoring_service:
                self.logger.info("Testing real API monitoring service")
                
                # Poll all data sources
                api_responses = await monitoring_service.poll_all_sources(
                    lat=self.config["test_region_lat"],
                    lon=self.config["test_region_lon"],
                    radius_km=self.config["test_region_radius"]
                )
                
                # Analyze results
                successful_sources = 0
                source_details = {}
                
                for source, response in api_responses.items():
                    source_name = source.value
                    if response.success:
                        successful_sources += 1
                        status = "✅ SUCCESS"
                        print(f"  {status} {source_name}: {response.alerts_count} alerts")
                    else:
                        status = f"❌ FAILED: {response.error_message}"
                        print(f"  {status} {source_name}")
                    
                    source_details[source_name] = {
                        "success": response.success,
                        "alerts_count": response.alerts_count,
                        "error": response.error_message
                    }
                
                # Convert to monitoring data
                monitoring_data = monitoring_service.convert_to_monitoring_data(api_responses)
                
                test_result.update({
                    "success": successful_sources > 0,
                    "details": {
                        "total_sources": len(api_responses),
                        "successful_sources": successful_sources,
                        "source_details": source_details,
                        "total_alerts": sum(data.alerts_count for data in monitoring_data)
                    }
                })
                
                print(f"📊 API Monitoring Result: {successful_sources}/{len(api_responses)} sources successful")
                
        except Exception as e:
            self.logger.error(f"API monitoring test failed: {e}")
            test_result["details"]["error"] = str(e)
            print(f"❌ API monitoring test failed: {e}")
        
        test_result["end_time"] = datetime.now().isoformat()
        return test_result
    
    async def test_watsonx_integration(self) -> Dict[str, Any]:
        """Test IBM WatsonX integration."""
        print("\n🤖 TESTING IBM WATSONX INTEGRATION")
        print("-" * 40)
        
        test_result = {
            "test_name": "watsonx_integration", 
            "start_time": datetime.now().isoformat(),
            "success": False,
            "details": {}
        }
        
        try:
            # Test WatsonX planning orchestrator
            planner = WatsonXPlanningOrchestrator(
                WATSONX_APIKEY=self.config["WATSONX_APIKEY"],
                watsonx_url=self.config["watsonx_url"],
                project_id=self.config["watsonx_project_id"],
                model_id=self.config["watsonx_model_id"]
            )
            
            print("✅ WatsonX orchestrator initialized")
            
            # Test classification with sample data
            # Load sample data for testing
            sample_teams = self._load_sample_teams()
            sample_zones = self._load_sample_population_zones()
            
            if sample_teams and sample_zones:
                print(f"📂 Testing with {len(sample_teams)} teams and {len(sample_zones)} zones")
                
                # Test deployment planning
                deployment_plan = await planner.create_deployment_plan(
                    disaster_type="earthquake",
                    severity_level="moderate",
                    affected_areas=["San Francisco Bay Area"],
                    population_at_risk=50000,
                    available_teams=sample_teams,
                    population_zones=sample_zones
                )
                
                if deployment_plan and deployment_plan.get("deployments"):
                    print(f"✅ WatsonX deployment plan: {len(deployment_plan['deployments'])} deployments")
                    test_result["success"] = True
                    test_result["details"]["deployment_plan"] = {
                        "deployments_created": len(deployment_plan["deployments"]),
                        "strategy": deployment_plan.get("overall_strategy", ""),
                        "resource_gaps": deployment_plan.get("resource_gaps", [])
                    }
                else:
                    print("❌ WatsonX deployment planning failed")
                    test_result["details"]["error"] = "No deployments created"
            else:
                print("⚠️ Sample data not available for WatsonX testing")
                test_result["details"]["warning"] = "Sample data not loaded"
        
        except Exception as e:
            self.logger.error(f"WatsonX integration test failed: {e}")
            test_result["details"]["error"] = str(e)
            print(f"❌ WatsonX integration test failed: {e}")
        
        test_result["end_time"] = datetime.now().isoformat()
        return test_result
    
    async def test_detection_workflow(self) -> Dict[str, Any]:
        """Test complete detection workflow."""
        print("\n🔍 TESTING DETECTION WORKFLOW")
        print("-" * 40)
        
        test_result = {
            "test_name": "detection_workflow",
            "start_time": datetime.now().isoformat(),
            "success": False,
            "details": {}
        }
        
        try:
            # Create detection workflow
            detection_workflow = DisasterDetectionWorkflow(redis_url=self.config["redis_url"])
            
            # Set up monitoring regions
            monitoring_regions = [{
                "name": "Test Region (SF Bay Area)",
                "center_lat": self.config["test_region_lat"],
                "center_lon": self.config["test_region_lon"],
                "radius_km": self.config["test_region_radius"],
                "population_density": 2000,
                "priority": "high"
            }]
            
            # Run detection cycle
            print(f"🔄 Running detection workflow for region: {monitoring_regions[0]['name']}")
            
            detection_result = await detection_workflow.run_monitoring_cycle(
                monitoring_regions=monitoring_regions,
                session_id=self.test_session_id,
                config={
                    "confidence_threshold": self.config["confidence_threshold"],
                    "monitoring_interval": self.config["monitoring_interval"],
                    "debug_mode": self.config["debug_mode"]
                }
            )
            
            if detection_result and not detection_result.get("error"):
                # Analyze detection results
                monitoring_data = detection_result.get("current_monitoring_data", {})
                classification = detection_result.get("classification_results", {})
                active_events = detection_result.get("active_events", [])
                
                print(f"✅ Detection workflow completed")
                print(f"📡 Monitoring sources: {len(monitoring_data)}")
                print(f"🎯 Classification: {classification.get('disaster_type', 'none')}")
                print(f"🚨 Active events: {len(active_events)}")
                
                test_result.update({
                    "success": True,
                    "details": {
                        "monitoring_sources": len(monitoring_data),
                        "classification_performed": bool(classification),
                        "threat_detected": classification.get("threat_detected", False),
                        "confidence": classification.get("confidence_score", 0.0),
                        "active_events": len(active_events),
                        "planning_triggered": detection_result.get("planning_workflow_triggered", False)
                    }
                })
            else:
                error_msg = detection_result.get("error", "Unknown error")
                print(f"❌ Detection workflow failed: {error_msg}")
                test_result["details"]["error"] = error_msg
        
        except Exception as e:
            self.logger.error(f"Detection workflow test failed: {e}")
            test_result["details"]["error"] = str(e)
            print(f"❌ Detection workflow test failed: {e}")
        
        test_result["end_time"] = datetime.now().isoformat()
        return test_result
    
    async def test_planning_workflow(self) -> Dict[str, Any]:
        """Test complete planning workflow."""
        print("\n📋 TESTING PLANNING WORKFLOW")
        print("-" * 40)
        
        test_result = {
            "test_name": "planning_workflow",
            "start_time": datetime.now().isoformat(),
            "success": False,
            "details": {}
        }
        
        try:
            # Create planning workflow
            planning_workflow = DisasterPlanningWorkflow(redis_url=self.config["redis_url"])
            
            # Create initial state for planning (simulating trigger from detection)
            initial_state = create_initial_state(
                monitoring_regions=[{
                    "name": "Test Region",
                    "center_lat": self.config["test_region_lat"],
                    "center_lon": self.config["test_region_lon"],
                    "radius_km": self.config["test_region_radius"]
                }],
                session_id=self.test_session_id
            )
            
            # Simulate planning trigger
            initial_state.update({
                "planning_workflow_triggered": True,
                "current_event_id": "test_event_001",
                "active_events": [{
                    "id": "test_event_001",
                    "disaster_type": "earthquake",
                    "severity": "moderate"
                }]
            })
            
            print("🔄 Running planning workflow...")
            
            planning_result = await planning_workflow.run_planning_cycle(
                initial_state=initial_state,
                config={
                    "debug_mode": self.config["debug_mode"]
                }
            )
            
            if planning_result and not planning_result.get("error"):
                # Analyze planning results
                deployments = planning_result.get("team_deployments", [])
                evacuation_routes = planning_result.get("evacuation_routes", [])
                notifications = planning_result.get("notification_messages", [])
                workflow_phase = planning_result.get("workflow_phase", "unknown")
                
                print(f"✅ Planning workflow completed")
                print(f"🚁 Team deployments: {len(deployments)}")
                print(f"🛣️ Evacuation routes: {len(evacuation_routes)}")
                print(f"📱 Notifications: {len(notifications)}")
                print(f"📊 Workflow phase: {workflow_phase}")
                
                test_result.update({
                    "success": True,
                    "details": {
                        "team_deployments": len(deployments),
                        "evacuation_routes": len(evacuation_routes), 
                        "notifications_generated": len(notifications),
                        "workflow_phase": workflow_phase,
                        "planning_completed": workflow_phase in ["planning_completed", "operational_monitoring"]
                    }
                })
            else:
                error_msg = planning_result.get("error", "Unknown error")
                print(f"❌ Planning workflow failed: {error_msg}")
                test_result["details"]["error"] = error_msg
        
        except Exception as e:
            self.logger.error(f"Planning workflow test failed: {e}")
            test_result["details"]["error"] = str(e)
            print(f"❌ Planning workflow test failed: {e}")
        
        test_result["end_time"] = datetime.now().isoformat()
        return test_result
    
    async def test_integrated_system(self) -> Dict[str, Any]:
        """Test complete integrated disaster management system."""
        print("\n🌟 TESTING INTEGRATED SYSTEM")
        print("-" * 40)
        
        test_result = {
            "test_name": "integrated_system",
            "start_time": datetime.now().isoformat(),
            "success": False,
            "details": {}
        }
        
        try:
            # Create integrated management system
            integrated_system = IntegratedDisasterManagement(redis_url=self.config["redis_url"])
            
            # Set up monitoring regions
            monitoring_regions = [{
                "name": "Production Test Region",
                "center_lat": self.config["test_region_lat"],
                "center_lon": self.config["test_region_lon"],
                "radius_km": self.config["test_region_radius"],
                "population_density": 2000,
                "priority": "high"
            }]
            
            print("🔄 Running complete integrated disaster management cycle...")
            
            integrated_result = await integrated_system.run_complete_disaster_management(
                monitoring_regions=monitoring_regions,
                session_id=self.test_session_id,
                config={
                    "confidence_threshold": self.config["confidence_threshold"],
                    "monitoring_interval": self.config["monitoring_interval"],
                    "debug_mode": self.config["debug_mode"]
                }
            )
            
            if integrated_result and not integrated_result.get("error"):
                # Analyze integrated results
                management_phase = integrated_result.get("management_phase", "unknown")
                detection_summary = integrated_result.get("detection_summary", {})
                planning_summary = integrated_result.get("planning_summary", {})
                
                print(f"✅ Integrated system test completed")
                print(f"📊 Management phase: {management_phase}")
                print(f"🔍 Detection summary: {detection_summary}")
                print(f"📋 Planning summary: {planning_summary}")
                
                test_result.update({
                    "success": True,
                    "details": {
                        "management_phase": management_phase,
                        "detection_successful": bool(detection_summary),
                        "planning_successful": bool(planning_summary),
                        "teams_deployed": planning_summary.get("teams_deployed", 0),
                        "notifications_sent": planning_summary.get("notifications_sent", 0),
                        "complete_pipeline": management_phase == "complete_response"
                    }
                })
            else:
                error_msg = integrated_result.get("error", "Unknown error")
                print(f"❌ Integrated system test failed: {error_msg}")
                test_result["details"]["error"] = error_msg
        
        except Exception as e:
            self.logger.error(f"Integrated system test failed: {e}")
            test_result["details"]["error"] = str(e)
            print(f"❌ Integrated system test failed: {e}")
        
        test_result["end_time"] = datetime.now().isoformat()
        return test_result
    
    def _load_sample_teams(self) -> List:
        """Load sample response teams from CSV."""
        try:
            teams_file = Path("data/response_teams.csv")
            if teams_file.exists():
                teams_df = pd.read_csv(teams_file)
                return [
                    {
                        "team_id": row['team_id'],
                        "team_name": row['team_name'],
                        "team_type": row['team_type'],
                        "specialization": row['specialization'],
                        "capacity": row['capacity'],
                        "response_time_minutes": row['response_time_minutes']
                    }
                    for _, row in teams_df.iterrows()
                    if row['availability_status'] == 'available'
                ]
            return []
        except Exception as e:
            self.logger.warning(f"Could not load sample teams: {e}")
            return []
    
    def _load_sample_population_zones(self) -> List:
        """Load sample population zones from CSV."""
        try:
            zones_file = Path("data/population_zones.csv")
            if zones_file.exists():
                zones_df = pd.read_csv(zones_file)
                return [
                    {
                        "zone_id": row['zone_id'],
                        "zone_name": row['zone_name'],
                        "population": row['population'],
                        "population_density_per_km2": row['population_density_per_km2'],
                        "vulnerability_score": row['vulnerability_score'],
                        "special_needs_population": row['special_needs_population']
                    }
                    for _, row in zones_df.iterrows()
                ]
            return []
        except Exception as e:
            self.logger.warning(f"Could not load sample zones: {e}")
            return []
    
    async def run_complete_test_suite(self) -> Dict[str, Any]:
        """Run the complete production test suite."""
        print("🚀 PROJECTARKWATSON - PRODUCTION TEST SUITE")
        print("=" * 60)
        print(f"📋 Session ID: {self.test_session_id}")
        print(f"🌍 Test Region: {self.config['test_region_lat']:.4f}, {self.config['test_region_lon']:.4f}")
        print(f"🔧 Debug Mode: {self.config['debug_mode']}")
        print("=" * 60)
        
        test_suite_results = {
            "session_id": self.test_session_id,
            "start_time": datetime.now().isoformat(),
            "configuration": {
                "watsonx_configured": bool(self.config["WATSONX_APIKEY"]),
                "redis_configured": bool(self.config["redis_url"]),
                "debug_mode": self.config["debug_mode"]
            },
            "test_results": {},
            "summary": {}
        }
        
        # Test sequence
        tests = [
            ("API Monitoring", self.test_api_monitoring),
            ("WatsonX Integration", self.test_watsonx_integration),
            ("Detection Workflow", self.test_detection_workflow),
            ("Planning Workflow", self.test_planning_workflow),
            ("Integrated System", self.test_integrated_system)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                test_suite_results["test_results"][result["test_name"]] = result
                
                if result["success"]:
                    passed_tests += 1
                    status = "✅ PASSED"
                else:
                    status = "❌ FAILED"
                
                print(f"\n{status} {test_name}")
                
            except Exception as e:
                self.logger.error(f"Test {test_name} crashed: {e}")
                test_suite_results["test_results"][test_name.lower().replace(" ", "_")] = {
                    "test_name": test_name.lower().replace(" ", "_"),
                    "success": False,
                    "error": f"Test crashed: {str(e)}"
                }
                print(f"\n💥 CRASHED {test_name}: {e}")
        
        # Generate summary
        test_suite_results.update({
            "end_time": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": (passed_tests / total_tests) * 100,
                "overall_success": passed_tests == total_tests
            }
        })
        
        # Print final summary
        print("\n" + "=" * 60)
        print("📊 PRODUCTION TEST SUITE SUMMARY")
        print("=" * 60)
        print(f"✅ Tests Passed: {passed_tests}/{total_tests}")
        print(f"📈 Success Rate: {test_suite_results['summary']['success_rate']:.1f}%")
        
        if test_suite_results["summary"]["overall_success"]:
            print("🎉 ALL TESTS PASSED - PRODUCTION READY!")
        else:
            print("⚠️ Some tests failed - check logs for details")
        
        # Save results
        results_file = f"production_test_results_{self.test_session_id}.json"
        with open(results_file, "w") as f:
            json.dump(test_suite_results, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        print(f"📋 Test log saved to: production_test_{self.test_session_id}.log")
        
        return test_suite_results


async def main():
    """Main test execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ProjectArkWatson Production Test Suite")
    parser.add_argument("--config", default=".env", help="Environment configuration file")
    parser.add_argument("--test", choices=["api", "watsonx", "detection", "planning", "integrated", "all"], 
                       default="all", help="Specific test to run")
    
    args = parser.parse_args()
    
    # Create test suite
    test_suite = ProductionTestSuite(config_file=args.config)
    
    # Run specific test or full suite
    if args.test == "all":
        results = await test_suite.run_complete_test_suite()
        return 0 if results["summary"]["overall_success"] else 1
    else:
        # Run specific test
        test_methods = {
            "api": test_suite.test_api_monitoring,
            "watsonx": test_suite.test_watsonx_integration,
            "detection": test_suite.test_detection_workflow,
            "planning": test_suite.test_planning_workflow,
            "integrated": test_suite.test_integrated_system
        }
        
        if args.test in test_methods:
            result = await test_methods[args.test]()
            print(f"\nTest Result: {'✅ PASSED' if result['success'] else '❌ FAILED'}")
            return 0 if result["success"] else 1
        else:
            print(f"Unknown test: {args.test}")
            return 1


if __name__ == "__main__":
    print("🚀 ProjectArkWatson Production Testing")
    print("⚠️ This script requires real API keys and services")
    print("📋 Copy config_template.env to .env and set your API keys")
    print("")
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
