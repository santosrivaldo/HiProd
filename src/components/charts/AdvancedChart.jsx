import React from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis
} from 'recharts'

const CHART_COLORS = [
  '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', 
  '#06B6D4', '#F97316', '#84CC16', '#EC4899', '#6B7280',
  '#14B8A6', '#A855F7', '#F43F5E', '#6366F1'
]

export default function AdvancedChart({ 
  type = 'line',
  data = [],
  dataKey,
  xKey,
  yKeys = [],
  colors = CHART_COLORS,
  height = 300,
  showLegend = true,
  showGrid = true,
  stacked = false,
  area = false,
  noWrapper = false,
  title,
  subtitle,
  formatTooltip,
  formatXAxis,
  formatYAxis,
  customTooltip
}) {
  const renderChart = () => {
    const commonProps = {
      data,
      margin: { top: 5, right: 30, left: 20, bottom: 5 }
    }

    const tooltipProps = customTooltip ? { content: customTooltip } : {
      contentStyle: {
        backgroundColor: 'rgba(31, 41, 55, 0.95)',
        border: '1px solid rgba(75, 85, 99, 0.5)',
        borderRadius: '8px',
        padding: '12px'
      },
      formatter: formatTooltip
    }

    switch (type) {
      case 'line':
        return (
          <LineChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />}
            <XAxis 
              dataKey={xKey} 
              stroke="#6B7280"
              tick={{ fill: '#6B7280', fontSize: 12 }}
              tickFormatter={formatXAxis}
            />
            <YAxis 
              stroke="#6B7280"
              tick={{ fill: '#6B7280', fontSize: 12 }}
              tickFormatter={formatYAxis}
            />
            <Tooltip {...tooltipProps} />
            {showLegend && <Legend />}
            {yKeys.map((key, index) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[index % colors.length]}
                strokeWidth={2}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
              />
            ))}
          </LineChart>
        )

      case 'area':
        return (
          <AreaChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />}
            <XAxis 
              dataKey={xKey} 
              stroke="#6B7280"
              tick={{ fill: '#6B7280', fontSize: 12 }}
              tickFormatter={formatXAxis}
            />
            <YAxis 
              stroke="#6B7280"
              tick={{ fill: '#6B7280', fontSize: 12 }}
              tickFormatter={formatYAxis}
            />
            <Tooltip {...tooltipProps} />
            {showLegend && <Legend />}
            {yKeys.map((key, index) => (
              <Area
                key={key}
                type="monotone"
                dataKey={key}
                stackId={stacked ? '1' : undefined}
                stroke={colors[index % colors.length]}
                fill={colors[index % colors.length]}
                fillOpacity={0.6}
              />
            ))}
          </AreaChart>
        )

      case 'bar':
        return (
          <BarChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />}
            <XAxis 
              dataKey={xKey} 
              stroke="#6B7280"
              tick={{ fill: '#6B7280', fontSize: 12 }}
              tickFormatter={formatXAxis}
            />
            <YAxis 
              stroke="#6B7280"
              tick={{ fill: '#6B7280', fontSize: 12 }}
              tickFormatter={formatYAxis}
            />
            <Tooltip {...tooltipProps} />
            {showLegend && <Legend />}
            {yKeys.map((key, index) => (
              <Bar
                key={key}
                dataKey={key}
                stackId={stacked ? '1' : undefined}
                fill={colors[index % colors.length]}
                radius={[4, 4, 0, 0]}
              />
            ))}
          </BarChart>
        )

      case 'pie': {
        const outerRadius = Math.min(88, Math.max(60, (height || 200) / 2 - 36))
        return (
          <PieChart>
            <Pie
              data={data}
              dataKey={dataKey || yKeys[0]}
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={outerRadius}
              innerRadius={outerRadius * 0.55}
              paddingAngle={1}
              fill="#8884d8"
              labelLine={false}
              label={false}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={colors[index % colors.length]} stroke="rgba(255,255,255,0.8)" strokeWidth={1.5} />
              ))}
            </Pie>
            <Tooltip {...tooltipProps} formatter={(value, name) => [value, name]} />
            {showLegend && (
              <Legend
                layout="horizontal"
                align="center"
                verticalAlign="bottom"
                iconType="circle"
                iconSize={8}
                wrapperStyle={{ paddingTop: 8 }}
                formatter={(value) => <span className="text-gray-700 dark:text-gray-300 text-sm">{value}</span>}
              />
            )}
          </PieChart>
        )
      }

      case 'radar':
        return (
          <RadarChart data={data}>
            <PolarGrid />
            <PolarAngleAxis dataKey={xKey} />
            <PolarRadiusAxis />
            <Tooltip {...tooltipProps} />
            {yKeys.map((key, index) => (
              <Radar
                key={key}
                name={key}
                dataKey={key}
                stroke={colors[index % colors.length]}
                fill={colors[index % colors.length]}
                fillOpacity={0.6}
              />
            ))}
            {showLegend && <Legend />}
          </RadarChart>
        )

      default:
        return null
    }
  }

  const content = (
    <>
      {(title || subtitle) && (
        <div className="mb-4">
          {title && (
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
              {title}
            </h3>
          )}
          {subtitle && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {subtitle}
            </p>
          )}
        </div>
      )}
      <ResponsiveContainer width="100%" height={height}>
        {renderChart()}
      </ResponsiveContainer>
    </>
  )

  if (noWrapper) return <div className="w-full">{content}</div>

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
      {content}
    </div>
  )
}

