# Blog Community

一个使用 Django 构建的博客社区项目，包含文章管理、用户互动、AI 文章解析，以及基于站内文章检索的内容助手。页面由 Django 模板渲染，部分交互通过 JavaScript Fetch 调用后端 JSON 接口。

**当前状态：本地项目，尚未公开部署。** 2026 年 10 月 13 日的隔离验收已验证首次真实解析、缓存读取与 8 个现有测试；同时记录了异常处理和缓存更新的待修复问题，详见验收报告。

![文章详情与解析结果](docs/verification/2026-10-13/v1.png)

- [开发实例与验证记录](docs/AI_CODING_CASE.md)
- [个人贡献](docs/CONTRIBUTIONS.md)
- [实际验收记录与截图](docs/verification/2026-10-13/REPORT.md)
- GitHub 仓库地址：[ABhaoren/blog-community](https://github.com/ABhaoren/blog-community)。
- 项目演示视频：**待录制并补充链接**。
- 在线体验地址：**尚未上线**。

## 核心功能与验证状态

| 模块 | 当前源码包含的实现 | 状态 |
| --- | --- | --- |
| 内容管理 | 文章列表、详情、创建与编辑，分类、标签和附件关联 | 源码已确认；操作流程待运行验证 |
| 用户与社区 | 注册、登录、个人资料、评论、点赞、收藏、关注和通知 | 源码已确认；各功能及权限边界待验证 |
| AI 文章解析 | 登录用户发起 POST；后端读取文章、调用模型、保存并返回解析结果 | 基础流程实测通过；异常页面处理和输出格式存在问题 |
| 文章解析缓存 | 以文章为单位保存 ArticleAnalysis，再次请求优先返回已有结果 | 重复读取实测通过；正文更新后缓存未失效 |
| 站内内容 Agent | 按任务选择工具，执行检索、阅读、评论聚合、站点统计等操作 | 源码已确认；实际任务完成效果待验证 |
| 站内检索 | 对文章分块，以 BM25 进行词项相关性检索，返回文章来源 | 源码已确认；检索质量待验证 |
| 会话与草稿 | 保存会话消息、工具调用记录；写入私人草稿要求登录与显式授权 | 源码已确认；隔离与授权用例待验证 |

内容助手使用的是 BM25 文本检索，当前没有采用向量数据库或 Embedding 检索。现有前端采用 Django 模板与原生 JavaScript，React、Next.js 不属于这个项目的已实现技术栈。

## 技术栈

| 层次 | 当前实现 |
| --- | --- |
| 页面 | HTML、CSS、Django Templates、JavaScript Fetch |
| 后端 | Python、Django 5.2.1、Django Forms、Django ORM |
| 数据库 | 原配置为 SQLite；本次使用独立新建 SQLite，MySQL 未验证 |
| 模型接入 | openai Python SDK 1.82.1，通过可配置 base_url 调用兼容接口 |
| 模型配置 | 本次向 api.deepseek.com 请求 deepseek-chat 成功；返回模型标识为 deepseek-flash，名称差异原因未核验 |
| 编辑与后台 | django-ckeditor、django-jazzmin |
| 配置 | python-dotenv 加载项目根目录 .env |
| 测试 | Django TestCase、unittest.mock、FakeClient |

完整依赖版本见 [requirements.txt](requirements.txt)。应用运行时的模型由后端配置决定。

## 请求与数据流

```text
文章页面
  → JavaScript Fetch 发起 POST，附带 CSRF Token
  → Django 路由与视图检查登录状态和请求方法
  → ORM 读取 Article 与 ArticleAnalysis
      → 已有解析：返回 reply 和 cached=true
      → 没有解析：后端模型客户端请求 LLM
          → 整理模型输出并保存 ArticleAnalysis
          → 返回 reply 和 cached=false
  → 页面展示解析内容
```

Agent 是另一条请求链：

```text
/chat/ 页面 → POST /api/ai_chat/
  → 加载当前用户会话，选择任务 Skill
  → 模型提出工具调用 → 后端执行注册工具
  → 工具结果交回模型 → 生成回答
  → 保存会话与工具记录，返回引用与执行步骤
```

工具循环次数受 `AGENT_MAX_STEPS` 控制。一次循环可能包含多个工具调用；达到循环上限后，源码还会请求模型生成收尾回答，不能把该配置理解为总 API 调用次数或总工具次数。

## 代码导航

```text
blog/
  settings.py                 环境配置、数据库与模型设置
  urls.py                     项目级路由
blogapp/
  models.py                   文章、用户扩展、解析结果与 Agent 数据模型
  forms.py                    表单与输入校验
  urls.py                     业务路由
  views.py                    博客与社区业务
  views_chatbot.py             单篇文章 AI 解析
  views_agent.py               Agent 页面与 JSON 接口
  agent/
    client.py                 模型客户端
    service.py                会话与工具调用循环
    skills.py                 任务路由与提供给模型的工具集合
    tools.py                  工具定义及后端执行
    retrieval.py              分块、词项处理与 BM25 检索
  migrations/                 数据库迁移
  tests_agent.py              Agent 相关测试
templates/blogapp/            页面模板与部分交互脚本
static/                       静态资源
docs/                         AI 编码实例与贡献说明
manage.py                     Django 命令入口
requirements.txt              Python 依赖
```

## 本地启动

以下是根据源码整理的开发环境复现步骤，**尚未验证全新依赖安装**。本次发现原 `.venv` 指向重置电脑前已不存在的解释器，不能直接运行；验收使用可用 Python 3.12.14 加载保留的依赖并启动隔离服务，未重建原环境。实际可用的本机验收启动命令见 [验收记录](docs/verification/2026-10-13/REPORT.md)。以下步骤面向重新配置的新目录。

### 1. 准备 Python 环境

原 `pyvenv.cfg` 记录 Python 3.12.5，本次验收使用 Python 3.12.14。重新安装 Python 后，先保存 `python --version` 的输出，再在新目录创建虚拟环境并安装依赖：

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

后续直接调用虚拟环境解释器，无需先执行激活脚本。依赖清单包含 `mysqlclient`；即使选用 SQLite，完整安装依赖时也会安装它。如安装失败，应保留完整报错核对 Python 版本与安装条件，目前没有验证可通用的安装替代方案。

### 2. 配置环境变量

新项目目录中可将 [.env.example](.env.example) 复制为 `.env`，再填写自己的配置。已有 `.env` 时保留自己的值，不用示例覆盖。以下全部为示例或源码默认值，不包含真实凭据：

```dotenv
DJANGO_SECRET_KEY=CHANGE_ME_TO_A_RANDOM_LOCAL_SECRET
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DB_ENGINE=sqlite

DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
AGENT_MAX_STEPS=5
AGENT_MEMORY_MESSAGES=16
```

- `DJANGO_SECRET_KEY`：替换为自己生成的随机值；上面的占位值仅用于说明配置格式。
- `DEEPSEEK_API_KEY`：需要真实调用 AI 时填写服务商提供的密钥，由服务端读取。留空时，未命中解析缓存的 AI 请求会进入未配置错误分支；普通博客页面不以该密钥为启动前提。
- `DB_ENGINE=sqlite`：数据库路径固定为项目根目录 `db.sqlite3`。
- 使用 MySQL 时，设置 `DB_ENGINE=mysql`，并填写 `DB_NAME`、`DB_USER`、`DB_PASSWORD`、`DB_HOST`、`DB_PORT`。MySQL 分支本次未连接验证。
- 邮件与天气等附属功能另有配置项，未列入本次核心演示范围。

`.env.example` 是可公开的占位模板，真实密钥只填入本机 `.env`。以上配置用于本地开发。

### 3. 初始化并启动

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

`migrate` 会操作当前配置指向的数据库；复现时使用自己的开发数据库。新数据库没有原作者的文章，需要先注册并创建演示文章。

| 页面 | 本地路径 |
| --- | --- |
| 首页 | `http://127.0.0.1:8000/` |
| 注册 | `/accounts/register/` |
| 登录 | `/accounts/login/` |
| 新建文章 | `/article/new/` |
| Agent 页面 | `/chat/` |

管理员账号可按需通过 `manage.py createsuperuser` 创建。本次已验证隔离环境启动、现有迁移、测试账号登录与文章详情访问；账号由验收脚本建立，没有覆盖注册页面流程。

## 测试与演示

现有 [tests_agent.py](blogapp/tests_agent.py) 包含 8 个测试方法，涉及检索、文章目录、零命中提示、Skill 选择、草稿授权、工具调用记录和接口响应。模型相关测试使用 FakeClient 或 mock，不等于真实服务接入验证。

```powershell
.\.venv\Scripts\python.exe manage.py test blogapp.tests_agent -v 2
```

**执行结果：2026 年 10 月 13 日，隔离环境中 8/8 通过，退出码 0。** 见 [原始测试输出](docs/verification/2026-10-13/agent-tests.txt)。检查出现 `ckeditor.W001` 警告，未处理。当前没有覆盖率或性能基准数据，也没有真实 Agent 多步调用验收结果。

建议演示顺序：打开首页和文章详情 → 登录并展示文章编辑 → 对没有解析缓存的新文章发起 AI 解析 → 再次解析检查缓存 → 按实际验证情况选演 Agent。控制在约 3 分钟；发生错误时记录现象，不将其剪辑成成功结果。

文章解析的逐项验收步骤和结果记录表见 [AI 编码实例](docs/AI_CODING_CASE.md)。

## 当前边界与源码审查发现

以下列明已复现问题与尚未验证的源码发现；业务代码均未在本次验收中修复：

1. **解析缓存更新，已复现**：正文实际更新后，接口仍返回旧 reply 和 `cached=true`，没有重新调用模型。
2. **解析失败后的页面状态，已复现**：匿名访问返回登录 HTML、空密钥返回 503 JSON 时，前端都显示通用错误且按钮持续禁用。输出中部分 Markdown 格式也未正常展示。
3. **文章编辑权限**：编辑视图检查登录，但在该函数中未见文章作者所有权校验，需要以不同账号核验对象权限。
4. **Agent 工具边界**：Skill 会过滤提供给模型的工具集合；执行器检查全局工具注册表，未再次检查当前 Skill 的工具范围。草稿工具另有登录与写入授权检查。
5. **部署与工程验证**：当前材料未建立 Docker 部署、CI、线上运行、压力测试或完整安全测试的证据，不作相应完成声明。
6. **公开仓库资源范围**：本地数据库、上传文件和音乐 MP3 不随源码提交。新环境需要创建测试文章；音乐播放需要自行提供音频，默认头像等媒体也需自行准备。

## 个人贡献与材料使用

个人参与包括需求提出、功能规划、迭代调试、问题定位与 API 使用探索。详细说明见 [个人贡献](docs/CONTRIBUTIONS.md)，开发协作方式与验证过程见 [开发实例](docs/AI_CODING_CASE.md)。

公开源码前，核对提交内容中是否含凭据、个人数据与上传文件。当前 `.gitignore` 已列出 `.env`、`.venv/`、`media/` 和 `*.sqlite3` 等规则；规则存在不代表历史记录已经完成检查。项目演示使用测试账号与示例文章。
