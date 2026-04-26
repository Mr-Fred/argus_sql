"""
This file is used to deploy the Schema Profiler Agent to Vertex AI.

To deploy the agent, run the following command:

    gcloud ai agent apps create --project=[PROJECT_ID] --location=[LOCATION]
"""

from vertexai import agent_engines
from src.agents.profiler.agent import create_agent


app = agent_engines.AdkApp(agent=create_agent())
