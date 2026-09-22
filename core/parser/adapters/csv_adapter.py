import csv
import os
from typing import List, Optional
from core.models.schema import CanonicalScript, CanonicalStep, SourceRef, StepStatus, DataQualityWarning
from core.parser.column_matcher import ColumnMatcher

class DelimitedAdapter:
    def __init__(self, column_matcher: Optional[ColumnMatcher] = None):
        self.matcher = column_matcher or ColumnMatcher()

    def parse(self, file_path: str, delimiter: str = ',') -> List[CanonicalScript]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        rows = []
        with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            reader = csv.reader(f, delimiter=delimiter)
            for row in reader:
                rows.append([c.strip() for c in row])

        if not rows or len(rows) < 2:
            return []

        header_row_idx = 0
        headers = rows[0]
        sample_rows = rows[1:15]

        mapping, confidence = self.matcher.match_columns(headers, sample_rows)
        base_name = os.path.splitext(os.path.basename(file_path))[0]

        steps: List[CanonicalStep] = []
        warnings: List[DataQualityWarning] = []
        seen_ids = set()

        for idx, r in enumerate(rows[1:]):
            if not any(r):
                continue
            actual_row = idx + 2
            
            def get_val(f_key):
                if f_key in mapping and mapping[f_key] < len(r):
                    val = r[mapping[f_key]].strip()
                    return val if val else None
                return None

            desc = get_val('description')
            step_id = get_val('step_id') or f"{base_name}.{idx+1:02d}"
            role = get_val('role')
            test_data = get_val('test_data')
            expected = get_val('expected_result')
            status = get_val('status')

            if step_id in seen_ids:
                warnings.append(DataQualityWarning(
                    code="DUPLICATE_STEP_ID",
                    message=f"Duplicate Step ID '{step_id}' on line {actual_row}",
                    step_id=step_id,
                    row_index=actual_row
                ))
            seen_ids.add(step_id)

            cell_refs = {k: f"col_{v+1}_row_{actual_row}" for k, v in mapping.items() if v < len(r)}

            source_ref = SourceRef(
                file_path=os.path.abspath(file_path),
                format="csv",
                row_index=actual_row,
                cell_refs=cell_refs
            )

            steps.append(CanonicalStep(
                id=step_id,
                sequence=len(steps) + 1,
                role=role,
                raw_text=desc or "<blank>",
                test_data=test_data,
                expected_result=expected,
                status=StepStatus.NOT_ATTEMPTED,
                source_ref=source_ref
            ))

        fingerprint = self.matcher.compute_fingerprint(headers)

        return [CanonicalScript(
            script_id=base_name,
            title=base_name.replace('_', ' ').title(),
            steps=steps,
            warnings=warnings,
            source_file=os.path.abspath(file_path),
            template_fingerprint=fingerprint
        )]
