"""
Django's 'humanize' tags don't include methods for humanizing
durations of time (only timestamps).
These methods do that.
"""

from django import template

register = template.Library()


@register.filter
def humanize_minutes(minutes):
    # eesh this is messy with a lot of special cases
    if minutes < 1:
        return "less than a minute"
    if minutes < 2:
        return "1 minute"
    if minutes < 45:
        return f"{minutes:0.0f} minutes"
    halves = (minutes * 2) // 60
    if halves == 1:
        return "half an hour"
    if halves == 2:
        return "1 hour"
    if halves % 2:
        return f"{halves / 2:0.1f} hours"
    return f"{halves / 2:0.0f} hours"
