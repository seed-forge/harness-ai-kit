# Build 工作流（构建 / 打包 / 预览）

## 触发

- 构建失败排障（产物异常 / 资源 404 / 环境差异）
- 多环境构建（test / simulate / prod）
- 构建配置优化（分包、缓存、体积）

## 步骤

```
1. 识别构建工具（vite / webpack / next）
   - vite.config.* / vue.config.js / next.config.* / react-scripts
2. 构建前检查
   - 锁文件与 node_modules 一致性（pnpm install --frozen-lockfile / npm ci）
   - Node 版本符合 .nvmrc / engines
   - 环境变量文件齐全（缺失 key 先报清单）
3. 执行构建（按 profile toolchain）
   - Vite: vite build --mode production
   - Webpack/vue-cli: npm run build:prod
   - Next: next build
4. 构建验证
   - dist/ 存在性与大小；index.html + 入口资源存在
   - 关键路径 200 探测（可配 devlab-qa-ops 深化验收）
5. 产物说明
   - 输出构建报告（产物路径 / 大小 / 环境 / 构建时间）
```

## 排障引用

- `references/REFERENCE-BUILD-TOOLS.md`（Vite/Webpack/Next 配置要点）
- `profiles/vue/REFERENCE-PITFALLS.md`（高频踩坑）
