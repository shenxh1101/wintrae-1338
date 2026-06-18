import os
import argparse
from ..database import Database


def cmd_init(args: argparse.Namespace) -> None:
    base_dir = os.path.abspath(args.dir)

    db = Database(base_dir)

    was_initialized = db.is_initialized()

    if was_initialized and not args.force:
        print(f"错误: 目录 {base_dir} 已经是一个文献库")
        print("使用 --force 参数覆盖现有数据（将清空数据库、papers/ 和 notes/）")
        return

    if was_initialized and args.force:
        if args.keep_papers or args.keep_notes:
            print(f"警告: 将重置 {base_dir} 中的文献库数据库", end="")
            kept = []
            if args.keep_papers:
                kept.append("papers/ 目录")
            if args.keep_notes:
                kept.append("notes/ 目录")
            if kept:
                print(f"（保留: {', '.join(kept)}）")
            else:
                print()
        else:
            print(f"警告: 将清空并重建 {base_dir} 中的所有数据（数据库、papers/、notes/）")

        db.reset(keep_papers=args.keep_papers, keep_notes=args.keep_notes)
    else:
        db.initialize()

    config_path = os.path.join(base_dir, '.paper_notes', 'config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write('{\n  "version": "1.0.0"\n}\n')

    print(f"[OK] 文献库初始化成功: {base_dir}")
    if was_initialized and args.force:
        print(f"     模式: 强制重置（keep_papers={args.keep_papers}, keep_notes={args.keep_notes}）")
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
        help='强制重新初始化，覆盖现有数据（清空数据库、papers/ 和 notes/）'
    )
    parser.add_argument(
        '--keep-papers',
        action='store_true',
        help='强制重置时保留 papers/ 目录中的PDF文件'
    )
    parser.add_argument(
        '--keep-notes',
        action='store_true',
        help='强制重置时保留 notes/ 目录中的笔记文件'
    )
    parser.set_defaults(func=cmd_init)
