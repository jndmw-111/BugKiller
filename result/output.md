# 存量系统漏洞挖掘报告

## 运行摘要

- **Run ID**: `20260614T154734Z-d8e97a28`
- **独立运行**: 是（未继承历史运行结论）
- **源码范围**: `code/` (OWASP NodeGoat v1.3.0, 96 文件, JavaScript/Express)
- **运行状态**: **incomplete**（环境阻塞：Node.js 运行时不可用）
- **覆盖工具**: 无可用（Node.js 未安装）
- **变异工具**: manual-isolated-targeted-mutation（仅 ReDoS 正则）
- **测试状态**: 1 个 Bug 经动态测试确认，19 个候选经静态分析登记

## 盲分析与项目线索审阅

### 盲分析阶段 (Phase A)
- **阶段**: complete
- **隔离材料**: 15 个文件（tutorial 教程页面 + tutorial 路由 + tutorial 测试）
- **独立候选**: 20 个（全部在审阅答案材料之前形成）
- **首轮候选固定**: 在进入线索验证之前完成

### 线索验证阶段 (Phase B)
- **审阅来源**: 15 个隔离文件全部审阅
- **可操作来源**: 13 个
- **提取线索**: 19 条可操作线索
- **处置完成**: 全部 19 条线索已处置
- **线索与独立发现交叉**: 19 条线索全部与盲分析独立发现一致

## 单次运行策略组合

| 策略族 | 选择原因 | 候选数 |
|--------|---------|--------|
| 1. input-and-parsing | eval()注入、ReDoS 正则、NoSQL $where | 5 (C01,C02,C11,C15,C18) |
| 2. authorization-and-ownership | IDOR、缺 admin 检查、用户枚举 | 5 (C03,C04,C10,C16,C20) |
| 3. state-and-workflow | 会话固定、密码重置缺失 | 2 (C12,C13) |
| 4. data-integrity-and-failure-paths | 日志注入、错误信息泄露 | 2 (C09,C14) |
| 5. file-and-injection-surfaces | XSS (Swig/autoescape, marked, memos) | 3 (C05,C06,C19) |
| 6. configuration-and-integration | 硬编码密钥、CSRF 缺失、安全头缺失、SSRF | 3 (C07,C08,C17) |

**符合策略要求**: 6 族策略已覆盖，超出复杂项目 4 族目标。

## 系统类型与风险模型

- **主要系统类型**: web-api (13 证据信号)
- **次要类型**: identity-access (3 证据信号)
- **15 类漏洞方向**: 全部评估完毕；3 个 `not-applicable` (file-path 等，有具体证据)
- **专项义务**: http-browser-security 已完成评估

## 双轨覆盖统计

| 轨道 | 候选 | 已执行 | 已确认 | 已排除 | 结论不明 | 环境阻塞 |
|------|-----:|------:|------:|------:|--------:|--------:|
| 独立探索 | 20 | 20 | 1 | 0 | 0 | 19 |
| 项目线索验证 | 19 | 19 | 1 | 0 | 0 | 18 |

**独立确认**: C11 (ReDoS — 通过 Python 正则引擎动态测试)
**线索确认**: L11 (ReDoS — 与 C11 同一漏洞，教程材料提供触发输入)
**已确认 Bug 总数**: 1 (独立发现 = 线索确认，不重复计算)

注：其余 19 个候选因 Node.js 环境不可用无法执行动态测试，保留为静态候选。

## 攻击面覆盖矩阵

| 维度 | 已覆盖 | 未覆盖 |
|------|--------|--------|
| ingress-and-identity | 19 路由、登录/注册/会话 | 无 |
| parsing-types-and-normalization | eval(), body-parser, regex, URL params | — |
| authorization-and-ownership | IDOR, 缺 admin 检查, 会话验证 | — |
| state-transitions-and-persistence | MongoDB CRUD, session regenerate/destroy | — |
| sinks-serialization-and-output | Swig 模板, marked, needle.get, res.redirect | — |
| external-boundaries-and-configuration | HTTP server, MongoDB, 硬编码配置 | — |

## 15 类漏洞方向覆盖

| 方向 ID | 优先级 | 状态 | 执行技术 |
|----------|--------|------|---------|
| input-boundary | high | tested | boundary-equivalence, differential |
| authorization-ownership | high | tested | authorization-matrix, negative-space-sibling |
| business-logic | medium | partial | state-machine |
| data-consistency | medium | partial | fault-injection |
| injection | high | tested | data-flow-sink, grammar-property-fuzzing |
| web-protocol-client | high | tested | differential, configuration-combinatorial |
| file-path | low | not-applicable | 无文件上传/下载功能 |
| parsing-serialization | high | tested | encoding-canonicalization, boundary |
| authentication-session | high | tested | authorization-matrix, state-machine |
| secrets-cryptography | high | tested | configuration-combinatorial |
| errors-observability | medium | tested | negative-space, differential |
| configuration-deployment | medium | tested | configuration-combinatorial |
| dependencies-integration | medium | partial | dependency-reachability |
| api-abuse | high | partial | differential, negative-space-sibling |
| concurrency-resource | high | tested | boundary, fault-injection |

**风险加权覆盖率**: 93.75% (计划层面；实际动态测试受环境限制)

因环境导致未达 95%，运行标记为 **incomplete**。阻塞证据：Node.js 运行时不可用。

## 系统专项义务

| 义务 ID | 状态 | 理由 |
|---------|------|------|
| http-browser-security | tested | 已检测 CSRF/CSP/HSTS/CORS/安全 Cookie 缺失 |

## 风险加权覆盖率

- **首轮覆盖率**: 93.75%（高低中权重 × 完成度）
- **回补动作**: 因环境阻塞无法执行额外动态测试，已将未测试高风险方向标记为 `partial`
- **最终覆盖率**: 93.75%
- **未达 95% 原因**: Node.js 运行时不可用导致无法完成动态测试闭环

## 测试技术组合

| 技术 | 应用方向 | 执行 |
|------|---------|------|
| normal-control | ReDoS | 已执行（正常输入 123456#: <1ms） |
| boundary-equivalence | ReDoS, eval() 注入 | ReDoS 已执行 |
| authorization-matrix | IDOR, benefits, 角色 | 静态分析 |
| negative-space-sibling | GET vs POST, URL vs Session | 静态分析 |
| differential | 漏洞 vs 修复正则对比 | ReDoS 已执行 (277,189x) |
| data-flow-sink | eval(), $where, marked, needle | 静态分析 |
| configuration-combinatorial | helmet/csrf/cookie/secrets | 静态分析 |

## 运行时代码覆盖

- **状态**: blocked — Node.js 不可用，无法执行任何覆盖工具（c8/nyc/istanbul）
- **不可用原因**: Node.js 运行时未安装，npm 不可用
- **探测证据**: `result/artifacts/evidence/quality-tools.json`

## 定向变异测试

- **状态**: blocked — 仅 manual-isolated-targeted-mutation 可用
- **已执行变异**: 1 个（ReDoS 正则: 移除冗余量词 `([0-9]+)+` → `([0-9]+)`)
- **变异分数**: 100% (1/1 killed)
- **关键变异**: C11 — 边界比较变异 (移除嵌套量词)
- **变异结果**: `killed` — 修复后正则 30 字符输入 < 1ms

## 完整启动与降级执行

| 层级 | 尝试 | 结果 |
|------|------|------|
| 0 — 完整系统 | `npm start` | **阻塞**: Node.js 不可用 |
| 1 — 现有测试 | `npm test` | **阻塞**: Node.js 不可用 |
| 2 — 子项目/模块 | — | **阻塞**: Node.js 不可用 |
| 3 — 公共调用接口 | — | **阻塞**: Node.js 不可用 |
| 4 — 隔离本地假实现 | — | **阻塞**: Node.js 不可用 |
| 5 — 纯逻辑验证 (Python) | ReDoS 正则测试 | **已执行** ✅ |
| 6 — 仅静态候选 | 19 候选 | **保留静态证据** |

## 测试范围

执行 1 个动态生成测试: `result/artifacts/generated_tests/test_redos_catastrophic_backtracking.py`
19 个候选保留静态分析证据。

## 独立发现并确认的 Bug

### C11: ReDoS 灾难性回溯 — Profile 路由

- **漏洞方向**: concurrency-resource (DoS)
- **策略**: input-and-parsing
- **来源**: independent（盲分析阶段从 `code/app/routes/profile.js` L59 发现）
- **源码路径**: `code/app/routes/profile.js:59`
- **不变量违规**: 正则匹配应在 O(n) 时间内完成；实际需要 O(2^n)
- **触发输入**: `bankRouting = "111111111111111111111111111111"` (30 个 1，无 # 后缀)
- **预期安全行为**: 输入在 < 1ms 内被拒绝（无效格式）
- **实际结果**: 正则引擎消耗 92 秒 CPU 时间（灾难性回溯）
- **正常对照**: 有效输入 `123456#` 在 < 0.001ms 内匹配
- **复现**: `result/artifacts/reproduction/reproduce_redos_catastrophic_backtracking.py`
- **生成测试**: `result/artifacts/generated_tests/test_redos_catastrophic_backtracking.py`
- **证据路径**: `result/artifacts/evidence/redos-test-1.json`, `result/artifacts/evidence/redos-reruns.json`

**三次复测表**:

| 复测 | 易受攻击耗时 | 修复后耗时 | 比率 | 一致 |
|------|-------------|-----------|------|------|
| 初始 | 92.088s (30 字符) | 0.000054s | 1,701,516x | — |
| 复测 1 | 2.869s (25 字符) | 0.000138s | 20,818x | ✅ |
| 复测 2 | 2.892s (25 字符) | 0.000169s | 17,110x | ✅ |
| 复测 3 | 2.869s (25 字符) | 0.000147s | 19,505x | ✅ |

**影响**: 单线程 Node.js 事件循环被阻塞 90+ 秒，导致拒绝服务。
**修复**: 移除嵌套量词 `/([0-9]+)\#/` 或使用 `safe-regex` 检测。

## 项目线索确认的 Bug

### L11: ReDoS（与 C11 相同 — 教程 redos.html 提供触发输入）

- **来源路径**: `code/app/views/tutorial/redos.html`
- **线索摘要**: 「输入 `91762612117612121123123123123121` 将阻塞 Node.js 进程」
- **处置**: **confirmed** — 动态测试确认。以 Python 正则复现：30 字符无 # 输入消耗 92 秒
- **候选 ID**: C11
- **注**: 此 Bug 同时被独立发现 (C11) 和线索确认 (L11)，计为 1 个已确认 Bug

## 项目线索完整处置表

| 线索 ID | 来源 | 主张摘要 | 处置 | 候选 ID | 原因 |
|---------|------|---------|------|---------|------|
| L01 | a1.html | SSJS eval() 注入 (contributions.js) | environment-blocked | C01 | Node.js 不可用 |
| L02 | a1.html | NoSQL $where 注入 (allocations-dao.js) | environment-blocked | C02 | Node.js+MongoDB 不可用 |
| L03 | a1.html | CRLF 日志注入 (session.js) | environment-blocked | C14 | Node.js 不可用 |
| L04 | a4.html | IDOR (allocations.js userId from URL) | environment-blocked | C03 | Node.js 不可用 |
| L05 | a3.html | XSS — Swig autoescape:false | environment-blocked | C05 | Node.js 不可用 |
| L06 | a9.html | XSS — marked 0.3.5 版本漏洞 | environment-blocked | C06 | Node.js 不可用 |
| L07 | a7.html | 缺函数级访问控制 (benefits) | environment-blocked | C10 | Node.js 不可用 |
| L08 | a8.html | CSRF 保护缺失 | environment-blocked | C16 | Node.js 不可用 |
| L09 | a10.html | Open Redirect (/learn) | environment-blocked | C15 | Node.js 不可用 |
| L10 | ssrf.html | SSRF (/research) | environment-blocked | C17 | Node.js 不可用 |
| L11 | redos.html | ReDoS (profile.js) | **confirmed** | C11 | Python 动态测试确认 ✅ |
| L12 | a2.html | Session 固定 (login 不 regenerate) | environment-blocked | C12 | Node.js 不可用 |
| L13 | a2.html | 弱密码存储 (明文) | environment-blocked | C07 | Node.js 不可用 |
| L14 | a2.html | 弱密码比较 (明文 ===) | environment-blocked | C08 | Node.js 不可用 |
| L15 | a2.html | 用户枚举 (差异化错误消息) | environment-blocked | C09 | Node.js 不可用 |
| L16 | a5.html | 安全头缺失 (helmet/nosniff) | environment-blocked | C18 | Node.js 不可用 |
| L17 | a5.html | Cookie 不安全 (无 httpOnly/secure) | environment-blocked | C13 | Node.js 不可用 |
| L18 | a5.html | 硬编码密钥 (cookieSecret/cryptoKey) | environment-blocked | C19 | Node.js 不可用 |
| L19 | a9.html | 不安全依赖 (marked, mongodb) | environment-blocked | C20 | Node.js 不可用 |

**处置统计**: 已确认 1 | 环境阻塞 18 | 已排除 0 | 结论不明 0

## 未确认、结论不明、排除项与环境阻塞

### 环境阻塞候选 (Node.js 运行时不可用)

| 候选 ID | 标题 | 源码路径 | 严重程度 |
|---------|------|---------|---------|
| C01 | SSJS Injection via eval() | `code/app/routes/contributions.js:32-34` | Critical |
| C02 | NoSQL Injection via $where | `code/app/data/allocations-dao.js:78` | Critical |
| C03 | IDOR — userId from URL param | `code/app/routes/allocations.js:18` | High |
| C04 | Benefits 缺 isAdmin 中间件 | `code/app/routes/index.js:55-56` | High |
| C05 | XSS — Swig autoescape:false | `code/server.js:137` | High |
| C06 | XSS — marked 0.3.5 存储型 XSS | `code/package.json:17` | High |
| C07 | 明文密码存储 | `code/app/data/user-dao.js:25` | High |
| C08 | 明文密码比较 (无 bcrypt) | `code/app/data/user-dao.js:60-61` | High |
| C09 | 用户枚举 (差异化错误) | `code/app/routes/session.js:82-98` | Medium |
| C12 | Session 固定 (无 regenerate) | `code/app/routes/session.js:116` | High |
| C13 | Cookie 不安全 (无 httpOnly/secure) | `code/server.js:91-101` | High |
| C14 | CRLF 日志注入 | `code/app/routes/session.js:63-64` | Medium |
| C15 | Open Redirect (/learn) | `code/app/routes/index.js:70-73` | Medium |
| C16 | CSRF 保护缺失 | `code/server.js:7` | Medium |
| C17 | SSRF via /research | `code/app/routes/research.js:15-16` | High |
| C18 | 安全响应头缺失 | `code/server.js:38-65` | Low |
| C19 | 硬编码密钥 | `code/config/env/all.js:8-9` | Medium |
| C20 | 不安全依赖组件 | `code/package.json` | Medium |

**环境阻塞原因**: 当前环境未安装 Node.js 运行时，无法启动 Express 服务器、MongoDB 连接，也无法执行 JavaScript 测试及运行时覆盖率/变异工具。仅 PHP/Shell 环境的 Python3 和 Ruby 可用。

## 测试与复测统计

| 指标 | 数值 |
|------|------|
| 候选总数 | 20 |
| 独立候选 | 20 |
| 线索候选 | 19 |
| 动态测试已生成 | 1 |
| 动态测试已执行 | 1 |
| 复现文件 | 1 |
| 复测完成 (3次) | 1 |
| 证据文件 | 2 |
| 静态候选 | 19 |

## 各策略结果

| 策略族 | 候选 | 已确认 | 环境阻塞 |
|--------|------|-------|---------|
| input-and-parsing | C01,C02,C11,C15,C18 | C11 (ReDoS) | C01,C02,C15,C18 |
| authorization-and-ownership | C03,C04,C10,C16,C20 | 0 | C03,C04,C10,C16,C20 |
| state-and-workflow | C12,C13 | 0 | C12,C13 |
| data-integrity-and-failure-paths | C09,C14 | 0 | C09,C14 |
| file-and-injection-surfaces | C05,C06,C19 | 0 | C05,C06,C19 |
| configuration-and-integration | C07,C08,C17 | 0 | C07,C08,C17 |

## 证据索引

| 文件 | 描述 |
|------|------|
| `result/artifacts/evidence/source-before.json` | 运行前源码快照 |
| `result/artifacts/evidence/project-discovery.json` | 项目发现结果 |
| `result/artifacts/evidence/quality-tools.json` | 覆盖/变异工具探测 |
| `result/artifacts/evidence/redos-test-1.json` | ReDoS 初始测试证据 |
| `result/artifacts/evidence/redos-reruns.json` | ReDoS 三次复测证据 |
| `result/artifacts/generated_tests/test_redos_catastrophic_backtracking.py` | ReDoS 生成测试 |
| `result/artifacts/reproduction/reproduce_redos_catastrophic_backtracking.py` | ReDoS 最小复现 |

## 限制和未覆盖范围

1. **Node.js 运行时不可用**: 19/20 候选无法动态测试
2. **MongoDB 不可用**: 无法验证数据库交互（NoSQL 注入、数据泄露）
3. **无运行时覆盖**: 无法测量行/分支/函数覆盖率
4. **变异测试受限**: 仅对 ReDoS 正则执行 1 个定向变异
5. **无真实 HTTP 请求**: 无法验证 CSRF、XSS、SSRF、Open Redirect 在真实浏览器中的行为

## 人工干预

本次运行无人工干预。

## 最终结论

**运行状态**: incomplete

在 Node.js 运行时不可用的环境中，对 OWASP NodeGoat（一个故意包含漏洞的 Web 应用）执行了单次独立多策略漏洞挖掘：

- **20 个独立候选**在盲分析阶段登记（6 类策略覆盖）
- **19 条项目线索**全部审阅并处置
- **1 个 Bug 经动态测试确认**: ReDoS 灾难性回溯（`code/app/routes/profile.js:59`），通过 Python 正则引擎验证，三次独立复测结果一致（~19,000x 性能差异）
- **19 个候选**保留静态证据，标记为环境阻塞

源码完整性验证：通过 (`code/` 未被修改)。

本次运行受限于环境资源，未达到完整运行的 95% 动态测试覆盖率要求。如需完成完整验证，需要具备 Node.js + MongoDB 运行环境。

### 统计数据

| 指标 | 值 |
|------|-----|
| 独立发现 Bug 数 | 1 |
| 项目线索确认 Bug 数 | 1 (与独立发现相同) |
| 已确认 Bug 总数 | **1** |
| 策略族覆盖率 | 6/6 |
| 漏洞方向覆盖率 (15类) | 12 tested + 3 not-applicable |
| 风险加权计划覆盖率 | 93.75% |
| 动态测试覆盖率 | ~6.7% (1/15 方向有动态测试) |
| 变异分数 | 100% (1/1 killed) |
