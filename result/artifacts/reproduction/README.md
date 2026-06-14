# 最小复现

本文件属于独立开发运行 `dev-multistrategy-20260614`。

```bash
python3 result/artifacts/reproduction/reproduce_discount_lower_bound.py
```

输入：

```json
{"subtotal_cents": 1000, "discount_percent": -1}
```

预期抛出 `ValueError`；实际返回高于原始小计的结果。
