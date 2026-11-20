import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export const METRIC_COLORS = { Accuracy: '#2f6bff', Precision: '#7a5af8', Recall: '#0f9d8a', 'F1 Score': '#f29a1f', 'ROC-AUC': '#dc4c2f', 'PR-AUC': '#14223f' }

export default function ModelComparisonChart({ rows, metrics }) {
  return (
    <div className="chart-box">
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 10, right: 12, left: 0, bottom: 8 }}>
          <CartesianGrid vertical={false} stroke="#e6eef9" />
          <XAxis dataKey="model" tick={{ fontSize: 12.5 }} interval={0} />
          <YAxis domain={[0, 1]} tickFormatter={(v) => v.toFixed(1)} label={{ value: 'Score (0–1)', angle: -90, position: 'insideLeft', fontSize: 12, fill: '#5b6b86' }} />
          <Tooltip formatter={(v) => Number(v).toFixed(4)} cursor={{ fill: 'rgba(47,107,255,0.06)' }} />
          <Legend />
          {metrics.map((m) => <Bar key={m} dataKey={m} fill={METRIC_COLORS[m]} radius={[4, 4, 0, 0]} />)}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
