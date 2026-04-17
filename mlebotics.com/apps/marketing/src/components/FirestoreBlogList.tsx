import { useEffect, useState } from 'react'
import { getPublishedPosts, type BlogPostPublic } from '../lib/firebase'

function formatDate(post: BlogPostPublic) {
  if (!post.createdAt) return ''
  return new Date(post.createdAt.seconds * 1000).toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric',
  })
}

export default function FirestoreBlogList() {
  const [posts, setPosts] = useState<BlogPostPublic[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getPublishedPosts()
      .then(p => { setPosts(p); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{ color: 'var(--muted)', fontSize: '.875rem', padding: '2rem 0' }}>
      Loading posts…
    </div>
  )

  if (posts.length === 0) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {posts.map(post => (
        <a
          key={post.id}
          href={`/blog/read?id=${post.id}`}
          style={{
            display: 'block',
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: '12px',
            padding: '1.75rem',
            textDecoration: 'none',
            transition: 'border-color .2s, box-shadow .2s',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLAnchorElement).style.borderColor = 'rgba(0,212,255,.35)'
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLAnchorElement).style.borderColor = 'var(--border)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '.75rem', marginBottom: '.5rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '.8rem', color: 'var(--muted)' }}>{formatDate(post)}</span>
            <span style={{ color: 'var(--muted)', fontSize: '.7rem' }}>·</span>
            <span style={{ fontSize: '.75rem', color: 'var(--cyan)', fontWeight: 600 }}>
              {post.authorName}
            </span>
          </div>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff', marginBottom: '.5rem', lineHeight: 1.3 }}>
            {post.title}
          </h2>
          <p style={{ fontSize: '.9rem', color: '#94a3b8', lineHeight: 1.7, marginBottom: '1rem' }}>
            {post.excerpt}
          </p>
          <div style={{ display: 'flex', gap: '.4rem', flexWrap: 'wrap' }}>
            {post.tags.slice(0, 4).map(t => (
              <span
                key={t}
                style={{
                  fontSize: '.7rem', fontWeight: 600,
                  padding: '.2rem .6rem', borderRadius: '99px',
                  background: 'rgba(0,212,255,.06)',
                  border: '1px solid rgba(0,212,255,.15)',
                  color: 'var(--cyan)',
                }}
              >
                {t}
              </span>
            ))}
          </div>
        </a>
      ))}
    </div>
  )
}
