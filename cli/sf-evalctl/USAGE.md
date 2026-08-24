# evalctl Usage

## When To Use

Use `evalctl` to inspect the public evaluation-command contract or to exercise
the current trial command surface. The package is intentionally marked trial:
the commands validate their arguments and describe the planned evaluation
workflow, but do not yet execute a production evaluation backend.

## Install And Verify

```bash
python -m pip install sf-evalctl
evalctl --version
evalctl --help
```

## Command Contract

```bash
evalctl doctor
evalctl run [--module <name>] [--case <id>]
evalctl diff --baseline <git-ref-or-report-path>
evalctl ingest --source <source-id>
evalctl feedback
evalctl report [--format markdown|json]
```

Use `evalctl --help` and `<command> --help` before automating a workflow. Do
not treat the current trial output as an evaluation result or release gate.

## 可直接复制的中文 Prompt

```text
请使用 evalctl 检查当前评测任务的命令契约。
先运行 --help，明确该版本仍为 trial；不要把占位输出当成评测结果或发布门禁。
```
