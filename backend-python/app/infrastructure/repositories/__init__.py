"""Concrete repository implementations.

Each repository:
  - Takes an AsyncSession in __init__
  - Translates between ORM models and domain entities
  - Exposes only the methods declared in the matching domain Port
"""
