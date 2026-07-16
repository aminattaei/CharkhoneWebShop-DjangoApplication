#!/usr/bin/env python3
"""
Convert hardcoded static file paths in Django HTML templates to {% static %} tags.

Scans HTML files inside the templates/ directory, detects hardcoded paths
in src, href, and data-* attributes, and replaces them with Django's
{% static '...' %} template tag.
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

STATIC_PREFIXES = ("/static/", "static/", "/assets/", "assets/")

# Matches src, href, or data-* attributes with single or double quoted values.
# Group 1: attribute name, Group 2: double-quoted value, Group 3: single-quoted value
ATTR_PATTERN = re.compile(
    r'''((?:src|href|data-[\w-]+))\s*=\s*(?:"([^"]*)"|'([^']*)')''',
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert hardcoded static paths to Django {% static %} tags."
    )
    parser.add_argument(
        "--dir",
        type=str,
        default="templates/",
        help="Path to the templates directory (default: templates/)",
    )
    return parser.parse_args()


def has_static_tag(content: str) -> bool:
    """Return True if content already uses Django static template tags."""
    return "{% static" in content


def convert_match(match: re.Match) -> str:
    """Replace a single attribute match with the {% static %} tag if applicable.

    Preserves the original attribute name and quote style. Strips the static
    prefix from the path and wraps it in {% static '...' %}. Query strings
    and fragments are preserved after the closing %}.
    """
    attr_name = match.group(1)
    double_quoted = match.group(2)
    single_quoted = match.group(3)

    if double_quoted is not None:
        value = double_quoted
        quote = '"'
    elif single_quoted is not None:
        value = single_quoted
        quote = "'"
    else:
        return match.group(0)

    # Separate path from query string / fragment
    suffix = ""
    path_part = value
    for sep in ("?", "#"):
        idx = path_part.find(sep)
        if idx != -1:
            suffix = path_part[idx:]
            path_part = path_part[:idx]
            break

    matched_prefix = None
    for prefix in STATIC_PREFIXES:
        if path_part.startswith(prefix):
            matched_prefix = prefix
            break

    if matched_prefix is None:
        return match.group(0)

    relative = path_part[len(matched_prefix):]
    # Django {% static %} uses single quotes inside; switch outer quotes
    # to double quotes when the original attribute used single quotes,
    # to avoid nested single quotes like href='{% static '...' %}'.
    if quote == "'":
        quote = '"'
    return f'{attr_name}={quote}{{% static \'{relative}\' %}}{suffix}{quote}'


def count_conversions(original: str, converted: str) -> int:
    """Count how many attribute values were actually changed."""
    return sum(
        1
        for orig, new in zip(
            ATTR_PATTERN.findall(original), ATTR_PATTERN.findall(converted)
        )
        if orig != new
    )


def process_file(file_path: Path) -> int:
    """Process a single HTML file, converting hardcoded static paths.

    Creates a .bak backup before modifying. Returns the number of
    conversions made, 0 if no changes needed, or -1 on error.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"  ERROR reading {file_path}: {exc}")
        return -1

    if has_static_tag(content):
        print(f"  SKIPPED (already uses static tag): {file_path}")
        return 0

    new_content = ATTR_PATTERN.sub(convert_match, content)

    if new_content == content:
        print(f"  No changes: {file_path}")
        return 0

    backup_path = file_path.with_suffix(file_path.suffix + ".bak")
    try:
        shutil.copy2(file_path, backup_path)
    except Exception as exc:
        print(f"  ERROR creating backup {backup_path}: {exc}")
        return -1

    try:
        file_path.write_text(new_content, encoding="utf-8")
    except Exception as exc:
        print(f"  ERROR writing {file_path}: {exc}")
        return -1

    num = count_conversions(content, new_content)
    print(f"  Changed {num} path(s): {file_path}")
    return num


def main() -> None:
    """Main entry point: discover HTML files, process each, print summary."""
    args = parse_args()
    templates_dir = Path(args.dir).resolve()

    if not templates_dir.is_dir():
        print(f"Error: '{templates_dir}' is not a valid directory.")
        sys.exit(1)

    html_files = sorted(templates_dir.rglob("*.html"))

    if not html_files:
        print(f"No HTML files found in {templates_dir}")
        sys.exit(0)

    print(f"Scanning: {templates_dir}")
    print(f"Found {len(html_files)} HTML file(s)\n")

    total_changes = 0
    files_changed = 0
    errors = 0

    for html_file in html_files:
        result = process_file(html_file)
        if result == -1:
            errors += 1
        elif result > 0:
            total_changes += result
            files_changed += 1

    print("\n--- Summary ---")
    print(f"Files scanned:  {len(html_files)}")
    print(f"Files changed:  {files_changed}")
    print(f"Total changes:  {total_changes}")
    print(f"Errors:         {errors}")


if __name__ == "__main__":
    main()
