import asyncio
from typing import Optional

class FusionSynchronizer:
    @staticmethod
    async def wait_for_fusion_idle(page, timeout_ms: int = 15000):
        try:
            glasspane_loc = page.locator("div._afrGlassPane, div.AFBlockingGlassPane")
            count = await glasspane_loc.count()
            if count > 0:
                await glasspane_loc.first.wait_for(state="hidden", timeout=timeout_ms)
        except Exception:
            pass

        try:
            spinner_loc = page.locator("oj-progress-circle, .oj-loading-spinner, .app-busy-indicator")
            if await spinner_loc.count() > 0:
                await spinner_loc.first.wait_for(state="hidden", timeout=timeout_ms)
        except Exception:
            pass

        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
