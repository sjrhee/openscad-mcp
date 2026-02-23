import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { STLLoader } from 'three/addons/loaders/STLLoader.js'

export default function StlViewer({ stlUrl }) {
  const containerRef = useRef(null)
  const stateRef = useRef(null)

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

  useEffect(() => {
    if (!stlUrl || !stateRef.current) return
    const { scene, camera, controls } = stateRef.current

    // Remove old mesh
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

        // Center and fit camera
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
      })
  }, [stlUrl])

  return <div ref={containerRef} style={{ width: '100%', minHeight: 500 }} />
}
