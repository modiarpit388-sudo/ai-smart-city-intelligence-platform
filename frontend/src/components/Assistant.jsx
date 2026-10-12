import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Bot, Send, Sparkles, X } from 'lucide-react'
import { api } from '../api'

const START = [{ who: 'ai', text: "Hi! I'm your AI City Assistant. Ask about traffic, air quality, water, waste, electricity or accident risk — I answer from live city data and ML forecasts, never guesses." }]

export default function Assistant() {
  const [open, setOpen] = useState(false)
  const [msgs, setMsgs] = useState(START)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [sugg, setSugg] = useState([])
  const end = useRef(null)

  useEffect(() => { api.get('/api/assistant/suggestions').then((r) => setSugg(r.suggestions)).catch(() => {}) }, [])
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy, open])

  const send = async (q) => {
    const message = (q ?? text).trim()
    if (!message || busy) return
    setText(''); setMsgs((m) => [...m, { who: 'me', text: message }]); setBusy(true)
    try {
      const r = await api.post('/api/assistant/chat', { message })
      setMsgs((m) => [...m, { who: 'ai', text: r.answer, src: r.source }])
    } catch (e) {
      setMsgs((m) => [...m, { who: 'ai', text: `Sorry, I couldn't fetch that: ${e.message}` }])
    } finally { setBusy(false) }
  }

  return (
    <>
      <AnimatePresence>
        {open && (
          <motion.div className="chat" initial={{ opacity: 0, y: 30, scale: 0.94 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 30, scale: 0.94 }}>
            <div className="chat-h">
              <Sparkles size={20} color="#22d3ee" />
              <div style={{ flex: 1 }}><b>AI CITY ASSISTANT</b><small>Grounded in live data + ML forecasts</small></div>
              <button className="icon-btn" onClick={() => setOpen(false)}><X /></button>
            </div>
            <div className="chat-body">
              {msgs.map((m, i) => (
                <div key={i} className={`msg ${m.who}`}>{m.text}{m.src && <small>{m.src === 'llm+data' ? 'LLM · verified data' : 'verified city data'}</small>}</div>
              ))}
              {busy && <div className="msg ai typing"><span /><span /><span /></div>}
              {msgs.length < 3 && <div className="suggest">{sugg.map((s) => <button key={s} onClick={() => send(s)}>{s}</button>)}</div>}
              <div ref={end} />
            </div>
            <div className="chat-f">
              <input className="input" placeholder="Ask about your city…" value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && send()} />
              <button className="btn primary" onClick={() => send()} disabled={busy}><Send /></button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <motion.button className="fab" onClick={() => setOpen((o) => !o)} whileHover={{ scale: 1.08 }} whileTap={{ scale: 0.93 }} title="AI City Assistant"><Bot /></motion.button>
    </>
  )
}
