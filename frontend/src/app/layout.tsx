import type { Metadata } from 'next'
import { Inter, Outfit, JetBrains_Mono } from 'next/font/google'
import './globals.css'
import { AppShell } from '../components/AppShell'

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
  description: 'Metadata-first autonomous AI Data Engineering Agent powered by DataHub. Generates production dbt models grounded in real catalog metadata.',
  icons: {
    icon: '/favicon.jpg',
    apple: '/icon.jpg',
  },
  openGraph: {
    title: 'Synex — AI Data Engineering Agent',
    description: 'Metadata-first autonomous data engineering agent powered by DataHub and GPT-4o.',
    type: 'website',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="icon" href="/favicon.jpg" type="image/jpeg" />
        <link rel="apple-touch-icon" href="/icon.jpg" />
      </head>
      <body className={`bg-background text-gray-100 antialiased h-screen w-screen overflow-hidden ${fontInter.variable} ${fontOutfit.variable} ${fontMono.variable} font-sans`}>
        <AppShell>
          {children}
        </AppShell>
      </body>
    </html>
  )
}
