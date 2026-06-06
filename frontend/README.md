# HR Agent Frontend

前端项目基于 **React + TypeScript + Vite**，用于支撑“智能简历投递系统”的 Web 端。

---

## 1. 项目功能

### 1.1 登录与身份
- 用户登录/注册（求职者、招聘者两种角色）
- 基于角色的路由保护
- Token 持久化与自动刷新（401 场景）

### 1.2 求职者能力
- 岗位市场浏览与筛选
- 查看岗位详情
- 在线填写/上传简历并投递
- 查看“我的投递”与状态

### 1.3 招聘者能力
- 发布岗位
- 岗位列表管理（状态更新、删除）
- 查看候选人列表与简历详情
- 更新候选人状态（待查看/已查看/面试/不合适/已录用）

---

## 2. 技术栈

- **框架**：React 19、TypeScript、Vite
- **路由**：react-router-dom
- **服务端状态**：@tanstack/react-query
- **认证状态**：zustand（仅认证态）
- **请求层**：axios（带 request/response interceptors）
- **表单校验**：react-hook-form + zod + @hookform/resolvers
- **样式/UI**：Tailwind CSS v4 + shadcn/radix-ui + lucide-react
- **提示**：sonner
- **代码规范**：ESLint + TypeScript ESLint

---

## 3. 核心依赖

> 完整清单请查看 `package.json`。

主要运行依赖包括：
- `react` / `react-dom`
- `react-router-dom`
- `@tanstack/react-query`
- `zustand`
- `axios`
- `react-hook-form` / `zod`
- `tailwindcss` / `@tailwindcss/vite`
- `radix-ui` / `shadcn`
- `sonner`

---

## 4. 安装与启动

### 4.1 环境要求
- Node.js 18+
- npm 9+

### 4.2 安装依赖

```bash
cd frontend
npm install
```

### 4.3 启动开发环境

```bash
npm run dev
```

默认开发地址：
- Frontend: `http://localhost:3001`
- 后端 API 通过 Vite 代理：`/api -> http://localhost:8000`

> 请确保后端服务已启动，否则前端请求会失败。

---

## 5. 常用命令

```bash
npm run dev      # 本地开发
npm run lint     # 代码检查
npm run build    # 生产构建
npm run preview  # 本地预览构建产物
```

---

## 6. 目录概览

```txt
src/
  app/          # 应用级 Provider
  features/     # 按业务域拆分（auth/jobs/applications/resume）
  shared/       # 跨业务共享（api/constants/ui）
  pages/        # 路由页面
  components/ui # UI 原子组件
  lib/          # 工具函数
```

更详细的架构说明见：
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [PROJECT_NOTE.md](./PROJECT_NOTE.md)
