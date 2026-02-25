import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { STLLoader } from 'three/addons/loaders/STLLoader.js'

// Pick a "nice" round number for scale bar
const NICE = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
function niceScale(rawMm) {
  for (const n of NICE) {
    if (n >= rawMm * 0.5) return n
  }
  return NICE[NICE.length - 1]
}

function formatMm(mm) {
  return mm >= 10 ? `${mm} mm` : `${mm} mm`
}

export default function StlViewer({ stlUrl }) {
  const containerRef = useRef(null)
  const stateRef = useRef(null)
  const scaleBarRef = useRef(null)
  const scaleLabelRef = useRef(null)
  const [dims, setDims] = useState(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const width = el.clientWidth
    const height = 500

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0xf5f5dc)

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 10000)
    camera.position.set(0, -200, 150)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(window.devicePixelRatio)
    el.appendChild(renderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true

    const ambientLight = new THREE.AmbientLight(0x404040, 2)
    scene.add(ambientLight)
    const dirLight = new THREE.DirectionalLight(0xffffff, 2)
    dirLight.position.set(1, -1, 2)
    scene.add(dirLight)
    const dirLight2 = new THREE.DirectionalLight(0xffffff, 1)
    dirLight2.position.set(-1, 1, -1)
    scene.add(dirLight2)

    stateRef.current = { scene, camera, renderer, controls }

    let animId
    function animate() {
      animId = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
      updateScaleBar(camera, controls, renderer)
    }
    animate()

    const onResize = () => {
      const w = el.clientWidth
      camera.aspect = w / height
      camera.updateProjectionMatrix()
      renderer.setSize(w, height)
    }
    window.addEventListener('resize', onResize)

    return () => {
      window.removeEventListener('resize', onResize)
      cancelAnimationFrame(animId)
      controls.dispose()
      renderer.dispose()
      el.removeChild(renderer.domElement)
      stateRef.current = null
    }
  }, [])

  function updateScaleBar(camera, controls, renderer) {
    const bar = scaleBarRef.current
    const label = scaleLabelRef.current
    if (!bar || !label) return

    // Calculate mm per pixel at the target distance
    const dist = camera.position.distanceTo(controls.target)
    const fovRad = camera.fov * Math.PI / 180
    const visibleHeight = 2 * dist * Math.tan(fovRad / 2)
    const screenHeight = renderer.domElement.clientHeight
    const mmPerPx = visibleHeight / screenHeight

    // Target bar: ~120px on screen
    const rawMm = mmPerPx * 120
    const niceMm = niceScale(rawMm)
    const barPx = niceMm / mmPerPx

    bar.style.width = `${Math.round(barPx)}px`
    label.textContent = formatMm(niceMm)
  }

  useEffect(() => {
    if (!stlUrl || !stateRef.current) return
    const { scene, camera, controls } = stateRef.current

    const old = scene.getObjectByName('stlMesh')
    if (old) {
      old.geometry.dispose()
      old.material.dispose()
      scene.remove(old)
    }

    const loader = new STLLoader()
    fetch(stlUrl)
      .then(r => r.arrayBuffer())
      .then(buf => {
        const geometry = loader.parse(buf)
        geometry.computeVertexNormals()

        const material = new THREE.MeshPhongMaterial({
          color: 0xb8a000,
          specular: 0x333333,
          shininess: 40,
        })
        const mesh = new THREE.Mesh(geometry, material)
        mesh.name = 'stlMesh'
        scene.add(mesh)

        geometry.computeBoundingBox()
        const box = geometry.boundingBox
        const center = new THREE.Vector3()
        box.getCenter(center)
        mesh.position.sub(center)

        const size = new THREE.Vector3()
        box.getSize(size)
        const maxDim = Math.max(size.x, size.y, size.z)
        camera.position.set(0, -maxDim * 1.5, maxDim)
        controls.target.set(0, 0, 0)
        controls.update()

        setDims({ x: size.x.toFixed(1), y: size.y.toFixed(1), z: size.z.toFixed(1) })
      })
  }, [stlUrl])

  return (
    <div style={{ position: 'relative', width: '100%', minHeight: 500 }}>
      <div ref={containerRef} style={{ width: '100%', minHeight: 500 }} />

      {/* Scale bar - bottom left */}
      <div style={{
        position: 'absolute', bottom: 12, left: 12,
        display: 'flex', alignItems: 'center', gap: 6,
        background: 'rgba(0,0,0,0.55)', padding: '4px 10px',
        borderRadius: 4, fontFamily: 'monospace', fontSize: 12, color: '#fff',
      }}>
        <div ref={scaleBarRef} style={{
          width: 120, height: 0,
          borderTop: '2px solid #fff',
          borderLeft: '2px solid #fff',
          borderRight: '2px solid #fff',
          boxSizing: 'border-box',
          paddingTop: 4,
        }} />
        <span ref={scaleLabelRef}>—</span>
      </div>

      {/* Dimensions - bottom right */}
      {dims && (
        <div style={{
          position: 'absolute', bottom: 12, right: 12,
          background: 'rgba(0,0,0,0.55)', color: '#fff',
          padding: '4px 10px', borderRadius: 4, fontSize: 12, fontFamily: 'monospace',
        }}>
          Bounding: {dims.x} x {dims.y} x {dims.z} mm
        </div>
      )}
    </div>
  )
}
