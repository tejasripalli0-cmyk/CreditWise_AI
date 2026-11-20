// Copies ONLY the two public analytics images from model_assets/ into public/analytics/.
// The model pickle is deliberately never copied into anything served to browsers.
import { copyFileSync, mkdirSync, existsSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const src = resolve(here, '..', '..', 'model_assets')
const dest = resolve(here, '..', 'public', 'analytics')
const IMAGES = ['confusion_matrix.png', 'shap_summary.png']

mkdirSync(dest, { recursive: true })
for (const name of IMAGES) {
  const from = join(src, name)
  if (!existsSync(from)) throw new Error(`Missing ${name} in model_assets/`)
  copyFileSync(from, join(dest, name))
}
console.log(`synced ${IMAGES.length} analytics images -> public/analytics/`)
