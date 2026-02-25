import { useState, useRef, useEffect, useCallback } from 'react'
import { validateScad, renderPng, agentStart, agentEvaluate, agentApply, agentStop } from './api/openscad'
import { useFileWatcher } from './hooks/useFileWatcher'
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

  // Agent state
  const [agentSession, setAgentSession] = useState(null)
  const [agentResult, setAgentResult] = useState(null)
  const [agentHistory, setAgentHistory] = useState([])
  const [agentLoading, setAgentLoading] = useState(false)
  const [agentFeedback, setAgentFeedback] = useState('')
  const [agentMode, setAgentMode] = useState('review')
  const [generateDesc, setGenerateDesc] = useState('')

  function refreshFiles() {
    fetch(`${API_BASE}/files`)
      .then(r => r.json())
      .then(data => setFileList(data.files || []))
      .catch(() => {})
  }

  useEffect(() => { refreshFiles() }, [])

  const busy = loading !== null || agentLoading

  function updatePreview(url) {
    if (prevUrlRef.current && prevUrlRef.current.startsWith('blob:')) URL.revokeObjectURL(prevUrlRef.current)
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

  // Auto-refresh: re-render current view when .scad file changes on disk
  const autoRefreshRef = useRef(null)
  useEffect(() => {
    if (viewMode === '3d' && stlUrl) {
      autoRefreshRef.current = () => handle3DView()
    } else if (previewUrl) {
      autoRefreshRef.current = () => handlePreview()
    } else {
      autoRefreshRef.current = null
    }
  })

  const handleFileChange = useCallback((changedFiles) => {
    if (!scadFile) return
    const currentName = scadFile.split(/[/\\]/).pop()
    if (changedFiles.includes(currentName) && autoRefreshRef.current) {
      setStatus({ type: 'success', message: `File changed: ${currentName}. Auto-refreshing...` })
      autoRefreshRef.current()
    }
  }, [scadFile])

  const handleNewFiles = useCallback(() => { refreshFiles() }, [])

  useFileWatcher({
    enabled: !busy,
    interval: 2000,
    onChange: handleFileChange,
    onNewFiles: handleNewFiles,
  })

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

  // --- Agent handlers ---

  async function handleAgentStart() {
    setAgentLoading(true)
    setStatus(null)
    setAgentResult(null)
    setAgentHistory([])
    try {
      let result
      if (agentMode === 'generate') {
        if (!generateDesc.trim()) return
        result = await agentStart('', 'generate', generateDesc)
        setScadFile(result.scad_file)
        refreshFiles()
      } else {
        if (!scadFile.trim()) return
        result = await agentStart(scadFile)
      }
      setAgentSession(result)
      const evalResult = await agentEvaluate(result.session_id)
      setAgentResult(evalResult)
      setAgentHistory(evalResult.history)
      updatePreview(`data:image/png;base64,${evalResult.preview_base64}`)
      setViewMode('png')
    } catch (e) {
      setStatus({ type: 'error', message: e.message })
    } finally {
      setAgentLoading(false)
    }
  }

  async function handleAgentApplyAction() {
    if (!agentSession) return
    setAgentLoading(true)
    try {
      await agentApply(agentSession.session_id)
      setStatus({ type: 'success', message: 'Code applied. Evaluating next iteration...' })
      const evalResult = await agentEvaluate(agentSession.session_id)
      setAgentResult(evalResult)
      setAgentHistory(evalResult.history)
      updatePreview(`data:image/png;base64,${evalResult.preview_base64}`)
      setViewMode('png')
    } catch (e) {
      setStatus({ type: 'error', message: e.message })
    } finally {
      setAgentLoading(false)
    }
  }

  async function handleAgentSkip() {
    if (!agentSession) return
    setAgentLoading(true)
    try {
      const evalResult = await agentEvaluate(agentSession.session_id)
      setAgentResult(evalResult)
      setAgentHistory(evalResult.history)
      updatePreview(`data:image/png;base64,${evalResult.preview_base64}`)
      setViewMode('png')
    } catch (e) {
      setStatus({ type: 'error', message: e.message })
    } finally {
      setAgentLoading(false)
    }
  }

  async function handleAgentFeedback() {
    if (!agentSession || !agentFeedback.trim()) return
    setAgentLoading(true)
    try {
      const evalResult = await agentEvaluate(agentSession.session_id, agentFeedback)
      setAgentResult(evalResult)
      setAgentHistory(evalResult.history)
      setAgentFeedback('')
      updatePreview(`data:image/png;base64,${evalResult.preview_base64}`)
      setViewMode('png')
    } catch (e) {
      setStatus({ type: 'error', message: e.message })
    } finally {
      setAgentLoading(false)
    }
  }

  async function handleAgentStopAction() {
    if (!agentSession) return
    try {
      await agentStop(agentSession.session_id)
    } catch { /* ignore cleanup errors */ }
    setAgentSession(null)
    setAgentResult(null)
    setAgentHistory([])
    setAgentFeedback('')
  }

  function scoreClass(score) {
    if (score >= 8) return 'good'
    if (score >= 5) return 'fair'
    return 'poor'
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

      {/* Agent mode selector */}
      {!agentSession && (
        <div className="agent-mode-selector">
          <button className={`agent-tab ${agentMode === 'review' ? 'active' : ''}`} onClick={() => setAgentMode('review')}>
            Review
          </button>
          <button className={`agent-tab ${agentMode === 'generate' ? 'active' : ''}`} onClick={() => setAgentMode('generate')}>
            Generate
          </button>
          {agentMode === 'generate' && (
            <input
              className="generate-input"
              type="text"
              placeholder="Describe the 3D design..."
              value={generateDesc}
              onChange={(e) => setGenerateDesc(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !busy && handleAgentStart()}
            />
          )}
        </div>
      )}

      <div className="actions">
        <button className="btn-preview" disabled={busy || !scadFile.trim()} onClick={handlePreview}>
          {loading === 'preview' ? 'Rendering...' : 'Preview PNG'}
        </button>
        <button className="btn-3d" disabled={busy || !scadFile.trim()} onClick={handle3DView}>
          {loading === '3d' ? 'Loading...' : '3D View'}
        </button>
        <button className="btn-validate" disabled={busy || !scadFile.trim()} onClick={handleValidate}>
          {loading === 'validate' ? 'Validating...' : 'Validate'}
        </button>
        <button className="btn-stl" disabled={busy || !scadFile.trim()} onClick={handleDownloadStl}>
          {loading === 'export' ? 'Exporting HQ...' : 'Download STL'}
        </button>
        <button
          className="btn-review"
          disabled={busy || (!scadFile.trim() && agentMode !== 'generate') || (agentMode === 'generate' && !generateDesc.trim())}
          onClick={handleAgentStart}
        >
          {agentLoading && !agentResult ? 'Starting...' : agentSession ? 'Reviewing...' : 'AI Review'}
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

      {/* Agent Panel */}
      {agentSession && (
        <div className="agent-panel">
          <div className="agent-header">
            <h3>Design Agent {agentSession.mode === 'generate' ? '(Generate)' : '(Review)'}</h3>
            <button className="btn-stop" onClick={handleAgentStopAction} disabled={agentLoading}>Stop</button>
          </div>

          {agentLoading && (
            <div className="status loading">Evaluating with Claude... (~25 seconds)</div>
          )}

          {agentResult && !agentLoading && (
            <>
              <div className="agent-score">
                <span className={`score-badge ${scoreClass(agentResult.score)}`}>
                  {agentResult.score}/10
                </span>
                <span className="score-summary">{agentResult.summary}</span>
              </div>

              {agentResult.criteria_scores && Object.keys(agentResult.criteria_scores).length > 0 && (
                <div className="agent-criteria">
                  {Object.entries(agentResult.criteria_scores).map(([key, val]) => (
                    <div key={key} className="criterion">
                      <span className="criterion-name">{key.replace(/_/g, ' ')}</span>
                      <div className="criterion-bar">
                        <div className="criterion-fill" style={{ width: `${val * 10}%` }} />
                      </div>
                      <span className="criterion-score">{val}</span>
                    </div>
                  ))}
                </div>
              )}

              {agentResult.issues.length > 0 && (
                <div className="agent-issues">
                  <h4>Issues</h4>
                  <ul>
                    {agentResult.issues.map((issue, i) => <li key={i}>{issue}</li>)}
                  </ul>
                </div>
              )}

              {!agentResult.converged && (
                <div className="agent-actions">
                  {agentResult.has_suggested_code && (
                    <button className="btn-apply" disabled={agentLoading} onClick={handleAgentApplyAction}>
                      Apply Changes
                    </button>
                  )}
                  <button className="btn-skip" disabled={agentLoading} onClick={handleAgentSkip}>
                    Skip
                  </button>
                </div>
              )}

              {agentResult.converged && (
                <div className="status success">
                  {agentResult.converge_reason === 'target_reached'
                    ? `Target score reached (${agentResult.score}/10)`
                    : agentResult.converge_reason === 'stagnant'
                      ? 'Score stagnant — no further improvement'
                      : 'No further improvement possible'}
                </div>
              )}

              {!agentResult.converged && (
                <div className="agent-feedback">
                  <textarea
                    placeholder="Enter feedback for next evaluation..."
                    value={agentFeedback}
                    onChange={(e) => setAgentFeedback(e.target.value)}
                    rows={2}
                  />
                  <button
                    className="btn-feedback"
                    disabled={agentLoading || !agentFeedback.trim()}
                    onClick={handleAgentFeedback}
                  >
                    Send Feedback
                  </button>
                </div>
              )}

              {agentHistory.length > 1 && (
                <div className="agent-history">
                  <h4>Score Progression</h4>
                  <div className="score-progression">
                    {agentHistory.map((h, i) => (
                      <span key={i} className={`history-score ${scoreClass(h.score)}`}>
                        {h.score}{i < agentHistory.length - 1 && ' → '}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
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
