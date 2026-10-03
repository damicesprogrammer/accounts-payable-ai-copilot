import { getLanguage } from '../i18n'
import type { CopilotResponse } from '../types/api'
import { request } from './client'

// O agente pode fazer até 5 chamadas ao LLM (30 s cada no backend).
const TIMEOUT_MS = 180_000

/** O agente responde no idioma selecionado na interface. */
export function perguntarCopilot(question: string): Promise<CopilotResponse> {
  return request('/ai/copilot', {
    method: 'POST',
    body: JSON.stringify({ question, language: getLanguage() }),
    signal: AbortSignal.timeout(TIMEOUT_MS),
  })
}
