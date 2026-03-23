import { useEffect, useState } from 'react'
import {
  getReactions, addReaction, getComments, addComment,
  REACTION_EMOJIS,
  type ReactionCounts, type ReactionEmoji, type BlogComment,
} from '../lib/firebase'

const REACTION_LABELS: Record<string, string> = {
  '👍': 'Like', '❤️': 'Love', '😂': 'Haha',
  '🔥': 'Fire', '🤯': 'Mind Blown', '👏': 'Clap',
}

function ReactionsBar({ postId }: { postId: string }) {
  const [counts, setCounts] = useState<ReactionCounts | null>(null)
  const [reacted, setReacted] = useState<Set<ReactionEmoji>>(new Set())
  const [animating, setAnimating] = useState<ReactionEmoji | null>(null)

  useEffect(() => {
    getReactions(postId).then(setCounts)
    try {
      const stored = JSON.parse(localStorage.getItem(`reactions:${postId}`) ?? '[]')
      setReacted(new Set(stored))
    } catch { /* ignore */ }
  }, [postId])

  async function handleReact(emoji: ReactionEmoji) {
    if (reacted.has(emoji)) return
    setCounts(prev => prev ? { ...prev, [emoji]: (prev[emoji] ?? 0) + 1 } : prev)
    const next = new Set([...reacted, emoji])
    setReacted(next)
    setAnimating(emoji)
    setTimeout(() => setAnimating(null), 600)
    localStorage.setItem(`reactions:${postId}`, JSON.stringify([...next]))
    try { await addReaction(postId, emoji) } catch { /* best-effort */ }
  }

  if (!counts) return null

  return (
    <div style={{
      display: 'flex', gap: '.6rem', flexWrap: 'wrap', alignItems: 'center',
      margin: '2rem 0', padding: '1.25rem 1.5rem',
      background: 'rgba(255,255,255,.025)', border: '1px solid var(--border)',
      borderRadius: '12px',
    }}>
      <span style={{ fontSize: '.75rem', color: 'var(--muted)', marginRight: '.25rem' }}>React:</span>
      {REACTION_EMOJIS.map(emoji => {
        const count = counts[emoji] ?? 0
        const done = reacted.has(emoji)
        const pop = animating === emoji
        return (
          <button
            key={emoji}
            onClick={() => handleReact(emoji)}
            title={REACTION_LABELS[emoji]}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '.35rem',
              background: done ? 'rgba(0,212,255,.1)' : 'rgba(255,255,255,.04)',
              border: `1px solid ${done ? 'rgba(0,212,255,.35)' : 'var(--border)'}`,
              borderRadius: '99px', padding: '.3rem .8rem',
              cursor: done ? 'default' : 'pointer',
              fontSize: '1rem', transition: 'transform .15s, background .2s',
              transform: pop ? 'scale(1.35)' : 'scale(1)',
              userSelect: 'none',
            }}
          >
            <span>{emoji}</span>
            {count > 0 && (
              <span style={{ fontSize: '.75rem', fontWeight: 600, color: done ? 'var(--cyan)' : '#94a3b8' }}>
                {count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

function CommentsSection({ postId }: { postId: string }) {
  const [comments, setComments] = useState<BlogComment[]>([])
  const [name, setName] = useState('')
  const [content, setContent] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [submitError, setSubmitError] = useState('')

  useEffect(() => {
    getComments(postId).then(setComments)
  }, [postId])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim() || !content.trim()) return
    setSubmitting(true)
    setSubmitError('')
    try {
      await addComment(postId, name, content)
      setSubmitted(true)
      setComments(prev => [...prev, {
        id: Date.now().toString(),
        postId,
        name: name.trim(),
        content: content.trim(),
        createdAt: { seconds: Math.floor(Date.now() / 1000) },
      }])
      setName('')
      setContent('')
    } catch {
      setSubmitError('Failed to post comment. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    width: '100%', background: 'rgba(255,255,255,.04)', border: '1px solid var(--border)',
    borderRadius: '8px', padding: '.65rem .9rem', color: '#e2e8f0',
    fontSize: '.875rem', outline: 'none', boxSizing: 'border-box',
  }

  return (
    <div style={{ marginTop: '3.5rem' }}>
      <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: '1.5rem' }}>
        Comments {comments.length > 0 && <span style={{ color: 'var(--muted)', fontWeight: 400 }}>({comments.length})</span>}
      </h3>

      {comments.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '2rem' }}>
          {comments.map(c => (
            <div key={c.id} style={{
              background: 'rgba(255,255,255,.03)', border: '1px solid var(--border)',
              borderRadius: '10px', padding: '1rem 1.25rem',
            }}>
              <div style={{ display: 'flex', gap: '.6rem', alignItems: 'center', marginBottom: '.5rem' }}>
                <span style={{ fontWeight: 600, fontSize: '.875rem', color: '#e2e8f0' }}>{c.name}</span>
                {c.createdAt && (
                  <span style={{ fontSize: '.75rem', color: 'var(--muted)' }}>
                    {new Date(c.createdAt.seconds * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                  </span>
                )}
              </div>
              <p style={{ fontSize: '.875rem', color: '#94a3b8', lineHeight: 1.65, margin: 0, whiteSpace: 'pre-wrap' }}>{c.content}</p>
            </div>
          ))}
        </div>
      )}

      <div style={{
        background: 'rgba(255,255,255,.02)', border: '1px solid var(--border)',
        borderRadius: '12px', padding: '1.5rem',
      }}>
        <p style={{ fontSize: '.875rem', color: 'var(--muted)', marginBottom: '1rem', lineHeight: 1.6 }}>
          Leave a comment — no account needed.
          Want to <strong style={{ color: '#e2e8f0' }}>write for MLEbotics</strong>?{' '}
          <a href="mailto:eddie@mlebotics.com" style={{ color: 'var(--cyan)', textDecoration: 'none' }}>
            Contact Eddie Chongtham
          </a>{' '}to get hired as an employee writer.
        </p>

        {submitted ? (
          <p style={{ color: '#4ade80', fontSize: '.875rem' }}>Comment posted — thanks!</p>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '.75rem' }}>
            <input
              type="text" placeholder="Your name *" value={name} required maxLength={80}
              onChange={e => setName(e.target.value)} style={inputStyle}
            />
            <textarea
              placeholder="Your comment *" value={content} required maxLength={2000} rows={4}
              onChange={e => setContent(e.target.value)}
              style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }}
            />
            {submitError && <p style={{ color: '#f87171', fontSize: '.8rem', margin: 0 }}>{submitError}</p>}
            <button
              type="submit" disabled={submitting || !name.trim() || !content.trim()}
              style={{
                alignSelf: 'flex-start', background: 'var(--cyan)', color: '#000',
                border: 'none', borderRadius: '8px', padding: '.55rem 1.4rem',
                fontWeight: 700, fontSize: '.875rem', cursor: submitting ? 'not-allowed' : 'pointer',
                opacity: submitting ? .6 : 1,
              }}
            >
              {submitting ? 'Posting…' : 'Post Comment'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

/** Drop-in island for any static blog post page.
 *  Pass a stable `postId` string — e.g. the post slug — so reactions/comments
 *  are stored under a consistent Firestore document ID.
 */
export default function PostInteractions({ postId }: { postId: string }) {
  return (
    <>
      <ReactionsBar postId={postId} />
      <CommentsSection postId={postId} />
    </>
  )
}
