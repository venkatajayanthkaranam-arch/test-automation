"""
Multi-Sheet Executive HTML Report Generator (Clean - No Screenshots)
"""

import os
from typing import List, Union, Optional
from datetime import datetime
from jinja2 import Template
from core.models.schema import CanonicalScript, StepStatus

MULTI_SHEET_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Oracle Cloud Automated Execution Report</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --card-border: #e2e8f0;
      --text: #0f172a;
      --text-muted: #64748b;
      --primary: #0284c7;
      --primary-glow: rgba(2, 132, 199, 0.15);
      --pass: #16a34a;
      --pass-bg: #dcfce7;
      --fail: #dc2626;
      --fail-bg: #fee2e2;
      --not-attempted: #64748b;
      --not-attempted-bg: #f1f5f9;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 40px 24px;
      font-family: 'Plus Jakarta Sans', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
    }
    .container {
      max-width: 1280px;
      margin: 0 auto;
    }
    .header {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 20px;
      padding: 32px;
      box-shadow: 0 4px 20px -2px rgba(0,0,0,0.05);
      margin-bottom: 28px;
    }
    .badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 700;
    }
    .badge-pass { background: var(--pass-bg); color: var(--pass); }
    .badge-fail { background: var(--fail-bg); color: var(--fail); }
    .badge-not { background: var(--not-attempted-bg); color: var(--not-attempted); }
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-top: 24px;
    }
    .stat-card {
      background: #f8fafc;
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 16px 20px;
    }
    .stat-card .val {
      font-size: 28px;
      font-weight: 800;
      color: var(--primary);
    }
    .stat-card .lbl {
      font-size: 13px;
      color: var(--text-muted);
      font-weight: 600;
      margin-top: 4px;
    }
    .script-section {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      margin-bottom: 24px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.03);
      overflow: hidden;
    }
    .script-header {
      padding: 20px 24px;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #fafafa;
    }
    .script-header h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13.5px;
    }
    th {
      background: #f1f5f9;
      padding: 12px 18px;
      text-align: left;
      font-weight: 700;
      color: #334155;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    td {
      padding: 14px 18px;
      border-bottom: 1px solid var(--card-border);
      vertical-align: top;
    }
    tr:last-child td {
      border-bottom: none;
    }
    .step-id {
      font-family: 'JetBrains Mono', monospace;
      font-weight: 600;
      color: var(--primary);
    }
    .role-badge {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 6px;
      background: #e0f2fe;
      color: #0369a1;
      font-size: 11.5px;
      font-weight: 600;
    }
    .substep {
      margin-top: 6px;
      padding: 6px 10px;
      background: #f8fafc;
      border-radius: 6px;
      font-size: 12px;
      border-left: 3px solid var(--primary);
      color: #334155;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
          <h1 style="margin: 0; font-size: 24px; font-weight: 800; color: #0f172a;">Oracle Cloud Automated Execution Report</h1>
          <p style="margin: 6px 0 0; color: var(--text-muted); font-size: 14px;">
            Run Time: <b>{{ run_time }}</b> &nbsp;|&nbsp; Source File: <b>{{ source_file }}</b>
          </p>
        </div>
      </div>

      <div class="stats-grid">
        <div class="stat-card">
          <div class="val">{{ scripts|length }}</div>
          <div class="lbl">Total Test Cases</div>
        </div>
        <div class="stat-card">
          <div class="val" style="color: #0f172a;">{{ total_steps }}</div>
          <div class="lbl">Total Steps</div>
        </div>
        <div class="stat-card">
          <div class="val" style="color: var(--pass);">{{ total_passed }}</div>
          <div class="lbl">Passed Steps</div>
        </div>
        <div class="stat-card">
          <div class="val" style="color: var(--fail);">{{ total_failed }}</div>
          <div class="lbl">Failed Steps</div>
        </div>
      </div>
    </div>

    {% for script in scripts %}
    <div class="script-section">
      <div class="script-header">
        <div>
          <h3>📋 {{ script.script_id }} <span style="font-weight: 500; color: var(--text-muted);">— {{ script.title }}</span></h3>
        </div>
        <div>
          <span class="badge badge-pass">{{ script.steps|selectattr('status.name', 'equalto', 'PASS')|list|length }}/{{ script.steps|length }} Passed</span>
        </div>
      </div>
      <table>
        <thead>
          <tr>
            <th style="width: 130px;">Step ID</th>
            <th style="width: 140px;">Role</th>
            <th>Instruction & Sub-actions</th>
            <th>Observed Result</th>
            <th style="width: 110px;">Status</th>
          </tr>
        </thead>
        <tbody>
          {% for s in script.steps %}
          <tr>
            <td class="step-id">{{ s.id }}</td>
            <td>
              {% if s.role %}
                <span class="role-badge">{{ s.role }}</span>
              {% else %}
                <span style="color: var(--text-muted);">-</span>
              {% endif %}
            </td>
            <td>
              <div style="font-weight: 500; color: #1e293b;">{{ s.raw_text }}</div>
              {% if s.is_compound and s.sub_steps %}
                {% for sub in s.sub_steps %}
                  <div class="substep">⚡ <b>Sub-step {{ sub.sequence }}:</b> {{ sub.raw_text }}</div>
                {% endfor %}
              {% endif %}
            </td>
            <td>
              <span style="color: #334155; font-size: 13px;">{{ s.observed_result or '—' }}</span>
            </td>
            <td>
              {% if s.status.name == 'PASS' %}
                <span class="badge badge-pass">Pass</span>
              {% elif s.status.name == 'FAIL' %}
                <span class="badge badge-fail">Fail</span>
              {% else %}
                <span class="badge badge-not">Not Attempted</span>
              {% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% endfor %}
  </div>
</body>
</html>
"""

class HtmlReportEngine:
    def generate_report(self, script_or_scripts: Union[CanonicalScript, List[CanonicalScript]], output_path: Optional[str] = None) -> str:
        reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'reports'))
        os.makedirs(reports_dir, exist_ok=True)

        if isinstance(script_or_scripts, CanonicalScript):
            scripts = [script_or_scripts]
            default_name = f"{script_or_scripts.script_id}_execution_report.html"
            source_file = script_or_scripts.source_file or "Test Execution"
        else:
            scripts = script_or_scripts
            default_name = "Oracle_Cloud_Automated_Execution_Report.html"
            source_file = scripts[0].source_file if scripts else "Batch Execution"

        if not output_path:
            output_path = os.path.join(reports_dir, default_name)

        total_steps = sum(len(s.steps) for s in scripts)
        total_passed = sum(sum(1 for st in s.steps if st.status == StepStatus.PASS) for s in scripts)
        total_failed = sum(sum(1 for st in s.steps if st.status == StepStatus.FAIL) for s in scripts)

        tmpl = Template(MULTI_SHEET_HTML_TEMPLATE)
        rendered = tmpl.render(
            scripts=scripts,
            total_steps=total_steps,
            total_passed=total_passed,
            total_failed=total_failed,
            run_time=datetime.now().strftime("%B %d, %Y %I:%M %p"),
            source_file=os.path.basename(source_file)
        )

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered)

        return output_path
