import { useState, type FormEvent } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { perguntarCopilot } from '../api/copilot'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'
import type { CopilotResponse } from '../types/api'

// Apenas exemplos para demonstração: clicar preenche o campo, não envia.
const SUGESTOES = [
  'Quais títulos estão vencidos?',
  'Por que o título 4 está com erro e como posso corrigir?',
  'O que acontece quando um pagamento de um título pago é estornado?',
  'Por que um título com rateio incompleto não pode ser aprovado?',
]

interface Resultado {
  question: string
  response?: CopilotResponse
  error?: string
}

export default function CopilotPage() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  // Só a última pergunta: o agente não tem memória entre requisições.
  const [resultado, setResultado] = useState<Resultado | null>(null)

  async function enviar(event: FormEvent) {
    event.preventDefault()
    const pergunta = question.trim()
    if (!pergunta || loading) return
    setLoading(true)
    setResultado(null)
    try {
      setResultado({ question: pergunta, response: await perguntarCopilot(pergunta) })
    } catch (error) {
      setResultado({ question: pergunta, error: (error as Error).message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="mx-auto max-w-3xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">AI Copilot</h1>
        <p className="mt-1 text-sm text-slate-500">
          Ask about invoices and accounts payable rules. The agent queries the system and the documentation through
          read-only tools. Each question is independent.
        </p>
      </div>

      <form onSubmit={enviar} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <label htmlFor="question" className="sr-only">
          Question
        </label>
        <textarea
          id="question"
          rows={3}
          maxLength={1000}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              e.currentTarget.form?.requestSubmit()
            }
          }}
          placeholder="Ask the Copilot..."
          className="w-full resize-none rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
        />
        <div className="mt-3 flex justify-end">
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </form>

      <div className="mt-4 flex flex-wrap gap-2">
        {SUGESTOES.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setQuestion(s)}
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:border-slate-400 hover:text-slate-900"
          >
            {s}
          </button>
        ))}
      </div>

      {loading && <Loading text="Analyzing..." />}

      {resultado && (
        <div className="mt-8 space-y-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">You</p>
            <p className="mt-1 text-sm text-slate-900">{resultado.question}</p>
          </div>
          {resultado.error && <ErrorMessage message={resultado.error} />}
          {resultado.response && <Resposta response={resultado.response} />}
        </div>
      )}
    </section>
  )
}

const markdownClass = [
  'mt-2 space-y-3 text-sm leading-relaxed text-slate-900',
  '[&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:mt-1 [&_strong]:font-semibold',
  '[&_table]:block [&_table]:overflow-x-auto [&_table]:text-xs [&_th]:border-b [&_th]:border-slate-200',
  '[&_th]:bg-slate-50 [&_th]:px-2 [&_th]:py-1.5 [&_th]:text-left [&_td]:border-b [&_td]:border-slate-100',
  '[&_td]:px-2 [&_td]:py-1.5 [&_td]:whitespace-nowrap',
].join(' ')

function Resposta({ response }: { response: CopilotResponse }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Copilot</p>
      {/* O modelo responde em Markdown (listas, tabelas). HTML bruto não é renderizado. */}
      <div className={markdownClass}>
        <Markdown remarkPlugins={[remarkGfm]}>{response.answer}</Markdown>
      </div>

      <div className="mt-5 border-t border-slate-100 pt-4">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Tools used</p>
        {response.tools_used.length === 0 ? (
          <p className="mt-2 text-xs text-slate-500">No tools were used.</p>
        ) : (
          <ul className="mt-2 flex flex-wrap gap-2">
            {/* Na ordem em que o backend executou; a mesma tool pode aparecer mais de uma vez. */}
            {response.tools_used.map((tool, i) => (
              <li
                key={i}
                title={tool.ok ? 'Executed successfully' : 'Returned an error'}
                className={`rounded-md px-2 py-1 font-mono text-xs ring-1 ring-inset ${
                  tool.ok ? 'bg-slate-50 text-slate-700 ring-slate-200' : 'bg-red-50 text-red-700 ring-red-200'
                }`}
              >
                {tool.name}
                {!tool.ok && ' (error)'}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
