# Oracle Cloud Fusion Test Automation Platform

> **Format-Agnostic, Human-Parity Autonomous Browser Test Automation Engine**  
> Built specifically for enterprise Oracle Fusion Cloud ERP/HCM/SCM testing.

---

## 1. Executive Summary & Definition

The **Oracle Cloud Automation Platform** is an enterprise-grade, autonomous test automation system designed to eliminate the manual overhead of executing and maintaining Oracle Fusion Cloud test scripts. 

Unlike traditional test automation tools that require rigid scripts (like Selenium or manual Playwright coding), this platform is **Universal and Format-Agnostic**:
- It ingests manual test scripts written in **any format** (`.xlsx`, `.xls`, `.csv`, `.docx`, `.pdf`, `.md`, or raw copy-pasted text).
- It understands unstructured human instructions (e.g. *"Navigate to Procurement, create purchase order with 5 items, and submit for 1st Approver"*).
- It decomposes complex compound instructions into **atomic Playwright browser sub-actions**.
- It executes tests headlessly or in visible mode against Oracle Cloud instances with **self-healing ADF/JET locators**.
- It captures **timestamped proof screenshots** (e.g., login proof, form submissions, and failures).
- It generates **dual reports**: an **updated Excel file** with direct status write-back and a rich, interactive **Executive HTML Report**.

---

## 2. Architecture & Tech Stack

```
┌────────────────────────────────────────────────────────────────────────────┐
│                             REACT WEB STUDIO UI                            │
│    (3-Column Responsive Grid, Multi-Sheet Tabs, Live Logs, Report Links)   │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │ HTTP / JSON / File Upload
┌─────────────────────────────────────▼──────────────────────────────────────┐
│                              FASTAPI BACKEND                               │
│      (Endpoints: /api/upload, /api/paste, /api/execute/all, /api/config)   │
└──────────────┬──────────────────────┬───────────────────────┬──────────────┘
               │                      │                       │
┌──────────────▼──────┐ ┌─────────────▼─────────┐ ┌───────────▼──────────────┐
│ UNIVERSAL PARSER    │ │ GOOGLE CLOUD VERTEX AI│ │ PLAYWRIGHT EXECUTOR      │
│ - Hungarian Matching│ │ - Gemini 2.5 Flash    │ │ - Headless/Headed Engine │
│ - Adapters: Excel,  │ │ - OpenAPI Endpoint    │ │ - Oracle ADF/JET Sync    │
│   CSV, Word, PDF    │ │ - Semantic Intent De- │ │ - Auto-Proof Screenshots │
│ - In-Memory Parsing │ │   composition & Heal  │ │ - Multi-Role Account Map │
└──────────────┬──────┘ └───────────────────────┘ └───────────┬──────────────┘
               │                                              │
┌──────────────▼──────────────────────────────────────────────▼──────────────┐
│                             DUAL REPORTING ENGINES                         │
│  1. Excel Write-Back Engine (openpyxl status coloring & observed results)   │
│  2. Executive HTML Report Engine (Jinja2, responsive cards, proof gallery)  │
└────────────────────────────────────────────────────────────────────────────┘
```

### Technology Breakdown:
* **Frontend**: React 18, Vite, Vanilla CSS Design System with custom Tokens & Glassmorphism, Lucide Icons.
* **Backend API**: FastAPI, Python 3.10+, Uvicorn, Pydantic v2.
* **AI & Machine Learning**: Google Cloud Vertex AI (`google/gemini-2.5-flash`), Service Account OAuth2 Token Auth, Hungarian Linear-Sum Bipartite Assignment Algorithm.
* **Browser Automation**: Playwright (Chromium, Firefox, WebKit), Oracle Fusion ADF/JET DOM Synchronizer.
* **Parsing & File Ingestion**: `openpyxl`, `python-docx`, `pypdf`, `csv`, in-memory text normalization.
* **Reporting & Write-Back**: `openpyxl` Style Engines (Green/Red fill), Jinja2 HTML Templates.

---

## 3. Core Capabilities & Detailed Step-by-Step Workflow

### Step 1: Universal Document Parsing & Format Agnosticism
Manual test scripts come in diverse templates from different consulting firms and QA teams. The platform utilizes custom **Format Adapters**:
- **Excel Adapter (`excel_adapter.py`)**: Traverses multi-sheet workbooks (`ORC_001`, `ORC_002`, `PO_CREATION`, etc.), reads cell values, headers, and formulas.
- **Word / Docx Adapter (`docx_adapter.py`)**: Parses tables and structured bullet lists from `.docx` files.
- **PDF & Markdown Adapters**: Extracts tabular data and numbered steps.
- **Raw Text / Paste Parser**: Parses copy-pasted test instructions directly from clipboard.

### Step 2: Hungarian Bipartite 1-to-1 Column Mapping
To map unpredictable column headers (e.g. *"Step Desc"*, *"Action to Perform"*, *"Expected Output"*, *"Role Name"*) into a canonical schema without hardcoding:
- The system calculates semantic distance and cosine similarity scores between incoming headers and canonical target fields (`step_id`, `role`, `description`, `test_data`, `expected_result`, `status`, `observed_result`).
- It solves the **optimal 1-to-1 assignment problem** using the **Hungarian Algorithm** (O(n³)), guaranteeing that no two columns collide and the highest-confidence mapping is selected.

### Step 3: Atomic Sub-Action Decomposition & AI Enrichment
Human test steps often contain compound instructions (e.g. *"Click Navigator, go to Procurement, open Purchase Orders and enter supplier ABC"*):
- The **Intent Parser** breaks compound steps into discrete atomic actions:
  - `NAVIGATE` -> Target menu path
  - `CLICK` -> Target button or link
  - `ENTER_TEXT` -> Target field with test data
  - `VERIFY` -> Expected UI validation
- **Google Cloud Vertex AI (Gemini 2.5 Flash)** enriches ambiguous steps with structured JSON Playwright action specifications tailored to Oracle Fusion ADF/JET UI patterns.

### Step 4: Multi-Sheet Batch Automated Execution
- Ingesting an Excel workbook containing multiple sheets (e.g., 60 test cases with 1,103 steps) automatically loads the entire batch.
- Clicking **"Run Automated Flow"** triggers batch execution across all sheets sequentially without requiring manual sheet switching.
- Pill tabs at the top allow inspecting individual sheets at any time.

### Step 5: Background Headless Execution & Oracle Fusion Sync
- **Headless Mode (`headless: true`)**: Runs silently in the background without intrusive popup windows.
- **Fusion Synchronizer (`fusion_sync.py`)**: Solves Oracle ADF/JET asynchronous rendering issues by listening for:
  - `AdfPage.PAGE.isSynchronizedWithServer()`
  - Active network request idle states (`networkidle`)
  - DOM mutation stabilization before clicking or typing.

### Step 6: Automated Proof & Milestone Screenshot Capture
To provide visual proof of execution without consuming gigabytes of video storage:
- **Login Proof (`login_proof.png`)**: Automatically captures the Oracle Cloud landing dashboard upon sign-in as `ramya.dm`.
- **Milestone Proof**: Captures high-res snapshots on key form submissions and completions.
- **Failure Proof**: Immediately captures full-page snapshots if any step fails.
- Compressed automatically (~50 KB – 80 KB per screenshot) saving over 99% disk space compared to video.

### Step 7: Dual Reporting System
1. **Updated Excel File Write-Back (`.xlsx`)**:
   - The engine clones the original Excel file and updates each executed step.
   - Sets **Status** column to `Pass` (Soft Green `#C6EFCE`) or `Fail` (Soft Red `#FFC7CE`).
   - Fills in the **Observed Result** with execution timestamps and links screenshot paths in **Notes**.
   - Preserves original formulas, multiple sheets, and custom template formatting.
2. **Executive HTML Report**:
   - Self-contained, responsive dashboard with overall metrics (Total Test Cases, Steps Passed/Failed, Execution Time).
   - Sheet-by-sheet accordion breakdown with embedded proof screenshot thumbnails (clickable to view in full resolution).

### Step 8: Multi-Role Credential Mapping (Optional)
- **Single Demo User Mode (Default)**: Executes all roles (*Hiring Manager*, *Recruiter*, *Line Manager*) using the configured demo super-user (`ramya.dm`).
- **Multi-User Role Mapping (Optional Toggle)**: Allows mapping specific accounts to different roles for automated multi-user approval handoffs.

---

## 4. Configuration (`.env`)

Located at the root of the project:

```env
# =============================================================
# Oracle Fusion Cloud - Instance & Credentials
# =============================================================
ORACLE_BASE_URL=https://fa-eubg-test-saasfademo1.ds-fa.oraclepdemos.com
ORACLE_USERNAME=ramya.dm
ORACLE_PASSWORD=TLS@1234

# =============================================================
# Google Cloud Vertex AI (Gemini) - AI Interpretation Engine
# =============================================================
GCP_PROJECT_ID=project-b7e4de28-72cd-4ca3-92a
GCP_LOCATION=global
GCP_SERVICE_ACCOUNT_JSON=config/gcp_service_account.json
GEMINI_MODEL=google/gemini-2.5-flash

# =============================================================
# Browser Settings
# =============================================================
BROWSER=chromium
HEADLESS=true
```

---

## 5. Running the Application

### 1. Start Backend Server
```bash
python app.py
```
* Backend runs on **`http://127.0.0.1:8000`*.

### 2. Frontend Development / Build (Optional)
The pre-built React application is served directly by FastAPI. If you modify React code in `/frontend/src`:
```bash
cd frontend
npm run build
```

---

## 6. Project Structure

```
├── app.py                            # Application entrypoint
├── .env                              # Environment configuration
├── config/
│   └── gcp_service_account.json      # Google Cloud Vertex AI credentials
├── core/
│   ├── ai/
│   │   └── gemini_client.py          # Vertex AI Gemini OpenAPI client
│   ├── executor/
│   │   ├── fusion_sync.py            # Oracle ADF/JET DOM synchronizer
│   │   └── playwright_executor.py    # Playwright browser engine & screenshot capture
│   ├── parser/
│   │   ├── column_matcher.py         # Hungarian bipartite column mapper
│   │   ├── universal_parser.py       # Format-agnostic parser router
│   │   └── adapters/
│   │       ├── excel_adapter.py      # Multi-sheet Excel workbook reader
│   │       ├── csv_adapter.py        # CSV parser
│   │       └── docx_adapter.py       # Word document parser
│   ├── models/
│   │   └── schema.py                 # Canonical Script & Step Pydantic models
│   └── writeback/
│       ├── excel_writer.py           # Multi-sheet Excel status write-back
│       └── html_reporter.py          # Executive HTML report generator
├── frontend/
│   ├── src/
│   │   ├── App.jsx                   # React Web Studio UI
│   │   └── index.css                 # Glassmorphism Design System Tokens
│   └── dist/                         # Compiled production bundle
├── reports/
│   └── screenshots/                  # Timestamped proof and failure screenshots
└── uploads/                          # Temporary uploaded test script workbooks
```
