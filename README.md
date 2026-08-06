# AI Short Drama

AI 短剧画布项目：Vue 3 前端 + FastAPI 后端，使用 PostgreSQL、Redis/ARQ、ToAPIs 和 OSS。

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
npm run build
```

健康检查：<http://127.0.0.1:8000/api/health>
