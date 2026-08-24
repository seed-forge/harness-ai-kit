# loopctl Usage

## When To Use

Use `loopctl` to create, inspect, validate, and run Loop assets in a
`harness-ai-kit` checkout or project that contains Loop manifests.

## Install And Verify

```bash
python -m pip install sf-loopctl
loopctl --version
loopctl --help
```

## Common Commands

```bash
loopctl list
loopctl init <loop-id> --name "<display-name>" --output <directory>
loopctl validate <loop-id>
loopctl doctor <loop-id>
loopctl run <loop-id>
loopctl status <loop-id>
loopctl history <loop-id>
```

`init` refuses to overwrite an existing directory. Run `loopctl <command>
--help` before using lifecycle commands such as `pause`, `resume`, `cancel`,
or `promote`.

## 可直接复制的中文 Prompt

```text
请使用 loopctl 检查当前项目中的 Loop 资产。
先列出和校验资产；涉及运行、暂停、恢复、取消或晋级前，先展示命令作用范围与状态。
```
