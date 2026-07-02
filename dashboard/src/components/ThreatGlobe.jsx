// src/components/ThreatGlobe.jsx
import { useRef, useMemo, Suspense } from 'react'
import { Canvas, useFrame, useLoader } from '@react-three/fiber'
import { OrbitControls, Points, PointMaterial } from '@react-three/drei'
import * as THREE from 'three'
import { TextureLoader } from 'three'

function Globe() {
  const meshRef = useRef()
  const texture = useLoader(TextureLoader, '/world-map.png')

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[1.68, 64, 64]} />
      <meshStandardMaterial
        map={texture}
        transparent
        opacity={0.95}
        emissive={new THREE.Color('#c4a882')}
        emissiveIntensity={0.08}
      />
    </mesh>
  )
}

function ThreatPoints() {
  const ref = useRef()

  const positions = useMemo(() => {
    const pts = new Float32Array(300 * 3)
    for (let i = 0; i < 300; i++) {
      const theta = Math.random() * Math.PI * 2
      const phi   = Math.acos(2 * Math.random() - 1)
      const r     = 1.63
      pts[i * 3]     = r * Math.sin(phi) * Math.cos(theta)
      pts[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      pts[i * 3 + 2] = r * Math.cos(phi)
    }
    return pts
  }, [])

  useFrame((state) => {
    if (ref.current) {
      ref.current.rotation.y = state.clock.elapsedTime * 0.05
    }
  })

  return (
    <Points ref={ref} positions={positions} stride={3} frustumCulled={false}>
      <PointMaterial
        transparent
        color="#ef4444"
        size={0.03}
        sizeAttenuation
        depthWrite={false}
        opacity={0.9}
      />
    </Points>
  )
}

function Atmosphere() {
  return (
    <mesh>
      <sphereGeometry args={[1.6, 64, 64]} />
      <meshStandardMaterial
        color="#c4a882"
        transparent
        opacity={0.06}
        side={THREE.BackSide}
      />
    </mesh>
  )
}

export default function ThreatGlobe({ height = 380 }) {
  return (
    <div style={{ height, width: '100%' }} className="rounded-2xl overflow-hidden">
      <Canvas
        camera={{ position: [0, 0, 4.2], fov: 45 }}
        gl={{ antialias: true, alpha: true }}
        style={{ background: 'transparent' }}
      >
        {/* Lumières multiples pour un effet 3D réaliste */}
        <ambientLight intensity={0.4} />
        <directionalLight position={[5, 3, 5]}   intensity={1.5} color="#fff8f0" />
        <directionalLight position={[-5, -3, -2]} intensity={0.5} color="#c4a882" />
        <pointLight       position={[0, 5, 0]}    intensity={0.8} color="#ffffff" />
        <pointLight       position={[3, -2, 3]}   intensity={0.4} color="#8b7355" />

        <Suspense fallback={null}>
          <Globe />
          <ThreatPoints />
          <Atmosphere />
        </Suspense>

        <OrbitControls
          enableZoom={true}
          enablePan={false}
          autoRotate={true}
          autoRotateSpeed={0.5}
          minPolarAngle={Math.PI / 6}
          maxPolarAngle={Math.PI * 5 / 6}
          rotateSpeed={0.6}
          zoomSpeed={0.5}
          minDistance={3.5}
          maxDistance={8}
        />
      </Canvas>
    </div>
  )
}