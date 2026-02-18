import React, { useState } from 'react'
import {
  FunnelIcon,
  ArrowPathIcon,
  CalendarDaysIcon,
  BuildingOfficeIcon,
  Squares2X2Icon,
  ComputerDesktopIcon,
  UserCircleIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline'
import { format, subDays } from 'date-fns'

const PERIOD_OPTIONS = [
  { label: 'Hoje', value: 1 },
  { label: '7 dias', value: 7 },
  { label: '30 dias', value: 30 },
  { label: 'Personalizado', value: 'custom' }
]

const STATUS_OPTIONS = [
  { label: 'Todos', value: 'all' },
  { label: 'Produtivo', value: 'productive' },
  { label: 'Neutro', value: 'neutral' },
  { label: 'Não produtivo', value: 'nonproductive' }
]

export default function GlobalFilters({
  periodDays,
  onPeriodChange,
  customStart,
  customEnd,
  onCustomStartChange,
  onCustomEndChange,
  selectedDepartment,
  onDepartmentChange,
  selectedGroup,
  onGroupChange,
  selectedApplication,
  onApplicationChange,
  selectedUser,
  onUserChange,
  statusFilter,
  onStatusChange,
  departments = [],
  users = [],
  applicationOptions = [],
  groupOptions = [],
  onRefresh,
  loading = false
}) {
  const [showCustom, setShowCustom] = useState(periodDays === 'custom')
  const isCustom = periodDays === 'custom'

  const handlePeriodSelect = (value) => {
    if (value === 'custom') {
      setShowCustom(true)
      onPeriodChange('custom')
    } else {
      setShowCustom(false)
      onPeriodChange(Number(value))
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow border border-gray-200 dark:border-gray-700 p-4 mb-6">
      <div className="flex items-center gap-2 mb-4">
        <FunnelIcon className="w-5 h-5 text-gray-500 dark:text-gray-400" />
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Filtros globais</h3>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {/* Período */}
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
            <CalendarDaysIcon className="w-4 h-4 inline mr-1" />
            Período
          </label>
          <select
            value={isCustom ? 'custom' : periodDays}
            onChange={(e) => handlePeriodSelect(e.target.value)}
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm py-2"
          >
            {PERIOD_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          {showCustom && (
            <div className="grid grid-cols-2 gap-2 mt-2">
              <input
                type="date"
                value={customStart}
                onChange={(e) => onCustomStartChange(e.target.value)}
                className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-xs py-1.5"
              />
              <input
                type="date"
                value={customEnd}
                onChange={(e) => onCustomEndChange(e.target.value)}
                className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-xs py-1.5"
              />
            </div>
          )}
        </div>

        {/* Departamento */}
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
            <BuildingOfficeIcon className="w-4 h-4 inline mr-1" />
            Departamento
          </label>
          <select
            value={selectedDepartment}
            onChange={(e) => onDepartmentChange(e.target.value)}
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm py-2"
          >
            <option value="all">Todos</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>{d.nome}</option>
            ))}
          </select>
        </div>

        {/* Grupo de páginas */}
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
            <Squares2X2Icon className="w-4 h-4 inline mr-1" />
            Grupo de páginas
          </label>
          <select
            value={selectedGroup}
            onChange={(e) => onGroupChange(e.target.value)}
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm py-2"
          >
            <option value="all">Todos</option>
            {groupOptions.map((g) => (
              <option key={g.value} value={g.value}>{g.label}</option>
            ))}
          </select>
        </div>

        {/* Aplicação */}
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
            <ComputerDesktopIcon className="w-4 h-4 inline mr-1" />
            Aplicação
          </label>
          <select
            value={selectedApplication}
            onChange={(e) => onApplicationChange(e.target.value)}
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm py-2"
          >
            <option value="all">Todas</option>
            {applicationOptions.map((app) => (
              <option key={app.name} value={app.name}>{app.name}</option>
            ))}
          </select>
        </div>

        {/* Usuário */}
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
            <UserCircleIcon className="w-4 h-4 inline mr-1" />
            Usuário
          </label>
          <select
            value={selectedUser}
            onChange={(e) => onUserChange(e.target.value)}
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm py-2"
          >
            <option value="all">Todos</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>{u.nome}</option>
            ))}
          </select>
        </div>

        {/* Status */}
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
            <ChartBarIcon className="w-4 h-4 inline mr-1" />
            Status
          </label>
          <select
            value={statusFilter}
            onChange={(e) => onStatusChange(e.target.value)}
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm py-2"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-4 flex justify-end">
        <button
          onClick={onRefresh}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ArrowPathIcon className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Atualizar
        </button>
      </div>
    </div>
  )
}
