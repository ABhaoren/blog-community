from django.shortcuts import render
from django.utils import timezone

class BanMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = getattr(request.user, 'userprofile', None)
            if profile and profile.ban_expiration and profile.ban_expiration > timezone.now():
                return render(request, '403.html', {
                    'user': request.user
                })
        return self.get_response(request)
