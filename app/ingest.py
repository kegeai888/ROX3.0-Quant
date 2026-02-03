import os
import time
from typing import Optional

from .db import get_conn, ensure_schema, upsert_doc, update_fts


def read_txt(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return None


def read_docx(path: str) -> Optional[str]:
    try:
        import docx  # type: ignore
    except Exception:
        return None
    try:
        d = docx.Document(path)
        return "\n".join(p.text for p in d.paragraphs)
    except Exception:
        return None


def read_pdf(path: str) -> Optional[str]:
    try:
        from pdfminer.high_level import extract_text  # type: ignore
    except Exception:
        return None
    try:
        return extract_text(path)
    except Exception:
        return None


def extract_content(path: str, ext: str) -> Optional[str]:
    e = ext.lower()
    if e == ".txt":
        return read_txt(path)
    if e == ".docx":
        return read_docx(path)
    if e == ".pdf":
        return read_pdf(path)
    return None


def ingest_dir(root: str):
    conn = get_conn()
    ensure_schema(conn)
    total = 0
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            try:
                st = os.stat(fpath)
            except FileNotFoundError:
                continue
            ext = os.path.splitext(fname)[1]
            content = extract_content(fpath, ext)
            print(f"Ingesting: {fname}")
            doc_id = upsert_doc(
                conn,
                fpath,
                fname,
                ext.lower(),
                int(st.st_size),
                float(st.st_mtime),
                content,
            )
            conn.commit()
            update_fts(conn, doc_id, content or "")
            total += 1
    conn.close()
    return total


def main():
    root = "/Users/mac/Documents/word+pdf"
    t0 = time.time()
    n = ingest_dir(root)
    t1 = time.time()
    print(f"Ingested {n} files from {root} in {t1-t0:.2f}s")


if __name__ == "__main__":
    main()
