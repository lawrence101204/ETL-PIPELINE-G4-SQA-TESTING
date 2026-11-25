
# Author: Villalobos Lawrence C.
# Date: 2026-11-25
# Test Suite: Extraction
# Description: Automated unit tests for data retrieval,
# completeness, consistency, identifier validation,
# empty sources, and extraction error handling.

import importlib.util
import io
import shutil

from contextlib import redirect_stdout, redirect_stderr
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ============================================================
# TEST CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

COLUMNS = [
    "id",
    "color_hex",
    "rgb",
    "paint_components",
    "analysis_date",
]


# ============================================================
# MOCK TEST DATA
# ============================================================

@pytest.fixture
def valid_records():

    return [
        {
            "id": "PA-001",
            "color_hex": "#FFFFFF",
            "rgb": "[255, 255, 255]",
            "paint_components": '{"white": 100}',
            "analysis_date": "2026-10-01",
        },
        {
            "id": "PA-002",
            "color_hex": "#0000FF",
            "rgb": "[0, 0, 255]",
            "paint_components": '{"blue": 100}',
            "analysis_date": "2026-10-02",
        },
    ]


# ============================================================
# ISOLATED MODULE LOADER
# ============================================================

@pytest.fixture
def load_isolated_module(tmp_path):

    loaded_modules = []

    def load(relative_path):

        source = ROOT / relative_path
        destination = tmp_path / relative_path

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            source,
            destination,
        )

        spec = importlib.util.spec_from_file_location(
            destination.stem,
            destination,
        )

        module = importlib.util.module_from_spec(spec)

        with (
            patch("atexit.register"),
            patch("dotenv.load_dotenv"),
            patch(
                "supabase.create_client",
                side_effect=AssertionError(
                    "Real Supabase access is prohibited."
                ),
            ),
            redirect_stdout(io.StringIO()),
            redirect_stderr(io.StringIO()),
        ):

            spec.loader.exec_module(module)

        loaded_modules.append(module)

        module.log_extraction_report = MagicMock()

        return module

    yield load

    for module in loaded_modules:

        if hasattr(module, "log_file"):
            module.log_file.close()


@pytest.fixture
def csv_module(load_isolated_module):

    return load_isolated_module(
        "pipeline/CSV/csv_extraction.py"
    )


@pytest.fixture
def analysis_module(load_isolated_module):

    return load_isolated_module(
        "pipeline/analysis_extraction.py"
    )


# ============================================================
# MOCK SUPABASE EXTRACTION
# ============================================================

def mock_analysis_extraction(
    module,
    records,
    require_records=True,
):

    client = MagicMock()

    client.table.return_value \
        .select.return_value \
        .execute.return_value = SimpleNamespace(
            data=records
        )

    with patch.object(
        module,
        "get_supabase_client",
        return_value=client,
    ):

        result = module.extract_specific_columns(
            "paint_analysis_history",
            COLUMNS,
            require_records=require_records,
        )

    client.table.assert_called_once_with(
        "paint_analysis_history"
    )

    client.table.return_value.select \
        .assert_called_once_with(
            ",".join(COLUMNS)
        )

    client.table.return_value \
        .select.return_value \
        .execute.assert_called_once()

    report = (
        module.log_extraction_report
        .call_args.args[0]
    )

    return result, report


# ============================================================
# EX-01: SUCCESSFUL DATA RETRIEVAL
# ============================================================

def test_successful_data_retrieval(csv_module):

    # Arrange

    expected = pd.DataFrame({
        "Product ID": ["P001", "P002"],
        "Product Name": [
            "White Paint",
            "Blue Paint",
        ],
        "Stocks": [50, 25],
    })

    source_data = expected.copy(deep=True)

    # Act

    with (
        patch.object(
            Path,
            "exists",
            return_value=True,
        ),
        patch.object(
            csv_module.pd,
            "read_csv",
            return_value=source_data,
        ) as mock_read,
    ):

        actual = csv_module.extract_csv(
            "mock_products.csv"
        )

    # Assert

    mock_read.assert_called_once()

    pd.testing.assert_frame_equal(
        actual,
        expected,
    )

    pd.testing.assert_frame_equal(
        source_data,
        expected,
    )

    report = (
        csv_module.log_extraction_report
        .call_args.args[0]
    )

    assert report["status"] == "SUCCESS"
    assert report["records_extracted"] == 2


# ============================================================
# EX-02: DATA COMPLETENESS VALIDATION
# ============================================================

def test_data_completeness_validation(
    analysis_module,
    valid_records,
):

    # Arrange

    for record in valid_records:
        record["id"] = None

    # Act

    result, report = mock_analysis_extraction(
        analysis_module,
        valid_records,
    )

    # Assert

    assert result.empty
    assert report["status"] == "FAILED"

    assert "completeness" in (
        report["error"].lower()
    )

    assert report["records_rejected"] == 2
    assert report["records_extracted"] == 0


# ============================================================
# EX-03: DATA CONSISTENCY VALIDATION
# ============================================================

def test_data_consistency_validation(
    analysis_module,
    valid_records,
):

    # Arrange

    valid_records[0]["id"] = date(
        2026,
        10,
        1,
    )

    # Act

    result, report = mock_analysis_extraction(
        analysis_module,
        valid_records,
    )

    # Assert

    assert result.empty
    assert report["status"] == "FAILED"

    assert "consistency" in (
        report["error"].lower()
    )

    assert report["records_extracted"] == 0


# ============================================================
# EX-04: SUCCESSFUL EXTRACTION WITH VALID DATA
# ============================================================

def test_successful_extraction_with_valid_data(
    analysis_module,
    valid_records,
):

    # Arrange

    expected = pd.DataFrame(
        valid_records,
        columns=COLUMNS,
    )

    # Act

    actual, report = mock_analysis_extraction(
        analysis_module,
        valid_records,
    )

    # Assert

    pd.testing.assert_frame_equal(
        actual,
        expected,
    )

    assert report["status"] == "SUCCESS"
    assert report["validation_result"] == "PASS"
    assert report["records_read"] == 2
    assert report["records_extracted"] == 2
    assert report["records_rejected"] == 0
    assert report["error"] == "N/A"


# ============================================================
# EX-05: EMPTY SOURCE DATA VALIDATION
# ============================================================

def test_empty_required_source_data(
    analysis_module,
):

    # Arrange

    records = []

    # Act

    result, report = mock_analysis_extraction(
        analysis_module,
        records,
        require_records=True,
    )

    # Assert

    assert result.empty
    assert report["status"] == "FAILED"

    assert "empty source" in (
        report["error"].lower()
    )

    assert report["records_extracted"] == 0


# ============================================================
# ADDITIONAL TEST 01:
# REQUIRED IDENTIFIER COMPLETENESS BOUNDARY
# ============================================================

@pytest.mark.parametrize(
    "missing_count, expected_status",
    [
        (0, "SUCCESS"),
        (1, "FAILED"),
        (2, "FAILED"),
    ],
    ids=[
        "zero-missing",
        "one-missing",
        "all-missing",
    ],
)
def test_completeness_boundary(
    analysis_module,
    valid_records,
    missing_count,
    expected_status,
):

    # Arrange

    for index in range(missing_count):
        valid_records[index]["id"] = None

    # Act

    result, report = mock_analysis_extraction(
        analysis_module,
        valid_records,
    )

    # Assert

    assert report["status"] == expected_status

    if missing_count == 0:

        assert len(result) == 2

    else:

        assert result.empty

        assert "completeness" in (
            report["error"].lower()
        )


# ============================================================
# ADDITIONAL TEST 02: BLANK IDENTIFIERS
# ============================================================

@pytest.mark.parametrize(
    "invalid_id",
    ["", "   ", None],
    ids=[
        "empty-string",
        "whitespace",
        "null",
    ],
)
def test_blank_identifier(
    analysis_module,
    valid_records,
    invalid_id,
):

    # Arrange

    valid_records[0]["id"] = invalid_id

    # Act

    result, report = mock_analysis_extraction(
        analysis_module,
        valid_records,
    )

    # Assert

    assert result.empty
    assert report["status"] == "FAILED"

    assert "completeness" in (
        report["error"].lower()
    )


# ============================================================
# ADDITIONAL TEST 03: INVALID IDENTIFIER FORMATS
# ============================================================

@pytest.mark.parametrize(
    "invalid_id",
    [
        12345,
        date(2026, 10, 1),
        "2026-10-01",
    ],
    ids=[
        "numeric-id",
        "date-object",
        "date-string",
    ],
)
def test_invalid_identifier_format(
    analysis_module,
    valid_records,
    invalid_id,
):

    # Arrange

    valid_records[0]["id"] = invalid_id

    # Act

    result, report = mock_analysis_extraction(
        analysis_module,
        valid_records,
    )

    # Assert

    assert result.empty
    assert report["status"] == "FAILED"

    assert "consistency" in (
        report["error"].lower()
    )


# ============================================================
# ADDITIONAL TEST 04: DUPLICATE IDENTIFIERS
# ============================================================

def test_duplicate_identifiers(
    analysis_module,
    valid_records,
):

    # Arrange

    valid_records[1]["id"] = (
        valid_records[0]["id"]
    )

    # Act

    result, report = mock_analysis_extraction(
        analysis_module,
        valid_records,
    )

    # Assert

    assert result.empty
    assert report["status"] == "FAILED"

    assert "duplicate" in (
        report["error"].lower()
    )


# ============================================================
# ADDITIONAL TEST 05: OPTIONAL EMPTY SOURCE
# ============================================================

def test_empty_optional_source_data(
    analysis_module,
):

    # Arrange

    records = []

    # Act

    result, report = mock_analysis_extraction(
        analysis_module,
        records,
        require_records=False,
    )

    # Assert

    assert result.empty
    assert report["status"] == "SUCCESS"

    assert report["validation_result"] == (
        "PASS (empty result)"
    )


# ============================================================
# ADDITIONAL TEST 06: MISSING SOURCE COLUMN
# ============================================================

def test_missing_source_column(
    analysis_module,
    valid_records,
):

    # Arrange

    del valid_records[0]["id"]

    # Act

    result, report = mock_analysis_extraction(
        analysis_module,
        valid_records,
    )

    # Assert

    assert result.empty
    assert report["status"] == "FAILED"

    assert "missing column" in (
        report["error"].lower()
    )


# ============================================================
# ADDITIONAL TEST 07: SOURCE CONNECTION FAILURE
# ============================================================

def test_source_connection_failure(
    analysis_module,
):

    # Arrange

    with patch.object(
        analysis_module,
        "get_supabase_client",
        side_effect=ConnectionError(
            "Simulated connection failure"
        ),
    ) as mock_connection:

        # Act

        result = (
            analysis_module.extract_specific_columns(
                "paint_analysis_history",
                COLUMNS,
            )
        )

    # Assert

    mock_connection.assert_called_once()

    report = (
        analysis_module.log_extraction_report
        .call_args.args[0]
    )

    assert result.empty
    assert report["status"] == "FAILED"

    assert "connection" in (
        report["error"].lower()
    )

    assert report["records_extracted"] == 0


# ============================================================
# ADDITIONAL TEST 08: FAILED EXTRACTION HANDOVER
# ============================================================

def test_failed_extraction_raises_error(
    analysis_module,
):

    # Arrange

    client = MagicMock()

    client.table.return_value \
        .select.return_value \
        .execute.return_value = SimpleNamespace(
            data=[]
        )

    # Act and Assert

    with patch.object(
        analysis_module,
        "get_supabase_client",
        return_value=client,
    ):

        with pytest.raises(
            ValueError,
            match="Empty source",
        ):

            analysis_module.extract_specific_columns(
                "paint_analysis_history",
                COLUMNS,
                require_records=True,
                raise_on_error=True,
            )

    report = (
        analysis_module.log_extraction_report
        .call_args.args[0]
    )

    assert report["status"] == "FAILED"
