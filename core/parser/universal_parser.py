import os
from typing import List, Optional
from core.models.schema import CanonicalScript, CanonicalStep, SourceRef, StepStatus, ConfidenceTier
from core.parser.column_matcher import ColumnMatcher
from core.parser.adapters.excel_adapter import ExcelAdapter
from core.parser.adapters.csv_adapter import DelimitedAdapter
from core.parser.adapters.docx_adapter import DocxAdapter
from core.interpreter.intent_parser import StepInterpreter

class UniversalParser:
    def __init__(self, cache_file: Optional[str] = None):
        self.matcher = ColumnMatcher(cache_file=cache_file)
        self.excel_adapter = ExcelAdapter(self.matcher)
        self.csv_adapter = DelimitedAdapter(self.matcher)
        self.docx_adapter = DocxAdapter(self.matcher)
        self.interpreter = StepInterpreter()

    def parse(self, file_path: str, target_script: Optional[str] = None) -> List[CanonicalScript]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        if ext in ['.xlsx', '.xls', '.xlsm']:
            scripts = self.excel_adapter.parse(file_path, target_sheet=target_script)
        elif ext in ['.csv', '.tsv', '.txt']:
            delim = '\t' if ext == '.tsv' else ','
            scripts = self.csv_adapter.parse(file_path, delimiter=delim)
        elif ext in ['.docx']:
            scripts = self.docx_adapter.parse(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        # Post-process with Step Interpreter
        for script in scripts:
            processed_steps = []
            for step in script.steps:
                split_res = self.interpreter.split_compound_step(step)
                processed_steps.extend(split_res)
            script.steps = processed_steps

        return scripts

    def parse_file(self, file_path: str, target_script: Optional[str] = None) -> List[CanonicalScript]:
        """Alias for parse() to support parse_file calls."""
        return self.parse(file_path, target_script=target_script)

    def parse_text(self, text: str, title: str = "Pasted Test Script", fmt: str = "text") -> CanonicalScript:
        """Parses raw text / markdown / tabular text into a CanonicalScript."""
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        steps: List[CanonicalStep] = []

        seq = 1
        for idx, line in enumerate(lines):
            # Ignore headers if looks like table header
            if idx == 0 and ("step" in line.lower() or "description" in line.lower() or "|" in line):
                continue
            if line.startswith("#") or line.startswith("---"):
                continue

            clean_line = line.strip("| \t-")
            if not clean_line:
                continue

            step = CanonicalStep(
                id=f"STEP_{seq:03d}",
                sequence=seq,
                raw_text=clean_line,
                status=StepStatus.NOT_ATTEMPTED,
                confidence_tier=ConfidenceTier.AUTO_RUNNABLE,
                confidence_score=1.0,
                source_ref=SourceRef(file_path="pasted_text", sheet_name="pasted", format="text")
            )
            split_steps = self.interpreter.split_compound_step(step)
            steps.extend(split_steps)
            seq += 1

        return CanonicalScript(
            script_id="PASTED_001",
            title=title,
            source_file="pasted_script.txt",
            steps=steps
        )
