"""woodpeckerctl — Woodpecker CI wrapper CLI。

遵循「CLI Wrapper 两阶段演进原则」：
- Phase 1: 补官方 CLI 缺失的治理能力（audit builds / config）
- Phase 2: 对官方 woodpecker-cli 已有命令做别名路由

官方 CLI: `woodpecker-cli` (Go, woodpecker-ci.org)
本 wrapper: Python + argparse，统一团队 CLI 体验
"""
__version__ = "0.4.0"
