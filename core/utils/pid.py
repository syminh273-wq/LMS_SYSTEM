"""Public-ID generator shared by Consumer, Space, Course, Classroom.

PID format: ``LMS{YY}{8-digit-random}`` → 10 chars, 8^10 = 100M ids/year.
Cassandra secondary index is NOT unique, so we must retry on collision.
"""
import random
import string
from datetime import datetime

_DIGITS = string.digits
_FORMAT = 'LMS{yy}{rand}'


def generate_pid() -> str:
    year_suffix = datetime.now().strftime('%y')
    digits = ''.join(random.choices(_DIGITS, k=8))
    return _FORMAT.format(yy=year_suffix, rand=digits)


def generate_unique_pid(exists_fn, max_attempts: int = 16) -> str:
    """Generate a PID and verify uniqueness via ``exists_fn(pid)``.

    Args:
        exists_fn: callable ``(pid: str) -> bool`` returning True if pid already used.
        max_attempts: cap retries to avoid infinite loop on degenerate RNG.

    Returns:
        A PID guaranteed not to collide with any existing row.
    """
    for _ in range(max_attempts):
        pid = generate_pid()
        if not exists_fn(pid):
            return pid
    raise RuntimeError(
        f'Could not generate unique PID after {max_attempts} attempts. '
        f'Increase entropy (more digits) or check the exists_fn.'
    )
