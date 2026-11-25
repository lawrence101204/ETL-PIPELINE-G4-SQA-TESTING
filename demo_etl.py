
# Paintelligent ETL - Dataset Demonstration
# Authors:
# Haboc David Emannuel
# Macalindong Trisha Anne
# Villalobos Lawrence C.

import argparse
import atexit
import csv
import importlib.util
import json
import shutil
import sqlite3
import sys
import uuid

from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parent

DATASETS = ROOT / "demo" / "datasets"

OUTPUT = ROOT / "demo_output"


def write_csv(path, records):

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(records[0]),
        )

        writer.writeheader()
        writer.writerows(records)


def prepare_datasets():

    for scenario in ["success", "failed"]:

        products = [
            {
                "Product Name": "White Paint GALLON",
                "Unit Purchase Price": "350",
                "Estimated Price (PHP)": "450",
                "Stocks": "25",
                "Category": "Paint",
                "Brand": "Sample Brand",
            },
            {
                "Product Name": "Blue Paint LITER",
                "Unit Purchase Price": "180",
                "Estimated Price (PHP)": "250",
                "Stocks": "40",
                "Category": "Paint",
                "Brand": "Sample Brand",
            },
            {
                "Product Name": "Primer GALLON",
                "Unit Purchase Price": "300",
                "Estimated Price (PHP)": "400",
                "Stocks": "15",
                "Category": "Primer",
                "Brand": "Sample Brand",
            },
        ]

        sales = [
            {
                "Brand": "Sample Brand",
                "Product": "White Paint GALLON",
                "Category": "Paint",
                "Sales Date": "2026-10-15",
                "Quantity": "5",
                "Unit Sold": "2250",
                "Season": "Rainy",
            },
            {
                "Brand": "Sample Brand",
                "Product": "Blue Paint LITER",
                "Category": "Paint",
                "Sales Date": "2026-10-16",
                "Quantity": "3",
                "Unit Sold": "750",
                "Season": "Rainy",
            },
            {
                "Brand": "Sample Brand",
                "Product": "White Paint GALLON",
                "Category": "Paint",
                "Sales Date": "2026-04-10",
                "Quantity": "2",
                "Unit Sold": "900",
                "Season": "Dry",
            },
            {
                "Brand": "Sample Brand",
                "Product": "Blue Paint LITER",
                "Category": "Paint",
                "Sales Date": "2026-04-11",
                "Quantity": "4",
                "Unit Sold": "1000",
                "Season": "Dry",
            },
        ]

        paint_analysis = [
            {
                "id": "PA-001",
                "color_hex": "#FFFFFF",
                "rgb": "[255, 255, 255]",
                "paint_components": '{"white": 100}',
                "analysis_date": "2026-10-15",
            },
            {
                "id": "PA-002",
                "color_hex": "#0000FF",
                "rgb": "[0, 0, 255]",
                "paint_components": '{"blue": 100}',
                "analysis_date": "2026-10-16",
            },
        ]

        if scenario == "failed":

            # Intentional invalid product price.
            products[2]["Unit Purchase Price"] = "-300"

            # Intentional invalid sales quantity.
            sales[0]["Quantity"] = "-5"

            # Intentional invalid RGB channel.
            paint_analysis[0]["rgb"] = "[256, 255, 255]"

        directory = DATASETS / scenario

        write_csv(
            directory / "products.csv",
            products,
        )

        write_csv(
            directory / "sales.csv",
            sales,
        )

        write_csv(
            directory / "paint_analysis.csv",
            paint_analysis,
        )

        print(f"DATASET CREATED: {directory}")
        print("Products: 3")
        print("Sales: 4")
        print("Paint Analysis: 2")
        print("Total Records: 9")
        print()

    print("BOTH DEMONSTRATION DATASETS CREATED")


def import_module(name, path):

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import {path}")

    module = importlib.util.module_from_spec(spec)

    sys.modules[name] = module

    spec.loader.exec_module(module)

    return module


def read_json(path):

    if not path.exists():
        raise FileNotFoundError(path)

    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


def run_demo(scenario):

    dataset = DATASETS / scenario

    for filename in [
        "products.csv",
        "sales.csv",
        "paint_analysis.csv",
    ]:

        if not (dataset / filename).exists():
            raise FileNotFoundError(
                f"Missing dataset: {filename}. "
                "Run prepare first."
            )

    # Create an isolated project directory.
    # Never overwrite the original target database.

    run_id = uuid.uuid4().hex[:8]

    workspace = OUTPUT / f"{scenario}-{run_id}"

    workspace.mkdir(
        parents=True,
        exist_ok=False,
    )

    # Copy the actual ETL implementation.

    source_scripts = [
        "pipeline/CSV/csv_extraction.py",
        "pipeline/analysis_extraction.py",
        "pipeline/CSV/transformation.py",
        "pipeline/CSV/load.py",
    ]

    for filename in source_scripts:

        destination = workspace / filename

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            ROOT / filename,
            destination,
        )

    csv_directory = workspace / "pipeline" / "CSV"

    shutil.copy2(
        dataset / "products.csv",
        csv_directory / "All Products - Cleaned.csv",
    )

    shutil.copy2(
        dataset / "sales.csv",
        csv_directory / "GPC_Sales - make equal.csv",
    )

    # Read synthetic Paint Analysis source records.

    with (dataset / "paint_analysis.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as file:

        paint_records = list(csv.DictReader(file))

    print("=" * 65)
    print("PAINTELLIGENT ETL DATASET DEMONSTRATION")
    print("=" * 65)
    print(f"Scenario: {scenario.upper()}")
    print(f"Workspace: {workspace}")
    print("Source: Synthetic CSV datasets")
    print("Target: Isolated SQLite database")
    print("=" * 65)

    transformation = import_module(
        "demo_transformation",
        csv_directory / "transformation.py",
    )

    original_loader = transformation.load_module

    csv_modules = []

    def offline_loader(name, path):

        if Path(path).name == "csv_extraction.py":

            # Manage the CSV module's logging ourselves.

            with patch.object(atexit, "register"):

                module = original_loader(name, path)

            csv_modules.append(module)

            return module

        if Path(path).name == "analysis_extraction.py":

            module = original_loader(name, path)

            # Replace only the external Supabase connection.
            # Actual extraction validation remains active.

            client = Mock()

            client.table.return_value.select.return_value.execute.return_value = (
                SimpleNamespace(data=paint_records)
            )

            module.get_supabase_client = Mock(
                return_value=client
            )

            return module

        raise RuntimeError(
            f"Unexpected module: {path}"
        )

    original_stdout = sys.stdout
    original_stderr = sys.stderr

    try:

        with patch.object(
            transformation,
            "load_module",
            side_effect=offline_loader,
        ):

            transformation_exit = (
                transformation.run_transformation()
            )

    finally:

        sys.stdout = original_stdout
        sys.stderr = original_stderr

        for module in csv_modules:

            if hasattr(module, "log_file"):
                module.log_file.close()

    metadata = read_json(
        workspace
        / "transformation"
        / "output"
        / "handover_metadata.json"
    )

    # Execute the real Loading Stage against a new,
    # isolated SQLite database.

    loader = import_module(
        "demo_loading",
        csv_directory / "load.py",
    )

    loading_exit = loader.run_load()

    load_metadata = read_json(
        workspace / "load" / "load_metadata.json"
    )

    print()
    print("=" * 65)
    print("FINAL DEMONSTRATION RESULTS")
    print("=" * 65)

    print(f"Scenario           : {scenario.upper()}")
    print(f"Records read       : {metadata['records_read']}")
    print(f"Records transformed: {metadata['records_output']}")
    print(f"Records rejected   : {metadata['records_rejected']}")
    print(f"Transformation     : {metadata['status']}")
    print(f"Loading            : {load_metadata['status']}")
    print(f"Acceptance         : {load_metadata['acceptance_decision']}")

    database = workspace / "load" / "paintelligent.db"

    print()
    print("SQLITE DATABASE CONTENTS")
    print("-" * 65)

    if database.exists():

        with closing(
            sqlite3.connect(
                database.resolve().as_uri() + "?mode=ro",
                uri=True,
            )
        ) as connection:

            for table in [
                "product_table",
                "sales_table",
                "paint_analysis_table",
            ]:

                count = connection.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]

                print(f"{table}: {count} records")

            if load_metadata["status"] == "SUCCESS":

                rows = connection.execute(
                    """
                    SELECT product_name,
                           estimated_price_php,
                           stocks
                    FROM product_table
                    """
                ).fetchall()

                print()
                print("TRANSFORMED PRODUCTS")

                for row in rows:
                    print(row)

    print()
    print(f"Output folder: {workspace}")
    print(f"Transformation exit code: {transformation_exit}")
    print(f"Loading exit code: {loading_exit}")

    print("=" * 65)

    return loading_exit or transformation_exit


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "scenario",
        choices=["prepare", "success", "failed"],
    )

    arguments = parser.parse_args()

    if arguments.scenario == "prepare":

        prepare_datasets()

        return 0

    return run_demo(arguments.scenario)


if __name__ == "__main__":

    sys.exit(main())
