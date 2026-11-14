"""Offline reference validation. Parse Markdown and images; never execute examples."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from markdown_it import MarkdownIt

from ci_scope import documentation_path

MARKDOWN = MarkdownIt('commonmark')


class HtmlReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.anchors = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get('id'):
            self.anchors.add(values['id'])
        if tag == 'a' and values.get('name'):
            self.anchors.add(values['name'])
        for attr in ('href', 'src'):
            if values.get(attr):
                self.links.append(values[attr])


def markdown(text):
    links = []
    anchors = set()
    counts = {}
    html = HtmlReferences()
    tokens = MARKDOWN.parse(text)
    for index, token in enumerate(tokens):
        if token.type == 'heading_open':
            inline = tokens[index + 1]
            title = ''.join(child.content for child in (inline.children or [])
                            if child.type in ('text', 'code_inline'))
            slug = re.sub(r'[^\w\- ]', '', title.lower()).replace(' ', '-')
            count = counts.get(slug, 0)
            candidate = slug + (f'-{count}' if count else '')
            while candidate in anchors:
                count += 1
                candidate = f'{slug}-{count}'
            counts[slug] = count + 1
            anchors.add(candidate)
        if token.type == 'html_block':
            html.feed(token.content)
        for child in token.children or []:
            if child.type == 'link_open':
                links.append(child.attrGet('href'))
            elif child.type == 'image':
                links.append(child.attrGet('src'))
            elif child.type == 'html_inline':
                html.feed(child.content)
    return links + html.links, anchors | html.anchors


def formatting(text):
    errors = []
    if not text.strip():
        errors.append('empty Markdown document')
    if '\x00' in text:
        errors.append('NUL byte in Markdown')
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r' {0,3}(`{3,}|~{3,})(.*)$', line)
        if not match:
            continue
        marker, tail = match.groups()
        if fence is None:
            fence = (marker[0], len(marker), number)
        elif marker[0] == fence[0] and len(marker) >= fence[1] and not tail.strip():
            fence = None
    if fence:
        errors.append(f'unclosed code fence at line {fence[2]}')
    if text and not text.endswith('\n'):
        errors.append('missing final newline')
    return errors


def image_valid(path):
    data = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix == '.svg':
        try:
            root = ET.fromstring(data)
            return root.tag.rsplit('}', 1)[-1] == 'svg'
        except ET.ParseError:
            return False
    signatures = {
        '.png': data.startswith(b'\x89PNG\r\n\x1a\n'),
        '.jpg': data.startswith(b'\xff\xd8\xff'),
        '.jpeg': data.startswith(b'\xff\xd8\xff'),
        '.gif': data.startswith((b'GIF87a', b'GIF89a')),
        '.webp': data.startswith(b'RIFF') and data[8:12] == b'WEBP',
    }
    return signatures.get(suffix, False)


def validate(root, paths, reference_paths=()):
    root = Path(root).resolve()
    changed = set(paths)
    errors = []
    cache = {}

    def content(path):
        if path not in cache:
            cache[path] = markdown(path.read_text(encoding='utf-8'))
        return cache[path]

    for name in sorted(changed):
        if not isinstance(name, str) or not documentation_path(name):
            errors.append(f'{name!r}: not an approved reference path')
            continue
        path = root / name
        if not path.exists() and not path.is_symlink():
            continue  # Deleted references are checked below for inbound links.
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o111:
            errors.append(f'{name}: reference must be a regular, non-executable file')
            continue
        try:
            if path.suffix.lower() == '.md':
                text = path.read_text(encoding='utf-8')
                errors.extend(f'{name}: {error}' for error in formatting(text))
                content(path)
            elif not image_valid(path):
                errors.append(f'{name}: invalid image signature or SVG structure')
        except (OSError, UnicodeError) as error:
            errors.append(f'{name}: unreadable reference ({type(error).__name__})')

    for name in sorted(changed | set(reference_paths)):
        path = root / name
        if path.suffix.lower() != '.md' or not path.is_file() or path.is_symlink():
            continue
        try:
            links, _ = content(path)
            for href in links:
                parsed = urlsplit(href)
                if parsed.scheme or parsed.netloc or href.startswith('//'):
                    continue  # Offline: no authenticated URLs or network probes.
                target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path.resolve()
                try:
                    target_name = target.relative_to(root).as_posix()
                except ValueError:
                    if name in changed:
                        errors.append(f'{name}: link leaves repository: {href}')
                    continue
                if name not in changed and target_name not in changed:
                    continue  # Do not reject unrelated historical link debt.
                if not target.exists():
                    errors.append(f'{name}: missing local target: {href}')
                elif (name in changed and parsed.fragment and target.suffix.lower() == '.md'
                      and unquote(parsed.fragment) not in content(target)[1]):
                    errors.append(f'{name}: missing Markdown heading/anchor: {href}')
        except (OSError, UnicodeError, ValueError) as error:
            if name in changed:
                errors.append(f'{name}: cannot check links ({type(error).__name__})')
    return errors


def main():
    raw = os.environ.get('DOCUMENTATION_PATHS')
    if raw is None:
        raise SystemExit('Missing DOCUMENTATION_PATHS manifest')
    paths = json.loads(raw)
    if not isinstance(paths, list) or not paths or not all(isinstance(p, str) for p in paths):
        raise SystemExit('Invalid or empty documentation manifest')
    root = Path(__file__).resolve().parents[1]
    references = subprocess.run(['git', 'ls-files', '-z', '--', '*.md'], cwd=root,
                                capture_output=True, check=True).stdout.decode().rstrip('\0').split('\0')
    errors = validate(root, paths, references)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        raise SystemExit(1)
    print(f'PASS: {len(paths)} changed reference paths; offline Markdown, formatting, links and image checks')


if __name__ == '__main__':
    main()
