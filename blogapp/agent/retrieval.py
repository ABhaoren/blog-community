import math
import re
from collections import Counter
from html import unescape

from django.core.cache import cache
from django.db.models import Count, Max
from django.utils.html import strip_tags

from blogapp.models import Article


TOKEN_PATTERN = re.compile(r'[a-z0-9_+#.]+|[\u4e00-\u9fff]+', re.IGNORECASE)


def clean_text(value):
    value = strip_tags(value or '')
    value = unescape(value)
    return re.sub(r'\s+', ' ', value).strip()


def tokenize(value):
    tokens = []
    for part in TOKEN_PATTERN.findall((value or '').lower()):
        if re.fullmatch(r'[\u4e00-\u9fff]+', part):
            if len(part) == 1:
                tokens.append(part)
            else:
                tokens.extend(part[index:index + 2] for index in range(len(part) - 1))
        else:
            tokens.append(part)
    return tokens


def chunk_text(value, size=520, overlap=80):
    text = clean_text(value)
    if not text:
        return []
    if len(text) <= size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = max(
                text.rfind('。', start, end),
                text.rfind('！', start, end),
                text.rfind('？', start, end),
                text.rfind('\n', start, end),
            )
            if boundary > start + size // 2:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _corpus_cache_key():
    state = Article.objects.aggregate(total=Count('id'), latest=Max('updated_at'))
    latest = state['latest'].isoformat() if state['latest'] else 'empty'
    return f"agent-rag-corpus:{state['total']}:{latest}"


def build_corpus():
    cache_key = _corpus_cache_key()
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    documents = []
    articles = (
        Article.objects.select_related('category', 'author')
        .prefetch_related('tags')
        .order_by('-updated_at')[:300]
    )
    for article in articles:
        tags = [tag.name for tag in article.tags.all()]
        for chunk_index, chunk in enumerate(chunk_text(article.content)):
            documents.append({
                'article_id': article.id,
                'title': article.title,
                'author': article.author.username,
                'category': article.category.name if article.category else '',
                'tags': tags,
                'chunk_index': chunk_index,
                'text': chunk,
                'tokens': tokenize(f"{article.title} {article.title} {' '.join(tags)} {chunk}"),
                'updated_at': article.updated_at.isoformat(),
                'url': f'/article/{article.id}/',
            })

    cache.set(cache_key, documents, timeout=600)
    return documents


def search_articles(query, limit=5, category='', tag=''):
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    corpus = [
        document
        for document in build_corpus()
        if (not category or document['category'].lower() == category.lower())
        and (not tag or tag.lower() in {item.lower() for item in document['tags']})
    ]
    if not corpus:
        return []

    document_frequencies = Counter()
    document_lengths = []
    for document in corpus:
        document_frequencies.update(set(document['tokens']))
        document_lengths.append(len(document['tokens']))

    average_length = sum(document_lengths) / max(len(document_lengths), 1)
    scored = []
    k1 = 1.5
    b = 0.75
    for document, document_length in zip(corpus, document_lengths):
        term_frequencies = Counter(document['tokens'])
        score = 0.0
        for token in query_tokens:
            frequency = term_frequencies[token]
            if not frequency:
                continue
            document_frequency = document_frequencies[token]
            inverse_frequency = math.log(
                1 + (len(corpus) - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            denominator = frequency + k1 * (
                1 - b + b * document_length / max(average_length, 1)
            )
            score += inverse_frequency * (frequency * (k1 + 1)) / denominator

        title_tokens = set(tokenize(document['title']))
        score += 1.2 * sum(1 for token in query_tokens if token in title_tokens)
        if score > 0:
            scored.append((score, document))

    scored.sort(key=lambda item: item[0], reverse=True)
    results = []
    chunks_per_article = Counter()
    for score, document in scored:
        article_id = document['article_id']
        if chunks_per_article[article_id] >= 2:
            continue
        chunks_per_article[article_id] += 1
        results.append({
            'article_id': article_id,
            'title': document['title'],
            'author': document['author'],
            'category': document['category'],
            'tags': document['tags'],
            'content': document['text'],
            'chunk_index': document['chunk_index'],
            'score': round(score, 4),
            'url': document['url'],
        })
        if len(results) >= max(1, min(int(limit), 10)):
            break
    return results
