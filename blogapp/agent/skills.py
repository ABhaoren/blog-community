from dataclasses import dataclass


@dataclass(frozen=True)
class AgentSkill:
    name: str
    label: str
    instructions: str
    tools: tuple[str, ...]


SKILLS = {
    'knowledge_qa': AgentSkill(
        name='knowledge_qa',
        label='知识库问答',
        instructions='优先检索相关文章，必要时读取全文，基于站内证据回答并列出来源。',
        tools=('list_articles', 'search_articles', 'get_article_detail'),
    ),
    'comment_insight': AgentSkill(
        name='comment_insight',
        label='评论洞察',
        instructions='先定位目标文章，再读取评论，归纳认可点、争议点和可执行改进建议。',
        tools=('list_articles', 'search_articles', 'get_article_detail', 'get_article_comments'),
    ),
    'site_analytics': AgentSkill(
        name='site_analytics',
        label='站点分析',
        instructions='调用统计工具获取真实数据，解释指标含义，不猜测缺失数据。',
        tools=('get_site_statistics', 'list_articles', 'search_articles'),
    ),
    'content_drafting': AgentSkill(
        name='content_drafting',
        label='内容创作',
        instructions=(
            '先检索资料并形成大纲，再生成标题、正文、分类和标签。'
            '只有用户开启写入权限时才保存私人草稿。'
        ),
        tools=(
            'list_articles',
            'search_articles',
            'get_article_detail',
            'get_article_comments',
            'save_article_draft',
        ),
    ),
}


SKILL_KEYWORDS = {
    'content_drafting': ('写文章', '生成文章', '草稿', '大纲', '改写', '润色', '标题', '标签'),
    'comment_insight': ('评论', '读者反馈', '争议', '舆情', '观点归纳'),
    'site_analytics': ('统计', '浏览量', '点赞量', '收藏量', '站点数据', '运营数据'),
}


def select_skill(message):
    normalized = (message or '').lower()
    scores = {
        skill_name: sum(1 for keyword in keywords if keyword in normalized)
        for skill_name, keywords in SKILL_KEYWORDS.items()
    }
    selected = max(scores, key=scores.get)
    if scores[selected] == 0:
        selected = 'knowledge_qa'
    return SKILLS[selected]


def tool_schemas_for_skill(skill, tool_schemas):
    allowed = set(skill.tools)
    return [
        schema
        for schema in tool_schemas
        if schema['function']['name'] in allowed
    ]
