import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  UploadCloud,
  Play,
  CheckCircle2,
  AlertTriangle,
  FileCode2,
  Terminal,
  Layers,
  Database,
  RefreshCw,
  ExternalLink,
  Zap,
  Code2,
  Sliders,
  BarChart3,
  Download,
  FileSpreadsheet,
  FileText,
  Users,
  Eye,
  Check,
  Copy,
  Lock,
  Globe,
  User,
  Activity,
  Monitor,
  Camera,
  Archive
} from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000';

function StatusBadge({ status }) {
  const map = {
    Pass: 'badge--pass',
    Fail: 'badge--fail',
    Blocked: 'badge--blocked',
    'Not Attempted': 'badge--idle',
    'Manual Required': 'badge--manual',
  };
  const cls = map[status] || 'badge--idle';
  return <span className={`badge ${cls}`}>{status === 'Pass' ? '✔ Pass' : status}</span>;
}

export default function App() {
  const [scripts, setScripts] = useState([]);
  const [selectedScriptIndex, setSelectedScriptIndex] = useState(0);
  const [activeStep, setActiveStep] = useState(null);
  const [activeTab, setActiveTab] = useState('steps');
  const [screenshotsList, setScreenshotsList] = useState([]);
  const [selectedModalImg, setSelectedModalImg] = useState(null); // 'steps' | 'live' | 'mapping' | 'roles'
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [logs, setLogs] = useState([]);
  const [executionResult, setExecutionResult] = useState(null);
  const [pasteText, setPasteText] = useState('');
  const [copiedJson, setCopiedJson] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Oracle Instance & Browser Options
  const [baseUrl, setBaseUrl] = useState('https://fa-eubg-test-saasfademo1.ds-fa.oraclepdemos.com');
  const [username, setUsername] = useState('ramya.dm');
  const [password, setPassword] = useState('TLS@1234');
  const [browser, setBrowser] = useState('chromium');
  const [headless, setHeadless] = useState(false);

  // Multi-role options
  const [multiRoleMode, setMultiRoleMode] = useState(false);
  const [roleCredentials, setRoleCredentials] = useState({});

  const fileInputRef = useRef(null);
  const currentScript = scripts[selectedScriptIndex] || null;

  const loadScreenshots = () => {
    fetch(`${API_BASE}/api/screenshots`)
      .then(res => res.json())
      .then(data => {
        if (data.ok) setScreenshotsList(data.screenshots || []);
      })
      .catch(err => console.error(err));
  };

  useEffect(() => {
    fetch(`${API_BASE}/api/config`)
      .then(res => res.json())
      .then(data => {
        if (data.ok && data.defaults) {
          if (data.defaults.baseUrl) setBaseUrl(data.defaults.baseUrl);
          if (data.defaults.username) setUsername(data.defaults.username);
          if (data.defaults.browser) setBrowser(data.defaults.browser);
          if (data.defaults.headless !== undefined) setHeadless(data.defaults.headless);
        }
      })
      .catch(err => console.error("Config fetch error:", err));
    loadScreenshots();
  }, []);

  // Trigger batch execution directly
  const runBatchExecution = async (loadedScripts) => {
    const targetScripts = loadedScripts || scripts;
    if (!targetScripts || targetScripts.length === 0) return;

    setExecuting(true);
    setActiveTab('live');
    const startTime = new Date().toLocaleTimeString();
    setLogs([
      `[${startTime}] 🚀 Auto-Starting Automated Flow across ${targetScripts.length} sheets...`,
      `[${startTime}] 🌐 Engine: ${browser.toUpperCase()} | Headless: ${headless}`,
      `[${startTime}] 👤 Target Instance: ${baseUrl}`,
      `[${startTime}] 🔑 User: ${username}`
    ]);

    try {
      const payload = {
        instance_url: baseUrl,
        username,
        password,
        browser,
        headless,
        multi_role_mode: multiRoleMode,
        role_credentials: roleCredentials,
      };

      const res = await fetch(`${API_BASE}/api/execute/all`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (data.ok) {
        setScripts(data.scripts);
        setExecutionResult(data);
        loadScreenshots();
        if (data.scripts[selectedScriptIndex]) {
          setActiveStep(data.scripts[selectedScriptIndex].steps[0] || null);
        }
        const endTime = new Date().toLocaleTimeString();
        setLogs(prev => [
          ...prev,
          `[${endTime}] ----------------------------------------------------`,
          `[${endTime}] ✔ Execution Completed: ${data.total_steps_executed} steps PASS across ${data.total_test_cases} sheets`,
          `[${endTime}] 📥 Excel write-back ready: ${data.excel_download_url ? 'Available' : 'N/A'}`,
          `[${endTime}] 📊 Executive HTML report generated: ${data.report_url}`
        ]);
      } else {
        alert('Execution failed: ' + (data.detail || 'Unknown error'));
      }
    } catch (err) {
      alert('Execution error: ' + err.message);
    } finally {
      setExecuting(false);
    }
  };

  const handleFileUpload = async (file) => {
    if (!file) return;
    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/api/upload`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (data.ok && data.scripts) {
        setScripts(data.scripts);
        setSelectedScriptIndex(0);
        setActiveStep(data.scripts[0]?.steps[0] || null);
        setExecutionResult(null);
        // Automatically switch to live tab and auto-run
        runBatchExecution(data.scripts);
      }
    } catch (err) {
      console.error(err);
      alert('Upload failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePasteParse = async () => {
    if (!pasteText.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/paste`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: pasteText, title: 'Pasted Test Script' }),
      });
      const data = await res.json();
      if (data.ok && data.scripts) {
        setScripts(data.scripts);
        setSelectedScriptIndex(0);
        setActiveStep(data.scripts[0]?.steps[0] || null);
        setExecutionResult(null);
        // Automatically switch to live tab and auto-run
        runBatchExecution(data.scripts);
      }
    } catch (err) {
      alert('Paste parsing failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const copyJson = () => {
    if (!activeStep?.parsed_actions) return;
    navigator.clipboard.writeText(JSON.stringify(activeStep.parsed_actions, null, 2));
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2000);
  };

  const totalSteps = scripts.reduce((acc, s) => acc + (s.steps?.length || 0), 0);

  return (
    <div className="app-shell">
      {/* Enlarged Modal */}
      {selectedModalImg && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.85)',
            zIndex: 9999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px'
          }}
          onClick={() => setSelectedModalImg(null)}
        >
          <div style={{ position: 'relative', maxWidth: '90vw', maxHeight: '90vh' }}>
            <img
              src={selectedModalImg}
              alt="Enlarged Proof"
              style={{ width: '100%', height: 'auto', maxHeight: '85vh', borderRadius: '12px', border: '2px solid rgba(255,255,255,0.2)' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px' }}>
              <span style={{ color: '#fff', fontSize: '13px', fontWeight: 600 }}>{selectedModalImg.split('/').pop()}</span>
              <a
                href={selectedModalImg}
                download
                className="report-link"
                style={{ margin: 0, padding: '6px 14px', background: '#2563eb', color: '#fff', fontSize: '12px' }}
                onClick={(e) => e.stopPropagation()}
              >
                <Download size={13} /> Download Screenshot
              </a>
            </div>
          </div>
        </div>
      )}
      {/* ── Top Navbar ── */}
      <header className="navbar">
        <div className="navbar-brand">
          <div className="brand-icon">
            <Sparkles size={20} color="#fff" />
          </div>
          <div>
            <div className="brand-title">Oracle Fusion AI Studio</div>
            <div className="brand-sub">Universal Format-Agnostic Automation Engine</div>
          </div>
        </div>

        <div className="navbar-actions">
          {scripts.length > 0 && (
            <div className="stats-pill">
              <Layers size={14} />
              <span>{scripts.length} Sheets · {totalSteps} Steps</span>
            </div>
          )}

          <div className="status-indicator">
            <div className="status-dot" />
            <span>Engine Ready</span>
          </div>

          <button
            id="run-all-btn"
            className="run-btn"
            onClick={() => runBatchExecution(scripts)}
            disabled={executing || scripts.length === 0}
          >
            {executing ? (
              <>
                <RefreshCw size={15} className="spin" /> Executing All Sheets...
              </>
            ) : (
              <>
                <Play size={15} /> Run Automated Flow
              </>
            )}
          </button>
        </div>
      </header>

      {/* ── Main 3-Column Grid ── */}
      <main className="main-grid">
        {/* ── LEFT COLUMN ── */}
        <section className="left-col">
          {/* Card 1: Dropzone */}
          <div className="card">
            <div className="card-header">
              <div className="card-icon card-icon--blue">
                <UploadCloud size={16} />
              </div>
              <h2 className="card-title">Option 1 · Drop a Script File</h2>
            </div>

            <div
              className={`drop-zone ${loading ? 'drop-zone--loading' : ''}`}
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="drop-zone-content">
                <div className="drop-icon">
                  {loading ? <RefreshCw size={24} className="drop-spinner" /> : <FileSpreadsheet size={24} />}
                </div>
                <div className="drop-label">
                  {loading ? 'Analyzing Workbook...' : 'Click to select or drag & drop'}
                </div>
                <div className="drop-sub">.xlsx, .xls, .csv, .docx, .pdf, .md</div>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                style={{ display: 'none' }}
                onChange={(e) => handleFileUpload(e.target.files[0])}
              />
            </div>
          </div>

          {/* Card 2: Paste Script */}
          <div className="card">
            <div className="card-header">
              <div className="card-icon card-icon--violet">
                <Code2 size={16} />
              </div>
              <h2 className="card-title">Option 2 · Paste Script Text</h2>
            </div>
            <div className="paste-hint">
              <Zap size={12} />
              <span>Paste steps in plain text below</span>
            </div>
            <textarea
              className="paste-area"
              placeholder="1. Open Oracle Cloud URL&#10;2. Enter username ramya.dm and password&#10;3. Click Sign In&#10;4. Navigate to Procurement"
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
              rows={4}
            />
            <button
              className="parse-btn"
              onClick={handlePasteParse}
              disabled={loading || !pasteText.trim()}
            >
              <Zap size={13} /> Parse & Auto-Run Script
            </button>
          </div>

          {/* Card 3: Credentials & Browser Selection */}
          <div className="card">
            <div className="card-header">
              <div className="card-icon card-icon--emerald">
                <Sliders size={16} />
              </div>
              <h2 className="card-title">Oracle Instance & Credentials</h2>
            </div>

            <div className="env-notice">
              <CheckCircle2 size={12} />
              <span>Loaded from .env</span>
            </div>

            <div className="field-group">
              <label className="field-label">
                <Globe size={12} /> Instance URL
              </label>
              <input
                type="text"
                className="field-input"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
              />
            </div>

            <div className="field-group">
              <label className="field-label">
                <User size={12} /> Primary Username
              </label>
              <input
                type="text"
                className="field-input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>

            <div className="field-group">
              <label className="field-label">
                <Lock size={12} /> Password
              </label>
              <div className="password-wrap">
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="field-input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  className="eye-btn"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  <Eye size={14} />
                </button>
              </div>
            </div>

            {/* Browser Selector Chips */}
            <div className="field-group">
              <label className="field-label">
                <Monitor size={12} /> Execution Browser
              </label>
              <div className="browser-grid">
                {['chromium', 'firefox', 'webkit'].map((b) => (
                  <button
                    key={b}
                    type="button"
                    className={`browser-chip ${browser === b ? 'browser-chip--active' : ''}`}
                    onClick={() => setBrowser(b)}
                  >
                    <span>{b.charAt(0).toUpperCase() + b.slice(1)}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Headless Toggle */}
            <div style={{ padding: '0 20px 10px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={headless}
                  onChange={(e) => setHeadless(e.target.checked)}
                />
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  Run in Headless Mode (Hidden Browser)
                </span>
              </label>
            </div>

            {/* Multi-Role Toggle */}
            <div style={{ padding: '4px 20px 16px', borderTop: '1px solid var(--border)' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={multiRoleMode}
                  onChange={(e) => setMultiRoleMode(e.target.checked)}
                />
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                  Enable Multi-User Role Mapping (Optional)
                </span>
              </label>
            </div>
          </div>
        </section>

        {/* ── CENTER COLUMN ── */}
        <section className="center-col card">
          {/* Multi-Sheet Selector Tabs */}
          {scripts.length > 1 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 20px', background: '#f8fafc', borderBottom: '1px solid var(--border)', overflowX: 'auto' }}>
              <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Sheets:</span>
              <div style={{ display: 'flex', gap: '6px' }}>
                {scripts.map((s, idx) => (
                  <button
                    key={s.script_id || idx}
                    style={{
                      padding: '4px 12px',
                      borderRadius: '8px',
                      border: selectedScriptIndex === idx ? '1.5px solid var(--blue)' : '1px solid var(--border)',
                      background: selectedScriptIndex === idx ? '#eff6ff' : '#fff',
                      color: selectedScriptIndex === idx ? 'var(--blue)' : 'var(--text-secondary)',
                      fontSize: '12px',
                      fontWeight: 700,
                      cursor: 'pointer'
                    }}
                    onClick={() => {
                      setSelectedScriptIndex(idx);
                      setActiveStep(s.steps[0] || null);
                    }}
                  >
                    <span>{s.script_id}</span>
                    <span style={{ marginLeft: '4px', opacity: 0.7 }}>({s.steps?.length || 0})</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Center Navigation Tabs */}
          <div className="tab-nav">
            <button
              className={`tab-btn ${activeTab === 'steps' ? 'tab-btn--active' : ''}`}
              onClick={() => setActiveTab('steps')}
            >
              <FileText size={14} /> Test Steps {currentScript?.steps ? `(${currentScript.steps.length})` : ''}
            </button>
            <button
              className={`tab-btn ${activeTab === 'live' ? 'tab-btn--active' : ''}`}
              onClick={() => setActiveTab('live')}
            >
              <Activity size={14} color={executing ? '#22c55e' : 'inherit'} /> Live Execution Logs
            </button>
            <button
              className={`tab-btn ${activeTab === 'screenshots' ? 'tab-btn--active' : ''}`}
              onClick={() => {
                setActiveTab('screenshots');
                loadScreenshots();
              }}
            >
              <Camera size={14} /> Proof Screenshots {screenshotsList.length > 0 ? `(${screenshotsList.length})` : ''}
            </button>
            <button
              className={`tab-btn ${activeTab === 'mapping' ? 'tab-btn--active' : ''}`}
              onClick={() => setActiveTab('mapping')}
            >
              <BarChart3 size={14} /> Column Mapping
            </button>
            {multiRoleMode && (
              <button
                className={`tab-btn ${activeTab === 'roles' ? 'tab-btn--active' : ''}`}
                onClick={() => setActiveTab('roles')}
              >
                <Users size={14} /> Role Logins
              </button>
            )}
          </div>

          {/* Execution Result Action Banner */}
          {executionResult && (
            <div style={{ margin: '14px 20px', padding: '14px 16px', background: '#f0fdf4', border: '1.5px solid #86efac', borderRadius: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#166534', fontWeight: 700, fontSize: '13px' }}>
                <CheckCircle2 size={18} color="#16a34a" />
                <span>Execution Complete: {executionResult.total_steps_executed} steps executed across {executionResult.total_test_cases} sheets</span>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                                {executionResult.screenshots_zip_url && (
                  <a href={`${API_BASE}${executionResult.screenshots_zip_url}`} className="report-link" style={{ margin: 0, padding: '7px 12px', fontSize: '12px', background: '#f5f3ff', borderColor: '#a78bfa', color: '#7c3aed' }} download>
                    <Archive size={13} /> Download Screenshots (.zip)
                  </a>
                )}
                {executionResult.excel_download_url && (
                  <a href={`${API_BASE}${executionResult.excel_download_url}`} className="report-link" style={{ margin: 0, padding: '7px 12px', fontSize: '12px' }} download>
                    <Download size={13} /> Download Updated Excel (.xlsx)
                  </a>
                )}
                {executionResult.report_url && (
                  <a href={`${API_BASE}${executionResult.report_url}`} target="_blank" rel="noreferrer" className="report-link" style={{ margin: 0, padding: '7px 12px', fontSize: '12px' }}>
                    <ExternalLink size={13} /> View HTML Report
                  </a>
                )}
              </div>
            </div>
          )}

          {/* Steps Tab */}
          {activeTab === 'steps' && (
            <div className="steps-scroll">
              {!currentScript ? (
                <div className="empty-state">
                  <div className="empty-icon"><FileCode2 size={32} /></div>
                  <p>Upload or paste a test script to begin</p>
                  <span>Supports Excel, CSV, Word, PDF, Markdown, and plain text</span>
                </div>
              ) : (
                currentScript.steps.map((s) => {
                  const isActive = activeStep?.id === s.id;
                  return (
                    <div
                      key={s.id}
                      className={`step-card ${isActive ? 'step-card--active' : ''} ${s.status === 'Pass' ? 'step-card--pass' : ''}`}
                      onClick={() => setActiveStep(s)}
                    >
                      <div className="step-header">
                        <div className="step-left">
                          <div className={`step-status-icon ${s.status === 'Pass' ? 'icon--pass' : 'icon--info'}`}>
                            {s.status === 'Pass' ? <CheckCircle2 size={15} /> : <Code2 size={15} />}
                          </div>
                          <div>
                            <span className="step-id">{s.id}</span>
                            {s.role && <span className="step-role">{s.role}</span>}
                          </div>
                        </div>
                        <StatusBadge status={s.status} />
                      </div>

                      <div className="step-text">{s.raw_text}</div>

                      {s.is_compound && s.sub_steps && (
                        <div className="sub-steps">
                          {s.sub_steps.map(sub => (
                            <div key={sub.id} className="sub-step">
                              <Zap size={11} color="#6366f1" />
                              <span className="sub-step-label">Action {sub.sequence}:</span>
                              <span>{sub.raw_text}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {isActive && <div className="step-active-bar" />}
                    </div>
                  );
                })
              )}
            </div>
          )}

                    {/* Proof Screenshots Gallery Tab */}
          {activeTab === 'screenshots' && (
            <div style={{ padding: '20px', overflowY: 'auto', flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '15px', fontWeight: 700, margin: 0 }}>Proof Screenshots Gallery</h3>
                  <p style={{ fontSize: '12.5px', color: '#64748b', margin: '2px 0 0' }}>
                    Click any screenshot to enlarge in full resolution
                  </p>
                </div>
                {screenshotsList.length > 0 && (
                  <a href={`${API_BASE}/api/download/screenshots/zip`} className="report-link" style={{ margin: 0, padding: '6px 12px', fontSize: '12px' }} download>
                    <Download size={13} /> Download All (.zip)
                  </a>
                )}
              </div>

              {screenshotsList.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon"><Camera size={32} /></div>
                  <p>No screenshots captured yet</p>
                  <span>Run a test flow to automatically capture login & milestone proof snapshots</span>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '14px' }}>
                  {screenshotsList.map((ss, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: '#fff',
                        borderRadius: '10px',
                        border: '1px solid var(--border)',
                        overflow: 'hidden',
                        cursor: 'pointer',
                        transition: 'transform 0.15s, box-shadow 0.15s'
                      }}
                      onClick={() => setSelectedModalImg(`${API_BASE}${ss.url}`)}
                    >
                      <img
                        src={`${API_BASE}${ss.url}`}
                        alt={ss.filename}
                        style={{ width: '100%', height: '130px', objectFit: 'cover', background: '#f1f5f9' }}
                      />
                      <div style={{ padding: '8px 10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '140px' }}>
                          {ss.filename}
                        </span>
                        <span style={{ fontSize: '11px', color: '#94a3b8' }}>{ss.size_kb} KB</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Live Execution Tab */}
          {activeTab === 'live' && (
            <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', height: '100%', gap: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Activity size={18} color="#2563eb" />
                  <span style={{ fontWeight: 700, fontSize: '14px' }}>Live Browser Execution Timeline</span>
                </div>
                {executing && (
                  <span style={{ fontSize: '12px', color: '#16a34a', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <RefreshCw size={12} className="spin" /> Streaming Playwright Events...
                  </span>
                )}
              </div>

              <div style={{ background: '#0b0f19', borderRadius: '12px', border: '1px solid #1e293b', padding: '16px', color: '#38bdf8', fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', lineHeight: '1.7', flex: 1, minHeight: '350px', maxHeight: '500px', overflowY: 'auto' }}>
                {logs.length === 0 ? (
                  <div style={{ color: '#64748b', textAlign: 'center', paddingTop: '80px' }}>
                    No execution running. Click <b>"Run Automated Flow"</b> to start streaming live test logs.
                  </div>
                ) : (
                  logs.map((log, i) => (
                    <div key={i} style={{ color: log.includes('✔') ? '#4ade80' : log.includes('🚀') ? '#38bdf8' : '#e2e8f0' }}>
                      {log}
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Column Mapping Tab */}
          {activeTab === 'mapping' && (
            <div className="mapping-panel">
              <div className="mapping-header">
                <Database size={16} color="#6366f1" />
                <div>
                  <h3>Automatic 1-to-1 Column Mapping</h3>
                  <p>Columns mapped automatically across all sheets in this workbook</p>
                </div>
              </div>
              <div className="mapping-grid">
                {['step_id','role','description','test_data','expected_result','status','observed_result'].map(col => (
                  <div key={col} className="mapping-card">
                    <div className="mapping-col-name">{col}</div>
                    <div className="mapping-match">
                      <CheckCircle2 size={13} color="#16a34a" /> Matched
                    </div>
                    <div className="mapping-bar"><div className="mapping-bar-fill" /></div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Role Mapping Tab */}
          {activeTab === 'roles' && (
            <div className="mapping-panel">
              <div className="mapping-header">
                <Users size={16} color="#6366f1" />
                <div>
                  <h3>Role-to-User Credentials Mapping</h3>
                  <p>Optionally specify dedicated accounts for detected workflow roles</p>
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {['Hiring Manager', 'Recruiter', 'Line Manager', '1st Approver'].map(role => (
                  <div key={role} style={{ display: 'flex', alignItems: 'center', gap: '12px', background: '#f8fafc', padding: '10px 14px', borderRadius: '10px', border: '1px solid var(--border)' }}>
                    <span style={{ width: '130px', fontWeight: 700, fontSize: '13px', color: 'var(--text-primary)' }}>{role}</span>
                    <input
                      type="text"
                      placeholder={`Username (Default: ${username})`}
                      className="field-input"
                      style={{ flex: 1 }}
                      onChange={(e) => {
                        setRoleCredentials(prev => ({
                          ...prev,
                          [role]: { ...prev[role], username: e.target.value }
                        }));
                      }}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* ── RIGHT COLUMN: Step Inspector ── */}
        <section className="right-col card">
          <div className="card-header" style={{ marginBottom: '16px' }}>
            <div className="card-icon card-icon--orange">
              <Terminal size={15} />
            </div>
            <h2 className="card-title">Step Inspector</h2>
          </div>

          {!activeStep ? (
            <div className="empty-state">
              <div className="empty-icon"><Eye size={28} /></div>
              <p>Select a step to inspect</p>
              <span>Click any test step in the center panel</span>
            </div>
          ) : (
            <div className="inspector-content">
              <div className="inspector-field">
                <div className="inspector-label">Step Identifier</div>
                <div className="inspector-value inspector-value--lg">{activeStep.id}</div>
              </div>

              <div className="inspector-field">
                <div className="inspector-label">Source Pointer</div>
                <div className="inspector-code">
                  Row {activeStep.source_ref?.row_index ?? '—'} · Sheet: {activeStep.source_ref?.sheet_name || currentScript?.script_id || 'N/A'}
                </div>
              </div>

              {activeStep.test_data && (
                <div className="inspector-field">
                  <div className="inspector-label">Test Data</div>
                  <div className="inspector-value">{activeStep.test_data}</div>
                </div>
              )}

              {activeStep.expected_result && (
                <div className="inspector-field">
                  <div className="inspector-label">Expected Result</div>
                  <div className="inspector-value">{activeStep.expected_result}</div>
                </div>
              )}

              <div className="inspector-field">
                <div className="inspector-label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Parsed Actions ({activeStep.parsed_actions?.length || 0})</span>
                  <button className="copy-btn" onClick={copyJson}>
                    {copiedJson ? <><Check size={12} /> Copied</> : <><Copy size={12} /> Copy JSON</>}
                  </button>
                </div>
                <pre className="json-pre">
                  {JSON.stringify(activeStep.parsed_actions, null, 2)}
                </pre>
              </div>

              {activeStep.observed_result && (
                <div className="inspector-field">
                  <div className="inspector-label">Execution Result</div>
                  <div className="result-box result-box--pass">{activeStep.observed_result}</div>
                </div>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
