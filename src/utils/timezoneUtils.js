/**
 * Utilitários para datas e horários no fuso de São Paulo (America/Sao_Paulo, UTC-3).
 * Todo o sistema deve exibir e interpretar datas neste timezone.
 */

export const SAO_PAULO_TZ = 'America/Sao_Paulo'

/**
 * Parse de string ISO para Date (instante UTC). Strings sem timezone são assumidas como UTC.
 * @param {string} isoString
 * @returns {Date|null}
 */
export function parseBrasiliaDate(isoString) {
  if (!isoString) return null
  let str = String(isoString).trim()
  if (!str) return null
  // Se não tem indicador de timezone, assume UTC
  if (!/[-+Z]\d{0,2}:?\d{0,2}$/i.test(str) && str.indexOf('T') !== -1) {
    if (!str.endsWith('Z')) str = str.replace(/(\d)$/, '$1Z')
  } else if (str.indexOf('T') === -1 && /^\d{4}-\d{2}-\d{2}$/.test(str)) {
    // Apenas data: interpretar como meia-noite em São Paulo
    return new Date(str + 'T00:00:00-03:00')
  }
  const date = new Date(str)
  return isNaN(date.getTime()) ? null : date
}

/**
 * Formata um Date (ou string ISO) no fuso de São Paulo.
 * @param {Date|string|null} date
 * @param {'date'|'time'|'datetime'|'isoDate'} format - date: dd/MM/yyyy | time: HH:mm:ss | datetime: dd/MM/yyyy HH:mm:ss | isoDate: yyyy-MM-dd
 * @returns {string}
 */
export function formatBrasiliaDate(date, format = 'datetime') {
  if (date == null) return ''
  const dateObj = typeof date === 'string' ? parseBrasiliaDate(date) : date
  if (!dateObj || isNaN(dateObj.getTime())) return ''

  const opts = {
    timeZone: SAO_PAULO_TZ,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }

  if (format === 'date') {
    return dateObj.toLocaleDateString('pt-BR', { timeZone: SAO_PAULO_TZ, day: '2-digit', month: '2-digit', year: 'numeric' })
  }
  if (format === 'dateWithMonth') {
    return dateObj.toLocaleDateString('pt-BR', { timeZone: SAO_PAULO_TZ, day: '2-digit', month: 'short' })
  }
  if (format === 'time') {
    return dateObj.toLocaleTimeString('pt-BR', { timeZone: SAO_PAULO_TZ, hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  }
  if (format === 'isoDate') {
    const parts = dateObj.toLocaleDateString('en-CA', { timeZone: SAO_PAULO_TZ, year: 'numeric', month: '2-digit', day: '2-digit' }).split('-')
    return parts.length === 3 ? `${parts[0]}-${parts[1]}-${parts[2]}` : ''
  }
  // datetime
  const d = dateObj.toLocaleDateString('pt-BR', { timeZone: SAO_PAULO_TZ, day: '2-digit', month: '2-digit', year: 'numeric' })
  const t = dateObj.toLocaleTimeString('pt-BR', { timeZone: SAO_PAULO_TZ, hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  return `${d} ${t}`
}

/**
 * Data/hora atual no instante atual (para comparações). Para exibir "hoje" em SP use getTodayIsoDate().
 * @returns {Date}
 */
export function getBrasiliaNow() {
  return new Date()
}

/**
 * Retorna a data de hoje no fuso de São Paulo no formato yyyy-MM-dd.
 * @returns {string}
 */
export function getTodayIsoDate() {
  const now = new Date()
  const parts = now.toLocaleDateString('en-CA', { timeZone: SAO_PAULO_TZ, year: 'numeric', month: '2-digit', day: '2-digit' }).split('-')
  return parts.length === 3 ? `${parts[0]}-${parts[1]}-${parts[2]}` : ''
}

/**
 * Início do dia em São Paulo para a data yyyy-MM-dd (00:00:00 -03:00).
 * Use .toISOString() para enviar à API.
 * @param {string} isoDate - yyyy-MM-dd
 * @returns {Date}
 */
export function startOfDayBrasilia(isoDate) {
  if (!isoDate || !/^\d{4}-\d{2}-\d{2}$/.test(isoDate)) return null
  return new Date(isoDate + 'T00:00:00-03:00')
}

/**
 * Fim do dia em São Paulo para a data yyyy-MM-dd (23:59:59.999 -03:00).
 * @param {string} isoDate - yyyy-MM-dd
 * @returns {Date}
 */
export function endOfDayBrasilia(isoDate) {
  if (!isoDate || !/^\d{4}-\d{2}-\d{2}$/.test(isoDate)) return null
  return new Date(isoDate + 'T23:59:59.999-03:00')
}

/**
 * Formata para padrão tipo date-fns (dd/MM/yyyy HH:mm:ss) em São Paulo.
 * Útil para substituir format(parseISO(x), 'dd/MM/yyyy HH:mm:ss', { locale: ptBR }).
 * @param {Date|string} date
 * @returns {string}
 */
export function formatBrasiliaDateTimeLong(date) {
  return formatBrasiliaDate(date, 'datetime')
}

/**
 * Retorna HH:mm em São Paulo (para filtros por horário).
 * @param {Date|string} date
 * @returns {string}
 */
export function formatBrasiliaTimeHHMM(date) {
  if (date == null) return '00:00'
  const dateObj = typeof date === 'string' ? parseBrasiliaDate(date) : date
  if (!dateObj || isNaN(dateObj.getTime())) return '00:00'
  const t = dateObj.toLocaleTimeString('pt-BR', { timeZone: SAO_PAULO_TZ, hour: '2-digit', minute: '2-digit', hour12: false })
  return t.length >= 5 ? t.slice(0, 5) : '00:00'
}

/**
 * Subtrai n dias de uma data no fuso de São Paulo.
 * @param {string} isoDate - yyyy-MM-dd
 * @param {number} n
 * @returns {string} yyyy-MM-dd
 */
export function subDaysBrasilia(isoDate, n) {
  const d = startOfDayBrasilia(isoDate)
  if (!d) return isoDate
  const nNum = Number(n)
  if (nNum === 0) return isoDate
  const t = d.getTime() - nNum * 24 * 60 * 60 * 1000
  return formatBrasiliaDate(new Date(t), 'isoDate')
}

const WEEKDAY_SP = { Mon: 0, Tue: 1, Wed: 2, Thu: 3, Fri: 4, Sat: 5, Sun: 6 }

/**
 * Retorna a data (yyyy-MM-dd) da segunda-feira da semana que contém a data em SP.
 * @param {string} [isoDate] - se omitido, usa hoje em SP
 * @returns {string}
 */
export function getWeekStartBrasilia(isoDate) {
  const today = isoDate || getTodayIsoDate()
  const d = new Date(today + 'T12:00:00-03:00')
  const weekday = new Intl.DateTimeFormat('en-US', { timeZone: SAO_PAULO_TZ, weekday: 'short' }).format(d)
  const daysFromMonday = (WEEKDAY_SP[weekday] + 6) % 7
  return subDaysBrasilia(today, daysFromMonday)
}
