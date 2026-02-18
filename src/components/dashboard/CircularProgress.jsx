import React from 'react'

/**
 * Círculo de progresso (donut) para exibir % de produtividade.
 * @param {number} percent - 0 a 100
 * @param {number} size - diâmetro em px
 * @param {string} color - cor do segmento (verde/vermelho conforme valor)
 */
export default function CircularProgress({ percent = 0, size = 48, strokeWidth = 4, className = '' }) {
  const pct = Math.min(100, Math.max(0, Number(percent)))
  const r = (size - strokeWidth) / 2
  const cx = size / 2
  const cy = size / 2
  const circumference = 2 * Math.PI * r
  const strokeDashoffset = circumference - (pct / 100) * circumference
  const color = pct >= 50 ? '#059669' : pct >= 25 ? '#b45309' : '#dc2626'

  const trackColor = 'var(--chart-track, #e2e8f0)'

  return (
    <div className={`relative inline-flex items-center justify-center ${className}`} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90" aria-hidden>
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={trackColor}
          strokeWidth={strokeWidth}
        />
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-500"
        />
      </svg>
      <span
        className="absolute font-semibold text-gray-800 dark:text-gray-100 tabular-nums"
        style={{ fontSize: Math.round(size * 0.24) }}
      >
        {Math.round(pct)}%
      </span>
    </div>
  )
}
