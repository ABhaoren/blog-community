from graphviz import Digraph

# 创建 ER 图
dot = Digraph(format='png')
dot.attr(bgcolor='white')
dot.attr('node', shape='record', fontname='Microsoft YaHei', style='filled', fillcolor='#e6f0ff', color='#1a75ff')

# 定义表
dot.node('User', '''{
User|
+ id: int (PK)\\l
+ username: varchar\\l
+ email: varchar\\l
+ password: varchar\\l
+ avatar: image\\l
+ bio: text\\l
+ created_at: datetime\\l
}''')

dot.node('Article', '''{
Article|
+ id: int (PK)\\l
+ author_id: int (FK)\\l
+ title: varchar\\l
+ content: text\\l
+ created_at: datetime\\l
+ category_id: int (FK)\\l
}''')

dot.node('Category', '''{
Category|
+ id: int (PK)\\l
+ name: varchar\\l
}''')

dot.node('Tag', '''{
Tag|
+ id: int (PK)\\l
+ name: varchar\\l
}''')

dot.node('ArticleTag', '''{
ArticleTag|
+ id: int (PK)\\l
+ article_id: int (FK)\\l
+ tag_id: int (FK)\\l
}''')

dot.node('Comment', '''{
Comment|
+ id: int (PK)\\l
+ article_id: int (FK)\\l
+ user_id: int (FK)\\l
+ content: text\\l
+ parent_id: int (FK)\\l
+ created_at: datetime\\l
}''')

dot.node('Notification', '''{
Notification|
+ id: int (PK)\\l
+ recipient_id: int (FK)\\l
+ actor_id: int (FK)\\l
+ verb: varchar\\l
+ target_object_id: int\\l
+ read: bool\\l
+ created_at: datetime\\l
}''')

dot.node('ForumPost', '''{
ForumPost|
+ id: int (PK)\\l
+ author_id: int (FK)\\l
+ title: varchar\\l
+ content: text\\l
+ created_at: datetime\\l
}''')

dot.node('Music', '''{
Music|
+ id: int (PK)\\l
+ title: varchar\\l
+ file_path: varchar\\l
+ uploaded_by: int (FK)\\l
+ created_at: datetime\\l
}''')

dot.node('GameScore', '''{
GameScore|
+ id: int (PK)\\l
+ game_name: varchar\\l
+ user_id: int (FK)\\l
+ score: int\\l
+ created_at: datetime\\l
}''')

# 定义关系
dot.edges([
    ('Article', 'User'),
    ('Article', 'Category'),
    ('ArticleTag', 'Article'),
    ('ArticleTag', 'Tag'),
    ('Comment', 'Article'),
    ('Comment', 'User'),
    ('Comment', 'Comment'),
    ('Notification', 'User'),
    ('ForumPost', 'User'),
    ('Music', 'User'),
    ('GameScore', 'User'),
])

# 保存图像
output_path = "/er_diagram_blue.png"
dot.render(filename=output_path, cleanup=True)

output_path
