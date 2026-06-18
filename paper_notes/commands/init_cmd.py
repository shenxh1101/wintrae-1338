import os
import argparse
from ..database import Database


def cmd_init(args: argparse.Namespace) -> None:
    base_dir = os.path.abspath(args.dir)

    db = Database(base_dir)

    if db.is_initialized() and not args.force:
        print(f"错误: 目录 {base_dir} 已经是一个文献库")
        print("使用 --force 参数覆盖现有数据")
        return

    if args.force and db.is_initialized():
        print(f"警告: 将覆盖 {base_dir} 中的现有文献库")

    db.initialize()

    config_path = os.path.join(base_dir, '.paper_notes', 'config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write('{\n  "version": "1.0.0"\n}\n')

    print(f"[OK] 文献库初始化成功: {base_dir}")
    print()
    print("目录结构:")
    print(f"  {os.path.join(base_dir, 'papers')}/      - PDF 文献存储")
    print(f"  {os.path.join(base_dir, 'notes')}/       - 阅读笔记存储")
    print(f"  {os.path.join(base_dir, '.paper_notes')}/ - 数据库和配置")
    print()
    print("下一步操作:")
    print(f"  cd {base_dir}")
    print("  paper-notes import <pdf文件> [选项]")
    print("  paper-notes tag --help")


def register_init(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        'init',
        help='初始化文献目录',
        description='在指定目录创建论文笔记管理的目录结构和数据库'
    )
    parser.add_argument(
        'dir',
        nargs='?',
        default='.',
        help='文献库根目录（默认为当前目录）'
    )
    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='强制重新初始化，覆盖现有数据'
    )
    parser.set_defaults(func=cmd_init)
