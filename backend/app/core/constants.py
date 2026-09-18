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
    """诉求来源：群众反映或热线等渠道转办。"""

    PUBLIC = "群众反映"
    HOTLINE = "热线转办"
    ONLINE = "网络留言"
    ONSITE = "现场反映"
    OTHER = "其他渠道"


class ComplaintCategory(StrEnum):
    CLEANING = "保洁卫生"
    FACILITY = "设施损坏"
    ODOR = "异味扰民"
    CONSUMABLE = "耗材缺失"
    ATTITUDE = "服务态度"
    OTHER = "其他"


class ComplaintStatus(StrEnum):
    PENDING = "待分派"
    PROCESSING = "处理中"
    FOLLOW_UP = "待回访"
    RESOLVED = "已办结"
    CLOSED = "已关闭"


class FollowUpResult(StrEnum):
    REACHED = "已联系上"
    UNREACHABLE = "未联系上"


class FollowUpSatisfaction(StrEnum):
    SATISFIED = "满意"
    FAIR = "基本满意"
    DISSATISFIED = "不满意"


# 诉求办理流转规则：当前状态 -> 允许流转到的状态
COMPLAINT_TRANSITIONS: dict[str, list[str]] = {
    ComplaintStatus.PENDING: [ComplaintStatus.PROCESSING, ComplaintStatus.CLOSED],
    ComplaintStatus.PROCESSING: [ComplaintStatus.FOLLOW_UP, ComplaintStatus.CLOSED],
    ComplaintStatus.FOLLOW_UP: [ComplaintStatus.RESOLVED],
    ComplaintStatus.RESOLVED: [],
    ComplaintStatus.CLOSED: [],
}

# 按反映内容判定分类的关键词表：靠前的分类优先匹配
COMPLAINT_CATEGORY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    (ComplaintCategory.ODOR, ("异味", "臭味", "难闻", "熏", "气味")),
    (ComplaintCategory.FACILITY, ("水龙头", "冲水", "漏水", "损坏", "坏了", "故障", "门锁", "照明", "灯", "扶手", "无障碍")),
    (ComplaintCategory.CONSUMABLE, ("厕纸", "纸巾", "没有纸", "洗手液", "耗材", "皂液")),
    (ComplaintCategory.ATTITUDE, ("态度", "服务", "保洁员", "工作人员", "争吵")),
    (ComplaintCategory.CLEANING, ("脏", "污", "垃圾", "打扫", "清洁", "卫生", "积水", "蚊蝇", "痰迹")),
]

# 仍未办结、需要跟进的诉求状态
OPEN_COMPLAINT_STATUSES: list[str] = [
    ComplaintStatus.PENDING,
    ComplaintStatus.PROCESSING,
    ComplaintStatus.FOLLOW_UP,
]
