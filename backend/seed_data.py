"""Seed data for the tongshi AI course platform"""
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.entities import User, Chapter, Material, Question, Project, ActivityEvent


def seed():
    db = SessionLocal()

    # ── Users ────────────────────────────────────────────────────────────────
    if db.query(User).count() == 0:
        users = [
            User(id="2025001", name="张同学", hashed_password=get_password_hash("123456"), role="student", major="自动化专业"),
            User(id="2025002", name="李同学", hashed_password=get_password_hash("123456"), role="student", major="机械工程"),
            User(id="2025003", name="王同学", hashed_password=get_password_hash("123456"), role="student", major="测控技术"),
            User(id="2025004", name="陈同学", hashed_password=get_password_hash("123456"), role="student", major="电气工程"),
            User(id="2025005", name="刘同学", hashed_password=get_password_hash("123456"), role="student", major="材料科学"),
            User(id="T001", name="赵老师", hashed_password=get_password_hash("123456"), role="teacher", major=""),
        ]
        db.add_all(users)
        db.commit()
        print("  Users seeded")

    # ── Chapters ─────────────────────────────────────────────────────────────
    if db.query(Chapter).count() == 0:
        chapters = [
            Chapter(num="01", title="人工智能概述", desc="从图灵测试到深度学习，AI 发展全景扫描", topics=["AI 发展简史", "主要流派与学派", "关键里程碑事件", "中国 AI 发展"], status="已发布", sort_order=1),
            Chapter(num="02", title="计算机基础知识", desc="办公软件使用基础与计算思维入门", topics=["计算思维", "数据表示与运算", "办公软件基础", "信息安全入门"], status="已发布", sort_order=2),
            Chapter(num="03", title="AI 理论基础", desc="深度学习、大模型原理与核心算法", topics=["机器学习基础", "神经网络原理", "大模型架构", "Transformer 详解"], status="已发布", sort_order=3),
            Chapter(num="04", title="AI 工具使用", desc="大模型、智能体应用及简单开发实践", topics=["Prompt 工程", "AI Agent 开发", "API 调用实战", "Gradio 快速上手"], status="即将发布", sort_order=4),
            Chapter(num="05", title="AI 前沿与应用", desc="结合专业的前沿应用场景探索", topics=["AI + 医疗", "AI + 制造", "AI + 艺术", "AI + 科研"], status="即将发布", sort_order=5),
            Chapter(num="06", title="AI 伦理与未来", desc="技术向善，负责任的人工智能发展之路", topics=["算法偏见", "数据隐私", "AI 安全", "人机协作的未来"], status="即将发布", sort_order=6),
        ]
        db.add_all(chapters)
        db.commit()
        print("  Chapters seeded")

    # ── Materials ────────────────────────────────────────────────────────────
    if db.query(Material).count() == 0:
        ch_map = {ch.num: ch.id for ch in db.query(Chapter).all()}
        materials = [
            Material(chapter_id=ch_map["01"], type="video", title="AI 发展简史（上）", duration="12:30", size="128 MB", date="2026-03-01"),
            Material(chapter_id=ch_map["01"], type="video", title="图灵测试与机器智能", duration="08:45", size="95 MB", date="2026-03-02"),
            Material(chapter_id=ch_map["01"], type="pdf", title="AI 发展大事记", pages=15, size="2.4 MB", date="2026-03-03"),
            Material(chapter_id=ch_map["02"], type="video", title="计算思维导论", duration="15:20", size="110 MB", date="2026-03-10"),
            Material(chapter_id=ch_map["02"], type="pdf", title="数据表示与运算", pages=22, size="3.1 MB", date="2026-03-11"),
            Material(chapter_id=ch_map["03"], type="video", title="机器学习基础概念", duration="18:00", size="145 MB", date="2026-04-01"),
            Material(chapter_id=ch_map["03"], type="video", title="神经网络原理详解", duration="20:15", size="160 MB", date="2026-04-05"),
            Material(chapter_id=ch_map["03"], type="pdf", title="Transformer 架构图解", pages=30, size="5.2 MB", date="2026-04-06"),
        ]
        db.add_all(materials)
        db.commit()
        print("  Materials seeded")

    # ── Questions ────────────────────────────────────────────────────────────
    if db.query(Question).count() == 0:
        ch_map = {ch.num: ch.id for ch in db.query(Chapter).all()}
        questions = [
            Question(type="choice", chapter_id=ch_map["01"], stem="图灵测试由谁提出？", options=["A. 艾伦·图灵", "B. 约翰·麦卡锡", "C. 马文·明斯基", "D. 杰弗里·辛顿"], answer="A", explanation="图灵测试由英国数学家艾伦·图灵于1950年提出。"),
            Question(type="choice", chapter_id=ch_map["01"], stem="「人工智能」一词最早在哪一年被提出？", options=["A. 1946", "B. 1950", "C. 1956", "D. 1960"], answer="C", explanation="1956年达特茅斯会议首次提出「人工智能」这一术语。"),
            Question(type="fill", chapter_id=ch_map["01"], stem="请填写：AI 的英文全称是 ______。", answer="Artificial Intelligence", explanation="AI 即 Artificial Intelligence（人工智能）的缩写。"),
            Question(type="choice", chapter_id=ch_map["02"], stem="二进制数 1010 转换为十进制是多少？", options=["A. 8", "B. 10", "C. 12", "D. 14"], answer="B", explanation="1010 = 1×8 + 0×4 + 1×2 + 0×1 = 10。"),
            Question(type="fill", chapter_id=ch_map["02"], stem="请填写：计算思维的四大支柱是分解、模式识别、抽象和 ______。", answer="算法", explanation="计算思维四大支柱：分解、模式识别、抽象、算法。"),
            Question(type="choice", chapter_id=ch_map["03"], stem="以下哪个不是常见的机器学习类型？", options=["A. 监督学习", "B. 无监督学习", "C. 强化学习", "D. 递归学习"], answer="D", explanation="常见机器学习类型为监督学习、无监督学习和强化学习。"),
            Question(type="choice", chapter_id=ch_map["03"], stem="Transformer 架构的核心机制是什么？", options=["A. 循环神经网络", "B. 卷积神经网络", "C. 自注意力机制", "D. 决策树"], answer="C", explanation="Transformer 基于自注意力（Self-Attention）机制。"),
            Question(type="fill", chapter_id=ch_map["03"], stem="请填写：神经网络中常用的激活函数 ReLU 的全称是 ______。", answer="Rectified Linear Unit", explanation="ReLU 即 Rectified Linear Unit，f(x) = max(0, x)。"),
            Question(type="choice", chapter_id=ch_map["03"], stem="深度学习中的「反向传播」算法主要用于什么？", options=["A. 数据预处理", "B. 模型推理", "C. 计算梯度更新权重", "D. 选择超参数"], answer="C", explanation="反向传播算法通过链式法则计算损失函数对各层权重的梯度。"),
            Question(type="fill", chapter_id=ch_map["03"], stem="请填写：GPT 中的 G 代表 ______。", answer="Generative", explanation="GPT = Generative Pre-trained Transformer。"),
        ]
        db.add_all(questions)
        db.commit()
        print("  Questions seeded")

    # ── Sample projects ──────────────────────────────────────────────────────
    if db.query(Project).count() == 0:
        projects = [
            Project(title="智能分类垃圾桶", author_id="2025001", major="自动化专业", description="基于机器视觉的垃圾分类系统，使用树莓派 + 摄像头模块，调用本地部署的图像识别模型实现四分类。", tags=["树莓派", "机器视觉", "Python"], likes=23, featured=True, status="approved", date="2026-04-10"),
            Project(title="AI 桌面助手机器人", author_id="2025002", major="机械工程", description="接入大模型 API 的桌面机器人，支持语音交互、天气查询、日程提醒，舵机驱动实现表情变化。", tags=["ESP32", "大模型", "语音识别"], likes=18, featured=True, status="approved", date="2026-04-15"),
            Project(title="温室环境智能监控", author_id="2025003", major="测控技术", description="基于多传感器的温室大棚监控系统，温湿度、光照、CO2 数据实时上传，AI 预测最佳灌溉时间。", tags=["传感器", "IoT", "数据可视化"], likes=0, status="pending", date="2026-05-01"),
            Project(title="手势控制机械臂", author_id="2025004", major="电气工程", description="通过摄像头捕捉手势姿态，实时映射到六轴机械臂，实现无接触操控，可完成简单抓取任务。", tags=["Arduino", "MediaPipe", "机械臂"], likes=0, status="pending", date="2026-05-05"),
            Project(title="智能书法教学系统", author_id="2025005", major="材料科学", description="结合压力传感器笔和 AI 书法评估模型，实时分析笔画结构，为初学者提供智能评分和改进建议。", tags=["压力传感", "深度学习", "书法"], likes=0, status="rejected", reject_reason="课程报告缺少实验数据", date="2026-05-08"),
            Project(title="无障碍导航手杖", author_id="2025001", major="自动化专业", description="集成超声波测距和语音反馈的智能手杖，AI 识别障碍物类型并通过振动提示，辅助视障人士出行。", tags=["超声波", "目标检测", "嵌入式"], likes=0, status="pending", date="2026-05-12"),
        ]
        db.add_all(projects)
        db.commit()
        print("  Projects seeded")

    # ── Activity events ──────────────────────────────────────────────────────
    if db.query(ActivityEvent).count() == 0:
        events = [
            ActivityEvent(date="2026年3月", title="课程正式启动", description="AI 通识课平台上线，首批 128 名学生注册"),
            ActivityEvent(date="2026年4月", title="首次作品提交", description="同学们陆续提交 AI 项目作品，涵盖机器视觉、语音交互等方向"),
            ActivityEvent(date="2026年5月", title="作品审核进行中", description="教师团队开始审核学生提交的项目作品"),
        ]
        db.add_all(events)
        db.commit()
        print("  Activity events seeded")

    db.close()
    print("Seed complete!")


if __name__ == "__main__":
    seed()
