import re
from typing import List, Dict, Any, Optional
from core.models.schema import (
    CanonicalStep, CanonicalAction, ActionType, ConfidenceTier
)

class StepInterpreter:
    def __init__(self):
        self.split_regex = re.compile(
            r'(\s*(?:→|->|;|\bthen\b|\band\s+(?:then\s+)?(?:click|select|enter|type|navigate|open|choose|verify)\b)\s*)',
            re.IGNORECASE
        )

    def split_compound_step(self, step: CanonicalStep) -> List[CanonicalStep]:
        raw = step.raw_text.strip()
        if not raw:
            return [step]

        parts = self._split_text(raw)
        if len(parts) <= 1:
            step.is_compound = False
            step.parsed_actions = self.interpret_action(raw, step.test_data, step.expected_result)
            step.confidence_score = min([a.confidence for a in step.parsed_actions]) if step.parsed_actions else 0.95
            step.confidence_tier = self._calc_tier(step.confidence_score, raw)
            return [step]

        step.is_compound = True
        sub_steps: List[CanonicalStep] = []
        for idx, part in enumerate(parts):
            sub_id = f"{step.id}.{idx+1}" if "." in step.id else f"{step.id}_{idx+1}"
            actions = self.interpret_action(part, step.test_data if idx == 0 else None, step.expected_result if idx == len(parts)-1 else None)
            conf = min([a.confidence for a in actions]) if actions else 0.90
            tier = self._calc_tier(conf, part)

            sub_step = CanonicalStep(
                id=sub_id,
                sequence=idx + 1,
                role=step.role,
                process_step=step.process_step,
                raw_text=part,
                test_data=step.test_data if idx == 0 else None,
                expected_result=step.expected_result if idx == len(parts)-1 else None,
                status=step.status,
                confidence_tier=tier,
                confidence_score=conf,
                parsed_actions=actions,
                source_ref=step.source_ref
            )
            sub_steps.append(sub_step)

        step.sub_steps = sub_steps
        step.parsed_actions = [act for s in sub_steps for act in s.parsed_actions]
        step.confidence_score = min([s.confidence_score for s in sub_steps]) if sub_steps else 0.9
        step.confidence_tier = self._calc_tier(step.confidence_score, raw)
        return [step]

    def _split_text(self, text: str) -> List[str]:
        if "→" in text or "->" in text:
            parts = [p.strip() for p in re.split(r'→|->', text) if p.strip()]
            return parts

        m_login = re.match(r'^(Login\s+as\s+[^,]+?)\s+and\s+(click\s+.*)$', text, re.IGNORECASE)
        if m_login:
            return [m_login.group(1).strip(), m_login.group(2).strip()]

        splits = self.split_regex.split(text)
        parts = []
        curr = ""
        for token in splits:
            if not token:
                continue
            if self.split_regex.match(token):
                if curr.strip():
                    parts.append(curr.strip())
                m_act = re.search(r'\b(click|select|enter|type|navigate|open|choose|verify)\b', token, re.IGNORECASE)
                if m_act:
                    curr = m_act.group(1) + " "
                else:
                    curr = ""
            else:
                curr += token

        if curr.strip():
            parts.append(curr.strip())

        return parts if len(parts) > 1 else [text]

    def interpret_action(self, text: str, test_data: Optional[str] = None, expected: Optional[str] = None) -> List[CanonicalAction]:
        text_clean = text.strip()
        t_lower = text_clean.lower()

        # 1. LOGIN
        m_login = re.search(r'log\s*in\s+(?:as\s+)?([a-zA-Z0-9_\s]+?)(?:\s+and|\s+to|\.|$)', t_lower)
        if m_login or 'sign in' in t_lower:
            role_target = m_login.group(1).strip() if m_login else "default_user"
            return [CanonicalAction(
                action_type=ActionType.LOGIN,
                target=role_target,
                logical_name=f"Login_{role_target.replace(' ', '_')}",
                confidence=0.98,
                rationale=f"Login detected for role: {role_target}"
            )]

        # 2. NAVIGATE
        m_nav = re.search(r'navigate\s+to\s+([^\.]+?)(?:\s+under\s+[\'"]?([^\'"]+)[\'"]?|\.|$)', text_clean, re.IGNORECASE)
        if m_nav or 'go to' in t_lower:
            target = m_nav.group(1).strip() if m_nav else text_clean
            parent = m_nav.group(2).strip() if (m_nav and m_nav.group(2)) else None
            menu_path = [parent, target] if parent else [target]
            return [CanonicalAction(
                action_type=ActionType.NAVIGATE,
                target=target,
                logical_name=f"Nav_{target.replace(' ', '_')}",
                parameters={"menu_path": menu_path},
                confidence=0.95,
                rationale=f"Menu navigation path: {' -> '.join(menu_path)}"
            )]

        # 3. CLICK
        m_click = re.search(r'click\s+(?:on\s+)?(?:the\s+)?([\'"]?[^\'"]+?[\'"]?)(?:\s+(?:button|tile|icon|link|tab|checkbox|task|radio))?(?:\s+to\s+.*|\.|$)', text_clean, re.IGNORECASE)
        if m_click or t_lower.startswith('click') or t_lower.startswith('select'):
            raw_target = m_click.group(1).strip().strip("'\"") if m_click else text_clean.replace('click', '').strip()
            elem_type = "button"
            if 'bell' in raw_target.lower() or 'notification' in raw_target.lower():
                elem_type = "bell_notification_icon"
                raw_target = "Bell Notifications"
            elif 'tile' in t_lower or 'card' in t_lower:
                elem_type = "quick_action_tile"
            elif 'link' in t_lower:
                elem_type = "hyperlink"

            return [CanonicalAction(
                action_type=ActionType.CLICK,
                target=raw_target,
                logical_name=f"Click_{elem_type}_{raw_target.replace(' ', '_')[:30]}",
                parameters={"element_type": elem_type},
                confidence=0.95,
                rationale=f"Click interaction for {elem_type}: '{raw_target}'"
            )]

        # 4. ENTER / TYPE
        m_enter = re.search(r'(?:enter|type|fill|input|set)\s+(?:the\s+)?([\'"]?[^\'"]+?[\'"]?)\s+(?:as|with|to|=|:)\s+([\'"]?[^\'"]+[\'"]?)', text_clean, re.IGNORECASE)
        if m_enter or 'enter' in t_lower or 'type' in t_lower:
            if m_enter:
                field_name = m_enter.group(1).strip().strip("'\"")
                val = m_enter.group(2).strip().strip("'\"")
            else:
                field_name = text_clean
                val = test_data if test_data and test_data != '<blank>' else "AutoGenerated_Value"

            return [CanonicalAction(
                action_type=ActionType.ENTER_TEXT,
                target=field_name,
                value=val,
                logical_name=f"Input_{field_name.replace(' ', '_')[:30]}",
                confidence=0.93,
                rationale=f"Input '{val}' into field '{field_name}'"
            )]

        # 5. VERIFY
        if 'notice' in t_lower or 'verify' in t_lower or 'check' in t_lower or 'assert' in t_lower:
            m_status = re.search(r'(?:has\s+changed\s+to|is\s+|displays?\s+)([\'"]?[^\'"]+[\'"]?)', text_clean, re.IGNORECASE)
            expected_val = m_status.group(1).strip().strip("'\"") if m_status else (expected or text_clean)
            return [CanonicalAction(
                action_type=ActionType.VERIFY,
                target=text_clean,
                value=expected_val,
                logical_name="Verify_State",
                confidence=0.92,
                rationale=f"Verification of status/message: '{expected_val}'"
            )]

        return [CanonicalAction(
            action_type=ActionType.CUSTOM,
            target=text_clean,
            value=test_data,
            confidence=0.85,
            rationale=f"Generic automated execution for: {text_clean}"
        )]

    def _calc_tier(self, score: float, text: str) -> ConfidenceTier:
        t_low = text.lower()
        if 'captcha' in t_low or 'otp' in t_low or 'scan qr' in t_low:
            return ConfidenceTier.NEEDS_HUMAN
        if score >= 0.85:
            return ConfidenceTier.AUTO_RUNNABLE
        elif score >= 0.65:
            return ConfidenceTier.RUNNABLE_VERIFY_TARGET
        return ConfidenceTier.NEEDS_HUMAN
