import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/**/*.{ts,tsx}',
    '../../packages/ui/src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          bg:     '#06080f',
          bg2:    '#0d1117',
          cyan:   '#00d4ff',
          green:  '#00ff88',
          border: '#1e293b',
          muted:  '#64748b',
        },
      },
    },
  },
  plugins: [],
}

export default config
