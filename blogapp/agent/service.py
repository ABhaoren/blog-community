import json
import time

from django.conf import settings

from blogapp.models import AgentMessage, AgentSession, AgentToolLog

from .client import get_client
from .skills import select_skill, tool_schemas_for_skill
from .tools import TOOL_SCHEMAS, ToolExecutionError, execute_tool


SYSTEM_PROMPT = """
你是博客站内的知识库与内容创作 Agent。

工作规则：
1. 用户询问“有哪些文章”或站内内容概览时，调用 list_articles；询问具体主题时调用 search_articles。
2. 复杂任务应自行分解，并按“检索-阅读-分析-回答”的顺序调用多个工具。
3. 回答要区分站内资料与通用知识；引用站内资料时写明文章标题。
4. 只有用户明确开启草稿写入权限时，才能调用 save_article_draft。草稿不会公开发布。
5. 不得删除文章、封禁用户或执行任何未注册的操作。
6. 工具没有返回足够证据时，应说明资料不足。
7. 最终用简洁、清晰的中文回答，不展示内部推理过程。
8. search_articles 返回零命中只表示该关键词没有匹配结果，不能据此声称知识库或站点为空；应查看 total_articles，必要时调用 list_articles。
""".strip()


def _get_or_create_session(user, session_id, first_message):
    if session_id:
        try:
            return AgentSession.objects.get(id=session_id, user=user)
        except (AgentSession.DoesNotExist, ValueError):
            pass
    return AgentSession.objects.create(user=user, title=first_message[:50])


def _load_messages(session):
    limit = max(4, settings.AGENT_MEMORY_MESSAGES)
    history = list(session.messages.order_by('-created_at')[:limit])
    history.reverse()
    return [
        {'role': message.role, 'content': message.content}
        for message in history
    ]


def _assistant_message_payload(message):
    payload = {'role': 'assistant', 'content': message.content or ''}
    if message.tool_calls:
        payload['tool_calls'] = [
            {
                'id': call.id,
                'type': 'function',
                'function': {
                    'name': call.function.name,
                    'arguments': call.function.arguments,
                },
            }
            for call in message.tool_calls
        ]
    return payload


def _citation_summary(citation):
    return {
        'article_id': citation.get('article_id'),
        'title': citation.get('title', ''),
        'author': citation.get('author', ''),
        'category': citation.get('category', ''),
        'url': citation.get('url', ''),
    }


def _merge_citations(current, incoming):
    seen = {(item.get('article_id'), item.get('url')) for item in current}
    for citation in incoming or []:
        summary = _citation_summary(citation)
        key = (summary.get('article_id'), summary.get('url'))
        if key not in seen:
            current.append(summary)
            seen.add(key)


def run_agent(*, user, user_message, session_id=None, allow_write=False):
    message_text = (user_message or '').strip()
    if not message_text:
        raise ValueError('消息不能为空。')
    if len(message_text) > 4000:
        raise ValueError('单条消息不能超过 4000 个字符。')

    session = _get_or_create_session(user, session_id, message_text)
    AgentMessage.objects.create(session=session, role='user', content=message_text)

    skill = select_skill(message_text)
    skill_prompt = (
        f"\n\n当前 Skill：{skill.label}（{skill.name}）\n"
        f"Skill 执行要求：{skill.instructions}"
    )
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT + skill_prompt}]
    messages.extend(_load_messages(session))
    client = get_client()
    citations = []
    tool_steps = []
    available_tools = tool_schemas_for_skill(skill, TOOL_SCHEMAS)

    for _ in range(max(1, settings.AGENT_MAX_STEPS)):
        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=messages,
            tools=available_tools,
            tool_choice='auto',
            temperature=0.2,
            max_tokens=1800,
        )
        assistant_message = response.choices[0].message
        messages.append(_assistant_message_payload(assistant_message))

        if not assistant_message.tool_calls:
            reply = (assistant_message.content or '').strip()
            if not reply:
                reply = '暂时没有生成有效回复，请重新描述任务。'
            AgentMessage.objects.create(
                session=session,
                role='assistant',
                content=reply,
                metadata={
                    'citations': citations,
                    'tool_steps': tool_steps,
                    'skill': skill.name,
                },
            )
            return {
                'reply': reply,
                'session_id': str(session.id),
                'citations': citations,
                'tool_steps': tool_steps,
                'skill': {'name': skill.name, 'label': skill.label},
            }

        for tool_call in assistant_message.tool_calls:
            started_at = time.perf_counter()
            success = True
            arguments = {}
            try:
                result, arguments = execute_tool(
                    tool_call.function.name,
                    tool_call.function.arguments,
                    user=user,
                    session=session,
                    allow_write=allow_write,
                )
                _merge_citations(citations, result.get('citations', []))
                tool_content = json.dumps(result, ensure_ascii=False, default=str)
            except (ToolExecutionError, TypeError, ValueError) as exc:
                success = False
                tool_content = json.dumps({'error': str(exc)}, ensure_ascii=False)

            duration_ms = int((time.perf_counter() - started_at) * 1000)
            AgentToolLog.objects.create(
                session=session,
                tool_name=tool_call.function.name,
                arguments=arguments,
                result_preview=tool_content[:1000],
                success=success,
                duration_ms=duration_ms,
            )
            tool_steps.append({
                'tool': tool_call.function.name,
                'success': success,
                'duration_ms': duration_ms,
            })
            messages.append({
                'role': 'tool',
                'tool_call_id': tool_call.id,
                'content': tool_content[:12000],
            })

    messages.append({
        'role': 'system',
        'content': '工具调用已达到上限。请根据已有结果直接给出最终答复，并说明尚未完成的部分。',
    })
    response = client.chat.completions.create(
        model=settings.DEEPSEEK_MODEL,
        messages=messages,
        temperature=0.2,
        max_tokens=1200,
    )
    reply = (response.choices[0].message.content or '').strip()
    AgentMessage.objects.create(
        session=session,
        role='assistant',
        content=reply,
        metadata={
            'citations': citations,
            'tool_steps': tool_steps,
            'skill': skill.name,
            'step_limit_reached': True,
        },
    )
    return {
        'reply': reply,
        'session_id': str(session.id),
        'citations': citations,
        'tool_steps': tool_steps,
        'skill': {'name': skill.name, 'label': skill.label},
    }
