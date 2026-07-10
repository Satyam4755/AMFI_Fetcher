# AMFI Fetcher

A robust, production-ready data pipeline for fetching, parsing, and normalizing Mutual Fund Scheme information and NAV details from the Association of Mutual Funds in India (AMFI). 

## Project Overview

AMFI Fetcher is a Python-based ETL (Extract, Transform, Load) system that builds a "Single Source of Truth" dataset for Indian mutual fund schemes. It automatically retrieves scheme investment strategies, downloads and parses undocumented Summary XLS files to extract composite mapping identifiers (SEBI, AMFI, and ISIN codes), and aggregates them into comprehensive CSV files.

## Features

- **Automated AMFI Fetching**: Discovers and requests live scheme details straight from AMFI APIs.
- **Document Enrichment**: Automatically scrapes and parses AMFI Summary XLS files.
- **CSV as Single Source of Truth**: Data is fully aggregated and enriched into a static CSV format.
- **Resilient Pipeline**: Graceful handling of missing (HTTP 404) documents and automatic rejection of invalid or corrupted downloads (e.g. HTML pages disguised as XLS).
- **Automatic Cleanup**: Seamlessly deletes temporary XLS files upon successful parsing to save disk space.
- **Production-Safe Logging**: Verbose yet non-spammy logging architecture that highlights actionable errors and suppresses expected warnings.

## Project Architecture

The system operates as a unified fetching pipeline: APIs are hit, Excel files are downloaded and parsed, composite keys are extracted using Regex, and a heavily enriched `sif_scheme.csv` is written to disk.

## Folder Structure

```text
AMFI_Fetcher/
├── config/
│   ├── __init__.py
│   └── settings.py
├── data/
│   ├── sif/
│   │   ├── nav/
│   │   │   └── YYYY-MM-DD.csv
│   │   └── schemes/
│   │       └── sif_X.json
├── scripts/
│   ├── fetch_scheme_data.py
│   └── fetch_sif_nav.py
├── services/
│   ├── __init__.py
│   ├── api_client.py
│   ├── composite_mapper_service.py
│   ├── csv_service.py
│   ├── parser.py
│   ├── scheme_api_client.py
│   ├── scheme_document_service.py
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

To scrape and generate the CSV payload for NAV data:
```bash
python scripts/fetch_sif_nav.py
```

To scrape and generate the CSV payload for Scheme data:
```bash
python scripts/fetch_scheme_data.py
```

## Automatic CSV Updates (GitHub Actions)

Every day, GitHub automatically performs:

**NAV Data:**
`AMFI NAV Text Endpoint` ➔ `fetch_sif_nav.py` ➔ `data/sif/nav/YYYY-MM-DD.csv` (Strict 3-column format: `sif_code,nav_date,nav`)

**Scheme Data:**
`AMFI Scheme APIs` ➔ `fetch_scheme_data.py` ➔ `data/sif/schemes/sif_X.json` (One nested JSON per scheme)

These CSV files act as our single source of truth. They are automatically refreshed by GitHub Actions, meaning absolutely **no manual work is required** to fetch new data.

## Pipeline Flow

1. **NAV Parsing**: Periodically runs to scrape the baseline `sif_id` index.
2. **Strategy Fetching**: Uses the `sif_id` to query AMFI's investment strategy endpoint to discover active `scheme_id`s.
3. **Detail Fetching**: Hits the scheme details endpoint.
4. **Document Scraping**: Queries the document service to locate the specific `Summary XLS` URL for the scheme.
5. **Validation & Download**: Downloads the document, validating the headers and binary signature to block HTML error pages.
6. **Parsing**: Uses Pandas to rip through the spreadsheet, while a composite mapper uses Regular Expressions to locate the precise SEBI, AMFI (`SIF-XX`), and ISIN (`INFXX`) codes.
7. **CSV Assembly**: Aggregates all arrays and attributes into `data/sif_scheme.csv`.

## Logging

Logging is centralized and configured to output to the console gracefully.
- **INFO**: General pipeline progression and extraction metrics.
- **WARNING**: Graceful handling of business-logic failures, specifically 404 missing files or rejected HTML bodies. These will *not* stop the pipeline.
- **ERROR**: Reserved for genuine structural crashes like timeouts or 500 server errors.

## Error Handling

- Missing pages (HTTP 404) are treated as expected states. The CSV will just contain empty identifiers for that scheme.
- Corrupted documents or HTML payloads masquerading as `.xls` files are rejected based on byte signatures before touching disk.

## Example Output

```text
Starting Scheme Fetch Pipeline...

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

--- Pipeline Success Summary ---
- Scheme data fetched successfully.
- CSV generated successfully.
```

## Future Improvements

- Add asynchronous fetching to speed up I/O-bound document scraping.
- Shift configuration flags (like log levels) directly into `.env` configurations.

## Technologies Used
- **Language**: Python 3.10
- **Data Pipeline**: Pandas, Requests, xlrd, re
- **Architecture**: Decoupled CSV-First ETL

## License
MIT License