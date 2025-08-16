#!/usr/bin/env python3
"""
Test script for the disaster detection workflow.
Demonstrates the complete detection pipeline with sample data.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.workflows.detection_workflow import (
    DisasterDetectionWorkflow, 
    create_detection_workflow,
    get_sample_monitoring_regions
)
from src.core.state import create_initial_state


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('detection_workflow.log')
    ]
)

logger = logging.getLogger(__name__)


async def test_single_monitoring_cycle():
    """Test a single monitoring cycle of the detection workflow."""
    logger.info("=== Testing Single Monitoring Cycle ===")
    
    # Create workflow
    monitoring_regions = get_sample_monitoring_regions()[:1]  # Test with SF Bay Area only
    workflow = create_detection_workflow(monitoring_regions)
    
    # Configure test parameters
    config = {
        "confidence_threshold": 0.5,  # Lower threshold for testing
        "monitoring_interval": 30,    # Shorter interval for testing
        "debug_mode": True
    }
    
    session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # Run single cycle
        logger.info(f"Starting monitoring cycle for session: {session_id}")
        final_state = await workflow.run_monitoring_cycle(
            monitoring_regions=monitoring_regions,
            session_id=session_id,
            config=config
        )
        
        # Display results
        print("\n" + "="*50)
        print("DETECTION WORKFLOW RESULTS")
        print("="*50)
        
        if final_state.get("error"):
            print(f"❌ Workflow Error: {final_state['error']}")
            return False
        
        # Basic state information
        print(f"Session ID: {final_state.get('session_id', 'Unknown')}")
        print(f"Workflow Phase: {final_state.get('workflow_phase', 'Unknown')}")
        print(f"Next Action: {final_state.get('next_action', 'Unknown')}")
        print(f"Last Update: {final_state.get('last_update_time', 'Unknown')}")
        
        # Monitoring data
        monitoring_data = final_state.get("current_monitoring_data", {})
        print(f"\n📡 API Sources Monitored: {len(monitoring_data)}")
        for source, data in monitoring_data.items():
            print(f"  - {source.value}: {data.alerts_count} alerts")
        
        # Classification results
        classification = final_state.get("classification_results", {})
        if classification:
            print(f"\n🤖 WatsonX Classification:")
            print(f"  - Threat Detected: {classification.get('threat_detected', False)}")
            print(f"  - Disaster Type: {classification.get('disaster_type', 'Unknown')}")
            print(f"  - Confidence: {classification.get('confidence_score', 0.0):.2f}")
            print(f"  - Severity: {classification.get('severity_level', 'Unknown')}")
        
        # Confirmation results
        confirmation_confidence = final_state.get("confirmation_confidence", 0.0)
        if confirmation_confidence > 0:
            print(f"\n🔍 Web Search Confirmation:")
            print(f"  - Confirmation Confidence: {confirmation_confidence:.2f}")
            print(f"  - Status: {final_state.get('confirmation_status', 'Unknown')}")
        
        # Events created
        active_events = final_state.get("active_events", [])
        if active_events:
            print(f"\n🚨 Active Events: {len(active_events)}")
            for event in active_events:
                print(f"  - {event.id}: {event.disaster_type.value} ({event.severity.value})")
        
        # Planning workflow
        if final_state.get("planning_workflow_triggered", False):
            print(f"\n📋 Planning Workflow Triggered:")
            print(f"  - Workflow ID: {final_state.get('planning_workflow_id', 'Unknown')}")
            actions = final_state.get("management_actions_needed", [])
            print(f"  - Actions Needed: {len(actions)}")
            for action in actions[:3]:  # Show first 3
                print(f"    • {action}")
        
        # Safe zones
        safe_zones = final_state.get("safe_zones", [])
        if safe_zones:
            print(f"\n🛡️ Safe Zones Identified: {len(safe_zones)}")
            for zone in safe_zones[:3]:  # Show first 3
                print(f"  - {zone.name}: {zone.capacity} capacity")
        
        # Errors
        errors = final_state.get("processing_errors", [])
        if errors:
            print(f"\n⚠️ Processing Errors: {len(errors)}")
            for error in errors[-3:]:  # Show last 3
                print(f"  - {error}")
        
        print("\n" + "="*50)
        
        # Success indicators
        success_indicators = []
        if monitoring_data:
            success_indicators.append("✅ API monitoring completed")
        if classification:
            success_indicators.append("✅ WatsonX classification completed")
        if not errors:
            success_indicators.append("✅ No processing errors")
        
        print("Success Indicators:")
        for indicator in success_indicators:
            print(f"  {indicator}")
        
        return len(success_indicators) >= 2  # At least 2 out of 3
        
    except Exception as e:
        logger.error(f"Test cycle error: {e}")
        print(f"\n❌ Test failed with error: {e}")
        return False


async def test_workflow_diagram():
    """Test workflow diagram generation."""
    logger.info("=== Testing Workflow Diagram ===")
    
    try:
        workflow = DisasterDetectionWorkflow()
        diagram = workflow.get_workflow_diagram()
        
        if diagram and "Error" not in diagram:
            print("\n📊 Workflow Diagram Generated Successfully")
            print(f"Diagram length: {len(diagram)} characters")
            
            # Save diagram to file
            with open("detection_workflow_diagram.mmd", "w") as f:
                f.write(diagram)
            print("Diagram saved to: detection_workflow_diagram.mmd")
            
            return True
        else:
            print(f"\n❌ Diagram generation failed: {diagram}")
            return False
            
    except Exception as e:
        logger.error(f"Diagram test error: {e}")
        print(f"\n❌ Diagram test failed: {e}")
        return False


async def test_state_management():
    """Test state management and serialization."""
    logger.info("=== Testing State Management ===")
    
    try:
        # Create initial state
        monitoring_regions = get_sample_monitoring_regions()[:1]
        session_id = "test_state_mgmt"
        
        initial_state = create_initial_state(
            monitoring_regions=monitoring_regions,
            session_id=session_id,
            confidence_threshold=0.7,
            monitoring_interval=60
        )
        
        # Test state serialization
        state_json = json.dumps(initial_state, default=str, indent=2)
        
        print(f"\n📋 Initial State Created Successfully")
        print(f"State size: {len(state_json)} characters")
        print(f"Monitoring regions: {len(initial_state['monitoring_regions'])}")
        print(f"Session ID: {initial_state['session_id']}")
        
        # Save state to file for inspection
        with open("sample_initial_state.json", "w") as f:
            f.write(state_json)
        print("Sample state saved to: sample_initial_state.json")
        
        return True
        
    except Exception as e:
        logger.error(f"State management test error: {e}")
        print(f"\n❌ State management test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests and provide summary."""
    print("🚀 ProjectArkWatson - Disaster Detection Workflow Test Suite")
    print("=" * 60)
    
    test_results = {}
    
    # Test 1: State Management
    print("\n1️⃣ Testing State Management...")
    test_results["state_management"] = await test_state_management()
    
    # Test 2: Workflow Diagram
    print("\n2️⃣ Testing Workflow Diagram...")
    test_results["workflow_diagram"] = await test_workflow_diagram()
    
    # Test 3: Single Monitoring Cycle (main test)
    print("\n3️⃣ Testing Single Monitoring Cycle...")
    test_results["monitoring_cycle"] = await test_single_monitoring_cycle()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(test_results.values())
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The detection workflow is ready for demo.")
    else:
        print("⚠️ Some tests failed. Check logs for details.")
    
    print(f"\nLog file: detection_workflow.log")
    print(f"Generated files:")
    print(f"  - detection_workflow_diagram.mmd")
    print(f"  - sample_initial_state.json")
    
    return passed == total


if __name__ == "__main__":
    # Run tests
    success = asyncio.run(run_all_tests())
    
    if success:
        print("\n🚀 Ready for hackathon demo!")
        sys.exit(0)
    else:
        print("\n🔧 Some issues need to be resolved.")
        sys.exit(1)
