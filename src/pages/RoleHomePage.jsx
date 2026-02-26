import React from 'react'
import { useAuth } from '../contexts/AuthContext'
import Dashboard from '../components/Dashboard'
import { getPerfilLabel } from '../utils/permissions'

function SectionWrapper({ title, subtitle, children }) {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{title}</h1>
        {subtitle && (
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            {subtitle}
          </p>
        )}
      </div>
      {children}
    </div>
  )
}

function ColaboradorHome() {
  return (
    <SectionWrapper
      title="Painel do colaborador"
      subtitle="Visualize sua produtividade, atividades recentes e presença, apenas com os seus próprios dados."
    >
      <Dashboard />
    </SectionWrapper>
  )
}

function SupervisorHome() {
  return (
    <SectionWrapper
      title="Painel do supervisor"
      subtitle="Acompanhe as atividades do seu setor, usuários monitorados e produtividade consolidada da equipe."
    >
      <Dashboard />
    </SectionWrapper>
  )
}

function CoordenadorHome() {
  return (
    <SectionWrapper
      title="Painel do coordenador"
      subtitle="Visualize informações consolidadas de mais de um setor, com foco em comparativo entre equipes."
    >
      <Dashboard />
    </SectionWrapper>
  )
}

function HeadHome() {
  return (
    <SectionWrapper
      title="Painel do head"
      subtitle="Visão geral de todos os setores, com métricas resumidas da empresa e por departamento."
    >
      <Dashboard />
    </SectionWrapper>
  )
}

function AdminHome() {
  return (
    <SectionWrapper
      title="Painel do administrador"
      subtitle="Acesso completo a todas as informações, além de configurações de usuários, tokens, departamentos e tags."
    >
      <Dashboard />
    </SectionWrapper>
  )
}

export default function RoleHomePage() {
  const { user } = useAuth()
  const perfil = (user?.perfil || 'colaborador').toLowerCase()

  if (perfil === 'admin') return <AdminHome />
  if (perfil === 'head' || perfil === 'ceo' || perfil === 'gerente') return <HeadHome />
  if (perfil === 'coordenador') return <CoordenadorHome />
  if (perfil === 'supervisor') return <SupervisorHome />

  // Padrão: colaborador
  return <ColaboradorHome />
}

