## Project Overview
- 智能简历投递系统（HR Agent），帮助求职者自动匹配岗位并投递简历
- 技术栈：FastAPI + SQLAlchemy 2.0 + Pydantic v2 (后端), Next.js + TypeScript (前端)
- 当前阶段：重构前端页面 UI

## Architecture
- backend/        - 后端代码
- frontend/       - 前端代码

## Python Code Conventions
* **Strict Type Hints**: Every function/method must have explicit parameter and return type hints (use `-> None` if empty).
* **Mypy Strict**: Code must pass `mypy --strict`. Use modern syntax (e.g., `int | None`, `list[str]`). Always run `mypy --strict` to validate the typed correctness of the generated code after implementation.
* **Layer Separation (Crucial)**:
  * **Database (ORM)**: Use modern SQLAlchemy 2.0 type-annotated style (e.g., `Mapped[str] = mapped_column(...)`).
  * **Data Validation (DTO/API)**: Use `Pydantic (v2)` exclusively for request/response schemas, API boundaries, and configuration.

## Commands
- 类型检查: `cd backend && uv run mypy --strict app/`
- 运行测试: `cd backend && uv run pytest tests/ -v`