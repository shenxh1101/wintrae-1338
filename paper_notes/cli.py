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

  # 导入单篇论文
  paper-notes import ./my_papers paper.pdf -s summary.txt --tags "深度学习" "NLP"

  # 批量导入目录
  paper-notes import --dir ./downloads

  # 添加标签
  paper-notes tag --ids 1,2,3 --add "深度学习"

  # 标记已读
  paper-notes tag --ids 1 --read

  # 搜索文献
  paper-notes search "transformer" --tags "深度学习"

  # 导出阅读清单
  paper-notes export list -o reading_list.md

  # 查看统计
  paper-notes stats
  paper-notes stats --monthly
  paper-notes stats --stale
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
    register_search(subparsers)
    register_export(subparsers)
    register_stats(subparsers)

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
