import os
import sys
import argparse
from datetime import datetime
from typing import List, Optional
from ..database import Database
from ..utils import parse_id_list


def cmd_note(args: argparse.Namespace) -> None:
    db = Database()
    with db:
        if args.list:
            _list_notes(db, args)
        elif args.quote:
            _add_quote(db, args)
        elif args.question:
            _add_question(db, args)
        elif args.note:
            _add_note(db, args)
        elif args.summary:
            _add_summary(db, args)
        elif args.from_file:
            _import_from_file(db, args)
        elif args.resolve:
            _resolve_question(db, args)
        elif args.delete:
            _delete_item(db, args)
        else:
            parser = args._parser
            parser.print_help()


def _validate_paper_ids(db: Database, ids_str: str) -> List[int]:
    ids = parse_id_list(ids_str)
    valid = []
    for pid in ids:
        paper = db.get_paper(pid)
        if paper:
            valid.append(pid)
        else:
            print(f"警告: 文献 ID {pid} 不存在，已跳过")
    if not valid:
        print("错误: 没有有效的文献 ID")
    return valid


def _read_content(args_content: Optional[str], interactive: bool = False,
                  prompt: str = "请输入内容（空行结束）:") -> str:
    if args_content and args_content != '__INTERACTIVE__':
        return args_content.strip()

    if interactive and sys.stdin.isatty():
        print(prompt)
        lines = []
        try:
            while True:
                line = input()
                if not line.strip():
                    break
                lines.append(line)
        except EOFError:
            pass
        return '\n'.join(lines).strip()

    content = sys.stdin.read().strip()
    return content


def _add_quote(db: Database, args: argparse.Namespace) -> None:
    ids = _validate_paper_ids(db, args.ids)
    if not ids:
        return

    content = _read_content(
        args.quote,
        interactive=True,
        prompt="请输入引用摘录内容（空行结束）:"
    )
    if not content:
        print("错误: 摘录内容不能为空")
        return

    for paper_id in ids:
        paper = db.get_paper(paper_id)
        qid = db.add_quote(paper_id, content, args.page, args.context)
        page_info = f" (p{args.page})" if args.page else ""
        print(f"[OK] [{paper_id}] {paper['title']}")
        print(f"     + 引用摘录 #{qid}{page_info}: {content[:50]}..." if len(content) > 50
              else f"     + 引用摘录 #{qid}{page_info}: {content}")


def _add_question(db: Database, args: argparse.Namespace) -> None:
    ids = _validate_paper_ids(db, args.ids)
    if not ids:
        return

    content = _read_content(
        args.question,
        interactive=True,
        prompt="请输入待解决问题（空行结束）:"
    )
    if not content:
        print("错误: 问题内容不能为空")
        return

    status = args.status or 'pending'

    for paper_id in ids:
        paper = db.get_paper(paper_id)
        qid = db.add_question(paper_id, content, status)
        print(f"[OK] [{paper_id}] {paper['title']}")
        print(f"     + 问题 #{qid} [{status}]: {content[:60]}..." if len(content) > 60
              else f"     + 问题 #{qid} [{status}]: {content}")


def _add_note(db: Database, args: argparse.Namespace) -> None:
    ids = _validate_paper_ids(db, args.ids)
    if not ids:
        return

    content = _read_content(
        args.note,
        interactive=True,
        prompt="请输入阅读笔记内容（空行结束）:"
    )
    if not content:
        print("错误: 笔记内容不能为空")
        return

    note_type = args.type or 'general'

    for paper_id in ids:
        paper = db.get_paper(paper_id)
        nid = db.add_note(paper_id, content, note_type, args.page)
        page_info = f" (p{args.page})" if args.page else ""
        type_info = f" [{note_type}]" if note_type != 'general' else ""
        print(f"[OK] [{paper_id}] {paper['title']}")
        print(f"     + 笔记 #{nid}{type_info}{page_info}: {content[:60]}..." if len(content) > 60
              else f"     + 笔记 #{nid}{type_info}{page_info}: {content}")


def _add_summary(db: Database, args: argparse.Namespace) -> None:
    ids = _validate_paper_ids(db, args.ids)
    if not ids:
        return

    content = _read_content(
        args.summary,
        interactive=True,
        prompt="请输入一句话摘要内容（空行结束）:"
    )
    if not content:
        print("错误: 摘要内容不能为空")
        return

    for paper_id in ids:
        paper = db.get_paper(paper_id)
        nid = db.add_note(paper_id, content, 'summary')
        print(f"[OK] [{paper_id}] {paper['title']}")
        print(f"     + 一句话摘要 #{nid}: {content[:80]}..." if len(content) > 80
              else f"     + 一句话摘要 #{nid}: {content}")


def _import_from_file(db: Database, args: argparse.Namespace) -> None:
    ids = _validate_paper_ids(db, args.ids)
    if not ids:
        return

    file_path = os.path.abspath(args.from_file)
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在: {file_path}")
        return

    from ..utils import parse_summary_file
    summary_data = parse_summary_file(file_path)

    for paper_id in ids:
        paper = db.get_paper(paper_id)
        print(f"[{paper_id}] {paper['title']}")

        count = 0
        if summary_data.get('summary'):
            db.add_note(paper_id, summary_data['summary'], 'summary')
            count += 1
            print(f"  + 摘要")

        for quote in summary_data.get('quotes', []):
            db.add_quote(paper_id, quote)
            count += 1
        if summary_data.get('quotes'):
            print(f"  + {len(summary_data['quotes'])} 条引用摘录")

        for question in summary_data.get('questions', []):
            db.add_question(paper_id, question)
            count += 1
        if summary_data.get('questions'):
            print(f"  + {len(summary_data['questions'])} 个待办问题")

        for note in summary_data.get('notes', []):
            db.add_note(paper_id, note, 'general')
            count += 1
        if summary_data.get('notes'):
            print(f"  + {len(summary_data['notes'])} 条阅读笔记")

        if summary_data.get('title') or summary_data.get('authors'):
            updates = {}
            if summary_data.get('title'):
                updates['title'] = summary_data['title']
            if summary_data.get('authors'):
                updates['authors'] = summary_data['authors']
            if summary_data.get('year'):
                updates['year'] = summary_data['year']
            if summary_data.get('venue'):
                updates['venue'] = summary_data['venue']
            if updates:
                db.update_paper(paper_id, **updates)
                print(f"  + 更新元数据: {', '.join(updates.keys())}")

        print(f"  总计: 追加 {count} 条内容")


def _resolve_question(db: Database, args: argparse.Namespace) -> None:
    paper_id = args.resolve
    paper = db.get_paper(paper_id)
    if not paper:
        print(f"错误: 文献 ID {paper_id} 不存在")
        return

    questions = db.get_paper_questions(paper_id)
    if not questions:
        print(f"[{paper_id}] {paper['title']} 没有待办问题")
        return

    print(f"[{paper_id}] {paper['title']} 的待办问题:")
    for i, q in enumerate(questions, 1):
        print(f"  {i}. [{q['status']}] #{q['id']} {q['content'][:60]}...")

    if args.qid:
        qid = args.qid
        status = args.status or 'resolved'
        db.conn.execute('UPDATE questions SET status = ? WHERE id = ?', (status, qid))
        db.conn.commit()
        print(f"\n[OK] 问题 #{qid} 状态已更新为: {status}")
    elif args.all_questions:
        status = args.status or 'resolved'
        count = 0
        for q in questions:
            db.conn.execute('UPDATE questions SET status = ? WHERE id = ?', (status, q['id']))
            count += 1
        db.conn.commit()
        print(f"\n[OK] 已将 {count} 个问题状态更新为: {status}")
    else:
        print("\n使用 --qid <问题ID> 标记单个问题，或 --all 标记全部")


def _delete_item(db: Database, args: argparse.Namespace) -> None:
    item_type, item_id = args.delete
    valid_types = ['note', 'quote', 'question']

    if item_type not in valid_types:
        print(f"错误: 无效的类型 '{item_type}'，有效类型: {', '.join(valid_types)}")
        return

    try:
        item_id_int = int(item_id)
    except ValueError:
        print(f"错误: ID 必须是整数: {item_id}")
        return

    table_map = {
        'note': 'notes',
        'quote': 'quotes',
        'question': 'questions'
    }
    table = table_map[item_type]

    cursor = db.conn.execute(f'SELECT * FROM {table} WHERE id = ?', (item_id_int,))
    item = cursor.fetchone()

    if not item:
        print(f"错误: {item_type} #{item_id_int} 不存在")
        return

    if not args.yes:
        print(f"确认删除 {item_type} #{item_id_int}:")
        content = dict(item).get('content', '')
        print(f"  内容: {content[:80]}...")
        confirm = input("确认删除? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("已取消")
            return

    db.conn.execute(f'DELETE FROM {table} WHERE id = ?', (item_id_int,))
    db.conn.commit()
    print(f"[OK] 已删除 {item_type} #{item_id_int}")


def _list_notes(db: Database, args: argparse.Namespace) -> None:
    paper_id = None
    if args.list is not True:
        try:
            paper_id = int(args.list)
        except (ValueError, TypeError):
            paper_id = None

    if paper_id is not None:
        paper = db.get_paper(paper_id)
        if not paper:
            print(f"错误: 文献 ID {paper_id} 不存在")
            return

        notes = db.get_paper_notes(paper_id)
        quotes = db.get_paper_quotes(paper_id)
        questions = db.get_paper_questions(paper_id)

        print(f"[{paper_id}] {paper['title']}")
        print("=" * 60)

        if notes:
            print(f"\n阅读笔记 ({len(notes)} 条):")
            for n in notes:
                tag = "[摘要]" if n['note_type'] == 'summary' else f"[{n['note_type']}]"
                page = f" (p{n['page_number']})" if n['page_number'] else ""
                print(f"  #{n['id']} {tag}{page}: {n['content'][:80]}")

        if quotes:
            print(f"\n引用摘录 ({len(quotes)} 条):")
            for q in quotes:
                page = f" (p{q['page_number']})" if q['page_number'] else ""
                print(f"  #{q['id']}{page}: \"{q['content'][:80]}\"")

        if questions:
            print(f"\n待办问题 ({len(questions)} 个):")
            for q in questions:
                status_icon = "[!]" if q['status'] == 'pending' else "[~]" if q['status'] == 'researching' else "[x]"
                print(f"  #{q['id']} {status_icon} [{q['status']}]: {q['content'][:80]}")

        if not notes and not quotes and not questions:
            print("\n暂无任何笔记、摘录或问题")
    else:
        all_papers = db.get_all_papers()
        print("所有文献的笔记统计:")
        print("=" * 60)
        for p in all_papers:
            n_count = len(db.get_paper_notes(p['id']))
            q_count = len(db.get_paper_questions(p['id']))
            qu_count = len(db.get_paper_quotes(p['id']))
            total = n_count + q_count + qu_count
            if total > 0 or args.all_list:
                print(f"  [{p['id']}] {p['title'][:50]}")
                print(f"       笔记:{n_count}  摘录:{qu_count}  问题:{q_count}")


def register_note(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        'note',
        help='管理阅读笔记、引用摘录和待办问题',
        description='为已有文献追加阅读笔记、引用摘录、待办问题和摘要'
    )

    target_group = parser.add_argument_group('目标文献')
    target_group.add_argument(
        '--ids',
        help='目标文献ID列表（支持逗号分隔和范围：1,3,5-10）'
    )

    add_group = parser.add_argument_group('添加内容')
    add_group.add_argument(
        '-q', '--quote',
        nargs='?',
        const='__INTERACTIVE__',
        metavar='CONTENT',
        help='添加引用摘录（直接跟内容，或从管道/交互输入）'
    )
    add_group.add_argument(
        '--question',
        nargs='?',
        const='__INTERACTIVE__',
        metavar='CONTENT',
        help='添加待办问题'
    )
    add_group.add_argument(
        '-n', '--note',
        nargs='?',
        const='__INTERACTIVE__',
        metavar='CONTENT',
        help='添加阅读笔记'
    )
    add_group.add_argument(
        '-s', '--summary',
        nargs='?',
        const='__INTERACTIVE__',
        metavar='CONTENT',
        help='添加一句话摘要（适用于组会汇总导出）'
    )
    add_group.add_argument(
        '--from-file',
        metavar='FILE',
        help='从摘要格式文件批量导入笔记、摘录、问题和摘要'
    )

    opt_group = parser.add_argument_group('选项')
    opt_group.add_argument(
        '-p', '--page',
        type=int,
        help='页码（用于笔记和摘录）'
    )
    opt_group.add_argument(
        '-c', '--context',
        help='引用摘录的上下文说明'
    )
    opt_group.add_argument(
        '-t', '--type',
        choices=['general', 'summary', 'method', 'result', 'conclusion'],
        default='general',
        help='笔记类型（默认: general）'
    )
    opt_group.add_argument(
        '--status',
        choices=['pending', 'researching', 'resolved'],
        help='问题状态（默认: pending）'
    )

    list_group = parser.add_argument_group('查看和管理')
    list_group.add_argument(
        '-l', '--list',
        nargs='?',
        const=True,
        metavar='ID',
        help='列出指定文献的所有笔记（不带ID则显示所有文献统计）'
    )
    list_group.add_argument(
        '--all',
        dest='all_list',
        action='store_true',
        help='列出所有文献（包括没有笔记的）'
    )
    list_group.add_argument(
        '--resolve',
        type=int,
        metavar='PAPER_ID',
        help='管理指定文献的待办问题'
    )
    list_group.add_argument(
        '--qid',
        type=int,
        help='待解决问题ID（配合 --resolve 使用）'
    )
    list_group.add_argument(
        '--all-questions',
        action='store_true',
        help='处理所有问题（配合 --resolve 使用）'
    )
    list_group.add_argument(
        '-d', '--delete',
        nargs=2,
        metavar=('TYPE', 'ID'),
        help='删除: note|quote|question + ID'
    )
    list_group.add_argument(
        '-y', '--yes',
        action='store_true',
        help='删除时不提示确认'
    )

    parser.set_defaults(func=cmd_note, _parser=parser)
