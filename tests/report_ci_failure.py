"""Emit bounded failure detail as an Actions annotation, without downloading logs."""
from pathlib import Path
import sys


def annotation(path):
    with Path(path).open('rb') as stream:
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(max(0, size - 8192))
        text = stream.read(8192).decode('utf-8', errors='replace')
    escaped = text.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    return '::error title=Coordination test failure::' + escaped


if __name__ == '__main__':
    print(annotation(sys.argv[1]))
