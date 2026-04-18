'use client'

import { useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { Bell, LogOut } from 'lucide-react'
import { trpc } from '@/lib/trpc'
import { signOut } from '@/lib/firebase'

const crumbs: Record<string, string> = {
  '/dashboard':   'Dashboard',
  '/projects':    'Projects',
  '/robots':      'Robots',
  '/workflows':   'Workflows',
  '/settings':    'Settings',
  '/world':       'World',
  '/automation':  'Automation',
  '/plugins':     'Plugins',
}

function initials(name: string | undefined): string {
  if (!name) return 'U'
  const parts = name.trim().split(/\s+/)
  return parts.length >= 2
    ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    : parts[0][0].toUpperCase()
}

export function Topbar() {
  const pathname = usePathname()
  const router = useRouter()
  const label = crumbs[pathname] ?? 'MLEbotics'
  const { data: user } = trpc.user.getCurrentUser.useQuery()
  const [signingOut, setSigningOut] = useState(false)

  async function handleSignOut() {
    setSigningOut(true)
    try {
      await signOut()
    } finally {
      router.replace('/login')
      setSigningOut(false)
    }
  }

  return (
    <header className="flex h-16 flex-shrink-0 items-center justify-between border-b border-[#1e293b] bg-[#06080f] px-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <span className="text-gray-500">MLEbotics</span>
        <span className="text-gray-700">/</span>
        <span className="font-medium text-white">{label}</span>
      </div>

      {/* Right */}
      <div className="flex items-center gap-3">
        <button className="relative rounded-md p-2 text-gray-400 hover:bg-gray-800 hover:text-white transition-colors">
          <Bell className="h-4 w-4" />
        </button>
        <button
          onClick={handleSignOut}
          disabled={signingOut}
          className="flex items-center gap-2 rounded-md border border-gray-800 px-3 py-1.5 text-xs font-semibold text-gray-300 hover:bg-gray-800 hover:text-white transition-colors disabled:opacity-50"
        >
          <LogOut className="h-3.5 w-3.5" />
          {signingOut ? 'Signing out…' : 'Sign out'}
        </button>
        <div
          title={user?.name ?? 'Loading…'}
          className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white select-none"
        >
          {initials(user?.name)}
        </div>
      </div>
    </header>
  )
}
