import React from 'react'
import { EyeIcon } from '@heroicons/react/24/outline'

export default function ProductivityByUserTable({
  userStats,
  formatTime,
  formatPercentage,
  onViewDetails
}) {
  if (!userStats?.length) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow border border-gray-200 dark:border-gray-700 p-6 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Produtividade por usuário</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">Nenhum dado no período.</p>
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow border border-gray-200 dark:border-gray-700 overflow-hidden mb-6">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white p-4 border-b border-gray-200 dark:border-gray-700">
        Produtividade por usuário
      </h3>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700/50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Usuário</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Departamento</th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Tempo produtivo</th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Não produtivo</th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Neutro</th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">% Produtividade</th>
              <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Detalhes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {userStats.map((u) => {
              const pct = u.total > 0 ? formatPercentage(u.productive, u.total) : '0%'
              return (
                <tr key={u.userId} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-sm font-medium text-gray-900 dark:text-white">{u.nome}</td>
                  <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300">{u.departamentoNome || '—'}</td>
                  <td className="px-4 py-2 text-sm text-right text-green-600 dark:text-green-400">{formatTime(u.productive)}</td>
                  <td className="px-4 py-2 text-sm text-right text-red-600 dark:text-red-400">{formatTime(u.nonproductive)}</td>
                  <td className="px-4 py-2 text-sm text-right text-amber-600 dark:text-amber-400">{formatTime(u.neutral)}</td>
                  <td className="px-4 py-2 text-sm text-right font-medium text-gray-900 dark:text-white">{pct}</td>
                  <td className="px-4 py-2 text-center">
                    <button
                      onClick={() => onViewDetails(u.userId)}
                      className="inline-flex items-center gap-1 text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 text-sm"
                    >
                      <EyeIcon className="w-4 h-4" />
                      Ver
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
