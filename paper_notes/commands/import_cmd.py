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
    sources = [s for s in [args.pdf, args.dir, args.batch] if s]
    if len(sources) > 1:
        print("错误: PDF、目录(-d)、清单(-b)三种方式不能同时使用")
        print("提示: 只能选择一种导入方式")
        return

    if not args.pdf and not args.dir and not args.batch:
        parser = args._parser
        parser.print_help()
        return

    db = Database()
    with db:
        if args.pdf:
            _import_single(db, args)
        elif args.dir:
            _import_directory(db, args)
        elif args.batch:
            _import_batch(db, args)


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
    batch_arg = args.batch
    use_stdin = False
    lines = []

    if batch_arg == '-' or batch_arg == 'stdin':
        use_stdin = True
    else:
        batch_file = os.path.abspath(batch_arg)
        if not os.path.exists(batch_file):
            print(f"错误: 批量导入清单不存在: {batch_file}")
            print()
            print("清单格式示例（每行一篇，字段用 | 分隔）:")
            print("  标题|PDF路径|作者|年份|会议|主题标签(逗号分隔)|摘要文件路径")
            print()
            print("提示:")
            print("  - PDF路径、摘要文件路径不存在时会跳过该文件（但文献记录仍会创建）")
            print("  - 字段可留空（如：标题||作者|年份||标签|摘要.txt）")
            print("  - 使用 -b stdin 从管道读取: cat list.txt | paper-notes import -b stdin")
            return

        if not os.path.isfile(batch_file):
            print(f"错误: {batch_file} 不是一个文件")
            return

        try:
            with open(batch_file, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except UnicodeDecodeError:
            print(f"错误: 无法读取文件编码，请使用 UTF-8 编码保存: {batch_file}")
            return
        except Exception as e:
            print(f"错误: 读取文件失败: {e}")
            return

    if use_stdin:
        import sys
        if sys.stdin.isatty():
            print("错误: 未从管道获取输入且清单文件不存在")
            print("  用法1: paper-notes import -b import_list.txt")
            print("  用法2: cat import_list.txt | paper-notes import -b stdin")
            return
        lines = [line.strip() for line in sys.stdin if line.strip() and not line.startswith('#')]

    if not lines:
        print("错误: 导入清单为空，没有任何数据行")
        return

    print("=" * 60)
    print(f"批量导入 {len(lines)} 篇文献")
    if not use_stdin:
        print(f"来源: {batch_file}")
    print("=" * 60)
    print()
    print("格式说明: 标题 | PDF路径 | 作者 | 年份 | 会议 | 主题标签(,) | 摘要路径")
    print("-" * 60)
    print()

    success_list = []
    skip_list = []
    fail_list = []

    for idx, line in enumerate(lines, 1):
        parts = [p.strip() for p in line.split('|')]

        while len(parts) < 7:
            parts.append('')

        title = parts[0]
        pdf_path = parts[1]
        authors = parts[2] if parts[2] else None
        year = int(parts[3]) if parts[3].isdigit() else None
        venue = parts[4] if parts[4] else None
        tags_str = parts[5]
        summary_path = parts[6] if parts[6] else None

        if not title:
            msg = f"第 {idx} 行缺少标题字段"
            fail_list.append({'line': idx, 'raw': line, 'reason': msg})
            print(f"[FAIL] 第{idx}行: {msg}")
            print(f"        原始内容: {line[:60]}...")
            continue

        existing = db.get_paper_by_title(title)
        if existing and not args.force:
            msg = f"标题已存在 (ID={existing['id']})"
            skip_list.append({'line': idx, 'title': title, 'reason': msg})
            print(f"[SKIP] 第{idx}行: {title}")
            print(f"        原因: {msg}，使用 -f 可更新")
            continue

        pdf_warnings = []
        dst_pdf_path = None
        if pdf_path:
            abs_pdf = os.path.abspath(pdf_path)
            if not os.path.exists(abs_pdf):
                pdf_warnings.append(f"PDF不存在: {pdf_path}")
            elif not abs_pdf.lower().endswith('.pdf'):
                pdf_warnings.append(f"不是PDF文件: {pdf_path}")
            else:
                try:
                    dst_pdf_path = copy_file_to_dir(abs_pdf, db.papers_dir, args.force)
                except Exception as e:
                    pdf_warnings.append(f"复制PDF失败: {e}")

        dst_summary_path = None
        summary_data = {}
        if summary_path:
            abs_summary = os.path.abspath(summary_path)
            if os.path.exists(abs_summary):
                try:
                    summary_data = parse_summary_file(abs_summary)
                    safe_name = safe_filename(title)
                    dst_summary_path = os.path.join(db.notes_dir, f"{safe_name}_summary.txt")
                    os.makedirs(os.path.dirname(dst_summary_path), exist_ok=True)
                    with open(abs_summary, 'r', encoding='utf-8') as f:
                        content = f.read()
                    with open(dst_summary_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                except Exception as e:
                    pdf_warnings.append(f"处理摘要失败: {e}")
            else:
                pdf_warnings.append(f"摘要文件不存在: {summary_path}")

            if summary_data.get('title'):
                title = summary_data['title']
            if summary_data.get('authors') and not authors:
                authors = summary_data['authors']
            if summary_data.get('year') and not year:
                year = summary_data['year']
            if summary_data.get('venue') and not venue:
                venue = summary_data['venue']

        try:
            if existing and args.force:
                paper_id = existing['id']
                db.update_paper(
                    paper_id,
                    title=title,
                    authors=authors,
                    year=year,
                    venue=venue,
                    file_path=dst_pdf_path,
                    summary_path=dst_summary_path
                )
                status_label = "[UPD]"
            else:
                paper_id = db.add_paper(
                    title=title,
                    authors=authors,
                    year=year,
                    venue=venue,
                    file_path=dst_pdf_path,
                    summary_path=dst_summary_path
                )
                status_label = "[ OK ]"
        except Exception as e:
            msg = f"写入数据库失败: {e}"
            fail_list.append({'line': idx, 'title': title, 'reason': msg})
            print(f"[FAIL] 第{idx}行: {title}")
            print(f"        原因: {msg}")
            continue

        tag_count = 0
        if tags_str:
            for tag_name in tags_str.split(','):
                tag_name = tag_name.strip()
                if tag_name:
                    try:
                        tag_id = db.add_tag(tag_name, 'topic')
                        db.tag_paper(paper_id, tag_id)
                        tag_count += 1
                    except Exception:
                        pass

        if summary_data.get('summary'):
            try:
                db.add_note(paper_id, summary_data['summary'], 'summary')
            except Exception:
                pass
        for quote in summary_data.get('quotes', []):
            try:
                db.add_quote(paper_id, quote)
            except Exception:
                pass
        for question in summary_data.get('questions', []):
            try:
                db.add_question(paper_id, question)
            except Exception:
                pass
        for note in summary_data.get('notes', []):
            try:
                db.add_note(paper_id, note, 'general')
            except Exception:
                pass

        info = f"{status_label} 第{idx}行: [{paper_id}] {title}"
        if authors:
            info += f" - {authors}"
        print(info)
        if tag_count:
            print(f"        标签: {tags_str} ({tag_count}个)")
        if pdf_warnings:
            for w in pdf_warnings:
                print(f"        警告: {w}")

        success_list.append({
            'line': idx,
            'id': paper_id,
            'title': title,
            'updated': (existing is not None and args.force)
        })

    print()
    print("=" * 60)
    print("批量导入汇总报告")
    print("=" * 60)
    total = len(lines)
    ok = len(success_list)
    skip = len(skip_list)
    fail = len(fail_list)
    print(f"总行数: {total}")
    print(f"成功:   {ok}   ({ok/total*100:.1f}%)")
    print(f"跳过:   {skip}   ({skip/total*100:.1f}%)")
    print(f"失败:   {fail}   ({fail/total*100:.1f}%)")

    if success_list:
        updated_count = sum(1 for x in success_list if x['updated'])
        new_count = ok - updated_count
        print()
        print(f"  新增: {new_count} 篇")
        if updated_count:
            print(f"  更新: {updated_count} 篇")

    if skip_list:
        print()
        print("跳过详情:")
        for s in skip_list:
            print(f"  第{s['line']}行 - {s['title']}")
            print(f"    原因: {s['reason']}")

    if fail_list:
        print()
        print("失败详情:")
        for f in fail_list:
            title = f.get('title', f"原始行: {f.get('raw','')[:50]}")
            print(f"  第{f['line']}行 - {title}")
            print(f"    原因: {f['reason']}")
            fail_count = fail

    print()
    if fail > 0:
        print("提示: 修正失败条目后，使用 -f 重新运行可更新已存在的记录")
    elif skip > 0:
        print("提示: 使用 -f 参数可强制更新被跳过的已存在记录")


def register_import(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        'import',
        help='导入 PDF 文件和手写摘要',
        description='导入 PDF 文献文件和手写摘要文本到文献库',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:

  # 单篇导入（PDF + 摘要）
  paper-notes import paper.pdf -s summary.txt --tags "深度学习"

  # 目录批量导入
  paper-notes import -d ./pdfs/

  # 清单批量导入
  paper-notes import -b import_list.txt

  # 从管道读取清单
  cat list.txt | paper-notes import -b -
        '''
    )

    parser.add_argument(
        'pdf',
        nargs='?',
        help='PDF 文件路径（单篇导入时使用）'
    )
    parser.add_argument(
        '-d', '--dir',
        help='批量导入目录下的所有 PDF'
    )
    parser.add_argument(
        '-b', '--batch',
        help='批量导入清单文件（格式：标题|PDF路径|作者|年份|会议|标签(,分隔)|摘要文件路径；#开头的行忽略；使用 - 或 stdin 从管道读取）'
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
