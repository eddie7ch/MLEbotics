import { initializeApp, getApps } from 'firebase/app'
import {
  getFirestore, collection, getDocs, getDoc,
  addDoc, doc, query, where, serverTimestamp,
  setDoc, increment,
} from 'firebase/firestore'

const firebaseConfig = {
  apiKey: 'AIzaSyDTJWhkRNMa5lOSdwxGLUGrpvWXrLuljfc',
  authDomain: 'running-companion-a935f.firebaseapp.com',
  projectId: 'running-companion-a935f',
  storageBucket: 'running-companion-a935f.firebasestorage.app',
  messagingSenderId: '618174257557',
  appId: '1:618174257557:web:29ca5df050bd6daae9be9c',
}

const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0]
export const db = getFirestore(app)

export interface BlogPostPublic {
  id: string
  title: string
  slug: string
  excerpt: string
  content: string
  tags: string[]
  authorName: string
  published: boolean
  createdAt: { seconds: number } | null
}

export async function getPublishedPosts(): Promise<BlogPostPublic[]> {
  const q = query(
    collection(db, 'blog_posts'),
    where('published', '==', true),
  )
  const snap = await getDocs(q)
  const posts = snap.docs.map(d => ({ id: d.id, ...d.data() } as BlogPostPublic))
  // Sort client-side to avoid requiring a composite Firestore index
  return posts.sort((a, b) => (b.createdAt?.seconds ?? 0) - (a.createdAt?.seconds ?? 0))
}

export async function getPostById(id: string): Promise<BlogPostPublic | null> {
  const snap = await getDoc(doc(db, 'blog_posts', id))
  if (!snap.exists()) return null
  return { id: snap.id, ...snap.data() } as BlogPostPublic
}

// ── Comments ──────────────────────────────────────────────────────────────────

export interface BlogComment {
  id: string
  postId: string
  name: string
  content: string
  createdAt: { seconds: number } | null
}

export async function getComments(postId: string): Promise<BlogComment[]> {
  const q = query(
    collection(db, 'blog_comments'),
    where('postId', '==', postId),
    orderBy('createdAt', 'asc'),
  )
  const snap = await getDocs(q)
  return snap.docs.map(d => ({ id: d.id, ...d.data() } as BlogComment))
}

export async function addComment(
  postId: string,
  name: string,
  content: string,
): Promise<void> {
  await addDoc(collection(db, 'blog_comments'), {
    postId,
    name: name.trim().slice(0, 80),
    content: content.trim().slice(0, 2000),
    createdAt: serverTimestamp(),
  })
}

// ── Reactions ─────────────────────────────────────────────────────────────────

export const REACTION_EMOJIS = ['👍', '❤️', '😂', '🔥', '🤯', '👏'] as const
export type ReactionEmoji = typeof REACTION_EMOJIS[number]
export type ReactionCounts = Record<ReactionEmoji, number>

export async function getReactions(postId: string): Promise<ReactionCounts> {
  const snap = await getDoc(doc(db, 'blog_reactions', postId))
  const empty = Object.fromEntries(REACTION_EMOJIS.map(e => [e, 0])) as ReactionCounts
  if (!snap.exists()) return empty
  return { ...empty, ...snap.data() } as ReactionCounts
}

export async function addReaction(postId: string, emoji: ReactionEmoji): Promise<void> {
  await setDoc(
    doc(db, 'blog_reactions', postId),
    { [emoji]: increment(1) },
    { merge: true },
  )
}
