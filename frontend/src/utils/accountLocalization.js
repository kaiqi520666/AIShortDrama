import { i18n } from '../i18n'

// Translate known API system labels; preserve user-authored content.
const labels = {
  "文本": "text",
  "图片": "image",
  "视频": "video",
  "音频": "audio",
  "图片生成": "imageGeneration",
  "视频生成": "videoGeneration",
  "音频生成": "audioGeneration",
  "图片反推": "imageReverse",
  "视频反推": "videoReverse",
  "比例": "ratio",
  "分辨率": "resolution",
  "参考图片": "referenceImages",
  "时长": "duration",
  "生成音频": "generateAudio",
  "是": "yes",
  "否": "no",
  "参考视频": "referenceVideos",
  "参考音频": "referenceAudio",
  "格式": "format",
  "采样率": "sampleRate",
  "语速": "speechRate",
  "音量": "volume",
  "音调": "pitch",
  "来源类型": "sourceType",
  "新用户注册赠送": "signup",
  "每日免费积分补足": "daily",
  "退还未使用的冻结积分": "unused"
}

export function localizeAccountText(value) {
  const { t } = i18n.global
  if (labels[value]) return t(`records.${labels[value]}`)
  if (typeof value !== 'string') return value
  const duration = value.match(/^(\d+(?:\.\d+)?) 秒$/)
  if (duration) return t('records.seconds', { count: duration[1] })
  const billing = value.match(/^(冻结|结算) (.+) 生成积分$/)
  if (billing) return t(billing[1] === '冻结' ? 'records.freezeNote' : 'records.settleNote', { model: billing[2] })
  const recharge = value.match(/^充值 (CNY|IDR) (\d+)，赠送 (\d+) 积分$/)
  if (recharge) return t('records.rechargeNote', { currency: recharge[1], amount: recharge[2], bonus: recharge[3] })
  return value
}
