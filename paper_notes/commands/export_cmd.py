import os
import argparse
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any
from ..database import Database
from ..utils import (
    format_status,
    format_date,
    parse_id_list
)


def cmd_export(args: argparse.Namespace) -> None:
    db = Database()
    with db:
        if args.type == 'list':
            _export_reading_list(db, args)
        elif args.type == 'quotes':
            _export_quotes(db, args)
        elif args.type == 'questions':
            _export_questions(db, args)
        elif args.type == 'meeting':
            _export_meeting(db, args)
        elif args.type == 'all':
            _export_all(db, args)
        else:
            parser = args._parser
            parser.print_help()


def _get_papers_by_topic(db: Database) -> Dict[str, List[Dict[str, Any]]]:
    topic_tags = db.get_all_tags('topic')
    result = defaultdict(list)
    uncategorized = []

    all_papers = db.get_all_papers()

    for paper in all_papers:
        tags = db.get_paper_tags(paper['id'])
        paper_topics = [t['name'] for t in tags if t['category'] == 'topic']

        if paper_topics:
            for topic in paper_topics:
                result[topic].append(paper)
        else:
            uncategorized.append(paper)

    if uncategorized:
        result['未分类'] = uncategorized

    return result


def _get_target_papers(db: Database, args: argparse.Namespace) -> List[Dict[str, Any]]:
    if args.ids:
        ids = parse_id_list(args.ids)
        papers = []
        for pid in ids:
            paper = db.get_paper(pid)
            if paper:
                papers.append(paper)
        return papers

    if args.topic:
        return db.get_papers_by_tag(args.topic)

    if args.status:
        return db.search_papers(status=args.status)

    return db.get_all_papers()


def _papers_by_topic_from_list(db: Database, papers: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    result = defaultdict(list)
    uncategorized = []

    for paper in papers:
        tags = db.get_paper_tags(paper['id'])
        paper_topics = [t['name'] for t in tags if t['category'] == 'topic']
        if paper_topics:
            for topic in paper_topics:
                result[topic].append(paper)
        else:
            uncategorized.append(paper)

    if uncategorized:
        result['未分类'] = uncategorized

    return result


def _export_reading_list(db: Database, args: argparse.Namespace) -> None:
    papers = _get_target_papers(db, args)
    papers_by_topic = _papers_by_topic_from_list(db, papers)
    papers_by_topic = dict(sorted(papers_by_topic.items()))

    output_lines = []

    output_lines.append("# 论文阅读清单")
    output_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output_lines.append("")

    total = sum(len(papers) for papers in papers_by_topic.values())
    output_lines.append(f"总计: {total} 篇文献，分为 {len(papers_by_topic)} 个主题")
    output_lines.append("")

    for topic, papers in papers_by_topic.items():
        output_lines.append(f"## {topic} ({len(papers)} 篇)")
        output_lines.append("-" * 50)
        output_lines.append("")

        for i, paper in enumerate(papers, 1):
            status_icon = {
                'unread': '[ ]',
                'reading': '[~]',
                'read': '[x]',
                'to_review': '[!]'
            }.get(paper['reading_status'], '[ ]')

            line = f"{i}. {status_icon} **{paper['title']}**"
            if paper['authors']:
                line += f" - {paper['authors']}"
            if paper['year']:
                line += f" ({paper['year']})"
            output_lines.append(line)

            meta_parts = []
            meta_parts.append(f"状态: {format_status(paper['reading_status'])}")
            meta_parts.append(f"进度: {paper['reading_progress']}%")
            if paper['venue']:
                meta_parts.append(f"会议: {paper['venue']}")
            output_lines.append(f"   {' | '.join(meta_parts)}")

            notes = db.get_paper_notes(paper['id'])
            if notes:
                output_lines.append(f"   笔记: {len(notes)} 条")

            quotes = db.get_paper_quotes(paper['id'])
            if quotes:
                output_lines.append(f"   摘录: {len(quotes)} 条")

            questions = db.get_paper_questions(paper['id'])
            if questions:
                pending = [q for q in questions if q['status'] == 'pending']
                if pending:
                    output_lines.append(f"   待解决问题: {len(pending)} 个")

            output_lines.append("")

        output_lines.append("")

    _write_output(output_lines, args.output, args.format)
    print(f"[OK] 已导出阅读清单: {len(papers_by_topic)} 个主题，共 {total} 篇文献")


def _export_quotes(db: Database, args: argparse.Namespace) -> None:
    papers = _get_target_papers(db, args)

    output_lines = []
    output_lines.append("# 引用摘录")
    output_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output_lines.append("")

    all_quotes = []

    for paper in papers:
        quotes = db.get_paper_quotes(paper['id'])
        for quote in quotes:
            all_quotes.append({
                'paper': paper,
                'quote': quote
            })

    output_lines.append(f"总计: {len(all_quotes)} 条引用摘录")
    output_lines.append("")

    if args.group_by_paper:
        for paper in papers:
            quotes = db.get_paper_quotes(paper['id'])
            if not quotes:
                continue

            output_lines.append(f"## {paper['title']}")
            if paper['authors']:
                output_lines.append(f"*{paper['authors']}*")
            output_lines.append("")

            for i, quote in enumerate(quotes, 1):
                page_info = f" (第 {quote['page_number']} 页" if quote['page_number'] else ""
                output_lines.append(f"{i}. > {quote['content']}{page_info}")
                if quote['context']:
                    output_lines.append(f"   上下文: {quote['context']}")
                output_lines.append("")
    else:
        for i, item in enumerate(all_quotes, 1):
            paper = item['paper']
            quote = item['quote']

            output_lines.append(f"### {i}. {paper['title']}")
            output_lines.append(f"*{paper['authors']}*")
            output_lines.append("")
            page_info = f" (第 {quote['page_number']} 页)" if quote['page_number'] else ""
            output_lines.append(f"> {quote['content']}{page_info}")
            if quote['context']:
                output_lines.append("")
                output_lines.append(f"**上下文**: {quote['context']}")
            output_lines.append("")

    _write_output(output_lines, args.output, args.format)
    print(f"[OK] 已导出 {len(all_quotes)} 条引用摘录")


def _export_questions(db: Database, args: argparse.Namespace) -> None:
    papers = _get_target_papers(db, args)

    output_lines = []
    output_lines.append("# 待办问题")
    output_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output_lines.append("")

    all_questions = []

    for paper in papers:
        status_filter = args.question_status if hasattr(args, 'question_status') else None
        questions = db.get_paper_questions(paper['id'], status_filter)
        for q in questions:
            all_questions.append({
                'paper': paper,
                'question': q
            })

    output_lines.append(f"总计: {len(all_questions)} 个问题")
    output_lines.append("")

    for i, item in enumerate(all_questions, 1):
        paper = item['paper']
        question = item['question']

        status_icon = {
            'pending': '[!] 待解决',
            'resolved': '[x] 已解决',
            'researching': '[~] 研究中'
        }.get(question['status'], '[!] 待解决')

        output_lines.append(f"### {i}. [{status_icon}] {question['content']}")
        output_lines.append("")
        output_lines.append(f"**文献**: {paper['title']}")
        if paper['authors']:
            output_lines.append(f"**作者**: {paper['authors']}")
        output_lines.append(f"**创建时间**: {format_date(question['created_at'])}")
        output_lines.append("")

    _write_output(output_lines, args.output, args.format)
    print(f"[OK] 已导出 {len(all_questions)} 个待办问题")


def _get_summary_note(db: Database, paper_id: int) -> str:
    notes = db.get_paper_notes(paper_id)
    summary_notes = [n for n in notes if n['note_type'] == 'summary']
    if summary_notes:
        return summary_notes[0]['content']
    general_notes = [n for n in notes if n['note_type'] in ('general', 'conclusion', 'result')]
    if general_notes:
        return general_notes[0]['content']
    return '(暂无摘要，可用 note --summary 添加)'


def _export_meeting(db: Database, args: argparse.Namespace) -> None:
    output_lines = []

    title = getattr(args, 'meeting_title', None) or '组会阅读报告'
    output_lines.append(f"# {title}")
    output_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output_lines.append("")

    papers = _get_target_papers(db, args)

    if getattr(args, 'status', None):
        papers = [p for p in papers if p['reading_status'] == getattr(args, 'status')]

    if getattr(args, 'topic', None):
        topic = args.topic
        tagged_ids = set(p['id'] for p in db.get_papers_by_tag(topic))
        papers = [p for p in papers if p['id'] in tagged_ids]

    if not papers:
        output_lines.append("没有符合筛选条件的文献")
        _write_output(output_lines, args.output, args.format)
        print("[OK] 组会汇总（无数据）")
        return

    papers_by_topic = defaultdict(list)
    uncategorized = []
    for paper in papers:
        tags = db.get_paper_tags(paper['id'])
        topics = [t['name'] for t in tags if t['category'] == 'topic']
        if topics:
            for topic in topics:
                papers_by_topic[topic].append(paper)
        else:
            uncategorized.append(paper)
    if uncategorized:
        papers_by_topic['未分类'] = uncategorized

    total_papers = len(papers)
    total_questions = 0
    total_to_review = 0

    output_lines.append(f"**总览**")
    output_lines.append(f"- 文献总数: {total_papers} 篇")
    output_lines.append(f"- 涉及主题: {len(papers_by_topic)} 个")
    output_lines.append("")

    for paper in papers:
        if paper['reading_status'] == 'to_review':
            total_to_review += 1
        questions = db.get_paper_questions(paper['id'], 'pending')
        total_questions += len(questions)

    output_lines.append(f"- 待精读: {total_to_review} 篇")
    output_lines.append(f"- 未解决问题: {total_questions} 个")
    output_lines.append("")

    output_lines.append("---")
    output_lines.append("")

    output_lines.append("## 一、按主题阅读摘要")
    output_lines.append("")

    sorted_topics = sorted(papers_by_topic.keys())
    for topic in sorted_topics:
        topic_papers = papers_by_topic[topic]
        output_lines.append(f"### {topic}（{len(topic_papers)} 篇）")
        output_lines.append("")

        for i, paper in enumerate(topic_papers, 1):
            paper_id = paper['id']
            summary = _get_summary_note(db, paper_id)
            status = format_status(paper['reading_status'])
            authors = paper['authors'] or ''
            year = paper['year'] and f"({paper['year']})" or ''
            output_lines.append(f"**{i}. {paper['title']}**")
            meta_parts = []
            if authors:
                meta_parts.append(authors)
            if year:
                meta_parts.append(str(year))
            if paper['venue']:
                meta_parts.append(paper['venue'])
            if meta_parts:
                output_lines.append(f"*{', '.join(meta_parts)}*")
            output_lines.append(f"- **阅读状态**: {status} | **进度**: {paper['reading_progress']}%")
            output_lines.append(f"- **一句话摘要**: {summary}")
            output_lines.append("")

        output_lines.append("")

    output_lines.append("## 二、待精读清单")
    output_lines.append("")

    to_review_papers = [p for p in papers if p['reading_status'] == 'to_review']
    if to_review_papers:
        for i, paper in enumerate(to_review_papers, 1):
            summary = _get_summary_note(db, paper['id'])
            output_lines.append(f"{i}. **{paper['title']}**")
            authors = paper['authors'] or ''
            year = paper['year'] and f" ({paper['year']})" or ''
            if paper['authors'] or paper['year']:
                output_lines.append(f"   *{authors}{year}*")
            output_lines.append(f"   原因/计划: {summary}")
            output_lines.append("")
    else:
        output_lines.append("_暂无待精读文献，继续保持！")
        output_lines.append("")

    output_lines.append("## 三、未解决问题汇总")
    output_lines.append("")

    all_pending = []
    for paper in papers:
        questions = db.get_paper_questions(paper['id'], 'pending')
        for q in questions:
            all_pending.append((paper, q))

    if all_pending:
        for i, (paper, q) in enumerate(all_pending, 1):
            output_lines.append(f"{i}. **{q['content']}**")
            output_lines.append(f"   文献: {paper['title']}")
            if paper['authors']:
                output_lines.append(f"   作者: {paper['authors']}")
            output_lines.append(f"   创建: {format_date(q['created_at'])}")
            output_lines.append("")
    else:
        output_lines.append("_太棒了！没有未解决的问题_")
        output_lines.append("")

    output_lines.append("---")
    output_lines.append("")
    output_lines.append(f"_本报告由 paper-notes 工具自动生成_")

    _write_output(output_lines, args.output, args.format)
    print(f"[OK] 组会汇总报告已生成")
    print(f"     文献: {total_papers} 篇 | 待精读: {total_to_review} 篇 | 问题: {total_questions} 个")


def _export_all(db: Database, args: argparse.Namespace) -> None:
    base_name = os.path.splitext(args.output)[0] if args.output else 'export'

    original_output = args.output

    args.output = f"{base_name}_reading_list.md"
    args.type = 'list'
    _export_reading_list(db, args)

    args.output = f"{base_name}_quotes.md"
    args.type = 'quotes'
    _export_quotes(db, args)

    args.output = f"{base_name}_questions.md"
    args.type = 'questions'
    _export_questions(db, args)

    print(f"\n[OK] 已导出所有文件到: {os.path.dirname(os.path.abspath(base_name)) or '.'}")


def _write_output(lines: List[str], output_path: str = None, fmt: str = 'md') -> None:
    content = '\n'.join(lines)

    if fmt == 'txt':
        content = content.replace('# ', '').replace('## ', '').replace('### ', '')
        content = content.replace('**', '').replace('*', '')
        content = content.replace('> ', '')

    if output_path:
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[OK] 已写入文件: {output_path}")
    else:
        print(content)


def register_export(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        'export',
        help='导出阅读清单、引用摘录和待办问题',
        description='生成按主题分组的阅读清单、引用摘录和待办问题'
    )

    parser.add_argument(
        'type',
        nargs='?',
        choices=['list', 'quotes', 'questions', 'meeting', 'all'],
        default='list',
        help='导出类型: list(阅读清单), quotes(引用摘录), questions(待办问题), meeting(组会汇总), all(全部)'
    )

    filter_group = parser.add_argument_group('筛选条件')
    filter_group.add_argument(
        '--ids',
        help='指定文献ID列表（如：1,3,5-10）'
    )
    filter_group.add_argument(
        '--topic',
        help='按主题筛选（组会汇总、阅读清单支持）'
    )
    filter_group.add_argument(
        '--status',
        choices=['unread', 'reading', 'read', 'to_review'],
        help='按阅读状态筛选（组会汇总、阅读清单、引用摘录支持）'
    )
    filter_group.add_argument(
        '--question-status',
        choices=['pending', 'resolved', 'researching'],
        default='pending',
        help='问题状态筛选（仅待办问题导出）'
    )

    output_group = parser.add_argument_group('输出选项')
    output_group.add_argument(
        '-o', '--output',
        help='输出文件路径'
    )
    output_group.add_argument(
        '-f', '--format',
        choices=['md', 'txt'],
        default='md',
        help='输出格式'
    )
    output_group.add_argument(
        '--group-by-paper',
        action='store_true',
        help='按文献分组显示（仅引用摘录导出）'
    )

    meeting_group = parser.add_argument_group('组会汇总选项')
    meeting_group.add_argument(
        '--meeting-title',
        default='组会阅读报告',
        help='组会汇总报告的标题（默认：组会阅读报告）'
    )

    parser.set_defaults(func=cmd_export, _parser=parser)
