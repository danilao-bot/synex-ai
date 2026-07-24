'use client'

import React, { useState, useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { Sidebar } from './Sidebar'
import { SplashScreen } from './SplashScreen'
import { API_BASE_URL } from '../lib/api'

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const pathname = usePathname()
  const router = useRouter()
  const [showSplash, setShowSplash] = useState(true)
  const [isConfigured, setIsConfigured] = useState<boolean | null>(null)

  useEffect(() => {
    // Check backend configuration on app load
    fetch(`${API_BASE_URL}/api/v1/settings`)
      .then(res => res.json())
      .then(data => {
        const configured = Boolean(data.datahub_gms_url || data.openai_api_key_masked)
        setIsConfigured(configured)
        if (!configured && pathname !== '/onboarding') {
          router.replace('/onboarding')
        }
      })
      .catch(() => {
        setIsConfigured(false)
        if (pathname !== '/onboarding') {
          router.replace('/onboarding')
        }
      })
  }, [pathname, router])

  const handleSplashComplete = () => {
    setShowSplash(false)
  }

  const isOnboarding = pathname === '/onboarding'

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-gray-100 font-sans relative">
      {showSplash && <SplashScreen onComplete={handleSplashComplete} />}

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
