import json

from django.db.models import Sum
from django.utils.html import strip_tags

from blogapp.models import AgentDraft, Article, Comment

from .retrieval import clean_text, search_articles


class ToolExecutionError(RuntimeError):
    pass


TOOL_SCHEMAS = [
    {
        'type': 'function',
        'function': {
            'name': 'list_articles',
            'description': 'List existing or recent blog articles. Use this for catalog questions such as what content exists on the site.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'limit': {'type': 'integer', 'minimum': 1, 'maximum': 20},
                    'category': {'type': 'string'},
                    'tag': {'type': 'string'},
                    'order_by': {
                        'type': 'string',
                        'enum': ['recent', 'popular'],
                    },
                },
                'additionalProperties': False,
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'search_articles',
            'description': 'Search the blog knowledge base. Use this before answering questions about site content.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {'type': 'string', 'description': 'Search query in Chinese or English.'},
                    'limit': {'type': 'integer', 'minimum': 1, 'maximum': 10},
                    'category': {'type': 'string'},
                    'tag': {'type': 'string'},
                },
                'required': ['query'],
                'additionalProperties': False,
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_article_detail',
            'description': 'Read one full article and its metadata by article id.',
            'parameters': {
                'type': 'object',
                'properties': {'article_id': {'type': 'integer'}},
                'required': ['article_id'],
                'additionalProperties': False,
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_article_comments',
            'description': 'Read recent comments for an article to summarize reader feedback.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'article_id': {'type': 'integer'},
                    'limit': {'type': 'integer', 'minimum': 1, 'maximum': 30},
                },
                'required': ['article_id'],
                'additionalProperties': False,
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_site_statistics',
            'description': 'Get aggregate article, comment, view, like and collection statistics.',
            'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'save_article_draft',
            'description': 'Save generated content to a private draft. Only call when the user explicitly enables draft writing.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'title': {'type': 'string'},
                    'content': {'type': 'string'},
                    'category': {'type': 'string'},
                    'tags': {'type': 'array', 'items': {'type': 'string'}},
                    'source_article_ids': {'type': 'array', 'items': {'type': 'integer'}},
                },
                'required': ['title', 'content'],
                'additionalProperties': False,
            },
        },
    },
]


GENERIC_CATALOG_QUERIES = {
    '博客',
    '文章',
    '全部文章',
    '所有文章',
    '站内文章',
    '文章列表',
    '已有文章',
    '已有内容',
    '目前内容',
}


def _article_summary(article):
    return {
        'article_id': article.id,
        'title': article.title,
        'author': article.author.username,
        'category': article.category.name if article.category else '',
        'tags': [tag.name for tag in article.tags.all()],
        'excerpt': clean_text(article.content)[:300],
        'views': article.views,
        'updated_at': article.updated_at.isoformat(),
        'url': f'/article/{article.id}/',
    }


def _list_articles(arguments, **_):
    limit = max(1, min(int(arguments.get('limit', 10)), 20))
    articles = Article.objects.select_related('author', 'category').prefetch_related('tags')

    category = str(arguments.get('category', '')).strip()
    tag = str(arguments.get('tag', '')).strip()
    if category:
        articles = articles.filter(category__name__iexact=category)
    if tag:
        articles = articles.filter(tags__name__iexact=tag)

    total = articles.distinct().count()
    if arguments.get('order_by') == 'popular':
        articles = articles.distinct().order_by('-views', '-updated_at')
    else:
        articles = articles.distinct().order_by('-updated_at')

    results = [_article_summary(article) for article in articles[:limit]]
    return {
        'total_articles': total,
        'returned': len(results),
        'results': results,
        'citations': results,
    }


def _search_articles(arguments, **_):
    query = str(arguments.get('query', '')).strip()[:300]
    if query in GENERIC_CATALOG_QUERIES:
        return _list_articles(arguments)

    results = search_articles(
        query=query,
        limit=arguments.get('limit', 5),
        category=str(arguments.get('category', ''))[:100],
        tag=str(arguments.get('tag', ''))[:100],
    )
    return {
        'total_articles': Article.objects.count(),
        'matched_articles': len({result['article_id'] for result in results}),
        'returned_chunks': len(results),
        'results': results,
        'citations': results,
        'note': (
            'No articles matched this query; this does not mean the site has no articles.'
            if not results
            else ''
        ),
    }


def _get_article_detail(arguments, **_):
    article_id = int(arguments['article_id'])
    try:
        article = Article.objects.select_related('author', 'category').prefetch_related('tags').get(
            id=article_id
        )
    except Article.DoesNotExist as exc:
        raise ToolExecutionError(f'Article {article_id} does not exist.') from exc

    content = clean_text(article.content)
    result = {
        'article_id': article.id,
        'title': article.title,
        'author': article.author.username,
        'category': article.category.name if article.category else '',
        'tags': [tag.name for tag in article.tags.all()],
        'content': content[:8000],
        'updated_at': article.updated_at.isoformat(),
        'url': f'/article/{article.id}/',
    }
    return {'article': result, 'citations': [result]}


def _get_article_comments(arguments, **_):
    article_id = int(arguments['article_id'])
    limit = max(1, min(int(arguments.get('limit', 10)), 30))
    if not Article.objects.filter(id=article_id).exists():
        raise ToolExecutionError(f'Article {article_id} does not exist.')
    comments = (
        Comment.objects.filter(article_id=article_id)
        .select_related('user')
        .order_by('-created_at')[:limit]
    )
    return {
        'article_id': article_id,
        'count': len(comments),
        'comments': [
            {
                'author': comment.user.username,
                'content': clean_text(comment.content)[:1000],
                'created_at': comment.created_at.isoformat(),
            }
            for comment in comments
        ],
    }


def _get_site_statistics(arguments, **_):
    articles = Article.objects.all()
    return {
        'article_count': articles.count(),
        'comment_count': Comment.objects.count(),
        'total_views': articles.aggregate(value=Sum('views'))['value'] or 0,
        'total_likes': sum(article.likes.count() for article in articles),
        'total_collections': sum(article.collectors.count() for article in articles),
    }


def _save_article_draft(arguments, user, session, allow_write=False):
    if not allow_write:
        raise ToolExecutionError('Draft writing is disabled. Ask the user to enable it first.')
    if not user.is_authenticated:
        raise ToolExecutionError('Authentication is required to save a draft.')

    title = str(arguments.get('title', '')).strip()[:200]
    content = str(arguments.get('content', '')).strip()
    if not title or not content:
        raise ToolExecutionError('Draft title and content are required.')

    tags = [str(tag).strip()[:100] for tag in arguments.get('tags', []) if str(tag).strip()]
    source_ids = []
    for value in arguments.get('source_article_ids', []):
        try:
            source_ids.append(int(value))
        except (TypeError, ValueError):
            continue

    draft = AgentDraft.objects.create(
        owner=user,
        session=session,
        title=title,
        content=content,
        category_name=str(arguments.get('category', '')).strip()[:100],
        tags=tags[:10],
        source_article_ids=source_ids[:20],
    )
    return {
        'saved': True,
        'draft_id': draft.id,
        'title': draft.title,
        'message': 'The draft was saved privately and was not published.',
    }


TOOL_HANDLERS = {
    'list_articles': _list_articles,
    'search_articles': _search_articles,
    'get_article_detail': _get_article_detail,
    'get_article_comments': _get_article_comments,
    'get_site_statistics': _get_site_statistics,
    'save_article_draft': _save_article_draft,
}


def execute_tool(name, raw_arguments, *, user, session, allow_write=False):
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        raise ToolExecutionError(f'Unknown tool: {name}')
    try:
        arguments = json.loads(raw_arguments or '{}')
    except json.JSONDecodeError as exc:
        raise ToolExecutionError('Tool arguments are not valid JSON.') from exc
    if not isinstance(arguments, dict):
        raise ToolExecutionError('Tool arguments must be a JSON object.')
    return handler(
        arguments,
        user=user,
        session=session,
        allow_write=allow_write,
    ), arguments
