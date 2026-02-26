/**
 * Níveis de visualização e edição por perfil (espelho do backend):
 * - Colaborador: apenas próprio perfil (visualização e edição).
 * - Supervisor: acesso a todos do seu setor.
 * - Coordenador: acesso a uma seleção de setores.
 * - Head: todos os setores + configuração de tags.
 * - Admin: tudo + configurações do sistema.
 */
export const PERFIL = {
  COLABORADOR: 'colaborador',
  SUPERVISOR: 'supervisor',
  COORDENADOR: 'coordenador',
  HEAD: 'head',
  ADMIN: 'admin',
  CEO: 'ceo',
  GERENTE: 'gerente',
}

export function isColaborador(perfil) {
  return (perfil || '').toLowerCase() === PERFIL.COLABORADOR
}

export function isAdmin(perfil) {
  return (perfil || '').toLowerCase() === PERFIL.ADMIN
}

export function canEditTags(perfil) {
  const p = (perfil || '').toLowerCase()
  return [PERFIL.ADMIN, PERFIL.HEAD, PERFIL.CEO, PERFIL.GERENTE].includes(p)
}

export function canManageSystem(perfil) {
  return (perfil || '').toLowerCase() === PERFIL.ADMIN
}

/** Ver menu "Usuários" (lista) ou apenas "Meu perfil" */
export function canListUsers(perfil) {
  return !isColaborador(perfil)
}

/** Ver Tokens API e Configurações do sistema */
export function canSeeSystemMenu(perfil) {
  return canManageSystem(perfil)
}

export function getPerfilLabel(perfil) {
  const labels = {
    [PERFIL.COLABORADOR]: 'Colaborador',
    [PERFIL.SUPERVISOR]: 'Supervisor',
    [PERFIL.COORDENADOR]: 'Coordenador',
    [PERFIL.HEAD]: 'Head',
    [PERFIL.ADMIN]: 'Admin',
    [PERFIL.CEO]: 'CEO',
    [PERFIL.GERENTE]: 'Gerente',
  }
  return labels[(perfil || '').toLowerCase()] || perfil || 'Colaborador'
}
