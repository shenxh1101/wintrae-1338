import os
import argparse
from datetime import datetime
from typing import List, Optional
from ..database import Database
from ..utils import (
    parse_id_list,
    format_status,
    print_paper_list
)


def cmd_tag(args: argparse.Namespace) -> None:
    db = Database()
    with db:
        if args.list:
            _list_tags(db, args)
        elif args.list_papers:
            _list_papers_by_tag(db, args)
        elif args.add or args.author or args.year_tag or args.topic or args.status:
            _add_tags(db, args)
        elif args.remove:
            _remove_tags(db, args)
        elif args.set_status or args.read or args.to_review or args.unread or args.reading:
            _set_status(db, args)
        elif args.progress is not None:
            _set_progress(db, args)
        elif args.recategorize:
            _recategorize_tag(db, args)
        else:
            parser = args._parser
            parser.print_help()


def _get_target_paper_ids(db: Database, args: argparse.Namespace) -> List[int]:
    if args.ids:
        return parse_id_list(args.ids)

    if args.query:
        papers = db.search_papers(
            keyword=args.query,
            status=args.status_filter
        )
        return [p['id'] for p in papers]

    if args.all:
        papers = db.get_all_papers()
        return [p['id'] for p in papers]

    return []


def _list_tags(db: Database, args: argparse.Namespace) -> None:
    category = args.category
    tags = db.get_all_tags(category)

    if not tags:
        print("没有标签")
        return

    categories = {}
    for tag in tags:
        cat = tag['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(tag)

    category_names = {
        'author': '作者',
        'year': '年份',
        'topic': '主题',
        'status': '状态'
    }

    for cat, tag_list in categories.items():
        cat_name = category_names.get(cat, cat)
        print(f"\n[{cat_name}]")
        for tag in tag_list:
            papers = db.get_papers_by_tag(tag['name'])
            print(f"  {tag['name']} ({len(papers)} 篇)")


def _list_papers_by_tag(db: Database, args: argparse.Namespace) -> None:
    tag_name = args.list_papers
    papers = db.get_papers_by_tag(tag_name)

    if not papers:
        print(f"没有找到带有标签 '{tag_name}' 的文献")
        return

    print(f"标签 '{tag_name}' 的文献列表 ({len(papers)} 篇):")
    print_paper_list(papers, show_tags=False)


def _add_tags(db: Database, args: argparse.Namespace) -> None:
    paper_ids = _get_target_paper_ids(db, args)

    if not paper_ids:
        print("错误: 没有指定目标文献")
        print("使用 --ids 指定文献ID，或 --query 搜索，或 --all 全选")
        return

    valid_ids = []
    for pid in paper_ids:
        paper = db.get_paper(pid)
        if paper:
            valid_ids.append(pid)
        else:
            print(f"警告: 文献 ID {pid} 不存在，已跳过")

    if not valid_ids:
        print("错误: 没有有效的文献ID")
        return

    print(f"将为 {len(valid_ids)} 篇文献添加标签...")
    print()

    tags_to_add = []

    if args.add:
        for tag_name in args.add:
            tags_to_add.append((tag_name, 'topic'))

    if args.author:
        tags_to_add.append((args.author, 'author'))

    if args.year_tag:
        tags_to_add.append((str(args.year_tag), 'year'))

    if args.topic:
        tags_to_add.append((args.topic, 'topic'))

    if args.status:
        tags_to_add.append((args.status, 'status'))

    for paper_id in valid_ids:
        paper = db.get_paper(paper_id)
        print(f"[{paper_id}] {paper['title']}")

        for tag_name, category in tags_to_add:
            tag_id = db.add_tag(tag_name, category)
            db.tag_paper(paper_id, tag_id)
            print(f"  + {tag_name} ({category})")

    print()
    print(f"[OK] 已为 {len(valid_ids)} 篇文献添加标签")


def _remove_tags(db: Database, args: argparse.Namespace) -> None:
    paper_ids = _get_target_paper_ids(db, args)

    if not paper_ids:
        print("错误: 没有指定目标文献")
        return

    valid_ids = []
    for pid in paper_ids:
        if db.get_paper(pid):
            valid_ids.append(pid)

    if not valid_ids:
        print("错误: 没有有效的文献ID")
        return

    print(f"将为 {len(valid_ids)} 篇文献移除标签...")
    print()

    for paper_id in valid_ids:
        paper = db.get_paper(paper_id)
        print(f"[{paper_id}] {paper['title']}")

        for tag_name in args.remove:
            tag = db.get_tag(tag_name)
            if tag:
                db.untag_paper(paper_id, tag['id'])
                print(f"  - {tag_name}")
            else:
                print(f"  ! 标签 '{tag_name}' 不存在")

    print()
    print(f"[OK] 已为 {len(valid_ids)} 篇文献移除标签")


def _set_status(db: Database, args: argparse.Namespace) -> None:
    paper_ids = _get_target_paper_ids(db, args)

    if not paper_ids:
        print("错误: 没有指定目标文献")
        return

    valid_ids = []
    for pid in paper_ids:
        if db.get_paper(pid):
            valid_ids.append(pid)

    if not valid_ids:
        print("错误: 没有有效的文献ID")
        return

    status = None
    if args.set_status:
        status = args.set_status
    elif args.read:
        status = 'read'
    elif args.to_review:
        status = 'to_review'
    elif args.unread:
        status = 'unread'
    elif args.reading:
        status = 'reading'

    if status not in ['unread', 'reading', 'read', 'to_review']:
        print(f"错误: 无效的阅读状态: {status}")
        print("有效状态: unread, reading, read, to_review")
        return

    update_data = {
        'reading_status': status,
        'last_read_at': datetime.now().isoformat()
    }

    if status == 'read':
        update_data['reading_progress'] = 100

    db.update_papers(valid_ids, **update_data)

    print(f"[OK] 已将 {len(valid_ids)} 篇文献标记为 {format_status(status)}")
    print()

    for paper_id in valid_ids:
        paper = db.get_paper(paper_id)
        print(f"  [{paper_id}] {paper['title']}")


def _set_progress(db: Database, args: argparse.Namespace) -> None:
    paper_ids = _get_target_paper_ids(db, args)

    if not paper_ids:
        print("错误: 没有指定目标文献")
        return

    progress = args.progress
    if progress < 0 or progress > 100:
        print("错误: 阅读进度必须在 0-100 之间")
        return

    valid_ids = []
    for pid in paper_ids:
        if db.get_paper(pid):
            valid_ids.append(pid)

    if not valid_ids:
        print("错误: 没有有效的文献ID")
        return

    update_data = {
        'reading_progress': progress,
        'last_read_at': datetime.now().isoformat()
    }

    if progress == 100:
        update_data['reading_status'] = 'read'
    elif progress > 0:
        update_data['reading_status'] = 'reading'

    db.update_papers(valid_ids, **update_data)

    print(f"[OK] 已将 {len(valid_ids)} 篇文献的阅读进度设置为 {progress}%")


def _recategorize_tag(db: Database, args: argparse.Namespace) -> None:
    old_name, new_category = args.recategorize

    valid_categories = ['author', 'year', 'topic', 'status']
    if new_category not in valid_categories:
        print(f"错误: 无效的分类: {new_category}")
        print(f"有效分类: {', '.join(valid_categories)}")
        return

    tag = db.get_tag(old_name)
    if not tag:
        print(f"错误: 标签 '{old_name}' 不存在")
        return

    db.conn.execute('UPDATE tags SET category = ? WHERE name = ?', (new_category, old_name))
    db.conn.commit()

    print(f"[OK] 已将标签 '{old_name}' 的分类从 '{tag['category']}' 改为 '{new_category}'")


def register_tag(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        'tag',
        help='管理文献标签和阅读状态',
        description='为文献打标签、修改阅读状态、批量分类管理'
    )

    target_group = parser.add_argument_group('目标选择')
    target_group.add_argument(
        '--ids',
        help='文献ID列表（支持逗号分隔和范围，如：1,3,5-10）'
    )
    target_group.add_argument(
        '--query',
        help='按关键词搜索选择文献'
    )
    target_group.add_argument(
        '--status-filter',
        choices=['unread', 'reading', 'read', 'to_review'],
        help='按阅读状态筛选'
    )
    target_group.add_argument(
        '--all',
        action='store_true',
        help='选择所有文献'
    )

    list_group = parser.add_argument_group('查看')
    list_group.add_argument(
        '-l', '--list',
        action='store_true',
        help='列出所有标签'
    )
    list_group.add_argument(
        '--category',
        choices=['author', 'year', 'topic', 'status'],
        help='按分类筛选标签列表'
    )
    list_group.add_argument(
        '--list-papers',
        metavar='TAG',
        help='列出带有指定标签的所有文献'
    )

    tag_group = parser.add_argument_group('标签操作')
    tag_group.add_argument(
        '-a', '--add',
        nargs='+',
        help='添加主题标签'
    )
    tag_group.add_argument(
        '-r', '--remove',
        nargs='+',
        help='移除指定标签'
    )
    tag_group.add_argument(
        '--author',
        help='添加作者标签'
    )
    tag_group.add_argument(
        '--year-tag',
        type=int,
        help='添加年份标签'
    )
    tag_group.add_argument(
        '--topic',
        help='添加主题标签'
    )
    tag_group.add_argument(
        '--status',
        help='添加状态标签'
    )
    tag_group.add_argument(
        '--recategorize',
        nargs=2,
        metavar=('TAG', 'CATEGORY'),
        help='修改标签的分类'
    )

    status_group = parser.add_argument_group('状态操作')
    status_group.add_argument(
        '--set-status',
        choices=['unread', 'reading', 'read', 'to_review'],
        help='设置阅读状态'
    )
    status_group.add_argument(
        '--read',
        action='store_true',
        help='标记为已读'
    )
    status_group.add_argument(
        '--to-review',
        action='store_true',
        help='标记为待精读'
    )
    status_group.add_argument(
        '--unread',
        action='store_true',
        help='标记为未读'
    )
    status_group.add_argument(
        '--reading',
        action='store_true',
        help='标记为在读'
    )
    status_group.add_argument(
        '--progress',
        type=int,
        help='设置阅读进度 (0-100)'
    )

    parser.set_defaults(func=cmd_tag, _parser=parser)
