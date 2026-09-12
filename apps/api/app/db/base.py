"""
Import all models here so Alembic can discover them via Base.metadata.
"""

from app.models.base import Base  # noqa: F401
from app.models.project import Project  # noqa: F401
