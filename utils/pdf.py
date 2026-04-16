import os
import re
import html
import markdown
from playwright.sync_api import sync_playwright


def _normalize_tag_table(block_text):
    """Convert [TABLE_START]... [TABLE_END] block text to markdown table."""
    lines = [ln.strip() for ln in str(block_text or '').split('\n') if ln.strip()]
    rows = []
    for line in lines:
        # Ignore markdown separator rows; we generate our own separator.
        if re.match(r'^\|?\s*[-:]+(\s*\|\s*[-:]+)+\s*\|?$', line):
            continue
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        if len(cells) >= 2:
            rows.append(cells)

    if not rows:
        return ''

    max_cols = max(len(r) for r in rows)
    normalized = [r + [''] * (max_cols - len(r)) for r in rows]
    header = normalized[0]
    body = normalized[1:]

    # If AI emits placeholder headers like Col1/Col2/Col3, use first data row as header.
    if body and all(re.match(r'^col\s*\d+$', str(h).strip(), flags=re.IGNORECASE) for h in header):
        header = body[0]
        body = body[1:]

    md_lines = [
        '| ' + ' | '.join(header) + ' |',
        '| ' + ' | '.join(['---'] * max_cols) + ' |',
    ]
    for row in body:
        md_lines.append('| ' + ' | '.join(row) + ' |')

    return '\n'.join(md_lines)


def _normalize_tag_list(block_text, ordered=False):
    """Convert list-tag blocks to markdown list syntax."""
    lines = [ln.strip() for ln in str(block_text or '').split('\n') if ln.strip()]
    out = []
    n = 1
    for line in lines:
        # Preserve explicit list markers if they already exist.
        if re.match(r'^(-|\*|\+|\d+\.)\s+', line):
            out.append(line)
            continue

        if ordered:
            out.append(f'{n}. {line}')
            n += 1
        else:
            out.append(f'- {line}')

    return '\n'.join(out)


def _apply_custom_format_tags(text):
    """Translate custom n8n formatting tags into markdown understood by renderer."""
    source = '' if text is None else str(text)
    if not source:
        return source

    # Normalize bold-style inline tags first.
    source = re.sub(r'\[BOLD\](.*?)\[/BOLD\]', r'**\1**', source, flags=re.IGNORECASE | re.DOTALL)

    # Subtitle is treated as a strong lead line; keeps print layout stable.
    source = re.sub(
        r'\[SUBTITLE\](.*?)\[/SUBTITLE\]',
        lambda m: f"\n\n**{m.group(1).strip()}**\n\n",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Subpoint becomes a nested bullet-compatible line.
    source = re.sub(
        r'\[SUBPOINT\](.*?)\[/SUBPOINT\]',
        # Keep indentation below 4 spaces, otherwise markdown treats it as code block.
        lambda m: f"\n  - {m.group(1).strip()}\n",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )

    source = re.sub(
        r'\[\s*TABLE_START\s*\](.*?)\[\s*/?\s*TABLE_END\s*\]',
        lambda m: '\n\n' + _normalize_tag_table(m.group(1)) + '\n\n',
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )

    source = re.sub(
        r'\[\s*BULLET_START\s*\](.*?)\[\s*/?\s*BULLET_END\s*\]',
        lambda m: '\n\n' + _normalize_tag_list(m.group(1), ordered=False) + '\n\n',
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )

    source = re.sub(
        r'\[\s*NUMBER_START\s*\](.*?)\[\s*/?\s*NUMBER_END\s*\]',
        lambda m: '\n\n' + _normalize_tag_list(m.group(1), ordered=True) + '\n\n',
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Drop any leftover known tag tokens that escaped parsing.
    source = re.sub(
        r'\[\s*/?\s*(?:TABLE_START|TABLE_END|BULLET_START|BULLET_END|NUMBER_START|NUMBER_END|SUBTITLE|SUBPOINT|BOLD)\s*\]',
        '',
        source,
        flags=re.IGNORECASE,
    )

    return source


def _normalize_table_format(text):
    """
    Detect and normalize various table formats to proper markdown syntax.
    Handles:
    - Pipe-delimited rows anywhere in text (even inline)
    - Markdown separator rows (---)
    - CSV-like tables with inconsistent spacing
    - Mixed inline and block table formats
    """
    lines = text.split('\n')
    output = []
    in_table = False
    table_rows = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Detect if this line contains table data (pipes with 2+ separators)
        pipe_count = stripped.count('|')
        
        # Check if line looks like table content or separator
        is_table_separator = bool(re.match(r'^\s*[\|\s\-]+$', stripped)) and '|' in stripped and '-' in stripped
        is_table_row = pipe_count >= 2  # Must have at least 2 pipes (3+ cells)
        
        if is_table_row or is_table_separator:
            if not in_table:
                in_table = True
                table_rows = []
            
            # If line has text before pipes, extract just the piped part
            if '|' in stripped:
                # Find first and last pipe positions
                first_pipe = stripped.find('|')
                last_pipe = stripped.rfind('|')
                if first_pipe != last_pipe:  # Has at least 2 pipes
                    table_content = stripped[first_pipe:last_pipe + 1]
                    table_rows.append(table_content)
        else:
            # End of table detected
            if in_table and table_rows:
                md_table = _convert_to_markdown_table(table_rows)
                output.extend(md_table)
                in_table = False
                table_rows = []
            
            output.append(line)
        
        i += 1
    
    # Handle case where text ends with a table
    if in_table and table_rows:
        md_table = _convert_to_markdown_table(table_rows)
        output.extend(md_table)
    
    return '\n'.join(output)


def _convert_to_markdown_table(rows):
    """
    Convert pipe-delimited rows into proper markdown table format:
    | Header 1 | Header 2 |
    |----------|----------|
    | Row 1    | Data     |
    
    Automatically filters out separator rows (---) before processing.
    """
    if not rows:
        return []
    
    # Clean up rows: strip pipes from edges and split by pipe
    cleaned_rows = []
    for row in rows:
        stripped = row.strip()
        if stripped.startswith('|'):
            stripped = stripped[1:]
        if stripped.endswith('|'):
            stripped = stripped[:-1]
        
        cells = [cell.strip() for cell in stripped.split('|')]
        
        # SKIP separator rows (all cells are dashes/empty)
        is_separator = all(c.strip() == '' or all(ch == '-' for ch in c.strip()) for c in cells)
        if not is_separator:
            cleaned_rows.append(cells)
    
    if not cleaned_rows:
        return []
    
    # Ensure all rows have same column count
    max_cols = max(len(row) for row in cleaned_rows) if cleaned_rows else 0
    if max_cols == 0:
        return []
    
    normalized = []
    for row in cleaned_rows:
        # Pad with empty cells if needed
        row = row + [''] * (max_cols - len(row))
        normalized.append(row[:max_cols])
    
    output = []
    
    # First row is header
    header_row = normalized[0]
    output.append('| ' + ' | '.join(header_row) + ' |')
    
    # Add markdown table separator
    separator = '| ' + ' | '.join(['---'] * max_cols) + ' |'
    output.append(separator)
    
    # Add data rows (skip first which is header)
    for row in normalized[1:]:
        output.append('| ' + ' | '.join(row) + ' |')
    
    # Add blank line after table for markdown parser
    output.append('')
    
    return output


def _md_to_html(text):
    """Convert markdown/plain text into safe HTML blocks for PDF rendering."""
    source = '' if text is None else str(text)
    if not source.strip():
        return '<p></p>'

    # Convert custom n8n tags into markdown before further normalization.
    source = _apply_custom_format_tags(source)

    # Normalize various table formats to proper markdown syntax first
    source = _normalize_table_format(source)

    # Keep markdown headings visually modest by treating them as bold lines.
    source = re.sub(r'(?m)^\s{0,3}#{1,6}\s+(.*?)\s*$', r'**\1**', source)

    # Normalize bullet character often returned by LLM/n8n outputs.
    source = re.sub(r'(?m)^(\s*)•\s+', r'\1- ', source)

    # IMPORTANT: Do NOT use 'nl2br' here — it breaks list parsing by converting
    # single newlines (which markdown needs to detect list items) into <br> tags.
    # 'sane_lists' ensures nested lists from AI output parse correctly.
    rendered = markdown.markdown(source, extensions=['tables', 'sane_lists'])

    # Wrap markdown tables with a class hook so CSS can force normal word wrapping
    # without changing global section-content wrapping rules.
    rendered = re.sub(
        r'(?is)<table>(.*?)</table>',
        r'<div class="table-word-safe"><table>\1</table></div>',
        rendered,
    )
    return rendered

def generate_pdf_from_html(html_content, base_url=None, student_name='Student'):
    """Generates a PDF bytes object from an HTML string using Playwright."""
    with sync_playwright() as p:
        # Using chromium headless
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage'],
        )
        context = browser.new_context()
        page = context.new_page()

        rendered_html = html_content
        if base_url and '<base ' not in rendered_html:
            normalized_base = str(base_url).rstrip('/') + '/'
            rendered_html = rendered_html.replace('<head>', f'<head><base href="{normalized_base}">', 1)

        # Extract first header/footer labels for native PDF header/footer templates.
        header_match = re.search(
            r'<div\s+class="page-header">\s*<span>(.*?)</span>\s*<span>(.*?)</span>',
            rendered_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        header_left = ''
        header_right = ''

        if header_match:
            header_left = html.unescape(re.sub(r'<[^>]+>', '', header_match.group(1)).strip())
            header_right = html.unescape(re.sub(r'<[^>]+>', '', header_match.group(2)).strip())

        header_left = html.escape(header_left)
        header_right = html.escape(header_right)
        footer_student_name = html.escape((student_name or 'Student').strip() or 'Student')

        header_template = (
            '<div style="font-size:9pt;color:#555;width:100%;'
            'padding:5pt 14mm 3pt 14mm;'
            'border-bottom:1px solid #ccc;'
            'display:flex;justify-content:space-between;'
            'font-family:Times New Roman,serif;">'
            f'<span>{header_left}</span><span>{header_right}</span>'
            '</div>'
        )
        footer_template = (
            '<div style="font-size:8pt;color:#555;width:100%;'
            'padding:3pt 14mm 3pt 14mm;'
            'border-top:1px solid #999;'
            'display:flex;flex-direction:column;gap:1pt;'
            'font-family:Times New Roman,serif;">'
            '  <div style="display:flex;justify-content:space-between;align-items:center;">'
            f'    <span>{footer_student_name}</span>'
            '    <span>Page <span class="pageNumber"></span></span>'
            '  </div>'
            '  <div style="text-align:center;font-size:7pt;color:#888;">'
            '    Plagiarism check below 15%'
            '  </div>'
            '</div>'
        )

        # Printable width = 210mm - 25.4mm (left) - 25.4mm (right) = 159.2mm = 602px at 96dpi
        # Printable height = 297mm - 30mm (top) - 25.4mm (bottom) = 241.6mm = 914px at 96dpi
        page.set_viewport_size({"width": 602, "height": 914})
        
        # Set content to HTML string
        page.set_content(rendered_html, wait_until='networkidle')

        # Allow template-side TOC pagination script to complete if present.
        try:
            page.wait_for_function('window.__tocReady === true', timeout=4000)
        except Exception:
            pass
        
        # Generate PDF bytes
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template=header_template,
            footer_template=footer_template,
            margin={"top": "30mm", "bottom": "25.4mm", "left": "25.4mm", "right": "25.4mm"}
        )
        
        browser.close()
        return pdf_bytes
