export function buildOssImageUrl(url, { width = 1024, quality = 85 } = {}) {
  if (!url || typeof url !== 'string' || !/^https?:\/\//i.test(url)) return url

  const hashIndex = url.indexOf('#')
  const hash = hashIndex >= 0 ? url.slice(hashIndex) : ''
  const withoutHash = hashIndex >= 0 ? url.slice(0, hashIndex) : url
  const queryIndex = withoutHash.indexOf('?')
  const base = queryIndex >= 0 ? withoutHash.slice(0, queryIndex) : withoutHash
  const query = queryIndex >= 0 ? withoutHash.slice(queryIndex + 1) : ''
  const params = query.split('&').filter((param) => {
    if (!param) return false
    const key = param.split('=', 1)[0]
    try {
      return decodeURIComponent(key) !== 'x-oss-process'
    } catch {
      return key !== 'x-oss-process'
    }
  })

  params.push(`x-oss-process=image/resize,w_${width}/quality,q_${quality}/format,webp`)
  return `${base}?${params.join('&')}${hash}`
}
