import type { Fornecedor, LogAuditoria, Pagamento, Rateio, Titulo, TituloDetalhe } from '../types/api'
import { request } from './client'

export interface FiltrosTitulos {
  status: string
  fornecedorId: string
  vencidos: boolean
}

// Sem paginação na UI: o limite máximo da API cobre os dados de demonstração.
export const LIMITE_TITULOS = 200

export function listarTitulos(filtros: FiltrosTitulos): Promise<Titulo[]> {
  const params = new URLSearchParams({ limit: String(LIMITE_TITULOS) })
  if (filtros.status) params.set('status', filtros.status)
  if (filtros.fornecedorId) params.set('fornecedor_id', filtros.fornecedorId)
  if (filtros.vencidos) params.set('vencidos', 'true')
  return request(`/titulos?${params}`)
}

export function listarFornecedores(): Promise<Fornecedor[]> {
  return request('/fornecedores?limit=200')
}

export function obterTitulo(id: string): Promise<TituloDetalhe> {
  return request(`/titulos/${id}`)
}

export function listarRateios(id: string): Promise<Rateio[]> {
  return request(`/titulos/${id}/rateios`)
}

export function listarPagamentos(id: string): Promise<Pagamento[]> {
  return request(`/titulos/${id}/pagamentos`)
}

export function listarLogs(id: string): Promise<LogAuditoria[]> {
  return request(`/titulos/${id}/logs`)
}
