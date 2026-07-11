import { describe, expect, it } from 'vitest'

import { getApiErrorMessage } from './api'

describe('getApiErrorMessage', () => {
  it('reads the stable backend error envelope', () => {
    const error = {
      isAxiosError: true,
      response: {
        data: {
          error: {
            code: 'UPSTREAM_RATE_LIMITED',
            message: '请稍后重试',
            retryable: true,
            request_id: 'request-1',
          },
        },
      },
    }

    expect(getApiErrorMessage(error, 'fallback')).toBe('请稍后重试')
  })

  it('uses the fallback for non-API errors', () => {
    expect(getApiErrorMessage(new Error('internal detail'), '加载失败')).toBe('加载失败')
  })
})
