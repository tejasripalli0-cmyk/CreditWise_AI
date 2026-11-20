import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, RotateCcw, ShieldCheck, Wand2 } from 'lucide-react'
import { api } from '../services/api.js'
import { useAsync } from '../services/hooks.js'
import { usePrediction } from '../services/PredictionContext.jsx'
import { pct, shown } from '../services/format.js'
import FieldControl, { validateField } from '../components/FieldControl.jsx'
import VariablePicker from '../components/VariablePicker.jsx'
import { Alert, ErrorState, Meter, Skeleton, Spinner } from '../components/ui.jsx'

const num = (v) => (v === '' || v == null ? null : Number.isFinite(Number(v)) ? Number(v) : null)

// Mirrors the server's derivation rules for PREVIEW only; the API is the source of truth and reports what it calculated.
function previewDerived(values, fm) {
  const ok = (k) => (fm[k] && !validateField(fm[k], values[k]) ? num(values[k]) : null)
  const out = {}
  const age = ok('AGE_YEARS'), db = ok('DAYS_BIRTH'), emp = ok('EMPLOYMENT_YEARS'), de = ok('DAYS_EMPLOYED')
  if (age != null && db == null) out.DAYS_BIRTH = Math.round(age * 365.25)
  if (db != null && age == null) out.AGE_YEARS = +(db / 365.25).toFixed(1)
  if (emp != null && de == null) out.DAYS_EMPLOYED = Math.round(emp * 365.25)
  if (de != null && emp == null) out.EMPLOYMENT_YEARS = +(de / 365.25).toFixed(1)
  const inc = ok('AMT_INCOME_TOTAL'), cr = ok('AMT_CREDIT'), an = ok('AMT_ANNUITY'), gp = ok('AMT_GOODS_PRICE')
  const free = (k) => ok(k) == null
  if (inc && cr != null && free('CREDIT_INCOME_RATIO')) out.CREDIT_INCOME_RATIO = +(cr / inc).toFixed(3)
  if (inc && an != null && free('ANNUITY_INCOME_RATIO')) out.ANNUITY_INCOME_RATIO = +(an / inc).toFixed(3)
  if (cr && gp != null && free('GOODS_CREDIT_RATIO')) out.GOODS_CREDIT_RATIO = +(gp / cr).toFixed(3)
  return out
}

export default function Predict() {
  const nav = useNavigate()
  const { data, error, loading, reload } = useAsync(() => api.features(), [])
  const { values, setValues, optional, setOptional, setResult } = usePrediction()
  const [serverErrors, setServerErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [failure, setFailure] = useState(null)

  const fm = useMemo(() => Object.fromEntries((data?.features || []).map((f) => [f.name, f])), [data])
  const featured = useMemo(() => (data?.features || []).filter((f) => f.featured), [data])
  const setValue = (name, v) => { setValues((s) => ({ ...s, [name]: v })); setServerErrors((e) => ({ ...e, [name]: undefined })) }

  const clientErrors = useMemo(() => Object.fromEntries(Object.keys(values).map((k) => [k, fm[k] ? validateField(fm[k], values[k]) : null]).filter(([, e]) => e)), [values, fm])
  const errors = { ...serverErrors, ...clientErrors }
  const entered = Object.keys(values).filter((k) => values[k] !== '' && values[k] != null && !clientErrors[k])
  const derived = useMemo(() => (data ? previewDerived(values, fm) : {}), [values, fm, data])
  const provided = new Set([...entered, ...Object.keys(derived)])
  const coverage = (data?.features || []).reduce((s, f) => s + (provided.has(f.name) ? f.importance_share : 0), 0)
  const level = coverage >= 0.6 ? 'good' : coverage >= 0.3 ? 'moderate' : 'limited'
  const levelText = { good: 'Good coverage', moderate: 'Moderate coverage', limited: 'Limited coverage' }[level]
  const hasErrors = Object.keys(clientErrors).length > 0
  const suggested = (data?.suggested || []).filter((n) => !optional.includes(n)).slice(0, 5)

  const clearAll = () => { setValues({}); setOptional([]); setServerErrors({}); setFailure(null) }

  const submit = async (e) => {
    e.preventDefault()
    if (!entered.length || hasErrors) return
    setSubmitting(true); setFailure(null); setServerErrors({})
    const inputs = {}
    for (const k of entered) {
      const f = fm[k]
      inputs[k] = f.kind === 'category' ? values[k] : Number(values[k])
    }
    try {
      const result = await api.predict(inputs)
      setResult({ ...result, submitted: inputs, labels: Object.fromEntries(Object.keys(inputs).map((k) => [k, fm[k].label])) })
      nav('/results')
    } catch (err) {
      if (err.errors?.length) setServerErrors(Object.fromEntries(err.errors.map((x) => [x.field, x.message])))
      setFailure(err)
    } finally { setSubmitting(false) }
  }

  return (
    <div className="container">
      <div className="page-title">
        <h1 style={{ fontSize: 'clamp(2rem,4vw,2.8rem)' }}>Predict credit risk</h1>
        <p>Enter whatever you know. You do not need all {data?.n_features ?? 125} details: anything left blank is filled by the model&apos;s saved preprocessing with typical training values.</p>
      </div>

      {error && <ErrorState error={error} onRetry={reload} />}
      {loading && <div className="grid g2"><Skeleton h={220} /><Skeleton h={220} /></div>}

      {data && (
        <form className="form-layout" onSubmit={submit} noValidate>
          <div className="stack" style={{ gap: 24 }}>
            <section className="card card-lg" aria-labelledby="key">
              <h3 id="key">Key applicant details</h3>
              <p className="muted small">Amounts use one consistent currency unit. Credit-to-income and similar ratios are calculated for you when the inputs are present.</p>
              <div className="grid g2" style={{ marginTop: 16 }}>
                {featured.map((f) => <FieldControl key={f.name} f={f} id={`f-${f.name}`} value={values[f.name] ?? ''} onChange={(v) => setValue(f.name, v)} error={errors[f.name]} />)}
              </div>
              {Object.keys(derived).length > 0 && (
                <div className="alert info" style={{ marginTop: 20 }}>
                  <Wand2 size={18} aria-hidden />
                  <div>
                    <strong>Calculated automatically:</strong>{' '}
                    {Object.entries(derived).map(([k, v]) => `${fm[k].label} ${shown(v)}`).join(' · ')}
                    <div className="tiny" style={{ marginTop: 4 }}>Add one of these yourself under &ldquo;More details&rdquo; to override the calculation.</div>
                  </div>
                </div>
              )}
            </section>

            <section className="card card-lg" aria-labelledby="more">
              <h3 id="more">More details (optional)</h3>
              <p className="muted small">The model uses {data.n_features} inputs in total. Search for any of them, or browse by category, and add as many as you like.</p>
              <VariablePicker features={data.features.filter((f) => !f.featured)} groups={data.groups} optional={optional} setOptional={setOptional}
                              values={values} setValue={setValue} errors={errors} suggested={suggested} />
            </section>
          </div>

          <aside className="sticky-panel stack">
            <div className="card">
              <div className="row spread"><h4 style={{ margin: 0 }}>Information coverage</h4><span className={`badge ${level === 'good' ? 'green' : level === 'moderate' ? 'orange' : 'coral'}`}>{levelText}</span></div>
              <p className="num" style={{ fontSize: '2.2rem', fontWeight: 700, margin: '10px 0 8px' }}>{pct(coverage, 0)}</p>
              <Meter value={coverage} level={level} />
              <div className="stat-line" style={{ marginTop: 12 }}><span className="k">Entered by you</span><span className="v">{entered.length}</span></div>
              <div className="stat-line"><span className="k">Calculated for you</span><span className="v">{Object.keys(derived).length}</span></div>
              <div className="stat-line"><span className="k">Filled with typical values</span><span className="v">{data.n_features - provided.size} of {data.n_features}</span></div>
              <p className="tiny" style={{ marginTop: 12 }}>Coverage is the share of the model&apos;s overall importance (exported SHAP analysis) carried by the details you provided. Fewer details can mean a less reliable result.</p>
            </div>

            {failure && !Object.keys(serverErrors).length && <ErrorState error={failure} onRetry={() => submit({ preventDefault() {} })} />}
            {Object.keys(serverErrors).length > 0 && <Alert kind="error">{failure?.message} Check the highlighted fields.</Alert>}
            {hasErrors && <Alert kind="warning">Fix the highlighted fields to continue.</Alert>}

            <button className="btn btn-primary btn-lg" type="submit" disabled={!entered.length || hasErrors || submitting}>
              {submitting ? <><Spinner /> Predicting…</> : <>Predict credit risk <ArrowRight size={18} /></>}
            </button>
            {submitting && <p className="tiny">The first request after a quiet period can take a few extra seconds while the model starts.</p>}
            {!entered.length && <p className="tiny">Enter at least one detail to continue.</p>}
            <button className="btn btn-secondary" type="button" onClick={clearAll}><RotateCcw size={16} />Clear all</button>
            <p className="tiny" style={{ display: 'flex', gap: 8 }}><ShieldCheck size={16} style={{ flex: 'none' }} />Details are sent for this one prediction only. Nothing is stored or logged.</p>
          </aside>
        </form>
      )}
    </div>
  )
}
