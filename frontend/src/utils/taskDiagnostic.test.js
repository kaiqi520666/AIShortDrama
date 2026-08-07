import { describe, expect, it } from 'vitest'
import { taskDiagnosticSummary, taskStageLabel } from './taskDiagnostic'

describe('task diagnostic formatting', () => {
  it('formats provider HTTP failures', () => {
    expect(taskDiagnosticSummary({ stage: 'submit', provider_status: 524 })).toBe('提交失败 · HTTP 524')
  })

  it('uses a safe provider message when no status is present', () => {
    expect(taskDiagnosticSummary({ stage: 'poll', provider_message: '内容审核拒绝' })).toBe('轮询失败 · 内容审核拒绝')
  })

  it('falls back for unknown stages', () => {
    expect(taskStageLabel('other')).toBe('未知阶段')
  })
})
