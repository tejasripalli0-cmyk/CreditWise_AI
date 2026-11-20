import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Brain, ChartColumn, Database, Layers, Lock, Scale, SlidersHorizontal, Sparkles } from 'lucide-react'
import { api } from '../services/api.js'
import { useAsync } from '../services/hooks.js'
import { fix, pct } from '../services/format.js'
import { Skeleton } from '../components/ui.jsx'

function ThresholdExplorer() {
  const { data, error } = useAsync(() => api.analytics(), [])
  const [t, setT] = useState(null)
  if (error) return <div className="card explorer"><h3>Held-out test results</h3><p className="muted">Live results are unavailable right now. The Analytics page shows them once the service responds.</p></div>
  if (!data) return <div className="card explorer"><Skeleton h={28} w="60%" /><div style={{ height: 14 }} /><Skeleton h={90} /><div style={{ height: 14 }} /><Skeleton h={30} /></div>
  const saved = data.saved_threshold
  const sel = t ?? saved
  const row = data.thresholds.reduce((a, b) => (Math.abs(b.threshold - sel) < Math.abs(a.threshold - sel) ? b : a))
  return (
    <div className="card explorer">
      <div className="explorer-title"><h3>Move the threshold</h3><span className="badge purple">{data.dataset.held_out_test_rows.toLocaleString('en')} held-out applications</span></div>
      <p className="muted small" style={{ margin: 0 }}>Real results from the exported analysis. A lower threshold catches more difficult cases but raises false alarms.</p>
      <div className="metric-trio">
        <div className="metric-box"><div className="v" style={{ color: 'var(--purple)' }}>{pct(row.precision)}</div><div className="l">Precision</div></div>
        <div className="metric-box"><div className="v" style={{ color: 'var(--green)' }}>{pct(row.recall)}</div><div className="l">Recall</div></div>
        <div className="metric-box"><div className="v" style={{ color: '#c27a05' }}>{pct(row.f1)}</div><div className="l">F1-score</div></div>
      </div>
      <input className="range" type="range" min={0.1} max={0.9} step={0.01} value={row.threshold} aria-label="Classification threshold"
             onChange={(e) => setT(Number(e.target.value))} />
      <div className="row spread small">
        <span>Threshold <strong className="num">{row.threshold.toFixed(2)}</strong></span>
        {Math.abs(row.threshold - saved) < 0.005 ? <span className="badge green">Saved model threshold</span> : <button className="btn btn-ghost btn-sm" onClick={() => setT(saved)}>Back to saved {saved}</button>}
      </div>
    </div>
  )
}

const caps = [
  [Sparkles, 'Works with partial details', 'Enter the few facts you have. The saved pipeline fills the rest with typical training values and tells you how much was missing.', ''],
  [Brain, 'Applicant-level explanations', 'Exact SHAP values show which of your inputs pushed the score up or down, and which came from assumed values.', 'purple'],
  [ChartColumn, 'Real evaluation, no mock data', 'Six models were compared, three were tuned, and every chart on this site reads the exported results.', 'green'],
  [SlidersHorizontal, 'Threshold you can inspect', 'The model flags difficulty at a saved 15% score, chosen for F1. See the precision and recall trade-off at every cut-off.', 'orange'],
]

export default function Home() {
  const { data } = useAsync(() => api.analytics(), [])
  const f = data?.final_metrics
  return (
    <>
      <section className="hero">
        <div className="container hero-grid">
          <div>
            <h1>See how a credit-risk model reads an application, with only the details you have.</h1>
            <p className="hero-lead">CreditWise AI estimates the chance of recorded loan payment difficulty using a gradient-boosting model trained on the Home Credit dataset, then shows what drove the result.</p>
            <div className="hero-actions">
              <Link to="/predict" className="btn btn-primary btn-lg">Predict credit risk <ArrowRight size={18} /></Link>
              <Link to="/analytics" className="btn btn-secondary btn-lg">View model analytics</Link>
            </div>
            <p className="hero-note"><Lock size={16} aria-hidden />Details are used for one prediction and never stored. The result is a model score, not a CIBIL score or a lending decision.</p>
          </div>
          <ThresholdExplorer />
        </div>
      </section>

      <section className="section-tight">
        <div className="container grid g4">
          {caps.map(([Icon, title, text, tone]) => (
            <div className="card" key={title}><div className={`icon-chip ${tone}`}><Icon size={22} /></div><h3>{title}</h3><p className="muted small" style={{ margin: 0 }}>{text}</p></div>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="section-head"><h2>How a prediction is made</h2><p>The same saved model and preprocessing from the original training notebook run on every request. Nothing is retrained.</p></div>
          <div className="steps">
            {[['You enter what you know', 'Six key details, plus any of the 125 model inputs through search.'],
              ['Missing details are handled', 'Blank numbers get the training median, blank categories the most common value.'],
              ['The model scores it', 'Gradient boosting returns a score; class 1 is predicted at or above 15%.'],
              ['SHAP explains it', 'Contributions are grouped by your original inputs and flagged as entered or assumed.']].map(([t, d], i) => (
              <div className="step" key={t}><div className="dot">{i + 1}</div><h4>{t}</h4><p className="muted small">{d}</p></div>
            ))}
          </div>
        </div>
      </section>

      <section className="section" style={{ paddingTop: 0 }}>
        <div className="container grid g2">
          <div className="card card-lg">
            <div className="icon-chip green"><Scale size={22} /></div>
            <h3>Model highlights</h3>
            {f ? (
              <>
                <div className="stat-line"><span className="k">Selected model</span><span className="v">{f.model}</span></div>
                <div className="stat-line"><span className="k">ROC-AUC</span><span className="v">{fix(f.roc_auc)}</span></div>
                <div className="stat-line"><span className="k">PR-AUC</span><span className="v">{fix(f.pr_auc)}</span></div>
                <div className="stat-line"><span className="k">Recall at saved threshold</span><span className="v">{pct(f.recall)}</span></div>
                <div className="stat-line"><span className="k">Precision at saved threshold</span><span className="v">{pct(f.precision)}</span></div>
              </>
            ) : <Skeleton h={150} />}
            <p className="tiny" style={{ marginTop: 12 }}>Precision around a quarter reflects how rare payment difficulty is in this dataset. This is a ranking aid, not a decision-maker.</p>
            <Link to="/analytics" className="btn btn-secondary btn-sm" style={{ marginTop: 8 }}>See the full analysis <ArrowRight size={15} /></Link>
          </div>
          <div className="card card-lg">
            <div className="icon-chip purple"><Database size={22} /></div>
            <h3>Dataset and technology</h3>
            <div className="stat-line"><span className="k">Dataset</span><span className="v">Home Credit Default Risk</span></div>
            <div className="stat-line"><span className="k">Model inputs</span><span className="v">125 (109 numeric, 16 categorical)</span></div>
            <div className="stat-line"><span className="k">After encoding</span><span className="v">247 columns</span></div>
            <div className="stat-line"><span className="k">Target</span><span className="v">1 = recorded payment difficulty</span></div>
            <div className="stat-line"><span className="k">Stack</span><span className="v">React · FastAPI · scikit-learn</span></div>
            <p className="tiny" style={{ marginTop: 12 }}><Layers size={13} style={{ verticalAlign: -2 }} /> Frontend and Python API deploy together as one Vercel project.</p>
          </div>
        </div>
      </section>
    </>
  )
}
