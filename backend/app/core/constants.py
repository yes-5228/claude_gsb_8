"""业务枚举与规则常量。"""

from enum import StrEnum


class RestroomStatus(StrEnum):
    NORMAL = "正常开放"
    MAINTENANCE = "维修中"
    CLOSED = "暂停使用"


class RestroomGrade(StrEnum):
    FIRST = "一类"
    SECOND = "二类"
    THIRD = "三类"


class Shift(StrEnum):
    MORNING = "早班"
    MIDDLE = "中班"
    NIGHT = "晚班"


class InspectionResult(StrEnum):
    NORMAL = "正常"
    ABNORMAL = "发现问题"


class IssueCategory(StrEnum):
    CLEANING = "保洁不到位"
    FACILITY = "设施损坏"
    ODOR = "异味扰民"
    CONSUMABLE = "耗材缺失"
    SAFETY = "安全隐患"
    OTHER = "其他"


class IssueSeverity(StrEnum):
    NORMAL = "一般"
    SERIOUS = "严重"
    URGENT = "紧急"


class IssueStatus(StrEnum):
    PENDING = "待整改"
    PROCESSING = "整改中"
    REVIEWING = "待验收"
    DONE = "已完成"
    CLOSED = "已关闭"


# 整改流转规则：当前状态 -> 允许流转到的状态
ISSUE_TRANSITIONS: dict[str, list[str]] = {
    IssueStatus.PENDING: [IssueStatus.PROCESSING, IssueStatus.CLOSED],
    IssueStatus.PROCESSING: [IssueStatus.REVIEWING, IssueStatus.CLOSED],
    IssueStatus.REVIEWING: [IssueStatus.DONE, IssueStatus.PROCESSING],
    IssueStatus.DONE: [IssueStatus.CLOSED],
    IssueStatus.CLOSED: [],
}

# 状态流转对应的动作名称，用于生成整改流水
TRANSITION_ACTIONS: dict[tuple[str, str], str] = {
    (IssueStatus.PENDING, IssueStatus.PROCESSING): "开始整改",
    (IssueStatus.PENDING, IssueStatus.CLOSED): "作废关闭",
    (IssueStatus.PROCESSING, IssueStatus.REVIEWING): "提交验收",
    (IssueStatus.PROCESSING, IssueStatus.CLOSED): "终止关闭",
    (IssueStatus.REVIEWING, IssueStatus.DONE): "验收通过",
    (IssueStatus.REVIEWING, IssueStatus.PROCESSING): "验收驳回",
    (IssueStatus.DONE, IssueStatus.CLOSED): "归档关闭",
}

# 巡查检查项，每项 0-10 分
INSPECTION_CHECK_ITEMS: list[str] = [
    "地面与台阶清洁",
    "便池蹲位清洁",
    "洗手台与镜面",
    "通风除臭",
    "耗材补充",
    "垃圾清运",
    "工具与标识摆放",
    "墙面门窗卫生",
]

INSPECTION_ITEM_MAX_SCORE = 10

GRADE_EXCELLENT = "优秀"
GRADE_GOOD = "良好"
GRADE_PASS = "合格"
GRADE_FAIL = "不合格"

# 仍处于整改闭环中的状态，用于统计未整改问题
OPEN_ISSUE_STATUSES: list[str] = [
    IssueStatus.PENDING,
    IssueStatus.PROCESSING,
    IssueStatus.REVIEWING,
]

# 单检查项低于该分数视为不合格项
INSPECTION_ITEM_PROBLEM_THRESHOLD = 6


class ComplaintSource(StrEnum):
    """群众反映与热线转办的登记来源。"""

    HOTLINE = "热线电话"
    TRANSFER_12345 = "12345转办"
    ON_SITE = "现场反映"
    NETWORK = "网络平台"
    OTHER = "其他渠道"


class ComplaintCategory(StrEnum):
    CLEANING = "保洁卫生"
    FACILITY = "设施损坏"
    ODOR = "异味扰民"
    CONSUMABLE = "耗材缺失"
    SAFETY = "安全隐患"
    ATTITUDE = "服务态度"
    OTHER = "其他"


class ComplaintStatus(StrEnum):
    PENDING = "待受理"
    PROCESSING = "处理中"
    PENDING_VISIT = "待回访"
    DONE = "已办结"
    CLOSED = "已关闭"


class ComplaintVisitResult(StrEnum):
    SATISFIED = "联系上-满意"
    UNSATISFIED = "联系上-不满意"
    UNREACHABLE = "未联系上"


# 投诉办理流转规则：当前状态 -> 允许流转到的状态
# 注意：「待回访」只能通过登记回访记录推进（满意办结 / 不满意退回 / 未联系上再约）
COMPLAINT_TRANSITIONS: dict[str, list[str]] = {
    ComplaintStatus.PENDING: [ComplaintStatus.PROCESSING, ComplaintStatus.CLOSED],
    ComplaintStatus.PROCESSING: [ComplaintStatus.PENDING_VISIT, ComplaintStatus.CLOSED],
    ComplaintStatus.PENDING_VISIT: [],
    ComplaintStatus.DONE: [ComplaintStatus.CLOSED],
    ComplaintStatus.CLOSED: [],
}

# 状态流转对应的动作名称，用于生成办理流水
COMPLAINT_TRANSITION_ACTIONS: dict[tuple[str, str], str] = {
    (ComplaintStatus.PENDING, ComplaintStatus.PROCESSING): "受理分派",
    (ComplaintStatus.PENDING, ComplaintStatus.CLOSED): "作废关闭",
    (ComplaintStatus.PROCESSING, ComplaintStatus.PENDING_VISIT): "办结待回访",
    (ComplaintStatus.PROCESSING, ComplaintStatus.CLOSED): "终止关闭",
    (ComplaintStatus.PENDING_VISIT, ComplaintStatus.DONE): "回访办结",
    (ComplaintStatus.PENDING_VISIT, ComplaintStatus.PROCESSING): "回访退回",
    (ComplaintStatus.DONE, ComplaintStatus.CLOSED): "归档关闭",
}

# 按反映内容判定分类的关键词表，命中越多分类越靠前
COMPLAINT_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    ComplaintCategory.CLEANING.value: [
        "脏", "污渍", "地面", "垃圾", "满溢", "打扫", "保洁", "卫生", "蚊蝇", "痰迹",
    ],
    ComplaintCategory.FACILITY.value: [
        "损坏", "坏了", "漏水", "堵塞", "冲水", "水龙头", "门锁", "灯", "故障", "维修", "扶手",
    ],
    ComplaintCategory.ODOR.value: ["臭", "异味", "刺鼻", "通风", "臭味"],
    ComplaintCategory.CONSUMABLE.value: ["厕纸", "纸巾", "洗手液", "耗材", "烘手", "缺纸"],
    ComplaintCategory.SAFETY.value: ["滑", "摔倒", "安全", "漏电", "隐患", "积水", "玻璃"],
    ComplaintCategory.ATTITUDE.value: ["态度", "辱骂", "推诿", "拒绝", "服务"],
}

# 仍未闭环的投诉状态，用于统计待办诉求
OPEN_COMPLAINT_STATUSES: list[str] = [
    ComplaintStatus.PENDING,
    ComplaintStatus.PROCESSING,
    ComplaintStatus.PENDING_VISIT,
]
