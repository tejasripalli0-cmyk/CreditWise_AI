import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function ThresholdChart({ data, saved, selected }) {
  return (
    <div className="chart-box">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 16, right: 16, left: 0, bottom: 24 }}>
          <CartesianGrid stroke="#e6eef9" />
          <XAxis type="number" dataKey="threshold" domain={[0.1, 0.9]} ticks={[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]} label={{ value: 'Classification threshold', position: 'insideBottom', offset: -12, fontSize: 12, fill: '#5b6b86' }} />
          <YAxis domain={[0, 1]} tickFormatter={(v) => v.toFixed(1)} />
          <Tooltip formatter={(v) => Number(v).toFixed(3)} labelFormatter={(l) => `Threshold ${l}`} />
          <Legend verticalAlign="top" />
          <ReferenceLine x={saved} stroke="#dc4c2f" strokeDasharray="5 4" label={{ value: `Saved ${saved}`, fill: '#dc4c2f', fontSize: 12, position: 'top' }} />
          {selected !== saved && <ReferenceLine x={selected} stroke="#7a5af8" strokeDasharray="2 3" />}
          <Line type="monotone" dataKey="precision" name="Precision" stroke="#7a5af8" strokeWidth={2.5} dot={false} />
          <Line type="monotone" dataKey="recall" name="Recall" stroke="#0f9d8a" strokeWidth={2.5} dot={false} />
          <Line type="monotone" dataKey="f1" name="F1-score" stroke="#f29a1f" strokeWidth={2.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
