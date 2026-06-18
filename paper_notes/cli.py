#!/usr/bin/env python3
"""
论文阅读笔记管理工具 - 命令行入口
"""

import os
import sys
import argparse
from . import __version__
from .commands import (
    register_init,
    register_import,
    register_tag,
    register_search,
    register_export,
    register_stats,
    register_note,
    register_doctor,
)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='paper-notes',
        description='研究生论文阅读笔记管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
命令示例:

  # 初始化文献库
  paper-notes init ./my_papers

  # 单篇导入（PDF + 摘要）
  paper-notes import paper.pdf -s summary.txt --tags "深度学习"

  # 清单批量导入（支持竖线分隔 / CSV / TSV）
  paper-notes import -b import_list.txt

  # 查看清单格式说明
  paper-notes import -b

  # 追加摘录、问题、笔记
  paper-notes note --ids 1 -q "引用的原文内容" -p 15
  paper-notes note --ids 1,2 --question "这个问题怎么解决？"
  paper-notes note --ids 1 -s "一句话摘要：本文提出了..."
  paper-notes note --ids 1 --from-file new_summary.txt

  # 按批次查看刚导入的文献
  paper-notes search --batch batch_20250619_101530

  # 组会汇总导出
  paper-notes export meeting -o meeting_report.md --topic "深度学习"
  paper-notes export meeting -o weekly.md --status to_review

  # 查看统计
  paper-notes stats
  paper-notes stats --monthly
  paper-notes stats --stale
  paper-notes stats --batches

  # 文献库健康检查
  paper-notes doctor
  paper-notes doctor --fix
        '''
    )

    parser.add_argument(
        '-V', '--version',
        action='version',
        version=f'paper-notes %(version)s'
    )

    subparsers = parser.add_subparsers(
        dest='command',
        title='子命令',
        metavar='<command>'
    )

    register_init(subparsers)
    register_import(subparsers)
    register_tag(subparsers)
    register_note(subparsers)
    register_search(subparsers)
    register_export(subparsers)
    register_stats(subparsers)
    register_doctor(subparsers)

    return parser


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if hasattr(args, 'func'):
            args.func(args)
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(130)
    except Exception as e:
        print(f"发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
