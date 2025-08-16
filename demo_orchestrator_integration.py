#!/usr/bin/env python3
"""
Run the Orchestrator-style detection (ReAct) + planning (Plan-Act) flow locally.

This uses the adapters in src/orchestrator/adapters.py so you can test the
integration without deploying to the watsonx Orchestrator control plane.
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.workflows.integrated_orchestrator import IntegratedOrchestratorManagement


def _setup_logging(session_id: str):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'integrated_orchestrator_{session_id}.log'),
        ],
    )


async def _run_once(args: argparse.Namespace) -> Dict[str, Any]:
    system = IntegratedOrchestratorManagement()

    monitoring_regions = [
        {
            "name": args.region,
            "center_lat": args.lat,
            "center_lon": args.lon,
            "radius_km": args.radius,
            "population_density": 2000,
            "priority": "high",
        }
    ]

    config: Dict[str, Any] = {
        "watsonx_config": {
            "api_key": args.watsonx_api_key or "",
            "url": args.watsonx_url,
            "project_id": args.watsonx_project_id or "",
            "model_id": args.watsonx_model_id,
        }
    }

    result = await system.run_complete_disaster_management(
        monitoring_regions=monitoring_regions,
        session_id=args.session,
        config=config,
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Orchestrator-style integrated workflow")
    parser.add_argument("--region", default="San Francisco Bay Area", help="Region name")
    parser.add_argument("--lat", type=float, default=37.7749, help="Center latitude")
    parser.add_argument("--lon", type=float, default=-122.4194, help="Center longitude")
    parser.add_argument("--radius", type=float, default=100.0, help="Radius in km")
    parser.add_argument("--session", default=f"orch_{datetime.now().strftime('%Y%m%d_%H%M%S')}", help="Session ID")

    # Optional watsonx config
    parser.add_argument("--watsonx-api-key", dest="watsonx_api_key", default=None, help="Watsonx API key")
    parser.add_argument("--watsonx-url", dest="watsonx_url", default="https://us-south.ml.cloud.ibm.com", help="Watsonx base URL")
    parser.add_argument("--watsonx-project-id", dest="watsonx_project_id", default=None, help="Watsonx project ID")
    parser.add_argument("--watsonx-model-id", dest="watsonx_model_id", default="ibm/granite-13b-instruct-v2", help="Watsonx model ID")

    args = parser.parse_args()
    _setup_logging(args.session)

    print("\n🌟 ProjectArkWatson - Orchestrator Integration Test")
    print("=" * 60)
    print(f"Region: {args.region} ({args.lat:.4f}, {args.lon:.4f}) / radius {args.radius} km")
    print(f"Session: {args.session}")

    try:
        result = asyncio.run(_run_once(args))

        # Output directory
        out_dir = Path("integrated_demo_output")
        out_dir.mkdir(exist_ok=True)
        out_file = out_dir / f"integrated_orchestrator_results_{args.session}.json"

        with open(out_file, "w") as f:
            json.dump(result, f, indent=2)

        print("\n📊 Orchestrator-style run complete")
        print(f"Management phase: {result.get('management_phase', 'unknown')}")
        if result.get("detection_summary"):
            ds = result["detection_summary"]
            print(f"  ▸ Event detected: {ds.get('event_detected', False)}")
            cls = ds.get("classification", {})
            print(f"  ▸ Disaster: {cls.get('disaster_type', 'unknown')} | Severity: {cls.get('severity_level', 'unknown')}")
        if result.get("planning_summary"):
            ps = result["planning_summary"]
            print(f"  ▸ Teams deployed: {ps.get('deployments_created', 0)} | Routes: {ps.get('routes', 0)}")

        print(f"\n💾 Results saved to: {out_file}")
        print(f"📝 Log saved to: integrated_orchestrator_{args.session}.log")

        return 0
    except Exception as e:
        print(f"\n❌ Run failed: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


