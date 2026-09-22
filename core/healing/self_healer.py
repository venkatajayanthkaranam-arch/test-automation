import os
import yaml
import json
from typing import Dict, Any, Optional, List

class SelfHealingEngine:
    """
    Oracle Fusion Self-Healing Engine:
    When locators shift or fail after an Oracle quarterly patch,
    inspects accessibility tree, semantic roles, and proposes object repository patches.
    """

    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = repo_path or os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'object_repo.yaml'))
        self.patch_log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'healed_patches.json'))

    async def attempt_healing(self, target_name: str, page) -> Optional[Any]:
        try:
            snapshot = await page.accessibility.snapshot()
            candidates = self._search_accessibility(snapshot, target_name)
            if candidates:
                best = candidates[0]
                healed_loc = page.get_by_role(best["role"], name=best["name"])
                if await healed_loc.first.is_visible(timeout=2000):
                    self._record_healed_strategy(target_name, {"type": "role", "value": f"{best['role']}[name='{best['name']}']"})
                    return healed_loc.first
        except Exception:
            pass

        try:
            loc = page.get_by_text(target_name, exact=False).first
            if await loc.is_visible(timeout=1500):
                self._record_healed_strategy(target_name, {"type": "text", "value": target_name})
                return loc
        except Exception:
            pass

        return None

    def _search_accessibility(self, node: Dict[str, Any], query: str) -> List[Dict[str, str]]:
        results = []
        if not node:
            return results

        name = node.get("name", "")
        role = node.get("role", "")
        if name and query.lower() in name.lower() and role in ["button", "link", "menuitem", "tab", "textbox", "combobox"]:
            results.append({"role": role, "name": name})

        for child in node.get("children", []):
            results.extend(self._search_accessibility(child, query))

        return results

    def _record_healed_strategy(self, logical_name: str, new_strategy: Dict[str, str]):
        patches = {}
        if os.path.exists(self.patch_log_path):
            try:
                with open(self.patch_log_path, 'r', encoding='utf-8') as f:
                    patches = json.load(f)
            except Exception:
                patches = {}

        if logical_name not in patches:
            patches[logical_name] = []
        
        if new_strategy not in patches[logical_name]:
            patches[logical_name].append(new_strategy)

        try:
            with open(self.patch_log_path, 'w', encoding='utf-8') as f:
                json.dump(patches, f, indent=2)
        except Exception:
            pass
