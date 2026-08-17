# EXAMPLE：Vue2 微前端项目画像示例（契约格式样例）

> 脱敏示例，仅演示 `devlab-web-context` 模式 B 产出的画像结构。真实执行时以实证值为准。

## 示例画像（`.harness/devlab/context/emas-web-context.yaml`）

```yaml
profile:
  project_name: emas-web
  profile_type: vue-microfrontend
  generated_by: devlab-web-context
  generated_at: "2026-08-14T10:00:00+08:00"
  overall_confidence: high
items:
  - key: tech_stack
    value: "Vue 2.6.14 + vue-router 3.x + vuex 3.x；构建 vue-cli-service 4.x；包管理 yarn 1.22 (lerna monorepo)"
    confidence: confirmed
    evidence: "package.json:1-40; lerna.json:1-20"
    note: ""
  - key: dev_server
    value: "dev.sh 封装启动，主应用端口 21010，子应用 21011-21015；Node 12.22.12 (.nvmrc)；崩溃模式 node OOM errno 134，处置：禁止会话自行重启共享 dev server，报给负责人"
    confidence: confirmed
    evidence: "scripts/dev.sh:1-80; .nvmrc:1"
    note: "实证：node 堆 OOM errno 134"
  - key: module_registry
    value: "运行时子应用清单来自 env VUE_APP_MODULES 数组；未注册子应用=白屏无报错"
    confidence: confirmed
    evidence: "src/shell/register.js:10-30; .env.local.example:5"
    note: "前端台账独有高价值条目"
  - key: dev_proxy
    value: "dev proxy → 网关 http://<internal-ip>:9090；业务 API 前缀 /emas/ms/；业务码约定 code=200 为成功"
    confidence: confirmed
    evidence: "vue.config.js:40-60; .env.development:1"
    note: "e2e.config.js 的 baseUrl 取值来源"
  - key: routing
    value: "hash 模式；跨子应用导航 hash 脏状态需真 reload"
    confidence: confirmed
    evidence: "src/router/index.js:1-50"
    note: ""
  - key: build_deploy
    value: "产物 dist/ 静态文件；publicPath /emas-web/；nginx 托管；环境隔离 .env.local"
    confidence: confirmed
    evidence: "vue.config.js:1-20; deploy/nginx.conf:1-30"
    note: ""
  - key: component_library
    value: "自研组件库二开（DOM 前缀 el- 改为 em-）；全局组件：左树/门户栅格/消息框，使用约束见 ui-components/README"
    confidence: inferred
    evidence: "src/ui-components/README.md:1-20（推断：DOM 前缀与官方文档不一致，源码位置 src/ui-components）"
    note: "二开换肤陷阱，深度验收前需实证 DOM 前缀"
```

## 消费方式

- 模式 A：`devlab-context-bootstrap` 读取本画像，将 `dev_proxy`/`module_registry`/`dev_server` 等条目填入 `.harness/devlab/` 五件套对应小节。
- 模式 B 独立使用：画像即交付物，可直接被 AI 会话/排障/验收读取。
