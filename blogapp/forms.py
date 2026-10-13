
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile
from .models import Article, ArticleAttachment
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from .models import DiscussionPost, DiscussionReply
from .models import Report
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
class DiscussionPostForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorUploadingWidget())

    class Meta:
        model = DiscussionPost
        fields = ['title', 'content']


class DiscussionReplyForm(forms.ModelForm):  # ✅ 必须是 ModelForm
    content = forms.CharField(widget=CKEditorUploadingWidget())

    class Meta:
        model = DiscussionReply
        fields = ['content']

class ArticleForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorUploadingWidget())
    class Meta:
        model = Article
        fields = ['title', 'content']


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = ArticleAttachment
        fields = ['file']


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name']



class ProfileEditForm(forms.ModelForm):
    birthday = forms.DateField(
        label='生日',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = UserProfile
        fields = ['gender', 'birthday', 'avatar', 'signature']




class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': '请输入举报原因...'})
        }


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(label='电子邮箱', required=True)
    first_name = forms.CharField(label='昵称', required=False)
    gender = forms.ChoiceField(label='性别', choices=UserProfile.GENDER_CHOICES, required=False)
    birthday = forms.DateField(label='生日', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    avatar = forms.ImageField(label='头像', required=False)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'email', 'password1', 'password2', 'gender', 'birthday', 'avatar']
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("该邮箱已被注册，请更换一个。")
        return email
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.utils import timezone

class CustomAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        profile = getattr(user, 'userprofile', None)
        if profile and profile.ban_expiration and profile.ban_expiration > timezone.now():
            raise PermissionDenied(f"你的账号已被封禁至 {profile.ban_expiration.strftime('%Y-%m-%d %H:%M')}")


