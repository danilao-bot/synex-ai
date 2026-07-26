'use client'

import React, { useState, useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { Sidebar } from './Sidebar'
import { SplashScreen } from './SplashScreen'
import { API_BASE_URL } from '../lib/api'

type AppState = 'splash' | 'onboarding' | 'app'

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const pathname = usePathname()
  const router = useRouter()
  // Start in 'splash' — nothing renders behind it until we know the state
  const [appState, setAppState] = useState<AppState>('splash')

  const checkConfiguration = async () => {
    // Fast path: onboarding already completed in this browser
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
        // Use correct field names matching Supabase schema
        const configured = Boolean(data.datahub_url || data.llm_api_key_masked)
        if (configured) {
          localStorage.setItem('synex_onboarding_completed', 'true')
          setAppState('app')
          return
        }
      }
    } catch {
      // Backend unreachable — go to onboarding anyway
    }

    // Not configured — go to onboarding
    setAppState('onboarding')
    if (pathname !== '/onboarding') {
      router.replace('/onboarding')
    }
  }

  const handleSplashComplete = () => {
    // Only check config once splash finishes — no flicker
    checkConfiguration()
  }

  // If user manually navigates to /onboarding, skip straight there
  useEffect(() => {
    if (pathname === '/onboarding' && appState === 'splash') {
      setAppState('onboarding')
    }
  }, [pathname, appState])

  const isOnboarding = pathname === '/onboarding'

  // During splash: show ONLY the splash (black screen + animation)
  if (appState === 'splash') {
    return (
      <div className="flex h-screen w-screen overflow-hidden bg-[#04060C]">
        <SplashScreen onComplete={handleSplashComplete} />
      </div>
    )
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-gray-100 font-sans relative">
      {isOnboarding ? (
        /* Full-Screen Standalone Onboarding (No Sidebar) */
        <div className="flex-1 h-full w-full overflow-y-auto">
          {children}
        </div>
      ) : (
        /* Main Workspace Layout with Sidebar */
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
