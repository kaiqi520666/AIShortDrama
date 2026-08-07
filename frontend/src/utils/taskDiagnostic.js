const STAGE_LABELS = {
  enqueue: '入队',
  submit: '提交',
  poll: '轮询',
  download: '下载',
  storage: '存储',
  billing: '计费',
  unknown: '未知阶段',
}

export function taskDiagnosticSummary(diagnostic) {
  if (!diagnostic) return ''
  const stage = STAGE_LABELS[diagnostic.stage] || STAGE_LABELS.unknown
  const reason = diagnostic.provider_status
    ? `HTTP ${diagnostic.provider_status}`
    : diagnostic.provider_message || '未知错误'
  return `${stage}失败 · ${reason}`
}

export function taskStageLabel(stage) {
  return STAGE_LABELS[stage] || STAGE_LABELS.unknown
}
