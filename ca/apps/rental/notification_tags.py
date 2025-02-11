# templatetags/notification_tags.py
from django import template
from models import Notification

register = template.Library()

@register.simple_tag
def unread_notifications_count(user):
    return Notification.objects.filter(user=user, is_read=False).count()

@register.simple_tag
def unread_admin_notifications_count(admin):
    return Notification.objects.filter(admin=admin, is_read=False).count()