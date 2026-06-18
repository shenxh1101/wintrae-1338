import os
import argparse
from typing import List, Dict, Any
from ..database import Database
from ..utils import (
    format_status,
    format_date,
    print_paper_list
)


def cmd_search(args: argparse.Namespace) -> None:
    db = Database()
    with db:
        if args.detail:
            _show_paper_detail(db, args)
        elif args.tags:
            _search_by_tags_combination(db, args)
        else:
            _search_papers(db, args)


def _search_papers(db: Database, args: argparse.Namespace) -> None:
    papers = db.search_papers(
        keyword=args.keyword,
        tags=args.tag,
        status=args.status,
        progress_min=args.progress_min,
        progress_max=args.progress_max,
        author=args.author,
        year=args.year,
        topic=args.topic
    )

    if not papers:
        print("未找到符合条件的文献")
        return

    print(f"找到 {len(papers)} 篇符合条件的文献:\n")
    print_paper_list(papers, show_tags=args.show_tags, db=db)

    if args.count:
        print(f"\n总计: {len(papers)} 篇")


def _search_by_tags_combination(db: Database, args: argparse.Namespace) -> None:
    tag_list = args.tags
    papers = None

    for tag_name in tag_list:
        tag_papers = set(p['id'] for p in db.get_papers_by_tag(tag_name))
        if papers is None:
            papers = tag_papers
        else:
            papers = papers & tag_papers

    if not papers:
        print(f"未找到同时带有所有标签 {tag_list} 的文献")
        return

    paper_list = []
    for pid in papers:
        paper = db.get_paper(pid)
        if paper:
            if args.status and paper['reading_status'] != args.status:
                continue
            if args.progress_min is not None and paper['reading_progress'] < args.progress_min:
                continue
            if args.progress_max is not None and paper['reading_progress'] > args.progress_max:
                continue
            paper_list.append(paper)

    if not paper_list:
        print("未找到符合条件的文献")
        return

    print(f"找到 {len(paper_list)} 篇同时带有标签 {tag_list} 的文献:\n")
    print_paper_list(paper_list, show_tags=args.show_tags, db=db)


def _show_paper_detail(db: Database, args: argparse.Namespace) -> None:
    paper_id = args.detail

    paper = db.get_paper(paper_id)
    if not paper:
        print(f"错误: 文献 ID {paper_id} 不存在")
        return

    tags = db.get_paper_tags(paper_id)
    notes = db.get_paper_notes(paper_id)
    quotes = db.get_paper_quotes(paper_id)
    questions = db.get_paper_questions(paper_id)

    print("=" * 70)
    print(f"[{paper['id']}] {paper['title']}")
    print("=" * 70)
    print()

    if paper['authors']:
        print(f"作者: {paper['authors']}")
    if paper['year']:
        print(f"年份: {paper['year']}")
    if paper['venue']:
        print(f"会议/期刊: {paper['venue']}")
    print()

    print(f"阅读状态: {format_status(paper['reading_status'])}")
    print(f"阅读进度: {paper['reading_progress']}%")
    print(f"创建时间: {format_date(paper['created_at'])}")
    print(f"更新时间: {format_date(paper['updated_at'])}")
    if paper['last_read_at']:
        print(f"最后阅读: {format_date(paper['last_read_at'])}")
    print()

    if paper['file_path']:
        print(f"PDF 文件: {paper['file_path']}")
    if paper['summary_path']:
        print(f"摘要文件: {paper['summary_path']}")
    print()

    if tags:
        print("标签:")
        tag_groups = {}
        for tag in tags:
            cat = tag['category']
            if cat not in tag_groups:
                tag_groups[cat] = []
            tag_groups[cat].append(tag['name'])

        category_names = {
            'author': '作者',
            'year': '年份',
            'topic': '主题',
            'status': '状态'
        }

        for cat, names in tag_groups.items():
            cat_name = category_names.get(cat, cat)
            print(f"  [{cat_name}] {', '.join(names)}")
        print()

    if quotes:
        print("引用摘录:")
        for i, quote in enumerate(quotes, 1):
            page_info = f" (p{quote['page_number']})" if quote['page_number'] else ""
            print(f"  {i}. {quote['content']}{page_info}")
        print()

    if questions:
        print("待办问题:")
        for i, q in enumerate(questions, 1):
            status = f" [{q['status']}]" if q['status'] != 'pending' else ""
            print(f"  {i}. {q['content']}{status}")
        print()

    if notes:
        print("阅读笔记:")
        for i, note in enumerate(notes, 1):
            note_type = f" ({note['note_type']})" if note['note_type'] != 'general' else ""
            page_info = f" [p{note['page_number']}]" if note['page_number'] else ""
            print(f"  {i}{note_type}{page_info}. {note['content']}")
        print()


def register_search(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        'search',
        help='搜索文献',
        description='按关键词、标签组合、阅读进度等多条件筛选文献'
    )

    parser.add_argument(
        'keyword',
        nargs='?',
        help='关键词搜索（标题、作者、会议）'
    )

    filter_group = parser.add_argument_group('筛选条件')
    filter_group.add_argument(
        '-t', '--tag',
        action='append',
        help='按标签筛选（可多次指定，OR关系）'
    )
    filter_group.add_argument(
        '--tags',
        nargs='+',
        help='按标签组合筛选（AND关系，必须同时包含所有标签）'
    )
    filter_group.add_argument(
        '-s', '--status',
        choices=['unread', 'reading', 'read', 'to_review'],
        help='按阅读状态筛选'
    )
    filter_group.add_argument(
        '--topic',
        help='按主题标签筛选'
    )
    filter_group.add_argument(
        '--author',
        help='按作者筛选'
    )
    filter_group.add_argument(
        '-y', '--year',
        type=int,
        help='按年份筛选'
    )
    filter_group.add_argument(
        '--progress-min',
        type=int,
        help='最低阅读进度 (0-100)'
    )
    filter_group.add_argument(
        '--progress-max',
        type=int,
        help='最高阅读进度 (0-100)'
    )

    output_group = parser.add_argument_group('输出选项')
    output_group.add_argument(
        '--show-tags',
        action='store_true',
        help='显示文献标签'
    )
    output_group.add_argument(
        '--count',
        action='store_true',
        help='仅显示数量'
    )
    output_group.add_argument(
        '-d', '--detail',
        type=int,
        metavar='ID',
        help='显示指定ID文献的详细信息'
    )

    parser.set_defaults(func=cmd_search)
