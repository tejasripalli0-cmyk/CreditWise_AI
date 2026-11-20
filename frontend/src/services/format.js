export const pct = (x, d = 1) => (x == null ? '–' : `${(x * 100).toFixed(d)}%`)
export const fix = (x, d = 3) => (x == null ? '–' : Number(x).toFixed(d))
export const signed = (x, d = 2) => (x > 0 ? '+' : x < 0 ? '−' : '') + Math.abs(x).toFixed(d)
export const compact = (x) => Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(x)
export const grouped = (x) => Intl.NumberFormat('en').format(x)
export const shown = (v) => (typeof v === 'number' ? (Math.abs(v) >= 1000 ? grouped(Math.round(v)) : String(+v.toFixed(4))) : String(v))

export function download(filename, text, type = 'text/plain') {
  const url = URL.createObjectURL(new Blob([text], { type }))
  const a = Object.assign(document.createElement('a'), { href: url, download: filename })
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
