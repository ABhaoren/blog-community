from django.conf import settings
from openai import OpenAI


class AgentConfigurationError(RuntimeError):
    pass


def get_client():
    if not settings.DEEPSEEK_API_KEY:
        raise AgentConfigurationError(
            'DEEPSEEK_API_KEY is not configured. Add it to the local .env file.'
        )
    return OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
    )
