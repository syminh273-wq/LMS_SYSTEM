from .space_repository import SpaceRepository

Repository = SpaceRepository  # backward-compat

__all__ = [
    'SpaceRepository',
    'Repository',
]
