export const storyboardTemplates = [
  { id: "ugc-seeding", label: "UGC 种草", description: "用户视角真实分享体验" },
];

export const storyboardTemplateRules = {
  "ugc-seeding": "以真实用户体验分享为主，不设置复杂剧情，不使用广告腔，开头尽快出现商品并通过实际操作和试吃表达感受。",
};

export const storyboardDurations = [15, 30, 45, 60];
export const storyboardSegmentShotCount = 6;
export const MAX_STORYBOARD_REFERENCES = 6;
export const MAX_STORYBOARD_CHARACTERS = 3;

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

export function createStoryboardTemplates() {
  return storyboardTemplates.map((item) => ({ ...item, enabled: true }));
}

export function storyboardSegmentCount(duration) {
  const seconds = Number(duration);
  return storyboardDurations.includes(seconds) ? seconds / 15 : 1;
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

const ugcStyleInstructions = `
UGC种草统一拍摄风格：全程由人物本人或同行者真实手持手机拍摄。自拍视频使用手臂长度的前置广角；第三人称跟拍、第一视角和商品近景使用后置1倍主摄。保留轻微腕部晃动、走路起伏、临时调整构图、自动对焦呼吸、自然曝光变化和环境混合光，手持感自然克制，不是剧烈抖动。
不使用三脚架、稳定器、滑轨、机械推镜、环绕运镜、专用微距、人像模式、电影级浅景深、慢动作、电影调色或商业广告运镜。镜头之间直接硬切，每个镜头只完成一个连续动作，动作结束后再切换，不快速蒙太奇。背景环境保持清晰可辨，构图允许轻微倾斜、偏离中心和自然截断，保留真实肤质和手机自动曝光变化。
`;

function buildReferenceInstructions(characterReferences, productCount) {
  const characters = normalizeStoryboardCharacters(characterReferences);
  const imageCharacters = characters.map((_, index) => `图片${index + 1}是角色${index + 1}参考图`).join("，");
  const imageProducts = Array.from({ length: productCount }, (_, index) => `图片${characters.length + index + 1}`).join("、");
  const videoCharacters = characters.map((_, index) => `图片${index + 2}是角色${index + 1}参考图`).join("，");
  const videoProducts = Array.from({ length: productCount }, (_, index) => `图片${characters.length + index + 2}`).join("、");
  return {
    image: [imageCharacters, `${imageProducts}是商品参考图`].filter(Boolean).join("。") + "。",
    video: ["图片1是本段分镜图", videoCharacters, `${videoProducts}是商品参考图`].filter(Boolean).join("，") + "。",
  };
}

function buildSpeakerInstructions(characterCount) {
  if (!characterCount) {
    return "没有角色参考图时不得生成可识别人脸；使用画外音或现场音，画外音必须写成‘画外音说道：\"内容。\"’。";
  }
  const speakers = characterCount === 1
    ? "她说道：\"内容。\"、他说道：\"内容。\"或他回答：\"内容。\""
    : Array.from({ length: characterCount }, (_, index) => `角色${index + 1}${index === 1 ? "回答" : "说道"}：\"内容。\"`).join("、");
  return `共有${characterCount}个指定角色，每个角色只能对应自己的参考图，不得新增人物。${speakers}。每个镜头都要有与当前动作相关的自然分享或连续画外音，人物未露脸、手部特写和商品特写也不能停止分享。对白必须使用中文双引号，禁止写“台词：”，禁止背诵式广告口号。`;
}

export function buildProductStoryboardPrompt(productContext, _templates, data = {}, supportedAspectRatios = []) {
  const requestedDuration = Number(data.duration);
  const totalDuration = storyboardDurations.includes(requestedDuration) ? requestedDuration : 15;
  const segments = storyboardSegmentCount(totalDuration);
  const ratio = supportedAspectRatios.includes(data.videoAspectRatio)
    ? data.videoAspectRatio
    : supportedAspectRatios.includes("9:16") ? "9:16" : supportedAspectRatios[0];
  if (!ratio) throw new Error("视频模型能力尚未加载");
  const grid = storyboardGrid(15, ratio);
  const characters = normalizeStoryboardCharacters(data.characterReferences);
  const productCount = Math.max(1, Math.min(getStoryboardProductLimit(characters.length), data.productReferences?.length || 1));
  const references = buildReferenceInstructions(characters, productCount);
  const extra = data.prompt?.trim() ? `\n用户补充要求：${data.prompt.trim()}` : "";
  const segmentRules = Array.from({ length: segments }, (_, index) => {
    const number = index + 1;
    return `第${number}段：15秒，固定6个镜头，按镜头1至镜头6顺序输出。${number === 1 ? "第一段必须独立开场，开头尽快出现商品。" : `本段默认承接第${number - 1}段；videoPrompt开头必须明确写“向后延长视频${number - 1}，延续上一段的主体、场景、光影、声音和手持拍摄质感”，只有确实换场时才写独立换场。`}`;
  }).join("\n");
  const context = productContext?.trim() || "暂无结构化商品资料，严格以商品参考图为准。";
  const schema = '{"templateId":"ugc-seeding","title":"UGC 种草","globalScript":"整体内容方向","segments":[{"segmentIndex":1,"duration":15,"shotCount":6,"plotGoal":"本段内容目标","openingState":"开头状态","endingState":"结尾状态","continuityMode":"cut","prompt":"镜头1：... 镜头2：... 镜头3：... 镜头4：... 镜头5：... 镜头6：...","videoPrompt":"图片1是本段分镜图，... 镜头1：... 镜头2：... 镜头3：... 镜头4：... 镜头5：... 镜头6：..."}]}';
  return `你是商品UGC种草分镜导演，负责直接为项目生成可执行的生图提示词和Seedance 2视频提示词。只保留“UGC 种草”这一种内容，禁止输出其他内容模板。必须自行在每条prompt和videoPrompt中完整写出拍摄方式、镜头、景别、运镜、光线、声音和对白。

本次输入参考图顺序：
生图阶段：${references.image} 生图阶段只有角色图和商品图，不包含分镜图。
生视频阶段：${references.video} 视频阶段图片1是刚生成的分镜图，角色和商品的身份、外观、颜色、材质、包装结构和真实尺寸以对应参考图为准。

商品资料：
${context}

内容方向：以真实用户的日常体验分享为主，开头尽快出现商品，不设置复杂连续剧情；通过拿取、开盖、搅拌、舀取、拉丝、试吃等具体动作表达携带、质地、口感和使用便利性。不要夸大功效，不使用广告腔，不长时间正面陈列包装文字。${ugcStyleInstructions}
${buildSpeakerInstructions(characters.length)}

生图prompt要求：生成一张${grid.columns}列×${grid.rows}行的六格UGC分镜板，按从左到右、从上到下对应镜头1至镜头6，每个小格保持${ratio}视频画幅。每格是像真实iPhone生活视频截取的未调色原始帧，明确写出人物动作、地点、商品状态、画面构图和实际拍法；六格之间场景或动作要有区别。分镜板只允许出现“镜头1”至“镜头6”作为格子标签，不要时长、字幕、价格、二维码、水印、额外Logo或其他可识别文字。包装文字无法准确复现时，让文字区域侧置、手部遮挡或轻微虚化，不要乱码。生图prompt禁止写对白、音效和背景音乐。

生视频prompt要求：严格引用图片1分镜图的构图和动作顺序，明确写出${ratio}画幅、参考图关系、六个镜头的地点、主体动作、景别、单一运镜、手持手机方式、自然光线、现场音和对白。每个镜头只完成一个连续动作，动作结束后硬切；不能用快速蒙太奇。自拍视频使用手臂长度的前置广角，第一视角和商品近景使用后置1倍主摄，侧面或背面跟拍使用同行者后置1倍主摄。保留轻微腕部晃动、走路起伏、自动对焦呼吸和曝光变化，不要棚拍、电影调色、广告布景、背景虚化或英雄产品镜头。对白使用‘她说道：\"内容。\"’、‘他说道：\"内容。\"’、‘他回答：\"内容。\"’或对应角色编号，禁止写“台词：”。保留脚步、风声、呼吸、开盖和勺子碰触玻璃等现场声音，不生成背景音乐。视频提示词中所有图片编号必须与上方实际顺序一致。

${segmentRules}${extra}

严格只输出一个JSON对象，不要Markdown、解释或额外文本，格式必须符合：${schema}。templateId必须始终为“ugc-seeding”，title必须为“UGC 种草”，segments必须恰好${segments}条且按顺序。每个segment的duration必须为15、shotCount必须为6、segmentIndex必须连续；第一段continuityMode必须为“cut”，后续段落只能为“extend”或“cut”。每条prompt和videoPrompt都必须完整写出镜头1、镜头2、镜头3、镜头4、镜头5、镜头6，不能合并、省略或输出空镜头。每条videoPrompt至少包含六句与镜头动作对应的自然对白或连续画外音。JSON字符串中的对白双引号必须正确转义，确保整个结果可被JSON.parse直接解析。商品结构、颜色、材质、包装和人物身份必须稳定，不得新增人物、商品或文字。`;
}

export function parseProductStoryboardPlan(content, _templates, _characterReferences = [], _productReferenceCount = 1) {
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
  if (!parsed || parsed.templateId !== "ugc-seeding" || !Array.isArray(parsed.segments)) {
    throw new Error("商品分镜方案必须为 UGC 种草 JSON 对象");
  }
  const totalDuration = Number(parsed.totalDuration || parsed.duration || parsed.segments.length * 15);
  const expectedSegments = storyboardSegmentCount(totalDuration);
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
    if (!hasStoryboardShotLabels(segment.prompt) || !hasStoryboardShotLabels(segment.videoPrompt)) {
      throw new Error(`第${index + 1}段必须包含镜头1至镜头${storyboardSegmentShotCount}`);
    }
    return {
      segmentIndex,
      duration: 15,
      shotCount: storyboardSegmentShotCount,
      plotGoal: segment.plotGoal.trim(),
      openingState: segment.openingState.trim(),
      endingState: segment.endingState.trim(),
      continuityMode: segment.continuityMode,
      prompt: segment.prompt.trim(),
      videoPrompt: segment.videoPrompt.trim(),
    };
  });
  return {
    templateId: "ugc-seeding",
    title: typeof parsed.title === "string" && parsed.title.trim() ? parsed.title.trim() : "UGC 种草",
    globalScript: typeof parsed.globalScript === "string" ? parsed.globalScript.trim() : "",
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
