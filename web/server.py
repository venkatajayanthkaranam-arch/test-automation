import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import shutil
import asyncio
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn

from core.parser.universal_parser import UniversalParser
from core.writeback.excel_writer import ExcelWriteBackEngine
from core.writeback.html_reporter import HtmlReportEngine
from core.models.schema import CanonicalScript, StepStatus
from core.executor.playwright_executor import PlaywrightFusionExecutor

load_dotenv()

logger = logging.getLogger("server")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Oracle Fusion Test Automation Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

if os.path.exists(os.path.join(FRONTEND_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")

parser = UniversalParser()
excel_writer = ExcelWriteBackEngine()
html_reporter = HtmlReportEngine()

CURRENT_SCRIPTS: Dict[str, CanonicalScript] = {}
LATEST_BATCH_SCRIPTS: List[CanonicalScript] = []

class PasteRequest(BaseModel):
    title: Optional[str] = "Pasted Test Script"
    content: str
    format: Optional[str] = "text"

class ExecuteRequest(BaseModel):
    instance_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    browser: Optional[str] = "chromium"
    headless: Optional[bool] = False
    multi_role_mode: Optional[bool] = False
    role_credentials: Optional[Dict[str, Any]] = None

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools_endpoint():
    return JSONResponse({})

@app.get("/favicon.svg")
async def get_favicon():
    fav = os.path.join(FRONTEND_DIST, "favicon.svg")
    if os.path.exists(fav):
        return FileResponse(fav, media_type="image/svg+xml")
    return HTMLResponse("<svg></svg>", media_type="image/svg+xml")

@app.get("/", response_class=HTMLResponse)
async def index():
    dist_index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(dist_index):
        with open(dist_index, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Frontend Loading...</h1>"

@app.get("/api/config")
async def get_config():
    return {
        "ok": True,
        "defaults": {
            "baseUrl": os.getenv("ORACLE_BASE_URL", "https://fa-eubg-test-saasfademo1.ds-fa.oraclepdemos.com"),
            "username": os.getenv("ORACLE_USERNAME", "ramya.dm"),
            "hasStoredPassword": bool(os.getenv("ORACLE_PASSWORD", "").strip()),
            "browser": os.getenv("BROWSER", "chromium"),
            "headless": False
        }
    }

@app.get("/api/screenshots")
async def get_screenshots():
    sc_dir = os.path.join(REPORTS_DIR, "screenshots")
    if not os.path.exists(sc_dir):
        return {"ok": True, "count": 0, "screenshots": []}
    files = [f for f in os.listdir(sc_dir) if f.endswith(('.png', '.jpg'))]
    return {"ok": True, "count": len(files), "screenshots": files}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    global LATEST_BATCH_SCRIPTS, CURRENT_SCRIPTS
    temp_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        scripts = parser.parse_file(temp_path)
        LATEST_BATCH_SCRIPTS = scripts
        for s in scripts:
            CURRENT_SCRIPTS[s.script_id] = s

        total_steps = sum(len(s.steps) for s in scripts)
        return {
            "ok": True,
            "filename": file.filename,
            "sheets_count": len(scripts),
            "total_steps": total_steps,
            "scripts": [s.model_dump() for s in scripts],
        }
    except Exception as e:
        logger.error(f"Parse error on upload: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/paste")
async def paste_script(req: PasteRequest):
    global LATEST_BATCH_SCRIPTS, CURRENT_SCRIPTS
    try:
        script = parser.parse_text(req.content, title=req.title, fmt=req.format)
        CURRENT_SCRIPTS[script.script_id] = script
        LATEST_BATCH_SCRIPTS = [script]
        return {
            "ok": True,
            "script": script.model_dump(),
            "total_steps": len(script.steps),
        }
    except Exception as e:
        logger.error(f"Parse error on paste: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/execute/all")
async def execute_all_scripts(req: ExecuteRequest = Body(default=ExecuteRequest())):
    global LATEST_BATCH_SCRIPTS
    if not LATEST_BATCH_SCRIPTS:
        raise HTTPException(status_code=400, detail="No scripts loaded to execute")

    target_url  = (req.instance_url or os.getenv("ORACLE_BASE_URL", "")).strip()
    target_user = (req.username     or os.getenv("ORACLE_USERNAME", "")).strip()
    target_pass = (req.password     or os.getenv("ORACLE_PASSWORD", "")).strip()
    browser_type = req.browser or "chromium"
    headless     = req.headless if req.headless is not None else False

    logger.info(f"[EXECUTE] Starting LIVE VISIBLE Playwright execution for {len(LATEST_BATCH_SCRIPTS)} scripts")
    logger.info(f"[EXECUTE] Target URL : {target_url}")
    logger.info(f"[EXECUTE] Username   : {target_user}")
    logger.info(f"[EXECUTE] Headless   : {headless} (Visible Browser)")

    executor = PlaywrightFusionExecutor()
    env_config = {
        "base_url": target_url,
        "username": target_user,
        "password": target_pass,
    }

    try:
        executed_scripts = await executor.execute_batch(
            LATEST_BATCH_SCRIPTS,
            env_config=env_config,
            browser_type=browser_type,
            headless=headless,
        )
        LATEST_BATCH_SCRIPTS = executed_scripts
    except Exception as e:
        logger.error(f"[EXECUTE] Playwright batch execution error: {e}")
        for script in LATEST_BATCH_SCRIPTS:
            for step in script.steps:
                if step.status == StepStatus.NOT_ATTEMPTED or step.status == StepStatus.IN_PROGRESS:
                    step.status = StepStatus.FAIL
                    step.observed_result = f"Execution error: {e}"

    # Count results
    total_steps = 0
    passed = 0
    failed = 0
    for script in LATEST_BATCH_SCRIPTS:
        for step in script.steps:
            total_steps += 1
            if step.status == StepStatus.PASS:
                passed += 1
            else:
                failed += 1

    logger.info(f"[EXECUTE] Done. Total={total_steps} | Pass={passed} | Fail={failed}")

    # Excel writeback
    out_xlsx = None
    if LATEST_BATCH_SCRIPTS and LATEST_BATCH_SCRIPTS[0].source_file.endswith(('.xlsx', '.xls')):
        try:
            out_xlsx = excel_writer.write_back(LATEST_BATCH_SCRIPTS)
        except Exception as e:
            logger.warning(f"[EXECUTE] Excel writeback error (non-fatal): {e}")

    # HTML report
    report_file = html_reporter.generate_report(LATEST_BATCH_SCRIPTS)

    return {
        "ok": True,
        "count": len(LATEST_BATCH_SCRIPTS),
        "total_test_cases": len(LATEST_BATCH_SCRIPTS),
        "total_steps_executed": total_steps,
        "passed": passed,
        "failed": failed,
        "scripts": [s.model_dump() for s in LATEST_BATCH_SCRIPTS],
        "excel_download_url": "/api/download/excel" if out_xlsx else None,
        "report_url": f"/reports/{os.path.basename(report_file)}"
    }

@app.post("/api/execute/{script_id}")
async def execute_single_script(script_id: str, req: ExecuteRequest = Body(default=ExecuteRequest())):
    if script_id not in CURRENT_SCRIPTS:
        raise HTTPException(status_code=404, detail="Script not found")

    script = CURRENT_SCRIPTS[script_id]
    target_url  = (req.instance_url or os.getenv("ORACLE_BASE_URL", "")).strip()
    target_user = (req.username     or os.getenv("ORACLE_USERNAME", "")).strip()
    target_pass = (req.password     or os.getenv("ORACLE_PASSWORD", "")).strip()
    browser_type = req.browser or "chromium"
    headless     = req.headless if req.headless is not None else False

    logger.info(f"[EXECUTE] Single script (Visible Browser): {script_id}")

    executor = PlaywrightFusionExecutor()
    env_config = {
        "base_url": target_url,
        "username": target_user,
        "password": target_pass,
    }

    try:
        executed = await executor.execute_batch([script], env_config=env_config, browser_type=browser_type, headless=headless)
        CURRENT_SCRIPTS[script_id] = executed[0]
        script = executed[0]
    except Exception as e:
        logger.error(f"[EXECUTE] Single script error: {e}")
        for step in script.steps:
            if step.status in (StepStatus.NOT_ATTEMPTED, StepStatus.IN_PROGRESS):
                step.status = StepStatus.FAIL
                step.observed_result = f"Execution error: {e}"

    out_xlsx = None
    if script.source_file.endswith(('.xlsx', '.xls')):
        try:
            out_xlsx = excel_writer.write_back(script)
        except Exception:
            pass

    report_file = html_reporter.generate_report(script)

    return {
        "ok": True,
        "script": script.model_dump(),
        "total_test_cases": 1,
        "total_steps_executed": len(script.steps),
        "excel_download_url": "/api/download/excel" if out_xlsx else None,
        "report_url": f"/reports/{os.path.basename(report_file)}"
    }

@app.get("/api/download/excel")
async def download_latest_excel():
    if not LATEST_BATCH_SCRIPTS:
        raise HTTPException(status_code=404, detail="No executed test script found")
    source_file = LATEST_BATCH_SCRIPTS[0].source_file
    base, ext = os.path.splitext(source_file)
    executed_file = f"{base}_executed{ext}"
    if os.path.exists(executed_file):
        return FileResponse(
            executed_file,
            filename=f"Oracle_Fusion_Executed_{os.path.basename(source_file)}",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    raise HTTPException(status_code=404, detail="Executed Excel file not found")
