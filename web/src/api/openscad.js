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
