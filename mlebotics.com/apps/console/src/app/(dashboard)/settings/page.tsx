const sections = [
  {
    title: 'Organization',
    fields: [
      { label: 'Organization Name', placeholder: 'MLEbotics', type: 'text' },
      { label: 'Slug',              placeholder: 'mlebotics',  type: 'text' },
    ],
  },
  {
    title: 'Account',
    fields: [
      { label: 'Display Name', placeholder: 'Your Name',          type: 'text' },
      { label: 'Email',        placeholder: 'you@mlebotics.com',  type: 'email' },
    ],
  },
]

export default function SettingsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="mt-1 text-sm text-gray-400">Manage your organization and account preferences.</p>
      </div>

      {sections.map((section) => (
        <div key={section.title} className="glass-card">
          <div className="border-b border-gray-800 px-6 py-4">
            <h2 className="text-sm font-semibold text-white">{section.title}</h2>
          </div>
          <div className="space-y-4 p-6">
            {section.fields.map((field) => (
              <div key={field.label}>
                <label className="mb-1.5 block text-xs font-medium text-gray-400">{field.label}</label>
                <input
                  type={field.type}
                  placeholder={field.placeholder}
                  className="field-input"
                />
              </div>
            ))}
          </div>
          <div className="flex justify-end border-t border-gray-800 px-6 py-4">
            <button className="btn-cyan">
              Save Changes
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
