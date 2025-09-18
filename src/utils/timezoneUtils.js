/**
 * Utilitários para manipulação de timezone de Brasília
 */

// Timezone de Brasília (UTC-3)
const BRASILIA_TIMEZONE = 'America/Sao_Paulo';

/**
 * Converte uma data ISO string para o timezone de Brasília
 * @param {string} isoString - Data em formato ISO string
 * @returns {Date} - Data no timezone de Brasília
 */
export function parseBrasiliaDate(isoString) {
  if (!isoString) return null;
  
  // Se a string não tem timezone, assume UTC
  if (!isoString.includes('+') && !isoString.includes('Z') && !isoString.includes('-', 10)) {
    isoString += 'Z'; // Adiciona UTC se não tiver timezone
  }
  
  const date = new Date(isoString);
  
  // Converte para Brasília usando toLocaleString
  const brasiliaDate = new Date(date.toLocaleString('en-US', { timeZone: BRASILIA_TIMEZONE }));
  
  return brasiliaDate;
}

/**
 * Formata uma data para o padrão brasileiro no timezone de Brasília
 * @param {string|Date} date - Data para formatar
 * @param {string} format - Formato desejado ('date', 'time', 'datetime')
 * @returns {string} - Data formatada
 */
export function formatBrasiliaDate(date, format = 'datetime') {
  if (!date) return '';
  
  let dateObj;
  if (typeof date === 'string') {
    dateObj = parseBrasiliaDate(date);
  } else {
    dateObj = date;
  }
  
  if (!dateObj) return '';
  
  const options = {
    timeZone: BRASILIA_TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  };
  
  if (format === 'time') {
    options.hour = '2-digit';
    options.minute = '2-digit';
    options.second = '2-digit';
  } else if (format === 'datetime') {
    options.hour = '2-digit';
    options.minute = '2-digit';
    options.second = '2-digit';
  }
  
  return dateObj.toLocaleString('pt-BR', options);
}

/**
 * Obtém a data atual no timezone de Brasília
 * @returns {Date} - Data atual em Brasília
 */
export function getBrasiliaNow() {
  return new Date(new Date().toLocaleString('en-US', { timeZone: BRASILIA_TIMEZONE }));
}

/**
 * Converte uma data para ISO string no timezone de Brasília
 * @param {Date} date - Data para converter
 * @returns {string} - Data em formato ISO string
 */
export function toBrasiliaISOString(date) {
  if (!date) return null;
  
  // Converte para Brasília e depois para ISO
  const brasiliaDate = new Date(date.toLocaleString('en-US', { timeZone: BRASILIA_TIMEZONE }));
  return brasiliaDate.toISOString();
}
