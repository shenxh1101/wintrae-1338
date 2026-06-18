import os
import glob
import argparse
from typing import List, Dict, Any
from ..database import Database
from ..utils import (
    parse_pdf_filename,
    parse_summary_file,
    extract_pdf_info,
    copy_file_to_dir,
    safe_filename,
    print_paper_list
)


def cmd_import(args: argparse.Namespace) -> None:
    db = Database()
    with db:
        if args.summary and args.pdf:
            _import_single(db, args)
        elif args.dir:
            _import_directory(db, args)
        elif args.batch:
            _import_batch(db, args)
        else:
            parser = args._parser
            parser.print_help()


def _import_single(db: Database, args: argparse.Namespace) -> None:
    pdf_path = os.path.abspath(args.pdf)

    if not os.path.exists(pdf_path):
        print(f"错误: PDF 文件不存在: {pdf_path}")
        return

    if not pdf_path.lower().endswith('.pdf'):
        print(f"错误: 不是 PDF 文件: {pdf_path}")
        return

    pdf_info = extract_pdf_info(pdf_path)
    filename_info = parse_pdf_filename(os.path.basename(pdf_path))

    title = args.title or pdf_info['title'] or filename_info['title']
    authors = args.authors or pdf_info['authors'] or filename_info['authors']
    year = args.year or filename_info['year']
    venue = args.venue or filename_info['venue']

    existing = db.get_paper_by_title(title)
    if existing and not args.force:
        print(f"警告: 已存在标题相同的文献: {title}")
        print(f"  ID: {existing['id']}")
        print("使用 --force 参数覆盖")
        return

    dst_pdf_path = copy_file_to_dir(pdf_path, db.papers_dir, args.force)

    summary_path = None
    summary_data = {}
    if args.summary:
        summary_src = os.path.abspath(args.summary)
        if os.path.exists(summary_src):
            summary_data = parse_summary_file(summary_src)
            safe_name = safe_filename(title)
            summary_dst = os.path.join(db.notes_dir, f"{safe_name}_summary.txt")
            os.makedirs(os.path.dirname(summary_dst), exist_ok=True)
            with open(summary_src, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(summary_dst, 'w', encoding='utf-8') as f:
                    f.write(content)
            summary_path = summary_dst

            if summary_data.get('title'):
                title = summary_data['title']
            if summary_data.get('authors'):
                authors = summary_data['authors']
            if summary_data.get('year'):
                year = summary_data['year']
            if summary_data.get('venue'):
                venue = summary_data['venue']

    if existing and args.force:
        paper_id = existing['id']
        db.update_paper(
            paper_id,
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            file_path=dst_pdf_path,
            summary_path=summary_path
        )
        print(f"[OK] 已更新文献: {title}")
    else:
        paper_id = db.add_paper(
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            file_path=dst_pdf_path,
            summary_path=summary_path
        )
        print(f"[OK] 已导入文献: {title}")

    if summary_data.get('summary'):
        db.add_note(paper_id, summary_data['summary'], 'summary')
        print(f"  - 已添加摘要")

    for quote in summary_data.get('quotes', []):
        db.add_quote(paper_id, quote)
    if summary_data.get('quotes'):
        print(f"  - 已添加 {len(summary_data['quotes'])} 条引用摘录")

    for question in summary_data.get('questions', []):
        db.add_question(paper_id, question)
    if summary_data.get('questions'):
        print(f"  - 已添加 {len(summary_data['questions'])} 个待办问题")

    for note in summary_data.get('notes', []):
        db.add_note(paper_id, note, 'general')
    if summary_data.get('notes'):
        print(f"  - 已添加 {len(summary_data['notes'])} 条阅读笔记")

    if args.tags:
        for tag_name in args.tags:
            tag_id = db.add_tag(tag_name, 'topic')
            db.tag_paper(paper_id, tag_id)
        print(f"  - 已添加标签: {', '.join(args.tags)}")

    if args.author:
        tag_id = db.add_tag(args.author, 'author')
        db.tag_paper(paper_id, tag_id)
        print(f"  - 已添加作者标签: {args.author}")

    if args.year_tag:
        tag_id = db.add_tag(str(args.year_tag), 'year')
        db.tag_paper(paper_id, tag_id)
        print(f"  - 已添加年份标签: {args.year_tag}")

    print()
    print(f"文献 ID: {paper_id}")


def _import_directory(db: Database, args: argparse.Namespace) -> None:
    dir_path = os.path.abspath(args.dir)

    if not os.path.isdir(dir_path):
        print(f"错误: 目录不存在: {dir_path}")
        return

    pdf_files = glob.glob(os.path.join(dir_path, '**', '*.pdf'), recursive=True)

    if not pdf_files:
        print(f"在目录中未找到 PDF 文件: {dir_path}")
        return

    print(f"找到 {len(pdf_files)} 个 PDF 文件，开始导入...")
    print()

    imported = []
    skipped = []

    for pdf_path in pdf_files:
        try:
            pdf_info = extract_pdf_info(pdf_path)
            filename_info = parse_pdf_filename(os.path.basename(pdf_path))

            title = pdf_info['title'] or filename_info['title']
            authors = pdf_info['authors'] or filename_info['authors']
            year = filename_info['year']
            venue = filename_info['venue']

            existing = db.get_paper_by_title(title)
            if existing and not args.force:
                skipped.append(title)
                print(f"跳过 (已存在): {title}")
                continue

            dst_pdf_path = copy_file_to_dir(pdf_path, db.papers_dir, args.force)

            if existing and args.force:
                paper_id = existing['id']
                db.update_paper(
                    paper_id,
                    title=title,
                    authors=authors,
                    year=year,
                    venue=venue,
                    file_path=dst_pdf_path
                )
                print(f"更新: {title}")
            else:
                paper_id = db.add_paper(
                    title=title,
                    authors=authors,
                    year=year,
                    venue=venue,
                    file_path=pdf_path,
                    summary_path=None
                )
                print(f"导入: {title}")

            if args.tags:
                for tag_name in args.tags:
                    tag_id = db.add_tag(tag_name, 'topic')
                    db.tag_paper(paper_id, tag_id)

            imported.append({'id': paper_id, 'title': title})

        except Exception as e:
            skipped.append(title)
            print(f"错误: {title} - {e}")

    print()
    print(f"完成: 成功导入 {len(imported)} 篇，跳过 {len(skipped)} 篇")


def _import_batch(db: Database, args: argparse.Namespace) -> None:
    batch_file = os.path.abspath(args.batch)

    if not os.path.exists(batch_file):
        with open(batch_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
    else:
        import sys
        lines = [line.strip() for line in sys.stdin if line.strip()]

    if not lines:
        print("错误: 没有提供导入列表")
        return

    print(f"批量导入 {len(lines)} 篇文献...")
    print()

    imported = []

    for line in lines:
        parts = line.split('|')
        if len(parts) < 2:
            print(f"跳过格式错误的行: {line}")
            continue

        title = parts[0].strip()
        pdf_path = parts[1].strip() if len(parts) > 1 else None
        authors = parts[2].strip() if len(parts) > 2 else None
        year = int(parts[3].strip()) if len(parts) > 3 and parts[3].strip().isdigit() else None
        venue = parts[4].strip() if len(parts) > 4 else None
        tags = parts[5].strip() if len(parts) > 5 else None

        dst_pdf_path = None
        if pdf_path and os.path.exists(pdf_path) and pdf_path.lower().endswith('.pdf'):
            dst_pdf_path = copy_file_to_dir(pdf_path, db.papers_dir, args.force)

        paper_id = db.add_paper(
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            file_path=dst_pdf_path
        )

        if tags:
            for tag_name in tags.split(','):
                tag_name = tag_name.strip()
                if tag_name:
                    tag_id = db.add_tag(tag_name, 'topic')
                    db.tag_paper(paper_id, tag_id)

        imported.append({'id': paper_id, 'title': title})
        print(f"导入: {title}")

    print()
    print(f"完成: 成功导入 {len(imported)} 篇文献")


def register_import(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        'import',
        help='导入 PDF 文件和手写摘要',
        description='导入 PDF 文献文件和手写摘要文本到文献库'
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        'pdf',
        nargs='?',
        help='PDF 文件路径'
    )
    group.add_argument(
        '-d', '--dir',
        help='批量导入目录下的所有 PDF'
    )
    group.add_argument(
        '-b', '--batch',
        help='从文件或标准输入批量导入（格式：标题|PDF路径|作者|年份|会议|标签）'
    )

    parser.add_argument(
        '-s', '--summary',
        help='手写摘要文本文件路径'
    )
    parser.add_argument(
        '-t', '--title',
        help='指定论文标题'
    )
    parser.add_argument(
        '-a', '--authors',
        help='指定作者列表（逗号分隔）'
    )
    parser.add_argument(
        '-y', '--year',
        type=int,
        help='指定出版年份'
    )
    parser.add_argument(
        '-v', '--venue',
        help='指定会议/期刊名称'
    )
    parser.add_argument(
        '--tags',
        nargs='+',
        help='添加主题标签'
    )
    parser.add_argument(
        '--author',
        help='添加作者标签'
    )
    parser.add_argument(
        '--year-tag',
        type=int,
        help='添加年份标签'
    )
    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='强制覆盖已存在的文献'
    )
    parser.set_defaults(func=cmd_import, _parser=parser)
