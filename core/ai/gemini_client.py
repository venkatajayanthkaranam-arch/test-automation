"""
Gemini Client - Google Cloud Vertex AI Integration
Enriched with Oracle Fusion Cloud Domain Knowledge Base, Demo/Prod Environment Heuristics,
and Intelligent Self-Healing Locators.
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional
import requests
from google.oauth2 import service_account
import google.auth.transport.requests

try:
    from core.ai.oracle_knowledge import OracleKnowledgeBase
except ImportError:
    from oracle_knowledge import OracleKnowledgeBase

logger = logging.getLogger("gemini")

class GeminiClient:
    _instance: Optional["GeminiClient"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._project_id = os.getenv("GCP_PROJECT_ID", "project-b7e4de28-72cd-4ca3-92a").strip()
        self._location   = os.getenv("GCP_LOCATION", "global").strip()
        self._model_name = os.getenv("GEMINI_MODEL", "google/gemini-2.5-flash").strip()
        if not self._model_name.startswith("google/"):
            self._model_name = f"google/{self._model_name}"

        self._token = None
        self._token_expiry = 0
        self._credentials = None
        self._ready = False
        self._error_hint = ""

        # Resolve service account JSON path
        sa_rel = os.getenv("GCP_SERVICE_ACCOUNT_JSON", "config/gcp_service_account.json")
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        sa_path = sa_rel if os.path.isabs(sa_rel) else os.path.join(root, sa_rel)

        if not os.path.exists(sa_path):
            logger.error(f"Service account JSON not found: {sa_path}")
            return

        try:
            with open(sa_path, "r", encoding="utf-8") as f:
                sa_data = json.load(f)
                if not self._project_id and "project_id" in sa_data:
                    self._project_id = sa_data["project_id"]

            self._credentials = service_account.Credentials.from_service_account_file(
                sa_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            token = self._get_token()
            if token:
                test_res = self.generate("Say OK", max_tokens=10)
                if test_res:
                    self._ready = True
                    logger.info(f"Gemini ready via Vertex AI - {self._project_id}/{self._location}/{self._model_name}")
                else:
                    logger.warning("Vertex AI probe generated empty response")
        except Exception as e:
            logger.error(f"Failed initializing Vertex AI Gemini client: {e}")
            self._error_hint = str(e)

    def _get_token(self) -> Optional[str]:
        """Obtain or refresh Google OAuth2 Bearer token."""
        try:
            if not self._credentials:
                return None
            now = time.time()
            if not self._token or (now >= self._token_expiry - 60):
                req = google.auth.transport.requests.Request()
                self._credentials.refresh(req)
                self._token = self._credentials.token
                self._token_expiry = self._credentials.expiry.timestamp() if self._credentials.expiry else (now + 3500)
            return self._token
        except Exception as e:
            logger.error(f"Error fetching Google access token: {e}")
            return None

    @property
    def available(self) -> bool:
        return self._credentials is not None

    def generate(self, prompt: str, temperature: float = 0.2, max_tokens: int = 2048) -> str:
        """Generate text using Vertex AI OpenAPI-compatible endpoint."""
        token = self._get_token()
        if not token:
            logger.error("No valid Google auth token available")
            return ""

        url = f"https://aiplatform.googleapis.com/v1beta1/projects/{self._project_id}/locations/{self._location}/endpoints/openapi/chat/completions"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self._model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
            else:
                logger.error(f"Vertex AI API error ({resp.status_code}): {resp.text}")
                return ""
        except Exception as e:
            logger.error(f"Vertex AI request failed: {e}")
            return ""
        return ""

    def interpret_test_step(self, raw_step: str, context: str = "", instance_url: str = "") -> Dict[str, Any]:
        """
        Interpret an Oracle Fusion test step into structured browser actions with full domain knowledge,
        demo vs client instance handling, and navigation mapping.
        """
        is_demo = OracleKnowledgeBase.is_demo_instance(instance_url)
        expert_system_prompt = OracleKnowledgeBase.generate_expert_system_prompt()
        nav_info = OracleKnowledgeBase.resolve_navigation_route(raw_step)

        if not self.available:
            # Domain-rule fallback if Gemini is offline
            if nav_info:
                return {
                    "actions": [
                        {"type": "navigate", "target": f"{nav_info['tab_name']} -> {nav_info['tile_name']}", "description": f"Navigate to {nav_info['tile_name']} under {nav_info['tab_name']}"}
                    ],
                    "confidence": 0.95,
                    "source": "oracle_knowledge_base"
                }
            return {"actions": [], "confidence": 0.5, "source": "fallback"}

        prompt = f"""{expert_system_prompt}

ENVIRONMENT CONTEXT:
- Target Oracle Instance: {'Demo / Vision Sandbox (Seed data fallback enabled)' if is_demo else 'Enterprise Production / Client Configured'}
{f'- Pre-mapped Oracle Nav: {json.dumps(nav_info)}' if nav_info else ''}

TEST STEP TO AUTOMATE:
{raw_step}
{f'ADDITIONAL CONTEXT: {context}' if context else ''}

TASK:
Extract the full executable sequence of browser actions for this step.
NEVER mark an action as 'custom' or 'manual'. Transform all business intents into real Playwright steps.
If client-specific data is requested in a Demo instance where that exact name might not exist, specify adaptive selection.

Return ONLY valid JSON (no markdown formatting):
{{
  "actions": [
    {{
      "type": "login|navigate|click|enter_text|select_option|verify|press_key",
      "target": "semantic label, button name, tab name, or input field description",
      "value": "text to enter or option to choose (or fallback option)",
      "description": "human readable explanation of action"
    }}
  ],
  "confidence": 0.95,
  "is_demo_adapted": {str(is_demo).lower()},
  "notes": "Oracle Fusion execution strategy notes"
}}"""

        try:
            raw = self.generate(prompt, temperature=0.05, max_tokens=1000)
            if not raw:
                return {"actions": [], "confidence": 0.3, "source": "gemini_empty"}
            if "```" in raw:
                raw = raw.split("```")[1].lstrip("json\n").split("```")[0]
            result = json.loads(raw.strip())
            result["source"] = "gemini_oracle_expert"
            return result
        except json.JSONDecodeError:
            return {"actions": [], "confidence": 0.4, "source": "gemini_parse_error"}
        except Exception as e:
            return {"actions": [], "confidence": 0.5, "source": "error", "error": str(e)}

    def heal_selector(self, failed_selector: str, page_snapshot: str, step_context: str = "") -> str:
        """Self-heal broken selectors using Oracle Fusion element pattern heuristics."""
        if not self.available:
            return ""
        prompt = f"""Oracle Fusion UI element locator failed during execution.
Suggest the optimal resilient Playwright locator strategy.

FAILED TARGET: {failed_selector}
{f'STEP CONTEXT: {step_context}' if step_context else ''}
PAGE ACCESSIBILITY SNAPSHOT:
{page_snapshot[:2000]}

HINTS FOR ORACLE FUSION (ADF / JET):
- Use aria-label, role-based locators (button, link, tab, combobox, textbox), or text substring matching.
- Avoid dynamic IDs like pt1:_FOr1:...

Return ONLY JSON: {{"selector": "...", "strategy": "role|label|text|css", "confidence": 0.9}}"""
        try:
            raw = self.generate(prompt, temperature=0.05, max_tokens=300)
            if "```" in raw:
                raw = raw.split("```")[1].lstrip("json\n").split("```")[0]
            return json.loads(raw.strip()).get("selector", "")
        except Exception:
            return ""

    def get_model_info(self) -> Dict[str, str]:
        return {
            "provider":  "Google Cloud Vertex AI",
            "backend":   "Vertex AI OpenAPI",
            "model":     self._model_name,
            "project":   self._project_id or "not-configured",
            "location":  self._location,
            "available": str(self.available),
            "oracle_knowledge_base": "Active (Demo & Client Awareness Enriched)",
            "action_required": self._error_hint if not self.available else "",
        }

def get_gemini_client() -> GeminiClient:
    return GeminiClient()
