import { describe, expect, it } from 'vitest'
import { buildCharacterProfilePrompt, buildCharacterVisualPrompt, characterReady, mergeCharacterProfile, parseCharacterProfile, parseCharacterVisualPlan } from './character'

describe('character creation', () => {
  const profileJson = '{"name":"林澈","identity":"记者","background":"追查旧案","appearance":"短发清瘦","personality":"冷静执着","costume":"深色风衣","signature":"银色录音笔","constraints":"固定面部与风衣"}'

  it('builds a profile prompt with world and optional image constraints', () => {
    const prompt = buildCharacterProfilePrompt('近未来沿海城市', { setting: { roleType: '主角', gender: '女', ageStage: '青年', visualStyle: '电影写实' }, prompt: '调查失踪案' }, true)
    expect(prompt).toContain('世界观：\n近未来沿海城市')
    expect(prompt).toContain('参考图片是角色外形依据')
    expect(prompt).toContain('"constraints"')
  })

  it('parses and merges generated profiles without overwriting manual fields', () => {
    const generated = parseCharacterProfile(profileJson)
    const profile = mergeCharacterProfile({ name: '手填姓名' }, generated)
    expect(profile.name).toBe('手填姓名')
    expect(profile.identity).toBe('记者')
    expect(characterReady(profile)).toBe(true)
  })

  it('builds and parses the three fixed visual types', () => {
    const prompt = buildCharacterVisualPrompt('世界', '角色', { aspectRatio: '3:4', resolution: '2K' }, false)
    expect(prompt).toContain('full-body=正面全身')
    const plans = parseCharacterVisualPlan('[{"type":"full-body","prompt":"全身"},{"type":"portrait","prompt":"半身"},{"type":"turnaround","prompt":"三视图"}]')
    expect(plans.map((item) => item.label)).toEqual(['正面全身', '半身肖像', '角色三视图'])
  })
})
