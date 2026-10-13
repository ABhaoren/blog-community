from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import Report, UserProfile, DiscussionPost, Article, Comment
from django.utils import timezone

@staff_member_required
def handle_report(request, report_id):
    report = get_object_or_404(Report, id=report_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if report.report_type == 'user':
            user = get_object_or_404(UserProfile, user_id=report.target_id)
            if action == 'ban_7':
                user.ban_expiration = timezone.now() + timezone.timedelta(days=7)
                user.save()
                messages.success(request, '用户已封禁7天')
            elif action == 'ban_permanent':
                user.ban_expiration = timezone.datetime.max.replace(tzinfo=timezone.utc)
                user.save()
                messages.success(request, '用户已永久封禁')

        elif report.report_type == 'article':
            article = get_object_or_404(Article, id=report.target_id)
            if action == 'delete':
                article.delete()
                messages.success(request, '文章已删除')

        elif report.report_type == 'post':
            post = get_object_or_404(DiscussionPost, id=report.target_id)
            if action == 'delete':
                post.delete()
                messages.success(request, '讨论帖已删除')

        elif report.report_type == 'comment':
            comment = get_object_or_404(Comment, id=report.target_id)
            if action == 'delete':
                comment.delete()
                messages.success(request, '评论已删除')

        report.delete()
        return redirect('/admin/blogapp/report/')

    return render(request, 'admin/handle_report.html', {
        'report': report
    })
