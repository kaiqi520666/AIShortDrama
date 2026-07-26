export const imageAssetCategories = [
  { value: 'all', label: '全部' },
  { value: 'general', label: '普通图片' },
  { value: 'model', label: '模特' },
  { value: 'character', label: '角色' },
]

const modelUrls = [
  '10ceb15ec0ad430b9ef9ac0eb92d9c5e.png',
  '14b359841edb4d50028a3244e134d0af.png',
  '18e9d453d226966892123157eb43caa6.png',
  '296d71c0fe0910e63bf3cd10cafe2114.png',
  '2dc021c209110df11f4c689473b72294.png',
  '2e17466edd26f4978075214894e42640.png',
  '33ec87f1da0b60b18ad6e93a0698061f.png',
  '39f1306b5af144696b21c8ad191970b0.png',
  '625f66cb1f35c116e5ee352227631ed8.png',
  '652401272e8274e381b2a01f92e6d1d2.png',
  '6af4f1a648faa00cfdd80a6112b0c99e.png',
  '7f1bbce8d4e7c6eab4c4ce520fbc4359.png',
  '84fc2055d7e95d1932ca4c6330e57ef1.png',
  '93bb1bb35715e703e45ecf475e928960.png',
  '97ed9e1e562c697e9e693c9765e39ed7.png',
  '9a20be85d4cc9df5393d0a2bf56ae393.png',
  'a382dab2122d923cdf8577f900a26ed1.png',
  'a9ff82de3ba38df9ae382a277757a8b3.png',
  'abf657269fea635934364a4f33f3ee74.png',
  'aeddca98b3d35b633566ffb3789c9706.png',
  'af0365ac163f4ce851af248e7290d368.png',
  'c2168ccb6a4b4829ae6476f54502b7f2.png',
  'c5d4cc970d81154c33c931dcbf529c94.png',
  'd0409c74d78262c25e4b3964c229708b.png',
  'e23dc2083b24e38f876940da012848da.png',
]

export const systemImageAssets = modelUrls.map((filename, index) => ({
  id: `system-model-${index + 1}`,
  name: `模特 ${String(index + 1).padStart(2, '0')}`,
  url: `https://image.nodepass.net/system/outfit-models/${filename}`,
  mediaType: 'image',
  category: 'model',
  source: 'system',
  width: 3,
  height: 4,
}))

export function normalizeAssetItem(asset) {
  return {
    id: asset.id,
    assetId: asset.id,
    name: asset.name,
    url: asset.url,
    mediaType: asset.media_type,
    category: asset.category || asset.metadata?.category || 'general',
    source: 'user',
    width: asset.width,
    height: asset.height,
    byteSize: asset.byte_size,
  }
}
