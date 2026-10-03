import { translate } from '../i18n'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/** Erro já traduzido em uma mensagem que pode ser mostrada ao usuário. */
export class ApiError extends Error {
  readonly code?: string

  constructor(message: string, code?: string) {
    super(message)
    this.code = code
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json' },
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new ApiError(translate('api.timeout'), 'TIMEOUT')
    }
    throw new ApiError(translate('api.unavailable', { url: API_URL }), 'API_UNAVAILABLE')
  }

  const body = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(errorMessage(response.status, body), body?.error?.code)
  }
  if (body === null) {
    throw new ApiError(translate('api.unexpectedResponse'))
  }
  return body as T
}

function errorMessage(status: number, body: unknown): string {
  // Erros de domínio e de IA: { error: { code, message } }
  const domain = (body as { error?: { message?: string } } | null)?.error?.message
  if (domain) return domain
  // Validação do FastAPI: { detail: [{ msg }] }
  const detail = (body as { detail?: { msg?: string }[] } | null)?.detail
  if (Array.isArray(detail) && detail[0]?.msg) return translate('api.invalidRequest', { message: detail[0].msg })
  return translate('api.unexpectedError', { status })
}
