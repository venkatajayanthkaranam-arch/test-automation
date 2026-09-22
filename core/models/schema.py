from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field

class ConfidenceTier(str, Enum):
    AUTO_RUNNABLE = "AUTO_RUNNABLE"
    RUNNABLE_VERIFY_TARGET = "RUNNABLE_VERIFY_TARGET"
    NEEDS_HUMAN = "NEEDS_HUMAN"

class StepStatus(str, Enum):
    NOT_ATTEMPTED = "Not Attempted"
    IN_PROGRESS = "In Progress"
    PASS = "Pass"
    FAIL = "Fail"
    BLOCKED = "Blocked"
    MANUAL_REQUIRED = "Manual Required"

class ActionType(str, Enum):
    CLICK = "click"
    ENTER_TEXT = "enter_text"
    SELECT_OPTION = "select_option"
    NAVIGATE = "navigate"
    VERIFY = "verify"
    LOGIN = "login"
    WAIT = "wait"
    UPLOAD = "upload"
    CUSTOM = "custom"
    MANUAL = "manual"

class SourceRef(BaseModel):
    file_path: str
    format: str
    sheet_name: Optional[str] = None
    row_index: Optional[int] = None
    cell_refs: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CanonicalAction(BaseModel):
    action_type: ActionType
    target: Optional[str] = None
    value: Optional[str] = None
    logical_name: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    rationale: Optional[str] = None

class CanonicalStep(BaseModel):
    id: str
    sequence: int
    role: Optional[str] = None
    process_step: Optional[str] = None
    raw_text: str
    test_data: Optional[str] = None
    expected_result: Optional[str] = None
    observed_result: Optional[str] = None
    status: StepStatus = StepStatus.NOT_ATTEMPTED
    sr_number: Optional[str] = None
    notes: Optional[str] = None
    confidence_tier: ConfidenceTier = ConfidenceTier.AUTO_RUNNABLE
    confidence_score: float = 1.0
    parsed_actions: List[CanonicalAction] = Field(default_factory=list)
    source_ref: SourceRef
    is_compound: bool = False
    sub_steps: List['CanonicalStep'] = Field(default_factory=list)

class DataQualityWarning(BaseModel):
    code: str
    message: str
    severity: str = "WARNING"
    step_id: Optional[str] = None
    row_index: Optional[int] = None

class CanonicalScript(BaseModel):
    script_id: str
    title: str
    description: Optional[str] = None
    system_environment: Optional[str] = None
    tester_name: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    steps: List[CanonicalStep] = Field(default_factory=list)
    warnings: List[DataQualityWarning] = Field(default_factory=list)
    source_file: str
    sheet_name: Optional[str] = None
    template_fingerprint: Optional[str] = None
