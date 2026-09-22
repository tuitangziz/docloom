"""Invented example documents. No personal, customer, or company records."""
DOCUMENTS = {
    "示例-借阅规则.md": """# 星港阅读室 · 虚构演示资料

普通图书借阅期限为 21 天。每位读者最多同时借阅 5 本图书。

图书可以续借一次，续借期限为 14 天。已被其他读者预约的图书不能续借。

阅读室周一闭馆，周二至周日的开放时间为 09:00—20:00。节假日开放时间另行公告。

遗失图书时，请联系服务台登记；本资料没有规定统一赔偿金额。
""",
    "示例-实验室手册.md": """# 松果实验室 · 虚构演示资料

GPU 工作站需要提前 24 小时预约，每次使用时长最多 3 小时。

实验数据必须在离开工作站之前备份到个人存储设备。共享临时目录每周五 18:00 清理。

模型训练完成后应释放显存，并在记录表中填写实验参数和评价指标。不要把访问密钥写进代码仓库。

实验室设备故障时先停止任务，再通知值班管理员。禁止自行拆机。
""",
    "sample-project-notes.txt": """Fictional project: Paper Kite

Paper Kite exports reports as Markdown and JSON. PDF export is planned but not available in version 1.0.

The default upload limit is 15 MiB per file. Supported inputs are PDF, DOCX, Markdown, and UTF-8 text.

The milestone review takes place every second Friday. The team records decisions in a changelog.

This sample contains invented product requirements. It is not a description of a real customer project.
""",
}

CASES = [
    ("普通图书借阅期限", "示例-借阅规则.md", "21 天"),
    ("每位读者最多借阅几本图书", "示例-借阅规则.md", "5 本"),
    ("哪些图书不能续借", "示例-借阅规则.md", "预约"),
    ("阅读室周一开放吗", "示例-借阅规则.md", "闭馆"),
    ("GPU 工作站提前多久预约", "示例-实验室手册.md", "24 小时"),
    ("共享临时目录什么时候清理", "示例-实验室手册.md", "周五"),
    ("实验室设备故障应该怎么办", "示例-实验室手册.md", "停止任务"),
    ("Which formats can Paper Kite export?", "sample-project-notes.txt", "Markdown and JSON"),
    ("What is the upload limit?", "sample-project-notes.txt", "15 MiB"),
    ("When is the milestone review?", "sample-project-notes.txt", "second Friday"),
    ("火星大气中氩气比例", None, None),
    ("quantum chromodynamics gluon scattering", None, None),
]
