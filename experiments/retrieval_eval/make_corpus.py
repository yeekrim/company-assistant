"""업무추진비 CSV → PDF 표. 앱 업로드가 받는 형식(PDF)으로 맞추기 위한 변환이다.

sql_harness/make_data.py와 같은 방식(reportlab, 내장 한글 CID 폰트, 페이지마다 헤더 반복)으로 만든다.

    ../../backend/venv/bin/python make_corpus.py
"""
import csv

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from companies import CORPUS, EXPENSES

FONT = "HYGothic-Medium"
MAX_CELL = 40  # 긴 셀(주소 등)은 잘라서 표가 페이지를 넘지 않게


def load(path, encoding, columns, keep) -> list[list[str]]:
    with open(path, encoding=encoding, newline="") as f:
        rows = [r for r in csv.DictReader(f) if keep is None or keep(r)]
    return [[(r[c] or "").strip()[:MAX_CELL] for c in columns] for r in rows]


def write_pdf(out, title, columns, rows):
    h1 = ParagraphStyle("h1", fontName=FONT, fontSize=14, leading=20, spaceAfter=6)
    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
    ])
    story = [Paragraph(title, h1), Spacer(1, 4), Table([columns] + rows, repeatRows=1, style=style)]
    SimpleDocTemplate(str(out), pagesize=landscape(A4), leftMargin=20, rightMargin=20).build(story)


def main():
    pdfmetrics.registerFont(UnicodeCIDFont(FONT))
    CORPUS.mkdir(parents=True, exist_ok=True)
    for name, (path, encoding, title, columns, keep) in EXPENSES.items():
        rows = load(path, encoding, columns, keep)
        out = CORPUS / f"{name}.pdf"
        write_pdf(out, title, columns, rows)
        print(f"{out.name}: {len(rows)}행")


if __name__ == "__main__":
    main()
