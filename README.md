# AMFI Fetcher

A robust, production-ready data pipeline for fetching, parsing, and normalizing Mutual Fund Scheme information and NAV details from the Association of Mutual Funds in India (AMFI). 

## Project Overview

AMFI Fetcher is a Python-based ETL (Extract, Transform, Load) system that builds a "Single Source of Truth" relational database for Indian mutual fund schemes. It automatically retrieves scheme investment strategies, downloads and parses undocumented Summary XLS files to extract composite mapping identifiers (SEBI, AMFI, and ISIN codes), aggregates them into a comprehensive CSV, and securely imports everything into a fully normalized SQLite database.

## Features

- **Automated AMFI Fetching**: Discovers and requests live scheme details straight from AMFI APIs.
- **Document Enrichment**: Automatically scrapes and parses AMFI Summary XLS files.
- **CSV as Single Source of Truth**: Data is fully aggregated and enriched into a static CSV format before touching the database.
- **Relational SQLite Import**: Safely UPSERTs data into a highly structured, normalized database schema with strictly enforced referential integrity.
- **Resilient Pipeline**: Graceful handling of missing (HTTP 404) documents and automatic rejection of invalid or corrupted downloads (e.g. HTML pages disguised as XLS).
- **One-Command Update**: Complete end-to-end orchestration using a single script `python scripts/update_scheme_database.py`.
- **Automatic Cleanup**: Seamlessly deletes temporary XLS files upon successful parsing to save disk space.
- **Production-Safe Logging**: Verbose yet non-spammy logging architecture that highlights actionable errors and suppresses expected warnings.

## Project Architecture

The system operates in a decoupled, two-phase pipeline:
1. **The Fetch Phase**: APIs are hit, Excel files are downloaded and parsed, composite keys are extracted using Regex, and a heavily enriched `sif_scheme.csv` is written to disk.
2. **The Import Phase**: The CSV acts as the sole payload, natively unpacking compound fields and importing them via robust `INSERT OR IGNORE` UPSERTS into multiple normalized mapping tables in SQLite.

## Folder Structure

```text
AMFI_Fetcher/
├── config/
│   ├── __init__.py
│   └── settings.py
├── data/
│   ├── sif_nav.csv
│   └── sif_scheme.csv
├── database/
│   └── scheme.db
├── scripts/
│   ├── fetch_scheme_data.py
│   ├── fetch_sif_nav.py
│   ├── import_scheme_csv.py
│   └── update_scheme_database.py
├── services/
│   ├── __init__.py
│   ├── api_client.py
│   ├── composite_mapper_service.py
│   ├── csv_service.py
│   ├── parser.py
│   ├── scheme_api_client.py
│   ├── scheme_document_service.py
│   ├── scheme_insert_service.py
│   ├── scheme_sqlite_service.py
│   ├── sqlite_service.py
│   ├── xls_download_service.py
│   └── xls_parser_service.py
├── temp/
│   └── xls/                   # Auto-cleaned during execution
├── README.md
└── requirements.txt
```

## Installation

### Requirements
- Python 3.10+
- Pandas
- Requests
- xlrd (for parsing legacy XLS formats)

### Setup Environment
1. Clone the repository:
   ```bash
   git clone https://github.com/Satyam4755/AMFI_Fetcher.git
   cd AMFI_Fetcher
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## How to Run

To execute the entire pipeline end-to-end safely:
```bash
python scripts/update_scheme_database.py
```

If you prefer to run the decoupled phases manually:
```bash
# 1. Scrape and generate the CSV payload
python scripts/fetch_scheme_data.py

# 2. Re-build and populate the SQLite Database
python scripts/import_scheme_csv.py
```

## Keeping the SQLite Database Updated

### Automatic CSV Updates (GitHub Actions)

Every day, GitHub automatically performs:

**NAV Data:**
`AMFI NAV API` ➔ `fetch_sif_nav.py` ➔ `data/sif_nav.csv`

**Scheme Data:**
`AMFI Scheme APIs` ➔ `fetch_scheme_data.py` ➔ `data/sif_scheme.csv`

These CSV files act as our single source of truth. They are automatically refreshed by GitHub Actions, meaning absolutely **no manual work is required** to fetch new data.

---

### Updating the Local SQLite Database

Whenever the latest CSV files are pulled from GitHub, you can instantly update the local SQLite database to reflect the newest data using the orchestrator scripts.

**For NAV Data:**
```bash
python scripts/update_nav_database.py
```

**For Scheme Data:**
```bash
python scripts/update_scheme_database.py
```

These scripts will safely read the respective CSV payloads, unpack the contents, and UPSERT everything securely into your SQLite schema.

## Pipeline Flow

1. **NAV Parsing**: Periodically runs to scrape the baseline `sif_id` index.
2. **Strategy Fetching**: Uses the `sif_id` to query AMFI's investment strategy endpoint to discover active `scheme_id`s.
3. **Detail Fetching**: Hits the scheme details endpoint.
4. **Document Scraping**: Queries the document service to locate the specific `Summary XLS` URL for the scheme.
5. **Validation & Download**: Downloads the document, validating the headers and binary signature to block HTML error pages.
6. **Parsing**: Uses Pandas to rip through the spreadsheet, while a composite mapper uses Regular Expressions to locate the precise SEBI, AMFI (`SIF-XX`), and ISIN (`INFXX`) codes.
7. **CSV Assembly**: Aggregates all arrays and attributes into `data/sif_scheme.csv`.
8. **Database Normalization**: Opens SQLite (enforcing `PRAGMA foreign_keys = ON`), constructs tables, unpacks semicolon-delimited CSV fields, and executes atomic UPSERTs.

## Database Schema

The database leverages strict referential integrity.

**`sif_master`**
- `sif_id` (PK)
- `sif_name`
- `amc_website`

**`scheme_master`**
- `scheme_id` (PK)
- `sif_id` (FK to `sif_master`)
- `scheme_name`, `scheme_type`, `category`, `objective`, `launch_date`, `load`, `min_amt`
- `sebi_code` (UNIQUE)

**`amfi_composite_mapping`**
- `id` (PK Auto-Increment)
- `sebi_code` (FK to `scheme_master`)
- `amfi_code`
- **Constraints**: `UNIQUE(sebi_code, amfi_code)`
- **Indexes**: `sebi_code`, `amfi_code`

**`isin_composite_mapping`**
- `id` (PK Auto-Increment)
- `sebi_code` (FK to `scheme_master`)
- `isin`
- **Constraints**: `UNIQUE(sebi_code, isin)`
- **Indexes**: `sebi_code`, `isin`

## Logging

Logging is centralized and configured to output to the console gracefully.
- **INFO**: General pipeline progression, extraction metrics, and database schema creation success.
- **WARNING**: Graceful handling of business-logic failures, specifically 404 missing files or rejected HTML bodies. These will *not* stop the pipeline.
- **ERROR**: Reserved for genuine structural crashes like timeouts, 500 server errors, or SQLite lock failures.

## Error Handling

- Missing pages (HTTP 404) are treated as expected states. The database will just insert the scheme with `null` identifiers.
- Corrupted documents or HTML payloads masquerading as `.xls` files are rejected based on byte signatures before touching disk.
- Database constraints prevent duplicate inserts entirely via `INSERT OR IGNORE` loops.

## Example Output

```text
Starting Full Scheme Update Pipeline...

--- Running fetch_scheme_data.py ---
Found 14 unique SIFs in NAV data...
Processing SIF 1/14 (sif_id: 47)...
  -> Fetching detail for scheme_id: S-22...
  -> Fetching detail for scheme_id: S-3...
INFO: Successfully downloaded XLS to: temp/xls/SSD_S-3.xls
INFO: Successfully parsed 67 rows...
INFO: Built composite mapping: 1 SEBI code, 4 AMFI mappings, 8 ISIN mappings.
     Deleted temporary XLS: temp/xls/SSD_S-3.xls
...
Fetch Pipeline Completed

--- Running import_scheme_csv.py ---
Connecting to SQLite database at database/scheme.db...
Successfully created database schema.
Found 27 records in data/sif_scheme.csv...
Import Pipeline Completed

--- Pipeline Success Summary ---
- Scheme data fetched successfully.
- CSV generated successfully.
- SQLite database updated successfully.
- Full update completed.
```

## Future Improvements

- Add asynchronous fetching to speed up I/O-bound document scraping.
- Shift configuration flags (like log levels) directly into `.env` configurations.
- Add robust data migration (Alembic) support if the SQLite schema scales into multiple layers.

## Technologies Used
- **Language**: Python 3.10
- **Data Pipeline**: Pandas, Requests, xlrd, re
- **Database**: SQLite3 (Native Python)
- **Architecture**: Decoupled CSV-First ETL

## License
MIT License