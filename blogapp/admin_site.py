from django.contrib.admin import AdminSite
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden

class AdminOnlySite(AdminSite):
    site_header = "博客后台管理"
    site_title = "管理后台"
    index_title = "欢迎使用管理系统"

    def has_permission(self, request):
        # 限制：仅 superuser 或 staff 用户可访问
        if request.user.is_active and request.user.is_staff:
            return True
        return False
