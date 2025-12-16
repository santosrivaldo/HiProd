import React, { useState, useEffect } from 'react'
import { 
  SparklesIcon, 
  LightBulbIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  InformationCircleIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline'

export default function AIInsights({ data, onAnalyze }) {
  const [insights, setInsights] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (data) {
      generateInsights(data)
    }
  }, [data])

  const generateInsights = async (dashboardData) => {
    setLoading(true)
    
    // Simular análise de IA (em produção, chamaria uma API real)
    setTimeout(() => {
      const newInsights = analyzeData(dashboardData)
      setInsights(newInsights)
      setLoading(false)
    }, 1000)
  }

  const analyzeData = (data) => {
    const insights = []
    
    if (!data || !data.summary) return insights

    const { summary, userStats = [] } = data
    const total = summary.total || 1
    const productivePercent = (summary.productive / total) * 100
    const nonproductivePercent = (summary.nonproductive / total) * 100
    const idlePercent = (summary.idle / total) * 100

    // Insight 1: Produtividade
    if (productivePercent < 40) {
      insights.push({
        type: 'warning',
        icon: ExclamationTriangleIcon,
        title: 'Produtividade Baixa',
        message: `Apenas ${productivePercent.toFixed(1)}% do tempo foi considerado produtivo. Considere revisar as categorizações ou focar em atividades mais relevantes.`,
        action: 'Revisar categorias',
        priority: 'high'
      })
    } else if (productivePercent > 70) {
      insights.push({
        type: 'success',
        icon: CheckCircleIcon,
        title: 'Excelente Produtividade',
        message: `${productivePercent.toFixed(1)}% do tempo foi produtivo. Continue mantendo esse foco!`,
        action: null,
        priority: 'low'
      })
    }

    // Insight 2: Ociosidade
    if (idlePercent > 20) {
      insights.push({
        type: 'warning',
        icon: ExclamationTriangleIcon,
        title: 'Alto Tempo Ocioso',
        message: `${idlePercent.toFixed(1)}% do tempo foi considerado ocioso (mais de 10 minutos sem atividade). Considere implementar pausas programadas.`,
        action: 'Configurar alertas',
        priority: 'medium'
      })
    }

    // Insight 3: Não produtivo
    if (nonproductivePercent > 30) {
      insights.push({
        type: 'info',
        icon: InformationCircleIcon,
        title: 'Atividades Não Produtivas',
        message: `${nonproductivePercent.toFixed(1)}% do tempo em atividades não produtivas. Revise se há distrações que podem ser reduzidas.`,
        action: 'Ver detalhes',
        priority: 'medium'
      })
    }

    // Insight 4: Usuários
    if (userStats.length > 0) {
      const topUser = userStats[0]
      const avgProductive = userStats.reduce((sum, u) => sum + (u.productive || 0), 0) / userStats.length
      
      if (topUser.productive > avgProductive * 1.5) {
        insights.push({
          type: 'success',
          icon: LightBulbIcon,
          title: 'Destaque de Performance',
          message: `${topUser.nome} está com ${((topUser.productive / (topUser.total || 1)) * 100).toFixed(1)}% de produtividade, acima da média.`,
          action: 'Ver perfil',
          priority: 'low'
        })
      }
    }

    // Insight 5: Presença Facial
    if (data.summary.facePresence > 0) {
      const presencePercent = (data.summary.facePresence / total) * 100
      if (presencePercent < 50) {
        insights.push({
          type: 'info',
          icon: InformationCircleIcon,
          title: 'Presença Facial',
          message: `Apenas ${presencePercent.toFixed(1)}% do tempo teve presença facial detectada. Verifique se a câmera está funcionando corretamente.`,
          action: 'Verificar câmera',
          priority: 'low'
        })
      }
    }

    // Insight 6: Horários
    if (data.hourlyData && data.hourlyData.length > 0) {
      const peakHour = data.hourlyData.reduce((max, h) => 
        (h.productive || 0) > (max.productive || 0) ? h : max
      )
      insights.push({
        type: 'info',
        icon: LightBulbIcon,
        title: 'Horário de Pico',
        message: `O horário mais produtivo é às ${peakHour.hour}:00. Considere agendar tarefas importantes neste período.`,
        action: null,
        priority: 'low'
      })
    }

    return insights.sort((a, b) => {
      const priorityOrder = { high: 3, medium: 2, low: 1 }
      return priorityOrder[b.priority] - priorityOrder[a.priority]
    })
  }

  const getTypeStyles = (type) => {
    switch (type) {
      case 'success':
        return 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-800 dark:text-green-200'
      case 'warning':
        return 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800 text-yellow-800 dark:text-yellow-200'
      case 'info':
        return 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-200'
      default:
        return 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-800 dark:text-gray-200'
    }
  }

  const getIconColor = (type) => {
    switch (type) {
      case 'success':
        return 'text-green-600 dark:text-green-400'
      case 'warning':
        return 'text-yellow-600 dark:text-yellow-400'
      case 'info':
        return 'text-blue-600 dark:text-blue-400'
      default:
        return 'text-gray-600 dark:text-gray-400'
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <SparklesIcon className="w-6 h-6 text-purple-600 dark:text-purple-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Insights de IA
          </h3>
        </div>
        <button
          onClick={() => onAnalyze && onAnalyze()}
          disabled={loading}
          className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 disabled:opacity-50"
          title="Atualizar insights"
        >
          <ArrowPathIcon className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-pulse text-gray-500 dark:text-gray-400">
            Analisando dados...
          </div>
        </div>
      ) : insights.length === 0 ? (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <InformationCircleIcon className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>Nenhum insight disponível no momento.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {insights.map((insight, index) => {
            const Icon = insight.icon
            return (
              <div
                key={index}
                className={`border rounded-lg p-4 ${getTypeStyles(insight.type)}`}
              >
                <div className="flex items-start space-x-3">
                  <Icon className={`w-5 h-5 flex-shrink-0 mt-0.5 ${getIconColor(insight.type)}`} />
                  <div className="flex-1 min-w-0">
                    <h4 className="font-semibold mb-1">{insight.title}</h4>
                    <p className="text-sm opacity-90">{insight.message}</p>
                    {insight.action && (
                      <button className="mt-2 text-sm font-medium underline hover:no-underline">
                        {insight.action} →
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

