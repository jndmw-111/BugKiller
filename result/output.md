# 存量系统漏洞挖掘报告

## 运行摘要

- 运行编号：`dev-multistrategy-20260614`
- 运行性质：独立开发样例验证
- 平台 Agent：通用 Agent 协议，不依赖特定品牌或额外 LLM API
- 正式 `code/` 状态：目录为空，未伪造正式输入
- 分析样例：`work/tests/fixtures/sample_legacy_app/`
- 人工干预：无，`logs/interaction.md` 为空
- 运行清单：`result/run_manifest.json`

## 单次运行策略组合

本次在同一独立运行中使用三类策略：

| 策略 | 目标 | 结果 |
|---|---|---|
| 输入与解析 | 折扣类型和数值上下边界 | 确认 1 个下界 Bug |
| 数据完整性与失败路径 | 有效折扣不能增加总额 | 正常控制通过；Bug 触发时关系被违反 |
| 配置与组件集成 | 服务启动依赖与包公开导出 | 服务环境阻塞；离线包导出控制通过 |

其余策略不适用原因已记录在 `result/run_manifest.json`。

## 完整启动与降级执行

1. **完整系统**：执行 `server.py`，因缺少本地数据库驱动失败。
2. **现有测试**：降级执行 2 个离线单元测试，全部通过。
3. **公共调用面**：直接测试 `legacy_shop.checkout_total`。

完整启动失败没有终止运行。环境阻塞证据：
`result/artifacts/evidence/full-start.txt`。

## 测试范围

- 项目识别和源码完整性快照。
- 2 个现有基线测试。
- 2 个本次生成的跨策略控制测试。
- 1 个本次生成的边界候选测试。
- 候选测试在三个独立 Python 进程中复测。
- 1 个最小公共函数复现。
- 18 个作品框架自动化测试。

## 已确认 Bug

### DEV-001：非法折扣下界未被拒绝

- 状态：**已确认**
- 主要策略：输入与解析
- 关联策略：数据完整性与失败路径
- 执行层级：公共调用面
- 公开约束：`discount_percent` 必须为 0 到 50 的整数；非法输入必须
  抛出 `ValueError`；有效折扣不得增加结算金额。
- 触发输入：`subtotal_cents=1000`，`discount_percent=-1`
- 预期结果：抛出 `ValueError`
- 实际结果：未抛出异常，返回 `actual_total=1010`，高于原始小计 1000。
- 动态测试：
  `result/artifacts/generated_tests/test_discount_lower_bound.py`
- 最小复现：
  `result/artifacts/reproduction/reproduce_discount_lower_bound.py`

## 三次复测

| 次数 | 初始方式 | 结果 | 退出码 | 证据 |
|---|---|---|---:|---|
| 1 | 新 Python 进程 | `ValueError not raised` | 1 | `result/artifacts/evidence/retest-1.txt` |
| 2 | 新 Python 进程 | `ValueError not raised` | 1 | `result/artifacts/evidence/retest-2.txt` |
| 3 | 新 Python 进程 | `ValueError not raised` | 1 | `result/artifacts/evidence/retest-3.txt` |

三次结果一致。基线与跨策略控制测试通过，生成测试能够正常加载目标函数，
因此已排除完整启动依赖、Python 环境和测试代码错误。

## 各策略结果

### 输入与解析

- 检查最近的非法下界值。
- 发现无效折扣被接受。
- 三次复现并最小化，结论为已确认。

### 数据完整性与失败路径

- 对 0、1、20、50 等有效折扣执行关系控制。
- 正常输入均满足 `0 <= total <= subtotal`。
- Bug 输入导致总额增加，作为关联状态证据。

### 配置与组件集成

- 完整服务因缺少数据库驱动阻塞。
- 没有把环境依赖错误标记为产品 Bug。
- 离线包公开导出和函数调用控制通过。

## 最小复现步骤

```bash
python3 result/artifacts/reproduction/reproduce_discount_lower_bound.py
```

关键输出：

```json
{"actual_total": 1010, "total_increased": true}
```

## 证据索引

- 运行清单：`result/run_manifest.json`
- 项目识别：`result/artifacts/evidence/project_discovery.json`
- 源码运行前快照：`result/artifacts/evidence/source-before.json`
- 源码完整性校验：`result/artifacts/evidence/source-integrity.txt`
- 完整启动失败：`result/artifacts/evidence/full-start.txt`
- 基线测试：`result/artifacts/evidence/baseline-tests.txt`
- 策略控制：`result/artifacts/evidence/strategy-controls.txt`
- 三次复测：`result/artifacts/evidence/retest-1.txt` 至 `retest-3.txt`
- 最小复现：`result/artifacts/evidence/minimal-reproduction.txt`
- 框架测试：`result/artifacts/evidence/framework-tests.txt`
- Trace：`logs/trace/dev-multistrategy-20260614.jsonl`

## 未确认候选与排除项

- 服务启动缺少数据库驱动：环境阻塞，不是产品 Bug。
- 身份权限策略不适用：样例没有身份、角色、租户或资源归属。
- 状态机策略不适用：公共计价函数无持久状态。
- 文件和注入策略不适用：样例无文件、模板、查询、命令或序列化输入。

## 限制和未覆盖范围

- 这是开发样例验证，不是正式比赛未知系统结论。
- 服务层因刻意缺失的开发依赖未启动，未测试网络行为。
- 正式运行必须重新对 `code/` 进行独立发现和动态测试。

## 最终结论

**开发验证成功。** 单次运行采用三种策略；完整服务启动失败后，Agent
降级到现有测试和公共调用面继续执行，最终动态生成测试并三次确认一个
无破坏逻辑 Bug。结果未依赖其他运行，也未修改输入源码。
