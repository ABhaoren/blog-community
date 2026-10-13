"""
URL configuration for blog project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from blogapp import admin_views  # 你可以建一个 admin_views.py 专门处理后台逻辑
from blogapp.forms import CustomAuthenticationForm
from django.conf.urls import handler403

handler403 = 'blogapp.views.custom_permission_denied_view'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('blogapp.urls')),  # 加上这行
    path('accounts/login/', auth_views.LoginView.as_view(
            authentication_form=CustomAuthenticationForm
        ), name='login'),
    path('ckeditor/', include('ckeditor_uploader.urls')),  #

]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



