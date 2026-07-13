// src/components/SplashScreen.jsx
import { useEffect, useState, Suspense, useRef, useMemo } from 'react'
import { Canvas, useFrame, useLoader } from '@react-three/fiber'
import { OrbitControls, Points, PointMaterial } from '@react-three/drei'
import * as THREE from 'three'
import { TextureLoader } from 'three'

const STATUS_MESSAGES = [
  'Connexion sécurisée…',
  'Chargement des indicateurs…',
  'Analyse des menaces actives…',
  'Synchronisation MITRE ATT&CK…',
  'Plateforme prête.',
]

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
      const phi = Math.acos(2 * Math.random() - 1)
      const r = 1.63
      pts[i * 3]     = r * Math.sin(phi) * Math.cos(theta)
      pts[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      pts[i * 3 + 2] = r * Math.cos(phi)
    }
    return pts
  }, [])
  useFrame((state) => {
    if (ref.current) ref.current.rotation.y = state.clock.elapsedTime * 0.05
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

export default function SplashScreen({ onDone, dataReady }) {
  const [msgIndex, setMsgIndex] = useState(0)
  const [visible, setVisible] = useState(true)
  const [minElapsed, setMinElapsed] = useState(false)

  // Défile les messages toutes les 600ms
  useEffect(() => {
    const last = STATUS_MESSAGES.length - 1
    if (msgIndex >= last) return
    const t = setTimeout(() => setMsgIndex(i => Math.min(i + 1, last)), 600)
    return () => clearTimeout(t)
  }, [msgIndex])

  // Durée minimum de 2.5s
  useEffect(() => {
    const t = setTimeout(() => setMinElapsed(true), 2500)
    return () => clearTimeout(t)
  }, [])

  // Quand les deux conditions sont remplies : données prêtes + durée min écoulée
  useEffect(() => {
    if (!dataReady || !minElapsed) return
    // Affiche "Plateforme prête." 400ms avant de fermer
    setMsgIndex(STATUS_MESSAGES.length - 1)
    const t = setTimeout(() => {
      setVisible(false)
      setTimeout(onDone, 400) // laisse le temps au fade-out
    }, 600)
    return () => clearTimeout(t)
  }, [dataReady, minElapsed, onDone])

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#faf8f5]"
      style={{
        transition: 'opacity 0.4s ease',
        opacity: visible ? 1 : 0,
      }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 mb-6">
        <img src="/Logo-Antic.png" alt="ANTIC" className="h-10 object-contain" />
        <div className="text-left">
          <p className="text-[10px] uppercase tracking-[0.15em] text-[#a8988a]">
            Threat Intelligence Platform
          </p>
          <p
            className="text-lg font-semibold text-[#2c1810]"
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}
          >
            ANTIC · CIRT
          </p>
        </div>
      </div>

      {/* Globe */}
      <div style={{ width: 360, height: 360 }}>
        <Canvas
          camera={{ position: [0, 0, 4.2], fov: 45 }}
          gl={{ antialias: true, alpha: true }}
          style={{ background: 'transparent' }}
        >
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
            enableZoom={false}
            enablePan={false}
            autoRotate={true}
            autoRotateSpeed={0.8}
            minPolarAngle={Math.PI / 6}
            maxPolarAngle={Math.PI * 5 / 6}
          />
        </Canvas>
      </div>

      {/* Message de statut */}
      <div className="mt-4 h-6 flex items-center justify-center">
        <p
          key={msgIndex}
          className="text-sm text-[#8b7355] font-medium"
          style={{ animation: 'fadeIn 0.4s ease' }}
        >
          {STATUS_MESSAGES[msgIndex]}
        </p>
      </div>

      {/* Barre de progression */}
      <div className="mt-3 w-48 h-0.5 bg-[#ede8e3] rounded-full overflow-hidden">
        <div
          className="h-full bg-[#c4a882] rounded-full"
          style={{
            width: `${((msgIndex + 1) / STATUS_MESSAGES.length) * 100}%`,
            transition: 'width 0.6s ease',
          }}
        />
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}