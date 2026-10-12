import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, LineChart, Pie, PieChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const Tip = ({ active, payload, label, unit = '' }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tip">
      <b>{label}</b>
      {payload.filter((p) => p.value != null && !String(p.dataKey).startsWith('_')).map((p) => (
        <div key={p.dataKey}><span style={{ color: p.color || p.stroke }}>●</span> {p.name}: <span className="mono">{Number(p.value).toLocaleString()}{unit}</span></div>
      ))}
    </div>
  )
}

/** Past actuals (solid) joined to model forecast (dashed, glowing). */
export function ForecastChart({ history = [], forecast = [], color = '#22d3ee', unit = '', height = 260, refLine, dotColor, domain, name = 'value' }) {
  const data = []
  history.forEach((h) => data.push({ label: h.label, actual: h.value }))
  if (history.length && forecast.length) data[data.length - 1].predicted = data[data.length - 1].actual
  forecast.forEach((f) => data.push({ label: f.label, predicted: f.value, _lv: f.level }))
  const id = `g${color.replace('#', '')}`
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 8, right: 10, left: -12, bottom: 0 }}>
        <defs>
          <linearGradient id={id} x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor={color} stopOpacity=".45" /><stop offset="1" stopColor={color} stopOpacity="0" /></linearGradient>
        </defs>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="label" tickLine={false} axisLine={false} interval="preserveStartEnd" minTickGap={18} />
        <YAxis tickLine={false} axisLine={false} domain={domain || ['auto', 'auto']} width={48} />
        <Tooltip content={<Tip unit={unit} />} />
        {refLine && <ReferenceLine y={refLine.y} stroke={refLine.color || '#fb7185'} strokeDasharray="4 4" label={{ value: refLine.label, fill: refLine.color || '#fb7185', fontSize: 10, position: 'insideTopRight' }} />}
        <Area type="monotone" dataKey="actual" name={`Actual ${name}`} stroke="#94a3d8" strokeWidth={2} fill="none" dot={false} connectNulls />
        <Area type="monotone" dataKey="predicted" name={`Predicted ${name}`} stroke={color} strokeWidth={2.5} strokeDasharray="6 4" fill={`url(#${id})`} connectNulls animationDuration={1400}
          dot={dotColor ? (p) => (p.payload.predicted == null ? null : <circle key={p.index} cx={p.cx} cy={p.cy} r={4} fill={dotColor(p.payload.predicted)} stroke="#050a17" strokeWidth={1.5} />) : false}
          style={{ filter: `drop-shadow(0 0 6px ${color}88)` }} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}

export function SimpleArea({ data, dataKey = 'value', color = '#22d3ee', unit = '', height = 200, xKey = 'label', name }) {
  const id = `s${color.replace('#', '')}${dataKey}`
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 6, right: 8, left: -14, bottom: 0 }}>
        <defs><linearGradient id={id} x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor={color} stopOpacity=".5" /><stop offset="1" stopColor={color} stopOpacity="0" /></linearGradient></defs>
        <CartesianGrid vertical={false} />
        <XAxis dataKey={xKey} tickLine={false} axisLine={false} minTickGap={20} />
        <YAxis tickLine={false} axisLine={false} width={44} />
        <Tooltip content={<Tip unit={unit} />} />
        <Area type="monotone" dataKey={dataKey} name={name || dataKey} stroke={color} strokeWidth={2.4} fill={`url(#${id})`} animationDuration={1300} style={{ filter: `drop-shadow(0 0 6px ${color}77)` }} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function ColorBars({ data, dataKey = 'value', colorFn, unit = '', height = 220, xKey = 'label', name }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 6, right: 8, left: -14, bottom: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey={xKey} tickLine={false} axisLine={false} minTickGap={12} />
        <YAxis tickLine={false} axisLine={false} width={44} />
        <Tooltip content={<Tip unit={unit} />} cursor={{ fill: 'rgba(125,165,255,.06)' }} />
        <Bar dataKey={dataKey} name={name || dataKey} radius={[7, 7, 0, 0]} animationDuration={1200}>
          {data.map((d, i) => <Cell key={i} fill={colorFn ? colorFn(d[dataKey], d) : '#22d3ee'} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export function MultiLine({ data, lines, height = 240, xKey = 'bucket', unit = '' }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey={xKey} tickLine={false} axisLine={false} minTickGap={24} />
        <YAxis tickLine={false} axisLine={false} width={48} />
        <Tooltip content={<Tip unit={unit} />} />
        {lines.map((l) => <Line key={l.key} type="monotone" dataKey={l.key} name={l.label} stroke={l.color} strokeWidth={2.4} dot={false} animationDuration={1200} />)}
      </LineChart>
    </ResponsiveContainer>
  )
}

const PIE = ['#22d3ee', '#8b5cf6', '#fbbf24', '#fb7185', '#34d399', '#3b82f6']
export function Donut({ data, unit = '', height = 220 }) {
  const total = data.reduce((s, d) => s + d.value, 0)
  return (
    <div style={{ position: 'relative' }}>
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius="62%" outerRadius="88%" paddingAngle={3} stroke="none" animationDuration={1200}>
            {data.map((d, i) => <Cell key={i} fill={PIE[i % PIE.length]} style={{ filter: `drop-shadow(0 0 6px ${PIE[i % PIE.length]}66)` }} />)}
          </Pie>
          <Tooltip content={<Tip unit={unit} />} />
        </PieChart>
      </ResponsiveContainer>
      <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', pointerEvents: 'none' }}>
        <div className="center"><b className="mono" style={{ fontSize: 22 }}>{total.toFixed(1)}</b><div className="mute" style={{ fontSize: 11 }}>{unit || 'total'}</div></div>
      </div>
    </div>
  )
}
export const pieColor = (i) => PIE[i % PIE.length]
