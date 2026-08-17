# Vue 微前端场景参考（qiankun / micro-app）

> 实证：vue-microfrontend 为当前工作区实战形态（devlab-web-context 实战级 profile）。

## 识别信号

- qiankun：`package.json` 含 `@qiankun/*`；主应用有 registerMicroApps / loadMicroApp 调用
- micro-app：`@micro-zoe/micro-app`
- 自研 shell：主应用自定义路由注册配置

## 主应用（基座）要点

1. **注册表**：registerMicroApps([{ name, entry, container, activeRule }])
   - entry 指向子应用 dev server 或构建产物静态服务
   - activeRule 与主应用路由不冲突
2. **端口协调**：主应用 + 各子应用固定端口映射（如 21010 主 / 21011-21012 子），
   多开发者用用户名哈希段
3. **公共依赖**：vue/vue-router 提升到主应用，子应用 externals 配置防多实例
4. **加载失败**：子应用 dev server 未启动 → 主应用 entry 404；
   先探活子应用端口再排查（doctor.sh 端口检查）

## 子应用要点

1. **生命周期导出**：qiankun 需要 bootstrap/mount/unmount 导出
   （Vue3: createApp 在 mount 内创建，unmount 内销毁）
2. **base 配置**：子应用路由 base 与 activeRule 对齐；`$route.params` 页面
   **刷新即空** → 必须链式导航进入，不可直接刷新 URL
3. **构建产物**：子应用独立 dist；publicPath 按部署路径配置
   （Vite: `base: '/sub-app/'`）
4. **样式隔离**：qiankun 默认 shadow 隔离或 scoped CSS；
   全局样式（reset/字体）由主应用统一注入

## 踩坑（迁移自 REFERENCE-PITFALLS 微前端相关）

- 子应用挂载期错误被吞：L1 用例 reset 勿放在导航后（会清掉 mounted 期错误）
- 复制残留页的 mounted 死调用：盘点期跑「视图→API 模块」死调用比对
- 主应用切换路由后子应用状态丢失：确认 keep-alive / 缓存策略

## 相关

- `references/REFERENCE-MONOREPO.md`（workspaces/Turborepo 编排）
- `workflows/packaging.md`（base/sub-app 交付）
