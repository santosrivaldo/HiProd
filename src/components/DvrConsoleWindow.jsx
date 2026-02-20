import React from 'react'
import { XMarkIcon, SignalIcon } from '@heroicons/react/24/outline'
import LiveScreensDvr from './LiveScreensDvr'

/**
 * Janela estilo console VNC para exibir o DVR (telas ao vivo) do usuário.
 * Telas lado a lado, barra de título com nome e botão fechar.
 */
export default function DvrConsoleWindow({ userId, userName, onClose }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70"
      onClick={(e) => e.target === e.currentTarget && onClose?.()}
      role="dialog"
      aria-modal="true"
      aria-label="Console DVR"
    >
      <div
        className="bg-gray-900 rounded-lg shadow-2xl border border-gray-600 flex flex-col w-full max-w-7xl overflow-hidden"
        style={{ height: '85vh', minHeight: 400 }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Barra de título estilo VNC/console */}
        <div className="flex-shrink-0 flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-600 rounded-t-lg">
          <div className="flex items-center gap-2">
            <SignalIcon className="w-5 h-5 text-emerald-400" />
            <span className="text-sm font-medium text-gray-200">
              DVR — {userName || `Usuário ${userId}`}
            </span>
            <span className="text-xs text-emerald-400/90 font-medium">Ao vivo</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded text-gray-400 hover:text-white hover:bg-gray-600 transition-colors"
            aria-label="Fechar"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>
        {/* Área das telas */}
        <div className="flex-1 min-h-0 flex flex-col">
          <LiveScreensDvr userId={userId} layout="row" showHeader={false} className="flex-1" />
        </div>
      </div>
    </div>
  )
}
