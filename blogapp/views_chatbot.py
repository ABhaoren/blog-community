import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.html import escape, strip_tags
from django.views.decorators.http import require_POST

from .agent.client import AgentConfigurationError, get_client
from .models import Article, ArticleAnalysis


logger = logging.getLogger(__name__)


def format_analysis(analysis_text):
    blocks = []
    list_items = []

    def flush_list():
        if list_items:
            blocks.append('<ul>' + ''.join(f'<li>{item}</li>' for item in list_items) + '</ul>')
            list_items.clear()

    for raw_line in (analysis_text or '').splitlines():
        line = raw_line.strip()
        if not line:
            flush_list()
            continue
        if line.startswith('###'):
            flush_list()
            blocks.append(f'<h3>{escape(line.lstrip("# "))}</h3>')
        elif line.startswith(('- ', '* ')):
            list_items.append(escape(line[2:].strip()))
        else:
            flush_list()
            blocks.append(f'<p>{escape(line)}</p>')
    flush_list()
    return ''.join(blocks) or '<p>暂无解析结果。</p>'


@login_required
@require_POST
def ai_parse_article(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    cached = ArticleAnalysis.objects.filter(article=article).first()
    if cached:
        return JsonResponse({'reply': cached.analysis_content, 'cached': True})

    try:
        response = get_client().chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[
                {
                    'role': 'system',
                    'content': '你是中文文章分析助手，请输出核心观点、内容结构、关键词和阅读建议。',
                },
                {
                    'role': 'user',
                    'content': f'请解析以下文章：\n\n{strip_tags(article.content)[:16000]}',
                },
            ],
            temperature=0.2,
            max_tokens=1200,
        )
        formatted_reply = format_analysis(response.choices[0].message.content)
        analysis, _ = ArticleAnalysis.objects.update_or_create(
            article=article,
            defaults={'analysis_content': formatted_reply},
        )
        return JsonResponse({'reply': analysis.analysis_content, 'cached': False})
    except AgentConfigurationError:
        return JsonResponse({'error': 'AI 服务尚未配置。'}, status=503)
    except Exception:
        logger.exception('Article analysis failed for article %s', article_id)
        return JsonResponse({'error': 'AI 解析失败，请稍后再试。'}, status=500)
