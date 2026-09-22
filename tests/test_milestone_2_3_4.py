import os
import pytest
from core.models.schema import StepStatus, ActionType, ConfidenceTier
from core.parser.universal_parser import UniversalParser
from core.interpreter.intent_parser import StepInterpreter
from core.writeback.excel_writer import ExcelWriteBackEngine
from core.writeback.html_reporter import HtmlReportEngine

TMEIC_WORKBOOK = r"C:\Users\aniru\Downloads\TMEIC_ORC_040_Validation_Scripts_Final.xlsx"

def test_compound_step_splitter():
    interpreter = StepInterpreter()
    parser = UniversalParser()
    scripts = parser.parse(TMEIC_WORKBOOK, target_script="ORC_040")
    script = scripts[0]

    # Step ORC_040.06: "Click on link to view details → Click on Approve button"
    step6 = next(s for s in script.steps if s.id == "ORC_040.06")
    assert step6.is_compound is True
    assert len(step6.sub_steps) == 2
    assert step6.sub_steps[0].raw_text == "Click on link to view details"
    assert step6.sub_steps[1].raw_text == "Click on Approve button"
    assert step6.sub_steps[1].parsed_actions[0].action_type == ActionType.CLICK
    assert step6.confidence_tier == ConfidenceTier.AUTO_RUNNABLE

def test_in_place_excel_writeback(tmp_path):
    parser = UniversalParser()
    scripts = parser.parse(TMEIC_WORKBOOK, target_script="ORC_040")
    script = scripts[0]

    # Simulate passing execution
    for step in script.steps:
        step.status = StepStatus.PASS
        step.observed_result = "Test executed successfully in Oracle Fusion"

    out_xlsx = str(tmp_path / "ORC_040_executed_test.xlsx")
    writer = ExcelWriteBackEngine()
    result_path = writer.write_back(script, output_path=out_xlsx)

    assert os.path.exists(result_path)
    
    # Verify values in output
    import openpyxl
    wb = openpyxl.load_workbook(result_path)
    ws = wb["ORC_040"]
    # Check status column on row 11 (first step)
    step1_status_cell = ws[script.steps[0].source_ref.cell_refs["status"]].value
    assert step1_status_cell == "Pass"

def test_html_report_generation(tmp_path):
    parser = UniversalParser()
    scripts = parser.parse(TMEIC_WORKBOOK, target_script="ORC_040")
    script = scripts[0]
    
    script.steps[0].status = StepStatus.PASS
    script.steps[0].observed_result = "Notification clicked"

    out_html = str(tmp_path / "report.html")
    reporter = HtmlReportEngine()
    result_html = reporter.generate_report(script, output_path=out_html)

    assert os.path.exists(result_html)
    with open(result_html, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "ORC_040" in content
        assert "Job Offer Approval" in content
        assert "badge-Pass" in content
