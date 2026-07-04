import sys

from app.db import SessionLocal
from app.importer import import_questions, parse_workbook


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] != "import":
        print("Usage: python -m app.cli import <path-to-xlsx>")
        return 1

    rows = parse_workbook(argv[1])
    with SessionLocal() as session:
        stats = import_questions(session, rows)
    print(f"Imported: {stats['created']} created, {stats['updated']} updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
