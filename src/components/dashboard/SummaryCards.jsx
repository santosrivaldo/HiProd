import React from 'react'
import { UserGroupIcon, ClockIcon, ChartBarIcon } from '@heroicons/react/24/outline'

export default function SummaryCards({ summary, userCount, formatTime, formatPercentage }) {
  const total = summary?.total || 1
  const avgProductivity = total > 0
    ? ((summary?.productive || 0) / total * 100).toFixed(0)
    : 0

  const cards = [
    { label: 'Usuários monitorados', value: userCount, icon: UserGroupIcon },
    { label: 'Tempo produtivo total', value: formatTime(summary?.productive || 0), icon: ClockIcon, color: 'text-green-600 dark:text-green-400' },
    { label: 'Tempo não produtivo', value: formatTime(summary?.nonproductive || 0), icon: ClockIcon, color: 'text-red-600 dark:text-red-400' },
    { label: 'Tempo neutro', value: formatTime(summary?.neutral || 0), icon: ClockIcon, color: 'text-amber-600 dark:text-amber-400' },
    { label: 'Produtividade média', value: `${avgProductivity}%`, icon: ChartBarIcon, color: 'text-indigo-600 dark:text-indigo-400' }
  ]

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow border border-gray-200 dark:border-gray-700 p-4 mb-6">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Resumo geral</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded-lg border border-gray-200 dark:border-gray-600 p-3 bg-gray-50 dark:bg-gray-700/50"
          >
            <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 text-xs mb-1">
              <card.icon className="w-4 h-4" />
              <span>{card.label}</span>
            </div>
            <p className={`text-lg font-semibold ${card.color || 'text-gray-900 dark:text-white'}`}>
              {card.value}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
