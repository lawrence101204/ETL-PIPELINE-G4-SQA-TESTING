
# Author: Haboc David Emannuel, Macalindong Trisha Anne, Villalobos Lawrence C.
# Date: 2026-11-25
# Description: Custom Pytest Terminal Reporter
# Project: Paintelligent ETL Pipeline - SQA Testing

import argparse
import os
import shutil
import sys
import time

from pathlib import Path

import pytest

try:
    from colorama import just_fix_windows_console
    just_fix_windows_console()
except ImportError:
    pass


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent

SUITES = {
    "extraction": "tests/test_extraction.py",
    "transformation": "tests/test_transformation.py",
    "loading": "tests/test_loading.py",
    "all": "tests",
}

COLORS_ENABLED = sys.stdout.isatty()

RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
WHITE = "\033[97m"
GRAY = "\033[90m"
BOLD = "\033[1m"

WIDTH = max(
    40,
    min(
        shutil.get_terminal_size((88, 24)).columns - 1,
        100
    )
)


def colored(text, color):

    if not COLORS_ENABLED:
        return text

    return f"{color}{text}{RESET}"


def divider():

    print(colored("-" * WIDTH, GRAY))


def centered(text, color=WHITE):

    print(colored(text.center(WIDTH), color))


# ============================================================
# CUSTOM PYTEST REPORTER
# ============================================================

class CustomReporter:

    def __init__(self):

        self.collected = 0

        self.results = {}

        self.errors = []

    def pytest_collection_finish(self, session):

        self.collected = len(session.items)

    def pytest_collectreport(self, report):

        if report.failed:

            self.errors.append(
                (
                    report.nodeid,
                    report.longreprtext
                )
            )

    def pytest_runtest_logreport(self, report):

        self.results.setdefault(
            report.nodeid,
            []
        ).append(report)

    def pytest_internalerror(self, excrepr):

        self.errors.append(
            (
                "Pytest internal error",
                str(excrepr)
            )
        )

    def pytest_keyboard_interrupt(self, excinfo):

        self.errors.append(
            (
                "Testing interrupted",
                str(excinfo)
            )
        )

    def get_status(self, reports):

        # Setup and teardown errors take priority.

        for report in reports:

            if report.failed and report.when != "call":
                return "ERROR"

        # Check actual test failures.

        for report in reports:

            if report.failed:
                return "FAILED"

        # Check expected failures.

        for report in reports:

            if hasattr(report, "wasxfail"):

                if report.skipped:
                    return "XFAILED"

                if report.passed:
                    return "XPASSED"

        # Check skipped tests.

        if any(report.skipped for report in reports):

            return "SKIPPED"

        # Only report PASSED when the test actually passed.

        for report in reports:

            if report.when == "call" and report.passed:

                return "PASSED"

        return "INCOMPLETE"


# ============================================================
# TERMINAL HEADER
# ============================================================

def print_header(suite):

    print()

    print(colored("=" * WIDTH, CYAN))

    centered(
        "PAINTELLIGENT",
        BOLD + CYAN
    )

    centered(
        "ETL PIPELINE - SOFTWARE QUALITY ASSURANCE",
        WHITE
    )

    print(colored("=" * WIDTH, CYAN))

    print()

    print(
        colored("Test Suite : ", GRAY)
        + colored(suite.upper(), CYAN)
    )

    print(
        colored("Test Authors: ", GRAY)
        + "Haboc David Emannuel"
    )

    print(" " * 14 + "Macalindong Trisha Anne")
    print(" " * 14 + "Villalobos Lawrence C.")

    print(
        colored("Framework  : ", GRAY)
        + f"Pytest {pytest.__version__}"
    )

    print()


# ============================================================
# DISPLAY INDIVIDUAL TEST RESULT
# ============================================================

def print_test_result(name, status):

    status_colors = {
        "PASSED": GREEN,
        "FAILED": RED,
        "ERROR": RED,
        "SKIPPED": YELLOW,
        "XFAILED": YELLOW,
        "XPASSED": YELLOW,
        "INCOMPLETE": YELLOW,
    }

    color = status_colors.get(status, WHITE)

    available_width = WIDTH - len(status) - 2

    if len(name) > available_width:

        print(colored(name, WHITE))

        print(
            colored(
                status.rjust(WIDTH),
                color
            )
        )

    else:

        print(
            colored(
                name.ljust(available_width),
                WHITE
            )
            + "  "
            + colored(status, color)
        )


# ============================================================
# FINAL REPORT
# ============================================================

def print_results(reporter, suite, duration, exit_code):

    counts = {
        "PASSED": 0,
        "FAILED": 0,
        "ERROR": 0,
        "SKIPPED": 0,
        "XFAILED": 0,
        "XPASSED": 0,
        "INCOMPLETE": 0,
    }

    print(
        colored(
            f"collected {reporter.collected} items",
            CYAN
        )
    )

    print()

    divider()

    for nodeid, reports in reporter.results.items():

        status = reporter.get_status(reports)

        counts[status] += 1

        parts = nodeid.split("::")

        test_name = "::".join(parts[1:])

        if not test_name:
            test_name = nodeid

        if suite == "all" and len(parts) > 1:

            test_name = (
                Path(parts[0]).stem
                + " :: "
                + test_name
            )

        print_test_result(test_name, status)

    divider()

    # Display actual failure details.

    failures = []

    for nodeid, reports in reporter.results.items():

        for report in reports:

            if report.failed:

                failures.append(
                    (
                        nodeid,
                        report.longreprtext
                    )
                )

    failures.extend(reporter.errors)

    if failures:

        print()

        centered(
            "FAILURE DETAILS",
            BOLD + RED
        )

        divider()

        for name, details in failures:

            print()

            print(colored(name, RED))

            print(details)

            divider()

    total = reporter.collected

    passed = counts["PASSED"]

    failed = counts["FAILED"]

    errors = (
        counts["ERROR"]
        + len(reporter.errors)
    )

    pass_rate = (
        passed / total * 100
        if total > 0
        else 0
    )

    print()

    centered(
        "TEST EXECUTION SUMMARY",
        BOLD + CYAN
    )

    divider()

    print(f"Total collected     : {total}")

    print(
        colored(
            f"Passed              : {passed}",
            GREEN
        )
    )

    print(
        colored(
            f"Failed              : {failed}",
            RED if failed else WHITE
        )
    )

    print(f"Errors              : {errors}")

    print(f"Skipped             : {counts['SKIPPED']}")

    print(f"Expected failures   : {counts['XFAILED']}")

    print(f"Unexpected passes   : {counts['XPASSED']}")

    print(f"Incomplete          : {counts['INCOMPLETE']}")

    print(f"Pass rate           : {pass_rate:.2f}%")

    print(f"Execution time      : {duration:.2f}s")

    divider()

    print()

    if (
        exit_code == 0
        and total > 0
        and passed == total
    ):

        centered(
            f"========== {passed} PASSED ==========",
            BOLD + GREEN
        )

        centered(
            "ALL TESTS PASSED SUCCESSFULLY",
            GREEN
        )

    elif exit_code == 0:

        centered(
            "TEST RUN COMPLETED WITH NON-PASS RESULTS",
            BOLD + YELLOW
        )

    else:

        centered(
            "TEST EXECUTION UNSUCCESSFUL",
            BOLD + RED
        )

    print()

    print(
        colored(
            f"Pytest exit code: {exit_code}",
            GRAY
        )
    )

    print()


# ============================================================
# MAIN EXECUTION
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="Paintelligent SQA Custom Test Runner"
    )

    parser.add_argument(
        "suite",
        choices=list(SUITES.keys()),
        nargs="?",
        default="all",
    )

    args = parser.parse_args()

    os.chdir(ROOT)

    test_path = ROOT / SUITES[args.suite]

    if not test_path.exists():

        print(
            colored(
                f"Test file not found: {test_path}",
                RED
            )
        )

        return 4

    reporter = CustomReporter()

    print_header(args.suite)

    started = time.perf_counter()

    exit_code = pytest.main(
        [
            str(test_path),
            "-p",
            "no:terminal",
            "-p",
            "no:sugar",
        ],
        plugins=[reporter],
    )

    duration = time.perf_counter() - started

    print_results(
        reporter,
        args.suite,
        duration,
        int(exit_code),
    )

    return int(exit_code)


if __name__ == "__main__":

    sys.exit(main())
