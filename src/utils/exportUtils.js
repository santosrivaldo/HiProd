
import { format } from 'date-fns'

export const exportToCSV = (data, filename, headers = null) => {
  if (!data || data.length === 0) {
    alert('Nenhum dado para exportar')
    return
  }

  // Se headers não foi fornecido, usar as chaves do primeiro objeto
  const csvHeaders = headers || Object.keys(data[0])
  
  // Criar o cabeçalho CSV
  const csvContent = [
    csvHeaders.join(','),
    ...data.map(row => 
      csvHeaders.map(header => {
        let value = row[header] || ''
        // Escapar aspas duplas e quebras de linha
        if (typeof value === 'string') {
          value = value.replace(/"/g, '""')
          if (value.includes(',') || value.includes('\n') || value.includes('"')) {
            value = `"${value}"`
          }
        }
        return value
      }).join(',')
    )
  ].join('\n')

  // Criar e baixar o arquivo
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', `${filename}_${format(new Date(), 'yyyy-MM-dd_HH-mm-ss')}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

export const printData = (title, data, columns) => {
  const printWindow = window.open('', '_blank')
  
  const printContent = `
    <!DOCTYPE html>
    <html>
    <head>
      <title>${title}</title>
      <style>
        body {
          font-family: Arial, sans-serif;
          margin: 20px;
          color: #333;
        }
        h1 {
          color: #1f2937;
          border-bottom: 2px solid #e5e7eb;
          padding-bottom: 10px;
        }
        .print-info {
          margin-bottom: 20px;
          font-size: 12px;
          color: #6b7280;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          margin-top: 20px;
        }
        th, td {
          border: 1px solid #d1d5db;
          padding: 8px 12px;
          text-align: left;
        }
        th {
          background-color: #f9fafb;
          font-weight: bold;
          color: #374151;
        }
        tr:nth-child(even) {
          background-color: #f9fafb;
        }
        .productive {
          background-color: #dcfce7 !important;
          color: #166534;
        }
        .nonproductive {
          background-color: #fecaca !important;
          color: #991b1b;
        }
        .neutral {
          background-color: #dbeafe !important;
          color: #1e40af;
        }
        .idle {
          background-color: #f3f4f6 !important;
          color: #374151;
        }
        @media print {
          body { margin: 0; }
          .no-print { display: none; }
        }
      </style>
    </head>
    <body>
      <h1>${title}</h1>
      <div class="print-info">
        Relatório gerado em: ${format(new Date(), 'dd/MM/yyyy HH:mm:ss')}
      </div>
      <table>
        <thead>
          <tr>
            ${columns.map(col => `<th>${col.header}</th>`).join('')}
          </tr>
        </thead>
        <tbody>
          ${data.map(row => `
            <tr>
              ${columns.map(col => `<td class="${col.className ? col.className(row) : ''}">${col.accessor(row)}</td>`).join('')}
            </tr>
          `).join('')}
        </tbody>
      </table>
      <script>
        window.onload = function() {
          window.print();
          window.onafterprint = function() {
            window.close();
          }
        }
      </script>
    </body>
    </html>
  `
  
  printWindow.document.write(printContent)
  printWindow.document.close()
}

export const formatTime = (seconds) => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}
