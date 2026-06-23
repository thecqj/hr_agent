# 后端单元测试 + mypy 修复设计

日期: 2026-06-22

## 目标

1. 为后端所有 API 接口新增集成测试
2. 修复 mypy --strict 配置问题，确保 `cd backend && uv run mypy --strict app/` 零错误通过

## 一、测试基础设施

### 数据库策略

- 使用本地 PostgreSQL 测试数据库（非 Docker）
- 测试库名：`jobboard_test`，通过 `TEST_DATABASE_URL` 环境变量配置
- 默认值：`postgresql+psycopg://app:password@localhost:5432/jobboard_test`

### 事务回滚隔离

1. 测试 session 启动时 `create_all` 确保表存在
2. 每个测试前 `connection.begin()` 开启外层事务
3. 覆盖 FastAPI `get_db` 依赖，注入绑定到外层事务的 session
4. 测试执行期间所有写操作在事务内
5. 测试结束后 `rollback()` 回滚外层事务，数据库恢复原状

### 文件结构

```
tests/
├── conftest.py                      # 全局 fixtures
├── test_auth_api.py                 # auth 端点测试
├── test_jobs_api.py                 # jobs 端点测试
└── test_applications_api.py         # applications 端点测试
```

### Fixtures

| Fixture | 作用域 | 功能 |
|---------|--------|------|
| `engine` | session | 连接测试库的 async engine |
| `db_tables` | session | `create_all` 确保表存在（仅一次） |
| `db_session` | function | 绑定到外层事务的 AsyncSession，测试后自动回滚 |
| `client` | function | 注入 `db_session` 的 `httpx.AsyncClient` |
| `auth_headers_seeker` | function | 注册求职者后返回 Bearer token headers |
| `auth_headers_recruiter` | function | 注册招聘者后返回 Bearer token headers |

## 二、测试用例（31 个）

### Auth API（11 个）

| 测试 | 端点 | 验证点 |
|------|------|--------|
| 注册求职者成功 | POST /register | 201，返回 token + user（role=job_seeker） |
| 注册招聘者成功 | POST /register | 201，返回 token + user（role=recruiter） |
| 重复邮箱注册失败 | POST /register | 400，邮箱已存在 |
| 登录成功 | POST /login | 200，返回 token + user |
| 登录密码错误 | POST /login | 401 |
| 登录不存在的用户 | POST /login | 401 |
| 刷新 token 成功 | POST /refresh | 200，返回新 token 对 |
| 刷新 token 无效 | POST /refresh | 401 |
| 获取当前用户信息 | GET /me | 200，返回 user 信息 |
| 未登录访问 /me | GET /me | 401 |
| 登出成功 | POST /logout | 200，返回消息 |

### Jobs API（12 个）

| 测试 | 端点 | 验证点 |
|------|------|--------|
| 招聘者创建职位 | POST /jobs/ | 201，返回 job 数据 |
| 求职者创建职位失败 | POST /jobs/ | 403，无权限 |
| 列出职位（默认过滤） | GET /jobs/ | 200，只返回 active 职位 |
| 列出职位（关键词搜索） | GET /jobs/ | 200，匹配 title/description |
| 列出职位（薪资范围过滤） | GET /jobs/ | 200，结果在范围内 |
| 获取单个职位 | GET /jobs/{id} | 200，返回完整 job |
| 获取不存在职位 | GET /jobs/{id} | 404 |
| 招聘者更新自己的职位 | PUT /jobs/{id} | 200，字段更新 |
| 更新他人职位失败 | PUT /jobs/{id} | 403 |
| 删除自己的职位 | DELETE /jobs/{id} | 204 |
| 删除他人职位失败 | DELETE /jobs/{id} | 403 |
| 更新职位状态 | PATCH /jobs/{id}/status | 200，状态变更 |

### Applications API（8 个）

| 测试 | 端点 | 验证点 |
|------|------|--------|
| 求职者投递申请 | POST /applications/ | 201，返回 application |
| 招聘者投递失败 | POST /applications/ | 403，无权限 |
| 投递已关闭的职位 | POST /applications/ | 400，职位非 active |
| 重复投递同一职位 | POST /applications/ | 409，冲突 |
| 查看自己的申请列表 | GET /applications/my | 200，返回当前用户的申请 |
| 查看职位的申请列表（招聘者） | GET /applications/job/{id} | 200，返回该职位下的申请 |
| 查看职位申请（非拥有者） | GET /applications/job/{id} | 403 |
| 更新申请状态（招聘者） | PATCH /applications/{id}/status | 200，状态变更 |

## 三、mypy --strict 修复

### 问题

`mypy --strict app/` 报模块名冲突（`api.auth` vs `app.api.auth`），因为缺少 `explicit_package_bases` 配置。代码本身类型注解完整，`--explicit-package-bases` 下零错误。

### 修复

在 `mypy.ini` 中添加一行：

```ini
[mypy]
python_version = 3.12
explicit_package_bases = True   # 新增
warn_unused_configs = True
```

修复后 `cd backend && uv run mypy --strict app/` 零错误通过。
