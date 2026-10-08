import csv
from django.contrib import admin
from django.db.models import Count
from django.http import HttpResponse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import ContactMessage, SourceVisit


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone', 'subject', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'phone', 'subject', 'message')
    readonly_fields = ('first_name', 'last_name', 'email', 'phone', 'subject', 'message', 'ip_address', 'created_at')
    ordering = ('-created_at',)
    list_per_page = 25
    date_hierarchy = 'created_at'
    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} message(s) marked as read.')
    mark_as_read.short_description = 'Mark selected messages as read'

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'{updated} message(s) marked as unread.')
    mark_as_unread.short_description = 'Mark selected messages as unread'


@admin.register(SourceVisit)
class SourceVisitAdmin(admin.ModelAdmin):
    list_display = (
        'source_badge',
        'page_url_display',
        'ip_address',
        'referer_display',
        'user_agent_short',
        'created_at_formatted',
    )
    list_filter = ('source', 'created_at')
    search_fields = ('source', 'page_url', 'ip_address', 'user_agent', 'referer')
    readonly_fields = (
        'source',
        'get_formatted_name',
        'page_url',
        'ip_address',
        'referer',
        'user_agent',
        'created_at',
    )
    ordering = ('-created_at',)
    list_per_page = 50
    date_hierarchy = 'created_at'
    actions = ['export_as_csv']

    fieldsets = (
        ('Campaign & Source Information', {
            'fields': ('source', 'get_formatted_name', 'page_url'),
            'description': 'Tracking source parameter and landing page URL.'
        }),
        ('Visitor Technical Details', {
            'fields': ('ip_address', 'referer', 'user_agent'),
            'description': 'Visitor IP address, external HTTP referer, and browser headers.'
        }),
        ('Timestamp', {
            'fields': ('created_at',),
        }),
    )

    @admin.display(description="Source")
    def source_badge(self, obj):
        if not obj.source:
            return "-"
        formatted = ' '.join(word.capitalize() for word in obj.source.replace('-', '_').split('_') if word)
        return format_html(
            '<span style="background-color: #075da2; color: #ffffff; padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 12px; display: inline-block;">{}</span>'
            '<span style="color: #64748b; margin-left: 6px; font-family: monospace; font-size: 11px;">({})</span>',
            formatted,
            obj.source
        )

    @admin.display(description="Formatted Source Name")
    def get_formatted_name(self, obj):
        if not obj.source:
            return "-"
        return ' '.join(word.capitalize() for word in obj.source.replace('-', '_').split('_') if word)

    @admin.display(description="Page Visited")
    def page_url_display(self, obj):
        if not obj.page_url:
            return "-"
        return format_html('<code style="color: #0284c7; font-weight: 600;">{}</code>', obj.page_url)

    @admin.display(description="Referer")
    def referer_display(self, obj):
        if not obj.referer:
            return mark_safe('<span style="color: #94a3b8; font-style: italic;">Direct / Unknown</span>')
        truncated = obj.referer[:40] + ('...' if len(obj.referer) > 40 else '')
        return format_html('<a href="{}" target="_blank" rel="noopener noreferrer" style="color: #2563eb; text-decoration: underline;" title="{}">{}</a>', obj.referer, obj.referer, truncated)

    @admin.display(description="Device / Browser")
    def user_agent_short(self, obj):
        if not obj.user_agent:
            return "-"
        ua = obj.user_agent.lower()
        device = "Mobile" if any(kw in ua for kw in ["mobile", "android", "iphone"]) else "Desktop"
        browser = "Browser"
        if "chrome" in ua and "edg" not in ua and "opr" not in ua:
            browser = "Chrome"
        elif "safari" in ua and "chrome" not in ua:
            browser = "Safari"
        elif "firefox" in ua:
            browser = "Firefox"
        elif "edg" in ua:
            browser = "Edge"
        
        return format_html('<span style="font-weight: 600; color: #334155;">{}</span> <span style="color: #64748b; font-size: 11px;">({})</span>', browser, device)

    @admin.display(description="Visited At", ordering="created_at")
    def created_at_formatted(self, obj):
        return obj.created_at.strftime('%b %d, %Y %I:%M %p')

    @admin.action(description="Export Selected Source Visits to CSV")
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="source_visits_export.csv"'
        writer = csv.writer(response)

        writer.writerow(['ID', 'Source Key', 'Formatted Source Name', 'Page URL', 'IP Address', 'User Agent', 'Referer', 'Timestamp'])
        for obj in queryset:
            formatted = ' '.join(word.capitalize() for word in obj.source.replace('-', '_').split('_') if word) if obj.source else ''
            writer.writerow([
                obj.id,
                obj.source,
                formatted,
                obj.page_url,
                obj.ip_address,
                obj.user_agent,
                obj.referer,
                obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])

        self.message_user(request, f"Successfully exported {queryset.count()} source visit record(s) to CSV.")
        return response


