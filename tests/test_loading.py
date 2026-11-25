
# Author: Villalobos Lawrence C.
# Date: 2026-11-25
# Test Suite: Loading
# Description: Automated unit tests for data preparation,
# database insertion, updates, integrity validation,
# connection failures, and transaction rollback.

import importlib.util
import json
import logging
import shutil
import sqlite3
import sys

from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

RUN_ID = "MOCK-LOAD-001"
TRANSFORMATION_ID = "MOCK-TR-001"
BATCH_ID = "MOCK-BATCH-001"


# ============================================================
# ISOLATED LOADING MODULE
# ============================================================

@pytest.fixture
def loading_module(tmp_path, monkeypatch):

    source = ROOT / "pipeline/CSV/load.py"

    destination = tmp_path / "pipeline/CSV/load.py"

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(source, destination)

    spec = importlib.util.spec_from_file_location(
        "isolated_loading",
        destination,
    )

    module = importlib.util.module_from_spec(spec)

    isolated_logger = logging.Logger("test.loading")

    monkeypatch.setattr(
        sys,
        "dont_write_bytecode",
        True,
    )

    try:

        with patch.object(
            logging,
            "getLogger",
            return_value=isolated_logger,
        ):

            spec.loader.exec_module(module)

        # Suppress console logs during unit tests.

        for handler in isolated_logger.handlers[:]:

            if (
                isinstance(handler, logging.StreamHandler)
                and not isinstance(handler, logging.FileHandler)
            ):

                handler.close()
                isolated_logger.removeHandler(handler)

        # Prohibit actual database connections.

        sqlite_mock = Mock(wraps=sqlite3)

        sqlite_mock.connect.side_effect = AssertionError(
            "Real database connections are prohibited."
        )

        monkeypatch.setattr(
            module,
            "sqlite3",
            sqlite_mock,
        )

        yield module

    finally:

        for handler in isolated_logger.handlers[:]:

            handler.close()
            isolated_logger.removeHandler(handler)


# ============================================================
# MOCK TRANSFORMED DATASETS
# ============================================================

@pytest.fixture
def incoming_data():

    return {

        "product_table": pd.DataFrame([
            {
                "product_id": "PROD-001",
                "product_name": "White Paint GALLON",
                "unit_purchase_price": "350.00",
                "estimated_price_php": "450.00",
                "stocks": "25",
                "category": "Paint",
                "brand": "Sample Brand",
            }
        ]),

        "sales_table": pd.DataFrame([
            {
                "sales_id": "SALE-001",
                "brand": "Sample Brand",
                "product": "White Paint GALLON",
                "category": "Paint",
                "sales_date": "2026-10-15",
                "quantity": "5",
                "unit_sold": "2250.00",
                "season": "Rainy",
            }
        ]),

        "paint_analysis_table": pd.DataFrame([
            {
                "id": "PA-001",
                "color": "#FFFFFF",
                "rgb": "[255, 255, 255]",
                "paint_components": '{"white": 100}',
                "analysis_date": "2026-10-15T00:00:00",
            }
        ]),
    }


# ============================================================
# MOCK HANDOVER METADATA
# ============================================================

@pytest.fixture
def handover_metadata():

    return {
        "run_id": TRANSFORMATION_ID,
        "batch_id": BATCH_ID,
        "status": "SUCCESS",
        "batch_window": "Mock testing batch",

        "expected_counts": {
            "product_table": 1,
            "sales_table": 1,
            "paint_analysis_table": 1,
        },
    }


# ============================================================
# MOCK DATABASE HELPERS
# ============================================================

def make_cursor(one=None, rows=None):

    cursor = Mock()

    cursor.fetchone.return_value = one

    cursor.fetchall.return_value = (
        rows if rows is not None else []
    )

    return cursor


def sql_operations(connection):

    return [
        (
            " ".join(call.args[0].upper().split()),
            call.args[1] if len(call.args) > 1 else None,
        )

        for call in connection.execute.call_args_list
    ]


def business_inserts(connection):

    return [
        (sql, params)

        for sql, params in sql_operations(connection)

        if sql.startswith((
            "INSERT INTO PRODUCT_TABLE",
            "INSERT INTO SALES_TABLE",
            "INSERT INTO PAINT_ANALYSIS_TABLE",
        ))
    ]


def make_database(
    module,
    existing_product=None,
    existing_paint=None,
    product_insert_failure=False,
    orphan_sales=0,
    duplicate_keys=0,
    sales_total=2250.00,
    product_count=1,
):

    connection = Mock()

    connection.in_transaction = False

    connection.iterdump.return_value = iter([])

    def execute(sql, parameters=()):

        query = " ".join(sql.upper().split())

        # Target schema validation.

        if query.startswith("PRAGMA TABLE_INFO"):

            table = query.split("(")[1].split(")")[0].lower()

            columns = module.EXPECTED_SCHEMAS[table]

            return make_cursor(
                rows=[
                    (index, column)
                    for index, column in enumerate(columns)
                ]
            )

        # Existing batch detection.

        if (
            query.startswith("SELECT COUNT(*)")
            and "FROM LOAD_LOG" in query
        ):

            return make_cursor(one=(0,))

        # Existing product lookup.

        if query.startswith(
            "SELECT PRODUCT_KEY FROM PRODUCT_TABLE"
        ):

            return make_cursor(one=existing_product)

        # Sales foreign-key lookup.

        if query.startswith(
            "SELECT PRODUCT_NAME, MIN(PRODUCT_KEY)"
        ):

            return make_cursor(
                rows=[("White Paint GALLON", 101)]
            )

        # Existing paint analysis lookup.

        if query.startswith(
            "SELECT ANALYSIS_KEY FROM PAINT_ANALYSIS_TABLE"
        ):

            return make_cursor(one=existing_paint)

        # Simulate database insertion failure.

        if query.startswith("INSERT INTO PRODUCT_TABLE"):

            if product_insert_failure:

                raise sqlite3.IntegrityError(
                    "Mock product insertion failure"
                )

            return make_cursor()

        # Primary-key validation.

        if "COUNT(DISTINCT" in query:

            return make_cursor(
                one=(duplicate_keys, 0, 0)
            )

        # Foreign-key validation.

        if "LEFT JOIN PRODUCT_TABLE" in query:

            return make_cursor(one=(orphan_sales,))

        # Mandatory value validation.

        if (
            query.startswith("SELECT COUNT(*) FROM")
            and "IS NULL" in query
        ):

            return make_cursor(one=(0,))

        # Optional attribute completeness.

        if (
            "SUM(CASE WHEN CATEGORY IS NULL" in query
        ):

            return make_cursor(one=(1, 0, 0))

        # Seasonal sales reconciliation.

        if "LOWER(TRIM(SEASON))" in query:

            if "'DRY'" in query:

                return make_cursor(one=(0, 0.0, 0))

            return make_cursor(
                one=(1, sales_total, 5)
            )

        # Total sales and quantity reconciliation.

        if "SUM(UNIT_SOLD)" in query:

            return make_cursor(
                one=(sales_total, 5)
            )

        # Product price reconciliation.

        if "SUM(ESTIMATED_PRICE_PHP)" in query:

            return make_cursor(one=(450.00,))

        # Target batch record counts.

        if (
            query.startswith("SELECT COUNT(*)")
            and "WHERE BATCH_ID" in query
        ):

            if "FROM PRODUCT_TABLE" in query:

                return make_cursor(
                    one=(product_count,)
                )

            return make_cursor(one=(1,))

        return make_cursor()

    connection.execute.side_effect = execute

    return connection


# ============================================================
# MOCK LOAD RUN PREPARATION
# ============================================================

def prepare_load_run(
    module,
    incoming_data,
    handover_metadata,
    connection,
    monkeypatch,
):

    # All generated files are isolated in tmp_path.

    module.TRANSFORMATION_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Create synthetic placeholder files.
    # CSV reading itself remains mocked.

    for path in module.INPUT_FILES.values():

        path.touch()

    def mock_read_csv(path, *args, **kwargs):

        for table, expected_path in module.INPUT_FILES.items():

            if Path(path) == expected_path:

                return incoming_data[table].copy()

        raise AssertionError(
            f"Unexpected file access: {path}"
        )

    monkeypatch.setattr(
        module.pd,
        "read_csv",
        mock_read_csv,
    )

    monkeypatch.setattr(
        module,
        "read_transformation_handover",
        Mock(return_value=handover_metadata),
    )

    monkeypatch.setattr(
        module,
        "backup_target_database",
        Mock(return_value=None),
    )

    monkeypatch.setattr(
        module,
        "deduplicate_log_for_batch",
        Mock(),
    )

    monkeypatch.setattr(
        module,
        "initialize_target_database",
        Mock(),
    )

    # Pre-load validation has its own independent test.

    monkeypatch.setattr(
        module,
        "run_pre_load_checks",
        Mock(return_value=("PASS", [])),
    )

    module.sqlite3.connect.side_effect = None

    module.sqlite3.connect.return_value = connection


# ============================================================
# LD-01: DATA PREPARATION BEFORE LOADING
# ============================================================

def test_data_preparation_before_loading(
    loading_module,
    incoming_data,
    handover_metadata,
):

    module = loading_module

    connection = make_database(module)

    mock_disk = Mock()

    mock_disk.free = module.MIN_FREE_DISK_BYTES

    # Store synthetic handover metadata in temporary directory.

    module.HANDOVER_METADATA_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    module.HANDOVER_METADATA_FILE.write_text(
        json.dumps(handover_metadata),
        encoding="utf-8",
    )

    metadata = module.read_transformation_handover()

    # Run the actual pre-load validation function.

    with patch.object(
        module.shutil,
        "disk_usage",
        return_value=mock_disk,
    ):

        result, checks = module.run_pre_load_checks(
            connection,
            metadata,
            incoming_data,
        )

    assert metadata["batch_id"] == BATCH_ID

    assert metadata["status"] == "SUCCESS"

    assert metadata["expected_counts"] == {
        "product_table": 1,
        "sales_table": 1,
        "paint_analysis_table": 1,
    }

    assert result == "PASS"

    assert len(checks) == 6

    assert all(
        check["result"] == "PASS"
        for check in checks
    )

    assert module.clean_val("  Paint  ") == "Paint"

    assert module.clean_val("   ") is None

    assert module.to_float_or_none(
        "350.00"
    ) == 350.0

    assert module.to_int_or_none("25") == 25

    assert business_inserts(connection) == []


# ============================================================
# LD-02: EXISTING RECORD HANDLING
# ============================================================

def test_existing_record_handling(
    loading_module,
    incoming_data,
):

    module = loading_module

    connection = make_database(
        module,
        existing_product=(101,),
        existing_paint=(501,),
    )

    rejected = []

    products = module.load_products_table(
        connection,
        incoming_data["product_table"],
        RUN_ID,
        TRANSFORMATION_ID,
        BATCH_ID,
        rejected,
    )

    paint = module.load_paint_analysis_table(
        connection,
        incoming_data["paint_analysis_table"],
        RUN_ID,
        TRANSFORMATION_ID,
        BATCH_ID,
        rejected,
    )

    assert products["records_updated"] == 1

    assert products["records_inserted"] == 0

    assert paint["records_updated"] == 1

    assert paint["records_inserted"] == 0

    assert rejected == []

    operations = sql_operations(connection)

    product_updates = [
        params

        for sql, params in operations

        if sql.startswith("UPDATE PRODUCT_TABLE")
    ]

    paint_updates = [
        params

        for sql, params in operations

        if sql.startswith("UPDATE PAINT_ANALYSIS_TABLE")
    ]

    assert len(product_updates) == 1

    assert len(paint_updates) == 1

    assert product_updates[0][-1] == 101

    assert paint_updates[0][-1] == 501

    assert business_inserts(connection) == []


# ============================================================
# LD-03: NEW RECORD INSERTION
# ============================================================

def test_new_record_insertion(
    loading_module,
    incoming_data,
):

    module = loading_module

    connection = make_database(module)

    rejected = []

    stats = module.load_products_table(
        connection,
        incoming_data["product_table"],
        RUN_ID,
        TRANSFORMATION_ID,
        BATCH_ID,
        rejected,
    )

    assert stats["records_received"] == 1

    assert stats["records_inserted"] == 1

    assert stats["records_updated"] == 0

    assert stats["records_rejected"] == 0

    inserts = business_inserts(connection)

    assert len(inserts) == 1

    query, parameters = inserts[0]

    assert query.startswith(
        "INSERT INTO PRODUCT_TABLE"
    )

    assert parameters[0] == "PROD-001"

    assert parameters[1] == "White Paint GALLON"

    assert parameters[2] == 350.0

    assert parameters[3] == 450.0

    assert parameters[8] == BATCH_ID

    assert rejected == []


# ============================================================
# LD-04: DATABASE CONNECTION FAILURE
# ============================================================

def test_database_connection_failure(
    loading_module,
    incoming_data,
    handover_metadata,
    monkeypatch,
):

    module = loading_module

    connection = make_database(module)

    prepare_load_run(
        module,
        incoming_data,
        handover_metadata,
        connection,
        monkeypatch,
    )

    module.sqlite3.connect.side_effect = (
        sqlite3.OperationalError(
            "Mock database connection unavailable"
        )
    )

    with patch.object(
        module,
        "load_products_table",
    ) as product_loader, patch.object(
        module,
        "load_sales_table",
    ) as sales_loader, patch.object(
        module,
        "load_paint_analysis_table",
    ) as paint_loader:

        try:

            result = module.run_load()

        finally:

            product_loader.assert_not_called()

            sales_loader.assert_not_called()

            paint_loader.assert_not_called()

            connection.execute.assert_not_called()

    # Expected: controlled failure instead of uncaught exception.

    assert result == 1


# ============================================================
# LD-05: DATA INTEGRITY CONSTRAINTS
# ============================================================

def test_data_integrity_constraints(
    loading_module,
    incoming_data,
):

    module = loading_module

    connection = make_database(module)

    rejected = []

    invalid_products = incoming_data[
        "product_table"
    ].copy()

    invalid_products.loc[
        0, "unit_purchase_price"
    ] = "-100.00"

    product_stats = module.load_products_table(
        connection,
        invalid_products,
        RUN_ID,
        TRANSFORMATION_ID,
        BATCH_ID,
        rejected,
    )

    invalid_sales = incoming_data[
        "sales_table"
    ].copy()

    invalid_sales.loc[
        0, "product"
    ] = "Nonexistent Product"

    sales_stats = module.load_sales_table(
        connection,
        invalid_sales,
        RUN_ID,
        TRANSFORMATION_ID,
        BATCH_ID,
        rejected,
    )

    assert product_stats["records_rejected"] == 1

    assert sales_stats["records_rejected"] == 1

    assert product_stats["records_inserted"] == 0

    assert sales_stats["records_inserted"] == 0

    assert len(rejected) == 2

    assert "negative price" in (
        rejected[0]["rejection_reason"].lower()
    )

    assert "foreign key violation" in (
        rejected[1]["rejection_reason"].lower()
    )

    assert business_inserts(connection) == []


# ============================================================
# LD-06: SUCCESSFUL LOAD VALIDATION
# ============================================================

def test_successful_load_validation(
    loading_module,
    incoming_data,
):

    module = loading_module

    connection = make_database(module)

    table_stats = {

        table: {
            "records_received": 1,
            "records_inserted": 1,
            "records_updated": 0,
            "records_rejected": 0,
        }

        for table in incoming_data
    }

    result, checks = module.run_post_load_checks(
        connection,
        BATCH_ID,
        incoming_data,
        table_stats,
    )

    assert result == "PASS"

    assert len(checks) == 7

    assert all(
        check["result"] == "PASS"
        for check in checks
    )

    check_names = {
        check["check_name"]
        for check in checks
    }

    assert "Record reconciliation" in check_names

    assert "Primary key uniqueness" in check_names

    assert "Referential integrity" in check_names

    assert "Required columns not null" in check_names

    assert "Amount and quantity reconciliation" in check_names


# ============================================================
# LD-07: INSERTION FAILURE AND ROLLBACK
# ============================================================

def test_insertion_failure_and_rollback(
    loading_module,
    incoming_data,
    handover_metadata,
    monkeypatch,
):

    module = loading_module

    connection = make_database(
        module,
        product_insert_failure=True,
        product_count=0,
    )

    prepare_load_run(
        module,
        incoming_data,
        handover_metadata,
        connection,
        monkeypatch,
    )

    result = module.run_load()

    assert result == 1

    connection.rollback.assert_called_once()

    connection.close.assert_called_once()

    summary = json.loads(
        module.LOAD_SUMMARY_JSON.read_text(
            encoding="utf-8"
        )
    )

    assert summary["status"] == "FAILED"

    assert summary["acceptance_decision"] == "REJECTED"

    assert summary["post_load_result"] == "FAIL"

    assert summary["error_code"] == (
        "POST_LOAD_VALIDATION_FAILED"
    )

    assert "Record reconciliation" in (
        summary["error_message"]
    )

    # Verify the original insertion failure was recorded.

    import csv

    with open(
        module.LOAD_REJECTED_FILE,
        encoding="utf-8-sig",
        newline="",
    ) as rejected_file:

        rejected_rows = list(
            csv.DictReader(rejected_file)
        )

    assert len(rejected_rows) == 1

    assert rejected_rows[0]["error_code"] == (
        "LOAD_PRODUCT_REJECT"
    )

    assert "Mock product insertion failure" in (
        rejected_rows[0]["rejection_reason"]
    )

    assert summary["table_metrics"][
        "product_table"
    ]["records_rejected"] == 1

    # Verify rollback occurred before any commit.
    # A later commit is allowed for failure audit logs.

    calls = connection.mock_calls

    rollback_index = next(
        index

        for index, call in enumerate(calls)

        if call[0] == "rollback"
    )

    commit_indices = [
        index

        for index, call in enumerate(calls)

        if call[0] == "commit"
    ]

    assert all(
        index > rollback_index
        for index in commit_indices
    )


# ============================================================
# LD-08: SUCCESSFUL MOCKED DATABASE INSERTION
# ============================================================

def test_successful_mocked_database_insertion(
    loading_module,
    incoming_data,
    handover_metadata,
    monkeypatch,
):

    module = loading_module

    connection = make_database(module)

    prepare_load_run(
        module,
        incoming_data,
        handover_metadata,
        connection,
        monkeypatch,
    )

    result = module.run_load()

    assert result == 0

    module.sqlite3.connect.assert_called_once()

    connection.rollback.assert_not_called()

    assert connection.commit.call_count >= 1

    connection.close.assert_called_once()

    inserts = business_inserts(connection)

    assert len(inserts) == 3

    # Verify parent-before-child loading order.

    assert inserts[0][0].startswith(
        "INSERT INTO PRODUCT_TABLE"
    )

    assert inserts[1][0].startswith(
        "INSERT INTO SALES_TABLE"
    )

    assert inserts[2][0].startswith(
        "INSERT INTO PAINT_ANALYSIS_TABLE"
    )

    assert inserts[1][1][1] == 101

    operations = sql_operations(connection)

    assert any(
        query.startswith("BEGIN IMMEDIATE")
        for query, _ in operations
    )

    assert any(
        query.startswith("DELETE FROM SALES_TABLE")
        and params == (BATCH_ID,)

        for query, params in operations
    )

    summary = json.loads(
        module.LOAD_SUMMARY_JSON.read_text(
            encoding="utf-8"
        )
    )

    assert summary["status"] == "SUCCESS"

    assert summary["acceptance_decision"] == "APPROVED"

    assert summary["pre_load_result"] == "PASS"

    assert summary["post_load_result"] == "PASS"

    for stats in summary["table_metrics"].values():

        assert stats["records_received"] == 1

        assert stats["records_inserted"] == 1

        assert stats["records_rejected"] == 0




# ============================================================
# ADDITIONAL TESTS: AVAILABLE STORAGE BOUNDARY
# ============================================================

@pytest.mark.parametrize(
    "byte_difference,expected_result",
    [
        (-1, "FAIL"),
        (0, "PASS"),
        (1, "PASS"),
    ],
    ids=[
        "below-minimum-storage",
        "exact-minimum-storage",
        "above-minimum-storage",
    ],
)
def test_storage_space_boundary(
    loading_module,
    incoming_data,
    handover_metadata,
    byte_difference,
    expected_result,
):

    module = loading_module

    connection = make_database(module)

    mock_disk = Mock()

    mock_disk.free = (
        module.MIN_FREE_DISK_BYTES
        + byte_difference
    )

    with patch.object(
        module.shutil,
        "disk_usage",
        return_value=mock_disk,
    ):

        result, checks = module.run_pre_load_checks(
            connection,
            handover_metadata,
            incoming_data,
        )

    storage_check = next(
        check

        for check in checks

        if check["check_name"] == (
            "Storage space availability"
        )
    )

    assert storage_check["result"] == (
        expected_result
    )

    assert result == expected_result

    assert business_inserts(connection) == []


# ============================================================
# ADDITIONAL TESTS: OPTIONAL ATTRIBUTE NULL RATE
# ============================================================

@pytest.mark.parametrize(
    "field_name",
    ["category", "brand"],
)
@pytest.mark.parametrize(
    "missing_records,expected_result",
    [
        (4, "PASS"),
        (5, "PASS"),
        (6, "WARNING"),
    ],
    ids=[
        "below-five-percent",
        "exactly-five-percent",
        "above-five-percent",
    ],
)
def test_optional_attribute_null_rate_boundary(
    loading_module,
    incoming_data,
    field_name,
    missing_records,
    expected_result,
):

    module = loading_module

    records = []

    # Generate 100 synthetic product records.

    for index in range(100):

        record = incoming_data[
            "product_table"
        ].iloc[0].to_dict()

        record["product_id"] = (
            f"PROD-{index + 1:03d}"
        )

        if index > 0:

            record["product_name"] = (
                f"Mock Paint {index + 1}"
            )

        if index < missing_records:

            record[field_name] = None

        records.append(record)

    incoming_data["product_table"] = pd.DataFrame(
        records
    )

    connection = make_database(
        module,
        product_count=100,
    )

    original_execute = (
        connection.execute.side_effect
    )

    null_category = (
        missing_records
        if field_name == "category"
        else 0
    )

    null_brand = (
        missing_records
        if field_name == "brand"
        else 0
    )

    def execute(sql, parameters=()):

        query = " ".join(
            sql.upper().split()
        )

        if (
            "SUM(CASE WHEN CATEGORY IS NULL"
            in query
        ):

            return make_cursor(
                one=(
                    100,
                    null_category,
                    null_brand,
                )
            )

        if "SUM(ESTIMATED_PRICE_PHP)" in query:

            return make_cursor(
                one=(45000.00,)
            )

        return original_execute(
            sql,
            parameters,
        )

    connection.execute.side_effect = execute

    table_stats = {

        table: {
            "records_received": len(frame),
            "records_inserted": len(frame),
            "records_updated": 0,
            "records_rejected": 0,
        }

        for table, frame in incoming_data.items()
    }

    result, checks = module.run_post_load_checks(
        connection,
        BATCH_ID,
        incoming_data,
        table_stats,
    )

    null_check = next(
        check

        for check in checks

        if check["check_name"] == (
            "Optional attribute null rate check"
        )
    )

    assert null_check["severity"] == (
        "Non-critical"
    )

    assert null_check["result"] == (
        expected_result
    )

    assert result == expected_result

    assert all(
        check["result"] == "PASS"

        for check in checks

        if check["severity"] == "Critical"
    )


# ============================================================
# ADDITIONAL TESTS: CRITICAL INTEGRITY VALIDATION
# ============================================================

@pytest.mark.parametrize(
    "duplicate_keys,orphan_sales,failed_check",
    [
        (1, 0, "Primary key uniqueness"),
        (0, 1, "Referential integrity"),
    ],
    ids=[
        "duplicate-primary-key",
        "orphan-sales-record",
    ],
)
def test_critical_integrity_validation(
    loading_module,
    incoming_data,
    duplicate_keys,
    orphan_sales,
    failed_check,
):

    module = loading_module

    connection = make_database(
        module,
        duplicate_keys=duplicate_keys,
        orphan_sales=orphan_sales,
    )

    table_stats = {

        table: {
            "records_received": len(frame),
            "records_inserted": len(frame),
            "records_updated": 0,
            "records_rejected": 0,
        }

        for table, frame in incoming_data.items()
    }

    result, checks = module.run_post_load_checks(
        connection,
        BATCH_ID,
        incoming_data,
        table_stats,
    )

    integrity_check = next(
        check

        for check in checks

        if check["check_name"] == failed_check
    )

    assert integrity_check["severity"] == (
        "Critical"
    )

    assert integrity_check["result"] == "FAIL"

    assert result == "FAIL"
