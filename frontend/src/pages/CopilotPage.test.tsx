import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import CopilotPage from './CopilotPage'

function respostaFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status }))
}

function perguntar(texto: string) {
  fireEvent.change(screen.getByLabelText('Question'), { target: { value: texto } })
  fireEvent.click(screen.getByRole('button', { name: 'Send' }))
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('CopilotPage', () => {
  it('envia a pergunta e mostra a resposta com as tools usadas', async () => {
    const fetch = respostaFetch(200, {
      answer: 'O título 4 está com ERRO porque o centro de custo 1001 não existe no ERP.',
      tools_used: [
        { name: 'get_titulo', ok: true },
        { name: 'get_logs_titulo', ok: true },
        { name: 'search_documentation', ok: false },
      ],
    })
    vi.stubGlobal('fetch', fetch)
    render(<CopilotPage />)

    perguntar('Por que o título 4 está com erro?')

    expect(screen.getByText('Analyzing...')).toBeTruthy()
    expect(await screen.findByText(/centro de custo 1001/)).toBeTruthy()
    expect(screen.getByText('get_titulo')).toBeTruthy()
    expect(screen.getByText('get_logs_titulo')).toBeTruthy()
    expect(screen.getByText(/search_documentation/).textContent).toContain('(error)')

    const [url, init] = fetch.mock.calls[0]
    expect(url).toMatch(/\/ai\/copilot$/)
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({ question: 'Por que o título 4 está com erro?' })
  })

  it('renderiza Markdown da resposta sem interpretar HTML bruto', async () => {
    vi.stubGlobal(
      'fetch',
      respostaFetch(200, { answer: 'Status **ERRO**. <img src="x" onerror="alert(1)">', tools_used: [] }),
    )
    const { container } = render(<CopilotPage />)

    perguntar('Status do título 4?')

    expect((await screen.findByText('ERRO')).tagName).toBe('STRONG')
    expect(container.querySelector('img')).toBeNull()
    expect(screen.getByText('No tools were used.')).toBeTruthy()
  })

  it('mostra a mensagem de erro devolvida pela API', async () => {
    vi.stubGlobal(
      'fetch',
      respostaFetch(503, {
        error: { code: 'IA_NAO_CONFIGURADA', message: 'OPENAI_API_KEY não configurada.', details: {} },
      }),
    )
    render(<CopilotPage />)

    perguntar('Quais títulos estão vencidos?')

    expect((await screen.findByRole('alert')).textContent).toBe('OPENAI_API_KEY não configurada.')
  })

  it('avisa quando a API está indisponível', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    render(<CopilotPage />)

    perguntar('Quais títulos estão vencidos?')

    expect((await screen.findByRole('alert')).textContent).toMatch(/Could not reach the API/)
  })

  it('sugestão preenche o campo sem enviar', () => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    render(<CopilotPage />)

    fireEvent.click(screen.getByRole('button', { name: 'Quais títulos estão vencidos?' }))

    expect((screen.getByLabelText('Question') as HTMLTextAreaElement).value).toBe('Quais títulos estão vencidos?')
    expect(fetch).not.toHaveBeenCalled()
  })
})
