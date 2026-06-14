# 项目概况

> 开发验证运行：`dev-multistrategy-20260614`。正式比赛 `code/` 当前为空，
> 本文件不代表正式未知系统结论。

## 分析范围

- 样例：`work/tests/fixtures/sample_legacy_app/`
- 输入视为只读；运行前后使用 SHA-256 内容快照验证。
- 本次运行不使用此前报告或生成测试。

## 技术栈

- Python 3.9+。
- 标准库 `unittest`。
- `pyproject.toml` 项目清单。
- 无第三方离线计价模块依赖。

证据：`result/artifacts/evidence/project_discovery.json`。

## 子项目与独立模块

- 根项目：样例存量商店。
- `legacy_shop`：可独立导入和测试的计价包。
- `server.py`：完整服务入口，依赖开发环境未提供的数据库驱动。

## 构建与运行

完整服务启动：

```bash
cd work/tests/fixtures/sample_legacy_app
python3 server.py
```

结果：因缺少 `sample_external_database_driver` 退出，记录为环境阻塞，不是
产品 Bug。

离线测试命令：

```bash
cd work/tests/fixtures/sample_legacy_app
python3 -m unittest discover -s tests -v
```

结果：2 个现有测试通过。

## 入口与接口

- 服务入口：`server.py`，当前环境不可完整启动。
- 公共可调用接口：

  ```python
  checkout_total(subtotal_cents: int, discount_percent: int) -> int
  ```

## 信任边界和攻击面

- 外部服务与离线核心包之间的集成边界。
- 公共函数的参数类型和数值边界。
- 计价计算中的数据完整性关系。
- Python 包公开导出契约。

## 业务约束

- 小计必须是非负整数。
- 折扣必须是 0 到 50 的整数。
- 非法输入必须抛出 `ValueError`。
- 有效折扣不能增加结算金额。

## 完整启动状态与可用降级层

| 层级 | 状态 | 结果 |
|---|---|---|
| 完整系统 | 阻塞 | 缺少本地数据库驱动 |
| 现有测试 | 可用 | 2 项通过 |
| 子项目/模块 | 可用 | `legacy_shop` 可独立导入 |
| 公共调用面 | 可用 | `checkout_total` 可直接测试 |

完整启动失败后继续使用后三级完成测试，没有提前结束运行。

## 未解决的环境问题

- 开发样例不提供数据库驱动，因此未验证服务层网络行为。
- 该阻塞不影响离线计价模块的边界和数据完整性验证。
