import { useState, useRef, useEffect } from 'react'
import { validateScad, renderPng } from './api/openscad'
import StlViewer from './StlViewer'
import './App.css'

const API_BASE = '/api'

function App() {
  const [scadFile, setScadFile] = useState('')
  const [fileList, setFileList] = useState([])
  const [previewUrl, setPreviewUrl] = useState(null)
  const [stlUrl, setStlUrl] = useState(null)
  const [viewMode, setViewMode] = useState('png')
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(null)
  const prevUrlRef = useRef(null)
  const prevStlRef = useRef(null)

  function refreshFiles() {
    fetch(`${API_BASE}/files`)
      .then(r => r.json())
      .then(data => setFileList(data.files || []))
      .catch(() => {})
  }

  useEffect(() => { refreshFiles() }, [])

  const busy = loading !== null

  function updatePreview(url) {
    if (prevUrlRef.current) URL.revokeObjectURL(prevUrlRef.current)
    prevUrlRef.current = url
    setPreviewUrl(url)
  }

  function updateStl(url) {
    if (prevStlRef.current) URL.revokeObjectURL(prevStlRef.current)
    prevStlRef.current = url
    setStlUrl(url)
  }

  async function handlePreview() {
    if (!scadFile.trim()) return
    setLoading('preview')
    setStatus(null)
    try {
      const url = await renderPng(scadFile)
      updatePreview(url)
      setViewMode('png')
      setStatus({ type: 'success', message: 'Preview rendered.' })
    } catch (e) {
      setStatus({ type: 'error', message: e.message })
    } finally {
      setLoading(null)
    }
  }

  async function fetchStl(quality) {
    const res = await fetch(`${API_BASE}/render/stl`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scad_file: scadFile, quality }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'STL render failed')
    }
    return res.blob()
  }

  async function handle3DView() {
    if (!scadFile.trim()) return
    setLoading('3d')
    setStatus(null)
    try {
      const blob = await fetchStl('preview')
      const url = URL.createObjectURL(blob)
      updateStl(url)
      setViewMode('3d')
      setStatus({ type: 'success', message: '3D view loaded. Drag to rotate, scroll to zoom.' })
    } catch (e) {
      setStatus({ type: 'error', message: e.message })
    } finally {
      setLoading(null)
    }
  }

  async function handleDownloadStl() {
    if (!scadFile.trim()) return
    setLoading('export')
    setStatus(null)
    try {
      const blob = await fetchStl('export')
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = scadFile.split(/[/\\]/).pop().replace(/\.scad$/, '.stl')
      a.click()
      URL.revokeObjectURL(url)
      setStatus({ type: 'success', message: `STL exported (${(blob.size / 1024).toFixed(0)} KB, high quality).` })
    } catch (e) {
      setStatus({ type: 'error', message: e.message })
    } finally {
      setLoading(null)
    }
  }

  async function handleValidate() {
    if (!scadFile.trim()) return
    setLoading('validate')
    setStatus(null)
    try {
      const result = await validateScad(scadFile)
      setStatus({
        type: result.success ? 'success' : 'error',
        message: result.success ? 'Syntax is valid.' : result.message,
      })
    } catch (e) {
      setStatus({ type: 'error', message: e.message })
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="app">
      <h1>OpenSCAD Viewer</h1>

      <div className="input-group">
        <select
          value={scadFile}
          onChange={(e) => setScadFile(e.target.value)}
          onFocus={refreshFiles}
        >
          <option value="">-- Select a .scad file --</option>
          {fileList.map(f => (
            <option key={f.path} value={f.path}>{f.name}</option>
          ))}
        </select>
      </div>

      <div className="actions">
        <button className="btn-preview" disabled={busy} onClick={handlePreview}>
          {loading === 'preview' ? 'Rendering...' : 'Preview PNG'}
        </button>
        <button className="btn-3d" disabled={busy} onClick={handle3DView}>
          {loading === '3d' ? 'Loading...' : '3D View'}
        </button>
        <button className="btn-validate" disabled={busy} onClick={handleValidate}>
          {loading === 'validate' ? 'Validating...' : 'Validate'}
        </button>
        <button className="btn-stl" disabled={busy} onClick={handleDownloadStl}>
          {loading === 'export' ? 'Exporting HQ...' : 'Download STL'}
        </button>
      </div>

      {status && (
        <div className={`status ${status.type === 'success' ? 'success' : 'error'}`}>
          {status.message}
        </div>
      )}

      {loading && (
        <div className="status loading">Processing...</div>
      )}

      <div className="preview-area">
        {viewMode === '3d' && stlUrl ? (
          <StlViewer stlUrl={stlUrl} />
        ) : previewUrl ? (
          <img src={previewUrl} alt="OpenSCAD preview" />
        ) : (
          <span className="placeholder">Preview will appear here</span>
        )}
      </div>
    </div>
  )
}

export default App
