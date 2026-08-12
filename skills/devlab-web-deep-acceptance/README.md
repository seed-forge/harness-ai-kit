# devlab-web-deep-acceptance — Asset Router

> **AI-Kit Router**：本文件是本 Skill 的**内部资产导航**，只列同级目录下的内部资产（references/scripts/templates）。
> 不列外部 skill/CLI/MCP（外部交互见 `SKILL.md` 的 `## Integration Points` 与 `skill.json` 的 `integrations`）。

## 内部资产地图

| 资产 | 路径 | 用途 |
|------|------|------|
| 主文档 | `SKILL.md` | 七阶段方法论（画像→建模→预检→执行→甄别→审计→回写）、Human Decisions 汇总 |
| 元数据 | `skill.json` | id/version/integrations 等结构化声明 |
| 决策清单 | `decisions.yaml` | HD-1 高危写操作 / HD-2 环境故障处置 |
| 变更记录 | `CHANGELOG.md` | 版本变更历史 |
| 使用指南 | `USAGE.md` | 安装、前置条件、可复制 Prompt |
| 参考文档 | `references/` | 五份专题（分级/假成功/registry schema/五分类/陷阱库），导航见 `references/REFERENCE-INDEX.md` |
| 执行器脚本 | `scripts/` | run.js 唯一入口 + lib 六件套 + tools/dashboard.js + e2e.config.example.js |
| 模板 | `templates/` | registry-module / modules / case / SUMMARY / pending-issues / dashboard 六件套 |

## scripts 结构

```
scripts/
├── e2e.config.example.js   # 环境差异唯一收敛点（拷贝为 e2e.config.js 后改配置）
├── run.js                  # 唯一入口：--dry-run/--precheck/--seed/--case/--all/--audit/--cleanup
├── lib/
│   ├── browser.js          # Playwright 封装：豁免重试/噪声过滤/假成功嗅探（config 驱动）
│   ├── session.js          # 通用表单登录 + preflight 探活
│   ├── api-common.js       # bodyVerdict 六态分诊/captureApis/gotoPageResilient/dbQuery/dbWrite
│   ├── assert.js           # 断言集（noErrors/tableHasRows/noSwallowedErrors...）
│   ├── precheck.js         # 方言静扫 + 表/函数/列三级存在性预检
│   ├── report.js           # 功能点报告 + SUMMARY 落盘
│   └── actions.js          # 最小动作集占位（项目侧自行扩展 _helpers）
└── tools/
    └── dashboard.js        # 全局聚合：dashboard.md + 数据质量告警
```

## 使用说明

- 落地到项目：拷贝 `scripts/` → 项目 `test/e2e/`，`cp e2e.config.example.js e2e.config.js` 改配置，`npm i playwright js-yaml`，先跑 `node run.js --dry-run`。
- 新增 reference 时在 `references/REFERENCE-INDEX.md` 补一行导航。
- 组件库专属原语（左树/特殊选择器等）不进本 skill，留项目侧 `cases/<module>/_helpers.js`。
