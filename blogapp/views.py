
from django.core.cache import cache
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.clickjacking import xframe_options_exempt

from .forms import CustomUserCreationForm, UserEditForm, ProfileEditForm, DiscussionReplyForm, \
    DiscussionPostForm  # 替代默认的 UserCreationForm
from django.http import HttpResponseForbidden, Http404, HttpResponseBadRequest
from .models import UserProfile, DiscussionAttachment, Report
from django.contrib.auth.models import User
from .models import  Comment
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from .models import Message, Notification
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .forms import ArticleForm
from .models import Article, Category, Tag, ArticleAttachment
from .models import DiscussionPost, DiscussionReply
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from .models import DiscussionPost
from .forms import ReportForm

# 创建通知的通用函数，用于评论、回复、点赞等场景
def create_notification(user, message, link='', type='reply', preview=None):
    if user:  # 防止为匿名用户创建通知（Django默认的匿名用户为 AnonymousUser）
        Notification.objects.create(
            user=user,  # 通知目标用户
            message=message,  # 通知正文内容（例如“张三评论了你的文章”）
            link=link,  # 通知跳转链接（通常是文章或讨论帖地址）
            type=type,  # 通知类型，例如 reply/comment/like/feature/pin 等
            preview=preview or ''  # 内容预览（可为空）
        )


@login_required  # 确保只有登录用户才可访问此视图
def delete_comment(request, comment_id):
    # 尝试从数据库获取指定评论对象，不存在则返回 404 页面
    comment = get_object_or_404(Comment, id=comment_id)

    # 判断评论是否为当前用户所写，防止非法删除
    if comment.user != request.user:
        return HttpResponseForbidden("你没有权限删除这条评论")

    # 获取该评论所属的文章 ID，用于删除后跳转回文章详情页
    article_id = comment.article.id

    # 删除该评论对象
    comment.delete()

    # 重定向回文章详情页
    return redirect('article_detail', article_id=article_id)


# 帖子的创建和编辑
@login_required

def article_create_or_edit(request, article_id=None):
    #编辑模式
    if article_id:
        article = get_object_or_404(Article, pk=article_id)
        mode = 'edit'
    #创建模式
    else:
        article = None
        mode = 'create'

    if request.method == 'POST':
        form = ArticleForm(request.POST) # 将请求中的表单数据传入表单类进行校验
        if form.is_valid():
            if article is None:
                article = form.save(commit=False)
                article.author = request.user
            else:
                article.title = form.cleaned_data['title']
                article.content = form.cleaned_data['content']
            article.save()

            # 分类处理
            category_new = request.POST.get('category_new', '').strip()  # 自定义分类字段
            category_select = request.POST.get('category_select', '').strip()  # 下拉框选择分类字段
            category_name = category_new or category_select or None  # 优先使用新建值，其次是选择值
            if category_name:
                # 获取或创建分类对象（确保分类存在）
                category, _ = Category.objects.get_or_create(name=category_name)
                article.category = category  # 设置分类
                article.save()  # 再次保存文章对象


            # 标签处理
            tags_str = request.POST.get('tags', '')  # 获取标签字段内容
            tag_names = [t.strip() for t in tags_str.replace('，', ',').split(',') if t.strip()]
            # 替换中文逗号并清洗标签列表
            tags = [Tag.objects.get_or_create(name=name)[0] for name in tag_names]  # 批量获取/创建标签对象
            article.tags.set(tags)  # 设置文章的标签列表


            # 附件处理
            for file in request.FILES.getlist('file'):  # 遍历上传文件
                ArticleAttachment.objects.create(article=article, file=file)  # 关联文章保存附件
            return redirect('article_detail', article_id=article.id)# 跳转到文章详情页
    else:
        # 默认填充值
        initial = {}
        if article:
            initial = {
                'title': article.title,
                'content': article.content
            }
        form = ArticleForm(initial=initial)

    categories = Category.objects.all()
    tags = Tag.objects.all()

    return render(request, 'blogapp/article_form.html', {
        'form': form,  # 表单对象
        'article': article,  # 当前文章对象（可能为 None）
        'categories': categories,  # 分类选项
        'tags': tags,  # 标签选项
        'mode': mode,  # 当前模式：create 或 edit
    })



#注册
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            # 保存扩展信息
            gender = form.cleaned_data['gender']
            birthday = form.cleaned_data['birthday']
            default_img='avatars/default_avatar.png'
            avatar = form.cleaned_data['avatar'] if 'avatar' in request.FILES else default_img

            UserProfile.objects.create(
                user=user,
                gender=gender,
                birthday=birthday,
                avatar=avatar
            )
            login(request, user)
            return redirect('article_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'blogapp/register.html', {'form': form})



from .models import Article, Category
from django.db.models import Count
from django.utils.timezone import now
import requests

#帖子列表
def article_list(request):
    articles = Article.objects.all().order_by('-created_at')
    total_articles = articles.count()
    categories = Category.objects.annotate(article_count=Count('article'))
    total_views = Article.objects.aggregate(total_views=Count('views'))['total_views'] or 0
    recent_articles = articles.order_by('-updated_at')[:5]

    return render(request, 'blogapp/article_list.html', {
        'articles': articles,  # 文章列表
        'total_articles': total_articles,  # 总数量
        'categories': categories,  # 分类信息 + 每个分类的文章数
        'total_views': total_views,  # 所有文章的浏览总数
        'recent_articles': recent_articles,  # 最近更新文章
    })


#获取自动天气和ip
def fetch_weather_auto_ip():
    url = 'https://api.seniverse.com/v3/weather/now.json'
    params = {
        'location': 'ip',
        'language': 'zh-Hans',
        'unit': 'c',
        'key': settings.SENIVERSE_API_KEY,
    }

    try:
        print("【请求天气参数】：", params)
        res = requests.get(url, params=params, timeout=5)
        res.raise_for_status()
        data = res.json()
        now = data['results'][0]['now']
        city = data['results'][0]['location']['name']
        return {
            'city': city,
            'text': now['text'],
            'temp': now['temperature'],
            'icon': now['code']
        }
    except Exception as e:
        print("【天气接口请求失败】：", e)
        return {'city': '未知', 'text': '未知', 'temp': '--', 'icon': '99'}
#天气自动显示
def weather_auto_view(request):
    weather = fetch_weather_auto_ip()
    return JsonResponse(weather)


import time
import hmac
import hashlib
import base64
import urllib.parse



#帖子内容
def article_detail(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    comments = Comment.objects.filter(article=article, parent=None).order_by('-created_at')  # 顶级评论
    article.views += 1
    article.save()

    if request.method == 'POST':
        if request.user.is_authenticated:  # 只有登录用户可评论
            content = request.POST.get('content')  # 评论正文
            parent_id = request.POST.get('parent_id')  # 若为回复，则存在父评论 ID
            is_followup = request.POST.get('is_followup') == '1'  # 是否追评标志


            if content.strip():  # 评论内容非空
                parent = Comment.objects.get(id=parent_id) if parent_id else None
                # 获取父评论对象（如果有）

                Comment.objects.create(
                    article=article,
                    user=request.user,
                    content=content,
                    parent=parent,
                    is_followup=is_followup
                )
                if article.author != request.user:
                    create_notification(
                        user=article.author,
                        message=f"{request.user.username} 评论了你的文章《{article.title}》",
                        link=reverse('article_detail', args=[article.id]),
                        type='comment',
                        preview=content[:50]
                    )

                # 评论创建后（Comment.objects.create...之后）执行：
                if parent and parent.user != request.user:
                    create_notification(
                        user=parent.user,
                        message=f"{request.user.username} 回复你的帖子《{article.title}》",
                        link=reverse('article_detail', args=[article.id]),
                        type='reply',
                        preview=article.content[:50]
                    )

                return redirect('article_detail', article_id=article.id)
            else:
                messages.error(request, "评论内容不能为空")

    return render(request, 'blogapp/article_detail.html', {
        'article': article,
        'comments': comments,
    })

#文章分类
def articles_by_category(request, category_id):
    articles = Article.objects.filter(category_id=category_id).order_by('-created_at')
    return render(request, 'blogapp/article_list.html', {
        'articles': articles,
        'filter_title': f"分类：{Category.objects.get(id=category_id).name}",
    })
#文章标签
def articles_by_tag(request, tag_id):
    articles = Article.objects.filter(tags__id=tag_id).order_by('-created_at')
    return render(request, 'blogapp/article_list.html', {
        'articles': articles,
        'filter_title': f"标签：{Tag.objects.get(id=tag_id).name}",
    })

#消息通知
@login_required
def notification_list(request):
    notif_type = request.GET.get('type')
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    if notif_type:
        notifications = notifications.filter(type=notif_type)

    return render(request, 'blogapp/notification_list.html', {
        'notifications': notifications,
        'notif_type': notif_type,
    })

@require_POST # 只允许 POST 请求（提高安全性）
@login_required
#单一删除
def delete_notification(request, notification_id):
    Notification.objects.filter(id=notification_id, user=request.user).delete()
    return JsonResponse({'status': 'ok'})

@require_POST
@login_required
#一键已读
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'ok'})

@require_POST
@login_required
#一键删除
def delete_all_notifications(request):
    Notification.objects.filter(user=request.user).delete()
    return JsonResponse({'status': 'ok'})

@login_required
#已读
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
    if request.method == 'POST':
        notification.is_read = True
        notification.save()
    return redirect('notification_list')

@login_required
#删除通知
def delete_notification(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
    if request.method == 'POST':
        notification.delete()
    return redirect('notification_list')


#修改个人信息
@login_required
def edit_profile(request):
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        user_form = UserEditForm(request.POST, instance=user)
        profile_form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, '信息修改成功')
            return redirect('article_list')
    else:
        user_form = UserEditForm(instance=user)
        profile_form = ProfileEditForm(instance=profile)

    return render(request, 'blogapp/edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })

#收藏功能
@login_required
def toggle_collect(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    if request.user in article.collectors.all():
        article.collectors.remove(request.user)
        return JsonResponse({'collected': False})
    else:
        article.collectors.add(request.user)
        return JsonResponse({'collected': True})

#个人主页
def user_profile(request, username):
    user_obj = get_object_or_404(User, username=username)
    profile, _ = UserProfile.objects.get_or_create(user=user_obj)
    discussion_posts = DiscussionPost.objects.filter(author=user_obj)
    articles = Article.objects.filter(author=user_obj)
    collections = user_obj.collections.all()
    liked_articles = user_obj.liked_articles.all()
    comments = Comment.objects.filter(user=user_obj).order_by('-created_at')

    is_following = False
    if request.user.is_authenticated and request.user != user_obj:
        current_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        is_following = profile in current_profile.following.all()

    return render(request, 'blogapp/user_profile.html', {
        'user_obj': user_obj,
        'articles': articles,
        'collections': collections,
        'liked_articles': liked_articles,
        'comments': comments,
        'is_following': is_following,
        'discussion_posts': discussion_posts,
    })


#个人收藏
@login_required
def my_collections(request):
    articles = request.user.collections.all()
    return render(request, 'blogapp/my_collections.html', {'articles': articles})

#关注
@login_required
def toggle_follow(request, username):
    target_user = get_object_or_404(User, username=username)
    target_profile, _ = UserProfile.objects.get_or_create(user=target_user)
    current_profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if current_profile == target_profile:
        return JsonResponse({'error': '不能关注自己'}, status=400)

    is_following = target_profile in current_profile.following.all()

    if is_following:
        current_profile.following.remove(target_profile)
    else:
        current_profile.following.add(target_profile)

        # 创建通知
        Notification.objects.create(
            user=target_user,
            message=f"{request.user.username} 关注了你",
            link=f"/user/{request.user.username}/"
        )

    # ✅ 返回实际状态
    return JsonResponse({'followed': not is_following})



#粉丝列表
def followers_list(request, username):
    user_obj = get_object_or_404(User, username=username)
    profile, _ = UserProfile.objects.get_or_create(user=user_obj)
    followers = profile.followers.all()  # 关注该用户的所有人
    return render(request, 'blogapp/followers_list.html', {
        'user_obj': user_obj,
        'followers': followers
    })
#关注列表
def following_list(request, username):
    user_obj = get_object_or_404(User, username=username)
    profile, _ = UserProfile.objects.get_or_create(user=user_obj)
    following = profile.following.all()  # 该用户关注的所有人
    return render(request, 'blogapp/following_list.html', {
        'user_obj': user_obj,
        'following': following
    })


#帖子点赞
@login_required
def toggle_article_like(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    user = request.user
    if user in article.likes.all():
        article.likes.remove(user)
        liked = False
    else:
        article.likes.add(user)
        liked = True

        if user != article.author:
            Notification.objects.create(
                user=article.author,
                message=f"{user.username} 点赞了你的文章《{article.title}》",
                link=f"/article/{article.id}/"
            )

    return JsonResponse({'liked': liked, 'likes_count': article.likes.count()})

#评论点赞
@login_required
def toggle_comment_like(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    user = request.user
    if user in comment.likes.all():
        comment.likes.remove(user)
        liked = False
    else:
        comment.likes.add(user)
        liked = True

        if user != comment.user:
            Notification.objects.create(
                user=comment.user,
                message=f"{user.username} 赞了你的评论",
                link=f"/article/{comment.article.id}/"
            )

    return JsonResponse({'liked': liked, 'likes_count': comment.likes.count()})

#留言板
@login_required
def message_board(request):
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()  # 获取留言内容
        parent_id = request.POST.get('parent_id')  # 是否为回复某条留言
        parent = Message.objects.filter(id=parent_id).first() if parent_id else None

        if content:
            message = Message.objects.create(user=request.user, content=content, parent=parent)

            if not parent:
                admin_user = User.objects.filter(
                    username=settings.BLOG_OWNER_USERNAME
                ).first()
                if admin_user and request.user != admin_user:
                    Notification.objects.create(
                        user=admin_user,
                        message=f"{request.user.username} 留言了：{content[:20]}",
                        link="/messages/"
                    )

            # 被回复者收到通知
            if parent and parent.user != request.user:
                Notification.objects.create(
                    user=parent.user,
                    message=f"{request.user.username} 回复了你的留言",
                    link="/messages/"
                )

            return redirect('message_board')


    all_messages = Message.objects.filter(parent=None).order_by('-created_at')
    paginator = Paginator(all_messages, 10)  # 每页10条一级留言
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'blogapp/message_board.html', {
        'page_obj': page_obj,
    })

#删除帖子
@login_required
def article_delete(request, article_id):
    article = get_object_or_404(Article, id=article_id, author=request.user)
    if request.method == 'POST':
        article.delete()
        return redirect('user_profile', username=request.user.username)
    return redirect('article_detail', article_id=article_id)

#游戏列表
def game_list(request):
    games = [
        {'name': '贪吃蛇', 'key': 'snake'},
        {'name': '2048', 'key': '2048'},
    ]
    return render(request, 'blogapp/game_list.html', {'games': games})

#玩游戏
def play_game(request, game_name):
    return render(request, f'blogapp/games/{game_name}.html')


from django.http import JsonResponse
from .models import GameScore
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt#关闭 CSRF 防护机制
#提交分数
def submit_score(request):
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            data = json.loads(request.body.decode('utf-8'))
            game = data.get('game')
            score = int(data.get('score', 0))
            if game in ['snake', '2048', 'tetris']:
                GameScore.objects.create(user=request.user, game=game, score=score)
                return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'unauthorized'})

#游戏排行榜
def game_leaderboard(request, game_name):
    top_scores = GameScore.objects.filter(game=game_name).select_related('user')[:10]
    return render(request, 'blogapp/game_leaderboard.html', {
        'game_name': game_name,
        'scores': top_scores
    })

#音乐播放器
# blogapp/views.py
@xframe_options_exempt
def music_iframe(request):
    return render(request, 'blogapp/music_iframe.html')
# blogapp/views.py
def music_player(request):
    return render(request, 'blogapp/music_player.html')

#讨论组
@login_required
def forum_new(request):
    if request.method == 'POST':
        form = DiscussionPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()

            # 附件上传处理
            for file in request.FILES.getlist('file'):
                DiscussionAttachment.objects.create(post=post, file=file)

            return redirect('forum_detail', post_id=post.id)
    else:
        form = DiscussionPostForm()

    return render(request, 'blogapp/forum_new.html', {'form': form})


from django.db.models import Count

from django.db.models import Q
from django.core.paginator import Paginator
from django.db.models import Count
from .models import DiscussionPost  # 确保正确导入模型

#讨论区首页
def forum_index(request):
    query = request.GET.get("q", "")
    sort = request.GET.get("sort", "latest")

    posts = DiscussionPost.objects.all()

    # 搜索过滤
    if query:
        posts = posts.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ) # 支持标题和正文模糊搜索

    # 排序逻辑
    if sort == "hot":
        posts = posts.annotate(
            likes_count=Count('likes')
        ).order_by('-likes_count', '-views', '-created_at')
    elif sort == "featured":
        posts = posts.filter(is_featured=True).order_by('-created_at')
    else:
        posts = posts.order_by('-is_pinned', '-created_at')

    # 分页逻辑
    paginator = Paginator(posts, 10)
    page = request.GET.get('page')
    posts = paginator.get_page(page)

    return render(request, 'blogapp/forum_index.html', {
        'posts': posts,
        'sort': sort,
        'query': query,  # 别忘了传回模板
    })





@login_required
#讨论区内容
def forum_detail(request, post_id):
    post = get_object_or_404(DiscussionPost, id=post_id)
    replies = DiscussionReply.objects.filter(post=post, parent__isnull=True).prefetch_related('children')
    # 通知帖子作者（不是自己）
    if post.author != request.user:
        create_notification(
            user=post.author,
            message=f"{request.user.username} 回复你的帖子《{post.title}》",
            link=reverse('forum_detail', args=[post.id]),
            type='reply',
            preview=post.content[:50]
        )

    if request.method == 'POST' and request.user.is_authenticated:
        form = DiscussionReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.post = post
            reply.author = request.user
            parent_id = request.POST.get('parent_id')
            if parent_id:
                reply.parent = get_object_or_404(DiscussionReply, id=parent_id)
            reply.save()

            # ✅ 私信通知发帖者（不通知自己）
            if post.author != request.user:
                create_notification(
                    user=post.author,
                    message=f"{request.user.username} 回复你的帖子《{post.title}》",
                    link=reverse('forum_detail', args=[post.id]),
                    type='reply',
                    preview=post.content[:50]
                )

            return redirect('forum_detail', post_id=post.id)
    else:
        form = DiscussionReplyForm()

    return render(request, 'blogapp/forum_detail.html', {
        'post': post,
        'replies': replies,
        'form': form,
    })



@login_required
#讨论区回复
def delete_reply(request, reply_id):
    reply = get_object_or_404(DiscussionReply, pk=reply_id)
    if reply.author != request.user:
        return HttpResponseForbidden("你没有权限删除该回复")

    if request.method == "POST":
        reply.delete()
        return redirect('forum_detail', post_id=reply.post.id)

    return HttpResponseBadRequest("仅允许 POST 请求")



@login_required
#讨论区点赞
def toggle_forum_like(request, post_id):
    post = get_object_or_404(DiscussionPost, id=post_id)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
        if request.user != post.author:
            create_notification(
                user=post.author,
                message=f"{request.user.username} 点赞了你的帖子《{post.title}》",
                link=reverse('forum_detail', args=[post.id]),
                type='like',
                preview=post.content[:50]
            )

    return JsonResponse({'liked': liked, 'likes_count': post.likes.count()})


@login_required
#讨论区收藏
def toggle_forum_collect(request, post_id):
    post = get_object_or_404(DiscussionPost, id=post_id)
    if request.user in post.collectors.all():
        post.collectors.remove(request.user)
        collected = False
    else:
        post.collectors.add(request.user)
        collected = True
        if request.user != post.author:
            create_notification(
                user=post.author,
                message=f"{request.user.username} 收藏了你的帖子《{post.title}》",
                link=reverse('forum_detail', args=[post.id]),
                type='collect',
                preview=post.content[:50]
            )

    return JsonResponse({'collected': collected})


#
@require_POST
@login_required
#讨论区置顶
def toggle_pin(request, post_id):
    post = get_object_or_404(DiscussionPost, id=post_id)
    if request.user.is_superuser:
        post.is_pinned = not post.is_pinned
        post.save()
    return redirect('forum_detail', post_id=post_id)
#精华
@require_POST
@login_required
#讨论区精华
def toggle_feature(request, post_id):
    post = get_object_or_404(DiscussionPost, id=post_id)
    if request.user.is_superuser:
        post.is_featured = not post.is_featured
        post.save()
    return redirect('forum_detail', post_id=post_id)


@login_required
#讨论区编辑
def forum_edit(request, post_id):
    post = get_object_or_404(DiscussionPost, id=post_id)
    if request.user != post.author:
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = DiscussionPostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            return redirect('forum_detail', post_id=post.id)
    else:
        form = DiscussionPostForm(instance=post)

    return render(request, 'blogapp/forum_edit.html', {'form': form})


@login_required
#讨论区删除
def forum_delete(request, post_id):
    post = get_object_or_404(DiscussionPost, id=post_id)
    if request.user != post.author:
        return HttpResponseForbidden()

    post.delete()
    return redirect('forum_index')
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
#讨论区精华通知
def toggle_featured(request, post_id):
    post = get_object_or_404(DiscussionPost, id=post_id)
    post.is_featured = not post.is_featured
    post.save()
    if request.user != post.author:
        create_notification(
            user=post.author,
            message=f"你的帖子《{post.title}》已被设为【精华帖】",
            link=reverse('forum_detail', args=[post.id]),
            type='feature',
            preview=post.content[:50]
        )

    return redirect('forum_detail', post_id=post.id)

@staff_member_required
#讨论区置顶
def toggle_pinned(request, post_id):
    post = get_object_or_404(DiscussionPost, id=post_id)
    post.is_pinned = not post.is_pinned
    post.save()
    if request.user != post.author:
        create_notification(
            user=post.author,
            message=f"你的帖子《{post.title}》已被设为【置顶帖】",
            link=reverse('forum_detail', args=[post.id]),
            type='pin',
            preview=post.content[:50]
        )

    return redirect('forum_detail', post_id=post.id)

@staff_member_required# 只有后台成员能操作
#讨论区评论关闭
def toggle_status(request, post_id):
    post = get_object_or_404(DiscussionPost, id=post_id)
    post.status = 'closed' if post.status == 'open' else 'open'
    post.save()
    return redirect('forum_detail', post_id=post.id)

#举报
def report_view(request, report_type, target_id):
    if report_type == 'article':
        target = get_object_or_404(Article, id=target_id)
    elif report_type == 'user':
        target = get_object_or_404(User, id=target_id)
    elif report_type == 'post':
        target = get_object_or_404(DiscussionPost, id=target_id)
    elif report_type == 'reply':
        target = get_object_or_404(DiscussionReply, id=target_id)
    else:
        raise Http404("无效的举报类型")

    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.report_type = report_type
            report.target_id = target.id
            report.reporter = request.user
            report.save()
            messages.success(request, "举报已提交，感谢反馈！")
            return redirect('article_list')  # 或跳回之前页面
    else:
        form = ReportForm()

    return render(request, 'blogapp/report_form.html', {
        'form': form,
        'report_type': report_type,
        'target': target
    })
from django.utils import timezone
from datetime import timedelta
@staff_member_required
#处理举报
def admin_handle_report(request, report_id):
    report = get_object_or_404(Report, pk=report_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'ban_7' and report.report_type == 'user':
            profile = get_object_or_404(UserProfile, pk=report.target_id)
            profile.ban_expiration = timezone.now() + timedelta(days=7)
            profile.save()
            messages.success(request, f"{profile.user.username} 已被封禁 7 天")

        elif action == 'ban_permanent' and report.report_type == 'user':
            profile = get_object_or_404(UserProfile, pk=report.target_id)
            profile.ban_expiration = timezone.now() + timedelta(days=365 * 100)
            profile.save()
            messages.success(request, f"{profile.user.username} 已被永久封禁")


        elif action == 'delete':
            if report.report_type == 'article':
                try:
                    article = get_object_or_404(Article, pk=report.target_id)
                    article.delete()
                    messages.success(request, f"已删除文章 #{report.target_id}")
                except DiscussionReply.DoesNotExist:
                    messages.error(request, "找不到对应的文章，可能已被删除。")
            elif report.report_type == 'post':
                try:
                    post = get_object_or_404(DiscussionPost, pk=report.target_id)
                    post.delete()
                    messages.success(request, f"已删除讨论帖 #{report.target_id}")
                except DiscussionReply.DoesNotExist:
                    messages.error(request, "找不到对应的讨论贴，可能已被删除。")
            elif report.report_type == 'comment':
                try:
                    comment = get_object_or_404(Comment, pk=report.target_id)
                    comment.delete()
                    messages.success(request, f"已删除评论 #{report.target_id}")
                except DiscussionReply.DoesNotExist:
                    messages.error(request, "找不到对应的评论，可能已被删除。")

            elif report.report_type == 'reply':
                try:
                    obj = DiscussionReply.objects.get(id=report.target_id)
                    obj.delete()
                    messages.success(request, "讨论回复已删除。")
                except DiscussionReply.DoesNotExist:
                    messages.error(request, "找不到对应的讨论回复，可能已被删除。")


    # 可选：标记此举报已处理，或删除举报记录
        report.delete()
        return redirect('admin:blogapp_report_changelist')

    return render(request, 'admin/handle_report.html', {
        'report': report
    })

from django.shortcuts import render


#封号处理页面
def custom_permission_denied_view(request, exception=None):
    ban_expiration = None
    if request.user.is_authenticated:
        ban_expiration = request.user.userprofile.ban_expiration
    return render(request, '403.html', {
        'ban_expiration': ban_expiration,
    }, status=403)



from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import UserProfile
from django.urls import reverse

@staff_member_required
#解除封禁
def admin_unban_user(request, user_id):
    profile = get_object_or_404(UserProfile, user__id=user_id)
    profile.ban_expiration = None
    profile.save()
    messages.success(request, f"已解除用户 {profile.user.username} 的封禁")
    return redirect(reverse('admin:blogapp_userprofile_changelist'))
# views.py

def ban_notice(request):
    return render(request, 'blogapp/403.html', {
        'exception': "你的账号已被封禁，请联系管理员。",
    })

from django.http import JsonResponse

def clear_ban_session(request):
    request.session.pop('ban_expiration', None)
    return JsonResponse({'status': 'cleared'})

