import { shown } from '../services/format.js'

export function validateField(f, raw) {
  if (raw === '' || raw == null) return null
  if (f.kind === 'category' || f.kind === 'flag') return null
  const n = Number(raw)
  if (!Number.isFinite(n)) return 'Enter a valid number.'
  if (f.kind === 'integer' && !Number.isInteger(n)) return 'Enter a whole number.'
  if (f.min != null && n < f.min) return `Must be at least ${f.min}.`
  if (f.max != null && n > f.max) return `Must be at most ${f.max.toLocaleString('en')}.`
  return null
}

const UNIT = { years: 'years', days: 'days', hour: 'hour', ratio: 'ratio' }

export default function FieldControl({ f, value, onChange, error, id, autoValue }) {
  const hasValue = value !== '' && value != null
  let control
  if (f.kind === 'category') {
    control = (
      <select id={id} className={`select ${error ? 'invalid' : ''}`} value={value ?? ''} onChange={(e) => onChange(e.target.value)}>
        <option value="">Not provided</option>
        {f.choices.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
      </select>
    )
  } else if (f.kind === 'flag') {
    control = (
      <div className="seg" role="group" aria-label={f.label}>
        {f.choices.map((c) => (
          <button type="button" key={c.value} className={value === c.value ? 'on' : ''} aria-pressed={value === c.value}
                  onClick={() => onChange(value === c.value ? '' : c.value)}>{c.label}</button>
        ))}
      </div>
    )
  } else {
    control = (
      <div className="input-affix">
        <input id={id} className={`input ${error ? 'invalid' : ''}`} type="number" inputMode="decimal" value={value ?? ''} min={f.min ?? undefined} max={f.max ?? undefined}
               step={f.step ?? 'any'} placeholder={autoValue != null ? `Auto: ${shown(autoValue)}` : `Typical ${f.typical.label}`}
               onChange={(e) => onChange(e.target.value)} />
        {UNIT[f.unit] && <span className="affix">{UNIT[f.unit]}</span>}
      </div>
    )
  }
  return (
    <div className="field">
      <label htmlFor={id}>{f.label}{f.derived && !hasValue && autoValue != null && <span className="auto-tag">calculated</span>}</label>
      {control}
      {error ? <span className="error-text" role="alert">{error}</span> : <span className="hint">{f.description}</span>}
    </div>
  )
}
