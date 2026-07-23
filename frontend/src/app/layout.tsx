import type { Metadata } from 'next'
import { Inter, Outfit, JetBrains_Mono } from 'next/font/google'
import './globals.css'
import { Sidebar } from '../components/Sidebar'

const fontInter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
})

const fontOutfit = Outfit({
  subsets: ['latin'],
  variable: '--font-outfit',
})

const fontMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
})

export const metadata: Metadata = {
  title: 'Synex — AI Data Engineering Agent',
  description: 'Metadata-driven autonomous AI Data Engineering Agent powered by DataHub.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className={`bg-background text-gray-100 antialiased h-screen w-screen flex overflow-hidden ${fontInter.variable} ${fontOutfit.variable} ${fontMono.variable} font-sans`}>
        <Sidebar />
        <main className="flex-1 flex flex-col overflow-hidden h-full min-w-0 relative z-10">
          {children}
        </main>
      </body>
    </html>
  )
}
