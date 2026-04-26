"""
define configuration for the schema profiler agent based on dev or prod env.
"""
import os
from google.adk.sessions import InMemorySessionService, VertexAiSessionService

SESSION_SERVICE = None
if os.getenv("ENV") == "dev":
    SESSION_SERVICE = InMemorySessionService()
else:
    SESSION_SERVICE = VertexAiSessionService()
