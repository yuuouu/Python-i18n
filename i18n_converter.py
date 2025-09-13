#!/usr/bin/env python3
"""
Tool to convert an Excel i18n table into platform‑specific resource files.

This script reads a `.xlsx` spreadsheet containing translation keys and
values for multiple languages and emits the corresponding translation files
for Android, iOS and/or PC targets.  The spreadsheet is expected to have
a column called ``key`` which holds the resource identifiers.  All other
columns are treated as language columns.  The language code is inferred
from the column name: text within parentheses is interpreted as the
language code (e.g. ``中文(zh‑CN)`` → ``zh‑CN``).  If no parentheses are
present the column name itself becomes the language code.

Features:

* Duplicate keys are detected and reported as an error – no output will
  be generated when duplicates exist.
* Missing translations fall back to the English (``en``) column when
  present, otherwise the first language column acts as the fallback.
* Supports emitting resources for Android (`strings.xml`), iOS
  (`Localizable.strings`) and PC (`.ini`) simultaneously or individually.
* Output is rooted in the directory specified via ``--output`` (default
  ``res``).  Files are written into subdirectories according to
  platform conventions.

Usage:

    python i18n_converter.py --input translations.xlsx \
        --platforms android,ios,pc --output res

The input Excel file may contain arbitrary extra columns; only the
language columns are considered for translation output.

"""

import argparse
import os
import re
import sys
import shutil
from typing import Dict, List, Tuple
import pandas as pd
from xml.etree import ElementTree as ET

defautlPlatform = "android,ios,pc"

def parse_language_code(column_name: str) -> str:
    """Extract a language code from a column name.

    The function looks for a substring enclosed in parentheses.  If one
    exists it is returned (whitespace trimmed).  Otherwise the entire
    column name, stripped of surrounding whitespace, is returned.

    Examples::

        parse_language_code('中文(zh‑CN)') -> 'zh‑CN'
        parse_language_code('English (en)') -> 'en'
        parse_language_code('en') -> 'en'
        parse_language_code('fr') -> 'fr'

    Parameters
    ----------
    column_name: str
        The header label from which to extract the language code.

    Returns
    -------
    str
        A normalized language code.
    """
    if not isinstance(column_name, str):
        return str(column_name).strip()
    match = re.search(r"\(([^)]+)\)", column_name)
    if match:
        return match.group(1).strip()
    return column_name.strip()


def determine_fallback_column(languages: Dict[str, str]) -> str:
    """Determine the fallback column used when translations are missing.

    Prefers columns whose language code equates to English ('en' or
    variants such as 'en-us').  Falls back to the first entry in the
    mapping if no English variant is present.

    Parameters
    ----------
    languages: Dict[str, str]
        A mapping of column names to language codes.

    Returns
    -------
    str
        The column name which should be used as a fallback.
    """
    # Define potential English codes in lower case
    english_codes = {'en', 'en-us', 'en_us', 'english', 'es'}
    for col, code in languages.items():
        if code.lower() in english_codes:
            return col
    # no explicit English column found – use the first language column
    # (ensuring deterministic ordering by iteration over dict items)
    for col in languages:
        return col
    raise ValueError("No language columns found to select a fallback from")


def escape_android_text(text: str) -> str:
    """Escape special characters for Android XML.

    The Android XML format requires certain characters to be escaped.
    This function replaces & < > ' " characters with their corresponding
    XML entities and escapes apostrophes using a backslash (per Android
    string resource requirements).

    Parameters
    ----------
    text: str
        The raw text to escape.

    Returns
    -------
    str
        The escaped text.
    """
    if text is None:
        return ''
    replacements = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '\"',
    }
    # Replace '&' first to avoid double escaping
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Android strings treat apostrophe as escape with backslash
    text = text.replace("'", "\\'")
    return text


def write_android_resources(language_code: str, items: List[Tuple[str, str]], output_root: str) -> None:
    """Write Android string resources to the appropriate location.

    Creates a file at ``res/values-<language_code>/strings.xml`` containing
    all translations for the specified language.  Ensures directories
    exist prior to writing.

    Parameters
    ----------
    language_code: str
        The BCP‑47 language tag for the output directory.
    items: List[Tuple[str, str]]
        A list of (key, value) pairs for this language.
    output_root: str
        The root directory where the ``res`` folder resides.
    """
    values_dir = os.path.join(output_root, f'values-{language_code}')
    os.makedirs(values_dir, exist_ok=True)
    file_path = os.path.join(values_dir, 'strings.xml')

    # Build XML tree
    resources = ET.Element('resources')
    for key, value in items:
        elem = ET.SubElement(resources, 'string', attrib={'name': key})
        elem.text = escape_android_text(value)
    # Pretty print the XML with indentation for readability
    from xml.dom import minidom
    rough_string = ET.tostring(resources, encoding='utf-8')
    parsed = minidom.parseString(rough_string)
    pretty_xml = parsed.toprettyxml(indent='    ', encoding='utf-8')
    # Write with XML declaration at the top
    with open(file_path, 'wb') as f:
        f.write(pretty_xml)


def write_ios_resources(language_code: str, items: List[Tuple[str, str]], output_root: str) -> None:
    """Write iOS string resources to a ``Localizable.strings`` file.

    Creates a file at ``res/<language_code>.lproj/Localizable.strings``.
    Ensures directories exist prior to writing.  Values are quoted and
    terminated with a semicolon, as per Apple property list strings.

    Parameters
    ----------
    language_code: str
        The BCP‑47 language tag for the output directory.
    items: List[Tuple[str, str]]
        A list of (key, value) pairs for this language.
    output_root: str
        The root directory where the ``res`` folder resides.
    """
    lang_dir = os.path.join(output_root, f'{language_code}.lproj')
    os.makedirs(lang_dir, exist_ok=True)
    file_path = os.path.join(lang_dir, 'Localizable.strings')

    with open(file_path, 'w', encoding='utf-8') as f:
        for key, value in items:
            # Escape quotes and backslashes
            escaped_key = key.replace('"', '\\"').replace('\\', '\\\\')
            escaped_value = (value or '').replace('"', '\\"').replace('\\', '\\\\')
            f.write(f'"{escaped_key}" = "{escaped_value}";\n')


def write_pc_resources(language_code: str, items: List[Tuple[str, str]], output_root: str) -> None:
    """Write PC (INI) resources to a file.

    Creates a file at ``res/<language_code>.ini``.  Each entry is
    represented as ``key = "value";``.  Missing values are written as
    empty strings.

    Parameters
    ----------
    language_code: str
        The language code for the output filename.
    items: List[Tuple[str, str]]
        A list of (key, value) pairs for this language.
    output_root: str
        The root directory where the ``res`` folder resides.
    """
    os.makedirs(output_root, exist_ok=True)
    file_path = os.path.join(output_root, f'{language_code}.ini')

    with open(file_path, 'w', encoding='utf-8') as f:
        for key, value in items:
            val = value or ''
            # Quote the value and terminate with semicolon
            f.write(f'{key} = "{val}";\n')

def clear_dir_contents(output_root: str):
    if os.path.exists(output_root):
        for filename in os.listdir(output_root):
            file_path = os.path.join(output_root, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
    else:
        os.makedirs(output_root)

def convert_table(df: pd.DataFrame, output_root: str, platforms: List[str]) -> None:
    """Convert a DataFrame of translations into platform files.

    Parameters
    ----------
    df: pd.DataFrame
        The translation table containing at least a ``key`` column and one
        or more language columns.
    output_root: str
        Directory in which to write the ``res`` folder and contents.
    platforms: List[str]
        Platforms to generate.  Supported values: ``android``, ``ios``,
        ``pc``.
    """
    if 'key' not in df.columns:
        raise ValueError("Input spreadsheet must contain a 'key' column")

    # Normalize DataFrame – ensure string dtype and replace NaNs with empty
    df = df.copy()
    df['key'] = df['key'].astype(str)
    df.fillna('', inplace=True)

    # Check for duplicate keys
    duplicated_keys = df['key'][df['key'].duplicated()]
    if not duplicated_keys.empty:
        dup_list = ', '.join(sorted(duplicated_keys.unique()))
        raise ValueError(f"Duplicate keys found: {dup_list}")

    # Build mapping from column names to language codes (excluding 'key')
    language_columns: Dict[str, str] = {}
    for col in df.columns:
        if col == 'key':
            continue
        lang_code = parse_language_code(col)
        language_columns[col] = lang_code

    if not language_columns:
        raise ValueError("No language columns found in the spreadsheet")

    fallback_col = determine_fallback_column(language_columns)

    # Prepare items per language: list of (key, value)
    for col, lang_code in language_columns.items():
        items: List[Tuple[str, str]] = []
        for _, row in df.iterrows():
            key = row['key']
            raw_value = row[col]
            fallback_value = row[fallback_col]
            value = raw_value if str(raw_value).strip() else str(fallback_value) if fallback_value is not None else ''
            items.append((key, value))

        # Write to each requested platform
        if 'android' in platforms:
            write_android_resources(lang_code, items, output_root)
        if 'ios' in platforms:
            write_ios_resources(lang_code, items, output_root)
        if 'pc' in platforms:
            write_pc_resources(lang_code, items, output_root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert an Excel translation file into platform‑specific resource files.")
    parser.add_argument('-i', '--input', required=True, help='Path to the input Excel (.xlsx) file')
    parser.add_argument('-o', '--output', default='res', help='Root directory for the output resources (default: res)')
    parser.add_argument('-p', '--platforms', default=defautlPlatform, help='Comma‑separated list of platforms to generate (android, ios, pc)')

    args = parser.parse_args()
    input_path = args.input
    output_root = args.output
    platform_list = [p.strip().lower() for p in args.platforms.split(',') if p.strip()]
    allowed = {'android', 'ios', 'pc'}
    invalid = [p for p in platform_list if p not in allowed]
    if invalid:
        print(f"Unsupported platform(s): {', '.join(invalid)}", file=sys.stderr)
        sys.exit(1)

    try:
        clear_dir_contents(output_root)
    except Exception as exc:
        print(f"Failed to '{input_path}'")

    # Load Excel
    try:
        df = pd.read_excel(input_path, dtype=str)
    except Exception as exc:
        print(f"Failed to read input Excel file '{input_path}': {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        convert_table(df, output_root, platform_list)
    except ValueError as ve:
        print(f"Error: {ve}", file=sys.stderr)
        sys.exit(1)

    print(f"Successfully generated resources for platforms: {', '.join(platform_list)}")


if __name__ == '__main__':
    main()