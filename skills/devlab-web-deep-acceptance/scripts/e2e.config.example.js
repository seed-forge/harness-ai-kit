/**
 * e2e.config.example.js — 环境配置样例。拷贝为 e2e.config.js 后按项目改值。
 * 这是整个工程【唯一需要按项目修改】的文件；lib/run.js 全部从这里读环境差异。
 */
module.exports = {
  // ============ 被测前端 ============
  // 前端入口（dev server 或已部署环境）
  baseUrl: process.env.E2E_BASE_URL || 'http://localhost:8080/app',

  // 登录：表单选择器 + 凭据（也可改用 SSO/Token 模式，见 lib/session.js login 适配点）
  login: {
    hash: '#/login',
    userSelector: 'input[placeholder*="账号"]',   // 按项目登录页改
    passSelector: 'input[placeholder*="密码"]',
    submitSelector: 'button:has-text("登录")',
    user: process.env.E2E_USER || 'admin',
    pass: process.env.E2E_PASS || 'changeme',
  },

  // ============ 假成功嗅探 ============
  // 业务 API URL 匹配（只嗅探命中的 JSON 响应；HTTP200 但 body code!=200 / result:null 记入 swallowed）
  businessApiPattern: /\/api\//,
  // 响应体成功判定：code 字段等于该值视为业务成功（按项目响应包装约定改）
  bizSuccessCode: '200',

  // ============ DB 通道（precheck 与造数用） ============
  // 只读查询代理端点（dbserver 类 HTTP 代理；直连 JDBC 项目需自行适配 lib/precheck.js dbQuery）
  // 留空则 precheck 的 DB 段自动降级为仅静态方言扫描。
  dbServerUrl: process.env.E2E_DBSERVER || '',   // 例: 'http://<db-proxy-host>:<port>/oracle'

  // ============ 间歇抖动豁免表（每条必须附证据注释） ============
  // URL 命中且同路径稍后 2xx（重试成功）才记豁免不记失败；持续失败照常 FAIL
  exemptRetryPatterns: [
    // /order-service\//,   // 2026-XX-XX 实测：首发间歇 404/500 随后 200 恢复（问题 X 同模式）
  ],
  // 纯噪声：直接忽略不参与判定
  noisePatterns: [/sockjs-node/, /favicon/, /\.(js|css|woff2?|ttf|png|ico)(\?|$)/],

  // ============ Vue 微前端路由挂载检测（可选） ============
  // dry-run 时检测 $route.matched.length===0 报"模块未注册"（Vue2 项目开启；React/其他关闭）
  vueRouteCheck: false,
  // 微前端子应用注册提示（检测到未挂载时的修复指引文案）
  routeRegisterHint: '模块未注册进前端路由/子应用清单（如 VUE_APP_MODULES），补名后重启 dev server 再测',

  // ============ 组件库选择器（assert/tableHasRows 等用） ============
  selectors: {
    tableBodyRows: '.el-table__body tbody tr',   // element-ui；按项目组件库改
    tableRowByText: (text) => `.el-table__body tr:has-text("${text}")`,
  },
};
