# templatetags/hostel_extras.py
from django import template

register = template.Library()

@register.filter
def sum_beds(rooms):
    """Sum the number of beds in a queryset of rooms"""
    total = 0
    for room in rooms:
        total += room.beds.count()
    return total