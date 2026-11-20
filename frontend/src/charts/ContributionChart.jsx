import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { shown, signed } from '../services/format.js'

const SRC = { entered: 'You entered', calculated: 'Calculated from your inputs', assumed: 'Assumed typical value (not provided)' }

function Tip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="card" style={{ padding: 12, fontSize: 13, maxWidth: 260 }}>
      <strong>{d.label}</strong>
      {d.value !== undefined && <div>Value: {shown(d.value)}</div>}
      <div>{d.contribution > 0 ? 'Raises' : 'Lowers'} the score by {signed(d.contribution, 3)} log-odds</div>
      {d.source && <div className="tiny">{SRC[d.source]}</div>}
    </div>
  )
}

export default function ContributionChart({ explanation }) {
  const rows = explanation.contributions.map((c) => ({ ...c, name: c.label }))
  if (explanation.other_count > 0) rows.push({ name: `${explanation.other_count} other fields`, label: `${explanation.other_count} other fields combined`, contribution: explanation.other_contribution, source: null })
  const max = Math.ceil(Math.max(0.5, ...rows.map((r) => Math.abs(r.contribution))) * 2) / 2
  return (
    <div className="chart-box tall">
      <ResponsiveContainer>
        <BarChart data={rows} layout="vertical" margin={{ left: 4, right: 24, top: 8, bottom: 24 }}>
          <CartesianGrid horizontal={false} stroke="#e6eef9" />
          <XAxis type="number" domain={[-max, max]} tickCount={7} tickFormatter={(v) => v.toFixed(1)} label={{ value: 'Effect on score (log-odds): left lowers, right raises', position: 'insideBottom', offset: -14, fontSize: 12, fill: '#5b6b86' }} />
          <YAxis type="category" dataKey="name" width={215} tick={{ fontSize: 12.5, fill: '#14223f' }} interval={0} />
          <Tooltip content={<Tip />} cursor={{ fill: 'rgba(47,107,255,0.06)' }} />
          <ReferenceLine x={0} stroke="#14223f" />
          <Bar dataKey="contribution" radius={4} isAnimationActive={false}>
            {rows.map((r, i) => <Cell key={i} fill={r.contribution > 0 ? '#f29a1f' : '#2f6bff'} fillOpacity={r.source === 'assumed' || !r.source ? 0.4 : 1} stroke={r.source === 'assumed' ? (r.contribution > 0 ? '#f29a1f' : '#2f6bff') : 'none'} strokeDasharray="4 3" />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
