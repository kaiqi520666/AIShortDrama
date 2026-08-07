import { requireTemplate } from './contentTemplates'

export const storyboardSegmentShotCount = 6;
export const MAX_STORYBOARD_REFERENCES = 6;
export const MAX_STORYBOARD_CHARACTERS = 3;

function storyboardConfig(template) {
  return requireTemplate(template, '商品分镜模板').config
}

export function getStoryboardTemplates(template) {
  return storyboardConfig(template).templates.map((item) => ({ ...item }))
}

export function getStoryboardTemplateOption(template) {
  if (!template?.config) return null
  if (template.key === 'product_storyboard') {
    const option = template.config.templates?.[0]
    return option ? {
      key: template.key,
      id: option.id,
      label: option.label,
      description: option.description,
      enabled: Boolean(template.enabled && option.enabled),
      durations: [...template.config.durations],
    } : null
  }
  if (template.key === 'commerce_drama') {
    return {
      key: template.key,
      id: 'commerce-drama',
      label: template.config.label,
      description: template.config.description,
      enabled: Boolean(template.enabled),
      durations: [...template.config.durations],
    }
  }
  return null
}

export function getStoryboardDurations(template) {
  return [...storyboardConfig(template).durations]
}

export function normalizeStoryboardCharacters(value) {
  return (Array.isArray(value) ? value : value ? [value] : [])
    .filter((reference) => reference && (reference.url || reference.assetUrl))
    .slice(0, MAX_STORYBOARD_CHARACTERS);
}

export function buildStoryboardReferenceManifest(characterReferences = [], productReferences = []) {
  const characters = normalizeStoryboardCharacters(characterReferences);
  const products = (Array.isArray(productReferences) ? productReferences : [])
    .filter((reference) => reference && reference.url)
    .slice(0, Math.max(0, MAX_STORYBOARD_REFERENCES - characters.length));
  return { characters, products, references: [...characters, ...products] };
}

export function getStoryboardProductLimit(characterCount = 0) {
  const count = Math.min(MAX_STORYBOARD_CHARACTERS, Math.max(0, Number(characterCount) || 0));
  return Math.max(0, MAX_STORYBOARD_REFERENCES - count);
}

export function createStoryboardTemplates(template) {
  return getStoryboardTemplates(template);
}

export function storyboardSegmentCount(duration, durations) {
  const seconds = Number(duration);
  return durations.includes(seconds) ? seconds / 15 : 1;
}

export function storyboardShotCount(duration) {
  const seconds = Math.min(15, Math.max(4, Number(duration) || 4));
  if (seconds <= 5) return 2;
  if (seconds <= 8) return 3;
  if (seconds <= 11) return 4;
  return 6;
}

export function storyboardGrid(duration, videoAspectRatio = "9:16") {
  const shots = storyboardShotCount(duration);
  const portrait = ratioValue(videoAspectRatio) <= 1;
  const layouts = portrait
    ? { 2: [2, 1], 3: [3, 1], 4: [2, 2], 6: [3, 2] }
    : { 2: [1, 2], 3: [1, 3], 4: [2, 2], 6: [2, 3] };
  const [columns, rows] = layouts[shots];
  return { shots, columns, rows };
}

export function recommendStoryboardSettings(duration, videoAspectRatio = "9:16", model) {
  if (!model) throw new Error("图片模型能力尚未加载");
  const grid = storyboardGrid(duration, videoAspectRatio);
  const targetRatio = (grid.columns * ratioValue(videoAspectRatio)) / grid.rows;
  const aspectRatio = model.aspectRatios.reduce((best, value) =>
    Math.abs(ratioValue(value) - targetRatio) < Math.abs(ratioValue(best) - targetRatio) ? value : best,
  );
  const preferredResolution = grid.shots === 6 ? "4K" : "2K";
  const resolution = model.resolutions.includes(preferredResolution)
    ? preferredResolution
    : model.resolutions.at(-1) || model.defaultResolution;
  return { ...grid, aspectRatio, resolution };
}

export function buildProductStoryboardRequest({
  workspaceId,
  nodeId,
  model,
  template,
  productContext,
  duration,
  videoAspectRatio,
  characterReferences,
  productReferences,
  userRequirement,
}) {
  const manifest = buildStoryboardReferenceManifest(characterReferences, productReferences);
  return {
    workspace_id: workspaceId,
    node_id: nodeId,
    model,
    media_type: "image",
    media_url: manifest.references[0]?.url,
    media_urls: manifest.references.slice(1).map((reference) => reference.url),
    template_key: template.key,
    template_version: template.version,
    template_context: {
      product_context: productContext,
      duration,
      video_aspect_ratio: videoAspectRatio,
      character_count: manifest.characters.length,
      product_count: manifest.products.length,
      user_requirement: userRequirement || "",
    },
    response_mode: "product_storyboard_plan",
  };
}

export function parseProductStoryboardPlan(content, template) {
  const storyboardDurations = getStoryboardDurations(template);
  const expectedTemplateId = template.key === 'commerce_drama' ? 'commerce-drama' : 'ugc-seeding';
  const templateLabel = template.key === 'commerce_drama' ? '短剧带货' : 'UGC 种草';
  const source = String(content || "")
    .trim()
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/\s*```$/, "");
  const start = source.indexOf("{");
  const end = source.lastIndexOf("}");
  if (start < 0 || end <= start) throw new Error("未生成有效的商品分镜方案");
  let parsed;
  try {
    parsed = JSON.parse(source.slice(start, end + 1));
  } catch {
    throw new Error("商品分镜方案格式异常");
  }
  if (!parsed || parsed.templateId !== expectedTemplateId || !Array.isArray(parsed.segments)) {
    throw new Error(`商品分镜方案必须为${templateLabel} JSON 对象`);
  }
  const totalDuration = Number(parsed.totalDuration || parsed.duration || parsed.segments.length * 15);
  const expectedSegments = storyboardSegmentCount(totalDuration, storyboardDurations);
  if (parsed.segments.length !== expectedSegments) throw new Error(`商品分镜段落数量应为 ${expectedSegments} 条`);
  const segments = parsed.segments.map((segment, index) => {
    const segmentIndex = Number(segment?.segmentIndex);
    if (segmentIndex !== index + 1 || Number(segment?.duration) !== 15 || Number(segment?.shotCount) !== storyboardSegmentShotCount) {
      throw new Error("商品分镜段落顺序、时长或镜头数量异常");
    }
    if (!['cut', 'extend'].includes(segment?.continuityMode) || (index === 0 && segment.continuityMode !== 'cut')) {
      throw new Error("商品分镜衔接方式异常");
    }
    if (![segment.plotGoal, segment.openingState, segment.endingState, segment.prompt, segment.videoPrompt]
      .every((value) => typeof value === "string" && value.trim())) {
      throw new Error("商品分镜段落内容不完整");
    }
    if (expectedTemplateId === 'commerce-drama' && ![segment.dramaticBeat, segment.productPlacement]
      .every((value) => typeof value === 'string' && value.trim())) {
      throw new Error('短剧带货段落缺少剧情节拍或商品植入');
    }
    if (!hasStoryboardShotLabels(segment.prompt) || !hasStoryboardShotLabels(segment.videoPrompt)) {
      throw new Error(`第${index + 1}段必须包含镜头1至镜头${storyboardSegmentShotCount}`);
    }
    return {
      segmentIndex,
      duration: 15,
      shotCount: storyboardSegmentShotCount,
      plotGoal: segment.plotGoal.trim(),
      ...(expectedTemplateId === 'commerce-drama' ? {
        dramaticBeat: segment.dramaticBeat.trim(),
        productPlacement: segment.productPlacement.trim(),
      } : {}),
      openingState: segment.openingState.trim(),
      endingState: segment.endingState.trim(),
      continuityMode: segment.continuityMode,
      prompt: segment.prompt.trim(),
      videoPrompt: segment.videoPrompt.trim(),
    };
  });
  return {
    templateId: expectedTemplateId,
    title: typeof parsed.title === "string" && parsed.title.trim() ? parsed.title.trim() : templateLabel,
    globalScript: typeof parsed.globalScript === "string" ? parsed.globalScript.trim() : "",
    ...(expectedTemplateId === 'commerce-drama' && Array.isArray(parsed.characters)
      ? { characters: parsed.characters }
      : {}),
    totalDuration,
    segments,
  };
}

function ratioValue(value) {
  const [width, height] = String(value).split(":").map(Number);
  return width > 0 && height > 0 ? width / height : 1;
}

function hasStoryboardShotLabels(value) {
  return Array.from({ length: storyboardSegmentShotCount }, (_, index) => index + 1)
    .every((number) => new RegExp(`(?:镜头|第)\\s*${number}(?:格)?`).test(value));
}
