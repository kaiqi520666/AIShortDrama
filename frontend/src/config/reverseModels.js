export function normalizeTextModels(section) {
  return (section?.models || []).map(({ id, label, prompt_max_length: maxPromptLength }) => ({
    id,
    label,
    maxPromptLength,
  }))
}
