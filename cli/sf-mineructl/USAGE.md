# mineructl Usage

## When To Use

Use `mineructl` to check a MinerU service and submit or retrieve document
parsing jobs. It never ships a service endpoint or credentials.

## Configure And Verify

Set your endpoint in `~/.harness-ai-kit/config.yaml` under `assets.mineructl`,
or supply `--base-url` for one command.

```bash
python -m pip install sf-mineructl
mineructl --base-url <your-mineru-url> doctor
mineructl --base-url <your-mineru-url> probe
```

## Common Commands

```bash
mineructl submit --url <document-url> --format markdown
mineructl status <task-id>
mineructl result <task-id>
mineructl tasks --limit 20
```

Add `--json` before the command when a script needs machine-readable output.
Use `mineructl --help` before running against a production service.

## 可直接复制的中文 Prompt

```text
请使用 mineructl 检查我配置的 MinerU 服务，并处理一个文档解析任务。
先执行 doctor 或 probe；确认目标服务和提交 URL 后再提交任务，并返回 task id 与查询命令。
```
