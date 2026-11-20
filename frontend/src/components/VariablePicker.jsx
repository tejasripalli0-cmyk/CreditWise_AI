import { useMemo, useState } from 'react'
import { Plus, Search, Trash2 } from 'lucide-react'
import FieldControl, { validateField } from './FieldControl.jsx'

const score = (f, q) => {
  const label = f.label.toLowerCase(), name = f.name.toLowerCase().replace(/_/g, ' ')
  const hay = `${label} ${name} ${f.description.toLowerCase()} ${f.group.toLowerCase()} ${f.keywords.join(' ')}`
  let s = 0
  for (const t of q.split(/\s+/).filter(Boolean)) {
    if (!hay.includes(t)) return 0
    s += label.startsWith(t) ? 5 : label.includes(t) ? 3 : name.includes(t) ? 2 : 1
  }
  return s
}

export default function VariablePicker({ features, groups, optional, setOptional, values, setValue, errors, suggested }) {
  const [q, setQ] = useState('')
  const [cat, setCat] = useState('')
  const [picked, setPicked] = useState(null)
  const [draft, setDraft] = useState('')
  const byName = useMemo(() => Object.fromEntries(features.map((f) => [f.name, f])), [features])

  const matches = useMemo(() => {
    const term = q.trim().toLowerCase()
    if (!term && !cat) return []
    return features
      .filter((f) => !cat || f.group === cat)
      .map((f) => [f, term ? score(f, term) : 1])
      .filter(([, s]) => s > 0)
      .sort((a, b) => b[1] - a[1] || a[0].importance_rank - b[0].importance_rank)
      .map(([f]) => f)
  }, [q, cat, features])

  const choose = (f) => { setPicked(f); setDraft(''); }
  const draftError = picked ? validateField(picked, draft) : null
  const canAdd = picked && draft !== '' && !draftError
  const add = () => {
    if (!canAdd) return
    setValue(picked.name, draft)
    setOptional((o) => (o.includes(picked.name) ? o : [...o, picked.name]))
    setPicked(null); setDraft(''); setQ('')
  }
  const remove = (name) => { setOptional((o) => o.filter((n) => n !== name)); setValue(name, '') }
  const addedByGroup = groups.map((g) => [g, optional.filter((n) => byName[n].group === g)]).filter(([, l]) => l.length)

  return (
    <div className="stack">
      {suggested.length > 0 && (
        <div>
          <div className="small muted" style={{ marginBottom: 8 }}>Most influential fields you have not added yet:</div>
          <div className="pill-group">
            {suggested.map((n) => <button type="button" key={n} className="pill" onClick={() => { choose(byName[n]); setQ('') }}>{byName[n].label}</button>)}
          </div>
        </div>
      )}

      <div className="picker-search">
        <Search size={18} className="lead" aria-hidden />
        <input className="input" type="search" placeholder="Search a detail, e.g. education, score, car, children, occupation" value={q}
               onChange={(e) => setQ(e.target.value)} aria-label="Search additional details" />
      </div>
      <div className="pill-group" aria-label="Browse by category">
        {groups.map((g) => <button type="button" key={g} className={`pill ${cat === g ? 'on' : ''}`} onClick={() => setCat(cat === g ? '' : g)}>{g}</button>)}
      </div>

      {(q.trim() || cat) && (
        <div className="results-list" role="listbox" aria-label="Matching details">
          {matches.length === 0 && <div className="result-item" style={{ cursor: 'default' }}><span className="muted">No matching details. Try another word.</span></div>}
          {matches.slice(0, 60).map((f) => {
            const added = optional.includes(f.name) || f.featured
            return (
              <button type="button" key={f.name} className="result-item" disabled={added} onClick={() => choose(f)} role="option" aria-selected={picked?.name === f.name}>
                <span><span className="t">{f.label}</span><br /><span className="n">{f.name}</span></span>
                <span className="badge grey">{f.featured ? 'On the form above' : added ? 'Added' : f.group}</span>
              </button>
            )
          })}
        </div>
      )}

      {picked && (
        <div className="editor">
          <div className="row spread" style={{ marginBottom: 10 }}>
            <h4 style={{ margin: 0 }}>{picked.label}</h4>
            <span className="badge">{picked.group}</span>
          </div>
          <FieldControl f={picked} id="picker-draft" value={draft} onChange={setDraft} error={draftError} />
          <p className="tiny" style={{ margin: '10px 0 0' }}>If you leave this out, the model assumes a typical training value ({picked.typical.label}).</p>
          <div className="row" style={{ marginTop: 14 }}>
            <button type="button" className="btn btn-primary btn-sm" disabled={!canAdd} onClick={add}><Plus size={16} />Add to application</button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setPicked(null)}>Cancel</button>
          </div>
        </div>
      )}

      {optional.length > 0 && (
        <div>
          <div className="row spread" style={{ marginBottom: 4 }}>
            <h4 style={{ margin: 0 }}>Added details <span className="badge purple">{optional.length}</span></h4>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => optional.slice().forEach(remove)}><Trash2 size={15} />Clear added</button>
          </div>
          {addedByGroup.map(([g, names]) => (
            <div key={g} style={{ marginTop: 12 }}>
              <div className="tiny" style={{ fontWeight: 650 }}>{g}</div>
              {names.map((n) => (
                <div className="added-row" key={n}>
                  <FieldControl f={byName[n]} id={`opt-${n}`} value={values[n] ?? ''} onChange={(v) => setValue(n, v)} error={errors[n]} />
                  <button type="button" className="icon-btn" aria-label={`Remove ${byName[n].label}`} onClick={() => remove(n)}><Trash2 size={18} /></button>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
