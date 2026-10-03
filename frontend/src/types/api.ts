// Contratos de resposta da API FastAPI (backend/app/schemas).
// Valores monetários chegam como string decimal ("1234.56"): o backend usa Decimal.
export type Money = string

export type StatusTitulo = 'PENDENTE' | 'APROVADO' | 'PAGO' | 'CANCELADO' | 'ERRO'
export type StatusPagamento = 'CONFIRMADO' | 'ESTORNADO'

export interface Fornecedor {
  id: number
  nome: string
  ativo: boolean
}

export interface Titulo {
  id: number
  numero: string
  fornecedor_id: number
  fornecedor: { id: number; nome: string }
  descricao: string
  data_emissao: string
  data_vencimento: string
  valor_total: Money
  status: StatusTitulo
  created_at: string
  updated_at: string
}

export interface TituloDetalhe extends Titulo {
  valor_rateado: Money
  valor_pago: Money
  saldo_pendente: Money
  vencido: boolean
}

export interface Rateio {
  id: number
  centro_custo: { id: number; codigo: string; descricao: string; ativo: boolean }
  valor: Money
}

export interface Pagamento {
  id: number
  data_pagamento: string
  valor: Money
  status: StatusPagamento
}

export interface LogAuditoria {
  id: number
  tipo: string
  status: 'SUCESSO' | 'ERRO' | 'INFO'
  mensagem: string
  created_at: string
}

export interface CopilotResponse {
  answer: string
  tools_used: { name: string; ok: boolean }[]
}
