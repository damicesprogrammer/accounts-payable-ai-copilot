const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const dataHora = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' })

/** "1234.56" → "R$ 1.234,56" */
export function formatCurrency(value: string | number): string {
  return brl.format(Number(value))
}

/** "2026-10-03" → "03/10/2026". Sem `new Date`, que interpretaria a data em UTC. */
export function formatDate(value: string): string {
  const [ano, mes, dia] = value.slice(0, 10).split('-')
  return `${dia}/${mes}/${ano}`
}

/** Timestamp ISO → "03/10/2026, 14:05" no fuso do navegador. */
export function formatDateTime(value: string): string {
  return dataHora.format(new Date(value))
}
