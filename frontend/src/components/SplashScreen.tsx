'use client'

import React, { useEffect, useRef, useState } from 'react'

export const SplashScreen: React.FC<{ onComplete?: () => void }> = ({ onComplete }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const animationRef = useRef<number | null>(null)
  const [statusText, setStatusText] = useState('Initializing Synex Engine...')
  const [fadeOut, setFadeOut] = useState(false)

  const size = 180
  const color = '#6366F1' // Primary Indigo Accent

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    canvas.width = size
    canvas.height = size

    const centerX = canvas.width / 2
    const centerY = canvas.height / 2
    let time = 0

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      const numRays = 8
      for (let i = 0; i < numRays; i++) {
        const angle = (i / numRays) * Math.PI * 2
        const pulse = Math.sin(time * 0.03 + i * 0.5) * (size * 0.2) + (size * 0.25)

        ctx.beginPath()
        ctx.moveTo(centerX, centerY)
        const x = centerX + Math.cos(angle) * pulse
        const y = centerY + Math.sin(angle) * pulse
        ctx.lineTo(x, y)

        const opacity = 0.3 + Math.sin(time * 0.03 + i * 0.5) * 0.7
        ctx.strokeStyle = `${color}${Math.floor(opacity * 255).toString(16).padStart(2, '0')}`
        ctx.lineWidth = 2
        ctx.stroke()

        ctx.beginPath()
        ctx.arc(x, y, 3.5, 0, Math.PI * 2)
        ctx.fillStyle = '#00E5FF' // Cyan node tips
        ctx.fill()
      }

      // Center dot
      ctx.beginPath()
      ctx.arc(centerX, centerY, 5, 0, Math.PI * 2)
      ctx.fillStyle = '#6366F1'
      ctx.fill()

      time++
      animationRef.current = requestAnimationFrame(animate)
    }

    animate()

    // 1.8 Second Sequence Timing
    const t1 = setTimeout(() => setStatusText('Verifying Vault Connection...'), 600)
    const t2 = setTimeout(() => setStatusText('Synex Engine Ready.'), 1300)
    const t3 = setTimeout(() => {
      setFadeOut(true)
      setTimeout(() => {
        if (onComplete) onComplete()
      }, 400)
    }, 1800)

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
    }
  }, [onComplete])

  return (
    <div className={`fixed inset-0 bg-[#04060C] z-50 flex flex-col items-center justify-center transition-opacity duration-500 isolate ${fadeOut ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}>
      {/* Background Ambient Glow */}
      <div className="absolute w-[400px] h-[400px] bg-primary/10 rounded-full blur-3xl pointer-events-none animate-pulse" />

      {/* Canvas Radial Pulse Loader */}
      <div className="relative mb-6 flex items-center justify-center">
        <canvas ref={canvasRef} className="relative z-10" />
        <div className="absolute inset-0 bg-primary opacity-15 blur-2xl rounded-full" />
      </div>

      {/* Brand Title */}
      <h1 className="text-2xl font-bold text-white tracking-wider font-display mb-1">Synex</h1>
      <p className="text-[10px] font-mono text-gray-500 uppercase tracking-widest mb-6">Metadata-First Autonomous Agent</p>

      {/* Status Progress */}
      <div className="flex items-center gap-3 bg-surface/80 border border-surfaceBorder px-4 py-2 rounded-full shadow-lg backdrop-blur-md">
        <span className="w-2 h-2 rounded-full bg-accent animate-ping" />
        <span className="text-xs font-mono text-gray-300 min-w-[210px] text-center">{statusText}</span>
      </div>
    </div>
  )
}
