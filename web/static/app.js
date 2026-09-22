let currentScriptId = null;

async function uploadScript(file) {
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  document.getElementById('execStatus').innerText = 'Parsing script with Hungarian matcher & Step Splitter...';

  try {
    const res = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await res.json();
    if (data.ok) {
      currentScriptId = data.scripts[0].script_id;
      document.getElementById('scriptMeta').innerText = `${data.scripts[0].script_id} — ${data.scripts[0].title}`;
      document.getElementById('execStatus').innerText = `✓ Loaded ${data.scripts[0].steps.length} steps successfully.`;
      renderSteps(data.scripts[0].steps);
    }
  } catch(e) {
    document.getElementById('execStatus').innerText = 'Error parsing: ' + e;
  }
}

function renderSteps(steps) {
  const tbody = document.getElementById('stepsTable');
  tbody.innerHTML = '';
  steps.forEach(s => {
    let substepsHtml = '';
    if (s.is_compound && s.sub_steps) {
      substepsHtml = s.sub_steps.map(sub => `
        <div class="substep-badge">
          ⚡ <b>Action ${sub.sequence}:</b> ${sub.raw_text}
        </div>
      `).join('');
    }
    tbody.innerHTML += `
      <tr>
        <td style="font-weight: 700; color: var(--accent);">${s.id}</td>
        <td><span style="color: #cbd5e1; font-weight: 500;">${s.role || '-'}</span></td>
        <td>
          <div style="font-weight: 500;">${s.raw_text}</div>
          ${substepsHtml}
        </td>
        <td><span class="badge badge-ready">${s.status}</span></td>
      </tr>
    `;
  });
}

async function executeCurrentScript() {
  if (!currentScriptId) {
    alert('Please upload a test script first!');
    return;
  }
  document.getElementById('execStatus').innerHTML = '<span style="color: var(--accent);">⏳ Automated execution in progress in real Playwright browser...</span>';
  
  try {
    const res = await fetch(`/api/execute/${currentScriptId}`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      document.getElementById('execStatus').innerHTML = `<span style="color: var(--pass);">✓ Completed!</span> <a href="${data.report_url}" target="_blank" style="color: var(--accent); margin-left: 8px; text-decoration: underline;">View HTML Report</a>`;
      renderSteps(data.script.steps);
    }
  } catch(e) {
    document.getElementById('execStatus').innerText = 'Execution error: ' + e;
  }
}
