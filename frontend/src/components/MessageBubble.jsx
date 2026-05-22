import React from 'react'
import { ToolBadge } from './ToolBadge'
import { AudioPlayer } from './AudioPlayer'

export function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  const hasTools = message.tools_used && message.tools_used.length > 0

  return (
    <div
      className="animate-in"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
        gap: 6,
        maxWidth: '100%',
      }}
    >
      {/* Role label */}
      <span
        style={{
          fontSize: 10,
          color: 'var(--text-3)',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          fontWeight: 500,
          paddingLeft: 4,
        }}
      >
        {isUser ? 'you' : 'agent'}
        {message.timestamp && (
          <span style={{ marginLeft: 8, letterSpacing: 0 }}>
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        )}
      </span>

      {/* Tool badges — shown above assistant messages */}
      {!isUser && hasTools && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', paddingLeft: 4 }}>
          {message.tools_used.map((tool) => (
            <ToolBadge key={tool} toolName={tool} />
          ))}
        </div>
      )}

      {/* Message bubble */}
      <div
        style={{
          maxWidth: 'var(--bubble-max-w)',
          padding: isUser ? '10px 16px' : '12px 16px',
          borderRadius: isUser ? '14px 14px 4px 14px' : '4px 14px 14px 14px',
          background: isUser
            ? 'linear-gradient(135deg, #6d59f0, #9333ea)'
            : 'var(--bg-card)',
          border: isUser ? 'none' : `1px solid ${hasTools ? 'rgba(96,165,250,0.2)' : 'var(--border)'}`,
          color: isUser ? '#fff' : 'var(--text-1)',
          fontSize: 13.5,
          lineHeight: 1.65,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          boxShadow: isUser
            ? '0 2px 16px rgba(109,89,240,0.3)'
            : '0 1px 4px rgba(0,0,0,0.3)',
          position: 'relative',
        }}
      >
        {/* Tool indicator bar on left edge for agent messages with tools */}
        {!isUser && hasTools && (
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 8,
              bottom: 8,
              width: 3,
              background: 'var(--blue)',
              borderRadius: '0 2px 2px 0',
              opacity: 0.7,
            }}
          />
        )}

        <span style={{ paddingLeft: !isUser && hasTools ? 8 : 0 }}>
          {message.content}
        </span>
      </div>

      {/* Audio player if response has audio */}
      {!isUser && message.audio_base64 && (
        <div style={{ paddingLeft: 4 }}>
          <AudioPlayer base64Audio={message.audio_base64} autoPlay={message.autoPlayAudio} />
        </div>
      )}
    </div>
  )
}
