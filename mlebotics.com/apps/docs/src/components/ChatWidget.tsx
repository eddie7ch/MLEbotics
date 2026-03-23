'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { MessageCircle, X, Send, Wifi, WifiOff, Pencil } from 'lucide-react'
import { subscribeToChatMessages, sendChatMessage, type ChatMessage } from '@/lib/firebase'

const LOCAL_KEY         = 'mlebotics_chat_draft'
const LOCAL_NAME_KEY    = 'mlebotics_chat_name'
const LOCAL_DISMISS_KEY = 'mlebotics_chat_dismissed'
const LOCAL_OPEN_KEY    = 'mlebotics_chat_open'

function formatTimestamp(seconds: number): string {
  const d   = new Date(seconds * 1000)
  const now = new Date()
  const isToday =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth()    === now.getMonth()    &&
    d.getDate()     === now.getDate()
  const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  if (isToday) return `Today · ${time}`
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ` · ${time}`
}

export function ChatWidget() {
  const [dismissed, setDismissed] = useState(() =>
    typeof window !== 'undefined' ? localStorage.getItem(LOCAL_DISMISS_KEY) === '1' : false
  )
  const [open, setOpen] = useState(() =>
    typeof window !== 'undefined' ? localStorage.getItem(LOCAL_OPEN_KEY) === '1' : false
  )
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput]       = useState(() =>
    typeof window !== 'undefined' ? localStorage.getItem(LOCAL_KEY) ?? '' : ''
  )
  const [name, setName]         = useState(() =>
    typeof window !== 'undefined' ? localStorage.getItem(LOCAL_NAME_KEY) ?? '' : ''
  )
  const [nameInput, setNameInput] = useState('')
  const [editingName, setEditingName] = useState(false)
  const [online, setOnline]     = useState(true)
  const [sending, setSending]   = useState(false)
  const bottomRef               = useRef<HTMLDivElement>(null)
  const nameInputRef            = useRef<HTMLInputElement>(null)
  const msgInputRef             = useRef<HTMLInputElement>(null)

  // Show name prompt when panel opens and no name set
  const needsName = !name || editingName

  // Track online/offline
  useEffect(() => {
    const up   = () => setOnline(true)
    const down = () => setOnline(false)
    setOnline(navigator.onLine)
    window.addEventListener('online',  up)
    window.addEventListener('offline', down)
    return () => { window.removeEventListener('online', up); window.removeEventListener('offline', down) }
  }, [])

  // Subscribe to Firestore
  useEffect(() => {
    const unsub = subscribeToChatMessages(setMessages)
    return unsub
  }, [])

  // Scroll to bottom on new messages / open
  useEffect(() => {
    if (open && !needsName) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open, needsName])

  // Persist draft
  useEffect(() => { localStorage.setItem(LOCAL_KEY, input) }, [input])

  // Focus name input when name prompt shows
  useEffect(() => {
    if (open && needsName) setTimeout(() => nameInputRef.current?.focus(), 50)
  }, [open, needsName])

  const saveName = useCallback(() => {
    const trimmed = nameInput.trim()
    if (!trimmed) return
    setName(trimmed)
    localStorage.setItem(LOCAL_NAME_KEY, trimmed)
    setEditingName(false)
    setNameInput('')
    setTimeout(() => msgInputRef.current?.focus(), 50)
  }, [nameInput])

  const send = useCallback(async () => {
    const text = input.trim()
    if (!text || sending) return
    setSending(true)
    setInput('')
    localStorage.removeItem(LOCAL_KEY)
    try {
      await sendChatMessage(text, name || 'Anonymous')
    } finally {
      setSending(false)
    }
  }, [input, sending, name])

  const toggleOpen = (val: boolean) => {
    setOpen(val)
    localStorage.setItem(LOCAL_OPEN_KEY, val ? '1' : '0')
  }

  const dismiss = () => {
    setDismissed(true)
    setOpen(false)
    localStorage.setItem(LOCAL_DISMISS_KEY, '1')
    localStorage.setItem(LOCAL_OPEN_KEY, '0')
  }

  if (dismissed) return null

  return (
    <>
      {/* Floating button */}
      <div className="fixed bottom-6 right-6 z-50 flex items-center">
        <button
          onClick={() => toggleOpen(!open)}
          aria-label="Community chat"
          className="flex items-center gap-2 rounded-full bg-cyan-500 px-4 py-3 text-sm font-semibold text-gray-950 shadow-lg shadow-cyan-500/25 transition-all hover:bg-cyan-400 hover:scale-105 active:scale-95"
        >
          <MessageCircle size={16} />
          Community
          {messages.length > 0 && (
            <span className="rounded-full bg-gray-950/20 px-1.5 py-0.5 text-[10px] font-bold">
              {messages.length}
            </span>
          )}
        </button>
        <button
          onClick={dismiss}
          aria-label="Dismiss chat"
          title="Hide chat"
          className="absolute -top-1.5 -right-1.5 flex h-4 w-4 items-center justify-center rounded-full border border-gray-600 bg-gray-700 text-[10px] text-gray-400 hover:text-white transition-colors"
        >
          ×
        </button>
      </div>

      {/* Panel */}
      {open && (
        <div className="fixed bottom-20 right-6 z-50 flex w-80 flex-col rounded-2xl border border-gray-700 bg-gray-900 shadow-2xl overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-700 bg-gray-800 px-4 py-3">
            <div className="flex items-center gap-2">
              <MessageCircle size={15} className="text-cyan-400" />
              <span className="text-sm font-semibold text-white">Community Chat</span>
              <span className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                online ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
              }`}>
                {online ? <Wifi size={9} /> : <WifiOff size={9} />}
                {online ? 'Live' : 'Offline'}
              </span>
            </div>
            <button onClick={() => toggleOpen(false)} className="text-gray-400 hover:text-white transition-colors">
              <X size={15} />
            </button>
          </div>

          {/* Name prompt screen */}
          {needsName ? (
            <div className="flex flex-col gap-4 p-5">
              <div className="text-center">
                <div className="mb-1 text-2xl">👋</div>
                <p className="text-sm font-semibold text-white">
                  {editingName ? 'Change your display name' : 'What should we call you?'}
                </p>
                <p className="mt-1 text-xs text-gray-500">Your name will show next to your messages.</p>
              </div>
              <input
                ref={nameInputRef}
                value={nameInput}
                onChange={e => setNameInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && saveName()}
                placeholder="Enter your name…"
                maxLength={30}
                className="w-full rounded-lg bg-gray-800 px-3 py-2.5 text-sm text-gray-100 placeholder-gray-500 outline-none border border-gray-700 focus:border-cyan-500/50 transition-colors"
              />
              <div className="flex gap-2">
                {editingName && (
                  <button
                    onClick={() => { setEditingName(false); setNameInput('') }}
                    className="flex-1 rounded-lg border border-gray-600 py-2 text-sm text-gray-400 hover:text-white transition-colors"
                  >
                    Cancel
                  </button>
                )}
                <button
                  onClick={saveName}
                  disabled={!nameInput.trim()}
                  className="flex-1 rounded-lg bg-cyan-500 py-2 text-sm font-semibold text-gray-950 hover:bg-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  {editingName ? 'Save' : 'Join Chat'}
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Name bar */}
              <div className="flex items-center justify-between border-b border-gray-800 px-4 py-2 bg-gray-900/60">
                <span className="text-[11px] text-gray-500">
                  Chatting as <span className="font-semibold text-cyan-400">{name}</span>
                </span>
                <button
                  onClick={() => { setEditingName(true); setNameInput(name) }}
                  className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-cyan-400 transition-colors"
                >
                  <Pencil size={10} /> Edit
                </button>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-3 space-y-3" style={{ maxHeight: '300px' }}>
                {messages.length === 0 && (
                  <div className="py-6 text-center text-xs text-gray-500">👋 Be the first to say something!</div>
                )}
                {messages.map(msg => {
                  const isMe = msg.name === name
                  return (
                    <div key={msg.id} className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}>
                      {/* Sender name */}
                      <span className={`mb-0.5 px-1 text-[10px] font-medium ${isMe ? 'text-cyan-400' : 'text-gray-400'}`}>
                        {isMe ? 'You' : (msg.name || 'Anonymous')}
                      </span>
                      {/* Bubble */}
                      <div className={`max-w-[78%] rounded-2xl px-3 py-2 text-sm leading-relaxed break-words ${
                        isMe
                          ? 'bg-cyan-500 text-gray-950 rounded-tr-sm'
                          : 'bg-gray-800 text-gray-100 rounded-tl-sm'
                      }`}>
                        {msg.text}
                      </div>
                      {/* Timestamp */}
                      {msg.createdAt && (
                        <span className="mt-0.5 px-1 text-[10px] text-gray-400">
                          {formatTimestamp(msg.createdAt.seconds)}
                        </span>
                      )}
                    </div>
                  )
                })}
                <div ref={bottomRef} />
              </div>

              {/* Offline notice */}
              {!online && (
                <div className="border-t border-yellow-500/20 bg-yellow-500/10 px-3 py-1.5 text-center text-[11px] text-yellow-400">
                  Offline — messages will sync when reconnected
                </div>
              )}

              {/* Input */}
              <div className="border-t border-gray-700 p-3 flex gap-2">
                <input
                  ref={msgInputRef}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
                  placeholder="Type a message…"
                  className="flex-1 rounded-lg bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 outline-none border border-gray-700 focus:border-cyan-500/50 transition-colors"
                />
                <button
                  onClick={send}
                  disabled={!input.trim() || sending}
                  className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-cyan-500 text-gray-950 transition-all hover:bg-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <Send size={14} />
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </>
  )
}
