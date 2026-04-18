const SITE_URL = 'https://mlebotics.com'

const pageModules = import.meta.glob('./**/*.astro', { eager: true })

function toRoute(modulePath: string): string | null {
  const file = modulePath.replace(/^\.\//, '')

  // Exclude non-indexable/system pages.
  if (file === '404.astro') return null
  if (file === 'blog/read.astro') return null

  const noExt = file.replace(/\.astro$/, '')

  if (noExt === 'index') return '/'
  if (noExt.endsWith('/index')) return `/${noExt.slice(0, -'/index'.length)}`

  return `/${noExt}`
}

const routes = Object.keys(pageModules)
  .map(toRoute)
  .filter((route): route is string => Boolean(route))
  .sort((a, b) => a.localeCompare(b))

function escapeXml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

export async function GET() {
  const now = new Date().toISOString()

  const urls = routes
    .map((route) => {
      const loc = `${SITE_URL}${route === '/' ? '/' : route}`
      return [
        '  <url>',
        `    <loc>${escapeXml(loc)}</loc>`,
        `    <lastmod>${now}</lastmod>`,
        '  </url>',
      ].join('\n')
    })
    .join('\n')

  const xml = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    urls,
    '</urlset>',
    '',
  ].join('\n')

  return new Response(xml, {
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
    },
  })
}
