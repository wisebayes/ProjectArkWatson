"""
Main disaster detection workflow using LangGraph.
Orchestrates the complete detection, prediction, and response pipeline.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from langgraph.graph import StateGraph, END
# Redis checkpointing is optional for demo
try:
    from langgraph.checkpoint.redis import RedisSaver
except ImportError:
    RedisSaver = None

from core.state import DisasterDetectionState, create_initial_state
from .detection_nodes import (
    api_monitoring_node,
    data_analysis_node, 
    watsonx_classification_node,
    web_search_confirmation_node,
    severity_assessment_node,
    safe_zone_analysis_node,
    create_event_record_node,
    trigger_planning_workflow_node,
    wait_interval_node,
    log_false_positive_node
)


logger = logging.getLogger(__name__)


class DisasterDetectionWorkflow:
    """
    Main disaster detection workflow orchestrator.
    Uses LangGraph for state management and node coordination.
    """
    
    def __init__(self, redis_url: str = None):
        """
        Initialize the disaster detection workflow.
        
        Args:
            redis_url: Redis connection URL for state persistence
        """
        self.workflow = self._build_workflow()
        self.redis_url = redis_url
        self._app = None
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow structure."""
        workflow = StateGraph(DisasterDetectionState)
        
        # === ADD NODES ===
        workflow.add_node("api_monitoring", api_monitoring_node)
        workflow.add_node("data_analysis", data_analysis_node)
        workflow.add_node("watsonx_classification", watsonx_classification_node)
        workflow.add_node("web_search_confirmation", web_search_confirmation_node)
        workflow.add_node("severity_assessment", severity_assessment_node)
        workflow.add_node("safe_zone_analysis", safe_zone_analysis_node)
        workflow.add_node("create_event_record", create_event_record_node)
        workflow.add_node("trigger_planning_workflow", trigger_planning_workflow_node)
        workflow.add_node("wait_interval", wait_interval_node)
        workflow.add_node("log_false_positive", log_false_positive_node)
        
        # === SET ENTRY POINT ===
        workflow.set_entry_point("api_monitoring")
        
        # === ADD CONDITIONAL EDGES (ROUTING LOGIC) ===
        
        # From api_monitoring -> based on next_action
        workflow.add_conditional_edges(
            "api_monitoring",
            self._route_from_api_monitoring,
            {
                "data_analysis": "data_analysis",
                "error_handling": "wait_interval",
                "api_monitoring": "api_monitoring"  # Retry on recoverable errors
            }
        )
        
        # From data_analysis -> based on threat detection
        workflow.add_conditional_edges(
            "data_analysis", 
            self._route_from_data_analysis,
            {
                "watsonx_classification": "watsonx_classification",
                "wait_interval": "wait_interval"
            }
        )
        
        # From watsonx_classification -> based on threat detection and confidence
        workflow.add_conditional_edges(
            "watsonx_classification",
            self._route_from_watsonx_classification,
            {
                "web_search_confirmation": "web_search_confirmation",
                "severity_assessment": "severity_assessment",
                "wait_interval": "wait_interval"
            }
        )
        
        # From web_search_confirmation -> based on confirmation result
        workflow.add_conditional_edges(
            "web_search_confirmation",
            self._route_from_confirmation,
            {
                "severity_assessment": "severity_assessment",
                "log_false_positive": "log_false_positive"
            }
        )
        
        # From severity_assessment -> based on severity level
        workflow.add_conditional_edges(
            "severity_assessment",
            self._route_from_severity_assessment,
            {
                "safe_zone_analysis": "safe_zone_analysis",
                "create_event_record": "create_event_record"
            }
        )
        
        # From safe_zone_analysis -> always create event record
        workflow.add_edge("safe_zone_analysis", "create_event_record")
        
        # From create_event_record -> based on escalation requirements
        workflow.add_conditional_edges(
            "create_event_record",
            self._route_from_event_creation,
            {
                "trigger_planning_workflow": "trigger_planning_workflow",
                "wait_interval": "wait_interval"
            }
        )
        
        # From trigger_planning_workflow -> continue monitoring
        workflow.add_edge("trigger_planning_workflow", "wait_interval")
        
        # From wait_interval -> back to monitoring (continuous loop)
        workflow.add_edge("wait_interval", "api_monitoring")
        
        # From log_false_positive -> back to waiting
        workflow.add_edge("log_false_positive", "wait_interval")
        
        return workflow
    
    # === ROUTING FUNCTIONS ===
    
    def _route_from_api_monitoring(self, state: DisasterDetectionState) -> str:
        """Route from API monitoring based on success/failure."""
        next_action = state.get("next_action", "data_analysis")
        
        if next_action == "error_handling":
            return "error_handling"
        elif next_action == "api_monitoring":
            return "api_monitoring"  # Retry
        else:
            return "data_analysis"
    
    def _route_from_data_analysis(self, state: DisasterDetectionState) -> str:
        """Route from data analysis based on threat detection."""
        next_action = state.get("next_action", "wait_interval")
        
        if next_action == "watsonx_classification":
            return "watsonx_classification"
        else:
            return "wait_interval"
    
    def _route_from_watsonx_classification(self, state: DisasterDetectionState) -> str:
        """Route from WatsonX classification based on threat detection."""
        next_action = state.get("next_action", "wait_interval")
        
        if next_action == "web_search_confirmation":
            return "web_search_confirmation"
        elif next_action == "severity_assessment":
            return "severity_assessment"
        else:
            return "wait_interval"
    
    def _route_from_confirmation(self, state: DisasterDetectionState) -> str:
        """Route from web search confirmation based on confirmation result."""
        next_action = state.get("next_action", "severity_assessment")
        
        if next_action == "log_false_positive":
            return "log_false_positive"
        else:
            return "severity_assessment"
    
    def _route_from_severity_assessment(self, state: DisasterDetectionState) -> str:
        """Route from severity assessment based on escalation requirements."""
        next_action = state.get("next_action", "create_event_record")
        
        if next_action == "safe_zone_analysis":
            return "safe_zone_analysis"
        else:
            return "create_event_record"
    
    def _route_from_event_creation(self, state: DisasterDetectionState) -> str:
        """Route from event creation based on planning workflow trigger."""
        next_action = state.get("next_action", "wait_interval")
        
        if next_action == "trigger_planning_workflow":
            return "trigger_planning_workflow"
        else:
            return "wait_interval"
    
    def compile(self) -> Any:
        """Compile the workflow with optional Redis checkpointing."""
        if self.redis_url and RedisSaver:
            try:
                # Use Redis for state persistence
                with RedisSaver.from_conn_string(self.redis_url) as checkpointer:
                    checkpointer.setup()
                    self._app = self.workflow.compile(checkpointer=checkpointer)
            except Exception as e:
                logger.warning(f"Redis checkpointing failed: {e}. Using in-memory state.")
                self._app = self.workflow.compile()
        else:
            # In-memory state only
            self._app = self.workflow.compile()
        
        return self._app
    
    async def run_monitoring_cycle(
        self,
        monitoring_regions: list,
        session_id: str,
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run a single monitoring cycle.
        
        Args:
            monitoring_regions: List of geographic regions to monitor
            session_id: Unique session identifier
            config: Optional runtime configuration
        
        Returns:
            Final state after monitoring cycle
        """
        if not self._app:
            self._app = self.compile()
        
        # Create initial state
        initial_state = create_initial_state(
            monitoring_regions=monitoring_regions,
            session_id=session_id,
            confidence_threshold=config.get("confidence_threshold", 0.7) if config else 0.7,
            monitoring_interval=config.get("monitoring_interval", 60) if config else 60
        )
        
        # Set up runtime configuration
        run_config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": 50  # Prevent infinite loops
        }
        
        try:
            # Run the workflow
            final_state = None
            for state in self._app.stream(initial_state, config=run_config, stream_mode="values"):
                final_state = state
                
                # Log current workflow phase
                phase = state.get("workflow_phase", "unknown")
                next_action = state.get("next_action", "unknown")
                logger.info(f"Workflow phase: {phase}, next action: {next_action}")
                
                # Break on certain conditions to prevent infinite loops
                if state.get("next_action") == "wait_interval":
                    logger.info("Monitoring cycle completed, waiting for next interval")
                    break
            
            return final_state
            
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            return {
                "error": str(e),
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
    
    async def run_continuous_monitoring(
        self,
        monitoring_regions: list,
        session_id: str,
        max_cycles: int = None,
        config: Dict[str, Any] = None
    ):
        """
        Run continuous monitoring with automatic cycle restart.
        
        Args:
            monitoring_regions: List of geographic regions to monitor
            session_id: Unique session identifier  
            max_cycles: Maximum number of cycles to run (None for infinite)
            config: Optional runtime configuration
        
        Yields:
            State updates from each monitoring cycle
        """
        cycle_count = 0
        
        while max_cycles is None or cycle_count < max_cycles:
            try:
                logger.info(f"Starting monitoring cycle {cycle_count + 1}")
                
                final_state = await self.run_monitoring_cycle(
                    monitoring_regions, session_id, config
                )
                
                yield final_state
                
                cycle_count += 1
                
                # Check for termination conditions
                if final_state.get("error"):
                    logger.error(f"Cycle {cycle_count} failed: {final_state['error']}")
                    break
                
                # Implement actual waiting here based on monitoring_interval_seconds
                # For demo purposes, we'll just log and continue
                monitoring_interval = final_state.get("monitoring_interval_seconds", 60)
                logger.info(f"Cycle {cycle_count} completed, next cycle in {monitoring_interval} seconds")
                
            except Exception as e:
                logger.error(f"Continuous monitoring error in cycle {cycle_count + 1}: {e}")
                break
    
    def get_workflow_diagram(self) -> str:
        """Get Mermaid diagram representation of the workflow."""
        try:
            if not self._app:
                self._app = self.compile()
            return self._app.get_graph().draw_mermaid()
        except Exception as e:
            logger.error(f"Error generating workflow diagram: {e}")
            return "Error generating diagram"


# === UTILITY FUNCTIONS ===

def create_detection_workflow(
    monitoring_regions: list,
    redis_url: str = None,
    config: Dict[str, Any] = None
) -> DisasterDetectionWorkflow:
    """
    Factory function to create a disaster detection workflow.
    
    Args:
        monitoring_regions: Geographic regions to monitor
        redis_url: Optional Redis URL for state persistence
        config: Optional configuration parameters
    
    Returns:
        Configured DisasterDetectionWorkflow instance
    """
    workflow = DisasterDetectionWorkflow(redis_url=redis_url)
    return workflow


def get_sample_monitoring_regions() -> list:
    """Get sample monitoring regions for testing."""
    return [
        {
            "name": "San Francisco Bay Area",
            "center_lat": 37.7749,
            "center_lon": -122.4194,
            "radius_km": 100,
            "population_density": 2000,
            "priority": "high"
        },
        {
            "name": "Los Angeles Area", 
            "center_lat": 34.0522,
            "center_lon": -118.2437,
            "radius_km": 150,
            "population_density": 1500,
            "priority": "high"
        },
        {
            "name": "New York City Area",
            "center_lat": 40.7128,
            "center_lon": -74.0060,
            "radius_km": 75,
            "population_density": 3000,
            "priority": "high"
        }
    ]
