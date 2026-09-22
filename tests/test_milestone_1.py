import os
import pytest
from core.parser.universal_parser import UniversalParser
from core.parser.column_matcher import ColumnMatcher
from core.models.schema import StepStatus, ConfidenceTier

TMEIC_WORKBOOK = r"C:\Users\aniru\Downloads\TMEIC_ORC_040_Validation_Scripts_Final.xlsx"
FIXTURES_DIR = r"A:\test automation\tests\fixtures"

def test_column_matcher_direct():
    matcher = ColumnMatcher()
    headers = ["Step Number", "Assigned Role", "Instruction", "Expected Outcome", "Test Values", "Execution Status"]
    samples = [
        ["ORC_001.01", "1st Approver", "Click Bell Icon to open notifications", "Bell notifications panel opens", "<blank>", "Not Attempted"],
        ["ORC_001.02", "1st Approver", "Click on Approval task", "Approval details page is shown", "<blank>", "Pass"]
    ]
    mapping, conf = matcher.match_columns(headers, samples)
    
    assert mapping["step_id"] == 0
    assert mapping["role"] == 1
    assert mapping["description"] == 2
    assert mapping["expected_result"] == 3
    assert mapping["test_data"] == 4
    assert mapping["status"] == 5
    assert conf >= 0.70

def test_parse_tmeic_orc_040_workbook():
    if not os.path.exists(TMEIC_WORKBOOK):
        pytest.skip("TMEIC workbook not found at specified path")

    parser = UniversalParser()
    scripts = parser.parse(TMEIC_WORKBOOK, target_script="ORC_040")
    
    assert len(scripts) == 1
    script = scripts[0]
    
    assert script.script_id == "ORC_040"
    assert "Job Offer Approval" in script.title or "Multi-Level" in script.title
    assert len(script.steps) >= 5
    
    step1 = script.steps[0]
    assert step1.id == "ORC_040.01"
    assert "1st Approver" in step1.role
    assert "bell icon" in step1.raw_text.lower()
    assert step1.source_ref.sheet_name == "ORC_040"
    assert "status" in step1.source_ref.cell_refs
    assert "observed_result" in step1.source_ref.cell_refs

def test_parse_shuffled_csv():
    csv_path = os.path.join(FIXTURES_DIR, "shuffled_test.csv")
    parser = UniversalParser()
    scripts = parser.parse(csv_path)
    
    assert len(scripts) == 1
    script = scripts[0]
    assert len(script.steps) == 3
    assert script.steps[0].id == "REQ_01.01"
    assert script.steps[0].role == "Recruiter"
    assert "Job Requisitions" in script.steps[0].raw_text

def test_parse_messy_multi_row_excel():
    excel_path = os.path.join(FIXTURES_DIR, "messy_layout.xlsx")
    parser = UniversalParser()
    scripts = parser.parse(excel_path)
    
    assert len(scripts) == 1
    script = scripts[0]
    assert script.script_id == "AP_INV_001"
    assert len(script.steps) == 5
    assert script.steps[0].role == "Accounts Payable Specialist"
    assert "Invoices" in script.steps[0].raw_text

def test_parse_prose_docx():
    docx_path = os.path.join(FIXTURES_DIR, "prose_script.docx")
    parser = UniversalParser()
    scripts = parser.parse(docx_path)
    
    assert len(scripts) == 1
    script = scripts[0]
    assert len(script.steps) == 4
    assert script.steps[0].id == "1"
    assert "Talent Review" in script.steps[0].raw_text

if __name__ == "__main__":
    test_column_matcher_direct()
    print("✓ test_column_matcher_direct passed")
    test_parse_tmeic_orc_040_workbook()
    print("✓ test_parse_tmeic_orc_040_workbook passed")
    test_parse_shuffled_csv()
    print("✓ test_parse_shuffled_csv passed")
    test_parse_messy_multi_row_excel()
    print("✓ test_parse_messy_multi_row_excel passed")
    test_parse_prose_docx()
    print("✓ test_parse_prose_docx passed")
    print("\nALL MILESTONE 1 TESTS PASSED PERFECTLY!")
