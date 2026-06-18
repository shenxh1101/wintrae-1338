import os
import shutil
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any


class Database:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.getcwd()
        self.db_path = os.path.join(self.base_dir, '.paper_notes', 'library.db')
        self.papers_dir = os.path.join(self.base_dir, 'papers')
        self.notes_dir = os.path.join(self.base_dir, 'notes')
        self.conn = None

    def is_initialized(self) -> bool:
        return os.path.exists(self.db_path)

    def connect(self) -> None:
        if not self.is_initialized():
            raise RuntimeError("文献库未初始化，请先运行 init 命令")
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        cursor = self.conn.execute("PRAGMA table_info(papers)")
        columns = [row['name'] for row in cursor.fetchall()]
        if 'import_batch' not in columns:
            self.conn.execute("ALTER TABLE papers ADD COLUMN import_batch TEXT")
            self.conn.commit()
        try:
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_batch ON papers(import_batch)")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def initialize(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.papers_dir, exist_ok=True)
        os.makedirs(self.notes_dir, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")

        conn.execute('''
            CREATE TABLE papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                authors TEXT,
                year INTEGER,
                venue TEXT,
                file_path TEXT,
                summary_path TEXT,
                reading_status TEXT DEFAULT 'unread',
                reading_progress INTEGER DEFAULT 0,
                import_batch TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_read_at TEXT
            )
        ''')

        conn.execute('''
            CREATE TABLE tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                color TEXT DEFAULT '#3b82f6'
            )
        ''')

        conn.execute('''
            CREATE TABLE paper_tags (
                paper_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (paper_id, tag_id),
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        ''')

        conn.execute('''
            CREATE TABLE notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER,
                content TEXT NOT NULL,
                note_type TEXT DEFAULT 'general',
                page_number INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
            )
        ''')

        conn.execute('''
            CREATE TABLE quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER,
                content TEXT NOT NULL,
                page_number INTEGER,
                context TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
            )
        ''')

        conn.execute('''
            CREATE TABLE questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
            )
        ''')

        conn.execute('''
            CREATE INDEX idx_papers_status ON papers(reading_status)
        ''')
        conn.execute('''
            CREATE INDEX idx_papers_year ON papers(year)
        ''')
        conn.execute('''
            CREATE INDEX idx_papers_created ON papers(created_at)
        ''')
        conn.execute('''
            CREATE INDEX idx_tags_category ON tags(category)
        ''')

        conn.commit()
        conn.close()

    def reset(self, keep_papers: bool = False, keep_notes: bool = False) -> None:
        self.close()

        db_dir = os.path.dirname(self.db_path)
        if os.path.exists(db_dir):
            shutil.rmtree(db_dir)

        if not keep_papers and os.path.exists(self.papers_dir):
            shutil.rmtree(self.papers_dir)

        if not keep_notes and os.path.exists(self.notes_dir):
            shutil.rmtree(self.notes_dir)

        self.initialize()

    def add_paper(self, title: str, authors: Optional[str] = None,
                  year: Optional[int] = None, venue: Optional[str] = None,
                  file_path: Optional[str] = None, summary_path: Optional[str] = None,
                  import_batch: Optional[str] = None) -> int:
        now = datetime.now().isoformat()
        cursor = self.conn.execute('''
            INSERT INTO papers (title, authors, year, venue, file_path, summary_path, import_batch, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, authors, year, venue, file_path, summary_path, import_batch, now, now))
        self.conn.commit()
        return cursor.lastrowid

    def get_paper(self, paper_id: int) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute('SELECT * FROM papers WHERE id = ?', (paper_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_paper_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute('SELECT * FROM papers WHERE title = ?', (title,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_paper(self, paper_id: int, **kwargs) -> None:
        kwargs['updated_at'] = datetime.now().isoformat()
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [paper_id]
        self.conn.execute(f'UPDATE papers SET {fields} WHERE id = ?', values)
        self.conn.commit()

    def update_papers(self, paper_ids: List[int], **kwargs) -> None:
        if not paper_ids:
            return
        kwargs['updated_at'] = datetime.now().isoformat()
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        placeholders = ','.join(['?'] * len(paper_ids))
        values = list(kwargs.values()) + paper_ids
        self.conn.execute(
            f'UPDATE papers SET {fields} WHERE id IN ({placeholders})',
            values
        )
        self.conn.commit()

    def delete_paper(self, paper_id: int) -> None:
        self.conn.execute('DELETE FROM papers WHERE id = ?', (paper_id,))
        self.conn.commit()

    def add_tag(self, name: str, category: str, color: str = '#3b82f6') -> int:
        existing = self.conn.execute('SELECT id FROM tags WHERE name = ?', (name,)).fetchone()
        if existing:
            return existing['id']
        cursor = self.conn.execute('''
            INSERT INTO tags (name, category, color)
            VALUES (?, ?, ?)
        ''', (name, category, color))
        self.conn.commit()
        return cursor.lastrowid

    def get_tag(self, name: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute('SELECT * FROM tags WHERE name = ?', (name,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_tags(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        if category:
            cursor = self.conn.execute('SELECT * FROM tags WHERE category = ?', (category,))
        else:
            cursor = self.conn.execute('SELECT * FROM tags')
        return [dict(row) for row in cursor.fetchall()]

    def tag_paper(self, paper_id: int, tag_id: int) -> None:
        self.conn.execute('''
            INSERT OR IGNORE INTO paper_tags (paper_id, tag_id)
            VALUES (?, ?)
        ''', (paper_id, tag_id))
        self.conn.commit()

    def untag_paper(self, paper_id: int, tag_id: int) -> None:
        self.conn.execute('''
            DELETE FROM paper_tags WHERE paper_id = ? AND tag_id = ?
        ''', (paper_id, tag_id))
        self.conn.commit()

    def get_paper_tags(self, paper_id: int) -> List[Dict[str, Any]]:
        cursor = self.conn.execute('''
            SELECT t.* FROM tags t
            JOIN paper_tags pt ON t.id = pt.tag_id
            WHERE pt.paper_id = ?
        ''', (paper_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_papers_by_tag(self, tag_name: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute('''
            SELECT p.* FROM papers p
            JOIN paper_tags pt ON p.id = pt.paper_id
            JOIN tags t ON pt.tag_id = t.id
            WHERE t.name = ?
        ''', (tag_name,))
        return [dict(row) for row in cursor.fetchall()]

    def add_note(self, paper_id: int, content: str,
                 note_type: str = 'general', page_number: Optional[int] = None) -> int:
        now = datetime.now().isoformat()
        cursor = self.conn.execute('''
            INSERT INTO notes (paper_id, content, note_type, page_number, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (paper_id, content, note_type, page_number, now))
        self.conn.commit()
        return cursor.lastrowid

    def get_paper_notes(self, paper_id: int) -> List[Dict[str, Any]]:
        cursor = self.conn.execute('''
            SELECT * FROM notes WHERE paper_id = ? ORDER BY created_at
        ''', (paper_id,))
        return [dict(row) for row in cursor.fetchall()]

    def add_quote(self, paper_id: int, content: str,
                  page_number: Optional[int] = None, context: Optional[str] = None) -> int:
        now = datetime.now().isoformat()
        cursor = self.conn.execute('''
            INSERT INTO quotes (paper_id, content, page_number, context, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (paper_id, content, page_number, context, now))
        self.conn.commit()
        return cursor.lastrowid

    def get_paper_quotes(self, paper_id: int) -> List[Dict[str, Any]]:
        cursor = self.conn.execute('''
            SELECT * FROM quotes WHERE paper_id = ? ORDER BY created_at
        ''', (paper_id,))
        return [dict(row) for row in cursor.fetchall()]

    def add_question(self, paper_id: int, content: str, status: str = 'pending') -> int:
        now = datetime.now().isoformat()
        cursor = self.conn.execute('''
            INSERT INTO questions (paper_id, content, status, created_at)
            VALUES (?, ?, ?, ?)
        ''', (paper_id, content, status, now))
        self.conn.commit()
        return cursor.lastrowid

    def get_paper_questions(self, paper_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if status:
            cursor = self.conn.execute('''
                SELECT * FROM questions WHERE paper_id = ? AND status = ? ORDER BY created_at
            ''', (paper_id, status))
        else:
            cursor = self.conn.execute('''
                SELECT * FROM questions WHERE paper_id = ? ORDER BY created_at
            ''', (paper_id,))
        return [dict(row) for row in cursor.fetchall()]

    def search_papers(self, keyword: Optional[str] = None,
                      tags: Optional[List[str]] = None,
                      status: Optional[str] = None,
                      progress_min: Optional[int] = None,
                      progress_max: Optional[int] = None,
                      author: Optional[str] = None,
                      year: Optional[int] = None,
                      topic: Optional[str] = None,
                      batch: Optional[str] = None,
                      recent_minutes: Optional[int] = None) -> List[Dict[str, Any]]:
        query = '''
            SELECT DISTINCT p.* FROM papers p
            LEFT JOIN paper_tags pt ON p.id = pt.paper_id
            LEFT JOIN tags t ON pt.tag_id = t.id
            WHERE 1=1
        '''
        params = []

        if keyword:
            query += ' AND (p.title LIKE ? OR p.authors LIKE ? OR p.venue LIKE ?)'
            kw = f'%{keyword}%'
            params.extend([kw, kw, kw])

        if tags:
            placeholders = ','.join(['?'] * len(tags))
            query += f' AND t.name IN ({placeholders})'
            params.extend(tags)

        if status:
            query += ' AND p.reading_status = ?'
            params.append(status)

        if progress_min is not None:
            query += ' AND p.reading_progress >= ?'
            params.append(progress_min)

        if progress_max is not None:
            query += ' AND p.reading_progress <= ?'
            params.append(progress_max)

        if author:
            query += ' AND p.authors LIKE ?'
            params.append(f'%{author}%')

        if year:
            query += ' AND p.year = ?'
            params.append(year)

        if topic:
            query += ' AND t.name = ? AND t.category = ?'
            params.extend([topic, 'topic'])

        if batch:
            query += ' AND p.import_batch = ?'
            params.append(batch)

        if recent_minutes is not None:
            query += f" AND julianday('now') - julianday(p.created_at) <= {float(recent_minutes) / 1440.0}"

        query += ' ORDER BY p.updated_at DESC'

        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_all_papers(self) -> List[Dict[str, Any]]:
        cursor = self.conn.execute('SELECT * FROM papers ORDER BY created_at DESC')
        return [dict(row) for row in cursor.fetchall()]

    def get_monthly_stats(self) -> List[Dict[str, Any]]:
        cursor = self.conn.execute('''
            SELECT 
                strftime('%Y-%m', created_at) as month,
                COUNT(*) as count
            FROM papers
            GROUP BY month
            ORDER BY month DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]

    def get_topic_distribution(self) -> List[Dict[str, Any]]:
        cursor = self.conn.execute('''
            SELECT 
                t.name as topic,
                COUNT(DISTINCT p.id) as count
            FROM tags t
            LEFT JOIN paper_tags pt ON t.id = pt.tag_id
            LEFT JOIN papers p ON pt.paper_id = p.id
            WHERE t.category = ?
            GROUP BY t.name
            ORDER BY count DESC
        ''', ('topic',))
        return [dict(row) for row in cursor.fetchall()]

    def get_stale_papers(self, days: int = 30) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(f'''
            SELECT * FROM papers
            WHERE reading_status != 'read'
            AND (last_read_at IS NULL OR 
                 julianday('now') - julianday(COALESCE(last_read_at, created_at)) > {days})
            ORDER BY COALESCE(last_read_at, created_at) ASC
        ''')
        return [dict(row) for row in cursor.fetchall()]

    def get_status_distribution(self) -> List[Dict[str, Any]]:
        cursor = self.conn.execute('''
            SELECT reading_status as status, COUNT(*) as count
            FROM papers
            GROUP BY reading_status
        ''')
        return [dict(row) for row in cursor.fetchall()]

    def get_papers_by_batch(self, batch_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            'SELECT * FROM papers WHERE import_batch = ? ORDER BY id ASC',
            (batch_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_latest_batches(self, limit: int = 10) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(f'''
            SELECT import_batch as batch, 
                   COUNT(*) as count,
                   MAX(created_at) as latest_at
            FROM papers 
            WHERE import_batch IS NOT NULL 
            GROUP BY import_batch 
            ORDER BY latest_at DESC 
            LIMIT {limit}
        ''')
        return [dict(row) for row in cursor.fetchall()]

    def get_papers_by_created_after(self, iso_timestamp: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            'SELECT * FROM papers WHERE created_at >= ? ORDER BY created_at ASC',
            (iso_timestamp,)
        )
        return [dict(row) for row in cursor.fetchall()]
