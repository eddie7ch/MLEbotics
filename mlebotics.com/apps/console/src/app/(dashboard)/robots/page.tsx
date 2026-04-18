'use client'

import { useEffect, useState } from 'react'
import { Bot, Plus, Trash2 } from 'lucide-react'
import {
  subscribeToRobots,
  createRobot,
  updateRobotStatus,
  deleteRobot,
  type Robot,
} from '@/lib/firebase'

const STATUS_META: Record<Robot['status'], { dotClass: string; textClass: string; label: string }> = {
  online:  { dotClass: 'online',  textClass: 'text-emerald-400', label: 'Online' },
  offline: { dotClass: 'offline', textClass: 'text-[#64748b]',   label: 'Offline' },
  error:   { dotClass: 'error',   textClass: 'text-red-400',     label: 'Error' },
}

export default function RobotsPage() {
  const [robots, setRobots]     = useState<Robot[]>([])
  const [loading, setLoading]   = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({ name: '', type: '', status: 'offline' as Robot['status'] })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const unsub = subscribeToRobots(r => { setRobots(r); setLoading(false) })
    return unsub
  }, [])

  async function handleCreate() {
    if (!form.name.trim()) return
    setSaving(true)
    try {
      await createRobot(form)
      setForm({ name: '', type: '', status: 'offline' })
      setShowModal(false)
    } finally { setSaving(false) }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this robot?')) return
    await deleteRobot(id)
  }

  return (
    <>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Robots</h1>
            <p className="mt-1 text-sm text-[#64748b]">Connected robots and their current status.</p>
          </div>
          <button onClick={() => setShowModal(true)} className="btn-cyan">
            <Plus className="h-4 w-4" /> Add Robot
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-24">
            <div className="spinner" />
          </div>
        ) : robots.length === 0 ? (
          <div className="glass-card flex flex-col items-center justify-center py-24 text-center" style={{ borderStyle: 'dashed' }}>
            <Bot className="mb-4 h-12 w-12 text-[#1e293b]" />
            <h3 className="text-sm font-semibold text-white">No robots connected</h3>
            <p className="mt-1 text-sm text-[#64748b]">Add a robot to start monitoring and controlling it.</p>
            <button onClick={() => setShowModal(true)} className="btn-cyan mt-4">
              <Plus className="h-4 w-4" /> Add Robot
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {robots.map(r => {
              const s = STATUS_META[r.status]
              return (
                <div key={r.id} className="glass-card p-5 group">
                  <div className="flex items-start justify-between mb-4">
                    <div className={`flex items-center gap-2 text-xs font-semibold ${s.textClass}`}>
                      <span className={`status-dot ${s.dotClass}`} />
                      {s.label}
                    </div>
                    <button
                      onClick={() => handleDelete(r.id)}
                      className="opacity-0 group-hover:opacity-100 text-[#64748b] hover:text-red-400 transition-all"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                  <h3 className="font-semibold text-white">{r.name}</h3>
                  {r.type && <p className="mt-0.5 text-sm text-[#64748b]">{r.type}</p>}

                  {/* Inline status switcher */}
                  <div className="mt-4 flex gap-1.5">
                    {(['online', 'offline', 'error'] as Robot['status'][]).map(st => (
                      <button
                        key={st}
                        onClick={() => updateRobotStatus(r.id, st)}
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border transition-all ${
                          r.status === st
                            ? 'border-[#00d4ff]/40 text-[#00d4ff] bg-[#00d4ff]/10'
                            : 'border-[#1e293b] text-[#64748b] hover:border-[#00d4ff]/25 hover:text-[#94a3b8]'
                        }`}
                      >
                        {st}
                      </button>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Add Robot modal */}
      {showModal && (
        <div
          className="modal-overlay"
          onClick={e => e.target === e.currentTarget && setShowModal(false)}
        >
          <div className="modal-box">
            <h2 className="text-lg font-semibold text-white mb-4">Add Robot</h2>
            <div className="space-y-3">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-[#64748b]">Name</label>
                <input
                  className="field-input"
                  placeholder="Robot Alpha"
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  onKeyDown={e => e.key === 'Enter' && handleCreate()}
                  autoFocus
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-[#64748b]">Type</label>
                <input
                  className="field-input"
                  placeholder="e.g. Humanoid, Drone, Arm"
                  value={form.type}
                  onChange={e => setForm(f => ({ ...f, type: e.target.value }))}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-[#64748b]">Initial Status</label>
                <select
                  className="field-input"
                  value={form.status}
                  onChange={e => setForm(f => ({ ...f, status: e.target.value as Robot['status'] }))}
                >
                  <option value="offline">Offline</option>
                  <option value="online">Online</option>
                  <option value="error">Error</option>
                </select>
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-3">
              <button onClick={() => setShowModal(false)} className="btn-outline">Cancel</button>
              <button
                onClick={handleCreate}
                disabled={saving || !form.name.trim()}
                className="btn-cyan"
              >
                {saving ? 'Adding…' : 'Add Robot'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Robots</h1>
          <p className="mt-1 text-sm text-gray-400">Connected robots and their current status.</p>
        </div>
        <button className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500">
          + Add Robot
        </button>
      </div>

      {/* Status legend */}
      <div className="flex items-center gap-4">
        {Object.entries(statusColors).map(([status, color]) => (
          <div key={status} className="flex items-center gap-1.5 text-xs text-gray-400">
            <span className={`h-2 w-2 rounded-full ${color}`} />
            <span className="capitalize">{status}</span>
          </div>
        ))}
      </div>

      {/* Empty state */}
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-gray-700 bg-gray-900 py-24 text-center">
        <div className="mb-4 h-12 w-12 rounded-full bg-gray-800" />
        <h3 className="text-sm font-semibold text-white">No robots connected</h3>
        <p className="mt-1 text-sm text-gray-500">Add a robot to start monitoring and controlling it.</p>
        <button className="mt-4 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500">
          + Add Robot
        </button>
      </div>
    </div>
  )
}
