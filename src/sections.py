"""Section splitting that preserves repeated headings and inline content."""
from src.text_preprocessor import normalize_section_heading


def split_sections(text, aliases, initial=None):
    sections = {}
    current = initial
    for line in text.splitlines():
        line = line.strip()
        label, separator, content = line.partition(":")
        detected = aliases.get(normalize_section_heading(label if separator else line))
        if detected:
            current = detected
            sections.setdefault(current, [])
            if separator and content.strip():
                sections[current].append(content.strip())
        elif current is not None:
            sections.setdefault(current, []).append(line)
    return sections
