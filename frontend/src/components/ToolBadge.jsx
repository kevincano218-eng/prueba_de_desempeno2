import React from 'react'
import { Zap, Search, Cloud } from 'lucide-react'

const TOOL_CONFIG = {
  web_search: {
    label: 'Web Search',
    icon: Search,
    color: '#60a5fa',
    bg: 'rgba(96, 165, 250, 0.12)',
    border: 'rgba(96, 165, 250, 0.25)',
  },
  get_weather: {
    label: 'Weather',
    icon: Cloud,
    color: '#34d399',
    bg: 'rgba(52, 211, 153, 0.12)',
    border: 'rgba(52, 211, 153, 0.25)',
  },
}

const DEFAULT_CONFIG = {
  label: 'Tool',
  icon: Zap,
  color: '#a78bfa',
  bg: 'rgba(167, 139, 250, 0.12)',
  border: 'rgba(167, 139, 250, 0.25)',
}

export function ToolBadge({ toolName }) {
  const config = TOOL_CONFIG[toolName] || DEFAULT_CONFIG
  const Icon = config.icon

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        padding: '3px 10px',
        borderRadius: 20,
        background: config.bg,
        border: `1px solid ${config.border}`,
        color: config.color,
        fontSize: 11,
        fontFamily: 'var(--font-mono)',
        fontWeight: 500,
        letterSpacing: '0.04em',
        whiteSpace: 'nowrap',
      }}
    >
      <Icon size={11} strokeWidth={2} />
      {config.label}
    </span>
  )
}
