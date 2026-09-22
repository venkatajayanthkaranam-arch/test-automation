import os
from typing import List, Optional
from core.models.schema import CanonicalScript
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
