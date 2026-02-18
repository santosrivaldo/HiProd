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
  const color = pct >= 50 ? '#10B981' : pct >= 25 ? '#F59E0B' : '#EF4444'

  return (
    <div className={`relative inline-flex items-center justify-center ${className}`} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#E5E7EB"
          strokeWidth={strokeWidth}
          className="dark:stroke-gray-600"
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
        className="absolute text-xs font-semibold text-gray-700 dark:text-gray-200"
        style={{ fontSize: size * 0.22 }}
      >
        {Math.round(pct)}%
      </span>
    </div>
  )
}
