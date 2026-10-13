import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .agent.client import AgentConfigurationError
from .agent.service import run_agent


logger = logging.getLogger(__name__)


@login_required
def agent_chat_page(request):
    return render(request, 'blogapp/chat_page.html')


@login_required
@require_POST
def agent_chat(request):
    try:
        payload = json.loads(request.body or '{}')
        result = run_agent(
            user=request.user,
            user_message=payload.get('message', ''),
            session_id=payload.get('session_id'),
            allow_write=payload.get('allow_write') is True,
        )
        return JsonResponse(result)
    except json.JSONDecodeError:
        return JsonResponse({'error': '请求内容不是有效的 JSON。'}, status=400)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    except AgentConfigurationError:
        return JsonResponse(
            {'error': 'AI 服务尚未配置，请在 .env 中设置新的 DEEPSEEK_API_KEY。'},
            status=503,
        )
    except Exception:
        logger.exception('Agent request failed')
        return JsonResponse({'error': 'Agent 执行失败，请稍后重试。'}, status=500)
