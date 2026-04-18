'use client'

import { useEffect, useState } from 'react'
import { FolderOpen, Bot, Workflow, Users, ArrowUpRight } from 'lucide-react'
import { subscribeToProjects, subscribeToRobots } from '@/lib/firebase'

const STAT_META = [
  { label: 'Active Projects',   key: 'projects',  icon: FolderOpen, color: '#00d4ff' },
  { label: 'Connected Robots',  key: 'robots',    icon: Bot,        color: '#00ff88' },
  { label: 'Workflows Running', key: 'workflows', icon: Workflow,   color: '#a78bfa' },
  { label: 'Team Members',      key: 'members',   icon: Users,      color: '#fb923c' },
] as const

const QUICK_ACTIONS = [
  { label: 'New Project',  href: '/projects' },
  { label: 'Add Robot',    href: '/robots' },
  { label: 'New Workflow', href: '/workflows' },
  { label: 'Settings',     href: '/settings' },
]

export default function DashboardPage() {
  const [counts, setCounts] = useState({ projects: 0, robots: 0, workflows: 0, members: 1 })

  useEffect(() => {
    const unsub1 = subscribeToProjects(p => setCounts(c => ({ ...c, projects: p.length })))
    const unsub2 = subscribeToRobots(r  => setCounts(c => ({ ...c, robots: r.length })))
    return () => { unsub1(); unsub2() }
  }, [])

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="mt-1 text-sm text-[#64748b]">Welcome back. Here&apos;s what&apos;s happening.</p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {STAT_META.map(({ label, key, icon: Icon, color }) => (
          <div
            key={key}
            className="glass-card p-5"
            style={{ borderTop: `2px solid ${color}28` }}
          >
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-medium uppercase tracking-wider text-[#64748b]">{label}</p>
              <div className="rounded-lg p-1.5" style={{ background: `${color}18` }}>
                <Icon className="h-4 w-4" style={{ color }} />
              </div>
            </div>
            <p className="text-3xl font-bold text-white">{counts[key]}</p>
          </div>
        ))}
      </div>

      {/* Two-col lower section */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent activity */}
        <div className="glass-card p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-[#64748b]">Recent Activity</h2>
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="mb-3 h-10 w-10 rounded-full bg-[#1e293b]" />
            <p className="text-sm text-[#64748b]">No activity yet.</p>
            <p className="mt-1 text-xs text-[#374151]">Actions will appear here once you start using the platform.</p>
          </div>
        </div>

        {/* Quick actions */}
        <div className="glass-card p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-[#64748b]">Quick Actions</h2>
          <div className="grid grid-cols-2 gap-3">
            {QUICK_ACTIONS.map((action) => (
              <a
                key={action.href}
                href={action.href}
                className="flex items-center justify-between rounded-lg border border-[#1e293b] bg-white/[0.02] px-4 py-3 text-sm font-medium text-[#e2e8f0] transition-all hover:border-[#00d4ff]/30 hover:text-[#00d4ff]"
              >
                {action.label}
                <ArrowUpRight className="h-3.5 w-3.5 opacity-50" />
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
