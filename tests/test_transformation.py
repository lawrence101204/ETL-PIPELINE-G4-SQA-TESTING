
# Author: Villalobos Lawrence C.
# Test Team: Haboc David Emannuel, Macalindong Trisha Anne, Villalobos Lawrence C.
# Date: 2026-11-25
# Test Suite: Transformation
# Description: Automated unit tests for the
# Paintelligent ETL Transformation Stage.

import importlib.util
import logging
import shutil
import sys

from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

BATCH_ID = "BATCH-UNIT-TEST"


# ============================================================
# ISOLATED TRANSFORMATION MODULE
# ============================================================

@pytest.fixture
def transformation_module(tmp_path, monkeypatch):

    source = ROOT / "pipeline/CSV/transformation.py"

    destination = (
        tmp_path / "pipeline/CSV/transformation.py"
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(source, destination)

    spec = importlib.util.spec_from_file_location(
        "isolated_transformation",
        destination,
    )

    module = importlib.util.module_from_spec(spec)

    isolated_logger = logging.Logger(
        "test.transformation"
    )

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

        # Suppress unnecessary console logs.
        # Preserve isolated file logging.

        for handler in isolated_logger.handlers[:]:

            if (
                isinstance(handler, logging.StreamHandler)
                and not isinstance(handler, logging.FileHandler)
            ):

                handler.close()

                isolated_logger.removeHandler(handler)

        # Prevent actual source extraction.

        module._original_get_extracted_data = module.get_extracted_data

        with patch.object(
            module,
            "get_extracted_data",
            side_effect=AssertionError(
                "Real source extraction is prohibited."
            ),
        ):

            yield module

    finally:

        for handler in isolated_logger.handlers[:]:

            handler.close()

            isolated_logger.removeHandler(handler)


# ============================================================
# MOCK PRODUCT DATA
# ============================================================

@pytest.fixture
def valid_products():

    return pd.DataFrame([
        {
            "Product Name": "White Paint GALLON",
            "Unit Purchase Price": "350.00",
            "Estimated Price (PHP)": "450.00",
            "Stocks": "25",
            "Category": "Paint",
            "Brand": "Sample Brand",
        }
    ])


# ============================================================
# MOCK SALES DATA
# ============================================================

@pytest.fixture
def valid_sales():

    return pd.DataFrame([
        {
            "Brand": "Sample Brand",
            "Product": "White Paint GALLON",
            "Category": "Paint",
            "Sales Date": "10/15/2026",
            "Quantity": "5",
            "Unit Sold": "2,250.00",
            "Season": "Rainy",
        }
    ])


# ============================================================
# MOCK PAINT ANALYSIS DATA
# ============================================================

@pytest.fixture
def valid_paint_analysis():

    return pd.DataFrame([
        {
            "id": "PA-001",
            "color_hex": "#FFFFFF",
            "rgb": "[255, 255, 255]",
            "paint_components": '{"white": 100}',
            "analysis_date": "2026-10-15",
        }
    ])


# ============================================================
# TR-01: SUCCESSFUL DATA TRANSFORMATION
# ============================================================

def test_successful_data_transformation(
    transformation_module,
    valid_products,
    valid_sales,
    valid_paint_analysis,
):

    quarantine = []

    original_products = valid_products.copy(deep=True)

    original_sales = valid_sales.copy(deep=True)

    original_paint = valid_paint_analysis.copy(deep=True)

    products, product_stats, product_rules = (
        transformation_module.transform_products(
            valid_products,
            BATCH_ID,
            quarantine,
        )
    )

    sales, sales_stats, sales_rules = (
        transformation_module.transform_sales(
            valid_sales,
            products,
            BATCH_ID,
            quarantine,
        )
    )

    paint, paint_stats, paint_rules = (
        transformation_module.transform_paint_analysis(
            valid_paint_analysis,
            BATCH_ID,
            quarantine,
        )
    )

    # Product assertions

    assert len(products) == 1

    assert list(products.columns) == (
        transformation_module.PRODUCT_COLUMNS
    )

    product = products.iloc[0]

    assert product["product_id"].startswith("PROD-")

    assert product["product_name"] == (
        "White Paint GALLON"
    )

    assert product["unit_purchase_price"] == (
        Decimal("350.00")
    )

    assert product["estimated_price_php"] == (
        Decimal("450.00")
    )

    assert product["stocks"] == 25

    # Sales assertions

    assert len(sales) == 1

    assert list(sales.columns) == (
        transformation_module.SALES_COLUMNS
    )

    sale = sales.iloc[0]

    assert sale["sales_id"].startswith("SALE-")

    assert sale["product"] == "White Paint GALLON"

    assert sale["sales_date"] == "2026-10-15"

    assert sale["quantity"] == 5

    assert sale["unit_sold"] == Decimal("2250.00")

    # Paint analysis assertions

    assert len(paint) == 1

    assert list(paint.columns) == (
        transformation_module.PAINT_COLUMNS
    )

    assert paint.iloc[0]["id"] == "PA-001"

    assert paint.iloc[0]["color"] == "#FFFFFF"

    assert paint.iloc[0]["analysis_date"] == (
        "2026-10-15T00:00:00"
    )

    # Verify record counts.

    for stats in [
        product_stats,
        sales_stats,
        paint_stats,
    ]:

        assert stats["records_read"] == 1

        assert stats["records_output"] == 1

        assert stats["records_rejected"] == 0

    assert quarantine == []

    # Verify original source data remains unchanged.

    pd.testing.assert_frame_equal(
        valid_products,
        original_products,
    )

    pd.testing.assert_frame_equal(
        valid_sales,
        original_sales,
    )

    pd.testing.assert_frame_equal(
        valid_paint_analysis,
        original_paint,
    )


# ============================================================
# TR-02: MISSING VALUE HANDLING
# ============================================================

def test_missing_value_handling(
    transformation_module,
    valid_products,
):

    quarantine = []

    optional_missing = (
        valid_products.iloc[0].to_dict()
    )

    optional_missing["Category"] = None

    optional_missing["Brand"] = None

    optional_missing["Unit Purchase Price"] = None

    required_missing = (
        valid_products.iloc[0].to_dict()
    )

    required_missing["Product Name"] = None

    source = pd.DataFrame([
        optional_missing,
        required_missing,
    ])

    result, stats, rules = (
        transformation_module.transform_products(
            source,
            BATCH_ID,
            quarantine,
        )
    )

    assert stats["records_read"] == 2

    assert stats["records_output"] == 1

    assert stats["records_rejected"] == 1

    assert len(result) == 1

    assert pd.isna(result.iloc[0]["category"])

    assert pd.isna(result.iloc[0]["brand"])

    assert pd.isna(
        result.iloc[0]["unit_purchase_price"]
    )

    assert len(quarantine) == 1

    assert quarantine[0]["rule_id"] == "C-02"

    assert quarantine[0]["source_dataset"] == (
        "products"
    )

    assert "missing required product name" in (
        quarantine[0]["quarantine_reason"].lower()
    )


# ============================================================
# TR-03: DATA TYPE CONVERSION
# ============================================================

def test_data_type_conversion(
    transformation_module,
):

    price_input = "1,250.50"

    quantity_input = "25"

    date_input = "10/15/2026"

    actual_price = (
        transformation_module.as_decimal(
            price_input
        )
    )

    actual_quantity = (
        transformation_module.as_integer(
            quantity_input
        )
    )

    actual_date = (
        transformation_module.parse_date(
            date_input,
            date_only=True,
        )
    )

    assert actual_price == Decimal("1250.50")

    assert isinstance(actual_price, Decimal)

    assert actual_quantity == 25

    assert isinstance(actual_quantity, int)

    assert actual_date == "2026-10-15"

    assert isinstance(actual_date, str)


# ============================================================
# TR-04: DATA STANDARDIZATION
# ============================================================

def test_data_standardization(
    transformation_module,
    valid_products,
    valid_sales,
):

    quarantine = []

    valid_products.loc[
        0, "Product Name"
    ] = "  White Paint GALLON  "

    valid_sales.loc[
        0, "Product"
    ] = "DR-5 white paint GAL"

    valid_sales.loc[
        0, "Brand"
    ] = "  Sample Brand  "

    valid_sales.loc[
        0, "Season"
    ] = "  Rainy  "

    products, product_stats, _ = (
        transformation_module.transform_products(
            valid_products,
            BATCH_ID,
            quarantine,
        )
    )

    sales, sales_stats, _ = (
        transformation_module.transform_sales(
            valid_sales,
            products,
            BATCH_ID,
            quarantine,
        )
    )

    assert len(products) == 1

    assert len(sales) == 1

    assert products.iloc[0]["product_name"] == (
        "White Paint GALLON"
    )

    assert sales.iloc[0]["product"] == (
        "White Paint GALLON"
    )

    assert sales.iloc[0]["brand"] == (
        "Sample Brand"
    )

    assert sales.iloc[0]["season"] == "Rainy"

    assert list(products.columns) == (
        transformation_module.PRODUCT_COLUMNS
    )

    assert list(sales.columns) == (
        transformation_module.SALES_COLUMNS
    )

    assert product_stats["records_rejected"] == 0

    assert sales_stats["records_rejected"] == 0

    assert quarantine == []

    assert not transformation_module.values_match(
        "White Paint GALLON",
        "White Paint LITER",
    )


# ============================================================
# TR-05: INVALID DATA HANDLING
# ============================================================

def test_invalid_data_handling(
    transformation_module,
    valid_products,
    valid_sales,
):

    quarantine = []

    invalid_product = valid_products.copy()

    invalid_product.loc[
        0, "Unit Purchase Price"
    ] = "ABC"

    invalid_sales = valid_sales.copy()

    invalid_sales.loc[
        0, "Quantity"
    ] = "XYZ"

    rejected_products, product_stats, _ = (
        transformation_module.transform_products(
            invalid_product,
            BATCH_ID,
            quarantine,
        )
    )

    valid_catalog, _, _ = (
        transformation_module.transform_products(
            valid_products,
            BATCH_ID,
            quarantine,
        )
    )

    rejected_sales, sales_stats, _ = (
        transformation_module.transform_sales(
            invalid_sales,
            valid_catalog,
            BATCH_ID,
            quarantine,
        )
    )

    assert rejected_products.empty

    assert rejected_sales.empty

    assert product_stats["records_rejected"] == 1

    assert sales_stats["records_rejected"] == 1

    assert product_stats["records_output"] == 0

    assert sales_stats["records_output"] == 0

    assert len(quarantine) == 2

    assert quarantine[0]["rule_id"] == "C-03"

    assert quarantine[1]["rule_id"] == "C-03"

    assert "invalid decimal" in (
        quarantine[0]["quarantine_reason"].lower()
    )

    assert "invalid integer" in (
        quarantine[1]["quarantine_reason"].lower()
    )


# ============================================================
# TR-06: DUPLICATE RECORD HANDLING
# ============================================================

def test_duplicate_record_handling(
    transformation_module,
    valid_paint_analysis,
):

    quarantine = []

    first_record = (
        valid_paint_analysis.iloc[0].to_dict()
    )

    duplicate_record = first_record.copy()

    duplicate_record["color_hex"] = "#0000FF"

    unique_record = first_record.copy()

    unique_record["id"] = "PA-002"

    unique_record["color_hex"] = "#FF0000"

    source = pd.DataFrame([
        first_record,
        duplicate_record,
        unique_record,
    ])

    result, stats, rules = (
        transformation_module.transform_paint_analysis(
            source,
            BATCH_ID,
            quarantine,
        )
    )

    assert stats["records_read"] == 3

    assert stats["records_output"] == 2

    assert stats["records_rejected"] == 1

    assert len(result) == 2

    assert result["id"].is_unique

    assert set(result["id"]) == {
        "PA-001",
        "PA-002",
    }

    retained_record = result.loc[
        result["id"] == "PA-001"
    ].iloc[0]

    assert retained_record["color"] == "#FFFFFF"

    assert len(quarantine) == 1

    assert quarantine[0]["rule_id"] == "C-04"

    assert quarantine[0]["source_dataset"] == (
        "paint_analysis"
    )

    assert "duplicate" in (
        quarantine[0]["quarantine_reason"].lower()
    )



# ============================================================
# ADDITIONAL TESTS: REJECTION RATE BOUNDARY
# ============================================================

@pytest.mark.parametrize(
    "total_records,rejected_records,expected_status,expected_exit",
    [
        (100, 0, "SUCCESS", 0),
        (100, 1, "SUCCESS_WITH_QUARANTINE", 0),
        (100, 2, "MANUAL_REVIEW", 1),
        (0, 0, "FAILED", 1),
    ],
    ids=[
        "zero-percent-rejection",
        "exactly-one-percent",
        "above-one-percent",
        "empty-input",
    ],
)
def test_rejection_rate_boundary(
    transformation_module,
    valid_products,
    valid_sales,
    valid_paint_analysis,
    total_records,
    rejected_records,
    expected_status,
    expected_exit,
):

    import json

    # Arrange: Generate synthetic product records.

    records = []

    for index in range(total_records):

        record = valid_products.iloc[0].to_dict()

        record["Product Name"] = (
            f"Mock Paint Product {index + 1}"
        )

        if index < rejected_records:

            record["Product Name"] = None

        records.append(record)

    products = pd.DataFrame(
        records,
        columns=valid_products.columns,
    )

    sales = valid_sales.iloc[0:0].copy()

    paint = valid_paint_analysis.iloc[0:0].copy()

    # Mock the extraction stage.
    # No actual source database is accessed.

    mocked_extraction = (
        transformation_module.get_extracted_data
    )

    mocked_extraction.side_effect = None

    mocked_extraction.return_value = (
        products,
        sales,
        paint,
        "MOCK-EXTRACTION-RUN",
    )

    # Act: Execute the isolated transformation stage.

    actual_exit = (
        transformation_module.run_transformation()
    )

    metadata_path = (
        transformation_module.OUTPUT_DIR
        / "handover_metadata.json"
    )

    assert metadata_path.exists()

    metadata = json.loads(
        metadata_path.read_text(encoding="utf-8")
    )

    # Assert: Execution status.

    assert actual_exit == expected_exit

    assert metadata["status"] == expected_status

    assert metadata["records_read"] == total_records

    assert metadata["records_rejected"] == (
        rejected_records
    )

    assert metadata["records_output"] == (
        total_records - rejected_records
    )

    assert metadata["parent_run_id"] == (
        "MOCK-EXTRACTION-RUN"
    )

    mocked_extraction.assert_called_once()

    # Assert: Quarantine output.

    quarantine_path = (
        transformation_module.QUARANTINE_FILE
    )

    assert quarantine_path.exists()

    quarantine = pd.read_csv(quarantine_path)

    assert len(quarantine) == rejected_records

    if rejected_records > 0:

        assert set(quarantine["rule_id"]) == {
            "C-02"
        }

    # Assert: Rejection threshold validation.

    rejection_validation = (
        metadata["validation_results"]["rejection_rate"]
    )

    if total_records == 0:

        assert rejection_validation == (
            "FAIL (no input records)"
        )

    elif rejected_records / total_records > 0.01:

        assert rejection_validation == "WARNING"

    else:

        assert rejection_validation == "PASS"


# ============================================================
# ADDITIONAL TESTS: RGB CHANNEL BOUNDARY
# ============================================================

@pytest.mark.parametrize(
    "rgb_value,expected_valid",
    [
        ([0, 0, 0], True),
        ([255, 255, 255], True),
        ([-1, 100, 100], False),
        ([256, 100, 100], False),
    ],
    ids=[
        "minimum-valid-rgb",
        "maximum-valid-rgb",
        "below-minimum-rgb",
        "above-maximum-rgb",
    ],
)
def test_rgb_boundary(
    transformation_module,
    rgb_value,
    expected_valid,
):

    actual_result = (
        transformation_module.validate_rgb(
            rgb_value
        )
    )

    assert actual_result == expected_valid


# ============================================================
# EXTRACTION-TO-TRANSFORMATION HANDOVER TESTS
# ============================================================

def test_handover_preserves_identifier(
    transformation_module,
    valid_products,
    valid_sales,
    valid_paint_analysis,
):
    from unittest.mock import Mock

    module = transformation_module

    csv_source = Mock()
    csv_source.extract_both_csvs.return_value = (
        valid_products,
        valid_sales,
    )

    analysis_source = Mock()

    def mock_extract(table_name, columns, **kwargs):
        return valid_paint_analysis[columns].copy()

    analysis_source.extract_specific_columns.side_effect = (
        mock_extract
    )

    with patch.object(
        module,
        "find_script",
        side_effect=lambda name: Path(name),
    ), patch.object(
        module,
        "load_module",
        side_effect=[csv_source, analysis_source],
    ):
        products, sales, paint, parent_id = (
            module._original_get_extracted_data()
        )

    assert "id" in paint.columns
    assert paint.iloc[0]["id"] == "PA-001"

    pd.testing.assert_frame_equal(
        products,
        valid_products,
    )

    pd.testing.assert_frame_equal(
        sales,
        valid_sales,
    )

    csv_source.extract_both_csvs.assert_called_once()
    analysis_source.extract_specific_columns.assert_called_once()


def test_handover_propagates_extraction_failure(
    transformation_module,
    valid_products,
    valid_sales,
):
    from unittest.mock import Mock

    module = transformation_module

    csv_source = Mock()
    csv_source.extract_both_csvs.return_value = (
        valid_products,
        valid_sales,
    )

    analysis_source = Mock()

    def mock_failed_extraction(
        table_name,
        columns,
        *,
        raise_on_error=False,
        **kwargs,
    ):
        if raise_on_error:
            raise ValueError("Mock extraction failure")

        return pd.DataFrame(columns=columns)

    analysis_source.extract_specific_columns.side_effect = (
        mock_failed_extraction
    )

    with patch.object(
        module,
        "find_script",
        side_effect=lambda name: Path(name),
    ), patch.object(
        module,
        "load_module",
        side_effect=[csv_source, analysis_source],
    ):
        with pytest.raises(
            ValueError,
            match="Mock extraction failure",
        ):
            module._original_get_extracted_data()

    analysis_source.extract_specific_columns.assert_called_once()
