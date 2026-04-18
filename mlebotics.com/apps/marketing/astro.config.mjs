import { defineConfig } from 'astro/config'
import { fileURLToPath } from 'node:url'
import react from '@astrojs/react'
import tailwind from '@astrojs/tailwind'

const tailwindConfigFile = fileURLToPath(new URL('./tailwind.config.mjs', import.meta.url))

export default defineConfig({
  site: 'https://mlebotics.com',

  integrations: [
    react(),
    tailwind({ configFile: tailwindConfigFile }),
  ],

  output: 'static',

  server: {
    port: 54321,
    host: true,
  },
})
