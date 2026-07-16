#!/usr/bin/env python3
"""
Django Static Path Converter
-----------------------------
This script scans HTML files in a given directory and replaces hardcoded static file paths 
(e.g., "/static/css/style.css") with Django's {% static %} template tag.

Usage:
    python convert_static.py [--dir TEMPLATES_DIR] [--backup] [--dry-run]

Author: Amin Attaei
"""

import os
import re
import argparse
import shutil
from pathlib import Path

# Default template directory
DEFAULT_TEMPLATES_DIR = "templates"

# Regex pattern to match static file paths in HTML attributes
# Matches: src="static/...", href="/static/...", src="assets/...", etc.
STATIC_PATTERN = re.compile(
    r'(?P<attr>(?:src|href|data-[a-zA-Z-]+))\s*=\s*'
    r'(?P<quote>[\'"])(?P<path>(?:/?(?:static|assets))/[^\'"]+)(?P=quote)',
    re.IGNORECASE
)


def convert_static_paths(file_path, dry_run=False, backup=False):
    """
    Reads an HTML file, replaces static file paths with Django's {% static %} tag,
    and overwrites the file with updated content.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return 0

    # Skip files that already use {% static %}
    if re.search(r"{%\s*static\s+['\"]", content):
        print(f"⏭️  Skipping {file_path} (already using {% static %})")
        return 0

    # Find all matches
    matches = list(STATIC_PATTERN.finditer(content))
    if not matches:
        return 0

    # Backup original file if requested
    if backup:
        backup_path = f"{file_path}.bak"
        try:
            shutil.copy2(file_path, backup_path)
            print(f"📁 Backup created: {backup_path}")
        except Exception as e:
            print(f"⚠️  Could not create backup for {file_path}: {e}")

    # Perform replacements
    changed_count = 0
    new_content = content

    # Process matches in reverse to maintain correct positions
    for match in reversed(matches):
        old_text = match.group(0)
        attr = match.group('attr')
        quote = match.group('quote')
        path = match.group('path')

        # Remove leading /static/ or /assets/ and keep only the relative path
        clean_path = re.sub(r'^/?(?:static|assets)/', '', path)

        # Build the new tag
        new_text = f'{attr}={quote}{% static "{clean_path}" %}{quote}'

        # Perform the replacement in the new content
        new_content = new_content[:match.start()] + new_text + new_content[match.end():]
        changed_count += 1

        # Print a sample of the change
        print(f"  🔄 Changed: {old_text[:50]}... → {new_text[:50]}...")

    # Write changes if not a dry run
    if not dry_run:
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(new_content)
            print(f"✅ Processed: {file_path} ({changed_count} changes)")
        except Exception as e:
            print(f"❌ Error writing {file_path}: {e}")
            return 0
    else:
        print(f"🔍 DRY RUN: Would process {file_path} ({changed_count} changes)")

    return changed_count


def process_templates(template_dir, dry_run=False, backup=False):
    """
    Loops through all HTML files in the specified directory
    and applies the static path conversion.
    """
    total_files = 0
    total_changes = 0

    if not os.path.exists(template_dir):
        print(f"❌ Directory '{template_dir}' does not exist.")
        return

    print(f"🔍 Scanning for HTML files in: {template_dir}")
    print("=" * 60)

    for root, _, files in os.walk(template_dir):
        for file in files:
            if file.endswith(".html") or file.endswith(".htm"):
                file_path = os.path.join(root, file)
                changes = convert_static_paths(file_path, dry_run, backup)
                if changes > 0:
                    total_files += 1
                    total_changes += changes

    print("=" * 60)
    print(f"📊 Summary: {total_files} files processed, {total_changes} changes made.")
    if dry_run:
        print("⚠️  This was a DRY RUN. No files were actually modified.")


def main():
    parser = argparse.ArgumentParser(
        description="Convert hardcoded static paths to Django {% static %} tags."
    )
    parser.add_argument(
        "--dir",
        default=DEFAULT_TEMPLATES_DIR,
        help=f"Directory containing HTML templates (default: {DEFAULT_TEMPLATES_DIR})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the process without modifying any files"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create a .bak backup of each modified file"
    )

    args = parser.parse_args()

    process_templates(args.dir, args.dry_run, args.backup)


if __name__ == "__main__":
    main()