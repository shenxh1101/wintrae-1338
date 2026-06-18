import os
import re
import shutil
import hashlib
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any


def parse_pdf_filename(filename: str) -> Dict[str, Any]:
    name = os.path.splitext(filename)[0]
    result = {
        'title': name,
        'authors': None,
        'year': None,
        'venue': None
    }

    pattern1 = r'^(.*?) - (.*?) \((\d{4})\) - (.*?)$'
    match1 = re.match(pattern1, name)
    if match1:
        result['authors'] = match1.group(1).strip()
        result['title'] = match1.group(2).strip()
        result['year'] = int(match1.group(3))
        result['venue'] = match1.group(4).strip()
        return result

    pattern2 = r'^(.*?) \((\d{4})\) - (.*?)$'
    match2 = re.match(pattern2, name)
    if match2:
        result['authors'] = match2.group(1).strip()
        result['year'] = int(match2.group(2))
        result['title'] = match2.group(3).strip()
        return result

    pattern3 = r'^(.*?) - (\d{4}) - (.*?)$'
    match3 = re.match(pattern3, name)
    if match3:
        result['authors'] = match3.group(1).strip()
        result['year'] = int(match3.group(2))
        result['title'] = match3.group(3).strip()
        return result

    pattern4 = r'^(.*?) (\d{4}) (.*?)$'
    match4 = re.match(pattern4, name)
    if match4:
        result['authors'] = match4.group(1).strip()
        result['year'] = int(match4.group(2))
        result['title'] = match4.group(3).strip()
        return result

    year_match = re.search(r'(19|20)\d{2}', name)
    if year_match:
        result['year'] = int(year_match.group())

    return result


def parse_summary_file(summary_path: str) -> Dict[str, Any]:
    result = {
        'title': None,
        'authors': None,
        'year': None,
        'venue': None,
        'summary': None,
        'quotes': [],
        'questions': [],
        'notes': []
    }

    if not os.path.exists(summary_path):
        return result

    with open(summary_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    current_section = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('# '):
            result['title'] = line[2:].strip()
            current_section = 'title'
        elif line.lower().startswith('作者:') or line.lower().startswith('authors:'):
            result['authors'] = line.split(':', 1)[1].strip()
        elif line.lower().startswith('年份:') or line.lower().startswith('year:'):
            year_str = line.split(':', 1)[1].strip()
            if year_str.isdigit():
                result['year'] = int(year_str)
        elif line.lower().startswith('会议/期刊:') or line.lower().startswith('venue:'):
            result['venue'] = line.split(':', 1)[1].strip()
        elif line.startswith('## '):
            section = line[3:].strip().lower()
            if '摘要' in section or 'summary' in section:
                current_section = 'summary'
            elif '摘录' in section or 'quote' in section:
                current_section = 'quotes'
            elif '问题' in section or 'question' in section:
                current_section = 'questions'
            elif '笔记' in section or 'note' in section:
                current_section = 'notes'
            else:
                current_section = None
        elif line.startswith('- ') or line.startswith('* '):
            item = line[2:].strip()
            if current_section == 'quotes':
                result['quotes'].append(item)
            elif current_section == 'questions':
                result['questions'].append(item)
            elif current_section == 'notes':
                result['notes'].append(item)
        elif current_section == 'summary':
            if result['summary'] is None:
                result['summary'] = line
            else:
                result['summary'] += '\n' + line

    return result


def extract_pdf_info(pdf_path: str) -> Dict[str, Any]:
    result = {
        'title': None,
        'authors': None,
        'page_count': 0
    }

    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        info = reader.metadata

        if info:
            if info.title:
                result['title'] = str(info.title).strip()
            if info.author:
                result['authors'] = str(info.author).strip()

        result['page_count'] = len(reader.pages)
    except ImportError:
        pass
    except Exception:
        pass

    if result['title'] is None or result['title'] == '':
        result['title'] = parse_pdf_filename(os.path.basename(pdf_path))['title']

    return result


def copy_file_to_dir(src_path: str, dst_dir: str, overwrite: bool = False) -> str:
    os.makedirs(dst_dir, exist_ok=True)
    filename = os.path.basename(src_path)
    dst_path = os.path.join(dst_dir, filename)

    if os.path.exists(dst_path) and not overwrite:
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(dst_path):
            dst_path = os.path.join(dst_dir, f"{base}_{counter}{ext}")
            counter += 1

    shutil.copy2(src_path, dst_path)
    return dst_path


def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = name.strip().strip('.')
    return name[:200] or 'unnamed'


def file_hash(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def format_date(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime('%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        return date_str


def format_status(status: str) -> str:
    status_map = {
        'unread': '未读',
        'reading': '在读',
        'read': '已读',
        'to_review': '待精读'
    }
    return status_map.get(status, status)


def print_paper_list(papers: List[Dict[str, Any]], show_tags: bool = False,
                     db: Optional[Any] = None) -> None:
    if not papers:
        print("未找到符合条件的文献")
        return

    for i, paper in enumerate(papers, 1):
        status = format_status(paper['reading_status'])
        progress = paper['reading_progress']
        info = f"[{paper['id']}] {paper['title']}"
        if paper['year']:
            info += f" ({paper['year']})"
        if paper['authors']:
            info += f" - {paper['authors']}"
        info += f" | {status} | 进度: {progress}%"

        if show_tags and db:
            tags = db.get_paper_tags(paper['id'])
            if tags:
                tag_names = [t['name'] for t in tags]
                info += f" | 标签: {', '.join(tag_names)}"

        print(info)


def print_progress_bar(value: int, max_value: int = 100, width: int = 30) -> str:
    if max_value <= 0:
        max_value = 100
    ratio = min(max(value / max_value, 0), 1)
    filled = int(ratio * width)
    bar = '█' * filled + '░' * (width - filled)
    percent = int(ratio * 100)
    return f"{bar} {percent}%"


def parse_id_list(id_str: str) -> List[int]:
    ids = []
    for part in id_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = part.split('-', 1)
            try:
                ids.extend(range(int(start.strip()), int(end.strip()) + 1))
            except ValueError:
                continue
        else:
            try:
                ids.append(int(part))
            except ValueError:
                continue
    return ids


def read_stdin_lines() -> List[str]:
    import sys
    return [line.strip() for line in sys.stdin if line.strip()]
