import { afterEach, describe, expect, it, vi } from 'vitest'

afterEach(() => {
  localStorage.clear()
  vi.resetModules()
})

describe('i18n', () => {
  it('interpola parâmetros no idioma pedido', async () => {
    const { translate } = await import('./i18n')

    expect(translate('titulos.records', { count: 3 }, 'en-US')).toBe('3 records')
    expect(translate('titulos.records', { count: 3 }, 'pt-BR')).toBe('3 registros')
  })

  it('começa no idioma salvo e ignora valores desconhecidos', async () => {
    localStorage.setItem('ap-copilot.language', 'pt-BR')
    expect((await import('./i18n')).getLanguage()).toBe('pt-BR')

    vi.resetModules()
    localStorage.setItem('ap-copilot.language', 'xx')
    expect((await import('./i18n')).getLanguage()).toBe('en-US')
  })

  it('funciona sem localStorage disponível', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('bloqueado')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('bloqueado')
    })
    const i18n = await import('./i18n')

    expect(i18n.getLanguage()).toBe('en-US')
    i18n.setLanguage('pt-BR')
    expect(i18n.getLanguage()).toBe('pt-BR')
    vi.restoreAllMocks()
  })
})
