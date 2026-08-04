import { defaultImageModel } from "../imageModels";
import { videoAspectRatios } from "../videoModels";

export { videoAspectRatios };

export const storyboardTemplates = [
  { id: "ugc-seeding", label: "UGC 种草", description: "用户视角真实分享体验" },
  { id: "sales-drama", label: "带货短剧", description: "短剧情节植入产品" },
  {
    id: "product-demo",
    label: "产品演示",
    description: "多角度展示与使用演示",
  },
  {
    id: "product-pitch",
    label: "产品口播",
    description: "面对镜头讲解产品卖点",
  },
  { id: "tvc", label: "TVC 广告", description: "品牌广告片质感" },
  { id: "pain-solution", label: "痛点解决", description: "痛点场景到产品解决" },
  { id: "unboxing", label: "开箱种草", description: "第一视角拆包惊喜体验" },
  { id: "reaction", label: "反应展示", description: "首次使用的惊喜反应" },
];

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
  return {
    characters,
    products,
    references: [...characters, ...products],
  };
}

export function getStoryboardProductLimit(characterCount = 0) {
  const count = Math.min(MAX_STORYBOARD_CHARACTERS, Math.max(0, Number(characterCount) || 0));
  return Math.max(0, MAX_STORYBOARD_REFERENCES - count);
}

function buildCharacterSpeechRule(characterCount, isUgc, segmented = false) {
  if (!characterCount) return isUgc
    ? "没有注册角色时不得出现人脸；UGC不强制对白，只使用画外音或现场音，必要时写成“画外音说道：\"内容。\"”。"
    : "没有注册角色时不得出现人脸，使用画外音或现场音，写成“画外音说道：\"内容。\"”。";
  const speakers = characterCount === 1
    ? "她说道：“内容。”、他说道：“内容。”或他回答：“内容。”"
    : "角色1说道：“内容。”、角色2回答：“内容。”或角色3说道：“内容。”";
  const multiRoleRule = characterCount > 1
    ? `共有${characterCount}个角色，必须用角色1至角色${characterCount}明确区分说话人，每个角色至少参与一处对白，不得新增人物。`
    : "";
  if (!isUgc) return `每条 videoPrompt 至少安排一个指定角色自然说一句与当前动作直接相关的话；${multiRoleRule}对白必须用中文双引号包裹，使用${speakers}，同时说明口型与声音同步；禁止写成“台词：”或未加引号的对白。`;
  return `UGC种草由${characterCount === 1 ? "指定角色" : `角色1至角色${characterCount}`}围绕当前动作、场景和商品体验连续、真实地分享，不安排完全无对白的镜头。每个镜头至少包含一句自然口语；${multiRoleRule}人物未露脸或画面为手部、商品特写时，使用对应角色的连续画外音。${segmented ? "15秒六个镜头至少安排六句对白，每句简短、口语化、内容不重复，开头镜头立即开口。" : ""}对白必须用中文双引号包裹，使用${speakers}，口型与声音同步，禁止写成“台词：”或未加引号的对白。`;
}

export const ugcStoryboardImageStyleRule = `【UGC种草固定画面规则，程序统一控制，优先级高于镜头正文】
每格分镜必须像真实iPhone生活视频中截取的未调色原始帧。镜头1和镜头5使用手臂长度的前置广角自拍视频；镜头2和镜头4使用后置1倍主摄第一视角；镜头3使用同行者后置1倍主摄侧面手持跟拍；镜头6使用后置1倍主摄背面手持跟拍，少于六个镜头时按顺序取前面的拍法。
背景环境保持清晰可辨，构图允许轻微倾斜、偏离中心和自然截断，保留日光明暗变化、局部曝光变化和真实肤质。禁止棚灯、三脚架、稳定器、滑轨、机械推镜、环绕运镜、专用微距、人像模式、浅景深、背景虚化、电影调色、商业产品摄影、居中英雄镜头和精致广告布景。`;

export const ugcStoryboardVideoStyleRule = `【UGC种草固定拍摄规则，程序统一控制，优先级高于镜头正文】
全程由人物本人或同行者真实手持手机拍摄。自拍视频使用手臂长度的前置广角；第三人称跟拍、第一视角和商品近景使用后置1倍主摄。保留轻微腕部晃动、走路起伏、临时调整构图、自动对焦呼吸、自然曝光变化和环境混合光，手持感自然克制，不是剧烈抖动。
不使用三脚架、稳定器、滑轨、机械推镜、环绕运镜、专用微距、人像模式、电影级浅景深、慢动作、电影调色或商业广告运镜。镜头之间直接硬切，每个镜头只完成一个连续动作，动作结束后再切换，不快速蒙太奇。商品通过拿取、开盖、搅拌、舀取和试吃自然进入画面，不长时间正对镜头陈列标签。保留脚步、风声、呼吸、开盖和勺子碰触玻璃的现场声音，不生成背景音乐。`;

const ugcPromptOwnershipRule =
  "UGC种草模板的内容由Qwen负责，Qwen只输出人物动作、地点、商品状态、自然对白和现场音；不得自行决定镜头、景别、运镜、焦点、景深、灯光、调色或广告风格，这些由程序统一控制。";

export const storyboardTemplateRules = {
  "ugc-seeding": `生活化自拍视频：在真实生活场景中边体验边分享，按动作顺序展示商品使用过程，不设计剧情冲突、铺垫或正式推荐。${ugcPromptOwnershipRule}`,
  "sales-drama":
    "微剧情带货：先建立具体冲突或需求，角色自然说道问题，再让商品介入解决，展示结果变化并用一句回应收尾。剧情服务商品，不增加无关人物。",
  "product-demo":
    "操作演示：先完整展示商品，再按正确顺序演示使用步骤，穿插功能细节和实际结果。角色用简短说明同步讲清动作与核心卖点。",
  "product-pitch":
    "面对镜头口播：用问题或结论开场，角色依次说道核心卖点、适用人群和使用建议，配合拿取或指向商品，最后自然给出推荐。",
  tvc: "电影感品牌广告：商品亮相、材质细节、真实使用场景、最终英雄镜头逐步推进。角色只说一句克制的品牌主张，声音与画面保持高级简洁。",
  "pain-solution":
    "痛点解决：先呈现具体痛点并让角色说出困扰，再展示商品如何解决，给出清晰的使用结果，最后由角色确认改善并推荐。",
  unboxing:
    "开箱体验：未拆包装开场，依次完成拆封、取出、细节检查和首次试用，角色在关键发现时自然说道真实感受，保留包装与操作音。",
  reaction:
    "首次反应：建立使用前状态，展示第一次接触或使用商品，捕捉角色即时表情与自然反应，再补充结果特写并说出简短评价。",
};

export function createStoryboardTemplates() {
  return storyboardTemplates.map((item, index) => ({
    ...item,
    enabled: index === 0,
  }));
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

export function recommendStoryboardSettings(
  duration,
  videoAspectRatio = "9:16",
  model = defaultImageModel,
) {
  const grid = storyboardGrid(duration, videoAspectRatio);
  const targetRatio = (grid.columns * ratioValue(videoAspectRatio)) / grid.rows;
  const aspectRatio = model.aspectRatios.reduce((best, value) =>
    Math.abs(ratioValue(value) - targetRatio) <
    Math.abs(ratioValue(best) - targetRatio)
      ? value
      : best,
  );
  const preferredResolution = grid.shots === 6 ? "4K" : "2K";
  const resolution = model.resolutions.includes(preferredResolution)
    ? preferredResolution
    : model.resolutions.at(-1) || model.defaultResolution;
  return { ...grid, aspectRatio, resolution };
}

export function buildProductStoryboardPrompt(
  productContext,
  templates,
  data = {},
) {
  const selectedTemplate = templates.length === 1 ? templates[0] : null;
  const totalDuration = Number(data.duration);
  if (selectedTemplate && storyboardDurations.includes(totalDuration)) {
    const segments = storyboardSegmentCount(totalDuration);
    const extra = data.prompt?.trim()
      ? `\n用户补充要求：${data.prompt.trim()}`
      : "";
    const characterReferences = normalizeStoryboardCharacters(data.characterReferences);
    const productCount = Math.max(
      1,
      Math.min(
        MAX_STORYBOARD_REFERENCES - characterReferences.length,
        data.productReferences?.length || 1,
      ),
    );
    const referenceRule = buildImageReferenceRule(characterReferences, productCount);
    const characterRule = characterReferences.length
      ? `${characterReferences.map((_, index) => `角色${index + 1}使用图片${index + 1}`).join("；")}。每个角色保持对应参考图中的身份、人脸、发型、体型和服装一致。`
      : "禁止出现人脸、正脸、侧脸及面部局部；人物只允许出现手部、背影或肩部以下。";
    const segmentRule = Array.from({ length: segments }, (_, index) => {
      const number = index + 1;
      const defaultMode = number === 1 ? "cut" : "extend";
      return `第${number}段（15秒）：输出 segmentIndex=${number}、duration=15、shotCount=${storyboardSegmentShotCount}、continuityMode="${defaultMode}"、plotGoal、openingState、endingState、prompt、videoPrompt。prompt 和 videoPrompt 都必须严格写出镜头1、镜头2、镜头3、镜头4、镜头5、镜头6，六个镜头不能合并或省略；每个镜头标签后必须有至少一句具体的人物动作、地点或商品状态，禁止空镜头或只输出“镜头N：”。${number === 1 ? "第一段独立开场。" : "默认向后延长上一段；如果剧情明确换场则使用 cut。"}`;
    }).join("\n");
    const prefix = `${referenceRule}请为“${selectedTemplate.label}”生成总时长 ${totalDuration} 秒的连续商品短视频方案，拆成 ${segments} 个连续的15秒段落。\n模板要求：${storyboardTemplateRules[selectedTemplate.id]}\n${segmentRule}\n商品资料：\n`;
    const isUgc = selectedTemplate.id === "ugc-seeding";
    const imagePromptRule = isUgc
      ? `图片 prompt 只描述静态画面中的人物动作、商品状态和地点，不要写镜头、景别、构图、运镜、焦点、景深、灯光、调色或广告风格；${ugcPromptOwnershipRule}`
      : "图片 prompt 只描述静态画面：主体动作、商品状态、场景、景别、构图和光线；禁止对白、台词、说话、口型、声音、音效、环境音、旁白和引号内容。";
    const legacySpeechRule = characterReferences.length
      ? isUgc
        ? `UGC种草全程由${characterReferences.length === 1 ? "指定角色" : `角色1至角色${characterReferences.length}`}围绕当前动作、场景和商品体验进行连续、真实的分享，不安排完全无对白的镜头。每个镜头至少包含一句自然口语；多人时明确区分说话人，角色1、角色2、角色3只能对应各自参考图，不得新增人物。人物未露脸或画面为手部、商品特写时，使用对应角色的连续画外音。15秒六个镜头至少安排六句对白，每句简短、口语化、内容不重复，开头镜头立即开口。对白必须使用中文双引号包裹，严格使用格式：${characterReferences.length === 1 ? "她说道：\"内容。\"、他说道：\"内容。\"或他回答：\"内容。\"" : "角色1说道：\"内容。\"、角色2回答：\"内容。\"或角色3说道：\"内容。\""}，禁止写成未加引号的对白，也禁止写“台词：”。`
        : `有人物出镜时必须自然说一句话，使用${characterReferences.length === 1 ? "“她说道：\\\"内容。\\\"”“他说道：\\\"内容。\\\"”或“他回答：\\\"内容。\\\"”" : "“角色1说道：\\\"内容。\\\"”“角色2回答：\\\"内容。\\\"”或“角色3说道：\\\"内容。\\\"”"}，说明口型与声音同步，禁止写“台词：”。`
      : isUgc
        ? "没有注册角色时不得出现人脸；UGC不强制对白，只使用画外音或现场音。"
        : "没有注册角色时不得出现人脸，使用画外音或现场音。";
    const speechRule = buildCharacterSpeechRule(characterReferences.length, isUgc, true);
    const scaleRule =
      "如商品资料包含主体尺寸、外包装尺寸、包装关系或尺度参照，每条 prompt 和 videoPrompt 必须明确保持真实物理尺寸及其与人物、手部和环境的比例；开箱镜头使用外包装尺寸，拿取、使用和展示镜头使用主体尺寸，禁止因特写、透视或运镜改变商品实际大小。";
    const characterTerms = characterReferences.length > 1
      ? `角色1至角色${characterReferences.length}`
      : "指定出镜角色";
    const referenceMappingRule =
      `prompt 和 videoPrompt 的镜头正文不得自行声明或推算图片编号，只使用“${characterTerms}”和“主体商品”，实际参考关系由程序补充。`;
    const videoPromptRule = isUgc
      ? "UGC videoPrompt 每个镜头只描述人物动作、地点、商品状态、自然对白和现场音，不要自行写镜头、景别、运镜、焦点、景深、灯光、调色或广告风格，这些由程序统一追加。"
      : "每个 videoPrompt 镜头写主体动作、场景、景别、单一运镜、光影、角色说话和音效。";
    const suffix = `${extra}\n严格输出一个 JSON 对象，不要 Markdown：{"templateId":"${selectedTemplate.id}","title":"${selectedTemplate.label}","globalScript":"全局脚本","segments":[{"segmentIndex":1,"duration":15,"shotCount":6,"plotGoal":"剧情目标","openingState":"开场状态","endingState":"结束状态","continuityMode":"cut","prompt":"镜头1……镜头2……镜头3……镜头4……镜头5……镜头6……","videoPrompt":"镜头1……镜头2……镜头3……镜头4……镜头5……镜头6……"}]}。segments 必须恰好 ${segments} 条且按顺序。每条 prompt 和 videoPrompt 必须严格包含且只按时间顺序描述镜头1至镜头6，六个镜头分别对应分镜板的六个格子，不能用“ montage ”或一句话概括多个镜头。${imagePromptRule}${scaleRule}${referenceMappingRule}每个 videoPrompt 镜头写主体动作、场景、景别、单一运镜、光影、角色说话和音效。${speechRule}每条 videoPrompt 必须包含现场音或商品操作音，禁止背景音乐、字幕、价格、二维码、水印、乱码和额外 Logo。${characterRule}商品参考图中的商品外观、颜色、材质和包装保持一致。`;
    const controlledSuffix = isUgc
      ? `${suffix.replace("每个 videoPrompt 镜头写主体动作、场景、景别、单一运镜、光影、角色说话和音效。", videoPromptRule)}
UGC覆盖规则：${ugcPromptOwnershipRule} 图片和视频镜头正文只写人物动作、地点、商品状态、自然对白和现场音；不要自行决定镜头、景别、运镜、焦点、景深、灯光、调色或广告风格，以上内容由程序固定控制。`
      : suffix;
    return `${prefix}${productContext.slice(0, Math.max(0, 3000 - prefix.length - controlledSuffix.length))}${controlledSuffix}`;
  }
  const duration = Math.min(15, Math.max(4, Number(data.duration) || 4));
  const ratio = videoAspectRatios.includes(data.videoAspectRatio)
    ? data.videoAspectRatio
    : "9:16";
  const grid = storyboardGrid(duration, ratio);
  const types = templates
    .map(
      (item) =>
        `${item.id}=${item.label}：${item.description}。脚本要求：${storyboardTemplateRules[item.id]}`,
    )
    .join("\n");
  const extra = data.prompt?.trim()
    ? `\n用户补充要求：${data.prompt.trim()}`
    : "";
  const characterReferences = normalizeStoryboardCharacters(data.characterReferences);
  const productCount = Math.max(
    1,
    Math.min(
      getStoryboardProductLimit(characterReferences.length),
      data.productReferences?.length || 1,
    ),
  );
  const referenceRule = buildImageReferenceRule(characterReferences, productCount);
  const hasUgcTemplate = templates.some((item) => item.id === "ugc-seeding");
  const legacySpeechRule = characterReferences.length
    ? '每条 videoPrompt 至少安排指定角色自然说一句与当前动作直接相关的话；对白必须用中文双引号包裹，严格使用格式“她说道：\"内容。\"”“他说道：\"内容。\"”或“他回答：\"内容。\"”，同时说明口型与声音同步；禁止写成“台词：”或“角色说话：”，也禁止写成她说道：内容。'
    : '每条 videoPrompt 至少安排一句与当前画面直接相关的画外音，写成“画外音说道：\"……\"”。';
  const speechRule = buildCharacterSpeechRule(characterReferences.length, hasUgcTemplate);
  const characterRule = characterReferences.length
    ? `${characterReferences.map((_, index) => `图片${index + 1}是角色${index + 1}参考图`).join("，")}。每个有人物的镜头必须保持对应角色的身份、人脸、发型、体型和服装一致。`
    : "所有镜头禁止出现人脸、正脸、侧脸或面部局部；人物只允许出现手部、背影或肩部以下，口播与反应改为画外音、手部动作或商品特写。";
  const imagePromptRule = hasUgcTemplate
    ? `UGC模板的图片 prompt 只描述静态画面中的人物动作、商品状态和地点；${ugcPromptOwnershipRule}`
    : "prompt 只描述静态画面：主体动作、商品状态、场景、景别、构图和光线；禁止对白、台词、说话、口型、声音、音效、环境音、旁白和引号内容。";
  const prefix = `${referenceRule}请为以下每种商品短视频模板同时生成“多格分镜板图片提示词”和“Seedance 2 视频提示词”：\n${types}\n总时长：${duration} 秒；每个模板 ${grid.shots} 个镜头；分镜板采用 ${grid.columns} 列 × ${grid.rows} 行；每个小格保持 ${ratio} 视频画幅。\n商品资料：\n`;
  const characterTerms = characterReferences.length > 1
    ? `角色1至角色${characterReferences.length}`
    : "指定出镜角色";
  const suffix = `${extra}\n严格输出 JSON 数组，格式为 [{"type":"模板ID","title":"模板名称","prompt":"分镜板图片提示词","videoPrompt":"Seedance 2 视频提示词"}]。每个模板必须且只能出现一次，title 必须使用请求中的模板名称，顺序与请求一致。prompt 必须描述 ${grid.shots} 个按时间顺序推进且内容不同的镜头，明确每格的主体动作、景别、场景、构图和光线，整张图是边界清楚、间距统一的专业分镜板。${imagePromptRule}prompt 和 videoPrompt 的镜头正文不得自行声明或推算图片编号，只使用“${characterTerms}”和“主体商品”，实际参考关系由程序补充。videoPrompt 不超过 500 个中文字符；使用“镜头1、镜头2……”依次描述，每个镜头只使用一种运镜，并写明主体动作、场景、景别、光影和自然衔接。${speechRule}每条 videoPrompt 至少用尖括号写一个现场音或商品操作音，例如<包装撕开声>；禁止生成背景音乐。${characterRule}同一商品的外观、颜色、材质、包装和品牌标识必须保持一致；不生成标题、编号、字幕、价格、二维码、水印、乱码或额外 Logo，不虚构商品功能，不解释，不使用 Markdown。`;
  const genericImageRule = `prompt 必须描述 ${grid.shots} 个按时间顺序推进且内容不同的镜头，明确每格的主体动作、景别、场景、构图和光线，整张图是边界清楚、间距统一的专业分镜板。`;
  const genericUgcImageRule = `prompt 必须描述 ${grid.shots} 个按时间顺序推进且内容不同的镜头，只写每格的主体动作、商品状态和地点，整张图是边界清楚、间距统一的专业分镜板。`;
  const genericVideoRule =
    "videoPrompt 不超过 500 个中文字符；使用“镜头1、镜头2……”依次描述，每个镜头只使用一种运镜，并写明主体动作、场景、景别、光影和自然衔接。";
  const genericUgcVideoRule =
    "videoPrompt 不超过 500 个中文字符；使用“镜头1、镜头2……”依次描述，只写人物动作、地点、商品状态、自然对白和现场音。";
  const controlledSuffix = hasUgcTemplate
    ? `${suffix.replace(genericImageRule, genericUgcImageRule).replace(genericVideoRule, genericUgcVideoRule)}
UGC覆盖规则：${ugcPromptOwnershipRule} 图片和视频镜头正文只写人物动作、地点、商品状态、自然对白和现场音；不要自行决定镜头、景别、运镜、焦点、景深、灯光、调色或广告风格，以上内容由程序固定控制。`
    : suffix;
  return `${prefix}${productContext.slice(0, Math.max(0, 3000 - prefix.length - controlledSuffix.length))}${controlledSuffix}`;
}

export function parseProductStoryboardPlan(
  content,
  templates,
  characterReferences = [],
  productReferenceCount = 1,
) {
  const normalizedCharacters = normalizeStoryboardCharacters(characterReferences);
  const normalizedProductCount = Math.max(
    1,
    Math.min(getStoryboardProductLimit(normalizedCharacters.length), Number(productReferenceCount) || 1),
  );
  const source = content
    .trim()
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/\s*```$/, "");
  const start = source.indexOf(source.trimStart().startsWith("{") ? "{" : "[");
  const end = source.lastIndexOf(source.trimEnd().endsWith("}") ? "}" : "]");
  if (start < 0 || end <= start) throw new Error("未生成有效的商品分镜方案");
  let parsed;
  try {
    parsed = JSON.parse(source.slice(start, end + 1));
  } catch {
    throw new Error("商品分镜方案格式异常");
  }
  if (!Array.isArray(parsed)) {
    const segments = Array.isArray(parsed.segments) ? parsed.segments : [];
    const template = templates[0];
    const totalDuration = Number(
      parsed.duration || parsed.totalDuration || segments.length * 15,
    );
    const segmentTotal = storyboardSegmentCount(totalDuration);
    if (
      !template ||
      parsed.templateId !== template.id ||
      segments.length !== segmentTotal
    )
      throw new Error(`商品分镜段落数量应为 ${segmentTotal} 条`);
    const normalizedSegments = segments.map((segment, index) => {
      const segmentIndex = Number(segment?.segmentIndex) || index + 1;
      if (
        segmentIndex !== index + 1 ||
        Number(segment?.duration) !== 15 ||
        Number(segment?.shotCount || storyboardSegmentShotCount) !==
          storyboardSegmentShotCount
      )
        throw new Error("商品分镜段落顺序、时长或镜头数量异常");
      if (!["extend", "cut"].includes(segment?.continuityMode))
        throw new Error("商品分镜衔接方式异常");
      if (
        ![
          segment.plotGoal,
          segment.openingState,
          segment.endingState,
          segment.prompt,
          segment.videoPrompt,
        ].every((value) => typeof value === "string" && value.trim())
      )
        throw new Error("商品分镜段落内容不完整");
      if (
        !hasStoryboardShotLabels(segment.prompt) ||
        !hasStoryboardShotLabels(segment.videoPrompt)
      )
        throw new Error(
          `第${index + 1}段必须包含镜头1至镜头${storyboardSegmentShotCount}`,
        );
      const imagePromptSource = stripImagePromptAudio(segment.prompt);
      const imagePrompt =
        template.id === "ugc-seeding"
          ? ensureUgcImageReferenceRule(
              imagePromptSource,
              normalizedCharacters,
              normalizedProductCount,
            )
          : ensureImageReferenceRule(
              imagePromptSource,
              normalizedCharacters,
              normalizedProductCount,
            );
      const videoPrompt = ensureQuotedDialogue(
        template.id === "ugc-seeding"
          ? ensureUgcVideoReferenceRule(
              normalizeVideoReferenceLabels(
                segment.videoPrompt,
                normalizedCharacters,
                normalizedProductCount,
              ),
              normalizedCharacters,
              normalizedProductCount,
            )
          : ensureVideoReferenceRule(
              normalizeVideoReferenceLabels(
                segment.videoPrompt,
                normalizedCharacters,
                normalizedProductCount,
              ),
              normalizedCharacters,
              normalizedProductCount,
            ),
      );
      return {
        segmentIndex,
        duration: 15,
        shotCount: storyboardSegmentShotCount,
        plotGoal: segment.plotGoal.trim(),
        openingState: segment.openingState.trim(),
        endingState: segment.endingState.trim(),
        continuityMode: index === 0 ? "cut" : segment.continuityMode,
        prompt: `${imagePrompt}\n${normalizedCharacters.length ? "保持所有指定角色身份与外观一致。" : "禁止出现人脸、正脸、侧脸及面部局部。"}\n无文字水印。`,
        videoPrompt: `${videoPrompt}\n${index > 0 && segment.continuityMode === "extend" ? `向后延长视频${index}，延续上一段的主体、场景、光影和运镜。` : ""}\n不生成背景音乐。`,
      };
    });
    return {
      templateId: parsed.templateId,
      title:
        typeof parsed.title === "string" && parsed.title.trim()
          ? parsed.title.trim()
          : template.label,
      globalScript:
        typeof parsed.globalScript === "string"
          ? parsed.globalScript.trim()
          : "",
      totalDuration,
      segments: normalizedSegments,
    };
  }
  if (
    parsed.some(
      (item) =>
        !item || typeof item !== "object" || typeof item.type !== "string",
    )
  )
    throw new Error("商品分镜方案格式异常");
  const expectedTypes = new Set(templates.map((item) => item.id));
  const typeCounts = parsed.reduce(
    (counts, item) => counts.set(item?.type, (counts.get(item?.type) || 0) + 1),
    new Map(),
  );
  const duplicated = [...typeCounts]
    .filter(([, count]) => count > 1)
    .map(([type]) => type);
  if (duplicated.length)
    throw new Error(`商品分镜方案类型重复：${duplicated.join("、")}`);
  const unknown = [...typeCounts.keys()].filter(
    (type) => !expectedTypes.has(type),
  );
  if (unknown.length)
    throw new Error(`商品分镜方案包含未知类型：${unknown.join("、")}`);
  if (parsed.length !== templates.length)
    throw new Error(`商品分镜方案数量应为 ${templates.length} 条`);
  const results = new Map(parsed.map((item) => [item?.type, item]));
  const plans = templates.map((item) => {
    const result = results.get(item.id);
    const videoProductImageLabels = buildVideoProductReferenceLabels(
      normalizedCharacters,
      normalizedProductCount,
    );
    const imageRule = normalizedCharacters.length
      ? "所有镜头保持指定角色的身份、人脸、发型、体型和服装一致。"
      : "禁止出现人脸、正脸、侧脸及面部局部，人物仅可出现手部、背影或肩部以下。";
    const isUgc = item.id === "ugc-seeding";
    const videoRule = normalizedCharacters.length
      ? `${buildVideoCharacterReferenceLabels(normalizedCharacters)}必须保持人物身份与外貌一致；${videoProductImageLabels}为商品参考图。`
      : `全程禁止出现人脸及面部局部；${videoProductImageLabels}为商品参考图。`;
    const promptSource =
      typeof result?.prompt === "string"
        ? stripImagePromptAudio(result.prompt)
        : "";
    const prompt = promptSource
          ? `${isUgc ? ensureUgcImageReferenceRule(promptSource, normalizedCharacters, normalizedProductCount) : ensureImageReferenceRule(promptSource, normalizedCharacters, normalizedProductCount)}\n${imageRule}\n无文字水印。`
      : "";
    return {
      ...item,
      prompt,
      videoPrompt:
        typeof result?.videoPrompt === "string"
          ? `${ensureQuotedDialogue(isUgc ? ensureUgcVideoReferenceRule(normalizeVideoReferenceLabels(result.videoPrompt, normalizedCharacters, normalizedProductCount), normalizedCharacters, normalizedProductCount) : ensureVideoReferenceRule(normalizeVideoReferenceLabels(result.videoPrompt, normalizedCharacters, normalizedProductCount), normalizedCharacters, normalizedProductCount))}\n${videoRule}\n不生成背景音乐。`
          : "",
    };
  });
  const missing = plans
    .filter((item) => !item.prompt || !item.videoPrompt)
    .map((item) => item.label);
  if (missing.length)
    throw new Error(`商品分镜方案缺少：${missing.join("、")}`);
  return plans;
}

function ratioValue(value) {
  const [width, height] = String(value).split(":").map(Number);
  return width > 0 && height > 0 ? width / height : 1;
}

function hasStoryboardShotLabels(value) {
  return Array.from(
    { length: storyboardSegmentShotCount },
    (_, index) => index + 1,
  ).every((number) =>
    new RegExp(`(?:镜头|第)\\s*${number}(?:格)?`).test(value),
  );
}

function stripImagePromptAudio(value) {
  return value
    .replace(
      /(?:说道|说|回答|问道|表示|提到)[：:]?\s*[“"「][^”"」\n]*[”"」]?/g,
      "",
    )
    .replace(
      /(?:说道|回答|问道|表示|提到|说)(?:[：:，,]\s*|\s+)[^。；;\n]*/g,
      "",
    )
    .replace(
      /(?:现场音|环境音|背景音|声音|音效)[：:为]\s*[^。；;\n]*[。；;]?/g,
      "",
    )
    .replace(
      /(?:伴随|传来|发出|听见|保留|有)[^。；;\n]*(?:声音|音效|环境音|现场音|声响|背景音乐|音乐|摩擦声|碰撞声|脚步声|开盖声|鸟鸣|呼吸声|喘息声|底噪)[^。；;\n]*[。；;]?/g,
      "",
    )
    .replace(/(?:禁止|不)生成背景音乐[。；;]?/g, "")
    .replace(/<[^>]*(?:声|音)[^>]*>/g, "")
    .replace(/(^|[，,；;])\s*(?:她|他|角色\s*\d*|人物)(?=[。；;])/g, "$1")
    .replace(/[，、；;]\s*[。；;]/g, "。")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function ensureQuotedDialogue(value) {
  return value.replace(
    /((?:她|他|角色\s*\d*|人物|女性|男性|画外音)(?:说道|说|回答|问道|表示|提到)[：:])\s*(?![“"「])([^。！？!?；;\n]+[。！？!?；;]?)/g,
    (_, prefix, content) => `${prefix}“${content.trim()}”`,
  );
}

const ugcCameraReplacements = [
  [/(?:背景(?:被)?虚化|浅景深)/g, "背景清晰可辨"],
  [/(?:微距(?:镜头|特写)?)/g, "手机1倍主摄近景"],
  [/(?:固定机位|镜头固定)/g, "手持站定"],
  [/(?:缓慢推近|轻推近|推近)/g, "拍摄者自然靠近"],
  [/(?:平滑|稳定)(?:跟拍|运镜)/g, "自然手持跟拍"],
  [/(?:环绕运镜|环绕拍摄)/g, "手持调整角度"],
  [/(?:电影(?:级)?(?:感|调色)|广告质感|商业产品摄影)/g, "iPhone原相机直出"],
  [/(?:居中英雄镜头|居中构图)/g, "自然偏离中心构图"],
];

function normalizeUgcCameraTerms(value) {
  return ugcCameraReplacements.reduce(
    (result, [pattern, replacement]) => result.replace(pattern, replacement),
    value.trim(),
  );
}

function buildImageReferenceRule(characterReferences, productReferenceCount) {
  const characters = normalizeStoryboardCharacters(characterReferences);
  const productCount = Math.max(1, Number(productReferenceCount) || 1);
  const characterLabels = characters
    .map((_, index) => `图片${index + 1}是角色${index + 1}参考图`)
    .join("，");
  const productLabels = Array.from(
    { length: productCount },
    (_, index) => `图片${characters.length + index + 1}`,
  ).join("、");
  return [
    characterLabels ? `${characterLabels}。` : "",
    `${productLabels}是商品参考图。`,
  ].join("");
}

function ensureImageReferenceRule(
  value,
  characterReferences,
  productReferenceCount,
) {
  const prompt = normalizeImageReferenceLabels(value);
  return `${buildImageReferenceRule(characterReferences, productReferenceCount)}\n${prompt}`;
}

function ensureUgcImageReferenceRule(
  value,
  characterReferences,
  productReferenceCount,
) {
  const prompt = normalizeImageReferenceLabels(normalizeUgcCameraTerms(value));
  return `${buildImageReferenceRule(characterReferences, productReferenceCount)}\n${ugcStoryboardImageStyleRule}\n${prompt}`;
}

function normalizeImageReferenceLabels(value) {
  return value
    .trim()
    .replace(
      /(?:参考)?(?:图片|图)\s*\d+\s*(?:是|为)\s*(?:指定)?(?:出镜)?(?:角色\s*\d*|人物)/g,
      "指定出镜角色",
    )
    .replace(
      /参考(?:图片|图)\s*\d+(?=\s*(?:女性|男性|角色\s*\d*|人物|模特))/g,
      "指定出镜角色",
    )
    .replace(
      /(?:参考)?(?:图片|图)\s*\d+(?:\s*[、，]\s*(?:(?:参考)?(?:图片|图)\s*)?\d+)*\s*(?:是|为)\s*商品参考图/g,
      "商品参考图",
    )
    .replace(
      /参考(?:图片|图)\s*\d+(?=\s*(?:商品|产品|包装|瓶身|礼盒))/g,
      "商品参考图",
    );
}

function buildVideoCharacterReferenceLabels(characterReferences) {
  return normalizeStoryboardCharacters(characterReferences)
    .map((_, index) => `图片${index + 2}是角色${index + 1}参考图`)
    .join("，");
}

function buildVideoProductReferenceLabels(characterReferences, productReferenceCount) {
  const characterCount = normalizeStoryboardCharacters(characterReferences).length;
  const productCount = Math.max(1, Number(productReferenceCount) || 1);
  return Array.from(
    { length: productCount },
    (_, index) => `图片${index + characterCount + 2}`,
  ).join("、");
}

function buildVideoReferenceRule(characterReferences, productReferenceCount) {
  const characters = normalizeStoryboardCharacters(characterReferences);
  const productLabels = buildVideoProductReferenceLabels(characters, productReferenceCount);
  const characterLabels = buildVideoCharacterReferenceLabels(characters);
  return [
    "图片1是分镜图",
    characterLabels,
    `${productLabels}是商品参考图`,
  ].filter(Boolean).join("，") + "。";
}

function ensureVideoReferenceRule(
  value,
  characterReferences,
  productReferenceCount,
) {
  const prompt = value.trim();
  const rule = buildVideoReferenceRule(
    characterReferences,
    productReferenceCount,
  );
  return prompt.startsWith(rule) ? prompt : `${rule}\n${prompt}`;
}

function ensureUgcVideoReferenceRule(
  value,
  characterReferences,
  productReferenceCount,
) {
  const prompt = normalizeUgcCameraTerms(value);
  const rule = buildVideoReferenceRule(
    characterReferences,
    productReferenceCount,
  );
  return `${rule}\n${ugcStoryboardVideoStyleRule}\n${prompt.startsWith(rule) ? prompt.slice(rule.length).trim() : prompt}`;
}

function normalizeVideoReferenceLabels(
  value,
  characterReferences,
  productReferenceCount,
) {
  const characterCount = normalizeStoryboardCharacters(characterReferences).length;
  const productCount = Math.max(1, Number(productReferenceCount) || 1);
  const total = characterCount + productCount;
  const rolePattern = /(?:参考)?(?:图片|图)\s*(\d+)\s*(?:女性|男性|角色|人物|模特)/g;
  const productPattern = /(?:参考)?(?:图片|图)\s*\d+\s*(?:商品|产品|包装|瓶身|礼盒)/g;
  const semanticValue = value
    .replace(rolePattern, (_, rawIndex) => {
      const inputIndex = Number(rawIndex);
      const roleIndex = inputIndex <= characterCount
        ? inputIndex
        : inputIndex > productCount
          ? inputIndex - productCount
          : 1;
      return `角色${Math.min(characterCount || 1, Math.max(1, roleIndex))}`;
    })
    .replace(productPattern, "商品");
  const hasStoryboardReference = /(?:参考)?图片\s*1\s*(?:是|为)\s*分镜图/.test(semanticValue);
  const offset = hasStoryboardReference ? 0 : 1;
  const referencePattern = /(?:参考)?(?:图片|图)\s*(\d+)(?!\s*[-－~至])/g;
  return semanticValue.replace(referencePattern, (match, rawIndex) => {
    const inputIndex = Number(rawIndex);
    const outputIndex = inputIndex >= 1 && inputIndex <= total
      ? inputIndex + offset
      : inputIndex;
    return `图片${outputIndex}`;
  });
}

export function refreshStoryboardReferencePrompt(value, kind, characterReferences, productReferenceCount) {
  if (typeof value !== "string" || !value.trim()) return value;
  const lines = value.split("\n");
  const firstLine = lines[0] || "";
  const isReferenceRule = kind === "video"
    ? /(?:参考)?图片\s*1\s*(?:是|为)\s*分镜图/.test(firstLine)
    : /商品参考图/.test(firstLine);
  if (!isReferenceRule) return value;
  const rule = kind === "video"
    ? buildVideoReferenceRule(characterReferences, productReferenceCount)
    : buildImageReferenceRule(characterReferences, productReferenceCount);
  return [rule, ...lines.slice(1)].join("\n");
}
