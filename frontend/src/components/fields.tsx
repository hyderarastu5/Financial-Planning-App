import { useState } from 'react'

type Unit = 'money' | 'percent' | 'plain'

function toDisplay(value: number | null, unit: Unit): string {
  if (value === null) return ''
  // Rates are stored as decimals and shown as percentages; round away float noise.
  return unit === 'percent' ? String(Math.round(value * 100 * 1e4) / 1e4) : String(value)
}

interface NumberFieldProps {
  label: string
  value: number | null
  onChange: (value: number | null) => void
  unit?: Unit
  optional?: boolean // empty input means null instead of 0
  placeholder?: string
  hint?: string
}

// Keeps the raw text while typing so partial input like "7." or "" is not clobbered.
export function NumberField({ label, value, onChange, unit = 'plain', optional, placeholder, hint }: NumberFieldProps) {
  // null while not editing: show the formatted value instead.
  const [text, setText] = useState<string | null>(null)

  function handle(raw: string) {
    setText(raw)
    const cleaned = raw.replace(/[$,%\s]/g, '')
    if (cleaned === '') return onChange(optional ? null : 0)
    const n = Number(cleaned)
    if (Number.isFinite(n)) onChange(unit === 'percent' ? n / 100 : n)
  }

  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <span className={`input-wrap unit-${unit}`}>
        <input
          inputMode="decimal"
          value={text ?? toDisplay(value, unit)}
          placeholder={placeholder}
          onFocus={() => setText(toDisplay(value, unit))}
          onBlur={() => setText(null)}
          onChange={(e) => handle(e.target.value)}
        />
      </span>
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  )
}

interface TextFieldProps {
  label: string
  value: string
  onChange: (value: string) => void
  type?: 'text' | 'date'
}

export function TextField({ label, value, onChange, type = 'text' }: TextFieldProps) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <span className="input-wrap">
        <input type={type} value={value} onChange={(e) => onChange(e.target.value)} />
      </span>
    </label>
  )
}
