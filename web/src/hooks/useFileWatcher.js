import { useEffect, useRef } from 'react'

const API_BASE = '/api'

export function useFileWatcher({ enabled = true, interval = 2000, onChange, onNewFiles }) {
  const prevRef = useRef(null)
  const onChangeRef = useRef(onChange)
  const onNewFilesRef = useRef(onNewFiles)

  onChangeRef.current = onChange
  onNewFilesRef.current = onNewFiles

  useEffect(() => {
    if (!enabled) return

    async function poll() {
      try {
        const res = await fetch(`${API_BASE}/files/status`)
        if (!res.ok) return
        const { files: current } = await res.json()
        const prev = prevRef.current

        if (prev !== null) {
          const changed = []
          const added = []

          for (const [name, mtime] of Object.entries(current)) {
            if (!(name in prev)) {
              added.push(name)
            } else if (prev[name] !== mtime) {
              changed.push(name)
            }
          }

          if (changed.length > 0 && onChangeRef.current) {
            onChangeRef.current(changed)
          }
          if (added.length > 0 && onNewFilesRef.current) {
            onNewFilesRef.current(added)
          }
        }

        prevRef.current = current
      } catch {
        // Backend unreachable — skip silently
      }
    }

    poll()
    const timer = setInterval(poll, interval)
    return () => clearInterval(timer)
  }, [enabled, interval])
}
