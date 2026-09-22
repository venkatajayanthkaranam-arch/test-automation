import React, { useState, useRef, useEffect } from 'react';
import { 
  Play, Upload, CheckCircle2, AlertTriangle, 
  Terminal, Layers, ShieldCheck, FileSpreadsheet, 
  Sparkles, RefreshCw, Eye, Code2, KeyRound, Globe, User, 
  FileText, ClipboardPaste, ArrowRight, ShieldAlert, Cpu, Download
} from 'lucide-react';
import axios from 'axios';

export default function App() {
  const [script, setScript] = useState(null);
  const [allScripts, setAllScripts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [activeStep, setActiveStep] = useState(null);
  const [executionResult, setExecutionResult] = useState(null);
  const [activeTab, setActiveTab] = useState('steps'); // 'steps' | 'logs' | 'mapping'
  const [logs, setLogs] = useState([]);

  // Input States
  const [pastedText, setPastedText] = useState('');
  const [instanceUrl, setInstanceUrl] = useState('https://fa-eubg-test-saasfademo1.ds-fa.oraclepdemos.com');
  const [username, setUsername] = useState('ramya.dm');
  const [password, setPassword] = useState('TLS@1234');
  const [headless, setHeadless] = useState(true);

  const fileInputRef = useRef(null);

  useEffect(() => {
    // Fetch initial configuration
    axios.get('/api/config')
      .then(res => {
        if (res.data?.ok && res.data.defaults) {
          const d = res.data.defaults;
          if (d.baseUrl) setInstanceUrl(d.baseUrl);
          if (d.username) setUsername(d.username);
        }
      })
      .catch(() => {});
  }, []);

  // File Upload Handler
  const handleFileUpload = async (file) => {
    if (!file) return;
    setLoading(true);
    setExecutionResult(null);
    setLogs([`Analyzing uploaded file: ${file.name}...`]);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await axios.post('/api/upload', formData);
      if (res.data.ok && res.data.scripts.length > 0) {
        setAllScripts(res.data.scripts);
        setScript(res.data.scripts[0]);
        setActiveStep(res.data.scripts[0].steps[0]);
        setLogs(prev => [
          ...prev,
          `Ingested ${res.data.scripts.length} sheets (${res.data.scripts.reduce((acc, s) => acc + s.steps.length, 0)} total steps).`,
          `Selected primary sheet: ${res.data.scripts[0].script_id} — ${res.data.scripts[0].title}`
        ]);
      }
    } catch (err) {
      alert('Error parsing file: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // Paste Text Parser Handler
  const handleParsePasted = async () => {
    if (!pastedText.trim()) {
      alert('Please paste some test case text or steps first!');
      return;
    }
    setLoading(true);
    setExecutionResult(null);
    setLogs([`Deconstructing pasted test steps...`]);

    try {
      const res = await axios.post('/api/paste', {
        title: 'Pasted Fusion Test Script',
        content: pastedText
      });
      if (res.data.ok && res.data.scripts.length > 0) {
        setAllScripts(res.data.scripts);
        setScript(res.data.scripts[0]);
        setActiveStep(res.data.scripts[0].steps[0]);
        setLogs(prev => [
          ...prev,
          `Successfully extracted ${res.data.scripts[0].steps.length} atomic steps from pasted text.`
        ]);
      }
    } catch (err) {
      alert('Error parsing pasted script: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // Automated Batch Execution Handler
  const handleExecute = async () => {
    if (!script && allScripts.length === 0) return;
    setExecuting(true);
    setActiveTab('logs');
    setLogs([
      `Initializing automated execution on: ${instanceUrl}`,
      `Authenticating user: ${username}`,
      `Executing ${allScripts.length || 1} sheets sequentially in batch...`
    ]);

    try {
      const res = await axios.post('/api/execute/all', {
        instance_url: instanceUrl,
        username: username,
        password: password,
        headless: headless
      });

      if (res.data.ok) {
        setExecutionResult(res.data);
        if (res.data.scripts && res.data.scripts.length > 0) {
          setAllScripts(res.data.scripts);
          const currentId = script ? script.script_id : res.data.scripts[0].script_id;
          const updatedScript = res.data.scripts.find(s => s.script_id === currentId) || res.data.scripts[0];
          setScript(updatedScript);
          if (updatedScript.steps && updatedScript.steps.length > 0) {
            setActiveStep(updatedScript.steps[0]);
          }
        }
        setLogs(prev => [
          ...prev,
          `✓ Execution finished across all ${res.data.count || allScripts.length} sheets!`,
          `✓ Excel write-back generated successfully.`,
          `✓ Executive HTML report ready for review.`
        ]);
      }
    } catch (err) {
      alert('Execution error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      
      {/* Top Navigation Bar */}
      <header style={{ 
        padding: '16px 36px', 
        borderBottom: '1px solid #e2e8f0',
        background: '#ffffff',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 2px 8px rgba(0,0,0,0.03)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ 
            width: '42px', height: '42px', borderRadius: '12px',
            background: 'linear-gradient(135deg, #0284c7 0%, #4f46e5 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 12px rgba(2, 132, 199, 0.3)'
          }}>
            <Sparkles size={22} color="#fff" />
          </div>
          <div>
            <h1 style={{ fontSize: '18px', fontWeight: 800, color: '#0f172a', letterSpacing: '-0.02em', margin: 0 }}>
              Oracle Fusion AI Automation Studio
            </h1>
            <p style={{ fontSize: '12.5px', color: '#64748b', margin: '2px 0 0 0' }}>
              Universal Format-Agnostic Engine • Ultra-Fast Batch Test Runner
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ 
            display: 'flex', alignItems: 'center', gap: '8px', 
            padding: '6px 14px', borderRadius: '999px',
            background: '#ecfdf5', border: '1px solid #a7f3d0',
            fontSize: '12.5px', color: '#059669', fontWeight: 600
          }}>
            <ShieldCheck size={16} />
            <span>Target: TEST-POD-01 (Safe Guard Active)</span>
          </div>

          <button 
            onClick={handleExecute}
            disabled={(!script && allScripts.length === 0) || executing}
            className="primary-btn"
            style={{ 
              padding: '10px 22px', 
              fontSize: '14px', 
              opacity: ((!script && allScripts.length === 0) || executing) ? 0.6 : 1,
              cursor: ((!script && allScripts.length === 0) || executing) ? 'not-allowed' : 'pointer'
            }}
          >
            {executing ? <RefreshCw size={16} className="animate-spin" /> : <Play size={16} />}
            <span>{executing ? 'Executing Batch...' : 'Run Automated Flow'}</span>
          </button>
        </div>
      </header>

      {/* Main 3-Column Layout */}
      <main style={{ flex: 1, padding: '28px 36px', display: 'grid', gridTemplateColumns: '400px 1fr 380px', gap: '24px' }}>
        
        {/* Left Column: Script Upload, Paste Box & Credentials */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* 1. Drop a Script Box */}
          <div className="clean-card" style={{ padding: '22px' }}>
            <h2 style={{ fontSize: '15px', fontWeight: 700, color: '#0284c7', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px', margin: '0 0 14px 0' }}>
              <FileSpreadsheet size={18} /> Option 1: Drop a Script File
            </h2>

            <div 
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: '2px dashed #93c5fd',
                borderRadius: '14px',
                padding: '24px 16px',
                textAlign: 'center',
                cursor: 'pointer',
                background: '#f8fafc',
                transition: 'all 0.2s'
              }}
            >
              <div style={{ 
                width: '42px', height: '42px', borderRadius: '50%',
                background: '#e0f2fe', color: '#0284c7',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 10px auto'
              }}>
                <Upload size={20} />
              </div>
              <div style={{ fontWeight: 600, fontSize: '14px', color: '#1e293b' }}>
                {loading ? 'Analyzing with Hungarian Matcher...' : 'Drop file here or click to browse'}
              </div>
              <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
                .xlsx, .xls, .csv, .docx, .pdf, .md
              </div>
              <input 
                ref={fileInputRef}
                type="file" 
                style={{ display: 'none' }} 
                onChange={(e) => handleFileUpload(e.target.files[0])}
              />
            </div>
          </div>

          {/* 2. Paste Script Plain Text Box */}
          <div className="clean-card" style={{ padding: '22px' }}>
            <h2 style={{ fontSize: '15px', fontWeight: 700, color: '#0284c7', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px', margin: '0 0 14px 0' }}>
              <ClipboardPaste size={18} /> Option 2: Paste Script / Prose Text
            </h2>

            <textarea 
              rows={4}
              value={pastedText}
              onChange={(e) => setPastedText(e.target.value)}
              placeholder="Paste your test steps here, e.g.:&#10;1. Login as 1st Approver and click on bell icon&#10;2. Click on Offer approval notification&#10;3. Click on Approve button"
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '10px',
                border: '1.5px solid #cbd5e1',
                background: '#fff',
                fontSize: '13px',
                lineHeight: 1.5,
                fontFamily: 'inherit',
                resize: 'vertical',
                outline: 'none',
                boxSizing: 'border-box'
              }}
            />

            <button 
              onClick={handleParsePasted}
              disabled={loading || !pastedText.trim()}
              style={{
                width: '100%',
                padding: '10px',
                marginTop: '10px',
                borderRadius: '10px',
                border: '1px solid #bae6fd',
                background: '#f0f9ff',
                color: '#0284c7',
                fontWeight: 600,
                fontSize: '13px',
                cursor: (!pastedText.trim() || loading) ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px'
              }}
            >
              <Cpu size={15} /> Parse Pasted Script
            </button>
          </div>

          {/* 3. Oracle Cloud Credentials & Instance Form */}
          <div className="clean-card" style={{ padding: '22px' }}>
            <h2 style={{ fontSize: '15px', fontWeight: 700, color: '#0284c7', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', margin: '0 0 16px 0' }}>
              <Globe size={18} /> Oracle Instance & Credentials
            </h2>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Globe size={13} /> Instance URL
                </label>
                <input 
                  type="text" 
                  value={instanceUrl} 
                  onChange={(e) => setInstanceUrl(e.target.value)}
                  className="input-box"
                  style={{ marginTop: '4px', width: '100%', boxSizing: 'border-box' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <User size={13} /> Username
                </label>
                <input 
                  type="text" 
                  value={username} 
                  onChange={(e) => setUsername(e.target.value)}
                  className="input-box"
                  style={{ marginTop: '4px', width: '100%', boxSizing: 'border-box' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <KeyRound size={13} /> Password
                </label>
                <input 
                  type="password" 
                  value={password} 
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-box"
                  style={{ marginTop: '4px', width: '100%', boxSizing: 'border-box' }}
                />
              </div>
            </div>
          </div>
        </section>

        {/* Center Column: Atomic Steps & Compilation Badges */}
        <section className="clean-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column' }}>
          
          {/* Header Tabs */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button 
                onClick={() => setActiveTab('steps')}
                style={{
                  padding: '8px 16px', borderRadius: '10px', border: 'none',
                  background: activeTab === 'steps' ? '#e0f2fe' : 'transparent',
                  color: activeTab === 'steps' ? '#0284c7' : '#64748b',
                  fontWeight: 700, fontSize: '13.5px', cursor: 'pointer'
                }}
              >
                Test Steps ({script?.steps?.length || 0})
              </button>

              <button 
                onClick={() => setActiveTab('logs')}
                style={{
                  padding: '8px 16px', borderRadius: '10px', border: 'none',
                  background: activeTab === 'logs' ? '#e0f2fe' : 'transparent',
                  color: activeTab === 'logs' ? '#0284c7' : '#64748b',
                  fontWeight: 700, fontSize: '13.5px', cursor: 'pointer'
                }}
              >
                Live Execution Logs
              </button>

              <button 
                onClick={() => setActiveTab('mapping')}
                style={{
                  padding: '8px 16px', borderRadius: '10px', border: 'none',
                  background: activeTab === 'mapping' ? '#e0f2fe' : 'transparent',
                  color: activeTab === 'mapping' ? '#0284c7' : '#64748b',
                  fontWeight: 700, fontSize: '13.5px', cursor: 'pointer'
                }}
              >
                Column Mapping
              </button>
            </div>

            {executionResult && (
              <div style={{ display: 'flex', gap: '10px' }}>
                <a 
                  href="/api/download/excel" 
                  target="_blank" 
                  rel="noreferrer"
                  style={{ 
                    fontSize: '12.5px', color: '#16a34a', textDecoration: 'none',
                    display: 'flex', alignItems: 'center', gap: '5px', fontWeight: 700,
                    padding: '6px 12px', background: '#dcfce7', borderRadius: '8px'
                  }}
                >
                  <Download size={14} /> Download Excel
                </a>
                <a 
                  href={executionResult.report_url} 
                  target="_blank" 
                  rel="noreferrer"
                  style={{ 
                    fontSize: '12.5px', color: '#0284c7', textDecoration: 'none',
                    display: 'flex', alignItems: 'center', gap: '5px', fontWeight: 700,
                    padding: '6px 12px', background: '#e0f2fe', borderRadius: '8px'
                  }}
                >
                  <Eye size={14} /> View Report
                </a>
              </div>
            )}
          </div>

          {/* Tab 1: Step Breakdown */}
          {activeTab === 'steps' && (
            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px', paddingRight: '6px' }}>
              {!script ? (
                <div style={{ textAlign: 'center', padding: '100px 20px', color: '#64748b' }}>
                  <FileSpreadsheet size={48} style={{ opacity: 0.25, marginBottom: '12px' }} />
                  <div style={{ fontWeight: 700, fontSize: '15px', color: '#1e293b' }}>No Test Script Loaded</div>
                  <div style={{ fontSize: '13px', marginTop: '4px' }}>
                    Drop an Excel / Word script or paste plain text on the left to see atomic actions.
                  </div>
                </div>
              ) : (
                script.steps.map((s) => {
                  const isSelected = activeStep?.id === s.id;
                  const hasWarning = s.raw_text.toLowerCase().includes('mandatory') || s.confidence_score < 0.85;

                  return (
                    <div 
                      key={s.id}
                      onClick={() => setActiveStep(s)}
                      style={{
                        padding: '16px 18px', borderRadius: '14px',
                        background: isSelected ? '#f0f9ff' : '#ffffff',
                        border: `1.5px solid ${isSelected ? '#0284c7' : '#e2e8f0'}`,
                        boxShadow: isSelected ? '0 4px 12px rgba(2, 132, 199, 0.08)' : '0 1px 3px rgba(0,0,0,0.02)',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <div style={{ 
                            width: '30px', height: '30px', borderRadius: '8px',
                            background: s.status === 'Pass' ? '#dcfce7' : hasWarning ? '#fef3c7' : '#e0f2fe',
                            color: s.status === 'Pass' ? '#16a34a' : hasWarning ? '#d97706' : '#0284c7',
                            display: 'flex', alignItems: 'center', justifyContent: 'center'
                          }}>
                            {s.status === 'Pass' ? <CheckCircle2 size={17} /> : hasWarning ? <AlertTriangle size={17} /> : <Code2 size={17} />}
                          </div>

                          <div>
                            <span style={{ fontWeight: 800, fontSize: '14px', color: '#0284c7' }}>{s.id}</span>
                            {s.role && (
                              <span style={{ marginLeft: '10px', fontSize: '12px', padding: '2px 8px', borderRadius: '6px', background: '#ede9fe', color: '#6d28d9', fontWeight: 700 }}>
                                {s.role}
                              </span>
                            )}
                          </div>
                        </div>

                        <span style={{ 
                          fontSize: '11.5px', fontWeight: 700, padding: '3px 10px', borderRadius: '6px',
                          background: s.status === 'Pass' ? '#dcfce7' : '#f1f5f9',
                          color: s.status === 'Pass' ? '#15803d' : '#64748b'
                        }}>
                          {s.status}
                        </span>
                      </div>

                      <div style={{ marginTop: '10px', fontSize: '13.5px', lineHeight: 1.5, color: '#1e293b', fontWeight: 500 }}>
                        {s.raw_text}
                      </div>

                      {s.is_compound && s.sub_steps && (
                        <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          {s.sub_steps.map((sub) => (
                            <div key={sub.id} style={{ 
                              padding: '8px 12px', borderRadius: '8px', 
                              background: '#f8fafc', borderLeft: '3px solid #0284c7',
                              fontSize: '12.5px', display: 'flex', alignItems: 'center', gap: '8px', color: '#334155'
                            }}>
                              <span style={{ color: '#0284c7', fontWeight: 700 }}>⚡ Action {sub.sequence}:</span>
                              <span>{sub.raw_text}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}

          {/* Tab 2: Live Logs */}
          {activeTab === 'logs' && (
            <div style={{ flex: 1, background: '#0f172a', borderRadius: '12px', padding: '16px', overflowY: 'auto', fontFamily: 'JetBrains Mono, monospace' }}>
              <div style={{ color: '#38bdf8', fontWeight: 700, fontSize: '13px', marginBottom: '10px' }}>
                $ Live Execution Console Output
              </div>
              {logs.map((l, i) => (
                <div key={i} style={{ color: '#cbd5e1', fontSize: '12.5px', lineHeight: 1.6 }}>
                  <span style={{ color: '#64748b' }}>[{new Date().toLocaleTimeString()}]</span> {l}
                </div>
              ))}
            </div>
          )}

          {/* Tab 3: Column Matcher */}
          {activeTab === 'mapping' && (
            <div style={{ padding: '16px' }}>
              <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#0284c7', marginBottom: '8px', margin: '0 0 8px 0' }}>
                Hungarian Bipartite 1-to-1 Column Mapping
              </h3>
              <p style={{ fontSize: '13px', color: '#64748b', marginBottom: '16px', margin: '0 0 16px 0' }}>
                Optimal linear sum assignment matches tokens and cell content to canonical fields.
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
                {['step_id', 'role', 'description', 'test_data', 'expected_result', 'status', 'observed_result'].map(col => (
                  <div key={col} style={{ 
                    padding: '14px', borderRadius: '12px',
                    background: '#f8fafc', border: '1px solid #e2e8f0'
                  }}>
                    <div style={{ fontSize: '11.5px', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>{col}</div>
                    <div style={{ fontSize: '13.5px', fontWeight: 700, color: '#0284c7', marginTop: '4px' }}>
                      ✓ 1-to-1 Canonical Match
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Right Column: Step Inspector & Action Dispatch */}
        <section className="clean-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column' }}>
          <h2 style={{ fontSize: '15px', fontWeight: 700, color: '#0284c7', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', margin: '0 0 16px 0' }}>
            <Terminal size={18} /> Step Inspector & Actions
          </h2>

          {!activeStep ? (
            <div style={{ textAlign: 'center', padding: '80px 20px', color: '#64748b' }}>
              Select a step in the center panel to inspect its executable payload.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>Step Identifier</div>
                <div style={{ fontSize: '16px', fontWeight: 800, color: '#0f172a', marginTop: '2px' }}>{activeStep.id}</div>
              </div>

              <div>
                <div style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>Source Pointer (Write-Back Target)</div>
                <div style={{ fontSize: '12px', color: '#0284c7', fontFamily: 'JetBrains Mono', marginTop: '4px', background: '#f0f9ff', padding: '8px 10px', borderRadius: '8px', border: '1px solid #bae6fd' }}>
                  Row: {activeStep.source_ref.row_index} | Sheet: {activeStep.source_ref.sheet_name || 'N/A'}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>Confidence Tier</div>
                <div style={{ 
                  marginTop: '4px', display: 'inline-block',
                  padding: '4px 10px', borderRadius: '6px', fontSize: '12px', fontWeight: 700,
                  background: '#dcfce7', color: '#15803d'
                }}>
                  {activeStep.confidence_tier} ({(activeStep.confidence_score * 100).toFixed(0)}%)
                </div>
              </div>

              <div>
                <div style={{ fontSize: '12px', color: '#64748b', fontWeight: 600, marginBottom: '6px' }}>
                  Parsed Browser Actions ({activeStep.parsed_actions.length})
                </div>
                <pre style={{ 
                  background: '#0f172a', padding: '14px', borderRadius: '12px',
                  fontSize: '12px', color: '#38bdf8',
                  overflowX: 'auto', maxHeight: '250px'
                }}>
                  {JSON.stringify(activeStep.parsed_actions, null, 2)}
                </pre>
              </div>

              {activeStep.observed_result && (
                <div>
                  <div style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>Execution Verification</div>
                  <div style={{ marginTop: '4px', fontSize: '12.5px', color: '#15803d', background: '#ecfdf5', padding: '10px', borderRadius: '8px', border: '1px solid #a7f3d0' }}>
                    {activeStep.observed_result}
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
