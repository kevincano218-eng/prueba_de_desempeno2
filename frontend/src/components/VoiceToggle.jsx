import React from 'react'
import { Type, Volume2 } from 'lucide-react'

export function VoiceToggle({ voiceMode, onChange }) {
  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        background: 'var(--bg-input)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: 3,
        gap: 2,
      }}
    >
      <ToggleOption
        active={!voiceMode}
        onClick={() => onChange(false)}
        icon={<Type size={13} />}
        label="Text"
      />
      <ToggleOption
        active={voiceMode}
        onClick={() => onChange(true)}
        icon={<Volume2 size={13} />}
        label="Voice"
      />
    </div>
  )
}

function ToggleOption({ active, onClick, icon, label }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '6px 12px',
        border: 'none',
        borderRadius: 6,
        background: active ? 'var(--accent)' : 'transparent',
        color: active ? '#fff' : 'var(--text-2)',
        fontSize: 12,
        fontFamily: 'var(--font-mono)',
        fontWeight: active ? 500 : 400,
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        letterSpacing: '0.03em',
      }}
    >
      {icon}
      <span className="hide-label-mobile">{label}</span>
    </button>
  )
}
