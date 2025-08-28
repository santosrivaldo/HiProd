
import React from 'react'

const LoadingSpinner = ({ size = 'md', text = 'Carregando...', fullScreen = false }) => {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
    xl: 'h-16 w-16'
  }

  const textSizeClasses = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg',
    xl: 'text-xl'
  }

  if (fullScreen) {
    return (
      <div className="fixed inset-0 bg-white dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-75 flex items-center justify-center z-50">
        <div className="text-center">
          <div className={`animate-spin rounded-full border-b-2 border-indigo-500 ${sizeClasses[size]} mx-auto`}></div>
          {text && (
            <p className={`mt-4 text-gray-600 dark:text-gray-400 ${textSizeClasses[size]}`}>
              {text}
            </p>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center justify-center p-8">
      <div className={`animate-spin rounded-full border-b-2 border-indigo-500 ${sizeClasses[size]}`}></div>
      {text && (
        <p className={`mt-4 text-gray-600 dark:text-gray-400 ${textSizeClasses[size]}`}>
          {text}
        </p>
      )}
    </div>
  )
}

export default LoadingSpinner
