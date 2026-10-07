# AI Short Drama

AI 内容创作画布项目，支持通用画布和电商画布：Vue 3 前端 + FastAPI 后端，使用 PostgreSQL、Redis/ARQ、ToAPIs 和 OSS。

## 环境要求

- Docker Desktop
- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+

## 首次配置

在项目根目录执行：

```powershell
Copy-Item backend\.env.example backend\.env
```

然后填写 `backend\.env` 中的 PostgreSQL、Redis、OSS 和 ToAPIs 配置。`.env` 已被 Git 忽略，不要提交密钥。

现有 Docker 容器需要提供：

- PostgreSQL：`127.0.0.1:5432`
- Redis：`127.0.0.1:6379`
- 数据库：`ai_short_drama`

如容器未运行：

```powershell
docker start deploy-db-1 deploy-redis-1
```

## 启动后端

打开三个 PowerShell 窗口，分别执行。

### API 服务

```powershell
Set-Location backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### ARQ Worker

```powershell
Set-Location backend
uv run arq app.workers.settings.WorkerSettings
```

### 前端

```powershell
Set-Location frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

前端通过 Vite `/api` 代理访问 `http://127.0.0.1:8000`。如果端口 `5173` 被占用，Vite 会自动切换端口，使用终端输出的地址访问。

## 验证

先创建与业务库隔离的测试数据库，并在 `backend/.env` 配置 `TEST_DATABASE_URL`。数据库名称必须包含 `test`，pytest 会在运行前重建该数据库的 `public` schema：

```sql
CREATE DATABASE ai_short_drama_test;
```

```powershell
Set-Location backend
uv run pytest
uv run ruff check .
```

```powershell
Set-Location frontend
npm run test -- --run
npm run build
```

健康检查：<http://127.0.0.1:8000/api/health>

## 任务恢复与人工核查

生成任务的状态和账务由 `backend/app/services/task_lifecycle.py` 统一处理。Worker 先领取租约、保存提交意图，再调用 Provider；已有上游任务 ID 时只查询，已有完整结果时重放结果。提交结果不明确时，按客户端请求 ID 查询；无法确认则进入 `needs_review`，保留冻结积分，自动执行不会再次提交或退款。

结果存储、结算和查询故障最多自动恢复 4 次，超过上限进入 `needs_review`。后台“生成任务”页面可筛选并处理待核查任务，所有操作必须填写原因，并留下审计记录：

- 恢复：图片/视频可补充已确认的上游任务 ID；同步音频只能恢复已经保存的结果。
- 确认失败或取消：同一事务结束任务、退款并记录审计；重复处理返回冲突。
- 流式文本任务不能恢复中断的流，可人工确认失败或取消。

充值订单仅允许 `pending -> paid`。`failed` 订单不能再次结算；成功通知仍保存处理结果供核查，不发放积分。主动查询和支付回调复用同一结算服务，交易号和 ledger 唯一约束防止重复入账。

## 迁移与 CI

升级至 `z3c4d5e6f7a8` 会添加提交标识、结果缓存、Worker 租约和恢复计数，并补充上游任务唯一约束。发现同一 Provider、媒体类型下的重复任务 ID 时，迁移会列出相关任务并停止，需先人工核查；不会删除历史任务。部署前应停止旧 Worker，迁移成功后用同一版本镜像启动 backend 和 worker，避免旧 Worker 绕过新恢复流程。

迁移后，在 `backend` 目录核验数据库版本与约束：

```powershell
uv run python scripts/check_migrations.py
```

GitHub Actions 分别执行后端 PostgreSQL/Redis 集成测试、前端测试与构建、能力契约校验、空库迁移和生产 Compose 启动检查。CI 显式创建 `aisd_test`；测试库和迁移检查库独立。`deploy/ci-smoke.sh` 使用临时配置及独立命名卷，验证迁移、API、Worker 心跳、前端与代理健康，不读取生产 `.env`。

生产更新使用项目部署脚本，要求工作区干净且代码已提交。本机 Docker 不可用时，可在服务器构建当前提交的镜像：

```powershell
& '.codex\skills\ai-short-drama-deploy\scripts\update.ps1' -Mode Deploy -BuildOnServer
```

脚本先运行后端和前端测试，再构建镜像、备份数据库、停止旧应用并迁移，最后检查迁移版本、容器、Worker 心跳和公网健康。服务器构建仅上传已提交的 `backend`、`frontend` 源码；生产 `.env` 仅更新两个镜像标签，其他部署配置保持现有值。失败时回退旧镜像，不反向迁移数据库。
