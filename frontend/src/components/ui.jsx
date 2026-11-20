import { AlertTriangle, CircleCheck, Info } from 'lucide-react'

export const Spinner = ({ dark }) => <span className={`spinner ${dark ? 'dark' : ''}`} role="status" aria-label="Loading" />

export function Alert({ kind = 'info', children, action }) {
  const Icon = kind === 'warning' || kind === 'error' ? AlertTriangle : kind === 'success' ? CircleCheck : Info
  return (
    <div className={`alert ${kind}`} role={kind === 'error' ? 'alert' : 'note'}>
      <Icon size={18} aria-hidden />
      <div style={{ flex: 1 }}>{children}</div>
      {action}
    </div>
  )
}

export const Skeleton = ({ h = 20, w = '100%' }) => <div className="skeleton" style={{ height: h, width: w }} aria-hidden />

export function Meter({ value, level }) {
  return (
    <div className={`meter ${level || ''}`} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value * 100)}>
      <span style={{ width: `${Math.max(2, Math.min(100, value * 100))}%` }} />
    </div>
  )
}

export function ErrorState({ error, onRetry }) {
  return (
    <Alert kind="error" action={onRetry && <button className="btn btn-secondary btn-sm" onClick={onRetry}>Try again</button>}>
      {error?.message || 'Something went wrong.'}
    </Alert>
  )
}
