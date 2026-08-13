"""evalctl CLI 入口（draft skeleton）。

设计意图见 devlab-eval-driven-agent。本文件为草案骨架：定义子命令契约，
具体实现待管理员立项后补齐（当前各子命令仅打印占位说明）。
"""
from __future__ import annotations

import argparse
import sys

_DRAFT = "[draft] 该子命令为草案骨架，尚未实现；契约见 devlab-eval-driven-agent。"


def _cmd_doctor(args: argparse.Namespace) -> int:
    print("evalctl doctor:")
    print("  - 检查评测集目录 / mock 服务可达性 / sqlparse 可用性（待实现）")
    print(_DRAFT)
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    # 跑评测集（全量/按模块/单用例），输出分模块正确率报告
    print(f"evalctl run  module={args.module} case={args.case}")
    print(_DRAFT)
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    # 与基线比对，标出回归用例
    print(f"evalctl diff  baseline={args.baseline}")
    print(_DRAFT)
    return 0


def _cmd_ingest(args: argparse.Namespace) -> int:
    # 从真实运营/生产数据采集 badcase → 候选评测用例（须脱敏合规）
    print(f"evalctl ingest  from={args.source}")
    print(_DRAFT)
    return 0


def _cmd_feedback(args: argparse.Namespace) -> int:
    # 回流人工标注/运营反馈到评测集
    print("evalctl feedback")
    print(_DRAFT)
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    # 生成分模块质量报告（可对接看板）
    print(f"evalctl report  format={args.format}")
    print(_DRAFT)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="evalctl", description="AI/数据应用评测 CLI (draft)")
    p.add_argument("--version", action="version", version="evalctl 0.1.0")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="环境自检").set_defaults(func=_cmd_doctor)

    pr = sub.add_parser("run", help="跑评测集(全量/模块/单用例)")
    pr.add_argument("--module", default=None, help="仅跑某业务模块")
    pr.add_argument("--case", default=None, help="仅跑某单用例")
    pr.set_defaults(func=_cmd_run)

    pd = sub.add_parser("diff", help="与基线比对回归")
    pd.add_argument("--baseline", required=True, help="基线引用(如 git ref / 报告路径)")
    pd.set_defaults(func=_cmd_diff)

    pi = sub.add_parser("ingest", help="采集真实运营数据为候选评测用例")
    pi.add_argument("--source", required=True, help="运营数据源标识")
    pi.set_defaults(func=_cmd_ingest)

    sub.add_parser("feedback", help="回流人工/运营反馈到评测集").set_defaults(func=_cmd_feedback)

    prp = sub.add_parser("report", help="生成质量报告")
    prp.add_argument("--format", default="markdown", choices=["markdown", "json"])
    prp.set_defaults(func=_cmd_report)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
