import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { ChatWidget } from '@/components/ChatWidget'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'MLEbotics Studio',
  description: 'Visual editor for worlds, workflows, and plugins',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-gray-950 text-gray-100`}>
        {children}
        <ChatWidget />
      </body>
    </html>
  )
}
