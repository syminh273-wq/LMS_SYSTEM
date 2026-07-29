"""String case helpers used by management commands and scaffolding.

Covers the 3 conversions that appear throughout the LMS codebase:
    - to_snake_case           → file/module/variable names
    - to_pascal_case          → class names
    - to_plural_snake_case    → Cassandra table names and URL path segments
"""
import re


def to_snake_case(name: str) -> str:
    """Convert any case (Pascal / camel / kebab / spaces) → snake_case.

    Examples:
        'Classroom'      -> 'classroom'
        'ClassroomEvent' -> 'classroom_event'
        'classroomEvent' -> 'classroom_event'
        'classroom-event'-> 'classroom_event'
        'ClassRoom'      -> 'class_room'
    """
    if not name:
        return name

    s = name.strip()

    # kebab-case / spaces → underscores
    s = re.sub(r'[\s\-]+', '_', s)

    # camelCase boundary: lower(digit/upper) or upper(lower) preceded by upper
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)

    # collapse runs of uppercase into single underscore (ClassRoom -> Class_Room)
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', s)

    s = s.lower()
    s = re.sub(r'_+', '_', s).strip('_')
    return s


def to_pascal_case(name: str) -> str:
    """Convert any case → PascalCase.

    Examples:
        'classroom'      -> 'Classroom'
        'classroom_event'-> 'ClassroomEvent'
        'ClassroomEvent' -> 'ClassroomEvent'
        'classroom-event'-> 'ClassroomEvent'
    """
    if not name:
        return name

    s = to_snake_case(name)
    return ''.join(part.capitalize() for part in s.split('_') if part)


def to_plural_snake_case(name: str) -> str:
    """Snake_case + naive English pluralization.

    Examples:
        'classroom'      -> 'classrooms'
        'category'       -> 'categories'
        'box'            -> 'boxes'
        'quiz'           -> 'quizzes'
        'person'         -> 'people'
    """
    s = to_snake_case(name)
    if not s:
        return s

    irregular = {
        'person': 'people',
        'child': 'children',
        'man': 'men',
        'woman': 'women',
        'mouse': 'mice',
        'data': 'data',
        'quiz': 'quizzes',
        'matrix': 'matrices',
        'index': 'indices',
        'vertex': 'vertices',
    }
    if s in irregular:
        return irregular[s]

    if s.endswith(('ss', 'zz', 'xx', 'ch', 'sh')):
        return s + 'es'
    if s.endswith(('s', 'x', 'z')):
        return s + 'es'
    if s.endswith('y') and len(s) > 1 and s[-2] not in 'aeiou':
        return s[:-1] + 'ies'
    if s.endswith('f') and not s.endswith('ff'):
        return s[:-1] + 'ves'
    if s.endswith('fe'):
        return s[:-2] + 'ves'
    return s + 's'
