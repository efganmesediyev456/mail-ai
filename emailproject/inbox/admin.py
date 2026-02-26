from django.contrib import admin
from .models import IncomingEmail, CompanyInfo


@admin.register(CompanyInfo)
class CompanyInfoAdmin(admin.ModelAdmin):
    list_display = ('__str__',)

    def has_add_permission(self, request):
        if CompanyInfo.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(IncomingEmail)
class IncomingEmailAdmin(admin.ModelAdmin):
    list_display = ('subject', 'sender', 'department', 'is_replied', 'received_at')
    list_filter = ('department', 'is_replied')
    search_fields = ('subject', 'sender', 'body')
