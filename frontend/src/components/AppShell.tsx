'use client'

import React, { useState, useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { Sidebar } from './Sidebar'
import { SplashScreen } from './SplashScreen'
import { API_BASE_URL } from '../lib/api'

type AppState = 'splash' | 'navigating' | 'onboarding' | 'app'

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const pathname = usePathname()
  const router = useRouter()
  const [appState, setAppState] = useState<AppState>('splash')

  const checkConfiguration = async () => {
    // Fast path: already completed in this browser
    const isCompleted =
      typeof window !== 'undefined' &&
      localStorage.getItem('synex_onboarding_completed') === 'true'

    if (isCompleted) {
      setAppState('app')
      return
    }

    // Check backend for saved settings
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/settings`)
      if (res.ok) {
        const data = await res.json()
        const configured = Boolean(data.datahub_url || data.llm_api_key_masked)
        if (configured) {
          localStorage.setItem('synex_onboarding_completed', 'true')
          setAppState('app')
          return
        }
      }
    } catch {
      // Backend unreachable — send to onboarding anyway
    }

    // Not configured — navigate to onboarding.
    // Use 'navigating' to show a blank dark screen while the route change completes,
    // preventing any flash of workspace content.
    if (pathname !== '/onboarding') {
      setAppState('navigating')
      router.replace('/onboarding')
    } else {
      setAppState('onboarding')
    }
  }

  // Once router.replace fires and pathname becomes '/onboarding', lift to 'onboarding'
  useEffect(() => {
    if (pathname === '/onboarding' && appState === 'navigating') {
      setAppState('onboarding')
    }
  }, [pathname, appState])

  // If the user manually visits /onboarding while splash is still up, skip straight there
  useEffect(() => {
    if (pathname === '/onboarding' && appState === 'splash') {
      setAppState('onboarding')
    }
  }, [pathname, appState])

  // ── RENDER ────────────────────────────────────────────────────────────────

  // Phase 1: Splash only
  if (appState === 'splash') {
    return (
      <div className="flex h-screen w-screen overflow-hidden bg-[#04060C]">
        <SplashScreen onComplete={checkConfiguration} />
      </div>
    )
  }

  // Phase 2: Blank dark screen while router.replace is in flight (zero flicker)
  if (appState === 'navigating') {
    return <div className="h-screen w-screen bg-[#04060C]" />
  }

  // Phase 3: Onboarding (full-screen, no sidebar)
  if (appState === 'onboarding') {
    return (
      <div className="flex h-screen w-screen overflow-hidden bg-[#04060C] text-gray-100 font-sans">
        <div className="flex-1 h-full w-full overflow-y-auto">
          {children}
        </div>
      </div>
    )
  }

  // Phase 4: Main workspace (sidebar + content)
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-gray-100 font-sans relative">
      {pathname === '/onboarding' ? (
        <div className="flex-1 h-full w-full overflow-y-auto">{children}</div>
      ) : (
        <>
          <Sidebar />
          <main className="flex-1 flex flex-col overflow-hidden h-full min-w-0 relative z-10">
            {children}
          </main>
        </>
      )}
    </div>
  )
}
