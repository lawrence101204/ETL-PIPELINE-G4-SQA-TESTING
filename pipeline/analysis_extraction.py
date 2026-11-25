
import os
import re
import time
import uuid

import pandas as pd

from datetime import datetime
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "analysis_extraction.log"


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def generate_run_id() -> str:
    date_part = datetime.now().strftime("%Y%m%d")
    unique_part = uuid.uuid4().hex[:6].upper()

    return f"RUN-{date_part}-{unique_part}"


# ============================================================
# EXTRACTION REPORT
# ============================================================

def log_extraction_report(report: dict) -> None:

    divider = "=" * 70

    lines = [
        "",
        divider,
        f"[{get_timestamp()}] EXTRACTION REPORT",
        divider,
        f"Pipeline Run ID             : {report['pipeline_run_id']}",
        f"Table or File Name          : {report['source_name']}",
        f"Extraction Start Timestamp  : {report['start_timestamp']}",
        f"Extraction End Timestamp    : {report['end_timestamp']}",
        f"Extraction Status           : {report['status']}",
        f"Number of Records Read      : {report['records_read']}",
        f"Number of Records Extracted : {report['records_extracted']}",
        f"Number of Records Rejected  : {report['records_rejected']}",
        f"Extraction Window           : {report['data_range']}",
        f"Validation Results          : {report['validation_result']}",
        f"Error Message or Error Code : {report['error']}",
        f"Extraction Duration         : {report['duration']}",
        divider,
        "",
    ]

    message = "\n".join(lines)

    print(message)

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    with LOG_FILE.open("a", encoding="utf-8") as log:
        log.write(message + "\n")


# ============================================================
# SUPABASE CONNECTION
# ============================================================

def get_supabase_client() -> Client:

    load_dotenv()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        raise ValueError(
            "Missing SUPABASE_URL or SUPABASE_KEY "
            "in environment variables."
        )

    return create_client(url, key)


# ============================================================
# DATA COMPLETENESS VALIDATION
# ============================================================

def validate_data_completeness(
    df: pd.DataFrame,
    required_columns: list[str],
) -> None:

    for column in required_columns:

        if column not in df.columns:
            raise ValueError(
                f"Data completeness validation failed: "
                f"Required column '{column}' is missing."
            )

        values = df[column]

        missing = values.isna() | values.map(
            lambda value:
                isinstance(value, str)
                and not value.strip()
        )

        missing_count = int(missing.sum())

        if missing_count > 0:
            raise ValueError(
                f"Data completeness validation failed: "
                f"{missing_count} missing required "
                f"value(s) in '{column}'."
            )


# ============================================================
# DATA CONSISTENCY VALIDATION
# ============================================================

def is_valid_identifier(value) -> bool:

    if not isinstance(value, str):
        return False

    if not value.strip():
        return False

    # Reject recognizable ISO date values used as IDs.
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):

        try:
            datetime.strptime(
                value.strip(),
                "%Y-%m-%d"
            )

        except ValueError:
            pass

        else:
            return False

    return True


def validate_data_consistency(
    df: pd.DataFrame,
    identifier_column: str = "id",
) -> None:

    if identifier_column not in df.columns:
        raise ValueError(
            f"Data consistency validation failed: "
            f"Missing identifier column "
            f"'{identifier_column}'."
        )

    identifiers = df[identifier_column]

    invalid = ~identifiers.map(is_valid_identifier)

    invalid_count = int(invalid.sum())

    if invalid_count > 0:
        raise ValueError(
            f"Data consistency validation failed: "
            f"{invalid_count} invalid identifier(s) "
            f"detected."
        )

    if identifiers.duplicated().any():
        raise ValueError(
            "Data consistency validation failed: "
            "Duplicate identifiers detected."
        )


# ============================================================
# EMPTY SOURCE VALIDATION
# ============================================================

def validate_empty_source(
    df: pd.DataFrame,
    require_records: bool = False,
) -> None:

    if require_records and df.empty:
        raise ValueError(
            "Empty source validation failed: "
            "Records are required but the "
            "source returned no records."
        )


# ============================================================
# PAINT ANALYSIS VALIDATION
# ============================================================

def validate_analysis_identifiers(
    df: pd.DataFrame,
) -> None:

    validate_data_completeness(
        df,
        required_columns=["id"],
    )

    validate_data_consistency(
        df,
        identifier_column="id",
    )


# ============================================================
# SUPABASE DATA EXTRACTION
# ============================================================

def extract_specific_columns(
    table_name: str,
    columns: list[str],
    *,
    require_records: bool = False,
    raise_on_error: bool = False,
) -> pd.DataFrame:

    """
    Extract selected Supabase records and apply documented
    extraction validation rules.

    Empty results are allowed unless require_records=True.

    Failed extraction returns an empty DataFrame by default.
    If raise_on_error=True, an exception is raised after
    the extraction report is generated.
    """

    run_id = generate_run_id()
    start_time = time.time()
    start_ts = get_timestamp()

    status = "FAILED"
    records_read = 0
    records_extracted = 0
    records_rejected = 0

    data_range = "N/A"
    validation_result = "FAIL"
    error_msg = "N/A"

    df = pd.DataFrame(columns=columns)

    try:

        # ----------------------------------------------------
        # Retrieve records from the source
        # ----------------------------------------------------

        supabase = get_supabase_client()

        column_string = ",".join(columns)

        response = (
            supabase.table(table_name)
            .select(column_string)
            .execute()
        )

        raw_records = response.data

        if not isinstance(raw_records, list):
            raise ValueError(
                "Invalid source response: "
                "Expected a list of records."
            )

        records_read = len(raw_records)

        # ----------------------------------------------------
        # Validate the actual source schema
        # ----------------------------------------------------

        for record in raw_records:

            if not isinstance(record, dict):
                raise ValueError(
                    "Invalid source record structure."
                )

            missing_columns = [
                column
                for column in columns
                if column not in record
            ]

            if missing_columns:
                raise ValueError(
                    "Source schema validation failed: "
                    f"Missing column(s): {missing_columns}"
                )

        # ----------------------------------------------------
        # Convert records into a DataFrame
        # ----------------------------------------------------

        df = pd.DataFrame(
            raw_records,
            columns=columns,
        )

        # ----------------------------------------------------
        # Validate empty source
        # ----------------------------------------------------

        validate_empty_source(
            df,
            require_records=require_records,
        )

        if df.empty:

            status = "SUCCESS"
            validation_result = "PASS (empty result)"

        else:

            # ------------------------------------------------
            # Validate Paint Analysis identifiers
            # ------------------------------------------------

            if table_name == "paint_analysis_history":
                validate_analysis_identifiers(df)

            records_extracted = len(df)

            status = "SUCCESS"
            validation_result = "PASS"

        # ----------------------------------------------------
        # Determine extraction data range
        # ----------------------------------------------------

        if "analysis_date" in df.columns and not df.empty:

            try:

                dates = pd.to_datetime(
                    df["analysis_date"],
                    errors="coerce",
                ).dropna()

                if not dates.empty:
                    data_range = (
                        f"{dates.min().date()} to "
                        f"{dates.max().date()}"
                    )

                else:
                    data_range = "No valid analysis dates"

            except (ValueError, TypeError):
                data_range = "Full available table"

        else:
            data_range = "Full available table"

    except Exception as error:

        status = "FAILED"
        validation_result = "FAIL"

        error_msg = (
            f"{type(error).__name__}: {error}"
        )

        records_rejected = records_read
        records_extracted = 0

        # Reject the failed batch.
        df = pd.DataFrame(columns=columns)

    # --------------------------------------------------------
    # Generate extraction report
    # --------------------------------------------------------

    end_ts = get_timestamp()

    duration = (
        f"{time.time() - start_time:.3f}s"
    )

    log_extraction_report({
        "pipeline_run_id": run_id,
        "source_name": table_name,
        "start_timestamp": start_ts,
        "end_timestamp": end_ts,
        "status": status,
        "records_read": records_read,
        "records_extracted": records_extracted,
        "records_rejected": records_rejected,
        "data_range": data_range,
        "validation_result": validation_result,
        "error": error_msg,
        "duration": duration,
    })

    if status == "FAILED" and raise_on_error:
        raise ValueError(error_msg)

    return df


# ============================================================
# RUN EXTRACTION DIRECTLY
# ============================================================

if __name__ == "__main__":

    print(
        f"[{get_timestamp()}] "
        "STARTING SUPABASE EXTRACTION"
    )

    TARGET_TABLE = "paint_analysis_history"

    TARGET_COLUMNS = [
        "id",
        "color_hex",
        "rgb",
        "paint_components",
        "analysis_date",
    ]

    df = extract_specific_columns(
        TARGET_TABLE,
        TARGET_COLUMNS,
        raise_on_error=True,
    )

