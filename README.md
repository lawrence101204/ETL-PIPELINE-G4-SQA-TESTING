<!-- SQA-TESTING-SECTION -->

# Paintelligent ETL Pipeline - SQA Final Project

![Automated Testing](https://github.com/lawrence101204/ETL-PIPELINE-G4-SQA-TESTING/actions/workflows/unit-testing.yml/badge.svg)

![Tests](https://img.shields.io/badge/Tests-54%20Passed-brightgreen)
![Required Cases](https://img.shields.io/badge/Required%20Cases-19%2F19-brightgreen)
![Python](https://img.shields.io/badge/Python-3.13.0-blue)
![Pytest](https://img.shields.io/badge/Pytest-9.2.0-blue)
![Pass Rate](https://img.shields.io/badge/Pass%20Rate-100%25-brightgreen)

## Project Information

| Information | Details |
|---|---|
| Author | Villalobos Lawrence C. |
| Subject | Software Quality Assurance |
| Project | Paintelligent ETL Pipeline |
| Testing Date | November 25, 2026 |
| Testing Framework | Pytest 9.2.0 |
| Programming Language | Python 3.13.0 |
| Continuous Integration | GitHub Actions |

## Project Overview

This repository contains automated unit tests for the
Paintelligent ETL Pipeline, covering Extraction,
Transformation, and Loading.

It is a separate testing repository created for the
Software Quality Assurance final project.

The original group repository remains separate.

## Final Test Results

| ETL Stage | Required | Additional | Passed | Failed |
|---|---:|---:|---:|---:|
| Extraction | 5 | 14 | 19 | 0 |
| Transformation | 6 | 10 | 16 | 0 |
| Loading | 8 | 11 | 19 | 0 |
| Total | 19 | 35 | 54 | 0 |

### Verified Execution Results

| Environment | Passed | Failed | Execution Time |
|---|---:|---:|---:|
| Local Windows Environment | 54 | 0 | 7.01 seconds |
| GitHub Actions | 54 | 0 | 3.04 seconds |

All 19 required test cases and 35 additional
test executions passed successfully.

## Testing Features

- Automated unit testing
- Synthetic test datasets
- Mocked database connections
- Mocked extraction dependencies
- Data completeness validation
- Data consistency validation
- Data transformation validation
- Boundary value analysis
- Duplicate record validation
- Data integrity validation
- Database error handling
- Transaction rollback verification
- Regression testing
- Continuous integration
- Custom terminal test reporter

## Installation

Clone this repository:

```bash
git clone https://github.com/lawrence101204/ETL-PIPELINE-G4-SQA-TESTING.git
cd ETL-PIPELINE-G4-SQA-TESTING
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Running the Tests

### All ETL Test Suites

```powershell
.\.venv\Scripts\python.exe run_tests.py all
```

### Extraction

```powershell
.\.venv\Scripts\python.exe run_tests.py extraction
```

### Transformation

```powershell
.\.venv\Scripts\python.exe run_tests.py transformation
```

### Loading

```powershell
.\.venv\Scripts\python.exe run_tests.py loading
```

### Standard Pytest Execution

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

## Expected Test Summary

```text
Total collected : 54
Passed          : 54
Failed          : 0
Errors          : 0
Skipped         : 0
Pass rate       : 100.00%

========== 54 PASSED ==========
ALL TESTS PASSED SUCCESSFULLY

Pytest exit code: 0
```

## Continuous Integration

GitHub Actions automatically executes the unit tests
when changes are pushed to the main branch or when
a pull request targets the main branch.

The workflow supports manual execution as well.

[View GitHub Actions](https://github.com/lawrence101204/ETL-PIPELINE-G4-SQA-TESTING/actions)

## Testing Documentation

- [Extraction Test Report](docs/testing/extraction_test_report.md)
- [Transformation Test Report](docs/testing/transformation_test_report.md)
- [Loading Test Report](docs/testing/loading_test_report.md)
- [Final Testing Summary](docs/testing/final_testing_summary.md)

## Testing Evidence

- [Extraction Results](reports/extraction_results.txt)
- [Transformation Results](reports/transformation_results.txt)
- [Loading Results](reports/loading_results.txt)
- [Final Regression Results](reports/final_regression_results.txt)
- [JUnit XML Results](reports/final_regression_results.xml)

## Testing Scope and Limitations

Tests use synthetic data, mocked dependencies, and
isolated temporary directories.

The 100% pass rate represents the executed test
scenarios and does not indicate complete code coverage.

Actual production database operations and complete
end-to-end integration testing are outside the
verified testing scope.

The documented stock validation discrepancy remains
subject to business-rule clarification.

---

# Original ETL Project Documentation

# Lab 2 – Technical Metadata Documentation

## 1. Pipeline Metadata

The proposed **Product, Sales and Paint Analysis Pipeline** processes exported data from the Paintelligent Supabase database. Python is used for data ingestion, cleaning, transformation, and ETL orchestration, while SQLite is used for data storage and SQL-based analysis. The pipeline is designed to process exported datasets whenever new files are provided rather than operating continuously. Its main purpose is to convert raw sales, product, and paint analysis data into clean, structured, and analysis-ready information for business decision-making. :contentReference[oaicite:1]{index=1}

## 2. Data Lineage

The data lineage describes how data moves through the proposed ETL pipeline. The process begins with exported sales, product, and paint analysis data from Supabase. The data is ingested using Python, checked and cleaned for quality issues, transformed and standardized, and then loaded into SQLite. SQL queries are used to organize and retrieve the processed information. The final output consists of business-oriented metrics and insights such as top-selling products, slow-moving products, sales trends, and product performance. :contentReference[oaicite:2]{index=2}

### Six-Stage Data Lineage

1. **Source** – Exported sales, product, and paint analysis datasets are prepared from the Paintelligent Supabase database.
2. **Ingestion** – Python reads and imports the raw exported files into the ETL pipeline.
3. **Cleaning** – The data is checked for missing values, duplicates, inconsistent formats, invalid values, and other quality issues.
4. **Transformation** – Data types and values are standardized, required fields are calculated, and records are organized into a consistent structure.
5. **Storage & Querying** – Transformed data is loaded into SQLite tables and queried using SQL for business analysis.
6. **Business Output** – The processed data is used to generate business reports, analytical results, and decision-support insights. :contentReference[oaicite:3]{index=3}

## 3. Schema Metadata

The proposed SQLite database contains three main tables: **product_table**, **sales_table**, and **paint_analysis_table**. The schema defines the columns, data types, primary keys, foreign keys, and relationships needed for business-oriented analysis. The ETL system works separately from the operational Paintelligent database, using exported data as its source and loading the processed information into SQLite. :contentReference[oaicite:4]{index=4}

### Main Tables

- **product_table** – Stores product information such as product ID, name, category, brand, price, cost, stock quantity, and status.
- **sales_table** – Stores sales transactions including sale ID, product ID, sale date, quantity sold, total amount, and aggregated sales.
- **paint_analysis_table** – Stores paint analysis information including analysis ID, product ID, color, finish, components, and analysis date. :contentReference[oaicite:5]{index=5}

### Keys and Relationships

The primary keys are `product_id` for products, `sale_id` for sales, and `analysis_id` for paint analysis. The `product_id` in the Paint Analysis table serves as a foreign key connecting paint analysis records to their corresponding products. The Product and Paint Analysis tables have a **one-to-many relationship**, while multiple paint analysis records can refer to the same product. The Sales table has no direct foreign-key relationship with either Product or Paint Analysis in the proposed schema. :contentReference[oaicite:6]{index=6}

## 4. Technology Justification

**Python** was selected for ETL processing because it can handle data extraction, cleaning, transformation, validation, automation, and analysis. It allows the exported datasets to be processed and prepared for business-oriented use.

**SQLite** was selected for data storage because it is lightweight, simple to deploy, and does not require a separate database server. It provides SQL capabilities for querying and analyzing structured data, supporting outputs such as product performance and sales trends. :contentReference[oaicite:7]{index=7}