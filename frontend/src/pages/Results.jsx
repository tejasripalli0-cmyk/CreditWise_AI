import { lazy, Suspense } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Download, FileText } from 'lucide-react'
import { usePrediction } from '../services/PredictionContext.jsx'
import { download, pct, shown, signed } from '../services/format.js'
import ScoreTrack from '../components/ScoreTrack.jsx'
import { Alert, Meter, Skeleton } from '../components/ui.jsx'

const ContributionChart = lazy(() => import('../charts/ContributionChart.jsx'))
const BAND_BADGE = { low: 'green', moderate: 'blue', elevated: 'orange', high: 'coral' }
const SRC_BADGE = { entered: ['You entered', 'blue'], calculated: ['Calculated', 'green'], assumed: ['Assumed', 'grey'] }

export default function Results() {
  const { result: r } = usePrediction()
  if (!r) {
    return (
      <div className="container empty">
        <h2>No prediction yet</h2>
        <p className="muted">Results appear here after you submit applicant details. They are kept only in this tab&apos;s memory.</p>
        <Link to="/predict" className="btn btn-primary">Go to the prediction form</Link>
      </div>
    )
  }
  const { prediction: p, completeness: c, explanation: e, warnings } = r
  const bandKey = p.risk_band.key

  const summaryText = () => [
    'CreditWise AI: prediction summary', '='.repeat(36),
    `Predicted class: ${p.predicted_class} (${p.label})`,
    `Model score: ${pct(p.probability, 2)} (uncalibrated model output)`,
    `Saved decision threshold: ${p.threshold}`,
    `Score band relative to threshold: ${p.risk_band.label}`,
    `Fields entered: ${c.user_provided}; calculated: ${c.auto_derived}; filled with typical values: ${c.assumed_default} of ${c.total_features}`,
    `Information coverage: ${pct(c.importance_coverage, 0)} (${c.level})`, '',
    'Details you entered:', ...Object.entries(r.submitted).map(([k, v]) => `  - ${r.labels[k]}: ${shown(v)}`), '',
    ...(e.available ? ['Largest influences (log-odds):', ...e.contributions.map((x) => `  ${signed(x.contribution, 3)}  ${x.label} [${x.source}]`), ''] : []),
    ...r.summary, '', 'Not a CIBIL score. Not a lending decision. Educational model trained on the Home Credit dataset.',
  ].join('\n')

  return (
    <div className="container" style={{ paddingBottom: 40 }}>
      <div className="page-title row spread">
        <div><h1 style={{ fontSize: 'clamp(2rem,4vw,2.8rem)' }}>Prediction results</h1><p>Model output for the details you provided.</p></div>
        <div className="row">
          <Link to="/predict" className="btn btn-secondary"><ArrowLeft size={16} />Edit details</Link>
          <button className="btn btn-secondary" onClick={() => download('creditwise-summary.txt', summaryText())}><FileText size={16} />Summary (.txt)</button>
          <button className="btn btn-secondary" onClick={() => download('creditwise-result.json', JSON.stringify({ ...r, labels: undefined }, null, 2), 'application/json')}><Download size={16} />Data (.json)</button>
        </div>
      </div>

      <div className="result-hero">
        <section className="card card-lg">
          <span className={`class-pill c${p.predicted_class}`}>Predicted class {p.predicted_class}: {p.label}</span>
          <div className="big-score">{pct(p.probability)}</div>
          <p className="muted" style={{ marginTop: 6 }}>Model score for recorded payment difficulty <span className={`badge ${BAND_BADGE[bandKey]}`}>{p.risk_band.label} band</span></p>
          <ScoreTrack probability={p.probability} threshold={p.threshold} />
          <p className="small muted">{p.risk_band.description} Class 1 is predicted when the score reaches the saved threshold of {pct(p.threshold, 0)}, not the usual 50%.</p>
          <Alert kind="info">{p.probability_note}</Alert>
        </section>

        <section className="card card-lg">
          <h3>Applicant information completeness</h3>
          <div className="row spread"><span className="num" style={{ fontSize: '2rem', fontWeight: 700 }}>{pct(c.importance_coverage, 0)}</span>
            <span className={`badge ${c.level === 'good' ? 'green' : c.level === 'moderate' ? 'orange' : 'coral'}`}>{c.level === 'good' ? 'Good' : c.level === 'moderate' ? 'Moderate' : 'Limited'} coverage</span></div>
          <Meter value={c.importance_coverage} level={c.level} />
          <div style={{ marginTop: 12 }}>
            <div className="stat-line"><span className="k">Entered by you</span><span className="v">{c.user_provided}</span></div>
            <div className="stat-line"><span className="k">Calculated from your inputs</span><span className="v">{c.auto_derived}</span></div>
            <div className="stat-line"><span className="k">Filled with typical values</span><span className="v">{c.assumed_default} of {c.total_features}</span></div>
            <div className="stat-line"><span className="k">Decision threshold</span><span className="v">{p.threshold}</span></div>
          </div>
          <p className="tiny" style={{ marginTop: 10 }}>{c.basis} Missing details are not recovered; the model substitutes typical training values.</p>
        </section>
      </div>

      {warnings.length > 0 && <div className="stack" style={{ marginTop: 20 }}>{warnings.map((w) => <Alert key={w.code} kind={w.level === 'warning' ? 'warning' : 'info'}>{w.message}</Alert>)}</div>}

      <section className="card card-lg" style={{ marginTop: 24 }}>
        <h3>What influenced this prediction</h3>
        {e.available ? (
          <>
            <p className="muted">{e.method}. The model&apos;s baseline output, averaged over its training data, corresponds to a score of about {pct(e.base_probability)}. The contributions below move this applicant from that baseline to {pct(p.probability)}.</p>
            <Suspense fallback={<Skeleton h={420} />}><ContributionChart explanation={e} /></Suspense>
            <div className="row tiny" style={{ gap: 18, margin: '4px 0 16px' }}>
              <span><i className="legend-dot" style={{ background: '#f29a1f' }} />Raises the score</span>
              <span><i className="legend-dot" style={{ background: '#2f6bff' }} />Lowers the score</span>
              <span>Faded dashed bars: not provided, filled with a typical value</span>
            </div>
            <div className="table-wrap">
              <table className="data">
                <thead><tr><th>Field</th><th>Value used</th><th>Source</th><th>Effect (log-odds)</th></tr></thead>
                <tbody>{e.contributions.map((x) => (
                  <tr key={x.feature}><td>{x.label}</td><td>{shown(x.value)}</td><td><span className={`badge ${SRC_BADGE[x.source][1]}`}>{SRC_BADGE[x.source][0]}</span></td>
                    <td style={{ color: x.contribution > 0 ? '#b36b00' : 'var(--blue)', fontWeight: 650 }}>{signed(x.contribution, 3)}</td></tr>))}
                </tbody>
              </table>
            </div>
            <p className="small muted" style={{ marginTop: 14 }}>
              Of the total movement, {signed(e.from_provided_fields, 2)} comes from details you provided or that were calculated from them, and {signed(e.from_assumed_defaults, 2)} from typical values the model assumed for missing details. {e.reading_guide}
            </p>
          </>
        ) : <Alert kind="warning">{e.reason} The global feature importance on the Analytics page still describes the model overall, but it is not an explanation of this applicant.</Alert>}
      </section>

      <section className="card" style={{ marginTop: 24 }}>
        <h3>In plain words</h3>
        {r.summary.map((s, i) => <p key={i} className="muted" style={{ marginBottom: 8 }}>{s}</p>)}
        <p className="tiny" style={{ marginTop: 12 }}>Target meaning: 0 = {r.model.target_mapping['0']}; 1 = {r.model.target_mapping['1']}.</p>
      </section>
    </div>
  )
}
