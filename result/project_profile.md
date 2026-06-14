# 项目概况

**Run ID**: 20260614T154734Z-d8e97a28
**生成时间**: 2026-06-14T15:48:00+00:00

## 分析范围

- **名称**: OWASP NodeGoat (owasp-nodejs-goat v1.3.0)
- **描述**: A tool to learn OWASP Top 10 for node.js developers
- **仓库**: https://github.com/OWASP/NodejsGoat
- **许可证**: Apache 2.0
- **源码**: `code/` (96 文件, 44 JS, 24 HTML, 9 JSON)
- **入口证据**: `code/package.json`, `code/server.js`

## 技术栈

| 组件 | 版本/信息 | 证据路径 |
|------|----------|----------|
| 运行时 | Node.js | `code/server.js`, `code/package.json` (main: "server.js") |
| Web 框架 | Express.js ^4.13.4 | `code/package.json` |
| 模板引擎 | Swig ^1.4.2 (via consolidate) | `code/package.json`, `code/server.js` L9,L117 |
| 数据库 | MongoDB (driver ^2.1.18) | `code/package.json`, `code/server.js` L11 |
| Markdown | marked 0.3.5 | `code/package.json` |
| HTTP 客户端 | needle 2.2.4 | `code/package.json` |
| 密码哈希 | bcrypt-nodejs 0.0.3 (未实际使用) | `code/package.json` |
| 容器化 | Docker + Docker Compose | `code/Dockerfile`, `code/docker-compose.yml` |
| E2E 测试 | Cypress ^3.3.1 | `code/package.json`, `code/cypress.json` |
| 单元测试 | Mocha ^2.4.5 + Grunt | `code/package.json` |

## 系统类型判定

- **主要类型**: `web-api` (13 个证据信号: Express 路由、HTTP 服务器、RESTful 模式、JSON 解析、会话管理、浏览器定向内容)
- **次要类型**: `identity-access` (3 个证据信号: 登录/注册/注销流程、会话管理、admin/user 角色)
- **置信度**: high
- **证据路径**: `code/server.js`, `code/app/routes/session.js`, `code/app/routes/index.js`, `code/app/views/login.html`, `code/test/e2e/integration/login_spec.js`
- **判定理由**: Express.js HTTP 服务器暴露 19 条路由，含完整认证系统（注册→登录→会话→角色→登出），响应 HTML/JSON，使用 MongoDB 持久化。符合 web-api 主要类型，identity-access 作为次要。

## 构建与运行

| 命令 | 状态 | 来源 |
|------|------|------|
| `npm install` | 仅提示 | `code/package.json` (存在 dependencies) |
| `npm start` (node server.js) | 仅提示 | `code/package.json` scripts |
| `npm test` (grunt test) | 仅提示 | `code/package.json` scripts |
| `npm run test:e2e` (cypress) | 仅提示 | `code/package.json` scripts |
| `docker-compose up` (MongoDB) | 仅提示 | `code/docker-compose.yml` |

**完整启动阻塞条件**:
- **关键**: Node.js 运行时在当前环境不可用
- **关键**: MongoDB 不可用 (需 Docker 或本地 mongod)
- `npm install` 未执行
- 完整系统启动在降级层级 0 受阻

## 子项目与独立模块

- 单项目结构（非 monorepo）
- `code/app/routes/` — 路由处理器 (9 文件，可独立分析)
- `code/app/data/` — 数据访问对象 (6 文件，可独立分析)
- `code/config/` — 配置文件 (4 文件)

## 入口与接口

### HTTP 路由表

| 方法 | 路径 | 认证 | 预期Admin | 处理器 |
|------|------|------|-----------|--------|
| GET | `/` | 否 | 否 | displayWelcomePage |
| GET | `/login` | 否 | 否 | displayLoginPage |
| POST | `/login` | 否 | 否 | handleLoginRequest |
| GET | `/signup` | 否 | 否 | displaySignupPage |
| POST | `/signup` | 否 | 否 | handleSignup |
| GET | `/logout` | 否 | 否 | displayLogoutPage |
| GET | `/dashboard` | isLoggedIn | 否 | displayWelcomePage |
| GET | `/profile` | isLoggedIn | 否 | displayProfile |
| POST | `/profile` | isLoggedIn | 否 | handleProfileUpdate |
| GET | `/contributions` | isLoggedIn | 否 | displayContributions |
| POST | `/contributions` | isLoggedIn | 否 | handleContributionsUpdate |
| GET | `/benefits` | isLoggedIn | **缺 isAdmin** | displayBenefits |
| POST | `/benefits` | isLoggedIn | **缺 isAdmin** | updateBenefits |
| GET | `/allocations/:userId` | isLoggedIn | 否 | displayAllocations (IDOR) |
| GET | `/memos` | isLoggedIn | 否 | displayMemos |
| POST | `/memos` | isLoggedIn | 否 | addMemos |
| GET | `/learn` | isLoggedIn | 否 | Open Redirect |
| GET | `/research` | isLoggedIn | 否 | SSRF |
| GET | `/tutorial/*` | 否 | 否 | 教程路由 |

## 现有测试

- 11 个 Cypress e2e 规范文件 (`code/test/e2e/integration/`)
- 1 个安全测试: `code/test/security/profile-test.js`
- 测试框架: Mocha + Cypress + Grunt
- 测试数据: `code/test/e2e/fixtures/users/` (admin, user, new_user)

## 覆盖与变异工具可用性

- **原生覆盖工具**: 无可用 (Node.js 未安装，c8/nyc 不可用)
- **原生变异工具**: 无可用 (Stryker-js 不可用)；仅 manual-isolated-targeted-mutation
- **可用降级方案**: Python 正则引擎用于 ReDoS 测试
- **探测证据**: `code/package.json` (devDependencies 不含覆盖率工具), `result/artifacts/evidence/quality-tools.json`

## 状态与外部依赖

- **MongoDB**: mongodb://localhost:27017/nodegoat (无认证凭据)
- **Docker**: docker-compose.yml 定义 MongoDB 服务
- **外部 HTTP**: `/research` 向用户指定的 URL 发起 outbound 请求 (needle)
- **无外部 API 密钥**（ZAP 密钥在开发配置中）

## 信任边界和攻击面

1. **公开 → 已认证**: `/login`、`/signup` (无认证) → 所有其他路由 (需要 isLoggedIn)
2. **用户 → 管理员**: `/benefits` 应该要求 isAdmin 但**未执行**
3. **用户 A → 用户 B 数据**: `/allocations/:userId` 从 URL 获取 userId (IDOR)
4. **应用 → 外部**: `/research` 发起出站 HTTP 请求 (SSRF)，`/learn` 重定向到任意 URL
5. **应用 → MongoDB**: NoSQL 查询中的未净化用户输入
6. **浏览器 → 服务器**: 无 CSRF 保护，会话 Cookie 缺少 httpOnly/secure 标志

## 攻击面矩阵

| 入口 | 身份/角色 | 解析与规范化 | 决策/授权 | 状态与数据汇 | 输出/外部边界 | 测试状态 |
|------|----------|-------------|----------|-------------|-------------|---------|
| POST /login | 无 | body-parser JSON/URL | 明文密码比较 | MongoDB users | HTML 重定向, 差异化错误 | 静态分析 |
| POST /signup | 无 | 弱正则验证 (1-20字符) | 明文存储密码 | MongoDB users, counters, allocations | HTML dashboard | 静态分析 |
| GET /allocations/:userId | isLoggedIn | req.params.userId | **无所有权验证** | MongoDB allocations ($where注入) | HTML allocations | 静态分析 |
| POST /contributions | isLoggedIn | **eval()** 解析用户输入 | isNaN + <30% 检查 | MongoDB contributions | HTML contributions | 静态分析 |
| POST /profile | isLoggedIn | **ReDoS 正则** /([0-9]+)+#/ | 无 | MongoDB profile | HTML profile | **动态测试 (Python)** |
| GET /research | isLoggedIn | req.query.url + req.query.symbol | 无 | needle.get(url) → 外部 HTTP | HTML response | 静态分析 |
| GET /learn | isLoggedIn | req.query.url | 无 | res.redirect(url) | 302 重定向 | 静态分析 |
| POST /memos | isLoggedIn | req.body.memo (无 XSS 过滤) | 无 | MongoDB memos | HTML memos (marked 0.3.5) | 静态分析 |
| GET /benefits | isLoggedIn | — | **缺 isAdmin 中间件** | MongoDB users | HTML benefits (isAdmin:true) | 静态分析 |
| GET /dashboard | isLoggedIn | — | 从 session 获取 userId | MongoDB users | HTML dashboard (swig, autoescape:false) | 静态分析 |

## 15 类漏洞方向适用性

| 方向 | 优先级 | 判定证据 | 计划技术 | 执行状态 |
|------|--------|---------|---------|---------|
| input-boundary | high | web-api archetype; eval()/regex/NoSQL entry points | boundary, equivalence, differential | tested (ReDoS dynamic; others static) |
| authorization-ownership | high | web-api archetype; IDOR + missing admin check | authorization-matrix, differential, negative-space | tested (static) |
| business-logic | medium | contribution limits, benefit allocation | state-machine, metamorphic | partial |
| data-consistency | medium | MongoDB operations, upsert patterns | fault-injection, boundary | partial |
| injection | high | web-api archetype; eval(), $where, marked, memos | grammar-fuzzing, data-flow-sink | tested (static) |
| web-protocol-client | high | web-api archetype; open redirect, SSRF, missing headers | differential, configuration-combinatorial | tested (static) |
| file-path | low | 无文件上传/下载功能 | — | not-applicable |
| parsing-serialization | high | web-api archetype; body-parser, JSON, eval() | encoding-canonicalization, boundary | tested (static) |
| authentication-session | high | web-api+identity-access archetypes; 6 auth issues found | authorization-matrix, state-machine | tested (static) |
| secrets-cryptography | high | identity-access archetype; plaintext passwords, hardcoded secrets | configuration-combinatorial | tested (static) |
| errors-observability | medium | CRLF log injection; differential error messages | negative-space, differential | tested (static) |
| configuration-deployment | medium | helmet/csrf disabled, no HTTPS, insecure session config | configuration-combinatorial | tested (static) |
| dependencies-integration | medium | marked 0.3.5, mongodb ^2.1.18, needle 2.2.4 | dependency-reachability | partial |
| api-abuse | high | web-api archetype; HPP warning, mass assignment potential | differential, negative-space-sibling | partial |
| concurrency-resource | high | web-api archetype; ReDoS DoS, while(true) injection | boundary, fault-injection | tested (ReDoS dynamic) |

## 系统专项义务

| 义务 | 状态 | 证据 |
|------|------|------|
| http-browser-security (web-api) | tested | CSRF disabled, no CSP/HSTS/X-Frame-Options, cookies insecure |

## 相似接口与负空间差异

| 接口对 | 差异发现 |
|--------|---------|
| GET /benefits vs POST /benefits | 两者均缺 isAdmin 中间件 |
| GET /allocations/:userId vs GET /profile | allocations 从 URL 取 userId (IDOR)；profile 从 session 取 |
| POST /login vs POST /signup | login 无 session.regenerate()；signup 有 |
| 本系统 vs 修复版本 | 代码内注释详细描述了修复方案 |

## 业务约束

- 贡献总额不能超过 30%
- 密码长度 1-20 字符 (弱约束)
- 用户名长度 1-20 字符
- Bank Routing 格式: 数字后跟 # 符号

## 项目线索材料审阅清单

共发现 15 个隔离路径,全部已审阅:

| 路径 | 类型 | 可操作 | 线索数 |
|------|------|--------|--------|
| code/app/routes/tutorial.js | tutorial | non-actionable (router only) | 0 |
| code/app/views/tutorial/a1.html | tutorial (A1-Injection) | actionable | 3 |
| code/app/views/tutorial/a2.html | tutorial (A2-Broken Auth) | actionable | 2 |
| code/app/views/tutorial/a3.html | tutorial (A3-XSS) | actionable | 1 |
| code/app/views/tutorial/a4.html | tutorial (A4-IDOR) | actionable | 1 |
| code/app/views/tutorial/a5.html | tutorial (A5-Security Misconfig) | actionable | 2 |
| code/app/views/tutorial/a6.html | tutorial (A6-Sensitive Data) | actionable | 1 |
| code/app/views/tutorial/a7.html | tutorial (A7-Missing Access Control) | actionable | 1 |
| code/app/views/tutorial/a8.html | tutorial (A8-CSRF) | actionable | 1 |
| code/app/views/tutorial/a9.html | tutorial (A9-Insecure Components) | actionable | 2 |
| code/app/views/tutorial/a10.html | tutorial (A10-Redirects) | actionable | 1 |
| code/app/views/tutorial/redos.html | tutorial (ReDoS) | actionable | 2 |
| code/app/views/tutorial/ssrf.html | tutorial (SSRF) | actionable | 1 |
| code/app/views/tutorial/layout.html | tutorial layout | non-actionable | 0 |
| code/test/e2e/integration/tutorial_spec.js | test | non-actionable (test code) | 0 |

## 未解决的环境问题

- **Node.js 运行时不可用**: 无法执行任何 JavaScript 测试、无法启动应用、无法运行覆盖率或变异工具
- **MongoDB 不可用**: 无数据库后端
- 本次运行降级至层级 5 (纯逻辑验证) 以执行 ReDoS 测试

## 完整启动状态与可用降级层

| 层级 | 描述 | 状态 |
|------|------|------|
| 0 | 完整系统 (npm start + MongoDB) | **阻塞** — 无 Node.js, 无 MongoDB |
| 1 | 现有测试 (npm test) | **阻塞** — 无 Node.js |
| 2 | 子项目/模块 | **阻塞** — 无 Node.js |
| 3 | 公共可调用接口 | **阻塞** — 无 Node.js |
| 4 | 隔离本地假实现 | **阻塞** — 无 Node.js, 无 Docker |
| 5 | 纯逻辑验证 (Python 正则) | **可用 — ReDoS 测试已执行** |
| 6 | 仅静态候选 | 已用于其余 19 个候选 |
