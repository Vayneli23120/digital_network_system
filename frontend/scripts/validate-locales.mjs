// 校验 locales 表：无重复键、无 zh/en 缺键。
// 用法：node scripts/validate-locales.mjs
// 违规时 exit 1（供 npm run validate:locales 与 CI 使用）。
import { readFileSync } from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const FILE = path.resolve(__dirname, '../src/locales/index.js')

const lines = readFileSync(FILE, 'utf8').split('\n')

// 定位 zh / en 块边界（扁平 key: 'value' 结构，块以 2 空格缩进的 }, 或 } 收尾）
let zhStart = -1
let enStart = -1
lines.forEach((l, i) => {
  if (/^\s*zh:\s*\{/.test(l)) zhStart = i
  if (/^\s*en:\s*\{/.test(l)) enStart = i
})
if (zhStart < 0 || enStart < 0) {
  console.error('FAIL: 找不到 zh/en 块')
  process.exit(1)
}
const blockEnd = (start) => {
  for (let i = start; i < lines.length; i++) {
    if (/^\s{2}\},?\s*$/.test(lines[i])) return i
  }
  return lines.length
}
const zhEnd = blockEnd(zhStart)
const enEnd = blockEnd(enStart)

// 解析单行 key: 'value'
const parse = (line) => {
  const m = /^(\s*)([A-Za-z0-9_]+):\s*'.*?'\s*,?\s*$/.exec(line)
  if (!m) return null
  const ci = line.indexOf(':')
  const fq = line.indexOf("'", ci)
  const lq = line.lastIndexOf("'")
  if (fq < 0 || lq <= fq) return null
  return { key: m[2], value: line.slice(fq + 1, lq) }
}

const collect = (start, end) => {
  const keys = new Set()
  const dups = []
  for (let i = start + 1; i < end; i++) {
    const p = parse(lines[i])
    if (!p) continue
    if (keys.has(p.key)) dups.push({ key: p.key, line: i + 1 })
    keys.add(p.key)
  }
  return { keys, dups }
}

const zh = collect(zhStart, zhEnd)
const en = collect(enStart, enEnd)

const errors = []
for (const d of [...zh.dups, ...en.dups]) {
  errors.push(`重复键 L${d.line}: ${d.key}`)
}
for (const k of [...zh.keys].filter(k => !en.keys.has(k)).sort()) {
  errors.push(`缺英文: ${k}`)
}
for (const k of [...en.keys].filter(k => !zh.keys.has(k)).sort()) {
  errors.push(`缺中文: ${k}`)
}

if (errors.length) {
  console.error(`FAIL: locales 校验发现 ${errors.length} 处问题`)
  errors.forEach(e => console.error('  ' + e))
  process.exit(1)
}

console.log(`OK: ${zh.keys.size} zh / ${en.keys.size} en 键，无重复、无缺键`)
