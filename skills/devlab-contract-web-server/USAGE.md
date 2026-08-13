# devlab-contract-web-server — Usage

## Overview
前后端契约规范技能（contract 技能簇首个）：固化字段类型/序列化/错误码/配置分层契约，落地 schema 校验与契约测试，附联调防错清单。定位介于 devlab-srv-* 与 devlab-web-* 之间。

## When to use
- 前后端分离中大型项目、接口频繁演进。
- 联调反复"字段对不上/类型不匹配/序列化不一致"。

## 可直接复制的中文 Prompt

```text
用 devlab-contract-web-server 固化这些接口的前后端契约：
1) 盘点接口与现存契约问题；
2) 定义字段类型/可空性/枚举/时间格式、序列化(null语义/精度/时区)、错误码结构、配置分层；
3) 给 schema 校验与契约测试落点建议；
4) 输出联调防错清单。
注意：敏感配置不进前端；契约变更走"契约测试先行 + 同步调用侧"。
```
