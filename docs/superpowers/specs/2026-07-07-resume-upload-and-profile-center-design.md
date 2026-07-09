# 简历上传解析与个人中心 — 设计规格文档

## 1. 概述

在智能简历投递系统中新增两大功能：
1. **简历上传与智能解析**：求职者在投递页面可通过拖拽或选择文件的方式上传简历文件（PDF/DOCX/TXT），系统自动解析为结构化数据并填充投递表单。
2. **个人中心**：求职者可在右上角头像菜单进入个人中心，管理多份简历（上传、命名、删除、查看），支持不同岗位使用不同简历。

## 2. 后端变更

### 2.1 新模型：Resume（简历档案）

新增 `backend/app/models/resume.py`:

```python
class Resume(Base, TimestampMixin):
    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)       # 用户命名的简历名称
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)  # 原始文件名
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)   # MIME type: application/pdf, text/plain, ...
    file_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False) # 文件二进制数据
    parsed_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 提取的纯文本
    structured_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # LLM 解析的结构化数据
```

### 2.2 新 Schema：Resume schemas

新增 `backend/app/schemas/resume.py`:

```python
class ResumeResponse(BaseModel):
    id: str
    name: str
    file_name: str
    file_type: str
    parsed_text: str | None
    structured_data: dict | None
    created_at: datetime
    updated_at: datetime

class ResumeListItem(BaseModel):
    id: str
    name: str
    file_name: str
    file_type: str
    created_at: datetime

class ResumeListResponse(BaseModel):
    total: int
    items: list[ResumeListItem]

class ParseResumeResponse(BaseModel):
    """简历解析响应（不保存到库，仅用于填充表单）"""
    parsed_text: str
    structured_data: StructuredResume  # 复用已有 schema
```

### 2.3 新 API 路由

新增 `backend/app/api/resumes.py`:

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/resumes/parse` | 上传并解析简历（不保存），返回结构化数据用于填充表单 |
| POST | `/api/resumes/` | 上传并保存简历到个人中心 |
| GET | `/api/resumes/` | 获取用户简历列表 |
| GET | `/api/resumes/{id}` | 获取单份简历详情（含结构化数据） |
| GET | `/api/resumes/{id}/download` | 下载简历文件 |
| PUT | `/api/resumes/{id}` | 更新简历名称 |
| DELETE | `/api/resumes/{id}` | 删除简历 |

在 `backend/app/api/__init__.py` 中注册 `resumes.router`。

### 2.4 新增 Service：resume_service

新增 `backend/app/services/resume_service.py`，主要函数：

```python
async def parse_resume_file(file: UploadFile) -> tuple[str, StructuredResume]
```
- 根据文件类型提取文本内容
- 调用 DeepSeek 结构化解析
- 返回 (parsed_text, structured_data)

```python
async def extract_text_from_pdf(file_bytes: bytes) -> str
async def extract_text_from_docx(file_bytes: bytes) -> str
async def extract_text_from_txt(file_bytes: bytes) -> str
```

### 2.5 LLM 解析能力扩展

在 `backend/app/llm/deepseek.py` 中新增方法：

```python
async def parse_resume(self, raw_text: str) -> StructuredResume:
    """将简历原始文本解析为结构化简历数据"""
```

新增对应的 prompt 模板（`backend/app/services/resume_service.py` 或 `backend/app/services/agent/prompts.py` 中）：

```
你是一位专业的简历解析助手。请从以下简历文本中提取信息，输出严格的结构化 JSON。
字段包括：姓名、工作年限、最高学历、联系方式（电话/邮箱/微信）、
工作经历（公司/职位/起止时间/描述）、项目经历（项目名/角色/起止时间/描述/技术栈）、
教育经历（学校/专业/学位/起止时间）、证书、技能、自我评价。
```

### 2.6 数据库迁移

新建 Alembic migration 创建 `resumes` 表：

```python
op.create_table('resumes',
    sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    sa.Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
    sa.Column('name', sa.String(100), nullable=False),
    sa.Column('file_name', sa.String(255), nullable=False),
    sa.Column('file_type', sa.String(50), nullable=False),
    sa.Column('file_data', sa.LargeBinary, nullable=False),
    sa.Column('parsed_text', sa.Text, nullable=True),
    sa.Column('structured_data', JSONB, nullable=True),
    sa.Column('created_at', sa.DateTime, nullable=False),
    sa.Column('updated_at', sa.DateTime, nullable=False),
)
op.create_index('ix_resumes_user_id', 'resumes', ['user_id'])
```

### 2.7 依赖变更

在 `requirements.txt` 中新增：
- `PyPDF2` — PDF 文本提取
- `python-docx` — Word 文档文本提取

## 3. 前端变更

### 3.1 投递页面：简历上传组件

新建 `frontend/src/features/resumes/components/ResumeUploader.tsx`:

**交互设计：**
- 投递表单上方新增一个虚线边框的拖拽上传区域
- 支持点击选择文件（`accept=".pdf,.docx,.txt"`）
- 支持拖拽文件到区域（`onDragOver` + `onDrop`）
- 上传中显示加载动画
- 上传并解析成功后：
  - 显示已解析的简历文件名和状态
  - 自动填充表单所有字段
  - 显示"已从简历自动填充"提示
- 解析失败时显示错误信息，用户可继续手动填写
- 已登录用户还可以选择"从我的简历库选择"已有简历

**状态管理：**
```
- idle: 初始状态，显示上传区域
- uploading: 文件上传/解析中，显示 loading
- parsed: 解析完成，显示文件名 + 重新上传按钮
- error: 解析失败，显示错误信息
```

**ApplyPage 集成：**
- 在面包屑下方、StepForm 上方插入 ResumeUploader
- 解析成功后调用 `form.reset(parsedData)` 填充所有字段
- 添加 `useEffect` 在 `showSuccess` 时重置上传状态

### 3.2 个人中心入口（SeekerLayout 修改）

修改 `frontend/src/shared/ui/layout/SeekerLayout.tsx`:

- 在头像下拉菜单中添加"个人中心"选项（在用户名下方、退出登录上方）
- 点击跳转到 `/profile`

### 3.3 个人中心页面

新建 `frontend/src/pages/ProfilePage.tsx`:

**布局：**
- 页面标题："个人中心"
- 主体为简历管理区域

**简历列表：**
- 卡片网格布局，每张卡片展示：
  - 简历名称（可编辑）
  - 文件名 + 文件类型图标
  - 上传日期
  - 操作按钮：下载、删除
- 点击卡片可查看/编辑结构化数据

**上传新简历：**
- 页面顶部或悬浮按钮："上传新简历"
- 弹出对话框（或内联区域），支持拖拽/选择文件
- 上传后自动解析，解析成功后提示命名
- 保存到简历库

**编辑简历名称：**
- 点击名称直接内联编辑
- 或弹出编辑对话框

**删除确认：**
- 删除前弹出确认对话框

### 3.4 路由配置

在 `App.tsx` 中添加：

```tsx
<Route
  path="/profile"
  element={
    <ProtectedRoute role="job_seeker">
      <ProfilePage />
    </ProtectedRoute>
  }
/>
```

放在 SeekerLayout 路由组内。

### 3.5 API Client

新建 `frontend/src/features/resumes/api/resumes.ts`:

```typescript
// POST /api/resumes/parse — 上传解析（不保存）
export async function parseResume(file: File): Promise<ParseResumeResponse>

// POST /api/resumes/ — 上传保存
export async function uploadResume(file: File, name: string): Promise<ResumeResponse>

// GET /api/resumes/ — 获取简历列表
export async function getResumeList(): Promise<ResumeListResponse>

// GET /api/resumes/:id — 获取简历详情
export async function getResumeDetail(id: string): Promise<ResumeResponse>

// GET /api/resumes/:id/download — 下载简历文件
export async function downloadResume(id: string): Promise<Blob>

// PUT /api/resumes/:id — 更新简历名称
export async function updateResumeName(id: string, name: string): Promise<void>

// DELETE /api/resumes/:id — 删除简历
export async function deleteResume(id: string): Promise<void>
```

### 3.6 React Query Hooks

新建 `frontend/src/features/resumes/hooks/useResumes.ts`:

```typescript
export function useResumeListQuery()      // useQuery -> GET /api/resumes/
export function useResumeDetailQuery(id)   // useQuery -> GET /api/resumes/:id
export function useParseResumeMutation()   // useMutation -> POST /api/resumes/parse
export function useUploadResumeMutation()  // useMutation -> POST /api/resumes/
export function useUpdateResumeMutation()  // useMutation -> PUT /api/resumes/:id
export function useDeleteResumeMutation()  // useMutation -> DELETE /api/resumes/:id
```

## 4. 数据流

### 4.1 投递页面上传解析流程

```
用户拖拽/选择文件
  → 前端显示 uploading 状态
  → POST /api/resumes/parse (multipart/form-data)
  → 后端：
      1. 读取文件内容
      2. 根据文件类型提取文本（PDF/DOCX/TXT）
      3. 调用 DeepSeek 解析为结构化 JSON
      4. 返回 { parsed_text, structured_data }
  → 前端接收结构化数据
  → 自动填充表单字段（form.reset(parsedData)）
  → 显示 "已从 {filename} 自动填充" 提示
```

### 4.2 个人中心保存简历流程

```
用户在个人中心上传简历
  → POST /api/resumes/ (multipart/form-data)
  → 后端：
      1. 读取文件内容
      2. 提取文本
      3. 调用 DeepSeek 解析
      4. 保存到 resumes 表
  → 返回简历 ID
  → 刷新简历列表
```

### 4.3 投递页面使用已保存简历流程

```
用户在投递页面点击 "从简历库选择"
  → 弹出已保存简历列表
  → 选择一份简历
  → GET /api/resumes/{id} → 获取结构化数据
  → 填充表单
```

## 5. 错误处理

### 后端
- 文件大小限制：10MB
- 支持的文件类型：application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, text/plain
- 不支持的类型返回 400
- LLM 解析失败时返回 422，携带错误信息
- 文件为空时返回 400

### 前端
- 上传中显示加载动画/进度
- 解析失败显示 toast 错误，用户可以继续手动填写
- 文件类型不支持时前端提前拦截
- 文件大小超限时前端提前拦截

## 6. 组件树

```
SeekerLayout
├── Avatar Dropdown
│   ├── 用户名 (显示)
│   ├── 个人中心 (新)
│   └── 退出登录
└── Outlet
    ├── ApplyPage
    │   ├── ResumeUploader (新)
    │   │   ├── 拖拽上传区域
    │   │   └── 简历库选择按钮
    │   ├── StepForm
    │   └── ...
    └── ProfilePage (新)
        ├── 上传简历按钮
        └── 简历卡片列表
            └── ResumeCard (新)
                ├── 简历名称 (可编辑)
                ├── 文件信息
                └── 操作按钮
```

## 7. 文件变更清单

### 后端（新增）
- `backend/app/models/resume.py` — Resume ORM 模型
- `backend/app/schemas/resume.py` — Resume Pydantic schemas
- `backend/app/api/resumes.py` — Resume REST API
- `backend/app/services/resume_service.py` — 文件解析 + LLM 解析业务逻辑

### 后端（修改）
- `backend/app/api/__init__.py` — 注册 resumes router
- `backend/app/llm/deepseek.py` — 新增 `parse_resume` 方法
- `backend/app/llm/base.py` — 新增 `parse_resume` 抽象方法
- `backend/app/database.py` — 导入 resume 模型
- `backend/alembic/env.py` — 导入 resume 模型
- `backend/requirements.txt` — 新增 PyPDF2, python-docx
- `backend/app/models/__init__.py` — 导出 Resume

### 前端（新增）
- `frontend/src/pages/ProfilePage.tsx` — 个人中心页面
- `frontend/src/features/resumes/api/resumes.ts` — API 客户端
- `frontend/src/features/resumes/hooks/useResumes.ts` — React Query hooks
- `frontend/src/features/resumes/components/ResumeUploader.tsx` — 简历上传组件
- `frontend/src/features/resumes/components/ResumeCard.tsx` — 简历卡片组件

### 前端（修改）
- `frontend/src/App.tsx` — 添加 `/profile` 路由
- `frontend/src/shared/ui/layout/SeekerLayout.tsx` — 添加个人中心菜单项
