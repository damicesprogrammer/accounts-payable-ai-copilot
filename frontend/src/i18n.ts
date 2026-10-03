import { useSyncExternalStore } from 'react'

// Textos da interface. Dados do sistema (status, nomes, mensagens da API e respostas
// do Copilot) não são traduzidos: vêm do backend como estão.
const enUS = {
  'layout.tagline': 'AI-powered Accounts Payable',
  'layout.language': 'Language',
  'nav.accountsPayable': 'Accounts Payable',
  'nav.copilot': 'AI Copilot',
  'common.loading': 'Loading...',
  'common.pageNotFound': 'Page not found.',
  'common.yes': 'Yes',
  'common.no': 'No',

  'titulos.subtitle': 'Payable invoices and their current status.',
  'titulos.status': 'Status',
  'titulos.allStatuses': 'All statuses',
  'titulos.supplier': 'Supplier',
  'titulos.allSuppliers': 'All suppliers',
  'titulos.overdueOnly': 'Overdue only',
  'titulos.showingFirst': 'Showing the first {count} records',
  'titulos.record': '{count} record',
  'titulos.records': '{count} records',
  'titulos.empty': 'No accounts payable records found.',

  'titulo.number': 'Number',
  'titulo.supplier': 'Supplier',
  'titulo.description': 'Description',
  'titulo.status': 'Status',
  'titulo.overdue': 'Overdue',
  'titulo.overdueBadge': 'OVERDUE',
  'titulo.issueDate': 'Issue date',
  'titulo.dueDate': 'Due date',
  'titulo.totalAmount': 'Total amount',
  'titulo.allocated': 'Allocated',
  'titulo.allocatedAmount': 'Allocated amount',
  'titulo.paid': 'Paid',
  'titulo.paidAmount': 'Paid amount',
  'titulo.outstandingBalance': 'Outstanding balance',
  'titulo.back': '← Back to Accounts Payable',
  'titulo.tab.summary': 'Summary',
  'titulo.tab.allocations': 'Allocations',
  'titulo.tab.payments': 'Payments',
  'titulo.tab.audit': 'Audit',
  'titulo.costCenter': 'Cost center',
  'titulo.amount': 'Amount',
  'titulo.inactive': '(inactive)',
  'titulo.paymentDate': 'Payment date',
  'titulo.noAllocations': 'No allocations found.',
  'titulo.noPayments': 'No payments found.',
  'titulo.noAuditEvents': 'No audit events found.',

  'copilot.intro':
    'Ask about invoices and accounts payable rules. The agent queries the system and the documentation through read-only tools. Each question is independent.',
  'copilot.question': 'Question',
  'copilot.placeholder': 'Ask the Copilot...',
  'copilot.send': 'Send',
  'copilot.analyzing': 'Analyzing...',
  'copilot.you': 'You',
  'copilot.copilot': 'Copilot',
  'copilot.toolsUsed': 'Tools used',
  'copilot.noTools': 'No tools were used.',
  'copilot.toolOk': 'Executed successfully',
  'copilot.toolError': 'Returned an error',
  'copilot.toolErrorSuffix': ' (error)',
  'copilot.suggestion.overdue': 'Which invoices are overdue?',
  'copilot.suggestion.error': 'Why is invoice 4 in error and how can I fix it?',
  'copilot.suggestion.reversal': 'What happens when a payment of a paid invoice is reversed?',
  'copilot.suggestion.allocation': 'Why can’t an invoice with an incomplete allocation be approved?',

  'api.timeout': 'The request timed out. Please try again.',
  'api.unavailable': 'Could not reach the API at {url}. Is the backend running?',
  'api.unexpectedResponse': 'Unexpected response from the API.',
  'api.invalidRequest': 'Invalid request: {message}',
  'api.unexpectedError': 'Unexpected API error (HTTP {status}).',
}

export type MessageKey = keyof typeof enUS

const ptBR: Record<MessageKey, string> = {
  'layout.tagline': 'Contas a pagar com IA',
  'layout.language': 'Idioma',
  'nav.accountsPayable': 'Contas a Pagar',
  'nav.copilot': 'Copiloto de IA',
  'common.loading': 'Carregando...',
  'common.pageNotFound': 'Página não encontrada.',
  'common.yes': 'Sim',
  'common.no': 'Não',

  'titulos.subtitle': 'Títulos a pagar e seu status atual.',
  'titulos.status': 'Status',
  'titulos.allStatuses': 'Todos os status',
  'titulos.supplier': 'Fornecedor',
  'titulos.allSuppliers': 'Todos os fornecedores',
  'titulos.overdueOnly': 'Somente vencidos',
  'titulos.showingFirst': 'Exibindo os primeiros {count} registros',
  'titulos.record': '{count} registro',
  'titulos.records': '{count} registros',
  'titulos.empty': 'Nenhum título a pagar encontrado.',

  'titulo.number': 'Número',
  'titulo.supplier': 'Fornecedor',
  'titulo.description': 'Descrição',
  'titulo.status': 'Status',
  'titulo.overdue': 'Vencido',
  'titulo.overdueBadge': 'VENCIDO',
  'titulo.issueDate': 'Emissão',
  'titulo.dueDate': 'Vencimento',
  'titulo.totalAmount': 'Valor total',
  'titulo.allocated': 'Rateado',
  'titulo.allocatedAmount': 'Valor rateado',
  'titulo.paid': 'Pago',
  'titulo.paidAmount': 'Valor pago',
  'titulo.outstandingBalance': 'Saldo pendente',
  'titulo.back': '← Voltar para Contas a Pagar',
  'titulo.tab.summary': 'Resumo',
  'titulo.tab.allocations': 'Rateios',
  'titulo.tab.payments': 'Pagamentos',
  'titulo.tab.audit': 'Auditoria',
  'titulo.costCenter': 'Centro de custo',
  'titulo.amount': 'Valor',
  'titulo.inactive': '(inativo)',
  'titulo.paymentDate': 'Data do pagamento',
  'titulo.noAllocations': 'Nenhum rateio encontrado.',
  'titulo.noPayments': 'Nenhum pagamento encontrado.',
  'titulo.noAuditEvents': 'Nenhum evento de auditoria encontrado.',

  'copilot.intro':
    'Pergunte sobre títulos e regras de contas a pagar. O agente consulta o sistema e a documentação por meio de tools somente leitura. Cada pergunta é independente.',
  'copilot.question': 'Pergunta',
  'copilot.placeholder': 'Pergunte ao Copilot...',
  'copilot.send': 'Enviar',
  'copilot.analyzing': 'Analisando...',
  'copilot.you': 'Você',
  'copilot.copilot': 'Copilot',
  'copilot.toolsUsed': 'Tools utilizadas',
  'copilot.noTools': 'Nenhuma tool foi utilizada.',
  'copilot.toolOk': 'Executada com sucesso',
  'copilot.toolError': 'Retornou um erro',
  'copilot.toolErrorSuffix': ' (erro)',
  'copilot.suggestion.overdue': 'Quais títulos estão vencidos?',
  'copilot.suggestion.error': 'Por que o título 4 está com erro e como posso corrigir?',
  'copilot.suggestion.reversal': 'O que acontece quando um pagamento de um título pago é estornado?',
  'copilot.suggestion.allocation': 'Por que um título com rateio incompleto não pode ser aprovado?',

  'api.timeout': 'A requisição excedeu o tempo limite. Tente novamente.',
  'api.unavailable': 'Não foi possível acessar a API em {url}. O backend está rodando?',
  'api.unexpectedResponse': 'Resposta inesperada da API.',
  'api.invalidRequest': 'Requisição inválida: {message}',
  'api.unexpectedError': 'Erro inesperado da API (HTTP {status}).',
}

export const LANGUAGES = ['en-US', 'pt-BR'] as const
export type Language = (typeof LANGUAGES)[number]

// Rótulos dos códigos de domínio (status de título, pagamento e log; tipo de log).
// Só apresentação: a API, os filtros e as tools continuam usando o código (ex.: PENDENTE).
const CODE_LABELS: Record<Language, Record<string, string>> = {
  'en-US': {
    PENDENTE: 'Pending',
    APROVADO: 'Approved',
    PAGO: 'Paid',
    CANCELADO: 'Canceled',
    ERRO: 'Error',
    CONFIRMADO: 'Confirmed',
    ESTORNADO: 'Reversed',
    SUCESSO: 'Success',
    INFO: 'Info',
    CRIACAO: 'Created',
    ATUALIZACAO: 'Updated',
    MUDANCA_STATUS: 'Status change',
    RATEIO: 'Allocation',
    PAGAMENTO: 'Payment',
    INTEGRACAO: 'Integration',
    CADASTRO: 'Registration',
  },
  'pt-BR': {
    PENDENTE: 'Pendente',
    APROVADO: 'Aprovado',
    PAGO: 'Pago',
    CANCELADO: 'Cancelado',
    ERRO: 'Erro',
    CONFIRMADO: 'Confirmado',
    ESTORNADO: 'Estornado',
    SUCESSO: 'Sucesso',
    INFO: 'Info',
    CRIACAO: 'Criação',
    ATUALIZACAO: 'Atualização',
    MUDANCA_STATUS: 'Mudança de status',
    RATEIO: 'Rateio',
    PAGAMENTO: 'Pagamento',
    INTEGRACAO: 'Integração',
    CADASTRO: 'Cadastro',
  },
}

const MESSAGES: Record<Language, Record<MessageKey, string>> = { 'en-US': enUS, 'pt-BR': ptBR }
const STORAGE_KEY = 'ap-copilot.language'
const DEFAULT_LANGUAGE: Language = 'en-US'

// Preferência por navegador: o armazenamento pode estar bloqueado, e a interface
// funciona sem ele (volta ao padrão).
function lerPreferencia(): Language {
  try {
    const salvo = localStorage.getItem(STORAGE_KEY)
    return LANGUAGES.find((l) => l === salvo) ?? DEFAULT_LANGUAGE
  } catch {
    return DEFAULT_LANGUAGE
  }
}

let current: Language = lerPreferencia()
document.documentElement.lang = current
const listeners = new Set<() => void>()

export function getLanguage(): Language {
  return current
}

export function setLanguage(language: Language): void {
  current = language
  document.documentElement.lang = language
  try {
    localStorage.setItem(STORAGE_KEY, language)
  } catch {
    // sem persistência: vale só para esta aba
  }
  listeners.forEach((listener) => listener())
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

/** "{count} records" + { count: 3 } → "3 records" */
export function translate(
  key: MessageKey,
  params: Record<string, string | number> = {},
  language: Language = current,
): string {
  return MESSAGES[language][key].replace(/\{(\w+)\}/g, (marcador, nome: string) =>
    nome in params ? String(params[nome]) : marcador,
  )
}

/** "PENDENTE" → "Pending" / "Pendente". Código desconhecido aparece como veio da API. */
export function codeLabel(code: string, language: Language = current): string {
  return CODE_LABELS[language][code] ?? code
}

/** Idioma atual + `t()` e `label()`; o componente re-renderiza quando o idioma muda. */
export function useI18n() {
  const language = useSyncExternalStore(subscribe, getLanguage)
  const t = (key: MessageKey, params?: Record<string, string | number>) => translate(key, params, language)
  const label = (code: string) => codeLabel(code, language)
  return { language, setLanguage, t, label }
}
