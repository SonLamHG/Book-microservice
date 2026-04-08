"""
Management command to load knowledge base data.
Seeds KB with:
1. Static markdown files from kb_data/
2. Dynamic book catalog data from Book Service + Catalog Service
"""
import os
import logging
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Load knowledge base documents from markdown files and book catalog'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing KB documents before loading',
        )
        parser.add_argument(
            '--skip-catalog',
            action='store_true',
            help='Skip loading book catalog from Book Service',
        )

    def handle(self, *args, **options):
        from app.models import KnowledgeDocument
        from app.knowledge_base import embed_and_store_document, bulk_embed_and_store, chunk_text

        if options['clear']:
            count = KnowledgeDocument.objects.count()
            KnowledgeDocument.objects.all().delete()
            self.stdout.write(f"Cleared {count} existing KB documents.")

        # ── 1. Load markdown files ──
        kb_dir = Path(settings.BASE_DIR) / 'kb_data'
        source_map = {
            'bookstore_policies.md': 'policy',
            'book_genres_guide.md': 'genre_guide',
            'faq.md': 'faq',
        }

        md_docs = []
        for filename, source in source_map.items():
            filepath = kb_dir / filename
            if not filepath.exists():
                self.stdout.write(self.style.WARNING(f"File not found: {filepath}"))
                continue

            content = filepath.read_text(encoding='utf-8')
            # Split by markdown headers for natural chunking
            sections = self._split_by_headers(content)

            for title, section_content in sections:
                chunks = chunk_text(section_content, chunk_size=500, overlap=50)
                for i, chunk in enumerate(chunks):
                    doc_title = title if len(chunks) == 1 else f"{title} (part {i+1})"
                    md_docs.append({
                        'title': doc_title,
                        'content': chunk,
                        'source': source,
                    })

            self.stdout.write(f"Parsed {filename}: {len(sections)} sections")

        if md_docs:
            self.stdout.write(f"Embedding {len(md_docs)} markdown documents...")
            try:
                bulk_embed_and_store(md_docs)
                self.stdout.write(self.style.SUCCESS(f"Stored {len(md_docs)} markdown KB documents"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to embed markdown docs: {e}"))

        # ── 2. Load book catalog ──
        if not options['skip_catalog']:
            self._load_book_catalog()

        total = KnowledgeDocument.objects.count()
        self.stdout.write(self.style.SUCCESS(f"\nKB loading complete. Total documents: {total}"))

    def _split_by_headers(self, content):
        """Split markdown content by ## headers."""
        sections = []
        current_title = 'General'
        current_content = []

        for line in content.split('\n'):
            if line.startswith('## '):
                if current_content:
                    sections.append((current_title, '\n'.join(current_content).strip()))
                current_title = line.lstrip('#').strip()
                current_content = []
            elif line.startswith('# '):
                if current_content:
                    sections.append((current_title, '\n'.join(current_content).strip()))
                current_title = line.lstrip('#').strip()
                current_content = []
            else:
                current_content.append(line)

        if current_content:
            sections.append((current_title, '\n'.join(current_content).strip()))

        return [(t, c) for t, c in sections if c.strip()]

    def _load_book_catalog(self):
        """Fetch books and categories from services and add to KB."""
        import requests
        from app.knowledge_base import bulk_embed_and_store

        book_url = getattr(settings, 'BOOK_SERVICE_URL', 'http://book-service:8000')
        catalog_url = getattr(settings, 'CATALOG_SERVICE_URL', 'http://catalog-service:8000')

        # Fetch categories
        cat_map = {}
        try:
            r = requests.get(f"{catalog_url}/categories/", timeout=5)
            if r.status_code == 200:
                for cat in r.json():
                    cat_map[cat['id']] = cat['name']
                self.stdout.write(f"Fetched {len(cat_map)} categories")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not fetch categories: {e}"))

        # Fetch books
        try:
            r = requests.get(f"{book_url}/books/", timeout=5)
            if r.status_code != 200:
                self.stdout.write(self.style.WARNING("Could not fetch books"))
                return
            books = r.json()
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not fetch books: {e}"))
            return

        book_docs = []
        for book in books:
            cat_name = cat_map.get(book.get('category_id'), 'Unknown')
            content = (
                f"Ten sach: {book.get('title', '')}\n"
                f"Tac gia: {book.get('author', '')}\n"
                f"Gia: {book.get('price', 0)} VND\n"
                f"The loai: {cat_name}\n"
                f"ISBN: {book.get('isbn', '')}\n"
                f"Mo ta: {book.get('description', '')}\n"
                f"Con hang: {'Co' if book.get('stock', 0) > 0 else 'Het hang'} ({book.get('stock', 0)} cuon)"
            )
            book_docs.append({
                'title': f"Sach: {book.get('title', '')} - {book.get('author', '')}",
                'content': content,
                'source': 'book_catalog',
            })

        if book_docs:
            self.stdout.write(f"Embedding {len(book_docs)} book catalog documents...")
            try:
                bulk_embed_and_store(book_docs)
                self.stdout.write(self.style.SUCCESS(f"Stored {len(book_docs)} book catalog documents"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to embed book catalog: {e}"))
