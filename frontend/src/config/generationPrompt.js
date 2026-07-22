export const maxGenerationPromptLength = 32000

export function getEffectivePrompt(data = {}, references = []) {
  return [
    ...references.filter((node) => node?.type === 'text').map((node) => node.data?.content),
    data.prompt,
  ].map((value) => value?.trim()).filter(Boolean).join('\n')
}
