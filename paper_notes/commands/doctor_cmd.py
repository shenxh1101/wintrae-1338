import os
import argparse
from typing import List, Dict, Any
from collections import Counter
from ..database import Database


def cmd_doctor(args: argparse.Namespace) -> None:
    db = Database()
    with db:
        print("=" * 60)
        print("文献库健康检查 (paper-notes doctor)")
        print("=" * 60)
        print()
        print(f"文献库目录: {db.base_dir}")
        print()

        all_papers = db.get_all_papers()
        if not all_papers:
            print("[i] 文献库为空，无需检查")
            return

        missing_pdf = []
        missing_summary = []
        empty_titles = []
        duplicate_titles = []
        orphan_pdf_files = []
        orphan_note_files = []

        title_counts = Counter((p.get('title') or '').strip() for p in all_papers)
        duplicate_titles = [t for t, c in title_counts.items() if t and c > 1]

        for p in all_papers:
            pid = p['id']
            title = (p.get('title') or '').strip()
            if not title:
                empty_titles.append(pid)

            fp = p.get('file_path')
            if fp:
                if not os.path.exists(fp):
                    missing_pdf.append({
                        'id': pid,
                        'title': title or '(空标题)',
                        'path': fp
                    })

            sp = p.get('summary_path')
            if sp:
                if not os.path.exists(sp):
                    missing_summary.append({
                        'id': pid,
                        'title': title or '(空标题)',
                        'path': sp
                    })

        actual_pdfs = set()
        if os.path.isdir(db.papers_dir):
            for root, dirs, files in os.walk(db.papers_dir):
                for f in files:
                    if f.lower().endswith('.pdf'):
                        full = os.path.join(root, f)
                        actual_pdfs.add(os.path.abspath(full))

        recorded_pdfs = set()
        for p in all_papers:
            fp = p.get('file_path')
            if fp:
                recorded_pdfs.add(os.path.abspath(fp))

        orphan_pdf_files = sorted(actual_pdfs - recorded_pdfs)

        actual_notes = set()
        if os.path.isdir(db.notes_dir):
            for root, dirs, files in os.walk(db.notes_dir):
                for f in files:
                    full = os.path.join(root, f)
                    actual_notes.add(os.path.abspath(full))

        recorded_notes = set()
        for p in all_papers:
            sp = p.get('summary_path')
            if sp:
                recorded_notes.add(os.path.abspath(sp))

        orphan_note_files = sorted(actual_notes - recorded_notes)

        total_issues = (
            len(missing_pdf)
            + len(missing_summary)
            + len(empty_titles)
            + len(duplicate_titles)
            + len(orphan_pdf_files)
            + len(orphan_note_files)
        )

        print(f"总文献数: {len(all_papers)} 篇")
        print(f"发现问题: {total_issues} 处")
        print()

        def _section(icon, title, items, fmt=None):
            print(f"{icon} {title} ({len(items)})")
            print("-" * 60)
            if not items:
                print("  [OK] 无问题")
            else:
                for it in items:
                    if isinstance(it, dict):
                        if fmt:
                            print(f"  - {fmt(it)}")
                        else:
                            print(f"  [{it.get('id')}] {it.get('title')}")
                            if it.get('path'):
                                print(f"       {it.get('path')}")
                    else:
                        print(f"  - {it}")
            print()

        _section("[!]", "PDF 文件缺失（数据库有记录但文件不存在）", missing_pdf)
        _section("[!]", "摘要文件缺失（数据库有记录但文件不存在）", missing_summary)
        _section("[!]", "空标题（标题为空）", empty_titles, fmt=lambda x: f"ID={x}")
        _section("[!]", "重复标题", duplicate_titles, fmt=lambda t: f"{t} (出现 {title_counts[t]} 次)")
        _section("[~]", "孤立 PDF（文件存在但无数据库记录）", orphan_pdf_files)
        _section("[~]", "孤立笔记文件（存在但无数据库记录）", orphan_note_files)

        if total_issues == 0:
            print("[OK] 检查通过，没有发现问题！")
            print()
            return

        if args.fix:
            _auto_fix(db, all_papers, missing_pdf, missing_summary, empty_titles, duplicate_titles, orphan_pdf_files, orphan_note_files, title_counts)
        else:
            print("[?] 操作建议:")
            print("  paper-notes doctor --fix   # 自动修复可修复的问题")
            print("  paper-notes doctor         # 仅检查不修复")
            print()


def _auto_fix(db, all_papers, missing_pdf, missing_summary, empty_titles, duplicate_titles, orphan_pdf_files, orphan_note_files, title_counts):
    print("=" * 60)
    print("自动修复")
    print("=" * 60)
    print()

    fixed_count = 0

    if missing_pdf:
        for item in missing_pdf:
            db.update_paper(item['id'], file_path=None)
            fixed_count += 1
        print(f"[FIX] 已将 {len(missing_pdf)} 条文献的缺失 PDF 路径置空（保留文献记录）")

    if missing_summary:
        print()
        for item in missing_summary:
            db.update_paper(item['id'], summary_path=None)
            fixed_count += 1
        print(f"[FIX] 已将 {len(missing_summary)} 条文献的缺失摘要路径置空")

    if empty_titles:
        print()
        for pid in empty_titles:
            new_title = f"未命名论文_{pid}"
            db.update_paper(pid, title=new_title)
            fixed_count += 1
        print(f"[FIX] 已为 {len(empty_titles)} 条空标题文献赋予临时标题")

    if duplicate_titles:
        print()
        dedup_fixed = 0
        for t in duplicate_titles:
            papers_with_title = [p for p in all_papers if (p.get('title') or '').strip() == t]
            for i, p in enumerate(papers_with_title[1:], 1):
                new_title = f"{t} ({i})"
                db.update_paper(p['id'], title=new_title)
                dedup_fixed += 1
        fixed_count += dedup_fixed
        print(f"[FIX] 已为 {dedup_fixed} 个重复标题加序号区分")

    if orphan_pdf_files:
        print()
        print(f"[i] 孤立 PDF 文件（请手动确认后用 import 命令导入）:")
        for f in orphan_pdf_files:
            print(f"    {f}")

    if orphan_note_files:
        print()
        print(f"[i] 孤立笔记文件（请手动确认后保留或删除）:")
        for f in orphan_note_files:
            print(f"    {f}")

    print()
    print(f"[OK] 自动修复完成，共处理 {fixed_count} 处")
    print()


def register_doctor(subparsers):
    parser = subparsers.add_parser(
        'doctor',
        help='文献库健康检查',
        description='扫描文献库：检查 PDF、摘要文件与数据库一致性，检测缺失文件、重复标题、空标题、孤立文件'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='自动修复可修复的问题（清空缺失文件路径、空标题重命名、重复标题加序号）'
    )
    parser.set_defaults(func=cmd_doctor, _parser=parser)
