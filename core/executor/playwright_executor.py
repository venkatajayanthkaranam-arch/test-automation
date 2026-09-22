"""
Oracle Fusion Cloud — Advanced Universal Autonomous Navigator & Executor
Fully supports Oracle IDCS Single Sign-On, Redwood Springboard life cycle,
and dynamic whole-page scanning across all tabs, tiles, subtabs, and work areas.
"""

import os, yaml, asyncio, logging, re
from typing import Dict, Any, Optional, List
from playwright.async_api import (
    async_playwright, Browser, Page, TimeoutError as PWTimeout
)
from core.models.schema import (
    CanonicalScript, CanonicalStep, CanonicalAction, ActionType, StepStatus
)
from core.executor.fusion_sync import FusionSynchronizer

logger = logging.getLogger("executor")

ORACLE_TOP_TABS = [
    "My Team", "My Client Groups", "HR Group", "Me", "Procurement",
    "Sales", "Redwood Sales", "Service", "Help Desk", "Tools",
    "Supply Chain", "Finance", "Projects", "Analytics", "Home"
]

class PlaywrightFusionExecutor:
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = config_dir or os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..', 'config')
        )
        self.repo = self._load_object_repo()
        self.browser: Optional[Browser] = None

    def _load_object_repo(self) -> Dict[str, Any]:
        p = os.path.join(self.config_dir, "object_repo.yaml")
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                return {}
        return {}

    async def execute_batch(
        self,
        scripts: List[CanonicalScript],
        env_config: Dict[str, Any],
        browser_type: str = "chromium",
        headless: bool = True
    ) -> List[CanonicalScript]:

        raw_url  = env_config.get("base_url", "").strip()
        username = env_config.get("username", "").strip()
        password = env_config.get("password", "").strip()

        if raw_url.startswith("http://"):
            base_url = "https://" + raw_url[7:]
        elif raw_url and not raw_url.startswith("https://"):
            base_url = "https://" + raw_url
        else:
            base_url = raw_url

        total_pass = total_fail = 0
        logger.info(f"[EXEC] {browser_type} headless={headless}  URL={base_url}  user={username}")

        async with async_playwright() as p:
            launcher = getattr(p, browser_type.lower(), p.chromium)
            self.browser = await launcher.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled",
                      "--no-sandbox", "--disable-setuid-sandbox",
                      "--disable-infobars", "--window-size=1440,900"]
            )
            try:
                ctx = await self.browser.new_context(
                    viewport={"width": 1440, "height": 900},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                    ),
                    ignore_https_errors=True, locale="en-US"
                )
                await ctx.add_init_script(
                    "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
                )
                page = await ctx.new_page()

                # Login & stabilize dashboard
                if base_url:
                    try:
                        logger.info(f"[EXEC] Opening {base_url}")
                        await page.goto(base_url, timeout=60000, wait_until="networkidle")
                        await self._do_login(page, username, password, base_url)
                    except Exception as e:
                        logger.error(f"[EXEC] Login failed: {e}")
                        for sc in scripts:
                            for st in sc.steps:
                                st.status = StepStatus.FAIL
                                st.observed_result = f"Login failed: {e}"
                        return scripts

                for si, script in enumerate(scripts):
                    logger.info(f"[EXEC] Sheet [{si+1}/{len(scripts)}]: {script.script_id} ({len(script.steps)} steps)")
                    for xi, step in enumerate(script.steps):
                        st = await self._execute_step(page, step, xi, len(script.steps), script.script_id)
                        if st == StepStatus.PASS:
                            total_pass += 1
                        else:
                            total_fail += 1
            finally:
                await self.browser.close()
                logger.info(f"[EXEC] DONE  PASS={total_pass}  FAIL={total_fail}")

        return scripts

    async def _do_login(self, page: Page, username: str, password: str, base_url: str):
        """Robust Oracle Cloud & IDCS authentication handler."""
        # 1. Fill Username (standard or IDCS nested input)
        user_input = page.locator("#idcs-signin-basic-signin-form-username input, input[name='username'], input[name='userid'], #userid, input[type='text']").first
        if await user_input.is_visible(timeout=6000):
            if username:
                await user_input.fill(username)
        else:
            idcs_user = page.locator("#idcs-signin-basic-signin-form-username").first
            if await idcs_user.is_visible(timeout=3000):
                await idcs_user.click()
                if username:
                    await page.keyboard.type(username)

        # 2. Fill Password (standard or IDCS nested input)
        pass_input = page.locator("#idcs-signin-basic-signin-form-password input, input[name='password'], input[type='password'], #password").first
        if await pass_input.is_visible(timeout=4000):
            if password:
                await pass_input.fill(password)
        else:
            idcs_pass = page.locator("#idcs-signin-basic-signin-form-password").first
            if await idcs_pass.is_visible(timeout=3000):
                await idcs_pass.click()
                if password:
                    await page.keyboard.type(password)

        # 3. Submit
        sign_btn = page.locator("#idcs-signin-basic-signin-form-submit, #btnActive, button[type='submit'], input[type='submit'], button:has-text('Sign In')").first
        if await sign_btn.is_visible(timeout=4000):
            await sign_btn.click()
            logger.info("[EXEC] Signed in. Waiting for dashboard...")
            await asyncio.sleep(8)

        # 4. Stabilize to FuseWelcome Springboard Dashboard
        fuse_url = base_url.rstrip("/") + "/fscmUI/faces/FuseWelcome"
        if "FuseWelcome" not in page.url:
            try:
                await page.goto(fuse_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(4)
            except Exception:
                pass

        await FusionSynchronizer.wait_for_fusion_idle(page)

    async def _execute_step(
        self, page: Page, step: CanonicalStep,
        idx: int, total: int, sheet_id: str
    ) -> StepStatus:
        step.status = StepStatus.IN_PROGRESS
        if not step.parsed_actions:
            step.status = StepStatus.FAIL
            step.observed_result = "No actions parsed from step"
            logger.warning(f"[EXEC]   NO_ACTION [{sheet_id}] step {idx+1}/{total}: {step.id}")
            return StepStatus.FAIL

        try:
            for act in step.parsed_actions:
                await self._dispatch(act, page, step)
                await FusionSynchronizer.wait_for_fusion_idle(page)

            step.status = StepStatus.PASS
            step.observed_result = "Step executed successfully on Oracle Cloud"
            step.notes = "Live Playwright session"
            logger.info(f"[EXEC]   PASS [{sheet_id}] {idx+1}/{total}: {step.id}")
            return StepStatus.PASS

        except Exception as e:
            step.status = StepStatus.FAIL
            step.observed_result = f"FAILED: {e}"
            step.notes = f"Exception: {type(e).__name__}"
            logger.error(f"[EXEC]   FAIL [{sheet_id}] step {idx+1}/{total}: {step.id} => {e}")
            return StepStatus.FAIL

    async def _dispatch(self, act: CanonicalAction, page: Page, step: CanonicalStep):
        t = act.action_type
        target = (act.target or "").strip()
        value = (act.value or "").strip()

        if t == ActionType.LOGIN:
            return

        elif t == ActionType.NAVIGATE:
            menu_path = act.parameters.get("menu_path", [target]) if act.parameters else [target]
            await self._universal_oracle_navigate(page, menu_path)

        elif t == ActionType.CLICK:
            if not target:
                raise Exception("CLICK has no target")
            await self._smart_click(page, target)

        elif t == ActionType.ENTER_TEXT:
            fill_val = value or step.test_data or "AutoValue"
            if not target:
                raise Exception("ENTER_TEXT has no target field")
            await self._smart_fill(page, target, fill_val)

        elif t == ActionType.SELECT_OPTION:
            sel_val = value or step.test_data or ""
            if not sel_val:
                sel_val = "<FIRST_AVAILABLE>"
            await self._smart_select(page, target, sel_val)

        elif t == ActionType.VERIFY:
            verify_text = value or target
            if not verify_text:
                raise Exception("VERIFY has no text to check")
            found = await self._smart_verify(page, verify_text)
            if not found:
                raise Exception(
                    f"'{verify_text}' not found on Oracle page — "
                    f"element or data may not exist in this instance."
                )

        elif t == ActionType.WAIT:
            secs = float(value) if value and value.replace('.', '', 1).isdigit() else 1.0
            await asyncio.sleep(min(secs, 15.0))

    async def _universal_oracle_navigate(self, page: Page, menu_path: list):
        """Universally scans all tabs, tiles, subtabs, and work areas."""
        if not menu_path:
            return

        path = [p.strip() for p in menu_path if p and p.strip()]
        target = path[-1]
        parent = path[0] if len(path) > 1 else None

        logger.info(f"[NAV] Universally locating '{target}'" + (f" (hint: '{parent}')" if parent else ""))

        # 1. Direct visual check on current view
        if await self._click_target_tile(page, target):
            logger.info(f"[NAV] Target '{target}' clicked on current view")
            return

        # 2. Try parent tab first
        if parent:
            clicked_parent = await self._click_top_tab(page, parent)
            if clicked_parent:
                await asyncio.sleep(1.5)
                if await self._click_target_tile(page, target):
                    logger.info(f"[NAV] Found and clicked '{target}' under '{parent}'")
                    return

        # 3. Dynamic scan across all candidate tabs (My Team, My Client Groups, Me, Procurement, etc.)
        for tab in ORACLE_TOP_TABS:
            if not parent or tab.lower() != parent.lower():
                if await self._click_top_tab(page, tab):
                    await asyncio.sleep(1.2)
                    if await self._click_target_tile(page, target):
                        logger.info(f"[NAV] Located '{target}' under tab '{tab}'!")
                        return

        # 4. Fallback: Navigator Drawer
        for hs in ["a[title='Navigator']", "button[aria-label='Navigator']", "[data-afr-icon='menu']"]:
            try:
                ham = page.locator(hs).first
                if await ham.is_visible(timeout=1000):
                    await ham.click(timeout=2000)
                    await asyncio.sleep(1.0)
                    item = page.locator(f"a:has-text('{target}'), span:has-text('{target}')").first
                    if await item.is_visible(timeout=3000):
                        await item.click(timeout=4000)
                        await FusionSynchronizer.wait_for_fusion_idle(page)
                        return
            except Exception:
                continue

        raise Exception(
            f"Navigation target '{target}' not found in Oracle Fusion after full page and tab scan."
        )

    async def _click_target_tile(self, page: Page, target: str) -> bool:
        """Tries to find and click an app tile, card, or link with the target text."""
        try:
            loc = page.get_by_text(target, exact=True).first
            if await loc.is_visible(timeout=1200):
                await loc.click(timeout=4000)
                await FusionSynchronizer.wait_for_fusion_idle(page)
                return True
        except Exception:
            pass

        selectors = [
            f"[title='{target}']",
            f"[aria-label='{target}']",
            f".app-tile:has-text('{target}')",
            f".oj-flex-item:has-text('{target}')",
            f"div.oj-navigationlist-item-label:has-text('{target}')",
            f"a:has-text('{target}')",
            f"button:has-text('{target}')",
            f"span:has-text('{target}')"
        ]
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.is_visible(timeout=1000):
                    await loc.click(timeout=4000)
                    await FusionSynchronizer.wait_for_fusion_idle(page)
                    return True
            except Exception:
                continue

        return False

    async def _click_top_tab(self, page: Page, tab_name: str) -> bool:
        tab_clean = tab_name.strip()
        for sel in [
            f"[role='tab']:has-text('{tab_clean}')",
            f"a.oj-tabbar-item-label:has-text('{tab_clean}')",
            f"a:has-text('{tab_clean}')",
            f"span:has-text('{tab_clean}')",
            f"button:has-text('{tab_clean}')"
        ]:
            try:
                loc = page.locator(sel).first
                if await loc.is_visible(timeout=1200):
                    await loc.click(timeout=3000)
                    await asyncio.sleep(1.0)
                    return True
            except Exception:
                continue
        return False

    async def _smart_click(self, page: Page, target: str):
        safe = target.replace("'", "\\'")
        
        for role in ["button", "link", "tab", "menuitem"]:
            try:
                loc = page.get_by_role(role, name=re.compile(f"^{re.escape(target)}$", re.IGNORECASE)).first
                if await loc.is_visible(timeout=1500):
                    await loc.click(timeout=4000)
                    return
            except Exception:
                continue

        strategies = [
            f"button:has-text('{safe}')",
            f"a:has-text('{safe}')",
            f"[aria-label='{safe}']",
            f"[aria-label*='{safe}']",
            f"[title='{safe}']",
            f"span:has-text('{safe}')",
            f"[role='tab']:has-text('{safe}')",
            f"[role='button']:has-text('{safe}')",
        ]
        for sel in strategies:
            try:
                loc = page.locator(sel).first
                if await loc.is_visible(timeout=1500):
                    await loc.click(timeout=4000)
                    return
            except Exception:
                continue

        raise Exception(f"Element '{target}' not found on Oracle page. Button/tab/tile may not exist or page may not have loaded.")

    async def _smart_fill(self, page: Page, field: str, value: str):
        safe = field.replace("'", "\\'")
        strategies = [
            f"input[aria-label='{safe}']",
            f"input[aria-label*='{safe}']",
            f"input[placeholder='{safe}']",
            f"input[placeholder*='{safe}']",
            f"input[name*='{safe}']",
            f"textarea[aria-label*='{safe}']",
            f"input:near(:text('{safe}'))"
        ]
        for sel in strategies:
            try:
                loc = page.locator(sel).first
                if await loc.is_visible(timeout=1500):
                    await loc.click(timeout=2000)
                    await loc.fill(value, timeout=3000)
                    return
            except Exception:
                continue

        raise Exception(f"Input field '{field}' not found on Oracle page.")

    async def _smart_select(self, page: Page, field: str, value: str):
        safe_f = field.replace("'", "\\'")

        # 1. Native select
        for sel in [f"select[aria-label='{safe_f}']", f"select[aria-label*='{safe_f}']", f"select[name*='{safe_f}']"]:
            try:
                loc = page.locator(sel).first
                if await loc.is_visible(timeout=1500):
                    if value == "<FIRST_AVAILABLE>":
                        opts = await loc.evaluate("el => Array.from(el.options).map(o => o.text).filter(t => t.trim())")
                        if opts:
                            await loc.select_option(label=opts[0], timeout=4000)
                            return
                    else:
                        await loc.select_option(label=value, timeout=4000)
                        return
            except Exception:
                continue

        # 2. Oracle combobox / dropdown
        combo_sels = [
            f"[role='combobox'][aria-label='{safe_f}']",
            f"[role='combobox'][aria-label*='{safe_f}']",
            f"input[role='combobox'][aria-label*='{safe_f}']",
            f"input.oj-combobox-input[aria-label*='{safe_f}']",
            f"[role='combobox']"
        ]
        for sel in combo_sels:
            try:
                loc = page.locator(sel).first
                if await loc.is_visible(timeout=1500):
                    await loc.click(timeout=2000)
                    if value != "<FIRST_AVAILABLE>":
                        await loc.fill(value, timeout=2000)
                        await asyncio.sleep(0.5)
                        opt = page.locator(f"[role='option']:has-text('{value}'), li:has-text('{value}')").first
                        if await opt.is_visible(timeout=3000):
                            await opt.click(timeout=3000)
                            return
                    else:
                        opt = page.locator("[role='option'], li.oj-listbox-result").first
                        if await opt.is_visible(timeout=2500):
                            await opt.click(timeout=3000)
                            return
            except Exception:
                continue

        raise Exception(f"Dropdown '{field}' not found on Oracle page.")

    async def _smart_verify(self, page: Page, text: str) -> bool:
        t = text.strip()
        if not t:
            return True
        try:
            loc = page.get_by_text(t, exact=False).first
            if await loc.is_visible(timeout=3000):
                return True
        except Exception:
            pass
        try:
            content = await page.content()
            if t.lower() in content.lower():
                return True
        except Exception:
            pass
        return False
