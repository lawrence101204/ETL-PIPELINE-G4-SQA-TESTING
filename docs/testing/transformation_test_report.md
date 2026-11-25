# Transformation Unit Testing Report

## 1. Project Information

- Project: Paintelligent ETL Pipeline
- Subject: Software Quality Assurance
- Test Authors: Haboc David Emannuel, Macalindong Trisha Anne, Villalobos Lawrence C.
- Testing Date: November 25, 2026
- Framework: Pytest 9.2.0
- Test Suite: Transformation

## 2. Testing Objective

To verify the correctness, reliability, data validation,
standardization, and error-handling capabilities of the
Transformation Stage using synthetic and mocked input data.

## 3. Required Test Cases

| Test ID | Test Case | Result |
|---|---|---|
| TR-01 | Successful Data Transformation | PASSED |
| TR-02 | Missing Value Handling | PASSED |
| TR-03 | Data Type Conversion | PASSED |
| TR-04 | Data Standardization | PASSED |
| TR-05 | Invalid Data Handling | PASSED |
| TR-06 | Duplicate Record Handling | PASSED |

## 4. Additional Test Cases

| Test Case | Result |
|---|---|
| Zero percent rejection | PASSED |
| Exactly one percent rejection | PASSED |
| Above one percent rejection | PASSED |
| Empty input dataset | PASSED |
| Minimum valid RGB value | PASSED |
| Maximum valid RGB value | PASSED |
| Below minimum RGB value | PASSED |
| Above maximum RGB value | PASSED |
| Handover preserves identifier | PASSED |
| Handover propagates extraction failure | PASSED |

## 5. Boundary Testing Results

### Rejection Rate

| Total Records | Rejected | Expected Status | Result |
|---|---|---|---|
| 100 | 0 | SUCCESS | PASSED |
| 100 | 1 | SUCCESS_WITH_QUARANTINE | PASSED |
| 100 | 2 | MANUAL_REVIEW | PASSED |
| 0 | 0 | FAILED | PASSED |

### RGB Validation

| Input | Expected Result | Test Result |
|---|---|---|
| [0, 0, 0] | Valid | PASSED |
| [255, 255, 255] | Valid | PASSED |
| [-1, 100, 100] | Invalid | PASSED |
| [256, 100, 100] | Invalid | PASSED |

## 6. Initial Expanded Test Results

- Total Tests: 16
- Passed: 14
- Failed: 2
- Pass Rate: 87.50%
- Execution Time: 4.15 seconds

## 7. Defect Documentation

### DEF-004: Missing Identifier Handover

Expected Behavior:
The Paint Analysis identifier must be preserved when
transferring extracted data to the Transformation Stage.

Actual Behavior:
The requested extraction columns excluded the id field.

Root Cause:
The identifier was missing from the requested column list
inside get_extracted_data().

Corrective Action:
Added id to the requested Paint Analysis columns.

Retest Result: PASSED

### DEF-005: Extraction Failure Propagation

Expected Behavior:
A Paint Analysis extraction failure must be propagated
to the Transformation Stage.

Actual Behavior:
The handover function did not propagate the mocked
extraction failure.

Root Cause:
The extraction function was called without enabling
raise_on_error.

Corrective Action:
Enabled raise_on_error=True during the handover.

Retest Result: PASSED

## 8. Final Transformation Test Results

- Required Test Cases: 6
- Additional Test Executions: 10
- Total Tests: 16
- Passed: 16
- Failed: 0
- Pass Rate: 100%

## 9. Combined Regression Testing

| Test Suite | Passed | Failed |
|---|---|---|
| Extraction | 19 | 0 |
| Transformation | 16 | 0 |
| Total | 35 | 0 |

- Overall Pass Rate: 100%
- Execution Time: 6.69 seconds
- Pytest Exit Code: 0

## 10. Testing Environment

- Operating System: Windows
- Python Version: 3.13.0
- Pytest Version: 9.2.0
- Testing Method: Automated Unit Testing
- Input Data: Synthetic and Mocked
- Database Connection: Mocked or isolated

## 11. Scope and Limitations

No actual business datasets or production database
connections were used in the Transformation tests.

The test results verify the implemented test scenarios
and do not establish complete source-code coverage.

The extraction-to-transformation handover was verified
using mocked extraction modules.

A discrepancy remains between the documented stock
validation rules and the permissive stock handling
in the existing implementation. This requires business
rule clarification before further changes are made.

Loading and complete end-to-end ETL validation remain
outside the scope of this test report.

## 12. Conclusion

All six required Transformation test cases and ten
additional test executions passed following corrective
actions.

The combined regression test verified that the applied
handover corrections did not introduce failures in the
existing Extraction test suite.

A total of 35 Extraction and Transformation test
executions passed successfully.
