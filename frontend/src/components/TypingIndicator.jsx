import React from 'react'

export function TypingIndicator({ toolName }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-start' }}>
      <span style={{ fontSize: 10, color: 'var(--text-3)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
        agent
      </span>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '10px 16px',
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: '4px 14px 14px 14px',
        }}
      >
        {/* Dots */}
        <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: 'var(--accent)',
                animation: `pulse 1.2s ease-in-out infinite`,
                animationDelay: `${i * 0.2}s`,
              }}
            />
          ))}
        </div>

        {toolName && (
          <span
            style={{
              fontSize: 11,
              color: 'var(--blue)',
              fontFamily: 'var(--font-mono)',
              display: 'flex',
              alignItems: 'center',
              gap: 5,
            }}
          >
            <span
              style={{
                display: 'inline-block',
                width: 8,
                height: 8,
                borderRadius: '50%',
                border: '2px solid var(--blue)',
                borderTopColor: 'transparent',
                animation: 'spin 0.7s linear infinite',
              }}
            />
            using {toolName}...
          </span>
        )}
      </div>
    </div>
  )
}
