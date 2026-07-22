import type { Metadata } from 'next'
import './globals.css'

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
      <body className="bg-background text-gray-100 antialiased min-h-screen">
        {children}
      </body>
    </html>
  )
}
