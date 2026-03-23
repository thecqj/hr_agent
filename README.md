# hr-agent

## 多人协作开发指南

本文档面向新加入项目的开发者，说明如何拉取仓库并搭建与团队一致的 uv 开发环境。

---

## 前置要求

- Git
- [uv](https://docs.astral.sh/uv/)（Python 包管理器）

安装 uv（若尚未安装）：

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows（PowerShell）
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

安装完成后重启终端，确认安装成功：

```bash
uv --version
```

---

## 1. 拉取仓库

```bash
git clone <仓库地址>
cd hr_agent
```

---

## 2. 创建并同步虚拟环境

uv 会读取项目根目录下的 `pyproject.toml`，自动创建虚拟环境并安装所有依赖：

```bash
uv sync
```

执行后 uv 会在项目目录下生成 `.venv/` 虚拟环境，并生成（或更新） `uv.lock` 锁文件，确保所有人使用完全一致的依赖版本。

---

## 3. 运行项目

```bash
uv run python main.py
```

或先激活虚拟环境再直接使用 Python：

```bash
# macOS / Linux
source .venv/bin/activate

# Windows（PowerShell）
.venv\Scripts\Activate.ps1

python main.py
```

---

## 4. 协作流程：拉取最新代码后同步依赖

每次从远端拉取代码后，若 `pyproject.toml` 或 `uv.lock` 有变动，都需要重新同步依赖：

```bash
git pull
uv sync
```

`uv sync` 会严格按照 `uv.lock` 安装或删除包，保证本地环境与锁文件完全一致。

---

## 5. 添加新依赖

需要引入新包时，使用 `uv add` 而不是手动修改 `pyproject.toml`：

```bash
uv add <包名>
```

uv 会自动更新 `pyproject.toml` 和 `uv.lock`。**请将这两个文件一同提交到仓库**，供其他人同步。

```bash
git add pyproject.toml uv.lock
git commit -m "feat: add <包名>"
git push
```

---

## 6. 移除依赖

```bash
uv remove <包名>
```

同样记得提交 `pyproject.toml` 和 `uv.lock` 的变更。

---

## 注意事项

- **提交 `uv.lock`**：锁文件是多人协作环境一致性的保障，必须纳入版本控制。
- **忽略 `.venv/`**：虚拟环境目录不应提交，确认 `.gitignore` 中已包含 `.venv`。
- **Python 版本**：本项目要求 Python >= 3.13，uv 会自动检测并使用符合要求的版本。
