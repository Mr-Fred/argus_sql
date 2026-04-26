"""
Agent for semantic enhancement of database schema metadata.
"""

from typing import Any, Dict, List

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.adk.runners import Runner
from google.genai import types
from pydantic import BaseModel, Field

from src.agents.profiler.agent_config import SESSION_SERVICE
from src.agents.profiler.prompts import SYSTEM_INSTRUCTIONS, USER_PROMPT_TEMPLATE

load_dotenv()


class SemanticEnhancement(BaseModel):
    """
    Pydantic model for the semantic enhancement of a table.
    """

    narrative_summary: str = Field(
        ...,
        description="A 3 to 5 sentence executive summary of what this table represents.",
    )
    domains: List[str] = Field(
        ...,
        description="Primary and secondary domains/industries represented by this table. (e.g., HR, Finance, Marketing, Sales, Product, Operations, Education, Healthcare",
    )
    hyde_questions: List[str] = Field(
        ...,
        description="5 to 10 hypothetical natural language questions a user might ask to query this table.",
    )
    # We use a Dict so the LLM only generates descriptions for confusing columns, saving tokens!
    column_descriptions: Dict[str, str] = Field(
        ...,
        description="Detailed descriptions ONLY for inherently ambiguous column names (key=column_name, value=description).",
    )

    confidence_scores: Dict[str, float] = Field(
        ...,
        description="Confidence score for each field in the semantic enhancement.",
    )


class SchemaProfilerAgent:
    """
    ADK Agent that ingests raw BigQuery metadata and uses Gemini to generate
    semantic enhancements (HyDE questions, summaries, column descriptions).
    """

    model: str = "gemini-3-flash-preview"
    name: str = "SchemaProfilerAgent"

    def __init__(self):
        self.agent = Agent(
            name=self.name,
            model=self.model,
            description="Profiles database schema and generates semantic metadata",
            instruction=SYSTEM_INSTRUCTIONS,
            output_schema=SemanticEnhancement,
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    thinking_budget=1024,  # token budget for thinking
                )
            ),
        )

    def format_user_prompt(self, table_metadata: List[Dict[str, Any]]) -> str:  # noqa: F821
        """
        Format the user prompt with the table metadata. replace table_name, dataset_name, columns_stats placeholder in user prompt template with actual values.
        """
        table_name = table_metadata["table_name"]
        dataset_name = table_metadata["dataset_name"]
        columns_stats_str = "\n".join(
            [
                f"{col['name']}: {col['type']}, {col['description']}"
                for col in table_metadata["columns"]
            ]
        )
        return USER_PROMPT_TEMPLATE.format(
            table_name=table_name,
            dataset_name=dataset_name,
            columns_stats=columns_stats_str,
        )

    async def run(
        self, user_id: str, session_id: str, table_metadata: List[Dict[str, Any]]
    ) -> SemanticEnhancement:  # noqa: F821
        """
        Run the Schema Profiler Agent to semantically enhance the table metadata.

        Args:
            table_metadata: List of dictionaries containing the table metadata.
        Returns:
            SemanticEnhancement object containing the semantic enhancements.
        """
        user_prompt = self.format_user_prompt(table_metadata)
        runner = Runner(
            app_name=self.name, agent=self.agent, session_service=SESSION_SERVICE
        )
        session = await SESSION_SERVICE.create_session(
            app_name=self.name,
            user_id=user_id,
            session_id=session_id,
        )
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=types.Content(
                role="user", parts=[types.Part(text=user_prompt)]
            ),
        ):
            if event.is_final_response() and event.content:
                # TODO convert event.content to SemanticEnhancement
                print(event.content.parts[0].text)


if __name__ == "__main__":
    import asyncio

    mock_table_metadata = {
        "table_name": "employees",
        "dataset_name": "hr",
        "columns": [
            {
                "name": "id",
                "type": "INTEGER",
                "description": "Unique employee identifier.",
            },
            {
                "name": "first_name",
                "type": "STRING",
                "description": "Employee's legal given name.",
            },
            {
                "name": "last_name",
                "type": "STRING",
                "description": "Employee's family name.",
            },
            {
                "name": "email",
                "type": "STRING",
                "description": "Work email address, typically first_name.last_name @[company].com.",
            },
            {
                "name": "hire_date",
                "type": "DATE",
                "description": "Date when the employee officially joined the company.",
            },
            {
                "name": "salary",
                "type": "NUMERIC",
                "description": "Annual base salary in USD.",
            },
            {
                "name": "department_id",
                "type": "INTEGER",
                "description": "Foreign key linking to the departments table, representing the employee's assigned department.",
            },
        ],
    }
    schema_profiler_agent = SchemaProfilerAgent()
    asyncio.run(
        schema_profiler_agent.run("test_user", "test_session", mock_table_metadata)
    )
