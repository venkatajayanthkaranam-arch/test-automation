"""
Oracle Fusion Cloud - Universal Dynamic Live Page Scanner & Visual Locator Engine
Scans and parses the entire live DOM / Accessibility tree dynamically across ANY Oracle Fusion module:
HCM, ERP, SCM, Procurement, Sales, Service, Finance, Tools, Redwood, and Classic ADF UI.

Never relies on hardcoded module names. Discovers and matches elements live in real-time.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from playwright.async_api import Page, ElementHandle

logger = logging.getLogger("page_scanner")

class OraclePageScanner:
    """
    Universally scans live Oracle Fusion pages to dynamically discover and locate
    tabs, springboard tiles, navigation groups, form inputs, buttons, tables, and dialogs.
    """

    @classmethod
    async def scan_navigation_elements(cls, page: Page) -> Dict[str, List[Dict[str, Any]]]:
        """
        Dynamically extracts all interactive navigation elements currently visible on the page:
        - Top horizontal tabs / navigation bars
        - Springboard application tiles
        - Left-side subtabs / accordion sections
        - Quick action links
        """
        scan_result = {
            "tabs": [],
            "tiles": [],
            "links": [],
            "buttons": []
        }

        try:
            # 1. Scan Top Navigation Tabs (e.g., Me, My Team, Procurement, HR Group, Sales, Tools, etc.)
            tabs = await page.query_selector_all("[role='tab'], .oj-navigationlist-item-element, .tab-header, [data-oj-tab]")
            for t in tabs:
                if await t.is_visible():
                    text = (await t.inner_text()).strip()
                    if text:
                        scan_result["tabs"].append({"text": text, "handle": t})

            # 2. Scan Application Tiles / Springboard Cards
            tiles = await page.query_selector_all(".app-tile, .oj-flex-item, [role='link'], .panel-card, .card-title")
            for tile in tiles:
                if await tile.is_visible():
                    text = (await tile.inner_text()).strip()
                    if text and len(text) < 60:
                        scan_result["tiles"].append({"text": text, "handle": tile})

        except Exception as e:
            logger.warning(f"Dynamic navigation scan error: {e}")

        return scan_result

    @classmethod
    async def dynamic_find_and_click(cls, page: Page, target_text: str, context_hint: Optional[str] = None) -> bool:
        """
        Universally resolves and clicks any target element on the live Oracle page using a multi-phase
        dynamic scanner across accessibility roles, visual labels, and contextual parents.
        """
        t_clean = target_text.strip()
        t_lower = t_clean.lower()

        # Phase 1: Direct exact accessibility role match
        for role in ["button", "tab", "link", "menuitem", "option", "treeitem"]:
            try:
                loc = page.get_by_role(role, name=re.compile(f"^{re.escape(t_clean)}$", re.IGNORECASE))
                if await loc.first.is_visible(timeout=1000):
                    await loc.first.click(timeout=3000)
                    return True
            except Exception:
                continue

        # Phase 2: If context hint exists (e.g. "under My Team" or "on Requisitions tab"), scan across tabs first
        if context_hint:
            c_clean = context_hint.strip()
            # Try finding and clicking the context tab first
            for tab_sel in ["[role='tab']", ".oj-navigationlist-item-element", "a", "button"]:
                try:
                    tab_loc = page.locator(tab_sel).filter(has_text=re.compile(f"^{re.escape(c_clean)}$", re.IGNORECASE)).first
                    if await tab_loc.is_visible(timeout=800):
                        await tab_loc.click(timeout=2000)
                        await page.wait_for_timeout(1000)
                        break
                except Exception:
                    continue

        # Phase 3: Dynamic live scan of all visible clickable elements on the page
        clickables = await page.query_selector_all("button, [role='button'], a, [role='link'], [role='tab'], span.oj-button-text, .app-tile, input[type='button'], input[type='submit']")
        
        # Priority A: Exact text match
        for elem in clickables:
            try:
                if await elem.is_visible():
                    txt = (await elem.inner_text()).strip()
                    if txt.lower() == t_lower:
                        await elem.click()
                        return True
            except Exception:
                continue

        # Priority B: Contains substring match
        for elem in clickables:
            try:
                if await elem.is_visible():
                    txt = (await elem.inner_text()).strip()
                    if t_lower in txt.lower():
                        await elem.click()
                        return True
            except Exception:
                continue

        # Phase 4: Aria-label & Title attribute scan
        for attr in ["aria-label", "title", "data-automation-id", "placeholder"]:
            try:
                loc = page.locator(f"[{attr}*='{t_clean}']").first
                if await loc.is_visible(timeout=1000):
                    await loc.click(timeout=2000)
                    return True
            except Exception:
                continue

        return False

    @classmethod
    async def dynamic_find_and_fill(cls, page: Page, field_name: str, value: str) -> bool:
        """
        Dynamically identifies input fields, textareas, and search boxes anywhere on the live Oracle page
        using visual proximity, label association, placeholder text, and aria attributes.
        """
        if not value:
            return True

        f_clean = field_name.strip()

        # 1. Direct label association
        try:
            loc = page.get_by_label(re.compile(f"{re.escape(f_clean)}", re.IGNORECASE))
            if await loc.first.is_visible(timeout=1500):
                await loc.first.click()
                await loc.first.fill(value)
                return True
        except Exception:
            pass

        # 2. Attribute-based queries (aria-label, placeholder, name)
        for attr in ["aria-label", "placeholder", "name", "id"]:
            try:
                loc = page.locator(f"input[{attr}*='{f_clean}'], textarea[{attr}*='{f_clean}']").first
                if await loc.is_visible(timeout=1000):
                    await loc.click()
                    await loc.fill(value)
                    return True
            except Exception:
                continue

        # 3. Proximity search: find input near a text label
        try:
            loc = page.locator(f"input:near(:text('{f_clean}'))").first
            if await loc.is_visible(timeout=1500):
                await loc.click()
                await loc.fill(value)
                return True
        except Exception:
            pass

        return False
