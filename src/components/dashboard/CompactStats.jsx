import React from 'react'
import { format } from 'date-fns'
import { 
  GlobeAltIcon,
  ComputerDesktopIcon,
  UserIcon,
  ClockIcon
} from '@heroicons/react/24/outline'

export default function CompactStats({ 
  domainData = [], 
  applicationData = [], 
  userStats = [],
  formatTime 
}) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Top Domínios */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center space-x-2 mb-3">
          <GlobeAltIcon className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Top Domínios</h3>
        </div>
        <div className="space-y-2">
          {domainData.slice(0, 5).map((domain, index) => (
            <div key={index} className="flex items-center justify-between text-xs">
              <span className="text-gray-700 dark:text-gray-300 truncate flex-1">{domain.name}</span>
              <span className="text-gray-900 dark:text-white font-medium ml-2">{formatTime(domain.value)}</span>
            </div>
          ))}
          {domainData.length === 0 && (
            <p className="text-xs text-gray-500 dark:text-gray-400">Nenhum domínio</p>
          )}
        </div>
      </div>

      {/* Top Aplicações */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center space-x-2 mb-3">
          <ComputerDesktopIcon className="w-5 h-5 text-purple-600 dark:text-purple-400" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Top Aplicações</h3>
        </div>
        <div className="space-y-2">
          {applicationData.slice(0, 5).map((app, index) => (
            <div key={index} className="flex items-center justify-between text-xs">
              <span className="text-gray-700 dark:text-gray-300 truncate flex-1">{app.name}</span>
              <span className="text-gray-900 dark:text-white font-medium ml-2">{formatTime(app.value)}</span>
            </div>
          ))}
          {applicationData.length === 0 && (
            <p className="text-xs text-gray-500 dark:text-gray-400">Nenhuma aplicação</p>
          )}
        </div>
      </div>

      {/* Top Usuários */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center space-x-2 mb-3">
          <UserIcon className="w-5 h-5 text-green-600 dark:text-green-400" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Top Usuários</h3>
        </div>
        <div className="space-y-2">
          {userStats.slice(0, 5).map((user, index) => (
            <div key={index} className="flex items-center justify-between text-xs">
              <span className="text-gray-700 dark:text-gray-300 truncate flex-1">{user.nome}</span>
              <span className="text-gray-900 dark:text-white font-medium ml-2">{formatTime(user.productive || 0)}</span>
            </div>
          ))}
          {userStats.length === 0 && (
            <p className="text-xs text-gray-500 dark:text-gray-400">Nenhum usuário</p>
          )}
        </div>
      </div>
    </div>
  )
}

