from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.contrib.auth import logout

class BanCheckMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            profile = getattr(request.user, 'userprofile', None)
            if profile and profile.ban_expiration and profile.ban_expiration > timezone.now():
                logout(request)
                # 将封禁时间保存到 session 中，方便 403.html 页面访问
                request.session['ban_expiration'] = profile.ban_expiration.strftime('%Y-%m-%d %H:%M')
                raise PermissionDenied("你的账号已被封禁")
