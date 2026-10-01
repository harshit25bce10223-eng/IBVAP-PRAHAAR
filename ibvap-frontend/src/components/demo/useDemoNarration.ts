import { useEffect, useRef, useState } from 'react'
export function useDemoNarration(text: string, chapter: string, playing: boolean) {
  const [enabled, setEnabled] = useState(false),
    [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]),
    [voiceName, setVoiceName] = useState(''),
    [status, setStatus] = useState('Voice off')
  const speaking = useRef(false)
  const active = useRef<SpeechSynthesisUtterance | null>(null)
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window
  useEffect(() => {
    if (!supported) return
    const synth = window.speechSynthesis
    const update = () => {
      const available = synth.getVoices().filter(v => v.lang.startsWith('en'))
      setVoices(available)
      setVoiceName(
        name =>
          name ||
          available.find(v => /natural|neural|online/i.test(v.name))?.name ||
          available.find(v => v.lang === 'en-IN')?.name ||
          available[0]?.name ||
          ''
      )
    }
    update()
    synth.addEventListener('voiceschanged', update)
    return () => {
      synth.removeEventListener('voiceschanged', update)
      synth.cancel()
    }
  }, [supported])
  const speak = () => {
    if (!supported) {
      setStatus('Voice unavailable in this browser')
      return
    }
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    active.current = utterance
    speaking.current = true
    utterance.voice = voices.find(v => v.name === voiceName) ?? null
    utterance.lang = utterance.voice?.lang ?? 'en-IN'
    utterance.rate = 1
    utterance.pitch = 1
    utterance.onstart = () => {
      speaking.current = true
      setStatus('Explaining this step…')
    }
    utterance.onend = () => {
      if (active.current !== utterance) return
      speaking.current = false
      setStatus('Ready for next step')
    }
    utterance.onerror = event => {
      if (active.current !== utterance) return
      speaking.current = false
      if (event.error !== 'canceled' && event.error !== 'interrupted')
        setStatus('Voice could not play. Try another voice.')
    }
    window.speechSynthesis.speak(utterance)
  }
  useEffect(() => {
    if (!supported) return
    if (!enabled) {
      window.speechSynthesis.cancel()
      speaking.current = false
      return
    }
    if (playing) {
      window.speechSynthesis.resume()
      speak()
    }
    return () => {
      window.speechSynthesis.cancel()
      speaking.current = false
    }
    // Step text is stable. A new chapter or selected voice starts a fresh explanation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, chapter, voiceName, supported])
  useEffect(() => {
    if (!supported || !enabled) return
    if (!playing) {
      window.speechSynthesis.pause()
      queueMicrotask(() => setStatus('Voice paused · press Play'))
      return
    }
    window.speechSynthesis.resume()
    if (!speaking.current) speak()
    // Playback changes pause/resume the current utterance instead of restarting it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, enabled, supported])
  return {
    enabled,
    voices,
    voiceName,
    status,
    supported,
    speaking,
    setVoiceName,
    toggle: () => {
      if (enabled) {
        window.speechSynthesis?.cancel()
        speaking.current = false
        setStatus('Voice off')
      } else {
        setStatus('Voice on · press Play')
      }
      setEnabled(v => !v)
    },
    speak: () => {
      window.speechSynthesis?.resume()
      speak()
    },
  }
}
