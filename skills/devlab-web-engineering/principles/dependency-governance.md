# 依赖治理（Web）

- **增量安装**：package.json + 锁文件指纹未变则跳过重装（install_deps_incremental）。
- **循环依赖**：monorepo 中检测 A → B → A 循环，打破后提升公共依赖到根。
- **公共依赖提升**：多个子包同版本依赖（如 vue@2.6.14）提升到根 package.json。
- **安全审计**：定期 `pnpm audit` / `npm audit`；高危漏洞登记处理。
- **制品源治理**：私有 registry 为主、官方源降级（见 REFERENCE-REGISTRY-STRATEGY）；
  地址/凭据从 devlab-infra-usage 获取，不硬编码。
- **废弃依赖清理**：doctor.sh 检测 node_modules/.cache 异常与重复版本。
