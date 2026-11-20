import { lazy, Suspense, useState } from 'react'
import { api } from '../services/api.js'
import { useAsync } from '../services/hooks.js'
import { fix, grouped, pct } from '../services/format.js'
import { Alert, ErrorState, Skeleton } from '../components/ui.jsx'

const ModelComparisonChart = lazy(() => import('../charts/ModelComparisonChart.jsx'))
const ThresholdChart = lazy(() => import('../charts/ThresholdChart.jsx'))
const ShapBarChart = lazy(() => import('../charts/ShapBarChart.jsx'))
const CHART_FALLBACK = <Skeleton h={360} />

const Section = ({ id, title, sub, children }) => (
  <section id={id} className="section-tight"><div className="container"><div className="section-head" style={{ marginBottom: 20 }}><h2>{title}</h2>{sub && <p>{sub}</p>}</div>{children}</div></section>
)

export default function Analytics() {
  const { data: d, error, loading, reload } = useAsync(() => api.analytics(), [])
  const [metrics, setMetrics] = useState(['ROC-AUC', 'PR-AUC', 'Recall', 'F1 Score'])
  const [topN, setTopN] = useState(15)
  const [encoded, setEncoded] = useState(false)
  const [sel, setSel] = useState(null)

  if (error) return <div className="container page-title"><ErrorState error={error} onRetry={reload} /></div>
  if (loading || !d) return <div className="container page-title"><Skeleton h={40} w="40%" /><div style={{ height: 20 }} /><div className="grid g4"><Skeleton h={110} /><Skeleton h={110} /><Skeleton h={110} /><Skeleton h={110} /></div></div>

  const mc = d.model_comparison, f = d.final_metrics, cm = d.confusion_matrix
  const toggle = (m) => setMetrics((s) => (s.includes(m) ? (s.length > 1 ? s.filter((x) => x !== m) : s) : [...s, m]))
  const saved = d.saved_threshold
  const row = d.thresholds.reduce((a, b) => (Math.abs(b.threshold - (sel ?? saved)) < Math.abs(a.threshold - (sel ?? saved)) ? b : a))
  const shapRows = encoded ? d.shap.top_encoded_columns : d.shap.top_original_features
  const navItems = [['overview', 'Overview'], ['comparison', 'Models'], ['tuning', 'Tuning'], ['performance', 'Performance'], ['shap', 'SHAP'], ['threshold', 'Threshold'], ['dataset', 'Dataset']]

  return (
    <>
      <div className="container page-title"><h1 style={{ fontSize: 'clamp(2rem,4vw,2.8rem)' }}>Model analytics</h1>
        <p>Everything here is read from the results exported from the original training notebook. No sample or simulated data.</p></div>
      <nav className="subnav" aria-label="Sections"><div className="container subnav-inner">{navItems.map(([id, l]) => <a key={id} href={`#${id}`}>{l}</a>)}</div></nav>

      <Section id="overview" title="Selected model at a glance">
        <div className="grid g4">
          {[['ROC-AUC', fix(f.roc_auc), 'Ranking quality, threshold-free'], ['PR-AUC', fix(f.pr_auc), 'Precision-recall area, threshold-free'], ['Recall', pct(f.recall), `Caught at threshold ${f.threshold}`], ['Precision', pct(f.precision), `Correct among flagged at ${f.threshold}`]].map(([l, v, s]) => (
            <div className="card kpi" key={l}><div className="l">{l}</div><div className="v">{v}</div><div className="d">{s}</div></div>))}
        </div>
      </Section>

      <Section id="comparison" title="Model comparison" sub={`${mc.rows.length} models were trained and compared. Best overall: ${mc.best_model}, chosen on ${mc.best_basis}.`}>
        <div className="card card-lg">
          <div className="pill-group" style={{ marginBottom: 16 }} aria-label="Metrics to show">
            {mc.metrics.map((m) => <button key={m} className={`pill ${metrics.includes(m) ? 'on' : ''}`} aria-pressed={metrics.includes(m)} onClick={() => toggle(m)}>{m}</button>)}
          </div>
          <Suspense fallback={CHART_FALLBACK}><ModelComparisonChart rows={mc.rows} metrics={metrics} /></Suspense>
          <div className="table-wrap" style={{ marginTop: 18 }}>
            <table className="data"><thead><tr><th>Model</th>{mc.metrics.map((m) => <th key={m}>{m}</th>)}<th>Train time (s)</th></tr></thead>
              <tbody>{mc.rows.map((r) => (
                <tr key={r.model} className={r.model === mc.best_model ? 'hl' : ''}><td><strong>{r.model}</strong> {r.model === mc.best_model && <span className="badge green">Best overall</span>}</td>
                  {mc.metrics.map((m) => <td key={m} className={mc.best_by_metric[m] === r.model ? 'best' : ''}>{fix(r[m], 4)}</td>)}<td>{r.training_time_seconds}</td></tr>))}</tbody></table>
          </div>
          <p className="tiny" style={{ marginTop: 10 }}>Green values are the best in each column. Bagging has the highest accuracy and precision, but with very low recall, so it misses most difficult cases.</p>
          <Alert kind="info">{mc.note}</Alert>
        </div>
      </Section>

      <Section id="tuning" title="Hyperparameter tuning" sub="Cross-validated search scored on PR-AUC for three candidate models.">
        <div className="grid g3">
          {d.tuning.map((t) => (
            <div className="card" key={t.model} style={t.model === f.model ? { borderColor: 'var(--blue)', boxShadow: 'var(--shadow-md)' } : {}}>
              <div className="row spread"><h3 style={{ margin: 0 }}>{t.model}</h3>{t.model === f.model && <span className="badge">Selected</span>}</div>
              <p className="num" style={{ fontSize: '1.8rem', fontWeight: 700, margin: '10px 0 2px' }}>{fix(t.best_cv_pr_auc, 4)}</p>
              <div className="tiny" style={{ marginBottom: 10 }}>Best cross-validated PR-AUC</div>
              {Object.entries(t.best_parameters).map(([k, v]) => <div className="stat-line" key={k}><span className="k small">{k}</span><span className="v small">{String(v)}</span></div>)}
            </div>))}
        </div>
      </Section>

      <Section id="performance" title="Final model performance" sub={`Gradient Boosting evaluated on ${grouped(cm.total)} held-out applications at the saved threshold of ${f.threshold}.`}>
        <div className="grid g2">
          <div className="card card-lg">
            <h3>Saved metrics</h3>
            {[['Accuracy', f.accuracy], ['Precision', f.precision], ['Recall', f.recall], ['F1-score', f.f1], ['ROC-AUC', f.roc_auc], ['PR-AUC', f.pr_auc]].map(([k, v]) => <div className="stat-line" key={k}><span className="k">{k}</span><span className="v">{fix(v, 4)}</span></div>)}
          </div>
          <div className="card card-lg">
            <h3>Confusion matrix</h3>
            <div className="img-frame"><img src={d.images.confusion_matrix} alt="Confusion matrix of the final model on held-out data" loading="lazy" /></div>
            <div className="cm-grid">
              <div className="cm-cell" style={{ background: 'var(--green-soft)' }}><div className="v">{grouped(cm.tn)}</div><div className="l">Correctly cleared</div></div>
              <div className="cm-cell" style={{ background: 'var(--orange-soft)' }}><div className="v">{grouped(cm.fp)}</div><div className="l">False alarms</div></div>
              <div className="cm-cell" style={{ background: 'var(--coral-soft)' }}><div className="v">{grouped(cm.fn)}</div><div className="l">Missed difficult cases</div></div>
              <div className="cm-cell" style={{ background: 'var(--blue-soft)' }}><div className="v">{grouped(cm.tp)}</div><div className="l">Correctly flagged</div></div>
            </div>
            <p className="tiny" style={{ marginTop: 8 }}>Counts transcribed from the exported image; they reproduce the saved accuracy, precision and recall exactly.</p>
          </div>
        </div>
      </Section>

      <Section id="shap" title="What the model relies on" sub={d.shap.grouping_note}>
        <div className="grid g2" style={{ gridTemplateColumns: 'minmax(0,1.1fr) minmax(0,0.9fr)' }}>
          <div className="card card-lg">
            <div className="row spread" style={{ marginBottom: 12 }}>
              <div className="pill-group">{[10, 15, 20].map((n) => <button key={n} className={`pill ${topN === n ? 'on' : ''}`} onClick={() => setTopN(n)}>Top {n}</button>)}</div>
              <div className="pill-group"><button className={`pill ${!encoded ? 'on' : ''}`} onClick={() => setEncoded(false)}>By original feature</button><button className={`pill ${encoded ? 'on' : ''}`} onClick={() => setEncoded(true)}>Encoded columns</button></div>
            </div>
            <Suspense fallback={CHART_FALLBACK}><ShapBarChart rows={shapRows} n={topN} /></Suspense>
            <p className="tiny">This is global importance across the test data. It is not an explanation of any one applicant; those appear on the results page.</p>
          </div>
          <div className="card card-lg"><h3>SHAP summary</h3><div className="img-frame"><img src={d.images.shap_summary} alt="SHAP summary plot from the original analysis" loading="lazy" /></div></div>
        </div>
      </Section>

      <Section id="threshold" title="Threshold analysis" sub="Moving the cut-off trades precision against recall. The saved model uses the value marked in red.">
        <div className="card card-lg">
          <Suspense fallback={CHART_FALLBACK}><ThresholdChart data={d.thresholds} saved={saved} selected={row.threshold} /></Suspense>
          <p className="tiny">At high thresholds very few applications are flagged, so precision swings sharply (and reaches 0 when none are flagged). Read the curve mainly in the 0.10–0.40 range.</p>
          <div className="grid g2" style={{ gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)', marginTop: 16, alignItems: 'center' }}>
            <div><input className="range" type="range" min={0.1} max={0.9} step={0.01} value={row.threshold} onChange={(e) => setSel(Number(e.target.value))} aria-label="Inspect threshold" />
              <div className="row spread small"><span>Inspecting threshold <strong className="num">{row.threshold.toFixed(2)}</strong></span>{row.threshold !== saved && <button className="btn btn-ghost btn-sm" onClick={() => setSel(saved)}>Saved {saved}</button>}</div></div>
            <div className="metric-trio" style={{ margin: 0 }}>
              <div className="metric-box"><div className="v">{pct(row.precision)}</div><div className="l">Precision</div></div>
              <div className="metric-box"><div className="v">{pct(row.recall)}</div><div className="l">Recall</div></div>
              <div className="metric-box"><div className="v">{pct(row.f1)}</div><div className="l">F1-score</div></div>
            </div>
          </div>
        </div>
      </Section>

      <Section id="dataset" title="Dataset information" sub="Only facts supported by the exported project are shown.">
        <div className="card card-lg">
          <div className="grid g2">
            <div>
              {[['Dataset', d.dataset.name], ['Target', 'Recorded payment difficulty (1) vs none (0)'], ['Held-out test rows', grouped(d.dataset.held_out_test_rows)],
                ['Difficulty cases in test set', `${grouped(d.dataset.held_out_positive_rows)} (${pct(d.dataset.held_out_positive_rate)})`]].map(([k, v]) => <div className="stat-line" key={k}><span className="k">{k}</span><span className="v">{v}</span></div>)}
            </div>
            <div>
              {[['Original input features', d.dataset.n_original_features], ['Numeric / categorical', `${d.dataset.n_numeric_features} / ${d.dataset.n_categorical_features}`], ['Columns after encoding', d.dataset.n_encoded_features]].map(([k, v]) => <div className="stat-line" key={k}><span className="k">{k}</span><span className="v">{v}</span></div>)}
              {d.dataset.preprocessing.map((p) => <p key={p} className="small muted" style={{ margin: '8px 0 0' }}>{p}</p>)}
            </div>
          </div>
          <p className="tiny" style={{ marginTop: 14 }}>Not included in the export, so not shown: {d.dataset.not_in_export.join('; ').toLowerCase()}.</p>
        </div>
      </Section>
    </>
  )
}
