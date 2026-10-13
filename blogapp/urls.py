from django.urls import path
from . import views, admin_views
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView

from .forms import CustomAuthenticationForm
from .views import submit_score, game_leaderboard, forum_index, forum_new, forum_detail, admin_unban_user
from blogapp.views import admin_handle_report
from blogapp.views_agent import agent_chat, agent_chat_page
from blogapp.views_chatbot import ai_parse_article
from django.contrib.auth import views as auth_views



urlpatterns = [

    path('accounts/password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    path('', views.article_list, name='article_list'),
    path('article/<int:article_id>/', views.article_detail, name='article_detail'),
    # path('article/new/', views.article_create, name='article_create'),
    # path('article/<int:article_id>/edit/', views.article_edit, name='article_edit'),
    path('article/new/', views.article_create_or_edit, name='article_create'),
    path('article/<int:article_id>/edit/', views.article_create_or_edit, name='article_edit'),
    path('category/<int:category_id>/', views.articles_by_category, name='articles_by_category'),
    path('category/name/<str:category_name>/', views.articles_by_category, name='articles_by_category_name'),

    path('tag/<int:tag_id>/', views.articles_by_tag, name='articles_by_tag'),
    path('tag/name/<str:tag_name>/', views.articles_by_tag, name='articles_by_tag_name'),

#登入
    path('accounts/login/', auth_views.LoginView.as_view(template_name='blogapp/login.html'), name='login'),

#退出
    path('accounts/logout/', LogoutView.as_view(next_page='article_list'), name='logout'),
path('accounts/login/', auth_views.LoginView.as_view(
    authentication_form=CustomAuthenticationForm
), name='login'),

#注册
    path('accounts/register/', views.register, name='register'),

#删除评论
    path('comment/delete/<int:comment_id>/', views.delete_comment, name='delete_comment'),

#通知
    path('notifications/', views.notification_list, name='notification_list'),

#编辑信息
    path('accounts/profile/edit/', views.edit_profile, name='edit_profile'),

#收藏帖子
    path('article/<int:article_id>/collect/', views.toggle_collect, name='toggle_collect'),

#个人主页
    path('user/<str:username>/', views.user_profile, name='user_profile'),

#个人收藏
    path('my/collections/', views.my_collections, name='my_collections'),

#关注粉丝
    path('user/<str:username>/follow/', views.toggle_follow, name='toggle_follow'),

#粉丝列表
    path('user/<str:username>/followers/', views.followers_list, name='followers_list'),

#关注列表
    path('user/<str:username>/following/', views.following_list, name='following_list'),

#帖子点赞
    path('article/<int:article_id>/like/', views.toggle_article_like, name='toggle_article_like'),

#评论点赞
    path('comment/<int:comment_id>/like/', views.toggle_comment_like, name='toggle_comment_like'),

#一键已读
    path('notifications/mark_read/', views.mark_all_read, name='mark_all_read'),

#一键删除
    path('notifications/delete_all/', views.delete_all_notifications, name='delete_all_notifications'),

#单一删除
    path('notifications/delete/<int:notification_id>/', views.delete_notification, name='delete_notification'),

#留言板
    path('messages/', views.message_board, name='message_board'),

#删除帖子
    path('article/<int:article_id>/delete/', views.article_delete, name='article_delete'),

#游戏
    path('games/', views.game_list, name='game_list'),
    path('games/<str:game_name>/', views.play_game, name='play_game'),
#加分
    path('api/game/submit_score/', submit_score, name='submit_score'),
#排行榜
    path('games/<str:game_name>/leaderboard/', game_leaderboard, name='game_leaderboard'),
#音乐播放器
    path('music-player-iframe/', views.music_iframe, name='music_player_iframe'),
    path('music-player/', views.music_player, name='music_player'),
#讨论组
    path('forum/', forum_index, name='forum_index'),
#新建讨论帖子
    path('forum/new/', forum_new, name='forum_new'),
#讨论帖子详情页
    path('forum/<int:post_id>/', forum_detail, name='forum_detail'),
#帖子删除
    path('forum/<int:post_id>/', views.forum_detail, name='forum_detail'),
#帖子回复
    path('forum/reply/delete/<int:reply_id>/', views.delete_reply, name='delete_forum_reply'),
#论坛喜欢
    path('forum/<int:post_id>/like/', views.toggle_forum_like, name='toggle_forum_like'),
#论坛收藏
    path('forum/<int:post_id>/collect/', views.toggle_forum_collect, name='toggle_forum_collect'),
#置顶
    path('forum/<int:post_id>/pin/', views.toggle_pin, name='toggle_pin'),
#精华
    path('forum/<int:post_id>/feature/', views.toggle_feature, name='toggle_feature'),
#主页帖子编辑
    path('forum/<int:post_id>/edit/', views.forum_edit, name='forum_edit'),
#主页帖子删除
    path('forum/<int:post_id>/delete/', views.forum_delete, name='forum_delete'),
    path('forum/<int:post_id>/toggle_featured/', views.toggle_featured, name='toggle_featured'),
    path('forum/<int:post_id>/toggle_pinned/', views.toggle_pinned, name='toggle_pinned'),

    path('forum/<int:post_id>/toggle_status/', views.toggle_status, name='toggle_status'),
path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
path('notifications/<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),
#举报
    path('report/<str:report_type>/<int:target_id>/', views.report_view, name='report'),
    path('report/<int:report_id>/handle/', admin_handle_report, name='admin_handle_report'),

#解禁
    path('unban/<int:user_id>/', views.admin_unban_user, name='admin_unban_user'),

# urls.py
    path('banned/', views.ban_notice, name='ban_notice'),
    path('clear-ban-session/', views.clear_ban_session, name='clear_ban_session'),
#AI
    path('api/ai_chat/', agent_chat, name='ai_chat'),
    path('chat/', agent_chat_page, name='chat_page'),

    path('article/<int:article_id>/ai_parse/', ai_parse_article, name='ai_parse_article'),\
    path('api/weather/', views.weather_auto_view),

]
