import React, { useState, useRef, useEffect } from 'react'
import { Play, Pause, Volume2 } from 'lucide-react'

export function AudioPlayer({ base64Audio, autoPlay = true }) {
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)
  const [duration, setDuration] = useState(0)
  const audioRef = useRef(null)

  useEffect(() => {
    if (!base64Audio) return

    const audio = new Audio(`data:audio/mpeg;base64,${base64Audio}`)
    audioRef.current = audio

    audio.onloadedmetadata = () => setDuration(audio.duration)
    audio.ontimeupdate = () => {
      if (audio.duration) setProgress(audio.currentTime / audio.duration)
    }
    audio.onended = () => {
      setPlaying(false)
      setProgress(0)
    }

    if (autoPlay) {
      audio.play().then(() => setPlaying(true)).catch(() => {})
    }

    return () => {
      audio.pause()
      audio.src = ''
    }
  }, [base64Audio, autoPlay])

  const toggle = () => {
    const audio = audioRef.current
    if (!audio) return
    if (playing) {
      audio.pause()
      setPlaying(false)
    } else {
      audio.play().then(() => setPlaying(true)).catch(() => {})
    }
  }

  const formatTime = (s) => {
    if (!s || isNaN(s)) return '0:00'
    const m = Math.floor(s / 60)
    const sec = Math.floor(s % 60)
    return `${m}:${sec.toString().padStart(2, '0')}`
  }

  const elapsed = duration * progress

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '8px 12px',
        marginTop: 8,
        background: 'rgba(124, 106, 247, 0.08)',
        border: '1px solid rgba(124, 106, 247, 0.2)',
        borderRadius: 8,
        maxWidth: 260,
      }}
    >
      {/* Play/Pause */}
      <button
        onClick={toggle}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 30,
          height: 30,
          borderRadius: '50%',
          border: 'none',
          background: 'var(--accent)',
          color: '#fff',
          cursor: 'pointer',
          flexShrink: 0,
        }}
      >
        {playing ? <Pause size={13} /> : <Play size={13} />}
      </button>

      {/* Waveform bars (animated when playing) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 2, flexShrink: 0 }}>
        {[1, 0.6, 1, 0.4, 0.8, 0.5, 1].map((h, i) => (
          <div
            key={i}
            style={{
              width: 2,
              height: 14 * h,
              background: 'var(--accent-2)',
              borderRadius: 1,
              opacity: playing ? 0.9 : 0.35,
              transformOrigin: 'center',
              animation: playing
                ? `waveBar ${0.4 + i * 0.1}s ease-in-out infinite alternate`
                : 'none',
              animationDelay: `${i * 0.06}s`,
            }}
          />
        ))}
      </div>

      {/* Progress bar */}
      <div
        style={{
          flex: 1,
          height: 3,
          background: 'var(--border)',
          borderRadius: 2,
          cursor: 'pointer',
          position: 'relative',
        }}
        onClick={(e) => {
          const rect = e.currentTarget.getBoundingClientRect()
          const p = (e.clientX - rect.left) / rect.width
          if (audioRef.current) {
            audioRef.current.currentTime = p * duration
            setProgress(p)
          }
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            height: '100%',
            width: `${progress * 100}%`,
            background: 'var(--accent)',
            borderRadius: 2,
            transition: 'width 0.1s linear',
          }}
        />
      </div>

      {/* Time */}
      <span
        style={{
          fontSize: 10,
          color: 'var(--text-2)',
          fontFamily: 'var(--font-mono)',
          flexShrink: 0,
        }}
      >
        {formatTime(elapsed)}/{formatTime(duration)}
      </span>

      <Volume2 size={12} color="var(--text-3)" />
    </div>
  )
}
