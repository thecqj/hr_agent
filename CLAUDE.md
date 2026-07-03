# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

智能简历投递系统（HR Agent）— helps job seekers auto-match positions and submit resumes, and helps recruiters evaluate candidates via AI.

**Stack**: FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 + LangGraph (backend), React 19 + TypeScript + Vite + shadcn/ui + Zustand (frontend). LLM via DeepSeek API.

## Commands

### Backend (from `backend/`)

```bash
# Setup
uv venv .venv --python 3.12 && source .venv/bin/activate && uv pip install -r requirements.txt

# Run dev server
uvicorn app.main:app --reload --port 8000

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_auth_api.py -v

# Run a single test by name
pytest tests/test_jobs_api.py::test_create_job -v

# Type check (must pass)
uv run mypy --strict app/

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
```

### Frontend (from `frontend/`)

```bash
npm install
npm run dev        # Vite dev server
npm run build      # tsc + vite build
npm run lint       # ESLint
```

### Prerequisites

- PostgreSQL 18 + pgvector extension
- Database: `jobboard` (dev), `jobboard_test` (test), user `app:password`
- Copy `backend/.env.example` → `backend/.env` and fill in `DEEPSEEK_API_KEY`


## Claude Code

- 每次启动新任务，**必须** 先阅读 `skeleton.md`，以构建系统结构和模块边界的思维导图。
- 探索代码时，非必要不深度阅读代码，应信任 `skeleton.md` 中可见的函数名或文档字符串；深度阅读仅限于设计规范直接涉及的特定模块、类或函数。
- 每当任务完成后：
    - 若涉及 Python 代码的变动，运行 `uv run mypy --strict app/` 验证代码的类型正确性，未通过验证修正代码直至通过检查。 
    - 当代码有结构性的变更后，更新 `skeleton.md`。