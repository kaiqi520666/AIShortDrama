# 界面双语文案清单与修改范围

盘点日期：2026-09-08。

状态：实施中，尚未全部完成。已接入语言基础设施、首页/登录注册、工作台列表、个人中心、后台 12 个页面及部分公共组件。完整进度见第 9 节；下列范围不代表全部已修改。

## 1. 已确认规则

- 仅支持简体中文 `zh-CN`、印尼语 `id`，覆盖用户端和管理后台。
- 首次访问按浏览器语言偏好列表依次匹配，中文变体统一匹配简体中文，印尼语变体匹配 `id`；全部不支持时使用印尼语。
- 用户手动选择保存在当前浏览器，优先于浏览器语言；同源用户端、后台共用，不做账号跨设备同步。
- 首页、登录/注册页和应用顶部提供同一个可复用语言选择组件。
- 切换语言不刷新、不跳转、不清空表单、不重启任务、不重新生成内容。
- 日期与数字的展示格式跟随语言，时区、币种、金额、积分计算和接口值不变。
- 支付地区与界面语言独立；本期不增加支付地区字段，不接印尼支付，不调整现有支付渠道。
- 提示词语言后续独立实现。全部生成文本及对白、旁白、字幕的语言属于后续阶段，只影响新生成内容。
- 本期不扩展公告等运营内容的双语编辑。

## 2. 文案清单

以下是按功能整理的文案项和来源，不是完成去重后的逐条中印翻译字典。实施时按语义提取 key，并逐项补齐两种语言；不能把所有包含中文的行直接翻译。

| 建议命名空间 | 文案项 / 已定位示例 | 来源 |
| --- | --- | --- |
| `common` | 确认、取消、保存、关闭、删除、编辑、清除、搜索、刷新、重新加载、操作、详情 | 公共 UI、全局交互、各页面 |
| `navigation` | 工作台、账户概览、个人中心、积分充值、生成记录、积分明细、计费标准、退出登录 | DashboardShell、账户菜单、布局 |
| `language` | 语言、简体中文、Bahasa Indonesia | 待新增选择组件 |
| `theme` | 主题及明暗模式选项、图标提示 | AppThemeSwitch |
| `home` | 首页导航、介绍、入口按钮、图像替代文字；已有英文装饰性标题也需纳入 | HomeView |
| `auth` | 登录、注册、用户名、邮箱、密码、验证码、显示/隐藏密码、人机验证、提交中、输入校验 | LoginView、RegisterView、AuthInputField、TurnstileWidget |
| `workspace` | 创建工作台、类型选择、名称、重命名、删除确认、加载与保存状态、空列表 | WorkspaceHome、WorkspaceCreateDialog、workspaces store |
| `account` | 可用积分、冻结积分、累计消耗、今日消耗、注册时间、安全设置、原密码、新密码、邀请 | AccountView、AppCreditBalance、AppAccountMenu |
| `billing` | 消费类型、基础积分、赠送积分、到账积分、计费单位、默认规格、筛选与分页 | BillingStandardsPanel、CreditLedgerPanel |
| `recharge` | 充值金额、阶梯赠送、订单号、待支付、已支付、失败、支付时间、订单查询提示 | RechargeView、后台充值页面 |
| `history` | 生成类型、任务状态、创建时间、模型、规格、失败提示、预览与下载 | GenerationHistoryView、AdminTasksView |
| `canvas` | 节点菜单、节点类型、工具栏、连线限制、分组、复制粘贴、上传、自动保存、快捷键说明 | 画布视图、组件、配置、stores、composables |
| `generation` | 文本/图片/视频/音频、模型、画幅、分辨率、时长、参考素材、已启用/已禁用、生成中、重试 | GenerationPanel、生成设置组件、模型配置 |
| `product` | 商品资料字段、商品创作步骤、商品出图、图种分组、UGC 种草、短剧带货、分镜衔接 | Product 系列组件、商品配置 |
| `apparel` | 服饰识别、服饰穿搭、单品属性、模特/场景来源、试穿与展示操作 | Apparel / Outfit 系列组件及配置 |
| `assets` | 素材库、系统模特、系统角色、系统服饰、类型筛选、选择、上传、预览、下载、无素材 | AssetDrawer、AppAssetPickerModal、媒体公共组件 |
| `admin.overview` | 近 1/7/30 天、已支付充值、调用次数、成功率、队列积压 | AdminOverviewView |
| `admin.users` | 用户管理、普通用户、管理员、启用、停用、积分调整、操作原因 | AdminUsersView |
| `admin.models` | 模型管理、展示名称、默认模型、模型 ID、状态、更新确认 | AdminModelsView |
| `admin.templates` | 出图设置、电商模板、服饰模板、编辑器标签、保存、校验、版本、更新确认 | AdminTemplatesView |
| `admin.assets` | 素材类型、标签、排序、上架/下架、虚拟人像、版权说明 | AdminReferenceAssetsView |
| `admin.finance` | 积分策略、充值政策、充值阶梯、模型计费、成本价、倍率、起充金额、赠送比例 | 四个财务配置页面及订单页 |
| `admin.audits` | 操作审计、管理员、操作、目标、原因、时间、变更 | AdminAuditsView |
| `errors` | 请求失败、登录失败、账户信息加载失败、参数无效、积分不足、上传失败、生成超时、服务不可用 | apiError、API、后端异常、轮询及流式返回 |
| `format` | 日期月份、星期、小时、分钟、今天、百分比、计数、时间单位、金额显示 | AppDateTime、账户/后台页面及公共面板 |

所有范围都包含 `title`、`placeholder`、`aria-label`、`alt`、表头、菜单、状态、确认文案和校验消息，不只处理可见正文。

## 3. 拟新增文件

| 文件 | 职责 |
| --- | --- |
| `frontend/src/i18n/index.js` | 单一 i18n 实例、初始语言解析、持久化切换、同步 HTML lang、共用日期/数字格式 |
| `frontend/src/i18n/locales/zh-CN.json` | 简体中文文案，按上述命名空间组织 |
| `frontend/src/i18n/locales/id.json` | 印尼语文案，与中文 key 和插值参数对齐 |
| `frontend/src/components/ui/AppLanguageSelect.vue` | 复用现有菜单/按钮，实现语言切换，不新增 UI 库 |
| `frontend/src/i18n/index.test.js` | 语言匹配、回退、持久化、字典一致性、插值与格式定向测试 |

先用两份字典，不引入远程翻译服务、翻译管理平台或额外状态管理层。

## 4. 前端修改范围

以下路径相对于 `frontend/`。同组文件只修改展示文案及必要的响应式绑定，不借机重构业务。

### 4.1 初始化、入口与共享 UI

- `package.json`、`package-lock.json`：本次已安装依赖。
- `index.html`、`src/main.js`：语言初始化与插件挂载；品牌标题保留 Mooncut。
- `src/layouts/DashboardLayout.vue`。
- `src/components/dashboard/AppDashboardShell.vue`。
- `src/components/auth/AuthFormShell.vue`、`AuthInputField.vue`、`TurnstileWidget.vue`。
- `src/components/ui/AppHeaderAccountControls.vue`、`AppThemeSwitch.vue`、`AppBrand.vue`、`AppCreditBalance.vue`。
- `src/components/ui/AppDateTime.vue`、`AppDataTable.vue`、`AppMediaPreview.vue`、`AppModal.vue`、`AppSelect.vue`。
- `src/components/global/GlobalToast.vue`；其余 GlobalConfirm / GlobalPrompt / GlobalLoading 只在需要响应语言切换时调整，优先从共用状态源解决。
- `src/composables/useGlobalUI.js`、`useGlobalLoading.js`、`useAdminMutation.js`。

现有前后台路由共用 DashboardLayout；无需复制后台语言系统。`src/router/index.js` 的路由名和路径不翻译，当前不列为必须修改文件。

### 4.2 用户页面与账户公共组件

- `src/views/public/HomeView.vue`。
- `src/views/auth/LoginView.vue`、`RegisterView.vue`。
- `src/views/dashboard/WorkspaceHome.vue`、`AccountView.vue`、`RechargeView.vue`、`GenerationHistoryView.vue`。
- `src/components/workspace/WorkspaceCreateDialog.vue`。
- `src/components/account/AppAccountMenu.vue`、`BillingStandardsPanel.vue`、`CreditLedgerPanel.vue`。
- `src/components/assets/AppAssetPickerModal.vue`。

`BillingStandardsView.vue`、`CreditLedgerView.vue` 是公共面板的入口，优先改公共面板，不为壳页面重复添加翻译逻辑。

### 4.3 管理后台：12 个页面

- `src/views/admin/AdminOverviewView.vue`、`AdminUsersView.vue`、`AdminModelsView.vue`。
- `src/views/admin/AdminTemplatesView.vue`、`AdminReferenceAssetsView.vue`。
- `src/views/admin/AdminTasksView.vue`、`AdminAuditsView.vue`。
- `src/views/admin/AdminCreditPolicyView.vue`、`AdminRechargePolicyView.vue`。
- `src/views/admin/AdminRechargeTiersView.vue`、`AdminRechargeOrdersView.vue`、`AdminPricingView.vue`。
- 公共弹窗：`src/components/admin/AdminDialog.vue`。

### 4.4 画布视图与组件

- `src/views/canvas/CanvasView.vue`、`WorkspaceCanvasView.vue`。
- `src/views/canvas/useWorkspaceCanvasSession.js`、`useCanvasGrouping.js`、`useCanvasDropUpload.js`。
- `src/components/canvas/CanvasHeader.vue`、`NodeCreateMenu.vue`、`ShortcutPanel.vue`、`AssetDrawer.vue`。
- `src/components/canvas/MediaNode.vue`、`StructuredNodeShell.vue`、`GenerationPanel.vue`、`PromptReferenceEditor.vue`。
- `src/components/canvas/TextGenerationControls.vue`、`ImageGenerationControls.vue`、`AudioGenerationSettings.vue`、`VideoGenerationSettings.vue`。
- `src/components/canvas/ProductNode.vue`、`ProductCreationPanel.vue`、`ProductVisualNode.vue`、`ProductVisualPanel.vue`、`ProductStoryboardNode.vue`、`ProductStoryboardPanel.vue`、`ProductWorkflowSteps.vue`。
- `src/components/canvas/ApparelNode.vue`、`ApparelPanel.vue`、`OutfitNode.vue`、`OutfitPanel.vue`。
- `src/components/canvas/WorldNode.vue`、`WorldCreationPanel.vue`、`CharacterNode.vue`、`CharacterCreationPanel.vue`、`CharacterProfilePanel.vue`、`CharacterVisualPanel.vue`。
- `src/components/canvas/useGenerationContext.js`、`useMediaNodeAsset.js`。

### 4.5 展示配置与错误来源

- `src/config/imageModels.js`、`videoModels.js`、`audioModels.js`、`modelCapabilitiesValidation.js`。
- `src/config/canvas/nodeCatalog.js`、`nodeRegistry.js`、`nodePacks.js`、`connectionRules.js`、`ecommerceWorkflows.js`。
- `src/config/canvas/contentTemplates.js`、`productVisual.js`、`productStoryboard.js`、`ecommerce.js`、`apparel.js`、`outfit.js`、`character.js`、`drama.js`：仅界面标签、选项展示和用户错误，保留提示词及解析协议。
- `src/stores/auth.js`、`workspaces.js`、`contentTemplates.js`、`modelCapabilities.js`、`canvas.js`、`canvasBusinessActions.js`。
- `src/stores/canvasBusiness/sharedActions.js`、`productActions.js`、`apparelActions.js`、`dramaActions.js`：只修改操作反馈，不改生成要求。
- `src/composables/useCanvasAutosave.js`、`useCanvasClipboard.js`、`useStreamingTextTask.js`。
- `src/services/generationAdapters.js`、`generationPolling.js`。
- `src/api/generations.js`、`reversals.js`、`client.js` 与 `src/utils/apiError.js`：统一错误显示，并保留结构化错误信息。
- `src/utils/download.js`、`mediaFiles.js`。

### 4.6 按验收结果调整，不预先扩大范围

- `src/styles/components/`、`src/styles/pages/`：仅在印尼语文本实际溢出时调整相关样式，不改整体设计。
- 上述模块现有 `*.test.js`：仅更新受影响的文案断言或导入初始化；优先保留业务测试。
- `src/data/demoCanvas.js`：先区分首页示例的界面文字与示例内容，只本地化必要的界面部分。
- `src/config/canvas/migrations.js`：旧数据兼容逻辑不因翻译重写；确有展示依赖再单独处理。

## 5. 后端范围与实施约束

仅装前端 i18n 无法覆盖后端返回的中文。当前 `fail()` 统一返回 `code: 1` 和 `message`，前端 `getApiErrorMessage()` 直接显示该消息，无法稳定区分具体业务错误。

建议保留现有成功/失败协议，增量补充稳定错误标识及必要参数，由前端字典负责显示，不使用中文文本正则或字符串替换推断错误含义。

### 必须处理的基础链路

- `backend/app/core/errors.py`：业务异常携带错误标识。
- `backend/app/schemas/response.py`：失败响应增加可选错误标识/参数，不改变现有 `code` 含义。
- `backend/app/main.py`：参数校验、业务异常和服务异常统一输出。
- `backend/app/api/routes/account.py`：任务类型、规格等展示项按已有稳定字段映射；缺失稳定标识时补充，前端不依赖中文标签。

### 按实际错误出口定向修改

- 路由：`backend/app/api/routes/` 下的 `auth.py`、`workspaces.py`、`assets.py`、`uploads.py`、`generations.py`、`reversals.py`、`recharge.py`、`credits.py`、`reference_library.py`、`admin.py`、`admin_reference_assets.py`、`content_templates.py`。
- 服务：`backend/app/services/` 下认证、上传、计费、充值、后台配置、模板校验与生成相关模块；只处理会到达界面的错误/展示值，不翻译内部日志。
- 异步链路：`backend/app/services/text_generation.py`、`generation_tasks.py`，以及 `backend/app/workers/generation.py`、`image_generation.py`、`video_generation.py`、`audio_generation.py`。流式错误和任务失败结果需要与普通 API 错误一致。
- 对应后端定向测试：验证新增错误字段兼容现有调用，且计费与任务状态行为不变。

异步任务错误已经持久化，如何保存错误标识需要实施前核对任务数据结构。暂不把数据库迁移列为已批准修改；若确有必要，先列出迁移范围。旧错误记录不批量改写，不承诺能把既有第三方诊断原文全部翻译。

## 6. 内容与界面隔离

1. **生成指令不动**：例如 nodeCatalog 中“生成结构化中文提示词”属于生成要求，不因界面切到印尼语而修改；界面中说明当前生成语言的标签应如实翻译，不能误示为已支持印尼语生成。
2. **选项显示和值分离**：题材、性别、角色类型等可能以中文保存或参与生成。只翻译显示 label，不替换持久化值、比较条件或发给模型的值。
3. **模板按稳定 ID 显示**：用模板 key、图种 ID、衔接方式 ID 映射内置双语显示文案，不修改服务端用于生成的原配置。
4. **管理员自定义值保留**：已编辑的模板名称/说明、模型展示名称、素材标签等属于运营数据，不能被内置译文静默覆盖。内置默认文案与自定义内容要区分；编辑表单保留真实原值，不把显示译文回写模板。
5. **不改历史内容**：工作台名、节点标题、素材名、提示词和生成结果不在切换时回写。节点类型等固定标签正常翻译，用户命名保持原文。
6. **技术标识不动**：JSON key、模型 ID、模板 key、参考素材标记、文件扩展名、画幅值、路由、快捷键组合、品牌名不翻译。
7. **支付事实不变**：现有人民币金额和渠道继续按真实状态展示，切换印尼语不把人民币符号改成印尼盾，不开放新的支付方式。
8. **诊断与业务反馈分开**：常见业务错误本地化；后台请求快照、原始诊断、审计原因等真实记录保留原文。
9. **邮件暂不纳入**：当前批准的是界面多语言，验证码邮件正文及第三方支付/人机验证页面由不同系统控制，需要单独核对后再扩展。

## 7. 推荐实施批次与验收

| 批次 | 修改内容 | 最小验收 |
| --- | --- | --- |
| A | i18n 初始化、语言选择、公共 UI、首页与登录注册 | 浏览器语言匹配、回退、刷新保持、中文/印尼语切换 |
| B | 用户中心、工作台、后台 12 页、日期数字 | 导航/表头/选项响应切换，金额币种与时区不变 |
| C | 画布、生成设置、内置模板展示 | 输入与任务不中断，切换前后画布数据和请求内容不变 |
| D | 后端业务错误、流式/轮询反馈与遗漏清理 | 用户错误可读，接口兼容，原始诊断保留 |

- 双语字典 key 和插值参数一致；不能显示翻译 key 或 undefined。
- 静态菜单和列定义要保持响应式，避免初始化时调用一次翻译后永久固定语言。
- 中文扫描只作为遗漏线索，不能要求所有中文消失；用户内容、模板原文和历史记录是合法保留项。
- 桌面和移动端检查长标签、按钮、表格、菜单、日期选择器和画布面板不重叠。
- 本次仅依赖安装与清单整理：验证依赖树、最小双语运行示例和生产构建，不调用收费生成或真实支付。

## 8. 初次盘点变更

- `frontend/package.json`：新增 `vue-i18n` 依赖。
- `frontend/package-lock.json`：锁定依赖；保留已有依赖记录，避免无关升级。
- `docs/i18n-scope.md`：本文档。

未修改应用业务代码、生成模板、支付配置或数据库；未提交 Git。工作区已有的 AGENTS.md、后端依赖文件修改不属于本次工作。

## 9. 实施进度（2026-09-08）

### 已接入

- `i18n/index.js` 和两份字典：浏览器偏好匹配、默认印尼语、手动选择持久化、HTML lang 同步、日期与数字格式函数。
- 浏览器自动匹配不会自动写入手动偏好；存储被禁用时仍能初始化和切换。
- 单一 `AppLanguageSelect` 复用现有 `AppSelect`，接入首页、登录注册和共用应用顶部；极窄屏使用图标入口。
- 首页、登录注册、工作台列表/创建弹窗、个人中心、导航、账户菜单、主题菜单、积分余额。
- 公共分页、日期选择、后台弹窗、默认确认/输入弹窗按钮、后台二次确认文字。
- 后台 12 个页面的固定界面文案、选项标签、操作反馈；模板的全部 5 个子类型均已接入。
- 选项和列定义使用响应式翻译；现有业务 ID、表单值、模板指令、管理员自定义名称与审计快照保留原文。
- 财务页面的显示格式随语言调整，币种仍明确为 CNY，计费运算、请求金额和订单行为不变。
- 画布 C 批：11 类节点及生成面板、节点菜单、快捷键、分组操作、保存状态、生成参数、素材抽屉和素材选择器的固定文案已接入简体中文/印尼语。
- 内置题材、角色选项只翻译显示标签；内置图种和分镜模板按 ID 与默认文案同时匹配，自定义名称/说明原样显示，不改模板或节点保存值。
- 上传、复制粘贴、连线校验、生成前校验、解析失败、流式/轮询的本地兜底提示已翻译；接口返回的原始错误不做中文文本匹配或替换。
- 引用编辑器只更新可见引用标签，不改 prompt、promptParts、引用 ID；图片预览、关闭弹窗和系统通知入口同步接入翻译。
- 根据截图修正画布顶部长文案、面板滚动、生成操作栏换行和移动端快捷键布局，不改节点位置或画布缩放数据。

### 尚未完成

- 用户端 `RechargeView.vue`、`GenerationHistoryView.vue`、`BillingStandardsPanel.vue`、`CreditLedgerPanel.vue`。
- 其余公共媒体/全局反馈组件及既有中文错误来源；历史节点中已保存的错误字符串不批量改写。
- 后端复杂模板配置、部分后台管理限制等细分错误目前使用按 HTTP 状态翻译的通用提示，后续可继续补充专用错误标识。
- 真实素材注册、第三方异步任务的完整状态联调；本批覆盖现有 active/processing/failed/unregistered 展示。
- 全站残留扫描、真实生成端到端验收和印尼语母语校对。

### 已验证

- 5 个定向测试文件、26 项测试通过，包含语言匹配、回退、字典 key/参数一致、偏好保存、存储不可用、数字格式及原有账户/工作台测试。
- 前端生产构建通过，`git diff --check` 无空白错误（存在仓库既有 LF/CRLF 提示）。
- 使用模拟 API 的浏览器检查：11 个后台入口在 320/390/1440px 共 33 次检查，无页面运行异常和页面级横向溢出。
- 日期选择器的印尼语星期显示检查通过。
- 5 个模板类型切换中印语言后，所有 textarea 原值保持不变，未触发 POST/PUT 写请求。
- 登录页语言切换保留邮箱输入，刷新后保留已选语言。
- 已查看登录、首页和后台移动端截图；尚未完成所有页面和状态的视觉验收。
- 画布 C 批新增验收：37 个相关测试文件、170 项测试通过，生产构建通过，`git diff --check` 通过。
- 11 类节点在模拟 API 中逐项切换中印语言，序列化画布数据前后一致；单元测试另验证世界观/角色提示词、视频请求及节点默认数据不受界面语言影响。
- 通过真实语言选择控件切换引用标签：`图片1` / `Gambar1` 正常更新，原始提示词与引用数据不变，切换未触发画布保存请求。
- 检查 320/390/1440px 画布、双语节点菜单、素材抽屉及移动端快捷键截图；浏览器无运行错误/警告，顶部控件无视口裁切。

未调用真实支付或收费生成，未部署、未提交 Git。本轮是部分实施，不应据此认定全站双语已验收。

### D 批：后端错误翻译

- 普通失败响应保留原 `code`、`message`、`data` 和 HTTP 状态，新增 `error_key` 与 `error_params`；前端只按稳定标识翻译，不根据中文消息推断含义。
- `ApiError` 支持显式标识，包装异常时从 cause 保留底层标识和插值参数；无专用标识时按状态码兜底。参数校验、框架 404/405、来源校验和未处理异常也走同一协议。
- 登录凭据、账号禁用/重复、验证码、密码修改、积分不足、模型停用、画布冲突、模板更新/停用、上传校验和充值校验已提供双语反馈；金额参数保持 CNY。
- Axios 统一拦截 HTTP-200 的 `code: 1` 失败响应，保留完整响应对象；HTTP 错误、网络异常、超时由共用函数处理。登录刷新、验证码状态字段保留。
- 文本生成和反推的流式错误事件携带相同字段，delta/生成指令保持原样。
- 轮询、用户生成历史和后台任务详情按失败/取消/超时状态显示本地化提示。标识在任务响应阶段提供，不新增数据库字段，不改写历史错误、结果或诊断。
- 后台任务详情的用户反馈本地化，原始错误信息及诊断仍在折叠诊断区域展示；直接查询的上游诊断原文保留。
- 未知或旧接口的原始消息不直接显示为用户错误，使用双语通用提示。复杂细分校验尚未全部逐条翻译；第三方原文不承诺逐字翻译。
- 验证：后端 10 个定向测试文件、57 项测试通过；前端 17 个定向测试文件、80 项测试通过；前端构建与差异空白检查通过。
- 模拟 API 浏览器验证：中文/印尼语登录失败提示正确，邮箱及密码输入不丢失；1440px/390px 无页面横向溢出或运行错误。仅模拟登录请求，无真实生成、支付或业务数据写入。

本批未新增依赖、未迁移数据库、未更改计费/退款/任务状态流转、未部署或提交 Git。
