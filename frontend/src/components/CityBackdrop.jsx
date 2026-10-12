import { useEffect, useMemo, useRef } from 'react'

// small seeded RNG so the skyline is identical on every render
function rng(seed) { let s = seed; return () => ((s = (s * 16807) % 2147483647) - 1) / 2147483646 }

export function Ambient() {
  return (
    <div className="ambient" aria-hidden>
      <div className="orb o1" /><div className="orb o2" /><div className="scan" />
    </div>
  )
}

/** Animated network of "IoT nodes": particles that connect and react to the mouse. */
export function ParticleField({ density = 0.00009, color = '34,211,238' }) {
  const ref = useRef(null)
  useEffect(() => {
    const cv = ref.current
    const ctx = cv.getContext('2d')
    let raf, w, h, pts = []
    const mouse = { x: -999, y: -999 }
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const resize = () => {
      const r = cv.parentElement.getBoundingClientRect()
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      w = r.width; h = r.height
      cv.width = w * dpr; cv.height = h * dpr; cv.style.width = w + 'px'; cv.style.height = h + 'px'
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      const n = Math.round(w * h * density)
      pts = Array.from({ length: n }, () => ({ x: Math.random() * w, y: Math.random() * h, vx: (Math.random() - 0.5) * 0.35, vy: (Math.random() - 0.5) * 0.35, r: Math.random() * 1.6 + 0.6, v: Math.random() > 0.8 }))
    }
    const move = (e) => { const r = cv.getBoundingClientRect(); mouse.x = e.clientX - r.left; mouse.y = e.clientY - r.top }
    const draw = () => {
      ctx.clearRect(0, 0, w, h)
      for (let i = 0; i < pts.length; i++) {
        const p = pts[i]
        if (!reduce) { p.x += p.vx; p.y += p.vy }
        if (p.x < 0 || p.x > w) p.vx *= -1
        if (p.y < 0 || p.y > h) p.vy *= -1
        const dm = Math.hypot(p.x - mouse.x, p.y - mouse.y)
        if (dm < 130) { p.x += (p.x - mouse.x) * 0.012; p.y += (p.y - mouse.y) * 0.012 }
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 7)
        ctx.fillStyle = p.v ? 'rgba(167,139,250,.9)' : `rgba(${color},.85)`; ctx.fill()
        for (let j = i + 1; j < pts.length; j++) {
          const q = pts[j], d = Math.hypot(p.x - q.x, p.y - q.y)
          if (d < 120) { ctx.strokeStyle = `rgba(${color},${(1 - d / 120) * 0.22})`; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke() }
        }
      }
      raf = requestAnimationFrame(draw)
    }
    resize(); draw()
    window.addEventListener('resize', resize); window.addEventListener('mousemove', move)
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize); window.removeEventListener('mousemove', move) }
  }, [density, color])
  return <canvas ref={ref} style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }} />
}

/** Night skyline: flickering windows, driving cars, a patrol drone, sensor beams, twinkling stars. */
export function Skyline() {
  const scene = useMemo(() => {
    const r = rng(42)
    const buildings = []
    let x = -10
    while (x < 1210) {
      const w = 34 + r() * 62, h = 70 + r() * 170
      const tall = r() > 0.86
      buildings.push({ x, w, h: tall ? h + 60 : h, antenna: r() > 0.7, tint: r() })
      x += w + 2 + r() * 6
    }
    buildings.forEach((b) => {
      b.wins = []
      for (let wx = b.x + 6; wx < b.x + b.w - 8; wx += 10)
        for (let wy = 300 - 30 - b.h + 10; wy < 300 - 40; wy += 13)
          if (r() > 0.42) b.wins.push({ x: wx, y: wy, d: r() * 6, c: r() > 0.85 ? '#a78bfa' : r() > 0.5 ? '#67e8f9' : '#fde68a' })
    })
    const stars = Array.from({ length: 46 }, () => ({ x: r() * 1200, y: r() * 130, d: r() * 4, s: r() * 1.4 + 0.4 }))
    return { buildings, stars }
  }, [])
  return (
    <div className="skyline" aria-hidden>
      <svg viewBox="0 0 1200 300" preserveAspectRatio="xMidYMax slice">
        <defs>
          <linearGradient id="bg1" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#0f1c3d" /><stop offset="1" stopColor="#070d1f" /></linearGradient>
          <linearGradient id="bg2" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#15264d" /><stop offset="1" stopColor="#09112a" /></linearGradient>
          <radialGradient id="moon"><stop offset="0" stopColor="#fff" stopOpacity=".95" /><stop offset="1" stopColor="#a5f3fc" stopOpacity="0" /></radialGradient>
          <linearGradient id="beamG" x1="0" x2="0" y1="1" y2="0"><stop offset="0" stopColor="#22d3ee" stopOpacity=".6" /><stop offset="1" stopColor="#22d3ee" stopOpacity="0" /></linearGradient>
        </defs>
        {scene.stars.map((s, i) => <circle key={i} className="star" cx={s.x} cy={s.y} r={s.s} fill="#fff" style={{ animationDelay: `${s.d}s` }} />)}
        <circle cx="980" cy="70" r="46" fill="url(#moon)" opacity=".55" /><circle cx="980" cy="70" r="16" fill="#e0f2fe" opacity=".9" />
        {scene.buildings.map((b, i) => (
          <g key={i}>
            <rect x={b.x} y={300 - 30 - b.h} width={b.w} height={b.h} fill={b.tint > 0.5 ? 'url(#bg1)' : 'url(#bg2)'} stroke="rgba(120,160,255,.14)" />
            {b.antenna && <><line x1={b.x + b.w / 2} y1={300 - 30 - b.h} x2={b.x + b.w / 2} y2={300 - 30 - b.h - 26} stroke="#3b4a75" strokeWidth="2" /><circle className="win" cx={b.x + b.w / 2} cy={300 - 30 - b.h - 28} r="2.6" fill="#fb7185" style={{ animationDelay: `${i * 0.3}s` }} /></>}
            {b.wins.map((w, j) => <rect key={j} className="win" x={w.x} y={w.y} width="5" height="7" rx="1" fill={w.c} style={{ animationDelay: `${w.d}s`, animationDuration: `${3 + (j % 5)}s` }} />)}
          </g>
        ))}
        {[180, 470, 760, 1040].map((x, i) => <polygon key={x} className="beam" points={`${x},250 ${x - 60},20 ${x + 60},20`} fill="url(#beamG)" style={{ animationDelay: `${i * 0.9}s` }} />)}
        <rect x="0" y="270" width="1200" height="30" fill="#060b1a" />
        <line x1="0" y1="285" x2="1200" y2="285" stroke="#22d3ee" strokeOpacity=".25" strokeDasharray="18 14" />
        {[0, 1, 2, 3].map((i) => (
          <g key={i} className="car" style={{ animationDuration: `${8 + i * 2.5}s`, animationDelay: `${-i * 3}s` }}>
            <rect x="0" y="276" width="26" height="8" rx="3" fill="#0b1226" stroke="#22d3ee" strokeOpacity=".6" />
            <circle cx="26" cy="280" r="7" fill="#fde68a" opacity=".35" /><circle cx="25" cy="280" r="2" fill="#fef9c3" />
          </g>
        ))}
        {[0, 1, 2].map((i) => (
          <g key={i} className="car rev" style={{ animationDuration: `${10 + i * 2}s`, animationDelay: `${-i * 4 - 1}s` }}>
            <rect x="0" y="288" width="26" height="8" rx="3" fill="#0b1226" stroke="#fb7185" strokeOpacity=".6" />
            <circle cx="1" cy="292" r="7" fill="#fb7185" opacity=".3" /><circle cx="2" cy="292" r="2" fill="#fecdd3" />
          </g>
        ))}
        <g className="drone"><g transform="translate(120,80)"><ellipse cx="0" cy="0" rx="10" ry="3" fill="#0b1226" stroke="#a78bfa" /><circle cx="0" cy="4" r="2" fill="#a78bfa" className="win" /><line x1="-13" y1="-3" x2="13" y2="-3" stroke="#67e8f9" strokeWidth="1.5" /></g></g>
      </svg>
    </div>
  )
}
