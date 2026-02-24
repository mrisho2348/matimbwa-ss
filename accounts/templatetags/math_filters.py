from django import template

register = template.Library()

@register.filter
def div(value, arg):
    """
    Divide the value by the argument
    Usage: {{ value|div:arg }}
    """
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0