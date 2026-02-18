// Grupos de páginas por funcionalidade (referência para classificação)
export const GRUPOS_FUNCIONALIDADE = [
  { grupo: 'Sistemas Corporativos', exemplos: 'ERP, CRM, Service Desk', classificacao: 'Produtivo' },
  { grupo: 'Comunicação', exemplos: 'Teams, Slack, Email', classificacao: 'Produtivo' },
  { grupo: 'Desenvolvimento', exemplos: 'VS Code, IDE, Git', classificacao: 'Produtivo' },
  { grupo: 'Navegação Geral', exemplos: 'Portais, pesquisas web', classificacao: 'Neutro' },
  { grupo: 'Navegação Web', exemplos: 'Chrome, Firefox, Edge', classificacao: 'Neutro' },
  { grupo: 'Entretenimento', exemplos: 'Streaming, redes sociais', classificacao: 'Não produtivo' },
  { grupo: 'Outros', exemplos: 'Sistema local, desconhecido', classificacao: 'Neutro' }
]

// Mapeamento categoria/application -> grupo para filtro e exibição
export const CATEGORIA_TO_GRUPO = {
  'escritorio': 'Sistemas Corporativos',
  'navegador': 'Navegação Web',
  'desenvolvimento': 'Desenvolvimento',
  'comunicacao': 'Comunicação',
  'entretenimento': 'Entretenimento',
  'neutral': 'Navegação Geral',
  'productive': 'Sistemas Corporativos',
  'nonproductive': 'Entretenimento'
}

export function getGrupoFromCategoria(categoria, application = '') {
  if (!categoria) return 'Outros'
  const cat = (categoria || '').toLowerCase()
  const app = (application || '').toLowerCase()
  if (app.includes('chrome') || app.includes('firefox') || app.includes('edge')) return 'Navegação Web'
  if (app.includes('code') || app.includes('vscode') || app.includes('visual studio')) return 'Desenvolvimento'
  if (app.includes('teams') || app.includes('slack') || app.includes('outlook')) return 'Comunicação'
  return CATEGORIA_TO_GRUPO[cat] || 'Outros'
}
