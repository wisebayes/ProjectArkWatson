"""
Main disaster response planning workflow using LangGraph.
Orchestrates team deployment, evacuation planning, and resource coordination.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from langgraph.graph import StateGraph, END

from core.state import DisasterDetectionState
from .planning_nodes import (
    load_planning_data_node,
    assess_planning_requirements_node,
    create_deployment_plan_node,
    create_evacuation_plan_node,
    coordinate_resources_node,
    generate_notifications_node,
    send_notifications_node,
    planning_complete_node,
    planning_error_handling_node
)


logger = logging.getLogger(__name__)


class DisasterPlanningWorkflow:
    """
    Main disaster response planning workflow orchestrator.
    Uses LangGraph for coordinated emergency response planning.
    """
    
    def __init__(self, redis_url: str = None):
        """
        Initialize the disaster planning workflow.
        
        Args:
            redis_url: Redis connection URL for state persistence
        """
        self.workflow = self._build_workflow()
        self.redis_url = redis_url
        self._app = None
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph planning workflow structure."""
        workflow = StateGraph(DisasterDetectionState)
        
        # === ADD NODES ===
        workflow.add_node("load_planning_data", load_planning_data_node)
        workflow.add_node("assess_planning_requirements", assess_planning_requirements_node)
        workflow.add_node("create_deployment_plan", create_deployment_plan_node)
        workflow.add_node("create_evacuation_plan", create_evacuation_plan_node)
        workflow.add_node("coordinate_resources", coordinate_resources_node)
        workflow.add_node("generate_notifications", generate_notifications_node)
        workflow.add_node("send_notifications", send_notifications_node)
        workflow.add_node("planning_complete", planning_complete_node)
        workflow.add_node("planning_error_handling", planning_error_handling_node)
        
        # === SET ENTRY POINT ===
        workflow.set_entry_point("load_planning_data")
        
        # === ADD CONDITIONAL EDGES (ROUTING LOGIC) ===
        
        # From load_planning_data -> based on success/failure
        workflow.add_conditional_edges(
            "load_planning_data",
            self._route_from_data_loading,
            {
                "assess_planning_requirements": "assess_planning_requirements",
                "planning_error_handling": "planning_error_handling"
            }
        )
        
        # From assess_planning_requirements -> always proceed to deployment
        workflow.add_edge("assess_planning_requirements", "create_deployment_plan")
        
        # From create_deployment_plan -> always proceed to evacuation
        workflow.add_edge("create_deployment_plan", "create_evacuation_plan")
        
        # From create_evacuation_plan -> coordinate resources
        workflow.add_edge("create_evacuation_plan", "coordinate_resources")
        
        # From coordinate_resources -> generate notifications
        workflow.add_edge("coordinate_resources", "generate_notifications")
        
        # From generate_notifications -> send notifications
        workflow.add_edge("generate_notifications", "send_notifications")
        
        # From send_notifications -> planning complete
        workflow.add_edge("send_notifications", "planning_complete")
        
        # From planning_complete -> END
        workflow.add_edge("planning_complete", END)
        
        # From planning_error_handling -> END (fallback)
        workflow.add_edge("planning_error_handling", END)
        
        return workflow
    
    # === ROUTING FUNCTIONS ===
    
    def _route_from_data_loading(self, state: DisasterDetectionState) -> str:
        """Route from data loading based on success/failure."""
        next_action = state.get("next_action", "assess_planning_requirements")
        
        if next_action == "planning_error_handling":
            return "planning_error_handling"
        else:
            return "assess_planning_requirements"
    
    def compile(self) -> Any:
        """Compile the workflow with optional Redis checkpointing."""
        # For planning workflow, we'll use in-memory state for demo
        # In production, you'd use Redis checkpointing like the detection workflow
        self._app = self.workflow.compile()
        return self._app
    
    async def run_planning_cycle(
        self,
        initial_state: DisasterDetectionState,
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run a complete planning cycle.
        
        Args:
            initial_state: State from detection workflow with planning trigger
            config: Optional runtime configuration
        
        Returns:
            Final state after planning completion
        """
        if not self._app:
            self._app = self.compile()
        
        # Set up runtime configuration
        run_config = {
            "configurable": {"thread_id": initial_state["session_id"]},
            "recursion_limit": 25  # Planning workflow is more linear
        }
        
        try:
            # Run the planning workflow
            final_state = None
            for state in self._app.stream(initial_state, config=run_config, stream_mode="values"):
                final_state = state
                
                # Log current workflow phase
                phase = state.get("workflow_phase", "unknown")
                next_action = state.get("next_action", "unknown")
                logger.info(f"Planning phase: {phase}, next action: {next_action}")
                
                # Break on completion
                if state.get("next_action") in ["operational_monitoring", None]:
                    logger.info("Planning cycle completed")
                    break
            
            return final_state
            
        except Exception as e:
            logger.error(f"Planning workflow execution error: {e}")
            return {
                **initial_state,
                "error": str(e),
                "workflow_phase": "planning_failed",
                "timestamp": datetime.now().isoformat()
            }
    
    def get_workflow_diagram(self) -> str:
        """Get Mermaid diagram representation of the planning workflow."""
        try:
            if not self._app:
                self._app = self.compile()
            return self._app.get_graph().draw_mermaid()
        except Exception as e:
            logger.error(f"Error generating planning workflow diagram: {e}")
            return "Error generating diagram"


class IntegratedDisasterManagement:
    """
    Integrated disaster management system combining detection and planning workflows.
    """
    
    def __init__(self, redis_url: str = None):
        """Initialize integrated disaster management system."""
        # Import here to avoid circular imports
        from .detection_workflow import DisasterDetectionWorkflow
        
        self.detection_workflow = DisasterDetectionWorkflow(redis_url)
        self.planning_workflow = DisasterPlanningWorkflow(redis_url)
        self.redis_url = redis_url
    
    async def run_complete_disaster_management(
        self,
        monitoring_regions: list,
        session_id: str,
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run complete disaster management cycle: detection -> planning -> response.
        
        Args:
            monitoring_regions: Geographic regions to monitor
            session_id: Unique session identifier
            config: Optional configuration
        
        Returns:
            Final state with both detection and planning results
        """
        logger.info("Starting integrated disaster management cycle")
        
        try:
            # Phase 1: Detection and Threat Assessment
            logger.info("Phase 1: Running disaster detection workflow")
            detection_result = await self.detection_workflow.run_monitoring_cycle(
                monitoring_regions=monitoring_regions,
                session_id=session_id,
                config=config
            )
            
            # Check if planning workflow should be triggered
            if not detection_result.get("planning_workflow_triggered", False):
                logger.info("No planning workflow trigger - detection cycle complete")
                return {
                    **detection_result,
                    "management_phase": "monitoring_only",
                    "planning_triggered": False
                }
            
            # Phase 2: Planning and Resource Coordination
            logger.info("Phase 2: Running disaster planning workflow")
            planning_result = await self.planning_workflow.run_planning_cycle(
                initial_state=detection_result,
                config=config
            )
            
            # Combine results
            integrated_result = {
                **planning_result,
                "management_phase": "complete_response",
                "detection_summary": {
                    "event_detected": len(detection_result.get("active_events", [])) > 0,
                    "confidence": detection_result.get("prediction_confidence", 0.0),
                    "severity": detection_result.get("classification_results", {}).get("severity_level", "unknown"),
                    "disaster_type": detection_result.get("classification_results", {}).get("disaster_type", "unknown")
                },
                "planning_summary": {
                    "teams_deployed": len(planning_result.get("team_deployments", [])),
                    "evacuation_routes": len(planning_result.get("evacuation_routes", [])),
                    "notifications_sent": len(planning_result.get("notification_messages", [])),
                    "planning_status": planning_result.get("workflow_phase", "unknown")
                }
            }
            
            logger.info(f"Integrated disaster management completed: "
                       f"{integrated_result['planning_summary']['teams_deployed']} teams deployed, "
                       f"{integrated_result['planning_summary']['notifications_sent']} notifications sent")
            
            return integrated_result
            
        except Exception as e:
            logger.error(f"Integrated disaster management error: {e}")
            return {
                "error": str(e),
                "management_phase": "failed",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_combined_workflow_diagram(self) -> Dict[str, str]:
        """Get workflow diagrams for both detection and planning workflows."""
        return {
            "detection_workflow": self.detection_workflow.get_workflow_diagram(),
            "planning_workflow": self.planning_workflow.get_workflow_diagram()
        }


# === UTILITY FUNCTIONS ===

def create_planning_workflow(
    redis_url: str = None,
    config: Dict[str, Any] = None
) -> DisasterPlanningWorkflow:
    """
    Factory function to create a disaster planning workflow.
    
    Args:
        redis_url: Optional Redis URL for state persistence
        config: Optional configuration parameters
    
    Returns:
        Configured DisasterPlanningWorkflow instance
    """
    workflow = DisasterPlanningWorkflow(redis_url=redis_url)
    return workflow


def create_integrated_management_system(
    redis_url: str = None,
    config: Dict[str, Any] = None
) -> IntegratedDisasterManagement:
    """
    Factory function to create integrated disaster management system.
    
    Args:
        redis_url: Optional Redis URL for state persistence
        config: Optional configuration parameters
    
    Returns:
        Configured IntegratedDisasterManagement instance
    """
    return IntegratedDisasterManagement(redis_url=redis_url)
