"""
为课程资料 PDF 生成真实文件并注册到数据库。
读取 pdf_content_data.json 中的结构化内容，生成可打开的 PDF。
仅处理 type=pdf 且尚未关联文件的 Material。

用法：
    cd backend
    py generate_pdf_materials.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from app.db.session import SessionLocal
from app.models.entities import Material, MaterialPreview, StoredFile

BACKEND_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BACKEND_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
FONT_PATH = "C:/Windows/Fonts/simsun.ttc"  # SimSun font for Chinese


def generate_pdf(title: str, chapters: list, output_path: str) -> str:
    """Generate a multi-page Chinese PDF with fpdf2."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Register Chinese font
    pdf.add_font("SimSun", "", FONT_PATH, uni=True)
    pdf.add_font("SimSun", "B", FONT_PATH, uni=True)

    # ---------- Cover ----------
    pdf.add_page()
    pdf.ln(60)
    pdf.set_font("SimSun", "B", 28)
    pdf.cell(0, 18, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(10)
    pdf.set_font("SimSun", "", 14)
    pdf.cell(0, 10, "AI Tongshi Education Platform", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(5)
    pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(20)
    pdf.set_font("SimSun", "", 11)
    pdf.cell(0, 8, "For educational reference only.", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

    # ---------- Table of Contents ----------
    pdf.add_page()
    pdf.set_font("SimSun", "B", 20)
    pdf.cell(0, 14, "CONTENTS", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(10)
    for chapter_title, sections in chapters:
        pdf.set_font("SimSun", "B", 12)
        pdf.cell(0, 9, chapter_title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        for section_title, _ in sections:
            pdf.set_font("SimSun", "", 11)
            pdf.cell(10, 7, "")
            pdf.cell(0, 7, section_title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ---------- Body Content ----------
    for chapter_title, sections in chapters:
        pdf.add_page()
        pdf.set_font("SimSun", "B", 18)
        pdf.cell(0, 14, chapter_title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2)
        pdf.ln(8)

        for section_title, content in sections:
            pdf.set_font("SimSun", "B", 14)
            pdf.cell(0, 10, section_title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2)
            pdf.set_font("SimSun", "", 11)

            paragraphs = content.strip().split("\n\n")
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                if pdf.get_y() > 260:
                    pdf.add_page()
                    pdf.set_font("SimSun", "", 11)
                pdf.multi_cell(0, 6.5, para)
                pdf.ln(2)

    pdf.output(output_path)
    return output_path


def main():
    # Load content data from JSON
    json_path = BACKEND_DIR / "pdf_content_data.json"
    with open(json_path, "r", encoding="utf-8") as f:
        pdf_data = json.load(f)

    db = SessionLocal()
    created_count = 0

    try:
        for title, config in pdf_data.items():
            mat = db.query(Material).filter(
                Material.type == "pdf",
                Material.title == title,
            ).first()

            if not mat:
                print(f"[skip] Material not found: {title}")
                continue

            # Check if already has a file
            if mat.file_id:
                existing = db.query(StoredFile).filter(StoredFile.id == mat.file_id).first()
                if existing:
                    print(f"[skip] {title} already linked to file_id={mat.file_id}")
                    continue

            # Generate PDF file
            safe_name = title.replace("/", "_").replace(" ", "_").replace(":", "_")
            filename = f"{safe_name}.pdf"
            filepath = UPLOAD_DIR / filename

            print(f"[gen] {title} -> {filename}")
            generate_pdf(title, config["chapters"], str(filepath))

            size_bytes = filepath.stat().st_size
            with open(filepath, "rb") as f:
                sha256 = hashlib.sha256(f.read()).hexdigest()

            # Create StoredFile record
            stored = StoredFile(
                biz_type="material",
                biz_id=mat.id,
                storage_provider="local",
                bucket_name="",
                object_key=f"uploads/{filename}",
                original_name=filename,
                stored_name=filename,
                content_type="application/pdf",
                extension="pdf",
                size_bytes=size_bytes,
                sha256=sha256,
                status="active",
                created_by=mat.course.created_by if mat.course else "admin",
                created_at=datetime.now(timezone.utc),
            )
            db.add(stored)
            db.flush()

            # Link to Material
            mat.file_id = stored.id
            mat.url = f"/api/materials/{mat.id}/file"
            mat.size = f"{size_bytes / 1024 / 1024:.1f} MB"

            # Update MaterialPreview
            preview = db.query(MaterialPreview).filter(
                MaterialPreview.material_id == mat.id
            ).first()
            if preview:
                preview.page_count = len(config["chapters"]) * 2 + 2  # rough page count
                if not preview.status or preview.status == "pending":
                    preview.status = "ready"

            db.commit()
            created_count += 1
            print(f"  [ok] {filename} {size_bytes/1024:.0f}KB sha256={sha256[:16]}...")

    finally:
        db.close()

    print(f"\nDone! Generated {created_count} PDF files.")
    print(f"Dir: {UPLOAD_DIR}")


if __name__ == "__main__":
    main()
