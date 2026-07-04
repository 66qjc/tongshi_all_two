"""
本地演示数据填充脚本。

用法：
    cd backend
    py mock_demo_data.py

说明：
- 仅用于本地开发环境展示完整流程。
- 会创建/更新管理员、教师、学生账号，课程、班级、课时、题目、公告、作业、作品、学习进度等数据。
- 不删除已有数据，仅做幂等插入或更新，可重复执行。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.entities import (
    Announcement,
    AnnouncementClass,
    Course,
    CourseStage,
    Class,
    Lesson,
    Material,
    MaterialPreview,
    Project,
    ProjectImage,
    Question,
    QuizAttempt,
    StudentClassEnrollment,
    TaskCompletion,
    User,
    CourseProgress,
)

# 账号信息（本地测试用弱密码）
USERS = {
    "admin": ("系统管理员", "admin", "Admin123"),
    "teacher1": ("张教授", "teacher", "Teacher123"),
    "teacher2": ("李老师", "teacher", "Teacher123"),
    "20210001": ("王小明", "student", "Student123"),
    "20210002": ("李小红", "student", "Student123"),
    "20210003": ("赵小军", "student", "Student123"),
    "20210004": ("孙小燕", "student", "Student123"),
    "20210005": ("周小杰", "student", "Student123"),
}

COURSES = [
    # (name, created_by, is_public, description)
    ("人工智能通识导论", "admin", True, "面向全校本科生的人工智能通识基础课程，涵盖机器学习、深度学习、计算机视觉与自然语言处理等前沿领域的入门知识，帮助学生建立 AI 思维框架。"),
    ("Python 程序设计", "teacher1", False, "零基础 Python 编程入门与实践课程，从环境搭建到面向对象编程，配合丰富的实战案例，让编程学习轻松有趣。"),
    ("机器学习初探", "teacher1", False, "面向高年级本科生的机器学习入门课程，系统讲解监督学习、无监督学习、特征工程与模型评估，使用 scikit-learn 进行实战演练。"),
    ("数据科学基础", "teacher2", False, "以 Python 为核心工具，系统学习数据采集、清洗、分析和可视化的完整流程，培养数据驱动的决策思维。"),
]

# 课程资料分类与资料（主结构）
# 每个课程有 stages（阶段/分类）+ materials
COURSE_MATERIALS = {
    "人工智能通识导论": {
        "stages": [
            {"name": "第一章：人工智能概述", "sort_order": 1},
            {"name": "第二章：机器学习基础", "sort_order": 2},
            {"name": "第三章：深度学习入门", "sort_order": 3},
            {"name": "第四章：AI 伦理与未来", "sort_order": 4},
        ],
        "materials": [
            # (type, title, url, size, duration, stage_index, summary, page_count)
            ("pdf", "人工智能导论课件 - 什么是 AI", "", "8.5 MB", "", 0,
             "本课件系统介绍人工智能的定义、发展简史和主要研究领域，包括图灵测试、符号主义与连接主义的对比，以及当前 AI 技术的应用场景概览。", 52),
            ("video", "AI 简史：从图灵到 GPT", "https://example.com/ai-history.mp4", "156 MB", "28:45", 0,
             "一部 30 分钟的科普纪录片，讲述人工智能从 1950 年图灵论文到现代大语言模型的发展历程，穿插关键人物和里程碑事件。", 0),
            ("link", "斯坦福 CS229 机器学习课程（参考链接）", "https://cs229.stanford.edu/", "", "", 0,
             "斯坦福大学经典机器学习课程 CS229，吴恩达主讲，涵盖线性回归、逻辑回归、SVM、神经网络等核心主题。适合有线性代数基础的学生深入学习。", 0),
            ("pdf", "机器学习核心算法详解", "", "12.3 MB", "", 1,
             "详细讲解监督学习（线性回归、逻辑回归、决策树、SVM）和无监督学习（K-Means、PCA、DBSCAN）的核心算法原理、数学推导与优缺点对比。", 78),
            ("video", "决策树与随机森林实战", "https://example.com/decision-tree.mp4", "245 MB", "42:10", 1,
             "从信息熵和信息增益出发，手推决策树建树过程，再引入 Bagging 和随机森林，配合 scikit-learn 代码演示，带你从原理到实战完整掌握。", 0),
            ("pdf", "深度学习与神经网络入门", "", "15.7 MB", "", 2,
             "从感知机到多层神经网络，涵盖激活函数（ReLU、Sigmoid、Tanh）、反向传播算法推导、CNN 卷积原理、RNN/LSTM 序列建模，以及 PyTorch 基础实战。附有大量图示和代码片段。", 96),
            ("video", "CNN 卷积神经网络可视化讲解", "https://example.com/cnn-visual.mp4", "188 MB", "35:22", 2,
             "通过动画直观展示卷积操作的每一步：卷积核滑动、特征图生成、池化降维，让你真正看懂 CNN 在看什么。", 0),
            ("link", "动手学深度学习（D2L）在线书", "https://zh.d2l.ai/", "", "", 2,
             "李沐等人的开源教材，配套 PyTorch/MXNet/TensorFlow 三版本代码，从线性代数基础到 Transformer，覆盖深度学习全栈知识。", 0),
            ("pdf", "AI 伦理与社会影响白皮书", "", "4.2 MB", "", 3,
             "讨论算法偏见、数据隐私、深度伪造、自主武器等 AI 伦理热点议题，结合欧盟 AI 法案和中国人工智能治理框架，培养负责任的 AI 开发者意识。内含课堂讨论题 20 道。", 34),
            ("video", "AI 的未来：机遇与挑战", "https://example.com/ai-future.mp4", "98 MB", "18:55", 3,
             "业界专家圆桌讨论：AGI 离我们有多远？AI 会取代哪些工作？我们该如何准备？", 0),
        ],
    },
    "Python 程序设计": {
        "stages": [
            {"name": "第一部分：入门基础", "sort_order": 1},
            {"name": "第二部分：核心语法", "sort_order": 2},
            {"name": "第三部分：进阶实战", "sort_order": 3},
        ],
        "materials": [
            # 保留原 3 条 + 大量新增
            ("video", "Python 入门视频", "https://example.com/python-intro.mp4", "320 MB", "15:30", 0,
             "从零开始学 Python：安装 Python 和 VS Code、运行第一个 Hello World 程序，了解 Python 的基本语法规则和交互式编程环境。", 0),
            ("pdf", "Python 基础讲义", "", "10 MB", "", 0,
             "精心整理的 Python 入门讲义，涵盖变量、数据类型、运算符、字符串处理等基础知识。每章附有课后练习和参考答案。", 45),
            ("link", "Python 官方教程（中文）", "https://docs.python.org/zh-cn/3/tutorial/", "", "", 0,
             "Python 官方文档的中文翻译版教程，最权威的 Python 学习参考资料。推荐遇到问题时优先查阅。", 0),
            ("pdf", "Python 控制流程与函数设计", "", "6.8 MB", "", 1,
             "深入讲解 if-elif-else、for/while 循环、列表推导式、函数定义与参数传递（位置参数、关键字参数、默认参数、可变参数），以及 lambda 匿名函数的妙用。", 38),
            ("video", "30分钟搞懂 Python 面向对象编程", "https://example.com/python-oop.mp4", "210 MB", "32:18", 1,
             "从类和对象的概念出发，逐步讲解封装、继承、多态三大特性，通过一个完整的图书管理系统案例让你真正理解 OOP 的精髓。", 0),
            ("link", "Python 编码规范 PEP 8 中文版", "https://pep8.org/", "", "", 1,
             "Python 官方编码风格指南：变量命名规范、缩进规则、注释写法、import 排序等。写出优雅 Python 代码的必修课。", 0),
            ("pdf", "Python 数据处理与可视化实战", "", "9.5 MB", "", 2,
             "手把手教你用 Pandas 处理 CSV/Excel 数据、用 Matplotlib 和 Seaborn 绘制专业图表。包含 10 个真实数据集的分析案例：电影票房分析、气候数据可视化、电商用户行为分析等。", 62),
            ("video", "Pandas 数据处理全流程", "https://example.com/pandas-tutorial.mp4", "450 MB", "55:40", 2,
             "2 小时完整 Pandas 教程：DataFrame 创建与索引、数据筛选与排序、分组聚合（groupby）、数据透视表、缺失值处理，以及一个完整的 Kaggle Titanic 数据集分析实战。", 0),
            ("link", "Real Python 教程网站", "https://realpython.com/", "", "", 2,
             "国外高质量 Python 教程网站，文章深入浅出，覆盖 Web 开发、数据科学、DevOps 等方向。英文阅读能力好的同学强烈推荐。", 0),
            ("pdf", "Python 常见错误与调试技巧", "", "3.1 MB", "", 2,
             "收集初学者最常见的 50 个 Python 错误（IndentationError、NameError、TypeError 等），逐一分析原因并提供解决方案。附录包含 VS Code 调试器使用指南和 logging 日志最佳实践。", 28),
        ],
    },
    "机器学习初探": {
        "stages": [
            {"name": "理论篇：算法原理", "sort_order": 1},
            {"name": "实战篇：项目演练", "sort_order": 2},
        ],
        "materials": [
            ("pdf", "机器学习数学基础复习", "", "7.2 MB", "", 0,
             "机器学习必备数学知识速查：线性代数（矩阵运算、特征值与特征向量）、概率论（贝叶斯定理、期望与方差）、微积分（梯度与偏导数）。每节配有 ML 场景应用示例。", 44),
            ("video", "从零推导线性回归", "https://example.com/linear-regression.mp4", "175 MB", "26:40", 0,
             "不使用任何框架，从损失函数定义出发，用最小二乘法和梯度下降法两种方式推导线性回归的参数求解。所有数学公式都有直观的可视化解释。", 0),
            ("pdf", "scikit-learn 实战手册", "", "11.8 MB", "", 0,
             "完整覆盖 scikit-learn 核心 API：数据预处理（标准化、编码、特征选择）、分类器（KNN、SVM、随机森林）、回归器、聚类、交叉验证与网格搜索调参。每个方法都配有可运行的代码示例。", 88),
            ("video", "Kaggle 入门：泰坦尼克号生存预测", "https://example.com/kaggle-titanic.mp4", "380 MB", "48:15", 1,
             "跟随 Kaggle 最经典的入门竞赛：从数据探索（EDA）开始，进行特征工程（缺失值填充、类别编码、特征交叉），然后尝试多种模型（逻辑回归→决策树→随机森林→XGBoost），最终提交预测结果并分析排名。", 0),
            ("pdf", "模型评估与调参指南", "", "5.6 MB", "", 1,
             "彻底搞懂混淆矩阵、准确率/精确率/召回率/F1-score、ROC/AUC 曲线、学习曲线和验证曲线。Grid Search vs Random Search vs Bayesian Optimization 三种调参策略的优缺点对比。", 36),
            ("link", "Kaggle 竞赛平台", "https://www.kaggle.com/", "", "", 1,
             "全球最大的数据科学竞赛平台，提供免费 GPU、海量公开数据集和社区 Notebook。学完本课程后推荐来这里练手。", 0),
        ],
    },
    "数据科学基础": {
        "stages": [
            {"name": "数据采集与清洗", "sort_order": 1},
            {"name": "数据分析与建模", "sort_order": 2},
            {"name": "可视化与报告", "sort_order": 3},
        ],
        "materials": [
            ("pdf", "数据采集方法论", "", "8.9 MB", "", 0,
             "系统介绍数据采集的多种方式：Web 爬虫（requests + BeautifulSoup）、API 调用（RESTful/GraphQL）、数据库查询（SQL），以及结构化/半结构化/非结构化数据的解析技巧。附有知乎、微博、GitHub API 的爬取示例。", 56),
            ("video", "Python 网络爬虫从入门到实战", "https://example.com/web-scraping.mp4", "290 MB", "40:30", 0,
             "讲解 HTTP 协议基础、requests 库使用、BeautifulSoup 解析 HTML、XPath 定位元素、反爬虫策略应对（User-Agent、Cookie、代理 IP），最后爬取豆瓣电影 Top250 保存为 CSV。", 0),
            ("link", "Requests 库官方文档", "https://docs.python-requests.org/", "", "", 0,
             "Python 最流行的 HTTP 库，API 设计优雅简洁，是学习网络请求的最佳起点。", 0),
            ("pdf", "Pandas 数据分析完全指南", "", "13.4 MB", "", 1,
             "从 DataFrame 基本操作到高级数据变换：merge/join/concat 表连接、apply/map 函数式操作、时间序列处理、多层索引，以及一个完整的电商用户 RFM 分析案例。配有 30+ 练习和答案。", 102),
            ("video", "统计分析基础与 Python 实现", "https://example.com/stats-python.mp4", "256 MB", "45:10", 1,
             "覆盖描述性统计（均值/中位数/方差/分位数）、假设检验（t 检验/卡方检验）、相关性分析（Pearson/Spearman）、方差分析（ANOVA），全部用 scipy 和 statsmodels 实现。", 0),
            ("pdf", "数据可视化最佳实践", "", "6.3 MB", "", 2,
             "从可视化设计原则（数据墨水比、视觉层级、颜色选择）到具体工具：Matplotlib 精细控制、Seaborn 统计图表、Plotly 交互式可视化。包含 20 个可复用的图表模板，覆盖折线图、柱状图、散点图、热力图、箱线图等常见图表类型。", 48),
            ("video", "用 ECharts 打造炫酷数据大屏", "https://example.com/echarts-dashboard.mp4", "310 MB", "52:00", 2,
             "从零搭建一个企业级数据大屏：布局设计、ECharts 图表配置、动态数据刷新、响应式适配。项目源码随视频提供下载。", 0),
            ("link", "ECharts 官方示例库", "https://echarts.apache.org/examples/", "", "", 2,
             "Apache ECharts 官方提供的 200+ 图表示例，可直接在线修改配置并预览效果，是数据可视化开发的宝藏资源。", 0),
        ],
    },
}


def ensure_users(db: SessionLocal):
    """创建或更新演示账号。"""
    for uid, (name, role, pwd) in USERS.items():
        user = db.query(User).filter(User.id == uid).first()
        if not user:
            user = User(id=uid)
            db.add(user)
        user.name = name
        user.role = role
        user.hashed_password = get_password_hash(pwd)
        user.major = "计算机学院" if role != "student" else _student_major(name)
        user.needs_password_change = False
    db.commit()
    print("[ok] 账号数据已准备")


def _student_major(name):
    mapping = {
        "王小明": "计量测试工程学院",
        "李小红": "信息工程学院",
        "赵小军": "质量与安全工程学院",
        "孙小燕": "理学院",
        "周小杰": "机电工程学院",
    }
    return mapping.get(name, "其他学院")


def ensure_courses(db: SessionLocal):
    """创建或查找演示课程。"""
    result = []
    for name, created_by, is_public, desc in COURSES:
        course = db.query(Course).filter(
            Course.name == name, Course.created_by == created_by
        ).first()
        if not course:
            course = Course(name=name, created_by=created_by,
                            description=desc, is_public=is_public)
            db.add(course)
            db.flush()
        course.description = desc
        course.is_public = is_public
        result.append(course)
    db.commit()
    print("[ok] 课程数据已准备")
    return result


def ensure_classes(db: SessionLocal, courses: list):
    """创建或查找演示班级。"""
    class_config = [
        ("计测 2301 班", "teacher1", "Python 程序设计"),
        ("计测 2302 班", "teacher1", "Python 程序设计"),
        ("计测 2303 班", "teacher1", "机器学习初探"),
        ("信息 2301 班", "teacher2", "数据科学基础"),
        ("信息 2302 班", "teacher2", "数据科学基础"),
    ]
    student_map = {
        "teacher1": ["20210001", "20210002", "20210003"],
        "teacher2": ["20210003", "20210004", "20210005"],
    }
    result = []
    for name, teacher_id, course_name in class_config:
        course = next((c for c in courses if c.name == course_name), None)
        if not course:
            continue
        cls = db.query(Class).filter(
            Class.name == name, Class.course_id == course.id, Class.created_by == teacher_id
        ).first()
        if not cls:
            cls = Class(name=name, course_id=course.id, created_by=teacher_id)
            db.add(cls)
            db.flush()
        students = student_map.get(teacher_id, [])
        for i, sid in enumerate(students):
            enroll = db.query(StudentClassEnrollment).filter(
                StudentClassEnrollment.class_id == cls.id,
                StudentClassEnrollment.user_id == sid,
            ).first()
            if not enroll:
                db.add(StudentClassEnrollment(
                    class_id=cls.id,
                    user_id=sid,
                    import_order=i + 1,
                ))
        result.append(cls)
    db.commit()
    print("[ok] 班级及学生已注册")
    return result


def ensure_lessons(db: SessionLocal, courses: list):
    """创建课时与进度（覆盖所有课程）。"""
    lessons_config = {
        "Python 程序设计": [
            ("第 1 课时：Python 概览与环境搭建",
             "<p>欢迎来到 Python 程序设计课程！本节课我们将：</p>"
             "<ul><li>了解 Python 语言的特点和应用领域</li>"
             "<li>安装 Python 3.11+ 和 VS Code 编辑器</li>"
             "<li>运行你的第一个 Python 程序 <code>print('Hello, World!')</code></li>"
             "<li>掌握交互式解释器和 .py 脚本的基本用法</li></ul>"
             "<p>Python 是一门解释型、面向对象的高级编程语言，由 Guido van Rossum 于 1991 年发布。"
             "其设计哲学强调代码的可读性和简洁的语法，被誉为『可执行的伪代码』。</p>"
             "<p>Python 广泛应用于 Web 开发（Django/Flask）、数据科学（NumPy/Pandas）、"
             "人工智能与机器学习（PyTorch/TensorFlow）、自动化运维等领域。</p>",
             "published", 1),
            ("第 2 课时：变量与数据类型",
             "<p>本节课学习 Python 的变量和基本数据类型：</p>"
             "<ul><li>变量命名规则与赋值</li><li>数字类型：int、float、complex</li>"
             "<li>字符串 str：索引、切片、格式化</li><li>布尔值 bool 与 NoneType</li></ul>"
             "<p>Python 是动态类型语言，变量不需要声明类型，解释器会自动推断。"
             "但要特别注意类型转换时的潜在错误，如 <code>int('abc')</code> 会抛出 ValueError。</p>",
             "published", 2),
            ("第 3 课时：条件与循环",
             "<p>控制流程是编程的核心，本节课学习：</p>"
             "<ul><li>if-elif-else 条件判断</li><li>for 循环与 while 循环</li>"
             "<li>break、continue、pass 关键字</li><li>列表推导式的妙用</li></ul>"
             "<p>实战练习：编写一个猜数字游戏，用户有 5 次机会猜中 1~100 的随机数。</p>",
             "published", 3),
            ("第 4 课时：函数与模块",
             "<p>函数是代码复用的基本单元：</p>"
             "<ul><li>函数定义与调用</li><li>参数类型：位置参数、关键字参数、默认参数、*args、**kwargs</li>"
             "<li>返回值与作用域</li><li>模块导入与包管理（pip）</li></ul>"
             "<p>课后练习：编写一个计算器模块，包含加减乘除四个函数，支持任意多个参数的求和求积。</p>",
             "published", 4),
            ("第 5 课时：面向对象编程（未发布）",
             "<p>本课时为进阶内容，目前还在备课中，敬请期待～</p>",
             "draft", 5),
        ],
        "机器学习初探": [
            ("第 1 课时：什么是机器学习",
             "<p>机器学习是人工智能的核心分支，让计算机从数据中自动学习规律。本节课内容包括：</p>"
             "<ul><li>机器学习的定义与分类（监督学习/无监督学习/强化学习）</li>"
             "<li>传统编程 vs 机器学习的区别</li><li>机器学习项目的基本流程</li></ul>"
             "<p>生活中的 ML 应用：推荐系统（抖音/B站）、语音助手（Siri/小爱）、人脸识别、垃圾邮件过滤。</p>",
             "published", 1),
            ("第 2 课时：线性回归详解",
             "<p>线性回归是最基础也最重要的监督学习算法：</p>"
             "<ul><li>一元线性回归的数学推导</li><li>损失函数（均方误差 MSE）</li>"
             "<li>梯度下降法求解最优参数</li><li>用 scikit-learn 实现线性回归</li></ul>"
             "<p>案例：根据房屋面积预测房价，使用波士顿房价数据集。</p>",
             "published", 2),
            ("第 3 课时：分类算法入门",
             "<p>分类是监督学习的核心任务之一：</p>"
             "<ul><li>逻辑回归与 Sigmoid 函数</li><li>K 近邻算法（KNN）</li><li>决策树与信息增益</li>"
             "<li>模型评估：混淆矩阵、精确率、召回率</li></ul>",
             "published", 3),
        ],
        "数据科学基础": [
            ("第 1 课时：数据科学概述",
             "<p>数据科学是 21 世纪最性感的职业！本节课了解：</p>"
             "<ul><li>数据科学家的日常工作与技能栈</li><li>数据科学项目生命周期</li>"
             "<li>Python 数据科学生态（NumPy、Pandas、Matplotlib、Jupyter）</li></ul>"
             "<p>准备好了吗？让我们一起踏入数据的世界！</p>",
             "published", 1),
            ("第 2 课时：Pandas 入门",
             "<p>Pandas 是 Python 数据分析的核心库：</p>"
             "<ul><li>Series 和 DataFrame 数据结构</li><li>数据读取（CSV/Excel/JSON/SQL）</li>"
             "<li>数据筛选、排序与基本统计</li><li>缺失值处理策略</li></ul>",
             "published", 2),
        ],
    }
    for course in courses:
        if course.name not in lessons_config:
            continue
        for title, content, status, order in lessons_config[course.name]:
            lesson = db.query(Lesson).filter(
                Lesson.course_id == course.id, Lesson.title == title
            ).first()
            if not lesson:
                lesson = Lesson(
                    course_id=course.id,
                    title=title,
                    content=content,
                    status=status,
                    sort_order=order,
                )
                db.add(lesson)
                db.flush()
    db.commit()
    print("[ok] 课时数据已准备")


def ensure_stages_and_materials(db: SessionLocal, courses: list):
    """创建课程分类（CourseStage）和资料（Material + MaterialPreview）。"""
    today = datetime.now().strftime("%Y-%m-%d")

    for course in courses:
        course_config = COURSE_MATERIALS.get(course.name)
        if not course_config:
            continue

        # 创建 Stage（分类/章节）
        stage_objs = []
        for stage_info in course_config.get("stages", []):
            stage = db.query(CourseStage).filter(
                CourseStage.course_id == course.id,
                CourseStage.name == stage_info["name"],
            ).first()
            if not stage:
                stage = CourseStage(
                    course_id=course.id,
                    name=stage_info["name"],
                    sort_order=stage_info["sort_order"],
                )
                db.add(stage)
                db.flush()
            stage_objs.append(stage)

        # 创建 Material + MaterialPreview
        for mat_info in course_config.get("materials", []):
            type_, title, url, size, duration, stage_idx, summary, page_count = mat_info

            stage_id = None
            if stage_idx is not None and stage_idx < len(stage_objs):
                stage_id = stage_objs[stage_idx].id

            mat = db.query(Material).filter(
                Material.course_id == course.id,
                Material.title == title,
                Material.type == type_,
            ).first()
            if not mat:
                mat = Material(
                    course_id=course.id,
                    type=type_,
                    title=title,
                    url=url,
                    duration=duration,
                    size=size,
                    date=today,
                    stage_id=stage_id,
                )
                db.add(mat)
                db.flush()
            else:
                # 更新已有资料的字段
                mat.stage_id = stage_id
                if url:
                    mat.url = url
                if duration:
                    mat.duration = duration
                if size:
                    mat.size = size

            # 创建/更新 MaterialPreview
            preview = db.query(MaterialPreview).filter(
                MaterialPreview.material_id == mat.id
            ).first()
            if not preview:
                status = "ready" if summary else "pending"
                resolution = None
                duration_seconds = None
                if type_ == "video":
                    resolution = "1920x1080"
                    # 解析 duration 字符串为秒（如 "42:10" -> 2530）
                    if duration:
                        parts = duration.split(":")
                        if len(parts) == 2:
                            try:
                                duration_seconds = int(parts[0]) * 60 + int(parts[1])
                            except ValueError:
                                pass

                preview = MaterialPreview(
                    material_id=mat.id,
                    status=status,
                    summary=summary or "",
                    page_count=page_count,
                    duration_seconds=duration_seconds or 0,
                    resolution=resolution or "",
                )
                db.add(preview)

    db.commit()
    print("[ok] 课程分类与资料数据已准备")


def ensure_questions(db: SessionLocal, courses: list):
    """创建题库。"""
    # 优先挂到公共课，让全站共享题库更有真实感
    course = next(c for c in courses if c.name == "人工智能通识导论")
    questions_data = [
        ("choice", "Python 中用于输出内容的函数是？", ["printf", "console.log", "print", "echo"], "C", "Python 内置 print() 函数用于输出。"),
        ("choice", "以下哪个是 Python 的合法变量名？", ["2name", "_name", "my-name", "class"], "B", "下划线开头的标识符在 Python 中合法，且不能是关键字。"),
        ("fill", "机器学习中的 KNN 指的是 _____ 。", [], "K近邻算法", "KNN 即 K-Nearest Neighbors 算法。"),
        ("multi_choice", "下列哪些是 Python 的内置数据类型？", ["list", "dict", "tuple", "object"], "ABC", "list、dict、tuple 均为 Python 内置类型。"),
        ("choice", "AI 的发展阶段不包括？", ["弱人工智能", "强人工智能", "超人工智能", "伪人工智能"], "D", "常见分类为弱、强、超人工智能。"),
    ]
    for q_type, stem, options, answer, explanation in questions_data:
        q = db.query(Question).filter(
            Question.stem == stem, Question.type == q_type
        ).first()
        if not q:
            q = Question(
                type=q_type,
                course_id=course.id,
                stem=stem,
                options=options,
                answer=answer,
                explanation=explanation,
                tags=["演示", "通识"],
            )
            db.add(q)
            db.flush()
    db.commit()
    print("[ok] 题库数据已准备")


def ensure_announcements_and_attempts(db: SessionLocal, courses: list, classes: list):
    """发布作业公告并生成部分学生的答题记录。"""
    course = next(c for c in courses if c.name == "Python 程序设计")
    questions = db.query(Question).filter(Question.course_id ==
                                          next(c.id for c in courses if c.name == "人工智能通识导论")).all()
    target_classes = [c for c in classes if c.course_id == course.id]
    if not questions or not target_classes:
        print("[skip] 缺少题目或班级，跳过作业")
        return

    ann = db.query(Announcement).filter(
        Announcement.title == "Python 第一次小测"
    ).first()
    if not ann:
        ann = Announcement(
            course_id=course.id,
            teacher_id="teacher1",
            type="quiz",
            title="Python 第一次小测",
            content="请完成 2 道选择题练习。",
            question_ids=[questions[0].id, questions[1].id],
            start_time=datetime.now(timezone.utc) - timedelta(days=1),
            end_time=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(ann)
        db.flush()
        for cls in target_classes:
            ac = db.query(AnnouncementClass).filter(
                AnnouncementClass.announcement_id == ann.id,
                AnnouncementClass.class_id == cls.id
            ).first()
            if not ac:
                db.add(AnnouncementClass(announcement_id=ann.id, class_id=cls.id))

    # 生成答题记录
    # 王小明答对 2 题
    _submit_if_missing(db, "20210001", questions[0], questions[0].answer, ann.id)
    _submit_if_missing(db, "20210001", questions[1], questions[1].answer, ann.id)
    # 李小红答对 1 题
    _submit_if_missing(db, "20210002", questions[0], questions[0].options[0], ann.id)
    _submit_if_missing(db, "20210002", questions[1], questions[1].answer, ann.id)
    # 赵小军未完成作业不写记录

    # 课外练习记录（非公告）
    _submit_if_missing(db, "20210001", questions[2], "K近邻算法")
    _submit_if_missing(db, "20210002", questions[3], "ABC")
    _submit_if_missing(db, "20210003", questions[0], "A")

    db.commit()
    print("[ok] 作业公告及答题记录已准备")


def _submit_if_missing(db, user_id, question, user_answer, announcement_id=None):
    """幂等插入答题记录。"""
    exist = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.question_id == question.id,
        QuizAttempt.announcement_id == announcement_id,
    ).first()
    if exist:
        return
    if question.type == "multi_choice":
        ua = "".join(sorted(user_answer.strip().upper()))
        ca = "".join(sorted(question.answer.strip().upper()))
        is_correct = ua == ca
    else:
        is_correct = user_answer.strip().upper() == question.answer.strip().upper()
    db.add(QuizAttempt(
        user_id=user_id,
        question_id=question.id,
        announcement_id=announcement_id,
        user_answer=user_answer,
        is_correct=is_correct,
    ))


def ensure_task_completions(db: SessionLocal):
    """标记王小明的作业完成。"""
    anns = db.query(Announcement).filter(
        Announcement.title == "Python 第一次小测"
    ).all()
    for ann in anns:
        for sid in ["20210001", "20210002"]:
            tc = db.query(TaskCompletion).filter(
                TaskCompletion.announcement_id == ann.id,
                TaskCompletion.user_id == sid,
            ).first()
            if not tc:
                db.add(TaskCompletion(
                    announcement_id=ann.id, user_id=sid))
    db.commit()
    print("[ok] 作业完成状态已准备")


def ensure_projects(db: SessionLocal, courses: list):
    """创建学生作品。"""
    course = next(c for c in courses if c.name == "Python 程序设计")
    projects = [
        ("20210001", "智能垃圾分类助手", "基于 Python 的垃圾分类识别小工具。", ["Python", "实践"]),
        ("20210002", "校园空气质量仪表盘", "实时展示校园 PM2.5 数据的可视化作品。", ["数据可视化", "Python"]),
        ("20210003", "课堂点名小程序", "帮助教师随机点名的 Python 小应用。", ["Python", "工具"]),
    ]
    for author_id, title, desc, tags in projects:
        p = db.query(Project).filter(
            Project.author_id == author_id, Project.title == title
        ).first()
        if not p:
            p = Project(
                author_id=author_id,
                course_id=course.id,
                major=_student_major(User(name="", role="student")),
                title=title,
                description=desc,
                tags=tags,
                date=datetime.now().strftime("%Y-%m-%d"),
                status="pending",
                image_url="",
            )
            db.add(p)
            db.flush()
            # 封面占位图
            if not p.images:
                p.images.append(ProjectImage(
                    image_url="https://via.placeholder.com/640x360?text=Project+Cover",
                    sort_order=0,
                ))
    db.commit()
    print("[ok] 学生作品已准备")


def ensure_progress(db: SessionLocal, courses: list):
    """更新多门课程的学生学习进度。"""
    progress_config = [
        ("Python 程序设计", "第 2 课时：变量与数据类型", ["20210001", "20210002", "20210003"]),
        ("Python 程序设计", "第 3 课时：条件与循环", ["20210001"]),
        ("机器学习初探", "第 1 课时：什么是机器学习", ["20210003", "20210004", "20210005"]),
        ("数据科学基础", "第 1 课时：数据科学概述", ["20210004", "20210005"]),
    ]
    for course_name, lesson_title, student_ids in progress_config:
        course = next((c for c in courses if c.name == course_name), None)
        if not course:
            continue
        lesson = db.query(Lesson).filter(
            Lesson.course_id == course.id,
            Lesson.title == lesson_title,
        ).first()
        if not lesson:
            continue
        for sid in student_ids:
            cp = db.query(CourseProgress).filter(
                CourseProgress.user_id == sid,
                CourseProgress.course_id == course.id,
            ).first()
            if not cp:
                cp = CourseProgress(user_id=sid, course_id=course.id)
                db.add(cp)
            cp.last_lesson_id = lesson.id
    db.commit()
    print("[ok] 学习进度已准备")


def main():
    db = SessionLocal()
    try:
        ensure_users(db)
        courses = ensure_courses(db)
        classes = ensure_classes(db, courses)
        ensure_lessons(db, courses)
        ensure_stages_and_materials(db, courses)
        ensure_questions(db, courses)
        ensure_announcements_and_attempts(db, courses, classes)
        ensure_task_completions(db)
        ensure_projects(db, courses)
        ensure_progress(db, courses)
        print("\n本地演示数据全部准备完成！")
        print("可登录账号：")
        print("  管理员  admin / Admin123")
        print("  教师    teacher1 / Teacher123（张教授，拥有 Python 程序设计 + 机器学习初探 两门课）")
        print("  教师    teacher2 / Teacher123（李老师，拥有 数据科学基础 课程）")
        print("  学生    20210001 / Student123 (王小明)")
        print("  学生    20210002 / Student123 (李小红)")
        print("  学生    20210003 / Student123 (赵小军)")
        print("  学生    20210004 / Student123 (孙小燕)")
        print("  学生    20210005 / Student123 (周小杰)")
        print(f"\n资料统计：")
        for name, config in COURSE_MATERIALS.items():
            v = sum(1 for m in config["materials"] if m[1])
            print(f"  {name}: {len(config['stages'])} 个分类, {v} 个资料")
    finally:
        db.close()


if __name__ == "__main__":
    main()
