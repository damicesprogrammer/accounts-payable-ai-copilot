import { useEffect, useState } from 'react'

interface Resultado<T> {
  key: string
  data?: T
  error?: string
}

/**
 * Carrega dados quando `key` muda. `load` deve depender só de `key`.
 * Respostas de uma key antiga são descartadas (filtros trocados rapidamente).
 */
export function useApi<T>(key: string, load: () => Promise<T>) {
  const [resultado, setResultado] = useState<Resultado<T> | null>(null)

  useEffect(() => {
    let ativo = true
    load().then(
      (data) => ativo && setResultado({ key, data }),
      (error: Error) => ativo && setResultado({ key, error: error.message }),
    )
    return () => {
      ativo = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `load` é derivado de `key`
  }, [key])

  const atual = resultado?.key === key ? resultado : null
  return { loading: atual === null, data: atual?.data, error: atual?.error }
}
