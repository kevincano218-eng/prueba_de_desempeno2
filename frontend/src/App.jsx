import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Mic, MicOff, Trash2, Bot, Wifi, WifiOff } from 'lucide-react'
import { MessageBubble } from './components/MessageBubble'
import { TypingIndicator } from './components/TypingIndicator'
import { VoiceToggle } from './components/VoiceToggle'
import { useVoiceInput } from './hooks/useVoiceInput'
import { sendChat, clearSession } from './api'

const WELCOME = {
  id: 'welcome',
  role: 'assistant',
  content: "Hello! I'm VoiceAgent — your AI assistant with real-time web search and weather tools. Ask me anything: current news, weather in any city, or just chat. You can also switch to Voice mode to hear my responses.",
  tools_used: [],
  timestamp: Date.now(),
}

function generateSessionId() {
  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export default function App() {
  const [messages, setMessages] = useState([WELCOME])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [voiceMode, setVoiceMode] = useState(false)
  const [sessionId] = useState(() => generateSessionId())
  const [error, setError] = useState(null)
  const [online, setOnline] = useState(true)

  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Check backend health on load
  useEffect(() => {
    fetch('/health')
      .then(() => setOnline(true))
      .catch(() => setOnline(false))
  }, [])

  const handleSend = useCallback(async (text) => {
    const msg = (text || input).trim()
    if (!msg || loading) return

    setInput('')
    setError(null)

    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: msg,
      timestamp: Date.now(),
    }
    setMessages((prev) => [...prev, userMsg])
    setLoading(true)

    try {
      const data = await sendChat({
        message: msg,
        sessionId,
        voiceMode,
      })

      const assistantMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.response,
        tools_used: data.tools_used || [],
        tool_display_names: data.tool_display_names || [],
        audio_base64: data.audio_base64 || null,
        tts_provider: data.tts_provider || null,
        autoPlayAudio: voiceMode,
        timestamp: Date.now(),
      }

      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      setError(err.message || 'Failed to reach the agent. Is the backend running?')
    } finally {
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [input, loading, sessionId, voiceMode])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleClear = async () => {
    await clearSession(sessionId).catch(() => {})
    setMessages([WELCOME])
    setError(null)
  }

  // Voice input
  const { listening, start: startListening, stop: stopListening, supported: micSupported } =
    useVoiceInput({
      onResult: (transcript) => handleSend(transcript),
      onError: (err) => setError(`Microphone error: ${err}`),
    })

  const toggleMic = () => {
    if (listening) stopListening()
    else startListening()
  }

  return (
    <div style={styles.root}>
      {/* Background grid */}
      <div style={styles.bgGrid} />

      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.logoMark}>
            <Bot size={18} color="var(--accent-2)" />
          </div>
          <div>
            <div style={styles.logoText}>VoiceAgent</div>
            <div style={styles.logoSub}>AI · Tools · Voice</div>
          </div>
        </div>

        <div style={styles.headerRight}>
          {/* Online indicator */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            {online
              ? <Wifi size={13} color="var(--green)" />
              : <WifiOff size={13} color="var(--red)" />
            }
            <span className="hide-label-mobile" style={{ fontSize: 11, color: online ? 'var(--green)' : 'var(--red)' }}>
              {online ? 'connected' : 'offline'}
            </span>
          </div>

          {/* Voice / Text toggle */}
          <VoiceToggle voiceMode={voiceMode} onChange={setVoiceMode} />

          {/* Clear conversation */}
          <button
            onClick={handleClear}
            title="Clear conversation"
            style={styles.iconBtn}
          >
            <Trash2 size={15} />
          </button>
        </div>
      </header>

      {/* Messages */}
      <main style={styles.messages}>
        <div style={styles.messagesInner}>
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {loading && <TypingIndicator />}

          {error && (
            <div style={styles.errorBox}>
              <span style={{ color: 'var(--red)', fontSize: 12 }}>⚠ {error}</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input area */}
      <footer style={styles.footer}>
        <div style={styles.inputRow}>
          {/* Voice input button */}
          {micSupported && (
            <button
              onClick={toggleMic}
              disabled={loading}
              style={{
                ...styles.iconBtn,
                color: listening ? 'var(--red)' : 'var(--text-2)',
                border: listening ? '1px solid var(--red)' : '1px solid var(--border)',
                background: listening ? 'var(--red-bg)' : 'var(--bg-input)',
                animation: listening ? 'pulse 1s ease-in-out infinite' : 'none',
              }}
              title={listening ? 'Stop recording' : 'Start voice input'}
            >
              {listening ? <MicOff size={16} /> : <Mic size={16} />}
            </button>
          )}

          {/* Text input */}
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              listening
                ? 'Listening...'
                : voiceMode
                ? 'Type a message (response will be spoken)...'
                : 'Type a message...'
            }
            rows={1}
            disabled={loading || listening}
            style={{
              ...styles.textarea,
              opacity: (loading || listening) ? 0.6 : 1,
            }}
          />

          {/* Send button */}
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            style={{
              ...styles.sendBtn,
              opacity: (!input.trim() || loading) ? 0.4 : 1,
            }}
          >
            <Send size={16} />
          </button>
        </div>

        <div style={styles.footerHint}>
          {voiceMode
            ? '🔊 Voice mode — responses will be synthesized as audio'
            : '⌨ Text mode — press Enter to send, Shift+Enter for new line'}
        </div>
      </footer>
    </div>
  )
}

const styles = {
  root: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    maxWidth: 820,
    margin: '0 auto',
    position: 'relative',
  },
  bgGrid: {
    position: 'fixed',
    inset: 0,
    backgroundImage:
      'linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px)',
    backgroundSize: '40px 40px',
    opacity: 0.25,
    pointerEvents: 'none',
    zIndex: 0,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 'var(--pad-h) var(--pad-w)',
    borderBottom: '1px solid var(--border)',
    background: 'rgba(10,10,15,0.85)',
    backdropFilter: 'blur(12px)',
    position: 'sticky',
    top: 0,
    zIndex: 10,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    minWidth: 0,
  },
  logoMark: {
    width: 38,
    height: 38,
    borderRadius: 10,
    background: 'var(--accent-glow)',
    border: '1px solid rgba(124,106,247,0.3)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  logoText: {
    fontFamily: 'var(--font-display)',
    fontSize: 18,
    fontWeight: 700,
    color: 'var(--text-1)',
    letterSpacing: '-0.02em',
    whiteSpace: 'nowrap',
  },
  logoSub: {
    fontSize: 10,
    color: 'var(--text-3)',
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
    whiteSpace: 'nowrap',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--header-gap)',
    flexShrink: 0,
  },
  iconBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 36,
    height: 36,
    borderRadius: 8,
    border: '1px solid var(--border)',
    background: 'var(--bg-input)',
    color: 'var(--text-2)',
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  messages: {
    flex: 1,
    overflowY: 'auto',
    position: 'relative',
    zIndex: 1,
  },
  messagesInner: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--msg-gap)',
    padding: 'var(--pad-w)',
    minHeight: '100%',
  },
  errorBox: {
    padding: '10px 14px',
    background: 'var(--red-bg)',
    border: '1px solid rgba(248,113,113,0.2)',
    borderRadius: 8,
  },
  footer: {
    borderTop: '1px solid var(--border)',
    background: 'rgba(10,10,15,0.9)',
    backdropFilter: 'blur(12px)',
    padding: 'var(--pad-h) var(--pad-w)',
    position: 'sticky',
    bottom: 0,
    zIndex: 10,
    paddingBottom: 'max(var(--pad-h), env(safe-area-inset-bottom, 0px))',
  },
  inputRow: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: 10,
  },
  textarea: {
    flex: 1,
    background: 'var(--bg-input)',
    border: '1px solid var(--border)',
    borderRadius: 10,
    padding: '11px 14px',
    color: 'var(--text-1)',
    fontFamily: 'var(--font-mono)',
    fontSize: 13.5,
    resize: 'none',
    outline: 'none',
    lineHeight: 1.6,
    minHeight: 44,
    maxHeight: 140,
    transition: 'border-color 0.15s',
  },
  sendBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 44,
    height: 44,
    borderRadius: 10,
    border: 'none',
    background: 'var(--accent)',
    color: '#fff',
    cursor: 'pointer',
    flexShrink: 0,
    transition: 'opacity 0.15s, transform 0.1s',
    boxShadow: '0 2px 12px rgba(124,106,247,0.35)',
  },
  footerHint: {
    marginTop: 8,
    fontSize: 11,
    color: 'var(--text-3)',
    letterSpacing: '0.02em',
  },
}
