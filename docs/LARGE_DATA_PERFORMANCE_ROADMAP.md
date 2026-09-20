# DataPilot AI — Large Data & Performance Roadmap

## Purpose

DataPilot must remain stable and usable when working with datasets much larger
than the small CSV files used during development.

The application should not assume that every dataset fits comfortably into RAM.

Target examples include:

- thousands of rows
- hundreds of thousands of rows
- millions of rows
- potentially tens of millions of rows

The system should automatically choose an appropriate processing strategy
instead of treating every dataset the same way.

---

# 1. Core Principle

Small datasets and large datasets do not need to use the same execution path.

Target architecture:

```text
Dataset
   ↓
Inspect size / format / estimated memory
   ↓
Processing strategy

Small data
→ Pandas / standard local engine

Medium data
→ optimized local processing

Large data
→ DuckDB / Polars / lazy processing
→ columnar storage
→ paginated preview
→ aggregate validation

2. Current Limitations
The current development version is optimized for small test datasets.
Known scalability risks:
- file.file.read() can load the entire upload into memory
- pd.read_csv() can load the full dataset into RAM
- Working datasets may be materialized completely as pandas DataFrames
- Some API responses may return many rows to the frontend
- Repeated profiling may scan the same dataset multiple times
- Large transformations can consume too much memory
- Long-running operations currently use normal synchronous request flow
- No explicit memory / CPU limits yet
- No large-dataset benchmark suite yet
These are acceptable for the current Functional MVP but must be addressed
before production-scale claims.
3. Dataset Size Classification
DataPilot should inspect a dataset before choosing the processing engine.
Possible classification:
Small
→ normal in-memory processing

Medium
→ optimized / lazy processing

Large
→ dedicated large-data processing mode
Classification may use:
- file size
- estimated row count
- column count
- data types
- estimated memory footprint
- file format
Exact limits should be based on benchmarks rather than hard-coded assumptions.
4. Streaming Uploads
Avoid loading the entire uploaded file into memory.
Planned work:
- Stream uploads to disk
- Read uploaded data in chunks where appropriate
- Add upload size limits
- Show upload progress
- Handle interrupted uploads
- Clean temporary files safely
- Avoid duplicate in-memory copies of the same dataset
5. Large Data Processing Engine
Evaluate local analytical engines for large datasets.
Primary candidates:
- DuckDB
- Polars
- PyArrow
Possible strategy:
CSV
 ↓
local ingestion
 ↓
Parquet
 ↓
DuckDB / Polars
 ↓
profiling
transformations
aggregations
validation
Goals:
- Process datasets larger than available RAM where possible
- Use lazy execution
- Push filters and projections down
- Read only required columns
- Avoid unnecessary DataFrame copies
- Support efficient aggregations
- Keep deterministic validation available
6. Parquet / Columnar Storage
CSV should not necessarily remain the internal working format.
Potential workflow:
Raw CSV
   ↓
validated ingestion
   ↓
Parquet working dataset
   ↓
transformations / profiling / analysis
Benefits to evaluate:
- lower storage size
- faster column reads
- better analytical performance
- typed schema
- better interoperability with analytical tools
Planned work:
- CSV → Parquet conversion
- Preserve original source
- Store working versions efficiently
- Version metadata
- Measure disk-space tradeoffs
7. Frontend Data Safety
The frontend must never receive millions of rows.
Target behavior:
Full dataset
     ↓
Backend
     ↓
Preview only
Frontend should receive:
- small preview sample
- row count
- column metadata
- profiling summary
- findings
- aggregate statistics
- paginated results where needed
Planned work:
- Row pagination
- Column pagination if needed
- Preview row limits
- Server-side filtering
- Server-side sorting
- Avoid full dataset JSON responses
8. Profiling at Scale
Profiling must remain useful without repeatedly loading the entire dataset.
Planned work:
- Single-pass profiling where possible
- Cached profiling results
- Incremental statistics
- Efficient null counting
- Efficient duplicate detection
- Approximate statistics where explicitly acceptable
- Column-specific profiling
- Avoid repeated full scans
Important:
Approximation must not silently replace deterministic validation.
The UI should distinguish:
- preview / estimate
- full validation
- sampled analysis
9. Sampling Strategy
Sampling can be used for:
- UI previews
- exploratory analysis
- initial visualization
- development guidance
Sampling should NOT automatically be treated as proof that the whole dataset
is correct.
Example:
10,000-row sample
→ useful for exploration

Full dataset
→ required for claims such as:
   "all duplicates removed"
   "no missing values remain"
Planned work:
- Define sampling rules
- Make sampled results visible in UI
- Prevent sampled results from being presented as full validation
- Full-data deterministic validation where feasible
10. Transformation Performance
Large transformations should avoid unnecessary memory copies.
Planned work:
- Lazy transformations
- SQL-based transformations where useful
- Column projection
- Filter pushdown
- Chunk-aware operations
- Efficient joins
- Efficient group-by operations
- Transformation cost estimation
- Prevent dangerous full-data operations where possible
11. Background Jobs
Long operations should not keep a normal HTTP request open indefinitely.
Candidates:
- large file ingestion
- profiling
- duplicate scanning
- heavy transformation
- export
- conversion to Parquet
- large validation jobs
Target flow:
User starts job
      ↓
Backend creates job
      ↓
Processing continues
      ↓
Frontend polls / receives progress
      ↓
Completed / failed / cancelled
Planned work:
- Background job model
- Job status endpoint
- Progress percentage
- Current processing stage
- Failure reason
- Retry policy
- Cancellation
12. Progress UI
Large-data work should clearly show what is happening.
Example:
Profiling dataset

43%

✓ Schema inspection
✓ Missing-value scan
● Duplicate detection
○ Statistical profile
Planned work:
- Upload progress
- Processing progress
- Current operation
- Estimated remaining stages
- Cancel action
- Clear failure messages
13. Resource Protection
The application should fail safely instead of crashing the entire service.
Planned work:
- Memory limits
- CPU limits
- Request limits
- Query timeouts
- Job timeouts
- Disk-space checks
- Temporary-storage limits
- Graceful out-of-memory handling
- Prevent multiple uncontrolled heavy jobs
The user should receive an actionable error instead of the application
becoming unavailable.
14. Caching
Avoid repeating expensive work.
Possible cached outputs:
- dataset profile
- schema
- null statistics
- duplicate statistics
- analysis results
- aggregates
- data model metadata
Cache should be invalidated when:
- source dataset changes
- working dataset changes
- transformation changes relevant data
15. Validation at Scale
Deterministic validation remains the source of truth.
Large datasets may use engines such as DuckDB to perform full-data checks
without loading everything into Python memory.
Examples:
SELECT COUNT(*)
FROM dataset;

SELECT COUNT(*)
FROM dataset
WHERE age IS NULL;
Possible validations:
- row count
- schema
- null counts
- duplicates
- uniqueness
- range checks
- referential integrity
- business expectations
16. Power BI / BI Outputs
Large Personal Projects should not necessarily export one giant raw CSV.
Preferred future output may look like:
project/
├── fact_sales.parquet
├── dim_date.parquet
├── dim_region.parquet
├── data_dictionary.md
├── kpi_definitions.md
└── powerbi_model_spec.md
Possible benefits:
- smaller model
- clearer star schema
- faster BI consumption
- professional portfolio/client output
17. Performance Benchmarks
Create repeatable benchmark datasets.
Suggested initial sizes:
- 10,000 rows
- 100,000 rows
- 1,000,000 rows
- 5,000,000 rows
- 10,000,000+ rows where hardware permits
Measure:
- ingestion time
- profiling time
- transformation time
- validation time
- memory usage
- disk usage
- API response size
Do not make scalability claims without benchmark evidence.
18. Performance Regression Tests
Add tests for:
- upload memory behavior
- pagination
- preview limits
- large profile execution
- cancellation
- timeout behavior
- disk cleanup
- cache invalidation
- full-data validation
- repeated-job protection
19. Offline / Secure Work Compatibility
Large-data architecture must also work with Local Secure Mode.
Confidential datasets should be able to use:
Local storage
+
DuckDB / Polars
+
Deterministic engine
+
Local LLM
without requiring external cloud processing.
Large dataset size must never be used as a reason to bypass organization
security policy.
20. Development Order
Do not interrupt the current Personal Project workflow implementation.
After the current end-to-end Personal Project flow is functional:
1. Benchmark current implementation
2. Identify actual bottlenecks
3. Introduce dataset-size classification
4. Stop full-dataset frontend responses
5. Add streaming / disk-based ingestion
6. Evaluate DuckDB and Polars
7. Add Parquet working storage
8. Add background jobs
9. Add resource limits
10. Build benchmark / regression suite
21. Product Goal
Large datasets should change DataPilot's execution strategy, not break the
application.
Target behavior:
Dataset arrives
      ↓
DataPilot assesses scale
      ↓
Chooses safe processing strategy
      ↓
Processes efficiently
      ↓
Junior continues the same guided workflow
The complexity of the processing engine should remain mostly hidden from the
junior user.

Sonra `docs/PRODUCT_ROADMAP.md` dosyasında **Immediate Development Plan** bölümünün sonuna da şu kısa bölümü ekleyelim:

```md
## Phase F — Large Data & Performance

Follow `LARGE_DATA_PERFORMANCE_ROADMAP.md`.

Key priorities:

- streaming ingestion
- dataset-size classification
- DuckDB / Polars evaluation
- Parquet working storage
- lazy processing
- frontend pagination / preview limits
- background jobs
- memory and CPU protection
- caching
- large-data deterministic validation
- performance benchmark suite