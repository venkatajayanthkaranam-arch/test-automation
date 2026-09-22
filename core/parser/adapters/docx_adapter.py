import os
import re
from typing import List, Optional
import docx

from core.models.schema import CanonicalScript, CanonicalStep, SourceRef, StepStatus, DataQualityWarning
from core.parser.column_matcher import ColumnMatcher

class DocxAdapter:
    def __init__(self, column_matcher: Optional[ColumnMatcher] = None):
        self.matcher = column_matcher or ColumnMatcher()

    def parse(self, file_path: str) -> List[CanonicalScript]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        doc = docx.Document(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        scripts: List[CanonicalScript] = []

        # 1. Check for Tables
        if doc.tables:
            for t_idx, table in enumerate(doc.tables):
                table_rows = []
                for row in table.rows:
                    table_rows.append([cell.text.strip() for cell in row.cells])
                
                if len(table_rows) < 2:
                    continue

                headers = table_rows[0]
                samples = table_rows[1:10]
                mapping, conf = self.matcher.match_columns(headers, samples)

                if 'description' in mapping or 'step_id' in mapping:
                    steps = []
                    for r_idx, r in enumerate(table_rows[1:]):
                        if not any(r):
                            continue
                        step_id = r[mapping['step_id']] if 'step_id' in mapping and mapping['step_id'] < len(r) else f"{base_name}.{r_idx+1:02d}"
                        desc = r[mapping['description']] if 'description' in mapping and mapping['description'] < len(r) else ""
                        role = r[mapping['role']] if 'role' in mapping and mapping['role'] < len(r) else None
                        expected = r[mapping['expected_result']] if 'expected_result' in mapping and mapping['expected_result'] < len(r) else None
                        
                        source_ref = SourceRef(
                            file_path=os.path.abspath(file_path),
                            format="docx",
                            row_index=r_idx + 2,
                            cell_refs={k: f"table_{t_idx}_cell_{v}_{r_idx+2}" for k, v in mapping.items()}
                        )

                        steps.append(CanonicalStep(
                            id=step_id,
                            sequence=len(steps) + 1,
                            role=role,
                            raw_text=desc or "<blank>",
                            expected_result=expected,
                            source_ref=source_ref
                        ))

                    if steps:
                        scripts.append(CanonicalScript(
                            script_id=f"{base_name}_table_{t_idx+1}",
                            title=f"{base_name} Table {t_idx+1}",
                            steps=steps,
                            source_file=os.path.abspath(file_path)
                        ))

        # 2. If no tables or prose doc, parse paragraphs
        if not scripts:
            steps = []
            title = base_name.replace('_', ' ').title()
            for p_idx, p in enumerate(doc.paragraphs):
                text = p.text.strip()
                if not text:
                    continue

                # Skip header/title paragraphs
                if p_idx == 0 and ('script' in text.lower() or 'test' in text.lower()):
                    title = text
                    continue
                if text.lower().startswith('test case:'):
                    continue

                # Detect numbered or bulleted step: "Step 1: Click Login" or "1. ..."
                m = re.match(r'^(?:step\s*)?(\d+|[A-Z0-9_\-\.]+)[.:\s\)]\s*(.*)', text, re.IGNORECASE)
                if m:
                    step_id = m.group(1)
                    desc = m.group(2)
                else:
                    step_id = f"{base_name}.{len(steps)+1:02d}"
                    desc = text

                source_ref = SourceRef(
                    file_path=os.path.abspath(file_path),
                    format="docx",
                    row_index=p_idx + 1,
                    metadata={"paragraph_index": p_idx}
                )

                steps.append(CanonicalStep(
                    id=step_id,
                    sequence=len(steps) + 1,
                    raw_text=desc,
                    source_ref=source_ref
                ))

            if steps:
                scripts.append(CanonicalScript(
                    script_id=base_name,
                    title=title,
                    steps=steps,
                    source_file=os.path.abspath(file_path)
                ))

        return scripts
