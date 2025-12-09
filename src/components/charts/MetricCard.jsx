import React from 'react'
import { 
  ArrowUpIcon, 
  ArrowDownIcon,
  MinusIcon 
} from '@heroicons/react/24/outline'

export default function MetricCard({ 
  title, 
  value, 
  subtitle, 
  icon: Icon, 
  trend, 
  trendValue,
  color = 'indigo',
  formatValue 
}) {
  const colorClasses = {
    indigo: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400',
    green: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
    red: 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400',
    yellow: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400',
    purple: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
    blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
  }

  const formattedValue = formatValue ? formatValue(value) : value

  return (
    <div className="bg-white dark:bg-gray-800 overflow-hidden shadow-lg rounded-xl border border-gray-200 dark:border-gray-700 hover:shadow-xl transition-shadow">
      <div className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
              {title}
            </p>
            <div className="flex items-baseline space-x-2">
              <p className="text-3xl font-bold text-gray-900 dark:text-white">
                {formattedValue}
              </p>
              {trend && trendValue && (
                <div className={`flex items-center text-xs font-medium ${
                  trend === 'up' ? 'text-green-600 dark:text-green-400' :
                  trend === 'down' ? 'text-red-600 dark:text-red-400' :
                  'text-gray-500 dark:text-gray-400'
                }`}>
                  {trend === 'up' && <ArrowUpIcon className="h-3 w-3 mr-1" />}
                  {trend === 'down' && <ArrowDownIcon className="h-3 w-3 mr-1" />}
                  {trend === 'neutral' && <MinusIcon className="h-3 w-3 mr-1" />}
                  {trendValue}
                </div>
              )}
            </div>
            {subtitle && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {subtitle}
              </p>
            )}
          </div>
          {Icon && (
            <div className={`w-12 h-12 ${colorClasses[color]} rounded-lg flex items-center justify-center flex-shrink-0`}>
              <Icon className="w-6 h-6" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

