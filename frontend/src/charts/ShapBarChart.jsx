import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function ShapBarChart({ rows, n }) {
  const data = rows.slice(0, n).map((r) => ({ name: r.label || r.feature, importance: r.importance }))
  return (
    <div className="chart-box tall" style={{ height: Math.max(340, n * 28 + 70) }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 20, top: 6, bottom: 26 }}>
          <CartesianGrid horizontal={false} stroke="#e6eef9" />
          <XAxis type="number" label={{ value: 'Mean absolute SHAP value', position: 'insideBottom', offset: -12, fontSize: 12, fill: '#5b6b86' }} />
          <YAxis type="category" dataKey="name" width={190} tick={{ fontSize: 12 }} interval={0} />
          <Tooltip formatter={(v) => Number(v).toFixed(4)} cursor={{ fill: 'rgba(47,107,255,0.06)' }} />
          <Bar dataKey="importance" name="Mean |SHAP|" fill="#7a5af8" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
