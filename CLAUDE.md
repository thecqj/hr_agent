## Project Overview
- 智能简历投递系统（HR Agent），帮助求职者自动匹配岗位并投递简历
- 技术栈：FastAPI + SQLAlchemy 2.0 + Pydantic v2 (后端), Next.js + TypeScript (前端)
- 当前阶段：HR-Agent

## Repository Architecture & Exploration Protocols

### 1. Global Navigation: `skeleton.md`
- **Purpose**: `skeleton.md` is the source of truth for the project's overall architecture, file layout, and major API signatures.
- **First Action**: Every time you start a new task or transition to the `writing-plans` stage, you **MUST** read `skeleton.md` first to build a mental map of the system's structure and module boundaries.
- **Maintenance**: After implementing changes, ensure relevant updates are made to `skeleton.md` if any public interfaces, classes, or folder structures were modified.

### 2. Precision Exploration Rules (Context Discipline)
When you are in the `writing-plans` (Detailed Design) stage, you **MUST** read relevant source code to ensure technical precision, but you must do so with aggressive context discipline under the following rules:
  
- **Targeted Domain Reading (Laser Focus)**:
  - Restrict deep reading strictly to the specific module, class, or functions directly targeted by the design spec.
  - If a file is over 500 lines, use specific line ranges or grep for exact definitions, rather than reading the whole file blindly.

- **Dependency Analysis (Conditional Traversal)**:
  - **Strongly Coupled**: If the target module heavily depends on or interacts with another component, you may read that dependency's interface/header.
  - **Weakly Coupled / Utility**: If it just uses general utilities or peripheral modules, **DO NOT** read their implementations. Trust their function names or docstrings visible in `skeleton.md`.

- **Anti-Greed Guardrail**:
  - Never execute blanket `grep` or `find` commands that scan the whole project or massive subdirectories.
  - Every file you open during the planning phase must have an explicit, justified reason in your inner monologue (e.g., "Reading X to check Y's method signature").


## Python Code Conventions
* **Strict Type Hints**: Every function/method must have explicit parameter and return type hints (use `-> None` if empty).
* **Mypy Strict**: Code must pass `mypy --strict`. Use modern syntax (e.g., `int | None`, `list[str]`). Always run `mypy --strict` to validate the typed correctness of the generated code after implementation.
* **Layer Separation (Crucial)**:
  * **Database (ORM)**: Use modern SQLAlchemy 2.0 type-annotated style (e.g., `Mapped[str] = mapped_column(...)`).
  * **Data Validation (DTO/API)**: Use `Pydantic (v2)` exclusively for request/response schemas, API boundaries, and configuration.


## Commands
- 后端环境: `cd backend && uv venv --python 3.12 && source .venv/bin/activate && uv pip install -r requirements.txt`
- 前端环境: `cd frontend && npm install && npm run dev`
- 类型检查: `cd backend && uv run mypy --strict app/`
- 运行测试: `cd backend && uv run pytest tests/ -v`