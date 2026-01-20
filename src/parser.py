"""MDX file parser for extracting Tailwind CSS documentation content."""

import re
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional
import frontmatter

logger = logging.getLogger(__name__)

# Regex pattern to extract utility classes from class attributes
CLASS_PATTERN = re.compile(r'class(?:Name)?="([^"]+)"')

# Regex pattern to extract code blocks
CODE_BLOCK_PATTERN = re.compile(r'```(?:\w+)?\n(.*?)```', re.DOTALL)


def parse_mdx_file(file_path: Path) -> Optional[Dict]:
    """
    Parse an MDX file and extract metadata, content, and utility classes.

    Args:
        file_path: Path to the MDX file

    Returns:
        Dict containing parsed data or None if parsing fails
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)

        # Extract frontmatter metadata
        title = post.get('title', '')
        description = post.get('description', '')

        # Get content without frontmatter
        content = post.content

        # Extract utility classes from code examples
        utility_classes = extract_utility_classes(content)

        # Extract code examples
        code_examples = extract_code_examples(content)

        # Infer section from file path
        section = infer_section(file_path)

        # Get relative file path for URL construction
        relative_path = str(file_path)

        return {
            'filepath': relative_path,
            'title': title,
            'description': description,
            'content': content,
            'section': section,
            'utility_classes': list(utility_classes),
            'code_examples': code_examples
        }

    except Exception as e:
        logger.error(f"Failed to parse {file_path}: {e}")
        return None


def extract_utility_classes(content: str) -> Set[str]:
    """
    Extract Tailwind CSS utility classes from code examples in content.

    Args:
        content: MDX file content

    Returns:
        Set of utility class names
    """
    all_classes = set()

    # Find all class and className attributes
    matches = CLASS_PATTERN.findall(content)

    for class_attr in matches:
        # Split on whitespace to get individual classes
        classes = class_attr.split()
        for cls in classes:
            # Filter out non-Tailwind classes (basic heuristic)
            # Keep classes that look like Tailwind utilities
            if cls and not cls.startswith('{') and not cls.startswith('...'):
                all_classes.add(cls)

    return all_classes


def extract_code_examples(content: str) -> List[str]:
    """
    Extract code blocks from MDX content.

    Args:
        content: MDX file content

    Returns:
        List of code example strings
    """
    code_blocks = []

    # Find all code blocks
    matches = CODE_BLOCK_PATTERN.findall(content)

    for code in matches:
        # Clean up the code and only keep blocks that contain class attributes
        # (likely to be HTML/JSX examples)
        if 'class' in code.lower() and len(code.strip()) > 0:
            code_blocks.append(code.strip())

    return code_blocks


def infer_section(file_path: Path) -> str:
    """
    Infer the documentation section from the file path structure.

    Args:
        file_path: Path to the MDX file

    Returns:
        Section name (e.g., "Layout", "Typography", etc.)
    """
    # Get the parent directory name as the section
    # Example: src/pages/docs/flex-direction.mdx -> "docs"
    # Example: src/pages/docs/typography/font-size.mdx -> "typography"

    parts = file_path.parts
    try:
        # Find the 'docs' index
        docs_index = parts.index('docs')
        # If there's a subdirectory after 'docs', use that as section
        if docs_index + 1 < len(parts) - 1:
            section = parts[docs_index + 1]
            # Capitalize and replace hyphens with spaces
            return section.replace('-', ' ').title()
        else:
            # File is directly under docs/
            return 'Core'
    except (ValueError, IndexError):
        return 'General'


def get_url_from_filepath(filepath: str, repo_path: str) -> str:
    """
    Convert file path to Tailwind CSS documentation URL.

    Args:
        filepath: Path to the MDX file
        repo_path: Root path of the repository

    Returns:
        URL to the documentation page
    """
    file_path = Path(filepath)

    # Get relative path from docs directory
    try:
        # Find the part after 'docs/'
        parts = file_path.parts
        docs_index = parts.index('docs')
        path_parts = parts[docs_index + 1:]

        # Remove .mdx extension
        if path_parts:
            last_part = path_parts[-1].replace('.mdx', '')
            url_path = '/'.join(path_parts[:-1] + (last_part,))
        else:
            url_path = ''

        return f"https://tailwindcss.com/docs/{url_path}" if url_path else "https://tailwindcss.com/docs"

    except (ValueError, IndexError):
        return "https://tailwindcss.com/docs"
