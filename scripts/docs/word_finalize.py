"""Open each generated .docx in Microsoft Word, refresh the table of contents and fields,
save it, and export a PDF copy next to it. Windows with Word installed only.

Usage: python scripts/docs/word_finalize.py docs/word/Laporan-Proyek-LabTrack.docx [...]
"""
import sys
from pathlib import Path

import win32com.client

WD_FORMAT_PDF = 17


def finalize(path):
    # One Word process per document: the late-bound COM proxy gets unreliable when reused
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(path)
        for toc in doc.TablesOfContents:
            toc.Update()
        doc.Fields.Update()
        doc.Save()
        pdf = str(Path(path).with_suffix(".pdf"))
        doc.ExportAsFixedFormat(pdf, WD_FORMAT_PDF)
        print(f"{Path(path).name}: {doc.ComputeStatistics(2)} pages, {doc.ComputeStatistics(0)} words -> {Path(pdf).name}")
        doc.Close(False)
    finally:
        try:
            word.Quit()
        except Exception:  # noqa: BLE001 - Word may already be gone (RPC failure); output is saved by then
            pass


def main(paths):
    for p in paths:
        finalize(str(Path(p).resolve()))


if __name__ == "__main__":
    main(sys.argv[1:])
