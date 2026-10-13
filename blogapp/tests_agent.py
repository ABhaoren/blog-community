import json
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from blogapp.agent.retrieval import search_articles
from blogapp.agent.service import run_agent
from blogapp.agent.skills import select_skill
from blogapp.agent.tools import ToolExecutionError, execute_tool
from blogapp.models import (
    AgentDraft,
    AgentSession,
    AgentToolLog,
    Article,
    Category,
    Comment,
    Tag,
)


class FakeCompletions:
    def __init__(self, messages):
        self.messages = list(messages)

    def create(self, **_kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=self.messages.pop(0))])


class FakeClient:
    def __init__(self, messages):
        self.chat = SimpleNamespace(completions=FakeCompletions(messages))


class AgentTestDataMixin:
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='agent-user', password='test-password')
        category = Category.objects.create(name='后端开发')
        django_tag = Tag.objects.create(name='Django')
        self.article = Article.objects.create(
            title='Django 权限管理实践',
            content=(
                '<p>Django 权限系统包含用户认证、权限校验和后台管理。</p>'
                '<p>项目通过 login_required 和对象所有权检查限制写操作。</p>'
            ),
            author=self.user,
            category=category,
        )
        self.article.tags.add(django_tag)
        Article.objects.create(
            title='夏季旅行记录',
            content='<p>这是一篇关于旅行路线和照片的记录。</p>',
            author=self.user,
        )
        Comment.objects.create(
            article=self.article,
            user=self.user,
            content='权限校验部分很实用。',
        )


class RetrievalTests(AgentTestDataMixin, TestCase):
    def test_bm25_retrieval_returns_relevant_article_with_source(self):
        results = search_articles('Django 权限校验', limit=3)

        self.assertTrue(results)
        self.assertEqual(results[0]['article_id'], self.article.id)
        self.assertEqual(results[0]['url'], f'/article/{self.article.id}/')
        self.assertGreater(results[0]['score'], 0)


class AgentToolTests(AgentTestDataMixin, TestCase):
    def test_catalog_query_lists_existing_articles(self):
        session = AgentSession.objects.create(user=self.user)
        result, _ = execute_tool(
            'search_articles',
            json.dumps({'query': '所有文章', 'limit': 10}),
            user=self.user,
            session=session,
        )

        self.assertEqual(result['total_articles'], 2)
        self.assertEqual(result['returned'], 2)
        self.assertEqual(len(result['citations']), 2)

    def test_zero_match_reports_nonempty_knowledge_base(self):
        session = AgentSession.objects.create(user=self.user)
        result, _ = execute_tool(
            'search_articles',
            json.dumps({'query': '量子芯片'}),
            user=self.user,
            session=session,
        )

        self.assertEqual(result['total_articles'], 2)
        self.assertEqual(result['matched_articles'], 0)
        self.assertIn('does not mean', result['note'])

    def test_skill_router_selects_content_workflow(self):
        skill = select_skill('结合站内资料生成文章并保存草稿')
        self.assertEqual(skill.name, 'content_drafting')
        self.assertIn('save_article_draft', skill.tools)

    def test_draft_tool_requires_explicit_write_permission(self):
        session = AgentSession.objects.create(user=self.user)
        arguments = json.dumps({'title': '测试草稿', 'content': '草稿正文'})

        with self.assertRaises(ToolExecutionError):
            execute_tool(
                'save_article_draft',
                arguments,
                user=self.user,
                session=session,
                allow_write=False,
            )

        result, _ = execute_tool(
            'save_article_draft',
            arguments,
            user=self.user,
            session=session,
            allow_write=True,
        )
        self.assertTrue(result['saved'])
        self.assertEqual(AgentDraft.objects.get().owner, self.user)

    def test_agent_executes_tool_and_records_trace(self):
        tool_call = SimpleNamespace(
            id='call-1',
            function=SimpleNamespace(
                name='search_articles',
                arguments=json.dumps({'query': 'Django 权限'}),
            ),
        )
        fake_client = FakeClient([
            SimpleNamespace(content=None, tool_calls=[tool_call]),
            SimpleNamespace(content='站内文章介绍了 Django 权限校验。', tool_calls=None),
        ])

        with patch('blogapp.agent.service.get_client', return_value=fake_client):
            result = run_agent(user=self.user, user_message='站内有哪些 Django 权限文章？')

        self.assertEqual(result['tool_steps'][0]['tool'], 'search_articles')
        self.assertEqual(result['skill']['name'], 'knowledge_qa')
        self.assertEqual(result['citations'][0]['article_id'], self.article.id)
        self.assertTrue(AgentToolLog.objects.get().success)


class AgentViewTests(AgentTestDataMixin, TestCase):
    def test_chat_api_requires_login(self):
        response = self.client.post(
            reverse('ai_chat'),
            data=json.dumps({'message': '测试'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 302)

    def test_chat_api_returns_structured_agent_result(self):
        self.client.force_login(self.user)
        expected = {
            'reply': '完成',
            'session_id': 'session-id',
            'citations': [],
            'tool_steps': [],
        }
        with patch('blogapp.views_agent.run_agent', return_value=expected):
            response = self.client.post(
                reverse('ai_chat'),
                data=json.dumps({'message': '测试'}),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
