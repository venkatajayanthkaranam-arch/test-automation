"""
Oracle Fusion Cloud — Step Interpreter
Converts raw Excel test step text into CanonicalAction objects.
Every action type is automated — no manual_required fallback.
"""

import re
import logging
from typing import List, Optional

from core.models.schema import (
    CanonicalStep, CanonicalAction, ActionType,
    ConfidenceTier, StepStatus
)

logger = logging.getLogger("interpreter")


class StepInterpreter:
    def split_compound_step(self, step: CanonicalStep) -> List[CanonicalStep]:
        raw = step.raw_text.strip()
        if not raw:
            return [step]

        parts = self._split_text(raw)
        if len(parts) <= 1:
            step.is_compound = False
            step.parsed_actions = self.interpret_action(raw, step.test_data, step.expected_result)
            step.confidence_score = min(a.confidence for a in step.parsed_actions) if step.parsed_actions else 0.9
            step.confidence_tier = self._calc_tier(step.confidence_score, raw)
            return [step]

        step.is_compound = True
        sub_steps: List[CanonicalStep] = []
        for idx, part in enumerate(parts):
            sub_id = f"{step.id}.{idx+1}" if "." in step.id else f"{step.id}_{idx+1}"
            actions = self.interpret_action(
                part,
                step.test_data if idx == 0 else None,
                step.expected_result if idx == len(parts) - 1 else None
            )
            conf = min(a.confidence for a in actions) if actions else 0.88
            tier = self._calc_tier(conf, part)
            sub_steps.append(CanonicalStep(
                id=sub_id, sequence=idx + 1, role=step.role,
                process_step=step.process_step, raw_text=part,
                test_data=step.test_data if idx == 0 else None,
                expected_result=step.expected_result if idx == len(parts) - 1 else None,
                status=step.status, confidence_tier=tier, confidence_score=conf,
                parsed_actions=actions, source_ref=step.source_ref
            ))

        step.sub_steps = sub_steps
        step.parsed_actions = [a for s in sub_steps for a in s.parsed_actions]
        step.confidence_score = min(s.confidence_score for s in sub_steps) if sub_steps else 0.88
        step.confidence_tier = self._calc_tier(step.confidence_score, raw)
        return [step]

    def _split_text(self, text: str) -> List[str]:
        if u"\u00bb" in text or "->" in text:
            parts = [p.strip() for p in re.split(r"\u00bb|->", text) if p.strip()]
            if len(parts) > 1:
                return parts
        m = re.match(
            r"^(log\s*in\s+(?:as\s+)?[^,]+?)\s+and\s+((?:click|navigate|go\s+to|open|select)\s+.+)$",
            text, re.IGNORECASE
        )
        if m:
            return [m.group(1).strip(), m.group(2).strip()]
        parts = re.split(r"\s*;\s*then\s*|\s*\bthen\s+(?=click|navigate|enter|select|verify)\b", text, flags=re.IGNORECASE)
        if len(parts) > 1:
            return [p.strip() for p in parts if p.strip()]
        return [text]

    def interpret_action(self, text: str, test_data: Optional[str] = None, expected: Optional[str] = None) -> List[CanonicalAction]:
        t  = text.strip()
        tl = t.lower()
        td = (test_data or "").strip()
        if td in ("<blank>", "n/a", "N/A", ""):
            td = ""

        # ── 1. LOGIN ──────────────────────────────────────────────────────────
        if re.search(r"\blog\s*in\b|\bsign\s*in\b|\blogon\b|\blaunch\s+oracle\b", tl):
            role_m = re.search(r"(?:as|with role|with)\s+([A-Za-z0-9 /]+?)(?:\s+and|\s+to|\s+with|$|\.)", t, re.IGNORECASE)
            role_target = role_m.group(1).strip() if role_m else "Oracle User"
            return [CanonicalAction(
                action_type=ActionType.LOGIN, target=role_target,
                logical_name="Login_{}".format(role_target.replace(" ", "_")[:30]),
                confidence=0.97, rationale="Login step: {}".format(role_target)
            )]

        # ── 2. NAVIGATE ───────────────────────────────────────────────────────
        nav_m = re.search(
            r"(?:navigate|go)\s+to\s+['\"]?(.+?)['\"]?"
            r"(?:\s+(?:under|in|within|from)\s+['\"]?(.+?)['\"]?)?(?:\s*$|\.|,)",
            t, re.IGNORECASE
        )
        if nav_m:
            target_nav = nav_m.group(1).strip().strip("'\"")
            parent_nav = nav_m.group(2).strip().strip("'\"") if nav_m.group(2) else None
            menu_path  = [parent_nav, target_nav] if parent_nav else [target_nav]
            return [CanonicalAction(
                action_type=ActionType.NAVIGATE, target=target_nav,
                logical_name="Nav_{}".format("_".join(menu_path).replace(" ", "_")[:40]),
                parameters={"menu_path": menu_path},
                confidence=0.95, rationale="Navigate: {}".format(" > ".join(p for p in menu_path if p))
            )]

        # ── 3. CLICK ─────────────────────────────────────────────────────────
        # "On the X tab, click 'Y'"
        on_tab_m = re.search(
            r"on\s+(?:the\s+)?(.+?)\s+tab[,\s]+click\s+(?:the\s+)?['\"]?(.+?)['\"]?(?:\s*$|\.|,)",
            t, re.IGNORECASE
        )
        if on_tab_m:
            elem = on_tab_m.group(2).strip().strip("'\"")
            return [CanonicalAction(
                action_type=ActionType.CLICK, target=elem,
                logical_name="Click_{}".format(elem.replace(" ", "_")[:30]),
                parameters={"context_tab": on_tab_m.group(1).strip()},
                confidence=0.95, rationale="Click '{}' on {} tab".format(elem, on_tab_m.group(1))
            )]

        click_m = re.search(
            r"(?:click|press|tap|hit)\s+(?:on\s+)?(?:the\s+)?['\"]?(.+?)['\"]?"
            r"(?:\s+(?:button|tab|icon|link|tile|card|checkbox|radio|task|action))?(?:\s*$|\.|,|to\s)",
            t, re.IGNORECASE
        )
        if click_m or re.match(r"^(?:click|press|tap)\b", tl):
            if click_m:
                raw_elem = click_m.group(1).strip().strip("'\"")
            else:
                raw_elem = re.sub(r"^(?:click|press|tap|hit)\s+(?:on\s+)?(?:the\s+)?", "", t, flags=re.IGNORECASE).strip().strip("'\"")
            raw_elem = re.sub(r"\s+(?:button|icon|tab|link|tile|card)$", "", raw_elem, flags=re.IGNORECASE).strip()
            return [CanonicalAction(
                action_type=ActionType.CLICK, target=raw_elem,
                logical_name="Click_{}".format(raw_elem.replace(" ", "_")[:30]),
                confidence=0.95, rationale="Click '{}'".format(raw_elem)
            )]

        # ── 4. SELECT ─────────────────────────────────────────────────────────
        # "Select 'Blank Requisition' in the 'Create Requisition Using' dropdown"
        sel_from_m = re.search(
            r"select\s+['\"]?(.+?)['\"]?\s+(?:from|in|in the|from the)\s+(?:the\s+)?['\"]?(.+?)['\"]?"
            r"(?:\s+(?:drop\s*down|dropdown|list|combobox|field))?(?:\s*$|\.|,)",
            t, re.IGNORECASE
        )
        if sel_from_m:
            val_sel  = sel_from_m.group(1).strip().strip("'\"")
            fld_sel  = sel_from_m.group(2).strip().strip("'\"")
            return [CanonicalAction(
                action_type=ActionType.SELECT_OPTION, target=fld_sel, value=val_sel,
                logical_name="Select_{}".format(fld_sel.replace(" ", "_")[:25]),
                confidence=0.94, rationale="Select '{}' from '{}'".format(val_sel, fld_sel)
            )]

        choose_m = re.search(
            r"(?:choose|pick)\s+['\"]?(.+?)['\"]?\s+(?:from|in)\s+['\"]?(.+?)['\"]?(?:\s*$|\.|,)",
            t, re.IGNORECASE
        )
        if choose_m:
            val_c = choose_m.group(1).strip().strip("'\"")
            fld_c = choose_m.group(2).strip().strip("'\"")
            return [CanonicalAction(
                action_type=ActionType.SELECT_OPTION, target=fld_c, value=val_c,
                logical_name="Select_{}".format(fld_c.replace(" ", "_")[:25]),
                confidence=0.93, rationale="Choose '{}' from '{}'".format(val_c, fld_c)
            )]

        # "Select 'X'" (quoted value, use test_data field hint)
        sel_quoted_m = re.search(r"^select\s+['\"]([^'\"]+)['\"]", t, re.IGNORECASE)
        if sel_quoted_m:
            val_q = sel_quoted_m.group(1).strip()
            fld_q = td if td else val_q
            return [CanonicalAction(
                action_type=ActionType.SELECT_OPTION, target=fld_q, value=val_q,
                logical_name="Select_{}".format(val_q.replace(" ", "_")[:25]),
                confidence=0.90, rationale="Select option '{}'".format(val_q)
            )]

        # "Select the X" / "Select Relevant X from dropdown"
        sel_field_m = re.search(
            r"^select\s+(?:the\s+)?(?:relevant\s+|appropriate\s+)?(.+?)(?:\s+from\s+the\s+drop\s*down|\s+from\s+drop\s*down|\s+drop\s*down|\s+list)?(?:\s*$|\.|,)",
            t, re.IGNORECASE
        )
        if sel_field_m and tl.startswith("select"):
            fld_s = sel_field_m.group(1).strip().rstrip("'\"")
            val_s = td if td else ""
            return [CanonicalAction(
                action_type=ActionType.SELECT_OPTION, target=fld_s, value=val_s,
                logical_name="Select_{}".format(fld_s.replace(" ", "_")[:25]),
                confidence=0.88, rationale="Select '{}' from '{}' dropdown".format(val_s or "value", fld_s)
            )]

        # ── 5. ENTER / TYPE / FILL ────────────────────────────────────────────
        enter_m = re.search(
            r"(?:enter|type|fill\s+in?|input|set|provide)\s+(?:the\s+)?['\"]?(.+?)['\"]?"
            r"(?:\s+(?:as|with|to|in|into|=|:)\s+['\"]?(.+?)['\"]?)?(?:\s*$|\.|,)",
            t, re.IGNORECASE
        )
        if enter_m or re.match(r"^(?:enter|type|fill|input)\b", tl):
            if enter_m:
                fld_e = enter_m.group(1).strip().strip("'\"")
                val_e = enter_m.group(2).strip().strip("'\"") if enter_m.group(2) else td or "AutoValue"
            else:
                fld_e = re.sub(r"^(?:enter|type|fill|input|set|provide)\s+(?:the\s+)?", "", t, flags=re.IGNORECASE).strip().strip("'\"")
                val_e = td or "AutoValue"
            return [CanonicalAction(
                action_type=ActionType.ENTER_TEXT, target=fld_e, value=val_e,
                logical_name="Input_{}".format(fld_e.replace(" ", "_")[:30]),
                confidence=0.93, rationale="Enter '{}' in '{}'".format(val_e, fld_e)
            )]

        # ── 6. UPLOAD ─────────────────────────────────────────────────────────
        if re.search(r"\bupload\b|\battach\b|\battachment\b", tl):
            att_m = re.search(r"(?:upload|attach)\s+(?:the\s+)?['\"]?(.+?)['\"]?(?:\s*$|\.|,)", t, re.IGNORECASE)
            fname = att_m.group(1).strip() if att_m else (td or "attachment")
            return [CanonicalAction(
                action_type=ActionType.UPLOAD, target=fname,
                logical_name="Upload_File", confidence=0.90,
                rationale="Upload file: {}".format(fname)
            )]

        # ── 7. SAVE / SUBMIT / APPROVE / REJECT ──────────────────────────────
        save_m = re.search(r"\b(save|submit|approve|reject|confirm|cancel|close|discard|publish)\b", tl)
        if save_m:
            verb = save_m.group(1).capitalize()
            return [CanonicalAction(
                action_type=ActionType.CLICK, target=verb,
                logical_name="Click_{}_Button".format(verb),
                parameters={"element_type": "action_button"},
                confidence=0.94, rationale="Click {} button".format(verb)
            )]

        # ── 8. WAIT ───────────────────────────────────────────────────────────
        if re.search(r"\bwait\b", tl):
            secs_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s\b)", tl)
            secs   = secs_m.group(1) if secs_m else "2"
            return [CanonicalAction(
                action_type=ActionType.WAIT, target="", value=secs,
                logical_name="Wait", confidence=0.95, rationale="Wait {} s".format(secs)
            )]

        # ── 9. VERIFY — "X appears", "X displays", "The X is..." ─────────────
        appears_m = re.search(
            r"(.+?)\s+(?:appears?|displays?|is\s+shown|is\s+visible|is\s+present|is\s+displayed)(?:\s*$|\.|,)",
            t, re.IGNORECASE
        )
        verify_kw_m = re.search(r"(?:verify|check|confirm|assert|ensure|validate)\s+(?:that\s+)?(.+)", t, re.IGNORECASE)
        notice_m    = re.search(r"(?:notice|observe|note)\s+(.+)", t, re.IGNORECASE)
        state_m     = re.search(r"^the\s+(.+?)\s+is\s+(.+)", t, re.IGNORECASE)

        if appears_m:
            elem_a = re.sub(r"^the\s+", "", appears_m.group(1).strip(), flags=re.IGNORECASE)
            return [CanonicalAction(
                action_type=ActionType.VERIFY, target=elem_a, value=expected or elem_a,
                logical_name="Verify_{}".format(elem_a.replace(" ", "_")[:30]),
                confidence=0.91, rationale="Verify element appears: '{}'".format(elem_a)
            )]
        if verify_kw_m:
            tgt_v = verify_kw_m.group(1).strip()
            return [CanonicalAction(
                action_type=ActionType.VERIFY, target=tgt_v, value=expected or tgt_v,
                logical_name="Verify_State",
                confidence=0.92, rationale="Verify: '{}'".format(tgt_v)
            )]
        if notice_m:
            tgt_n = notice_m.group(1).strip()
            return [CanonicalAction(
                action_type=ActionType.VERIFY, target=tgt_n, value=expected or tgt_n,
                logical_name="Verify_Observe",
                confidence=0.89, rationale="Observe: '{}'".format(tgt_n)
            )]
        if state_m:
            elem_s  = state_m.group(1).strip()
            state_s = state_m.group(2).strip()
            return [CanonicalAction(
                action_type=ActionType.VERIFY, target=elem_s, value=state_s,
                logical_name="Verify_{}".format(elem_s.replace(" ", "_")[:30]),
                confidence=0.90, rationale="Verify '{}' is '{}'".format(elem_s, state_s)
            )]

        # ── 10. SMART FALLBACK — still automated, not manual ─────────────────
        # If text mentions a section/screen/area/form => VERIFY it is visible
        # If text is a short action phrase => try CLICK
        is_observation = bool(re.search(
            r"\b(?:section|area|screen|page|panel|form|tab|window|dialog|popup|"
            r"workspace|work\s+area|module|region|block|group|header|footer)\b"
            r"|\bdefaulted\b|\bsame\s+as\b|\bname\b",
            tl
        ))

        quoted_m = re.search(r"['\"]([^'\"]+)['\"]", t)
        elem_f   = quoted_m.group(1).strip() if quoted_m else t

        if is_observation:
            return [CanonicalAction(
                action_type=ActionType.VERIFY, target=elem_f, value=expected or elem_f,
                logical_name="Verify_{}".format(elem_f.replace(" ", "_")[:30]),
                confidence=0.86, rationale="Auto-verify: '{}'".format(elem_f)
            )]
        else:
            return [CanonicalAction(
                action_type=ActionType.CLICK, target=elem_f,
                logical_name="Click_{}".format(elem_f.replace(" ", "_")[:30]),
                confidence=0.82, rationale="Best-effort click: '{}'".format(elem_f)
            )]

    def _calc_tier(self, score: float, text: str) -> ConfidenceTier:
        tl = text.lower()
        if any(k in tl for k in ["captcha", "otp", "scan qr", "two-factor", "2fa"]):
            return ConfidenceTier.NEEDS_HUMAN
        if score >= 0.85:
            return ConfidenceTier.AUTO_RUNNABLE
        if score >= 0.65:
            return ConfidenceTier.RUNNABLE_VERIFY_TARGET
        return ConfidenceTier.NEEDS_HUMAN
