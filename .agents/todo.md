# ARGUS-SQL Implementation Plan (TDD Blueprint)

This blueprint breaks down the ARGUS-SQL architecture into safe, independently testable, iterative steps using `uv`. All LLM interactions are strictly standardized on the Google Agent Development Kit (ADK) framework.

## Phase 1: Foundation & Zero Trust Security
**Goal:** Establish project infrastructure and the deterministic AST firewall.
- [x] **Step 1.1: Project Initialization & Configuration**
  - Initialize project using `uv` with `pytest`, `ruff`, `fastapi`, `google-adk`, `google-cloud-bigquery`, `sqlglot`.
- [x] **Step 1.2: AST Mutation Firewall**
  - Implement `validate_ast(sql: str)` using `sqlglot`.
  - Assert that pure `SELECT` queries pass and all mutations (`DROP`, `INSERT`, `ALTER`) throw a `SecurityError`.

## Phase 2: Database Population & Datasets
**Goal:** Build scripts to populate the BigQuery evaluation environments.
- [x] **Step 2.1: BIRD Benchmark Ingestion Script**
  - Write a CLI script to read the BIRD SQLite dataset, map types to GoogleSQL, and upload the tables to BigQuery.
- [x] **Step 2.2: Golden Dataset Setup**
  - Write a deployment script to create the 50 manually curated question-SQL pairs testing BigQuery-specific constructs (unnesting, window functions, partitioning).

## Phase 3: The Profiler Subsystem (M-Schema Builder)
**Goal:** Aggregate structural and statistical metadata into BigQuery embeddings.
- [x] **Step 3.1: BigQuery Structural & Statistical Extractor**
  - Build service to read `INFORMATION_SCHEMA` and perform safe `APPROX_TOP_COUNT` sampling.
- [ ] **Step 3.2: Schema Profiler Agent (via ADK)**
  - Implement the `SchemaProfilerAgent` using the ADK framework.
  - This agent takes raw metadata and uses Gemini to output the structured M-Schema Pydantic object (summary + HyDE questions).
  - Insert the compiled JSON payloads into the `meta_schema_embeddings` BigQuery table.

## Phase 4: Retrieval Engine
**Goal:** Find relevant schema payloads accurately natively in BigQuery.
- [ ] **Step 4.1: Hybrid Vector & Keyword Retrieval**
  - Implement BigQuery SQL logic for Vector Search and text indexing on the M-Schema table.
  - Apply the Domain Pre-Filter constraint.
- [ ] **Step 4.2: Reciprocal Rank Fusion (RRF)**
  - Implement the RRF mathematical algorithm to merge Vector and Keyword ranks and return Top-K schemas.

## Phase 5: Multi-Agent Core via ADK
**Goal:** Convert NLP to SQL using the Agent Development Kit and route via intent.
- [ ] **Step 5.1: Intent Router Agent**
  - Implement the `IntentRouterAgent` via ADK to extract domain and `Visualization` vs `Retrieval` intent.
- [ ] **Step 5.2: Subproblem Decomposer Agent**
  - Implement the `SubproblemDecomposerAgent` via ADK to structure logical plans from user input.
- [ ] **Step 5.3: SQL Generator Agent (Chain-of-Thought)**
  - Implement the primary `SQLGeneratorAgent` via ADK.
  - Wire the Router, Decomposer, and Generator states together in an ADK Orchestration Graph.

## Phase 6: Validation, Execution, & Taxonomy Loop
**Goal:** Execute safely and self-correct semantic errors.
- [ ] **Step 6.1: BigQuery Dry Run Validator**
  - Implement BQ dry-run integration (Syntax & 10GB Cost Limit).
- [ ] **Step 6.2: Error Taxonomist & ADK Retry Loop**
  - Implement the 10-category classification logic.
  - Integrate as an ADK Tool/Guardrail to pass classified errors back to the `SQLGeneratorAgent` up to 3 times.

## Phase 7: Synthesis & Fast API Setup
**Goal:** Polish the output and wire to FastAPI.
- [ ] **Step 7.1: Data-to-Text Narrator Agent**
  - Implement the `NarratorAgent` via ADK to auto-select visualizations and narrate query output.
- [ ] **Step 7.2: FastAPI Application Wiring**
  - Expose `/query` endpoint wiring Intent, Retrieval, ADK Core Graph, and Synthesis.

## Phase 8: System Evaluation & Scripts
**Goal:** Automate the benchmarking and benchmarking protocols.
- [ ] **Step 8.1: Execution Accuracy Evaluator**
  - Script to iterate over the Adapted BIRD and Golden datasets.
  - Execute both predicted SQL and gold SQL, asserting DataFrame row equality to measure Execution Accuracy (EX) and Valid SQL rates.
- [ ] **Step 8.2: Schema Perturbation (Drift) Protocol**
  - Script to randomly `ALTER TABLE RENAME COLUMN` and cast types on a test dataset.
  - Measure Profiler Eventarc latency, then re-run the benchmark script to compute the "Drift Robustness" ratio.
