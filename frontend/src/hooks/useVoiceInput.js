import { useState, useRef, useCallback } from 'react'

/**
 * Hook for browser microphone input via Web Speech API.
 * Returns { listening, transcript, start, stop, supported }
 */
export function useVoiceInput({ onResult, onError } = {}) {
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const recognitionRef = useRef(null)

  const supported =
    typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)

  const start = useCallback(() => {
    if (!supported) {
      onError?.('Speech recognition not supported in this browser.')
      return
    }

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition

    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = true
    recognition.lang = 'es-ES' // Supports Spanish; auto-detects English too

    recognition.onstart = () => setListening(true)

    recognition.onresult = (event) => {
      const current = Array.from(event.results)
        .map((r) => r[0].transcript)
        .join('')
      setTranscript(current)

      // Final result — fire callback
      if (event.results[event.results.length - 1].isFinal) {
        onResult?.(current)
        setTranscript('')
      }
    }

    recognition.onerror = (event) => {
      setListening(false)
      if (event.error !== 'no-speech') {
        onError?.(event.error)
      }
    }

    recognition.onend = () => {
      setListening(false)
      recognitionRef.current = null
    }

    recognitionRef.current = recognition
    recognition.start()
  }, [supported, onResult, onError])

  const stop = useCallback(() => {
    recognitionRef.current?.stop()
    setListening(false)
  }, [])

  return { listening, transcript, start, stop, supported }
}
