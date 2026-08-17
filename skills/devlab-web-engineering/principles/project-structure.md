# 项目结构（Web）

## 单仓库（Vue 示例）

```
src/
├── views/         # 路由页面
├── components/    # 通用组件（colocation：组件/样式/测试同目录）
├── composables/   # 组合式函数（Vue3） / hooks（React）
├── stores/        # 状态管理
├── services/      # API 封装层
├── utils/         # 工具函数
├── types/         # 全局类型
└── router/        # 路由配置
```

## Monorepo（微前端/多包）

```
apps/
├── main/          # 主应用（基座）
└── sub-*/         # 子应用（qiankun 注册）
packages/
├── common/        # 共享包（被多包依赖，构建优先）
└── components/    # 组件库
```

## 原则

- app vs lib 区分：可运行（有 dev/start）vs 纯库（无运行脚本）
- 路由参数驱动页必须链式导航进入（`$route.params` 刷新即空）
- 组件工程边界：工程结构归本技能；视觉/交互细节归 devlab-ui-taste-ops
