'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  FolderOpen,
  Bot,
  Workflow,
  Globe,
  Cpu,
  Puzzle,
  Settings,
  PenLine,
  type LucideIcon,
} from 'lucide-react'
import { OrgSwitcher } from './OrgSwitcher'
import { ChatWidget } from './ChatWidget'

const navItems: { label: string; href: string; icon: LucideIcon; phase?: number }[] = [
  { label: 'Dashboard',  href: '/dashboard',  icon: LayoutDashboard },
  { label: 'Projects',   href: '/projects',   icon: FolderOpen },
  { label: 'Blog',       href: '/blog',       icon: PenLine },
  { label: 'Robots',     href: '/robots',     icon: Bot },
  { label: 'Workflows',  href: '/workflows',  icon: Workflow },
  { label: 'World',      href: '/world',      icon: Globe,   phase: 3 },
  { label: 'Automation', href: '/automation', icon: Cpu,     phase: 3 },
  { label: 'Plugins',    href: '/plugins',    icon: Puzzle,  phase: 3 },
  { label: 'Settings',   href: '/settings',   icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="flex w-60 flex-shrink-0 flex-col border-r border-[#1e293b] bg-[#06080f]">
      {/* Logo */}
      <div className="flex h-16 items-center border-b border-[#1e293b] px-4 gap-3">
        <a href="https://mlebotics.com" className="logo-glow tracking-tight text-sm">MLEbotics</a>
        <span className="ml-auto text-[9px] font-semibold text-cyan-500 border border-cyan-500/30 rounded px-1.5 py-0.5 leading-none">
          CONSOLE
        </span>
      </div>

      {/* Org switcher */}
      <div className="px-3 py-3 border-b border-[#1e293b]">
        <OrgSwitcher />
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 px-3 py-3">
        {navItems.map(({ label, href, icon: Icon, phase }) => {
          const active = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                  : 'text-gray-400 hover:bg-gray-800/60 hover:text-white'
              }`}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              <span className="flex-1">{label}</span>
              {phase && !active && (
                <span className="text-[9px] text-gray-600 font-semibold">P{phase}</span>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-[#1e293b] p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-cyan-500/20 text-xs font-bold text-cyan-400">
            E
          </div>
          <div className="min-w-0">
            <p className="truncate text-xs font-medium text-gray-300">Eddie Chongtham</p>
            <p className="truncate text-xs text-gray-500">eddie@mlebotics.com</p>
          </div>
        </div>
      </div>
    </aside>
  )
}
