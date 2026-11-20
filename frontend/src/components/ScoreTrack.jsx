import { pct } from '../services/format.js'

// 0-50% scale split into bands that are multiples of the SAVED threshold (0.5x, 1x, 2x).
export default function ScoreTrack({ probability, threshold }) {
  const MAX = 0.5
  const at = (x) => `${Math.min(1, x / MAX) * 100}%`
  const bands = [[0, threshold * 0.5, 'var(--green)'], [threshold * 0.5, threshold, 'var(--blue)'], [threshold, threshold * 2, 'var(--orange)'], [threshold * 2, MAX, 'var(--coral)']]
  return (
    <div>
      <div className="track" role="img" aria-label={`Score ${pct(probability)} on a scale where the decision threshold is ${pct(threshold, 0)}`}>
        {bands.map(([a, b, c], i) => <div key={i} className="seg-band" style={{ width: `${((b - a) / MAX) * 100}%`, background: c, opacity: 0.85 }} />)}
        <div className="tick" style={{ left: at(threshold) }}><span>Threshold {pct(threshold, 0)}</span></div>
        <div className="marker" style={{ left: at(probability) }} data-label={pct(probability)} />
      </div>
      <div className="row tiny" style={{ gap: 16 }}>
        {[['var(--green)', 'Low'], ['var(--blue)', 'Moderate'], ['var(--orange)', 'Elevated'], ['var(--coral)', 'High']].map(([c, l]) =>
          <span key={l}><i className="legend-dot" style={{ background: c }} />{l}</span>)}
        <span>Scale shows 0–50%{probability > MAX ? '; this score is above the scale' : ''}.</span>
      </div>
    </div>
  )
}
