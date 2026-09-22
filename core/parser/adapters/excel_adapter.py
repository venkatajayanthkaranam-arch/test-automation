import re
import os
from typing import List, Dict, Any, Optional, Tuple
import openpyxl
from openpyxl.utils import get_column_letter

from core.models.schema import (
    CanonicalScript, CanonicalStep, SourceRef, StepStatus, DataQualityWarning, ConfidenceTier
)
from core.parser.column_matcher import ColumnMatcher

class ExcelAdapter:
    def __init__(self, column_matcher: Optional[ColumnMatcher] = None):
        self.matcher = column_matcher or ColumnMatcher()

    def parse(self, file_path: str, target_sheet: Optional[str] = None) -> List[CanonicalScript]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        wb = openpyxl.load_workbook(file_path, data_only=True)
        scripts: List[CanonicalScript] = []

        sheet_names = wb.sheetnames
        for sheet_name in sheet_names:
            clean_name = sheet_name.lower().strip()
            if clean_name in ['cover page', 'cover', 'index', 'summary', 'instruction', 'instructions', 'readme']:
                continue
            if target_sheet and sheet_name.lower() != target_sheet.lower():
                continue

            ws = wb[sheet_name]
            script = self._parse_worksheet(ws, file_path, sheet_name)
            if script and script.steps:
                scripts.append(script)

        return scripts

    def _parse_worksheet(self, ws, file_path: str, sheet_name: str) -> Optional[CanonicalScript]:
        rows = list(ws.iter_rows(values_only=False))
        if not rows or len(rows) < 2:
            return None

        metadata = self._extract_metadata(rows, sheet_name)
        header_row_idx, headers = self._find_table_header(rows)
        if header_row_idx is None:
            return None

        raw_table_rows = rows[header_row_idx + 1:]
        sample_values = []
        for r in raw_table_rows[:15]:
            row_vals = [c.value for c in r]
            if any(row_vals):
                sample_values.append(row_vals)

        header_strings = [str(c.value).strip() if c.value is not None else '' for c in rows[header_row_idx]]
        mapping, confidence = self.matcher.match_columns(header_strings, sample_values)

        if 'description' not in mapping and 'step_id' not in mapping:
            return None

        steps: List[CanonicalStep] = []
        warnings: List[DataQualityWarning] = []
        current_role = metadata.get('roles', [None])[0] if metadata.get('roles') else None
        current_process_step = None
        seen_step_ids = set()

        for r_offset, r in enumerate(raw_table_rows):
            actual_row_num = header_row_idx + 2 + r_offset
            row_vals = [c.value for c in r]
            
            if not any(v is not None and str(v).strip() for v in row_vals):
                continue

            def get_col_val(field_name: str) -> Optional[str]:
                if field_name in mapping:
                    c_idx = mapping[field_name]
                    if c_idx < len(row_vals):
                        v = row_vals[c_idx]
                        return str(v).strip() if v is not None else None
                return None

            raw_desc = get_col_val('description')
            step_id_val = get_col_val('step_id')
            role_val = get_col_val('role')
            process_step_val = get_col_val('process_step')
            test_data_val = get_col_val('test_data')
            expected_val = get_col_val('expected_result')
            observed_val = get_col_val('observed_result')
            status_val = get_col_val('status')
            sr_val = get_col_val('sr_number')
            notes_val = get_col_val('notes')

            if role_val:
                current_role = role_val
            if process_step_val:
                current_process_step = process_step_val

            if not raw_desc and not step_id_val:
                continue

            assigned_step_id = step_id_val or f"{metadata.get('script_id', sheet_name)}.{len(steps) + 1:02d}"
            
            if assigned_step_id in seen_step_ids:
                warnings.append(DataQualityWarning(
                    code="DUPLICATE_STEP_ID",
                    message=f"Duplicate Step ID '{assigned_step_id}' detected on row {actual_row_num}",
                    step_id=assigned_step_id,
                    row_index=actual_row_num
                ))
            seen_step_ids.add(assigned_step_id)

            if not raw_desc:
                warnings.append(DataQualityWarning(
                    code="EMPTY_DESCRIPTION",
                    message=f"Step {assigned_step_id} has an empty test action description",
                    step_id=assigned_step_id,
                    row_index=actual_row_num
                ))
                raw_desc = "<blank instruction>"

            cell_refs = {}
            for f_name, c_idx in mapping.items():
                if c_idx < len(r):
                    cell_refs[f_name] = f"{get_column_letter(c_idx + 1)}{actual_row_num}"

            norm_status = StepStatus.NOT_ATTEMPTED
            if status_val:
                s_lower = status_val.lower().strip()
                if 'pass' in s_lower:
                    norm_status = StepStatus.PASS
                elif 'fail' in s_lower:
                    norm_status = StepStatus.FAIL
                elif 'block' in s_lower:
                    norm_status = StepStatus.BLOCKED
                elif 'manual' in s_lower:
                    norm_status = StepStatus.MANUAL_REQUIRED
                elif 'in progress' in s_lower:
                    norm_status = StepStatus.IN_PROGRESS

            source_ref = SourceRef(
                file_path=os.path.abspath(file_path),
                format="xlsx",
                sheet_name=sheet_name,
                row_index=actual_row_num,
                cell_refs=cell_refs,
                metadata={"header_row": header_row_idx + 1}
            )

            canonical_step = CanonicalStep(
                id=assigned_step_id,
                sequence=len(steps) + 1,
                role=current_role,
                process_step=current_process_step,
                raw_text=raw_desc,
                test_data=test_data_val,
                expected_result=expected_val,
                observed_result=observed_val,
                status=norm_status,
                sr_number=sr_val,
                notes=notes_val,
                source_ref=source_ref
            )
            steps.append(canonical_step)

        fingerprint = self.matcher.compute_fingerprint(header_strings)

        return CanonicalScript(
            script_id=metadata.get('script_id', sheet_name),
            title=metadata.get('title', sheet_name),
            description=metadata.get('description'),
            system_environment=metadata.get('system_environment'),
            tester_name=metadata.get('tester_name'),
            roles=metadata.get('roles', []),
            steps=steps,
            warnings=warnings,
            source_file=os.path.abspath(file_path),
            sheet_name=sheet_name,
            template_fingerprint=fingerprint
        )

    def _extract_metadata(self, rows: List[Any], default_id: str) -> Dict[str, Any]:
        meta = {
            'script_id': default_id,
            'title': default_id,
            'description': None,
            'system_environment': None,
            'tester_name': None,
            'roles': []
        }
        for row in rows[:12]:
            for i, cell in enumerate(row):
                if cell.value is None:
                    continue
                c_str = str(cell.value).strip()
                c_lower = c_str.lower()
                next_val = None
                for k in range(i + 1, len(row)):
                    if row[k].value is not None and str(row[k].value).strip():
                        next_val = str(row[k].value).strip()
                        break
                if 'test case id' in c_lower and next_val:
                    meta['script_id'] = next_val
                elif 'test case title' in c_lower and next_val:
                    meta['title'] = next_val
                elif 'test case description' in c_lower and next_val:
                    meta['description'] = next_val
                elif 'system environment' in c_lower and next_val:
                    meta['system_environment'] = next_val
                elif 'tester name' in c_lower and next_val:
                    meta['tester_name'] = next_val
                elif c_lower in ['1st approver', '2nd approver', 'recruiter', 'hiring manager', 'candidate', 'buyer']:
                    if c_str not in meta['roles']:
                        meta['roles'].append(c_str)
        return meta

    def _find_table_header(self, rows: List[Any]) -> Tuple[Optional[int], List[str]]:
        candidate_keywords = ['test step', 'step id', 'description', 'expected result', 'role', 'status', 'action']
        for idx, row in enumerate(rows[:20]):
            row_texts = [str(c.value).strip().lower() for c in row if c.value is not None]
            if not row_texts:
                continue
            matches = sum(1 for kw in candidate_keywords if any(kw in txt for txt in row_texts))
            if matches >= 2:
                headers = [str(c.value).strip() if c.value is not None else '' for c in row]
                return idx, headers
        return None, []
