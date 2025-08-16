## Project ArkWatson

ProjectArkWatson/
├── 📊 data/                          # Simulated operational data
│   ├── response_teams.csv            # 15 emergency response teams
│   ├── evacuation_zones.csv          # 15 evacuation centers
│   └── population_zones.csv          # 20 population zones (SF)
│
├── 🤖 src/
│   ├── core/state.py                 # Complete state management (8 models)
│   ├── monitoring/
│   │   ├── api_clients.py            # 5 data source clients
│   │   ├── watsonx_agents.py         # WatsonX detection agents
│   │   └── planning_agents.py        # WatsonX planning agents
│   └── workflows/
│       ├── detection_workflow.py     # Detection orchestrator
│       ├── detection_nodes.py        # 10 detection workflow nodes
│       ├── planning_workflow.py      # Planning orchestrator  
│       └── planning_nodes.py         # 9 planning workflow nodes
│
├── 🎬 Demo Scripts
│   ├── demo_detection_workflow.py    # Detection demo
│   ├── demo_integrated_system.py     # Complete system demo
│   └── test_detection_workflow.py    # Technical validation
│
└── 📊 Generated Results
    ├── demo_output/                  # Detection demo results
    ├── integrated_demo_output/       # Complete system results
    └── *.log                        # Comprehensive logs