import uuid

from django.db import models
from django.contrib.auth.models import User
from ckeditor.fields import RichTextField
from django.db import models

#AI解析
class ArticleAnalysis(models.Model):
    article = models.OneToOneField('Article', on_delete=models.CASCADE)
    analysis_content = models.TextField()  # 存储AI解析内容
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"解析 - {self.article.title}"

class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_user = models.BooleanField(default=True)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({'User' if self.is_user else 'Bot'}): {self.message[:30]}"

#举报
class Report(models.Model):
    REPORT_TYPES = [
        ('article', '文章'),
        ('user', '用户'),
        ('comment', '评论'),
        ('post', '讨论帖'),
        ('reply', '讨论回复'),
    ]

    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    target_id = models.PositiveIntegerField()
    reason = models.CharField(max_length=255)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.report_type} #{self.target_id} by {self.reporter}"


#讨论组
class DiscussionPost(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    tags = models.CharField(max_length=100, blank=True)  # 可选的逗号分隔标签
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)
    collectors = models.ManyToManyField(User, related_name='collected_posts', blank=True)
    views = models.PositiveIntegerField(default=0)
    is_pinned = models.BooleanField(default=False, verbose_name="置顶")
    is_featured = models.BooleanField(default=False, verbose_name="精华")
    status = models.CharField(
        max_length=20,
        choices=[('open', '开放'), ('closed', '关闭')],
        default='open',
        verbose_name="状态"
    )
    def __str__(self):
        return self.title


class DiscussionReply(models.Model):
    post = models.ForeignKey('DiscussionPost', on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"回复 by {self.author.username}"


class DiscussionAttachment(models.Model):
    post = models.ForeignKey('DiscussionPost', on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='forum/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

#游戏得分
class GameScore(models.Model):
    GAME_CHOICES = [
        ('snake', '贪吃蛇'),
        ('2048', '2048'),
        ('tetris', '俄罗斯方块')
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.CharField(max_length=20, choices=GAME_CHOICES)
    score = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-score', 'created_at']

    def __str__(self):
        return f"{self.user.username} - {self.game}: {self.score}"

#留言板
class Message(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class UserProfile(models.Model):
    GENDER_CHOICES = (
        ('M', '男'),
        ('F', '女'),
        ('O', '保密'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    birthday = models.DateField(null=True, blank=True, verbose_name='生日')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, verbose_name='性别')
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.png', blank=True, verbose_name='头像')
    signature = models.CharField(max_length=100, blank=True, verbose_name='个性签名')
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_banned = models.BooleanField(default=False)
    ban_expiration = models.DateTimeField(null=True, blank=True)
    ban_reason = models.CharField(max_length=255, blank=True, null=True)
    def __str__(self):
        return f"{self.user.username} 的资料"


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name




class Article(models.Model):
    title = models.CharField(max_length=200)
    # content = models.TextField()
    content = RichTextField()  # 富文本
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views = models.IntegerField(default=0)
    collectors = models.ManyToManyField(User, related_name='collections', blank=True)
    likes = models.ManyToManyField(User, related_name='liked_articles', blank=True)#点赞
    def __str__(self):
        return self.title



class ArticleAttachment(models.Model):
    article = models.ForeignKey('Article', on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name

class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')  # 回复或追评
    is_followup = models.BooleanField(default=False)  # 是否是追评（True 为追评）
    likes = models.ManyToManyField(User, related_name='liked_comments', blank=True)#点赞
    def __str__(self):
        return f"{self.user.username} 评论文章《{self.article.title}》"

class Notification(models.Model):
    NOTIFY_TYPES = [
        ('like', '点赞'),
        ('collect', '收藏'),
        ('reply', '回复'),
        ('follow', '关注'),
        ('feature', '设为精华'),
        ('pin', '设为置顶'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)  # 被通知的人
    message = models.CharField(max_length=255)
    link = models.URLField(max_length=1024, blank=True)
    type = models.CharField(max_length=20, choices=NOTIFY_TYPES, default='reply')

    preview = models.TextField(blank=True, null=True)  # 可选摘要
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"通知：{self.message} 给 {self.user.username}"


class AgentSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='agent_sessions')
    title = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title or f'Agent session {self.id}'


class AgentMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    session = models.ForeignKey(
        AgentSession,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class AgentToolLog(models.Model):
    session = models.ForeignKey(
        AgentSession,
        on_delete=models.CASCADE,
        related_name='tool_logs',
    )
    tool_name = models.CharField(max_length=80)
    arguments = models.JSONField(default=dict)
    result_preview = models.TextField(blank=True)
    success = models.BooleanField(default=True)
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class AgentDraft(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='agent_drafts')
    session = models.ForeignKey(
        AgentSession,
        on_delete=models.SET_NULL,
        related_name='drafts',
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    category_name = models.CharField(max_length=100, blank=True)
    tags = models.JSONField(default=list, blank=True)
    source_article_ids = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title

