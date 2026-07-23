export const connectionTargets = {
  text: ['text', 'image', 'video'],
  image: ['text', 'image', 'video'],
  video: ['text', 'video'],
  audio: ['video'],
}

export const canConnect = (sourceType, targetType) => connectionTargets[sourceType]?.includes(targetType) ?? false
