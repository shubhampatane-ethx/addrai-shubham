"""
Celery Tasks Package
REFACTORED: Supplier → Entity
Import all tasks here so they can be discovered by Celery
"""
from backend.app.tasks.validation import validate_entities_task, test_task

__all__ = ['validate_entities_task', 'test_task']
