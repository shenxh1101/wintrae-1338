import os
import argparse
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any
from ..database import Database
from ..utils import (
    format_status,
    format_date,
    print_progress_bar
)


def cmd_stats(args: argparse.Namespace) -> None:
    db = Database()
    with db:
        if args.monthly:
            _show_monthly_stats(db, args)
        elif args.topics:
            _show_topic_distribution(db, args)
        elif args.stale:
            _show_stale_papers(db, args)
        elif args.status:
            _show_status_distribution(db, args)
        else:
            _show_overview(db, args)


def _show_overview(db: Database, args: argparse.Namespace) -> None:
    all_papers = db.get_all_papers()
    total = len(all_papers)

    if total == 0:
        print("文献库为空，还没有导入任何文献")
        return

    monthly_stats = db.get_monthly_stats()
    topic_dist = db.get_topic_distribution()
    status_dist = db.get_status_distribution()
    stale_papers = db.get_stale_papers(args.stale_days)

    print("=" * 60)
    print("[*] 论文阅读笔记统计总览")
    print("=" * 60)
    print()

    print(f"[=] 总文献数: {total} 篇")
    print()

    print("[+] 阅读状态分布:")
    status_total = sum(s['count'] for s in status_dist)
    for s in status_dist:
        count = s['count']
        percent = (count / status_total * 100) if status_total > 0 else 0
        bar = print_progress_bar(count, status_total, 30)
        print(f"  {format_status(s['status']):<6} {bar} {count} 篇 ({percent:5.1f}%)")
    print()

    read_count = sum(1 for p in all_papers if p['reading_status'] == 'read')
    avg_progress = sum(p['reading_progress'] for p in all_papers) / total if total > 0 else 0
    print(f"[x] 已完成: {read_count} 篇 ({read_count/total*100:.1f}%)")
    print(f"[~] 平均进度: {avg_progress:.1f}%")
    print()

    if topic_dist:
        print("[>] 主题分布 (TOP 10):")
        max_topic_count = max(t['count'] for t in topic_dist) if topic_dist else 1
        for i, t in enumerate(topic_dist[:10], 1):
            bar = print_progress_bar(t['count'], max_topic_count, 25)
            print(f"  {i:2d}. {t['topic']:<20} {bar} {t['count']} 篇")
        if len(topic_dist) > 10:
            print(f"      ... 还有 {len(topic_dist) - 10} 个主题")
        print()

    if monthly_stats:
        print("[#] 最近 12 个月文献导入:")
        recent = monthly_stats[:12]
        max_month_count = max(m['count'] for m in recent) if recent else 1
        for m in reversed(recent):
            bar = print_progress_bar(m['count'], max_month_count, 25)
            print(f"  {m['month']}  {bar} {m['count']} 篇")
        print()

    if stale_papers:
        print(f"[!] 长期未处理文献 (> {args.stale_days} 天): {len(stale_papers)} 篇")
        print(f"   使用 'paper-notes stats --stale' 查看详细列表")
        print()

    total_notes = 0
    total_quotes = 0
    total_questions = 0
    for paper in all_papers:
        total_notes += len(db.get_paper_notes(paper['id']))
        total_quotes += len(db.get_paper_quotes(paper['id']))
        total_questions += len(db.get_paper_questions(paper['id']))

    print("[N] 笔记统计:")
    print(f"  阅读笔记: {total_notes} 条")
    print(f"  引用摘录: {total_quotes} 条")
    print(f"  待办问题: {total_questions} 个")
    print()

    print("[?] 操作提示:")
    print("  paper-notes stats --monthly   - 查看月度阅读统计")
    print("  paper-notes stats --topics    - 查看完整主题分布")
    print("  paper-notes stats --stale     - 查看长期未处理文献")
    print("  paper-notes stats --status    - 查看状态分布")


def _show_monthly_stats(db: Database, args: argparse.Namespace) -> None:
    monthly_stats = db.get_monthly_stats()

    if not monthly_stats:
        print("没有数据")
        return

    print("=" * 60)
    print("[#] 每月阅读数量统计")
    print("=" * 60)
    print()

    total_all = sum(m['count'] for m in monthly_stats)
    print(f"总计: {total_all} 篇，共 {len(monthly_stats)} 个月")
    print()

    max_count = max(m['count'] for m in monthly_stats)

    for m in monthly_stats:
        bar = print_progress_bar(m['count'], max_count, 40)
        print(f"  {m['month']}  {bar} {m['count']} 篇")

    print()
    if len(monthly_stats) >= 2:
        latest = monthly_stats[0]['count']
        previous = monthly_stats[1]['count']
        if previous > 0:
            change = (latest - previous) / previous * 100
            arrow = "UP" if change > 0 else "DOWN" if change < 0 else "--"
            print(f"环比变化: {arrow} {abs(change):.1f}%")


def _show_topic_distribution(db: Database, args: argparse.Namespace) -> None:
    topic_dist = db.get_topic_distribution()

    if not topic_dist:
        print("没有主题标签数据")
        return

    print("=" * 60)
    print("[>] 主题分布统计")
    print("=" * 60)
    print()

    total = sum(t['count'] for t in topic_dist)
    print(f"总计: {total} 篇文献，共 {len(topic_dist)} 个主题")
    print()

    max_count = max(t['count'] for t in topic_dist)

    for i, t in enumerate(topic_dist, 1):
        percent = t['count'] / total * 100 if total > 0 else 0
        bar = print_progress_bar(t['count'], max_count, 35)
        print(f"  {i:2d}. {t['topic']:<20} {bar} {t['count']:3d} 篇 ({percent:5.1f}%)")

    print()
    if args.drilldown:
        for t in topic_dist[:5]:
            papers = db.get_papers_by_tag(t['topic'])
            print(f"\n[{t['topic']}] ({len(papers)} 篇):")
            for paper in papers[:5]:
                status = format_status(paper['reading_status'])
                print(f"  - {paper['title']} ({status})")
            if len(papers) > 5:
                print(f"  ... 还有 {len(papers) - 5} 篇")


def _show_stale_papers(db: Database, args: argparse.Namespace) -> None:
    stale_papers = db.get_stale_papers(args.stale_days)

    if not stale_papers:
        print(f"[OK] 没有超过 {args.stale_days} 天未处理的文献，继续保持！")
        return

    print("=" * 60)
    print(f"[!] 长期未处理文献 (> {args.stale_days} 天)")
    print("=" * 60)
    print()

    print(f"共 {len(stale_papers)} 篇文献需要处理:")
    print()

    for i, paper in enumerate(stale_papers, 1):
        last_activity = paper['last_read_at'] or paper['created_at']
        try:
            last_dt = datetime.fromisoformat(last_activity)
            days_ago = (datetime.now() - last_dt).days
        except (ValueError, TypeError):
            days_ago = args.stale_days + 1

        status = format_status(paper['reading_status'])
        print(f"{i:2d}. [{paper['id']}] {paper['title']}")
        print(f"    状态: {status} | 进度: {paper['reading_progress']}% | 已搁置 {days_ago} 天")
        print(f"    最后活动: {format_date(last_activity)}")
        if paper['authors']:
            print(f"    作者: {paper['authors']}")
        print()

    print("[?] 建议操作:")
    print(f"  paper-notes tag --ids 1,2,3 --to-review  # 标记为待精读")
    print(f"  paper-notes tag --ids 1,2,3 --read        # 标记为已读")


def _show_status_distribution(db: Database, args: argparse.Namespace) -> None:
    status_dist = db.get_status_distribution()
    all_papers = db.get_all_papers()

    if not status_dist:
        print("没有数据")
        return

    print("=" * 60)
    print("[+] 阅读状态分布")
    print("=" * 60)
    print()

    total = sum(s['count'] for s in status_dist)
    print(f"总计: {total} 篇文献")
    print()

    status_order = ['unread', 'reading', 'to_review', 'read']
    status_labels = {
        'unread': '[ ] 未读',
        'reading': '[~] 在读',
        'to_review': '[!] 待精读',
        'read': '[x] 已读'
    }

    for status in status_order:
        s = next((x for x in status_dist if x['status'] == status), None)
        count = s['count'] if s else 0
        percent = count / total * 100 if total > 0 else 0
        bar = print_progress_bar(count, total, 35)
        print(f"  {status_labels[status]:<10} {bar} {count:3d} 篇 ({percent:5.1f}%)")

    print()

    avg_progress = sum(p['reading_progress'] for p in all_papers) / total if total > 0 else 0
    print(f"[~] 平均阅读进度: {avg_progress:.1f}%")
    print()

    print("[~] 在读文献详情:")
    reading_papers = [p for p in all_papers if p['reading_status'] == 'reading']
    if reading_papers:
        for paper in reading_papers:
            bar = print_progress_bar(paper['reading_progress'], 100, 25)
            print(f"  [{paper['id']}] {paper['title']}")
            print(f"    {bar}")
    else:
        print("  没有正在阅读的文献")


def register_stats(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        'stats',
        help='统计分析',
        description='输出每月阅读数量、主题分布和长期未处理文献'
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-m', '--monthly',
        action='store_true',
        help='查看月度阅读统计'
    )
    group.add_argument(
        '-t', '--topics',
        action='store_true',
        help='查看主题分布'
    )
    group.add_argument(
        '-s', '--stale',
        action='store_true',
        help='查看长期未处理文献'
    )
    group.add_argument(
        '--status',
        action='store_true',
        help='查看阅读状态分布'
    )

    parser.add_argument(
        '--stale-days',
        type=int,
        default=30,
        help='定义长期未处理的天数阈值 (默认: 30天)'
    )
    parser.add_argument(
        '--drilldown',
        action='store_true',
        help='显示详细信息（如主题下的文献列表）'
    )

    parser.set_defaults(func=cmd_stats)
