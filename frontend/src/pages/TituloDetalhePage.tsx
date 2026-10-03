import { useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router'
import { listarLogs, listarPagamentos, listarRateios, obterTitulo } from '../api/titulos'
import { useApi } from '../api/useApi'
import EmptyState from '../components/EmptyState'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'
import StatusBadge from '../components/StatusBadge'
import type { LogAuditoria, Pagamento, Rateio, TituloDetalhe } from '../types/api'
import { formatCurrency, formatDate, formatDateTime } from '../utils/format'

const ABAS = ['Summary', 'Allocations', 'Payments', 'Audit'] as const
type Aba = (typeof ABAS)[number]

async function carregar(id: string) {
  const [titulo, rateios, pagamentos, logs] = await Promise.all([
    obterTitulo(id),
    listarRateios(id),
    listarPagamentos(id),
    listarLogs(id),
  ])
  return { titulo, rateios, pagamentos, logs }
}

export default function TituloDetalhePage() {
  const { id = '' } = useParams()
  const { loading, data, error } = useApi(id, () => carregar(id))
  const [aba, setAba] = useState<Aba>('Summary')

  return (
    <section>
      <Link to="/" className="text-sm text-slate-500 hover:text-slate-900">
        ← Back to Accounts Payable
      </Link>

      {loading && <Loading />}
      {error && (
        <div className="mt-4">
          <ErrorMessage message={error} />
        </div>
      )}
      {data && (
        <>
          <Cabecalho titulo={data.titulo} />
          <Totais titulo={data.titulo} />

          <div className="mt-8 border-b border-slate-200">
            <nav className="-mb-px flex gap-6" role="tablist">
              {ABAS.map((a) => (
                <button
                  key={a}
                  role="tab"
                  aria-selected={aba === a}
                  onClick={() => setAba(a)}
                  className={`border-b-2 pb-3 text-sm font-medium ${
                    aba === a
                      ? 'border-slate-900 text-slate-900'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  }`}
                >
                  {a}
                </button>
              ))}
            </nav>
          </div>

          <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
            {aba === 'Summary' && <Resumo titulo={data.titulo} />}
            {aba === 'Allocations' && <Rateios titulo={data.titulo} rateios={data.rateios} />}
            {aba === 'Payments' && <Pagamentos titulo={data.titulo} pagamentos={data.pagamentos} />}
            {aba === 'Audit' && <Auditoria logs={data.logs} />}
          </div>
        </>
      )}
    </section>
  )
}

function Cabecalho({ titulo }: { titulo: TituloDetalhe }) {
  return (
    <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">{titulo.numero}</h1>
          <StatusBadge status={titulo.status} />
          {titulo.vencido && (
            <span className="rounded-full bg-red-600 px-2 py-0.5 text-xs font-medium text-white">OVERDUE</span>
          )}
        </div>
        <p className="mt-1 text-sm text-slate-600">{titulo.fornecedor.nome}</p>
      </div>
      <p className="text-sm text-slate-500">
        Due date <span className="font-medium text-slate-900">{formatDate(titulo.data_vencimento)}</span>
      </p>
    </div>
  )
}

// Todos os valores vêm calculados pelo backend (GET /titulos/{id}).
function Totais({ titulo }: { titulo: TituloDetalhe }) {
  const itens = [
    ['Total amount', titulo.valor_total],
    ['Allocated', titulo.valor_rateado],
    ['Paid', titulo.valor_pago],
    ['Outstanding balance', titulo.saldo_pendente],
  ]
  return (
    <dl className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
      {itens.map(([rotulo, valor]) => (
        <div key={rotulo} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{rotulo}</dt>
          <dd className="mt-1 text-xl font-semibold tabular-nums">{formatCurrency(valor)}</dd>
        </div>
      ))}
    </dl>
  )
}

function Campo({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{rotulo}</dt>
      <dd className="mt-1 text-sm text-slate-900">{children}</dd>
    </div>
  )
}

function Resumo({ titulo }: { titulo: TituloDetalhe }) {
  return (
    <dl className="grid gap-6 p-6 sm:grid-cols-2">
      <Campo rotulo="Number">{titulo.numero}</Campo>
      <Campo rotulo="Supplier">{titulo.fornecedor.nome}</Campo>
      <div className="sm:col-span-2">
        <Campo rotulo="Description">{titulo.descricao}</Campo>
      </div>
      <Campo rotulo="Status">
        <StatusBadge status={titulo.status} />
      </Campo>
      <Campo rotulo="Overdue">{titulo.vencido ? 'Yes' : 'No'}</Campo>
      <Campo rotulo="Issue date">{formatDate(titulo.data_emissao)}</Campo>
      <Campo rotulo="Due date">{formatDate(titulo.data_vencimento)}</Campo>
      <Campo rotulo="Total amount">{formatCurrency(titulo.valor_total)}</Campo>
      <Campo rotulo="Allocated amount">{formatCurrency(titulo.valor_rateado)}</Campo>
      <Campo rotulo="Paid amount">{formatCurrency(titulo.valor_pago)}</Campo>
      <Campo rotulo="Outstanding balance">{formatCurrency(titulo.saldo_pendente)}</Campo>
    </dl>
  )
}

function Rodape({ itens }: { itens: [string, string][] }) {
  return (
    <div className="flex flex-wrap justify-end gap-x-8 gap-y-1 border-t border-slate-200 bg-slate-50 px-4 py-3 text-sm">
      {itens.map(([rotulo, valor]) => (
        <span key={rotulo} className="text-slate-500">
          {rotulo} <span className="ml-1 font-semibold text-slate-900 tabular-nums">{formatCurrency(valor)}</span>
        </span>
      ))}
    </div>
  )
}

const th = 'px-4 py-3'
const theadClass = 'bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500'

function Rateios({ titulo, rateios }: { titulo: TituloDetalhe; rateios: Rateio[] }) {
  return (
    <>
      {rateios.length === 0 ? (
        <EmptyState text="No allocations found." />
      ) : (
        <table className="min-w-full text-sm">
          <thead className={theadClass}>
            <tr>
              <th className={th}>Cost center</th>
              <th className={`${th} text-right`}>Amount</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rateios.map((r) => (
              <tr key={r.id}>
                <td className="px-4 py-3">
                  <span className="font-medium">{r.centro_custo.codigo}</span>
                  <span className="ml-2 text-slate-600">{r.centro_custo.descricao}</span>
                  {!r.centro_custo.ativo && <span className="ml-2 text-xs text-slate-400">(inactive)</span>}
                </td>
                <td className="px-4 py-3 text-right tabular-nums">{formatCurrency(r.valor)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <Rodape
        itens={[
          ['Total amount', titulo.valor_total],
          ['Allocated', titulo.valor_rateado],
        ]}
      />
    </>
  )
}

function Pagamentos({ titulo, pagamentos }: { titulo: TituloDetalhe; pagamentos: Pagamento[] }) {
  return (
    <>
      {pagamentos.length === 0 ? (
        <EmptyState text="No payments found." />
      ) : (
        <table className="min-w-full text-sm">
          <thead className={theadClass}>
            <tr>
              <th className={th}>Payment date</th>
              <th className={`${th} text-right`}>Amount</th>
              <th className={th}>Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {pagamentos.map((p) => {
              const estornado = p.status === 'ESTORNADO'
              return (
                <tr key={p.id} className={estornado ? 'text-slate-400' : ''}>
                  <td className="px-4 py-3">{formatDate(p.data_pagamento)}</td>
                  <td className={`px-4 py-3 text-right tabular-nums ${estornado ? 'line-through' : ''}`}>
                    {formatCurrency(p.valor)}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={p.status} />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
      <Rodape
        itens={[
          ['Paid', titulo.valor_pago],
          ['Outstanding balance', titulo.saldo_pendente],
        ]}
      />
    </>
  )
}

function Auditoria({ logs }: { logs: LogAuditoria[] }) {
  if (logs.length === 0) return <EmptyState text="No audit events found." />
  return (
    <ol className="divide-y divide-slate-100">
      {logs.map((log) => (
        <li key={log.id} className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-start sm:gap-4">
          <time className="w-36 shrink-0 text-xs text-slate-500 tabular-nums">{formatDateTime(log.created_at)}</time>
          <div className="flex shrink-0 items-center gap-2 sm:w-56">
            <span className="text-xs font-medium text-slate-700">{log.tipo.replaceAll('_', ' ')}</span>
            <StatusBadge status={log.status} />
          </div>
          <p className="text-sm text-slate-800">{log.mensagem}</p>
        </li>
      ))}
    </ol>
  )
}
