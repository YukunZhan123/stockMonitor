from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get dictionary item by key for use in templates"""
    if dictionary and isinstance(dictionary, dict):
        return dictionary.get(key)
    return None