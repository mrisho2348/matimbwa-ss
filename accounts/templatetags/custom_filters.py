# templatetags/custom_filters.py
import json
from django import template
from django.core.serializers import serialize
from django.db.models.query import QuerySet

register = template.Library()

@register.filter
def split_string(value, delimiter=','):
    """
    Split a string by delimiter and return a list of trimmed items.
    """
    if not value:
        return []
    return [item.strip() for item in str(value).split(delimiter) if item.strip()]

@register.filter
def contains_id(value, item_id):
    """
    Check if a list or string contains a specific ID.
    """
    if not value:
        return False
    if isinstance(value, str):
        return str(item_id) in split_string(value)
    elif hasattr(value, '__iter__'):
        return any(str(item_id) == str(x) for x in value)
    return False


@register.filter(name='json_serialize')
def json_serialize(value):
    """Serialize Django objects to JSON"""
    if isinstance(value, QuerySet):
        # Serialize QuerySet
        data = list(value.values('id', 'stream_letter', 'class_level_id'))
        return json.dumps(data)
    elif hasattr(value, '__dict__'):
        # Serialize model instance
        return json.dumps(value.__dict__)
    else:
        return json.dumps(list(value))