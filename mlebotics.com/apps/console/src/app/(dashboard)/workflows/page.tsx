const tabs = ['All', 'Active', 'Paused', 'Draft']

export default function WorkflowsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Workflows</h1>
          <p className="mt-1 text-sm text-gray-400">Automate tasks across your robots and projects.</p>
        </div>
        <button className="btn-cyan">
          + New Workflow
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-800">
        {tabs.map((tab, i) => (
          <button
            key={tab}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              i === 0
                ? 'border-b-2 border-[#00d4ff] text-[#00d4ff]'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Empty state */}
      <div className="flex flex-col items-center justify-center glass-card py-24 text-center" style={{ borderStyle: 'dashed' }}>
        <div className="mb-4 h-12 w-12 rounded-full bg-gray-800" />
        <h3 className="text-sm font-semibold text-white">No workflows yet</h3>
        <p className="mt-1 text-sm text-[#64748b]">Build your first automation workflow.</p>
        <button className="btn-cyan mt-4">
          + New Workflow
        </button>
      </div>
    </div>
  )
}
