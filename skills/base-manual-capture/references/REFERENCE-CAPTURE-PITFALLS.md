# REFERENCE: 采集实战坑库（Capture Pitfalls）

来自真实系统冒烟验证的踩坑记录。执行 B 阶段前先扫一遍本清单。

## P1. 会话式浏览器工具在轮询型 SPA 上超时

**现象**：browser-use MCP 的 `take_screenshot` / `click` 在持续轮询的仪表盘页面全部超时（等待 network-idle 永不满足），且不产出任何文件。

**规避**：此类系统直接降级到 Playwright（脚本或 MCP），用 `wait_until="domcontentloaded"` + 显式 `wait_for_selector` + 固定 `wait_for_timeout` 组合，**不要**等待 networkidle；`page.screenshot()` 不依赖 network-idle，可稳定出图。

## P2. headless 下仪表盘网格组件塌缩

**现象**：动画/自适应网格类首页（大屏风格 dashboard）在 headless 截图中卡片塌缩成竖条，resize 事件补发也无效。

**规避**：
1. 优先选择功能表单页/列表页作为手册截图对象（渲染稳定）；
2. 大屏首页确需截图时改用有头模式（headed）或真实浏览器会话截取；
3. 在台账 notes 标注"该页 headless 不可截"。

## P3. SPA 路由守卫拦截深链

**现象**：直接 goto 深链（如 `/#/module/page`）被路由守卫重定向回首页，URL 静默回跳。

**规避**：采集路径必须**从首页开始逐级点击导航**；capture-trace 记录点击链而不是只记 URL；C 化回放脚本同样按点击链生成。这正是 trace 需要 selector 序列的原因。

## P4. Windows 控制台 GBK 编码打印中文崩溃

**现象**：采集脚本 `print()` 页面中文文本时抛 `UnicodeEncodeError('gbk', ...)`。

**规避**：脚本开头强制 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")`；页面文本一律写入 UTF-8 文件（如 `_page_text.txt`）而不是打印到控制台。

## P5. 瞬时 toast 类校验提示的截取时机

**现象**：必填校验的 toast 提示 1~2 秒消失，常规"等页面稳定再截"的节奏截不到。

**规避**：触发动作后**立即**（等待 ≤700ms）执行非整页截图；此类步骤在 trace 的 `wait_condition` 标注 "toast present"，回放时同样紧凑截取。

## 回写约定

新坑按 "现象 + 规避" 两段式追加到本文件；属于项目专属的坑写入项目手册目录的备注，不进本清单。
