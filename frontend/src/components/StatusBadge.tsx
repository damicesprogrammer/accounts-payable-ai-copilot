// Status de título, pagamento e auditoria compartilham o mesmo badge.
const CORES: Record<string, string> = {
  PENDENTE: 'bg-amber-50 text-amber-800 ring-amber-200',
  APROVADO: 'bg-blue-50 text-blue-800 ring-blue-200',
  PAGO: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  CANCELADO: 'bg-slate-100 text-slate-600 ring-slate-300',
  ERRO: 'bg-red-50 text-red-700 ring-red-200',
  CONFIRMADO: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  ESTORNADO: 'bg-slate-100 text-slate-600 ring-slate-300',
  SUCESSO: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  INFO: 'bg-slate-100 text-slate-700 ring-slate-300',
}

export default function StatusBadge({ status }: { status: string }) {
  const cor = CORES[status] ?? 'bg-slate-100 text-slate-700 ring-slate-300'
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${cor}`}>
      {status}
    </span>
  )
}
