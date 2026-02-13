# your_app/templatetags/analysis_filters.py
from django import template
import math

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter
def split(value, delimiter=','):
    """Split string by delimiter"""
    if isinstance(value, str):
        return value.split(delimiter)
    return []

@register.filter
def filter_by(queryset, attribute):
    """Filter a list of dictionaries by an attribute"""
    if not queryset:
        return []
    return [item for item in queryset if item.get(attribute)]

@register.filter
def filter_value(queryset, value):
    """Filter a list of dictionaries by value"""
    if not queryset:
        return []
    return [item for item in queryset if str(item.get('value', '')).lower() == str(value).lower()]

@register.filter
def filter_rank_range(queryset, start, end):
    """Filter students by rank range"""
    try:
        start = int(start)
        end = int(end)
        return [student for student in queryset if start <= int(student.get('rank', 0)) <= end]
    except (ValueError, TypeError):
        return queryset

@register.filter
def increment(value):
    """Increment a value (used in loops)"""
    try:
        return int(value) + 1
    except (ValueError, TypeError):
        return 0

@register.filter
def dictsort(queryset, key):
    """Sort a list of dictionaries by key"""
    try:
        if isinstance(queryset, dict):
            return sorted(queryset.items(), key=lambda x: x[1])
        return sorted(queryset, key=lambda x: x.get(key, 0))
    except (AttributeError, TypeError):
        return queryset

@register.simple_tag
def get_percentage(value, total):
    """Calculate percentage"""
    try:
        value = float(value)
        total = float(total)
        if total == 0:
            return 0
        return (value / total) * 100
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """Divide value by argument"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0
    
@register.filter
def set_item(dictionary, key, value):
    """Set item in dictionary (for use in templates with with tag)"""
    if dictionary is None:
        dictionary = {}
    dictionary[key] = value
    return dictionary

@register.filter
def sub(value, arg):
    """Subtract argument from value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def add(value, arg):
    """Add argument to value"""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def mul(value, arg):
    """Multiply value by argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def widthratio(value, max_value, factor):
    """Calculate width ratio for charts"""
    try:
        value = float(value)
        max_value = float(max_value)
        if max_value == 0:
            return 0
        ratio = (value / max_value) * float(factor)
        return int(ratio)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def slice_string(value, arg):
    """Slice a string"""
    try:
        if ':' in arg:
            start, end = map(int, arg.split(':'))
            return value[start:end]
        else:
            arg = int(arg)
            return value[:arg]
    except (ValueError, TypeError, AttributeError):
        return value

@register.filter
def truncatechars(value, arg):
    """Truncate string to specified number of characters"""
    try:
        arg = int(arg)
        value = str(value)
        if len(value) > arg:
            return value[:arg-3] + '...'
        return value
    except (ValueError, TypeError):
        return value

@register.simple_tag
def get_average(queryset, field):
    """Calculate average of a field in queryset"""
    try:
        total = 0
        count = 0
        for item in queryset:
            value = item.get(field)
            if value:
                total += float(value)
                count += 1
        return total / count if count > 0 else 0
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def cos(degrees):
    """Calculate cosine of degrees"""
    try:
        import math
        radians = math.radians(float(degrees))
        return math.cos(radians)
    except (ValueError, TypeError, ImportError):
        return 0

@register.filter
def sin(degrees):
    """Calculate sine of degrees"""
    try:
        import math
        radians = math.radians(float(degrees))
        return math.sin(radians)
    except (ValueError, TypeError, ImportError):
        return 0

@register.simple_tag
def css_color(index):
    """Return CSS color variable based on index"""
    colors = [
        '#dc3545', '#fd7e14', '#ffc107', '#17a2b8', '#28a745',
        '#007bff', '#e83e8c', '#6c757d', '#6f42c1', '#20c997'
    ]
    try:
        idx = int(index) % len(colors)
        return colors[idx]
    except (ValueError, TypeError):
        return colors[0]

@register.filter
def get_range(value):
    """Create a range for template loops"""
    try:
        return range(int(value))
    except (ValueError, TypeError):
        return range(0)

@register.filter
def multiply(value, arg):
    """Multiply value by argument (alias for mul)"""
    return mul(value, arg)

@register.filter
def get_percentile_rank(queryset, index):
    """Get student by percentile rank"""
    try:
        index = int(index)
        if 0 <= index < len(queryset):
            return queryset[index]
        return None
    except (ValueError, TypeError, IndexError):
        return None

@register.filter
def calculate_band(student_rank, total_students):
    """Calculate performance band based on rank percentile"""
    try:
        percentile = (int(student_rank) / int(total_students)) * 100
        if percentile <= 10:
            return 'band-1'
        elif percentile <= 30:
            return 'band-2'
        elif percentile <= 70:
            return 'band-3'
        elif percentile <= 90:
            return 'band-4'
        else:
            return 'band-5'
    except (ValueError, TypeError, ZeroDivisionError):
        return 'band-3'

@register.filter
def slice_list(queryset, arg):
    """Slice a list by start:end or just limit"""
    try:
        if ':' in arg:
            start, end = map(int, arg.split(':'))
            return queryset[start:end]
        else:
            return queryset[:int(arg)]
    except (ValueError, TypeError, IndexError):
        return queryset

@register.filter
def get_first(queryset):
    """Get first item in queryset"""
    try:
        if queryset and len(queryset) > 0:
            return queryset[0]
    except (TypeError, IndexError):
        pass
    return None

@register.filter
def get_last(queryset):
    """Get last item in queryset"""
    try:
        if queryset and len(queryset) > 0:
            return queryset[-1]
    except (TypeError, IndexError):
        pass
    return None

@register.filter
def get_at_index(queryset, index):
    """Get item at specific index"""
    try:
        index = int(index)
        if 0 <= index < len(queryset):
            return queryset[index]
    except (ValueError, TypeError, IndexError):
        pass
    return None

@register.filter
def default_if_none(value, default):
    """Return default if value is None"""
    return default if value is None else value
