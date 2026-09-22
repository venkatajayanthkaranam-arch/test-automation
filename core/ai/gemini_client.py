"""
Gemini Client — Google Cloud Vertex AI Integration
Using Vertex AI OpenAPI-compatible endpoint with Service Account credentials.
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional
import requests
from google.oauth2 import service_account
import google.auth.transport.requests

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
            # Test token generation & probe
            token = self._get_token()
            if token:
                # Probe Vertex AI endpoint
                test_res = self.generate("Say OK", max_tokens=10)
                if test_res:
                    self._ready = True
                    logger.info(f"Gemini ready via Vertex AI — {self._project_id}/{self._location}/{self._model_name}")
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

    def interpret_test_step(self, raw_step: str, context: str = "") -> Dict[str, Any]:
        """Interpret an Oracle Fusion test step into structured browser actions."""
        if not self.available:
            return {"actions": [], "confidence": 0.5, "source": "fallback"}

        prompt = f"""You are an expert Oracle Fusion Cloud test automation engineer.
Analyze this test step and extract structured Playwright browser actions.

TEST STEP: {raw_step}
{f'CONTEXT: {context}' if context else ''}

Return ONLY valid JSON (no markdown):
{{
  "actions": [
    {{"type": "navigate|click|fill|select|assert|wait", "target": "selector or description", "value": "optional", "description": "human readable"}}
  ],
  "confidence": 0.0-1.0,
  "notes": "Oracle Fusion handling notes"
}}

Oracle Fusion hints:
- Login: username field #userid, password field #password, Sign In button
- Navigation: hamburger menu, Navigator, breadcrumbs, role-based tiles
- Approvals: notification bell icon, approve/reject buttons in workflow
- ADF/JET: use aria-label, data-automation-id, role attributes for locators"""

        try:
            raw = self.generate(prompt, temperature=0.05, max_tokens=800)
            if not raw:
                return {"actions": [], "confidence": 0.3, "source": "gemini_empty"}
            if "```" in raw:
                raw = raw.split("```")[1].lstrip("json\n").split("```")[0]
            result = json.loads(raw.strip())
            result["source"] = "gemini"
            return result
        except json.JSONDecodeError:
            return {"actions": [], "confidence": 0.4, "source": "gemini_parse_error"}
        except Exception as e:
            return {"actions": [], "confidence": 0.5, "source": "error", "error": str(e)}

    def heal_selector(self, failed_selector: str, page_snapshot: str) -> str:
        if not self.available:
            return ""
        prompt = f"""Oracle Fusion UI selector failed. Suggest best Playwright alternative.
FAILED: {failed_selector}
SNAPSHOT: {page_snapshot[:1500]}
Return ONLY JSON: {{"selector": "...", "strategy": "role|text|css", "confidence": 0.0-1.0}}"""
        try:
            raw = self.generate(prompt, temperature=0.05, max_tokens=200)
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
            "action_required": self._error_hint if not self.available else "",
        }

def get_gemini_client() -> GeminiClient:
    return GeminiClient()
