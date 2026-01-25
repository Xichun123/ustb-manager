import { useEffect, useState, useCallback } from 'react'

type SSEStatus = 'CONNECTING' | 'OPEN' | 'CLOSED'

interface SSEData {
  status: string
  message?: string
}

export function useSSE(url: string | null) {
  const [data, setData] = useState<SSEData | null>(null)
  const [error, setError] = useState<Event | null>(null)
  const [status, setStatus] = useState<SSEStatus>('CLOSED')

  const connect = useCallback(() => {
    if (!url) return

    const eventSource = new EventSource(url, { withCredentials: true })
    setStatus('CONNECTING')

    eventSource.onopen = () => {
      setStatus('OPEN')
      setError(null)
    }

    eventSource.addEventListener('status', (event: MessageEvent) => {
      try {
        setData(JSON.parse(event.data))
      } catch {
        setData({ status: event.data })
      }
    })

    eventSource.onerror = (err) => {
      setError(err)
      eventSource.close()
      setStatus('CLOSED')
    }

    return () => eventSource.close()
  }, [url])

  useEffect(() => {
    const cleanup = connect()
    return cleanup
  }, [connect])

  return { data, error, status }
}
