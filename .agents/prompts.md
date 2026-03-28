# LLM Code Generation Prompts for ARGUS-SQL

These prompts are designed to be fed sequentially to a code-generation LLM. Every step requires Test-Driven Development (TDD) using `pytest`.

## Phase 1: Foundation & Zero Trust Security

### Prompt 1.1: Project Setup
```text
We are building ARGUS-SQL, an enterprise text-to-SQL system. All LLM interaction MUST use the `google-adk` framework.
Initialize the Python project directory using `uv init`. We need a robust backend.
Add dependencies using `uv add`: fastapi, uvicorn, google-genai, google-adk, google-cloud-bigquery, sqlglot, pandas, and python-dotenv.
Add development dependencies using `uv add --dev`: pytest, pytest-asyncio, and ruff.
Create the foundational directory structure: `src/core/`, `src/agents/`, `src/scripts/`, `src/api/`, `tests/unit/`, and `tests/integration/`.
Generate a `.env.example` file with `GEMINI_API_KEY` and `GOOGLE_APPLICATION_CREDENTIALS`.
Create a basic `pytest.ini` and configure `ruff.toml` with strict linting rules. 
Output the bash commands to run, and the content for the basic configuration files.
```

### Prompt 1.2: AST Mutation Firewall
```text
Building on our setup, create `tests/unit/test_ast_firewall.py`. Write `pytest` assertions that test `validate_ast(sql: str)`.
Assert pure `SELECT` queries pass without error, but queries containing `DROP`, `INSERT`, `ALTER`, `UPDATE`, `DELETE`, or multiple statements raise a `SecurityError`. Provide edge cases for deeply nested subqueries containing mutation keywords to ensure the parser catches them.
After writing tests, implement `validate_ast` in `src/core/security.py` using `sqlglot` configured for the BigQuery dialect.
```

## Phase 2: Database Population & Datasets

### Prompt 2.1: BIRD Benchmark Ingestion Script
```text
We need to populate BigQuery with the BIRD dataset.
Write a robust, standalone Python script in `src/scripts/ingest_bird.py`. It must accept arguments for a local SQLite database file path and a target BigQuery dataset ID.
The script should use `sqlite3` and `google-cloud-bigquery` to read all tables, map SQLite data types to GoogleSQL types, and bulk upload the data. Implement error handling and logging.
Add a `tests/unit/test_ingestion.py` that mocks the BQ client and verifies the schema mapping logic.
```

### Prompt 2.2: Golden Dataset Script
```text
Write a script `src/scripts/setup_golden_set.py` to programmatically `CREATE TABLE` and `INSERT` the 50 queries of the Golden Dataset into BigQuery.
Include complex schemas necessary to test array unnesting, partitioning, and window functions as defined in the ARGUS-SQL spec. Use the BigQuery Python SDK to execute the statements deterministically.
```

## Phase 3: The Profiler Subsystem

### Prompt 3.1: BigQuery Profiler Extractor
```text
Create `tests/unit/test_profiler_extraction.py`. Mock the `google.cloud.bigquery.Client` to return dummy Table schemas and dummy data samples.
Implement `BigQueryExtractor` in `src/core/profiler.py` that queries `INFORMATION_SCHEMA.COLUMNS` and executes safe `APPROX_TOP_COUNT` sampling queries for string columns. Handle potential BQ permissions errors gracefully by falling back to structural-only data.
```

### Prompt 3.2: Schema Profiler Agent (via ADK)
```text
We will use `google-adk` to synthetically summarize our BQ schemas.
Create `tests/unit/test_schema_profiler_agent.py` and write tests simulating ADK agent generation.
Implement `SchemaProfilerAgent` natively in `google-adk` inside `src/agents/profiler_agent.py`. It must take the extracted metadata dictionary as input entirely within the ADK conversational state, invoke Gemini Flash, and return a strict Pydantic `MSchemaPayload` representing the schema summary and HyDE questions.
Write a script `src/scripts/run_profiler.py` that uses `BigQueryExtractor` and `SchemaProfilerAgent` to iterate over a BQ dataset and `MERGE` the generated JSON payloads and embeddings into the `meta_schema_embeddings` BigQuery table.
```

## Phase 4: Retrieval Engine

### Prompt 4.1: Hybrid BigQuery Retrieval
```text
Create `tests/unit/test_retrieval.py` and mock the response from BigQuery vector and keyword searches.
Implement `BigQueryRetriever` in `src/core/retrieval.py`. Instead of an external vector DB, this must construct and execute a `VECTOR_SEARCH` query directly against the `meta_schema_embeddings` table. 
Implement Reciprocal Rank Fusion (RRF) algorithm locally in Python to merge the vector rank results with keyword rank results. Ensure domain filtering is injected into the BQ query.
```

## Phase 5: Multi-Agent Core via ADK

### Prompt 5.1: Intent Router Agent (via ADK)
```text
Create `tests/unit/test_router_agent.py`. 
Implement `IntentRouterAgent` in `src/agents/router_agent.py` strictly using the `google-adk` framework. It must output a Pydantic object to classify a user query into [Data Retrieval, Visualization, Out-of-Scope]. Ensure the ADK agent raises an `AmbiguousQueryError` if confidence < 0.6.
```

### Prompt 5.2: Google ADK Orchestration
```text
We will now build the core reasoning layer using `google-adk`.
Create `tests/unit/test_sql_agents.py`. Write tests simulating ADK structured outputs.
Implement `SubproblemDecomposerAgent` and `SQLGeneratorAgent` using the `google-adk` framework in `src/agents/sql_agent.py`.
The Decomposer Agent must output a structured logical plan. The Generator Agent must accept this plan and M-Schemas, outputting valid GoogleSQL using Chain-of-Thought prompting. Wire their state transitions together cleanly.
```

## Phase 6: Validation & Taxonomy Loop

### Prompt 6.1: BigQuery Dry Run Validator
```text
Create `tests/integration/test_validation.py`. Mock the BQ SDK.
Implement `DryRunValidator` in `src/core/security.py` executing `queryJob(dry_run=True)`. Halt and raise `ResourceExhaustionError` if `total_bytes_processed > 10GB`.
```

### Prompt 6.2: Error Taxonomist as ADK Tool
```text
Implement `ErrorTaxonomist` in `src/core/correction.py` that categorizes dry-run or execution exceptions into the 10-category taxonomy (Syntax, Schema Link, Join, Filter, Aggregation, Value, Subquery, Set Operations, Other Issues, Security).
Integrate this taxonomist into the ADK Core as an ADK Tool/Guardrail node. If SQL Generation fails validation, the ADK state router must loop back to the `SQLGeneratorAgent` with the classified error for self-correction (limit 3 retries). If it is a `SecurityError`, the ADK graph must immediately exit and fail.
```

## Phase 7: Synthesis & Fast API Setup

### Prompt 7.1: Narrator Agent & REST API
```text
As our final LLM component, implement `NarratorAgent` in `src/agents/narrator_agent.py` via `google-adk`. It must take the final executed Pandas DataFrame results and summarize it into a business narrative.
Write `tests/integration/test_api.py` using `fastapi.testclient`. Mock the ADK Graph execution.
Implement `src/api/main.py`. Build a POST `/query` endpoint that sequentially runs the `IntentRouterAgent`, performs `BigQueryRetriever` lookup, executes the ADK SQL Generation graph, and uses the `NarratorAgent` to build the final response payload.
```

## Phase 8: System Evaluation Scripts

### Prompt 8.1: Execution Accuracy Evaluator
```text
Write `src/scripts/evaluate_accuracy.py`.
This script must iterate over the BIRD evaluation set hosted in BigQuery. For each evaluation pair, route it exclusively through the ADK core architecture.
Execute the generated SQL against BQ, and execute the BQ ground-truth Gold SQL. 
Compare the resulting Pandas DataFrames using row-order-independent set equality. Output standard evaluation metrics: Execution Accuracy (EX) and Valid SQL Rate to the terminal.
```

### Prompt 8.2: Schema Perturbation (Drift) Script
```text
Write `src/scripts/simulate_drift.py`.
This script must query BigQuery for a list of columns in a test dataset, randomly select 30% of them, and execute `ALTER TABLE RENAME COLUMN` statements, assigning realistic synonym replacements. It must cast 10% of numeric types to STING. 
Implement a timer to visually monitor how fast the Async Profiler detects and patches the `meta_schema_embeddings` table. Make the script easily reversible with a tear-down function.
```
