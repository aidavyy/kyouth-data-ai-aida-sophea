# kyouth-data-ai-aida-sophea Module 1

## Project Description


This project implements a local, file-based ETL pipeline for job listing data using a **Medallion architecture** (Bronze → Silver → Gold).

Raw `.mhtml` files are:
1. Extracted into HTML (Bronze layer)
2. Cleaned and structured into JSON (Silver layer)
3. Loaded into a SQLite database (Gold layer)
4. Profiled to generate a data-quality report

The goal is to show how a small pipeline can follow the same ideas used in production data platforms: preserve raw inputs, transform data in stages, enforce basic integrity, and produce a queryable final store.


## Project Structure

```text
week1/
├── data/
│   ├── 0_source/     # Raw .mhtml input files
│   ├── 1_bronze/     # Extracted HTML files
│   ├── 2_silver/     # Cleaned JSON files
│   └── 3_gold/       # Final SQLite database
├── src/
│   ├── ingestor.py
│   ├── loader.py
│   ├── processor.py
│   └── profiler.py
├── .gitignore
├── .python-version
├── main.py
├── pyproject.toml
├── README.md
└── uv.lock
```


## Setup Instructions

### Prerequisites

- Python 3.14 or newer, matching the version declared in [pyproject.toml](pyproject.toml)
- `uv` for environment management and dependency installation
- A folder of input `.mhtml` files placed in `data/0_source/`

```bash
uv python install 3.14
```

### Install Dependencies

From the `week1/` folder, create and sync the environment with `uv`:

```bash
uv sync
```

If `uv` is not installed, install it first using the official installer for your platform, then rerun `uv sync`.

### Environment Variables

This project does not currently require environment variables or API keys. If you add any later, store them in a local `.env` file or your shell profile and do not commit secrets to git.

## Usage

Run commands from the `week1/` directory so the relative `data/` paths resolve correctly.

### Input Data
Place .mhtml files inside: 
`data/0_source/`

This performs the full sequence:

1. Ingest `.mhtml` files from `data/0_source/` into `data/1_bronze/`
2. Transform HTML into structured JSON in `data/2_silver/`
3. Load JSON into SQLite at `data/3_gold/jobs.db`
4. Profile the database and print a data-quality summary

### Module 1: Extractor / Bronze Layer

Extract `.mhtml` files into `.html` files.

```bash
uv run python main.py ingest
```

Input:

```text
data/0_source/*.mhtml
```

Output:

```text
data/1_bronze/*.html
```

Expected summary:

```text
Total: 100 | Extracted: 100 | Failed: 0
```

---

### Module 2: Treatment Plant / Silver Layer

Process `.html` files into structured `.json` files.

```bash
uv run python main.py process
```

Input:

```text
data/1_bronze/*.html
```

Output:

```text
data/2_silver/*.json
```

Expected summary:

```text
Total: 100 | Processed: 84 | Skipped: 16
```

---

### Module 3: Blueprint & The Vault / Gold Layer

Load `.json` files into SQLite.

```bash
uv run python main.py load
```

Input:

```text
data/2_silver/*.json
```

Output:

```text
data/3_gold/jobs.db
```

Expected summary for the first run:

```text
Total: 84 | Inserted: 84 | Skipped: 0 | Failed: 0
```

If the command is run again, duplicate records will be skipped because `source_id` is the primary key.

---

### Module 4: QA Inspector & Orchestrator

Run the data quality report.

```bash
uv run python main.py profile
```

Expected output format:

```text
--- 🔍 DATA QUALITY REPORT ---
📊 Total Records: 84
❓ Missing Values -> job_title: 0, company: 0, description: 0
📏 Avg Description Length: <number> chars
⚠️ Shortest Description: <number> chars
   ↳ source_id: <SOURCE_ID> | job_title: <JOB_TITLE>
📌 Longest Description: <number> chars
   ↳ source_id: <SOURCE_ID> | job_title: <JOB_TITLE>
```

Run the full pipeline:

```bash
uv run python main.py all
```

Full sequence:

```text
ingest -> process -> load -> profile
```

## Technical Reflections

### Module 1: The Extractor (Medallion & Lakehouses)

Why is it useful to keep the original raw HTML files instead of directly inserting processed data into the database?
- **Answer**: Keeping the raw `.mhtml` and extracted HTML files preserves the source of truth. If the parsing logic changes, a field is extracted incorrectly, or a bug appears later, the pipeline can be replayed from the original files without needing to re-collect the data. Raw files also make it easier to compare what was received versus what was transformed, which is important for debugging broken encodings, missing sections, or unexpected page layouts.

### Module 2: Treatment Plant (ETL vs ELT & Scale)

Why do cloud systems prefer loading raw data first before cleaning it (ELT)? What problems happen when processing files sequentially, and how does distributed processing help?
- **Answer**: Cloud systems often prefer ELT because raw data can be stored cheaply and transformed later with better tooling, stronger lineage, and more flexible business logic. Sequential processing becomes slow and fragile as file volume grows, because one bad file or one long-running record can delay the whole pipeline. Distributed processing helps by splitting work across many workers, which improves throughput, isolates failures better, and makes large-scale transformations practical.

### Module 3: The Blueprint & The Vault (Storage & Contracts)

What should happen if an important field like job_title disappears? Why fail early instead of silently inserting nulls into DB? How does INSERT OR IGNORE help prevent duplicate records?
- **Answer**: If a required field like `job_title` disappears, the record should be rejected or quarantined because incomplete rows can break dashboards, distort metrics, and hide upstream data quality problems. Failing early makes the contract violation visible immediately instead of letting bad data spread quietly through the warehouse. `INSERT OR IGNORE` helps make the load idempotent by skipping duplicate `source_id` values, so rerunning the pipeline does not create duplicate rows in SQLite.

### Module 4: The QA Inspector & Orchestrator (Orchestration & DAGs)

What happens if `processor.py` crashes halfway? How are automated orchestration tools more reliable than manual retries with Python scripts?
- **Answer**: If `processor.py` crashes halfway, only part of the silver layer is produced, which can leave the pipeline in an inconsistent state and make it unclear which files were already handled. Manual retries require a human to inspect logs, decide what to rerun, and avoid duplicating work. Orchestration tools like Airflow are more reliable because they track task state, dependencies, retries, and scheduling explicitly, which makes recovery and repeatability much safer.
