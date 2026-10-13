# 博客知识库与内容创作 Agent

## 已实现能力

- DeepSeek Tool Calling 多步执行循环，最多执行 5 轮工具调用。
- 知识问答、评论洞察、站点分析、内容创作 4 类 Skill 路由与工具白名单。
- 基于文章标题、标签和正文分块的 BM25 RAG 检索。
- 文章全文读取、评论聚合、站点数据统计等只读工具。
- 登录用户多轮会话记忆与工具调用日志。
- 回答来源链接与执行步骤展示。
- 用户显式授权后保存私人文章草稿，草稿不会直接发布。
- API Key、数据库密码、邮件授权码等配置迁移到环境变量。

## Agent 执行流程

```text
用户任务
  -> 加载会话记忆
  -> DeepSeek 选择工具
  -> Django 执行受控工具
  -> 工具结果返回模型
  -> 继续调用工具或生成最终回答
  -> 保存消息、引用与调用日志
```

## 本地配置

1. 将 `.env.example` 复制为 `.env`。
2. 在本机 `.env` 中填写自己的 `DEEPSEEK_API_KEY`，不要提交真实凭据。
3. 默认使用 SQLite。需要连接原 MySQL 时，将 `DB_ENGINE` 改成 `mysql` 并填写数据库配置。
4. 安装依赖并执行迁移：

```powershell
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

登录后访问 `/chat/`。

## 可演示任务

- “检索站内关于 Django 权限管理的文章，总结主要方案并列出来源。”
- “读取这篇文章的最近评论，总结读者认可点和争议点。”
- “结合站内相关文章生成一篇学习笔记，推荐分类和标签。”
- 勾选“允许保存私人草稿”后：“把刚才的学习笔记保存为草稿。”

## 测试

```powershell
python manage.py test blogapp.tests_agent -v 2
```

测试覆盖 RAG 命中、工具调用链、调用日志、草稿写权限和登录鉴权。
