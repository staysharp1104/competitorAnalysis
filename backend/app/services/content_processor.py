"""内容处理服务"""
import os
from markdownify import markdownify as md
from typing import Optional
import trafilatura

class ContentProcessor:
    @staticmethod
    async def process_html(html_content: str) -> dict:
        clean_text = trafilatura.extract(html_content, include_links=True, include_images=False, include_tables=True, no_fallback=False, output_format="txt") or ""
        markdown_content = md(html_content, heading_style="ATX", strip=["script","style","nav","footer","aside"])
        return {"clean_text": clean_text, "markdown_content": markdown_content, "word_count": len(clean_text)}

    @staticmethod
    async def process_pdf(file_path: str) -> dict:
        import fitz
        doc = fitz.open(file_path)
        full_text = "\n\n".join(page.get_text() for page in doc)
        doc.close()
        return {"clean_text": full_text, "markdown_content": full_text, "word_count": len(full_text), "page_count": len(doc)}

    @staticmethod
    async def process_plain_text(text: str, title: Optional[str] = None) -> dict:
        return {"clean_text": text, "markdown_content": f"# {title or '页面内容'}\n\n{text}" if title else text, "word_count": len(text)}
