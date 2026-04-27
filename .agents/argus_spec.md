# ARGUS-SQL: Developer Implementation Specification

**Project:** Automated Reasoning and Grounded Understanding of Schema for Text-to-SQL (ARGUS-SQL)
**Version:** 1.0 (Implementation Spec based on Capstone Proposal)
**Target Stack:** Google Cloud Platform (BigQuery, Cloud Run, Eventarc, Cloud Build, Terraform)
**LLMs:** Gemini 3 Flash (Routing/Profiling), Gemini 3 Pro (Reasoning/Generation)

---

## 1. System Architecture Overview

ARGUS-SQL is an event-driven, multi-agent serverless architecture operating exclusively on Google Cloud Platform, targeting BigQuery (GoogleSQL dialect). It is composed of two independent subsystems:

1. **The Profiler Subsystem (Async):** Runs independently of user queries to mitigate schema drift by continuously maintaining a semantic index of the data warehouse.
2. **The Query Engine Subsystem (Sync):** Handles real-time user requests through a 6-layer sequential pipeline.

**Global Constraints & Metrics:**
- **Execution Accuracy (EX):** >= 60% on Adapted BIRD dataset.
- **Valid SQL Rate:** >= 85%.
- **Security Denial Rate:** 100% for AST-detectable payloads.
- **Drift Robustness:** >= 0.85.
- **Latency Overhead:** P50 <= 8s, P95 <= 20s.

---

## 2. The 6-Layer Query Engine Pipeline

Data flows unidirectionally. If a validation stage fails, the flow returns to the Reasoning Layer forming a bounded self-correction loop.

### Layer 1: Knowledge Layer (Schema Profiler)
**Trigger:** Eventarc (BigQuery Audit Logs for DDL events). To handle bursty events efficiently, the trigger implements debouncing and batching. The profiler ensures idempotency by uniquely identifying each run using a combination of `table_id` and the event timestamp.
An asynchronous 5-stage deep profiling pipeline:
1. **Structural Metadata Extraction:** Extract tables, columns, types, PKs, FKs from BQ `INFORMATION_SCHEMA`.
2. **Statistical Value Sampling:** Bounded tablesample queries. `APPROX_TOP_COUNT` for strings, `MIN`/`MAX` for numerics. Detect/exclude high-cardinality IDs. The system executes bounded sampling queries utilizing TABLESAMPLE to limit bytes processed.
3. **Semantic Synthesis (Gemini 3 Flash):** Generate business-contextual narrative summaries of tables.
4. **Domain Classification:** Auto-classify tables into domains (e.g., Sales, HR) for downstream hard-filtering.
5. **HyDE Augmentation (Gemini 3 Flash):** Generate 5-15 synthetic business questions the table can answer.

### Layer 2: Input Processing Layer
**Components:**
- **Intent Router (Gemini 3 Flash):** Classifies input into `[Data Retrieval, Visualization, Out-of-Scope]` and extracts Domain. Drops ambiguous queries (confidence < 0.6).
- **Query Rewriter:** Uses session memory for co-reference resolution (e.g., "What about last year?") converting it to a self-contained explicit query.

### Layer 3: Retrieval Layer
**Type:** Hybrid Semantic-Keyword Retrieval natively in BigQuery.
1. **Domain Pre-Filter:** Hard-filter the vector index using the Domain extracted by the Router to prevent cross-domain hallucination.
2. **Dense Search:** Vector search against the semantic embedding column.
3. **Sparse Search:** Keyword search against the raw JSON M-Schema payload.
4. **Reciprocal Rank Fusion (RRF):** Combine scores (smoothing constant `k=60`) to select top-K tables.

### Layer 4: Reasoning and SQL Generation Layer
Strict separation of logical planning from SQL synthesis.
- **Agent 1: Subproblem Decomposer (SQL-of-Thought adaptation):** Identifies target tables, WHERE filters, GROUP BY, aggregations, HAVING, and unnesting requirements. Rejects meta-schema queries ("List all tables").
- **Agent 2: SQL Generator:** Uses Chain-of-Thought. Inherits logical plan and M-Schemas. Outputs executable GoogleSQL. Applies partition filters where appropriate.

### Layer 5: Validation & Correction Layer (Defense-In-Depth)
1. **AST Mutation Firewall (`sqlglot`):** Parses query to AST. Hard rejects any non-SELECT commands (DROP, INSERT, etc.). Neutralizes SQL injection structurally.
2. **BigQuery Dry Run:** Validates syntax. Estimates bytes processed. Halts if > 10GB (Resource Exhaustion DOS protection).
3. **RLS Enforcement:** Final execution uses a restricted IAM Service Account mapped to native BQ Row-Level Security.

**Self-Correction Loop (Error Taxonomist):**
Maps failures into a 10-category taxonomy: `[Syntax, Schema Link, Join, Filter, Aggregation, Value, Subquery, Set Operations, Other Issues, Security]`.
- Categories 1-9 are routed back to reasoning with specific corrective prompts.
- `Security` errors (AST failure, RLS failure) trigger immediate hard rejection, NO retry.

### Layer 6: Response Synthesis Layer
1. **Data-to-Text Summarization (Gemini 3 Flash):** Translates the DataFrame into a business narrative.
2. **Visualization Routing:** Programmatically recommends Line (time-series), Bar (categorical), or Table based on DataFrame structure.
3. **Auditability:** Outputs the exact executed GoogleSQL to the UI and logs to Cloud Logging.

---

## 3. Data Structures: Augmented M-Schema

The foundational artifact is the Augmented M-Schema stored natively inside a BigQuery embedding table.

**Table Definition:**
```sql
CREATE TABLE `project.dataset.meta_schema_embeddings` (
  table_id STRING NOT NULL PRIMARY KEY NOT ENFORCED,
  domain ARRAY<STRING>,              -- Used for Layer 3 hard pre-filtering
  last_updated TIMESTAMP,            -- Sync staleness monitoring
  m_schema_payload JSON,             -- Full semantic payload
  semantic_embedding ARRAY<FLOAT64>  -- Embedding generated natively via AI.GENERATE_EMBEDDING
);
```

**M-Schema JSON Payload Schema:**
The `m_schema_payload` encompasses the outputs of the 5-stage profiling layer. Its schema is structured as follows:
```json
{
  "table_name": "STRING",
  "domain_tags": ["STRING"],
  "semantic_summary": "STRING",
  "columns": [
    {
      "column_name": "STRING",
      "data_type": "STRING",
      "is_primary_key": "BOOLEAN",
      "foreign_key_references": ["STRING"],
      "description": "STRING",
      "stats": {
        "min_value": "ANY",
        "max_value": "ANY",
        "approx_top_values": ["ANY"]
      }
    }
  ],
  "hyde_questions": ["STRING"]
}
```

---

## 4. Evaluation and Testing Protocol

### 4.1 Datasets
1. **Internal Golden Dataset (50 queries):** Tests GoogleSQL dialect specifics.
   - 15 Unnesting/Array queries
   - 15 Partition-date filter queries
   - 10 BQ Date/Time function queries
   - 10 Window function queries (rank, lead, lag)
2. **Adapted BIRD Benchmark (~1,500 queries):** BigQuery-transpiled version of BIRD for broad generalization.

### 4.2 Schema Perturbation Protocol (Drift Testing)
Used to validate the Reactive Profiler.
1. **Baseline:** Run BIRD on static DB. Record Execution Accuracy.
2. **Perturbation:** Python automation script injects schema drift:
   - 30% of column names randomly renamed to business synonyms (e.g., `total_amount` -> `gross_revenue`).
   - 10% of numeric columns `ALTER COLUMN` cast to `STRING`.
3. **Latency Measurement:** Measure Eventarc delay until `meta_schema_embeddings` updates (target <30s).
4. **Recovery Validation:** Re-run benchmark. Calculate Drift Robustness (Score after drift / Score before drift).

### 4.3 Security Testing (Adversarial Suite)
- Run 20 custom zero-knowledge adversarial prompts.
- Ensure 100% Security Denial Rate.

### 4.4 Evaluation Metrics and Thresholds

**1. SchemaLinker Evaluation Protocol (Retrieval Layer metrics):**
- **Component Ablation Metrics:** 
  - *Dense-Only Recall@10:* Evaluates semantic retrieval natively via AI.GENERATE_EMBEDDING (Target: >= 0.72)
  - *Sparse-Only Recall@10:* BM25 keyword matching isolation (Target: >= 0.65)
  - *Fused Recall@10 (RRF):* Synergistic hybrid retrieval performance (Target: >= 0.90)
- **Granularity Metrics (Depth Assessment):**
  - *Table-Level Recall@10:* Correct tables in top 10 (Target: >= 0.90)
  - *Column-Level Recall@10:* Correct columns in top 10 (Target: >= 0.85)
  - *Exact Schema Match (ESM@10):* 100% of required tables AND columns in top 10 (Target: >= 0.80)
- **Rank Quality Metric:**
  - *NDCG@10:* Evaluates positional relevance within the top-10 retrieved elements (Target: >= 0.85)

**2. Downstream Metrics:**
- **Execution Accuracy (EX):** Exact result set match (Target: >= 60%)
- **Valid SQL Rate (VSR):** Passes AST and BigQuery Dry Run (Target: >= 85%)
- **Security Denial Rate (SDR):** Interception of adversarial payloads (Target: 100%)
- **Drift Robustness:** EX_drifted / EX_original (Target: >= 0.85)
- **Latency Overhead:** End-to-end response time (Target: p50 <= 8s, p95 <= 20s)

---

## 5. Deployment Setup (IaC)

- **Agentic Framework:** Gemini Enterprise Agent platform with Google ADK for agent development, deployment, and governance.
- **Infrastructure as Code:** HashiCorp Terraform.
- **CI/CD:** Google Cloud Build.
- **Database:** BigQuery (GoogleSQL dialect strictly).
- **Compute:** Google Cloud Run (Dockerized FastAPI backend).
- **Service Accounts:**
  - `Profiler SA`: Requires `roles/bigquery.metadataViewer`, `roles/bigquery.jobUser`.
  - `Query Engine SA`: Requires `roles/bigquery.jobUser`, explicitly constrained by specific Data Access policies and RLS rules.