import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../services/api'
import { SignalIcon } from '@heroicons/react/24/outline'
import LiveScreensDvr from '../components/LiveScreensDvr'

/**
 * Página DVR: telas ao vivo do usuário monitorado.
 * Usa LiveScreensDvr com telas lado a lado. Pode ser aberta pelo menu ou em guia standalone.
 */
export default function DvrPage() {
  const [searchParams] = useSearchParams()
  const userIdFromUrl = searchParams.get('userId')

  const [users, setUsers] = useState([])
  const [selectedUserId, setSelectedUserId] = useState(userIdFromUrl || '')

  useEffect(() => {
    api.get('/usuarios-monitorados').then((res) => {
      const list = res.data || []
      setUsers(list)
      if (!selectedUserId && list.length > 0) setSelectedUserId(String(list[0].id))
    }).catch(() => setUsers([]))
  }, [])

  useEffect(() => {
    if (userIdFromUrl) setSelectedUserId(userIdFromUrl)
  }, [userIdFromUrl])

  return (
    <div className="min-h-screen bg-gray-900 text-gray-200 flex flex-col">
      <header className="flex-shrink-0 px-4 py-2 bg-gray-800 border-b border-gray-700 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <SignalIcon className="w-5 h-5 text-emerald-400" />
          <span className="text-sm font-medium text-emerald-400">DVR — Ao vivo</span>
        </div>
        <select
          value={selectedUserId}
          onChange={(e) => setSelectedUserId(e.target.value)}
          className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-sm text-white focus:ring-indigo-500 focus:border-indigo-500"
        >
          <option value="">Selecione o usuário</option>
          {users.map((u) => (
            <option key={u.id} value={u.id}>{u.nome || `Usuário ${u.id}`}</option>
          ))}
        </select>
      </header>

      <main className="flex-1 min-h-0 flex flex-col">
        <LiveScreensDvr userId={selectedUserId} layout="row" showHeader={true} className="flex-1" />
      </main>
    </div>
  )
}
