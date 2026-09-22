import os
import shutil
import openpyxl
from openpyxl.styles import PatternFill, Font
from typing import List, Optional, Union
from core.models.schema import CanonicalScript, StepStatus

PASS_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
PASS_FONT = Font(color="006100", bold=True)

FAIL_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
FAIL_FONT = Font(color="9C0006", bold=True)

BLOCKED_FILL = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
BLOCKED_FONT = Font(color="9C5700", bold=True)

class ExcelWriteBackEngine:
    def write_back(self, scripts: Union[CanonicalScript, List[CanonicalScript]], output_path: Optional[str] = None) -> str:
        """
        Writes back execution results into an Excel workbook.
        Supports both single CanonicalScript or multiple CanonicalScripts (multi-sheet).
        """
        if isinstance(scripts, CanonicalScript):
            script_list = [scripts]
        else:
            script_list = scripts

        if not script_list:
            raise ValueError("No scripts provided for Excel write-back.")

        source_path = script_list[0].source_file
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source file not found: {source_path}")

        if not output_path:
            base, ext = os.path.splitext(source_path)
            output_path = f"{base}_executed{ext}"

        shutil.copyfile(source_path, output_path)
        wb = openpyxl.load_workbook(output_path)

        for script in script_list:
            sheet_name = script.sheet_name or script.script_id
            if sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
            elif len(script_list) == 1:
                ws = wb.active
            else:
                continue

            for step in script.steps:
                refs = step.source_ref.cell_refs
                
                if "status" in refs:
                    cell = ws[refs["status"]]
                    cell.value = step.status.value
                    if step.status == StepStatus.PASS:
                        cell.fill = PASS_FILL
                        cell.font = PASS_FONT
                    elif step.status == StepStatus.FAIL:
                        cell.fill = FAIL_FILL
                        cell.font = FAIL_FONT
                    elif step.status in [StepStatus.BLOCKED, StepStatus.MANUAL_REQUIRED]:
                        cell.fill = BLOCKED_FILL
                        cell.font = BLOCKED_FONT

                if "observed_result" in refs and step.observed_result:
                    cell = ws[refs["observed_result"]]
                    cell.value = step.observed_result

                if "notes" in refs and step.notes:
                    cell = ws[refs["notes"]]
                    cell.value = step.notes

        wb.save(output_path)
        return output_path
