# from django.contrib import admin
# from .models import Article, Category, Tag, Comment
#
# admin.site.register(Article)
# admin.site.register(Category)
# admin.site.register(Tag)
# admin.site.register(Comment)
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Article, Category, Tag, Comment,
    UserProfile, Notification,
    DiscussionPost, DiscussionReply,
    DiscussionAttachment,Report, UserProfile
)
from django.contrib import admin, messages
from .models import Report, UserProfile, Article, Comment, DiscussionPost, DiscussionReply
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from django.contrib import admin
from .models import Report
from .models import AgentDraft, AgentSession, AgentToolLog

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reporter', 'report_type', 'target_id', 'reason', 'created_at', 'process_link')
    list_filter = ('report_type', 'created_at')

    def process_link(self, obj):
        url = reverse('admin_handle_report', args=[obj.id])
        return format_html('<a class="button" href="{}">处理</a>', url)

    process_link.short_description = '操作'



@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'created_at', 'views')
    search_fields = ('title', 'author__username')
    list_filter = ('category', 'created_at')
    ordering = ('-created_at',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'created_at')
    search_fields = ('user__username', 'article__title')
    list_filter = ('created_at',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'gender', 'signature', 'ban_status', 'ban_expiration', 'unban_link')
    list_filter = ('gender',)
    search_fields = ('user__username', 'nickname')

    def ban_status(self, obj):
        from django.utils import timezone
        return obj.ban_expiration and obj.ban_expiration > timezone.now()
    ban_status.boolean = True
    ban_status.short_description = "是否封禁中"

    def unban_link(self, obj):
        if obj.ban_expiration:
            url = reverse('admin_unban_user', args=[obj.user.id])
            return format_html('<a class="button" href="{}">解封</a>', url)
        return "-"
    unban_link.short_description = "操作"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('message',)

@admin.register(DiscussionPost)
class DiscussionPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'is_featured', 'is_pinned', 'status', 'created_at')
    list_filter = ('is_featured', 'is_pinned', 'status')
    actions = ['mark_as_featured', 'unmark_featured']
    search_fields = ('title', 'content', 'author__username')
    list_editable = ('is_pinned', 'is_featured', 'status')
    @admin.action(description='设为精华')
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"{updated} 个帖子已设为精华")

    @admin.action(description='取消精华')
    def unmark_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f"{updated} 个帖子已取消精华")

@admin.register(DiscussionReply)
class DiscussionReplyAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'created_at')
    search_fields = ('post__title', 'author__username', 'content')
    list_filter = ('created_at',)

@admin.register(DiscussionAttachment)
class DiscussionAttachmentAdmin(admin.ModelAdmin):
    list_display = ('post', 'file', 'uploaded_at')
    search_fields = ('post__title',)


@admin.register(AgentSession)
class AgentSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'created_at', 'updated_at')
    search_fields = ('user__username', 'title')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(AgentToolLog)
class AgentToolLogAdmin(admin.ModelAdmin):
    list_display = ('session', 'tool_name', 'success', 'duration_ms', 'created_at')
    list_filter = ('tool_name', 'success')
    readonly_fields = ('session', 'tool_name', 'arguments', 'result_preview', 'success', 'duration_ms', 'created_at')


@admin.register(AgentDraft)
class AgentDraftAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'category_name', 'status', 'updated_at')
    list_filter = ('status', 'category_name')
    search_fields = ('title', 'owner__username', 'content')
