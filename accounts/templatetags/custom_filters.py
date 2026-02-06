# templatetags/custom_filters.py
from datetime import timedelta
import json
import re
from django import template
from django.core.serializers import serialize
from django.db.models.query import QuerySet
from django.utils.safestring import mark_safe
from django.utils.html import escape

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

@register.filter(name='highlight')
def highlight(text, search_term):
    """
    Highlight search terms in text
    """
    if not search_term or not text:
        return text
    
    # Convert to string if needed
    text = str(text)
    search_term = str(search_term)
    
    # Escape HTML in text
    text = escape(text)
    
    # Create regex pattern for case-insensitive search
    pattern = re.compile(re.escape(search_term), re.IGNORECASE)
    
    # Replace matches with highlighted span
    highlighted = pattern.sub(
        lambda match: f'<span class="highlight">{match.group()}</span>',
        text
    )
    
    return mark_safe(highlighted)

@register.filter
def month_name(value):
    """Convert month number to month name"""
    import calendar
    try:
        return calendar.month_name[int(value)]
    except (ValueError, TypeError, IndexError):
        return value

@register.filter
def split(value, delimiter=' '):
    """Split a string by delimiter"""
    return value.split(delimiter)


@register.filter(name='query_transform')
def query_transform(request, **kwargs):
    """
    Add or replace parameters in query string
    """
    updated = request.GET.copy()
    for key, value in kwargs.items():
        if value:
            updated[key] = value
        else:
            updated.pop(key, None)
    
    return updated.urlencode()


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Get item from dictionary
    """
    return dictionary.get(key)


@register.filter(name='format_phone')
def format_phone(phone):
    """
    Format phone number for display
    """
    if not phone:
        return ''
    
    phone = str(phone).replace(' ', '')
    if len(phone) == 9:
        return f'{phone[:3]} {phone[3:6]} {phone[6:]}'
    return phone


@register.filter(name='truncate_chars')
def truncate_chars(value, max_length):
    """
    Truncate text to specified length
    """
    if len(value) <= max_length:
        return value
    return f"{value[:max_length]}..."


@register.filter(name='add_class')
def add_class(field, css_class):
    """
    Add CSS class to form field
    """
    return field.as_widget(attrs={"class": css_class})
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


@register.filter
def add_days(value, days):
    """Add days to a date"""
    try:
        return value + timedelta(days=int(days))
    except (ValueError, TypeError):
        return value        