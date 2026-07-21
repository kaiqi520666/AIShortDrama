export const connectionTargets = {
  text: ['text', 'image', 'video', 'audio'],
  image: ['text', 'image', 'video'],
  video: ['text', 'video', 'audio'],
  audio: ['text', 'video'],
}

export const canConnect = (sourceType, targetType) => connectionTargets[sourceType]?.includes(targetType) ?? false
