# 开发验证说明

正式比赛输入由平台放入根目录 `code/`。开发样例位于
`work/tests/fixtures/sample_legacy_app/`，只用于验证工具和流程，不是
正式运行依赖。

开发端到端验证由当前平台 Agent 在检查样例后动态创建测试到
`result/artifacts/generated_tests/`，执行三次复测，保存原始输出并写入
Trace。样例的具体 Bug 答案不会写入 `INSTRUCTION.md` 或 Skill。

验证同时覆盖：

- 通用 Agent 指令，不依赖品牌专属能力；
- 单次运行内的多策略记录；
- 完整启动不可用时的分层降级规范；
- 源码运行前后完整性快照。
