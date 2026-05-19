const BASE = import.meta.env.VITE_API_URL || ''

/**
 * Send a chat message to the backend agent.
 * @param {Object} params
 * @param {string} params.message
 * @param {string} params.sessionId
 * @param {boolean} params.voiceMode
 * @returns {Promise<{response, session_id, tools_used, tool_display_names, audio_base64, tts_provider}>}
 */
export async function sendChat({ message, sessionId, voiceMode }) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      voice_mode: voiceMode,
    }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }

  return res.json()
}

/**
 * Synthesize text to speech (standalone).
 * @param {string} text
 * @returns {Promise<{audio_base64, provider, error}>}
 */
export async function synthesize(text) {
  const res = await fetch(`${BASE}/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  return res.json()
}

/**
 * Clear session memory on the backend.
 * @param {string} sessionId
 */
export async function clearSession(sessionId) {
  await fetch(`${BASE}/session/${sessionId}`, { method: 'DELETE' })
}

/**
 * Play base64 MP3 audio in the browser.
 * @param {string} base64
 * @returns {HTMLAudioElement}
 */
export function playAudio(base64) {
  const audio = new Audio(`data:audio/mpeg;base64,${base64}`)
  audio.play().catch(console.error)
  return audio
}
