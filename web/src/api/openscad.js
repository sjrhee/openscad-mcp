const API_BASE = '/api'

export async function validateScad(scadFile) {
  const res = await fetch(`${API_BASE}/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scad_file: scadFile }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Validation failed')
  }
  return res.json()
}

export async function renderPng(scadFile, width = 1024, height = 768) {
  const res = await fetch(`${API_BASE}/render/png`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scad_file: scadFile, width, height }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Render failed')
  }
  const blob = await res.blob()
  return URL.createObjectURL(blob)
}

// --- Design Agent API ---

export async function agentStart(scadFile, mode = 'review', description = '', outputName = null) {
  const res = await fetch(`${API_BASE}/agent/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scad_file: scadFile, mode, description, output_name: outputName }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Agent start failed')
  }
  return res.json()
}

export async function agentEvaluate(sessionId, feedback = null) {
  const res = await fetch(`${API_BASE}/agent/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, feedback }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Evaluation failed')
  }
  return res.json()
}

export async function agentApply(sessionId) {
  const res = await fetch(`${API_BASE}/agent/apply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Apply failed')
  }
  return res.json()
}

export async function agentStop(sessionId) {
  const res = await fetch(`${API_BASE}/agent/stop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Stop failed')
  }
  return res.json()
}

export async function renderStl(scadFile) {
  const res = await fetch(`${API_BASE}/render/stl`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scad_file: scadFile }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'STL export failed')
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = scadFile.split(/[/\\]/).pop().replace(/\.scad$/, '.stl')
  a.click()
  URL.revokeObjectURL(url)
}
