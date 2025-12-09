import React, { useState } from 'react'
import { 
  FunnelIcon,
  XMarkIcon,
  CalendarIcon,
  UserIcon,
  BuildingOfficeIcon,
  ClockIcon
} from '@heroicons/react/24/outline'
import { format, subDays, startOfDay, endOfDay } from 'date-fns'

export default function AdvancedFilters({
  dateRange,
  onDateRangeChange,
  selectedUser,
  onUserChange,
  selectedDepartment,
  onDepartmentChange,
  users = [],
  departments = [],
  onReset,
  showQuickFilters = true
}) {
  const [isExpanded, setIsExpanded] = useState(false)

  const quickFilters = [
    { label: 'Hoje', days: 1 },
    { label: '7 dias', days: 7 },
    { label: '30 dias', days: 30 },
    { label: '90 dias', days: 90 }
  ]

  const activeFiltersCount = [
    dateRange !== 7,
    selectedUser !== 'all',
    selectedDepartment !== 'all'
  ].filter(Boolean).length

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-4 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <FunnelIcon className="w-5 h-5 text-gray-500 dark:text-gray-400" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            Filtros
          </h3>
          {activeFiltersCount > 0 && (
            <span className="px-2 py-0.5 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-xs font-medium rounded-full">
              {activeFiltersCount} ativo{activeFiltersCount > 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          {activeFiltersCount > 0 && (
            <button
              onClick={onReset}
              className="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            >
              Limpar tudo
            </button>
          )}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300"
          >
            {isExpanded ? 'Recolher' : 'Expandir'}
          </button>
        </div>
      </div>

      {/* Quick Filters */}
      {showQuickFilters && (
        <div className="mb-4">
          <div className="flex items-center space-x-2 mb-2">
            <CalendarIcon className="w-4 h-4 text-gray-400" />
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Período rápido:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {quickFilters.map(filter => (
              <button
                key={filter.days}
                onClick={() => onDateRangeChange(filter.days)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                  dateRange === filter.days
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                {filter.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Expanded Filters */}
      {isExpanded && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          {/* Date Range */}
          <div>
            <label className="flex items-center space-x-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <CalendarIcon className="w-4 h-4" />
              <span>Período</span>
            </label>
            <select
              value={dateRange}
              onChange={(e) => onDateRangeChange(parseInt(e.target.value))}
              className="w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value={1}>Hoje</option>
              <option value={7}>Últimos 7 dias</option>
              <option value={30}>Últimos 30 dias</option>
              <option value={90}>Últimos 90 dias</option>
              <option value={365}>Último ano</option>
            </select>
          </div>

          {/* User Filter */}
          <div>
            <label className="flex items-center space-x-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <UserIcon className="w-4 h-4" />
              <span>Usuário</span>
            </label>
            <select
              value={selectedUser}
              onChange={(e) => onUserChange(e.target.value)}
              className="w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="all">Todos os usuários</option>
              {users.map(user => (
                <option key={user.id} value={user.id}>{user.nome}</option>
              ))}
            </select>
          </div>

          {/* Department Filter */}
          <div>
            <label className="flex items-center space-x-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <BuildingOfficeIcon className="w-4 h-4" />
              <span>Departamento</span>
            </label>
            <select
              value={selectedDepartment}
              onChange={(e) => onDepartmentChange(e.target.value)}
              className="w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="all">Todos os departamentos</option>
              {departments.map(dept => (
                <option key={dept.id} value={dept.id}>{dept.nome}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Active Filters Tags */}
      {activeFiltersCount > 0 && !isExpanded && (
        <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
          {dateRange !== 7 && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 dark:bg-indigo-900/30 text-indigo-800 dark:text-indigo-200">
              {dateRange === 1 ? 'Hoje' : `Últimos ${dateRange} dias`}
            </span>
          )}
          {selectedUser !== 'all' && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 dark:bg-indigo-900/30 text-indigo-800 dark:text-indigo-200">
              {users.find(u => u.id.toString() === selectedUser)?.nome || 'Usuário'}
            </span>
          )}
          {selectedDepartment !== 'all' && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 dark:bg-indigo-900/30 text-indigo-800 dark:text-indigo-200">
              {departments.find(d => d.id.toString() === selectedDepartment)?.nome || 'Departamento'}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

