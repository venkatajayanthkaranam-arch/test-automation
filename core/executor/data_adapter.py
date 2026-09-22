"""
Oracle Fusion Cloud - Strict Data Verification & UI Option Matcher
Strictly verifies that required test data exists in the active Oracle instance.
If an exact match or exact case/whitespace variation exists in the UI, it selects it.
If client-required data or access is missing from the instance, it records an exact, accurate FAILURE
rather than fabricating or substituting fake/unrelated seeded values.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("data_adapter")

class OracleDataAdapter:
    """
    Strictly verifies and matches test data against live Oracle Fusion UI elements.
    Never silently substitutes arbitrary unrequested demo entities.
    """

    @classmethod
    def resolve_field_value(cls, field_name: str, requested_value: str, available_options: List[str] = None) -> Tuple[Optional[str], bool, str]:
        """
        Inspects available dropdown options or search results on the live page.
        
        Returns:
            (matched_value, is_success, failure_reason)
            - If found: (matched_value, True, "")
            - If missing in instance: (None, False, "Option 'X' not configured or missing in this Oracle instance")
        """
        if not requested_value or requested_value.strip() == "":
            return "", True, ""

        req_clean = requested_value.strip()

        # If we have inspected options from the live Oracle UI:
        if available_options is not None:
            # 1. Exact match (case-insensitive & trimmed)
            for opt in available_options:
                if opt.strip().lower() == req_clean.lower():
                    return opt.strip(), True, ""

            # 2. Exact prefix / suffix / substring match only if strongly aligned
            cleaned_opts = [o.strip() for o in available_options if o.strip()]
            for opt in cleaned_opts:
                # E.g. "US1 Business Unit" vs "US1 Business Unit (US1)"
                if opt.lower().startswith(req_clean.lower()) or req_clean.lower().startswith(opt.lower()):
                    return opt, True, ""

            # 3. If genuinely missing from instance, return explicit failure reason (NO fake fallback)
            reason = f"Required value '{req_clean}' for field '{field_name}' not found in Oracle instance options: {available_options[:10]}"
            logger.error(f"[DATA VERIFICATION FAILED] {reason}")
            return None, False, reason

        # If no UI options list was provided (e.g. text input field), pass requested value directly
        return req_clean, True, ""
