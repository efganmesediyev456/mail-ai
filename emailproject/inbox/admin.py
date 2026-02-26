from django.contrib import admin
from .models import IncomingEmail


@admin.register(IncomingEmail)
class IncomingEmailAdmin(admin.ModelAdmin):
    list_display = ('subject', 'sender', 'department', 'is_replied', 'received_at')
    list_filter = ('department', 'is_replied')
    search_fields = ('subject', 'sender', 'body')
