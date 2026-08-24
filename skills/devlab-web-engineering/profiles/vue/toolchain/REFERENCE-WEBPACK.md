# Webpack / vue-cli 兼容层

> 存量 Vue2 项目（@vue/cli-service）兼容参考；新项目一律 Vite 主线。

## 识别

- `vue.config.js` / `babel.config.js` + `@vue/cli-service` devDependency

## 关键配置（vue.config.js）

```js
module.exports = {
  publicPath: process.env.NODE_ENV === 'production' ? '/sub-app/' : '/',
  devServer: {
    port: Number(process.env.PORT || 21011),
    host: process.env.HOST || '127.0.0.1',
  },
  transpileDependencies: true,
  chainWebpack: (config) => {
    config.optimization.splitChunks({ chunks: 'all' })
  }
}
```

## 环境变量

- 前缀 `VUE_APP_`；`process.env.VUE_APP_API_BASE_URL`

## 微前端（qiankun）

- 子应用需 `publicPath` 与 activeRule 对齐
- vue.config.js 中 `devServer.headers: { 'Access-Control-Allow-Origin': '*' }`

## 迁移到 Vite 提示

- 移除 @vue/cli-service，加 vite + @vitejs/plugin-vue2（Vue2）
- vue.config.js 配置映射到 vite.config.ts（publicPath→base、devServer→server）
- 完整清单见 `references/REFERENCE-BUILD-TOOLS.md`
