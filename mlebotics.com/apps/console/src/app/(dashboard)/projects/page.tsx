'use client'

import { useEffect, useState } from 'react'
import { FolderOpen, Plus, Trash2 } from 'lucide-react'
import {
  subscribeToProjects,
  createProject,
  deleteProject,
  type Project,
} from '@/lib/firebase'

const STATUS_STYLES: Record<Project['status'], string> = {
  active:   'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
  draft:    'text-yellow-400 bg-yellow-400/10 border-yellow-400/20',
  archived: 'text-[#64748b] bg-[#64748b]/10 border-[#64748b]/20',
}

function formatDate(ts: Project['createdAt']) {
  if (!ts) return '—'
  return new Date(ts.seconds * 1000).toLocaleDateString('en-CA', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading]   = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({ name: '', description: '', status: 'active' as Project['status'] })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const unsub = subscribeToProjects(p => { setProjects(p); setLoading(false) })
    return unsub
  }, [])

  async function handleCreate() {
    if (!form.name.trim()) return
    setSaving(true)
    try {
      await createProject(form)
      setForm({ name: '', description: '', status: 'active' })
      setShowModal(false)
    } finally { setSaving(false) }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this project?')) return
    await deleteProject(id)
  }

  return (
    <>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Projects</h1>
            <p className="mt-1 text-sm text-[#64748b]">Manage and monitor your MLEbotics projects.</p>
          </div>
          <button onClick={() => setShowModal(true)} className="btn-cyan">
            <Plus className="h-4 w-4" /> New Project
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-24">
            <div className="spinner" />
          </div>
        ) : projects.length === 0 ? (
          <div className="glass-card flex flex-col items-center justify-center py-24 text-center" style={{ borderStyle: 'dashed' }}>
            <FolderOpen className="mb-4 h-12 w-12 text-[#1e293b]" />
            <h3 className="text-sm font-semibold text-white">No projects yet</h3>
            <p className="mt-1 text-sm text-[#64748b]">Create your first project to get started.</p>
            <button onClick={() => setShowModal(true)} className="btn-cyan mt-4">
              <Plus className="h-4 w-4" /> New Project
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {projects.map(p => (
              <div key={p.id} className="glass-card p-5 group">
                <div className="flex items-start justify-between mb-3">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${STATUS_STYLES[p.status]}`}>
                    {p.status}
                  </span>
                  <button
                    onClick={() => handleDelete(p.id)}
                    className="opacity-0 group-hover:opacity-100 text-[#64748b] hover:text-red-400 transition-all"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                <h3 className="font-semibold text-white">{p.name}</h3>
                {p.description && (
                  <p className="mt-1 text-sm text-[#64748b] line-clamp-2">{p.description}</p>
                )}
                <p className="mt-3 text-xs text-[#374151]">{formatDate(p.createdAt)}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* New Project modal */}
      {showModal && (
        <div
          className="modal-overlay"
          onClick={e => e.target === e.currentTarget && setShowModal(false)}
        >
          <div className="modal-box">
            <h2 className="text-lg font-semibold text-white mb-4">New Project</h2>
            <div className="space-y-3">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-[#64748b]">Name</label>
                <input
                  className="field-input"
                  placeholder="My Awesome Project"
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  onKeyDown={e => e.key === 'Enter' && handleCreate()}
                  autoFocus
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-[#64748b]">Description</label>
                <textarea
                  className="field-input resize-none"
                  placeholder="What does this project do?"
                  rows={3}
                  value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-[#64748b]">Status</label>
                <select
                  className="field-input"
                  value={form.status}
                  onChange={e => setForm(f => ({ ...f, status: e.target.value as Project['status'] }))}
                >
                  <option value="active">Active</option>
                  <option value="draft">Draft</option>
                  <option value="archived">Archived</option>
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
                {saving ? 'Creating…' : 'Create Project'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
