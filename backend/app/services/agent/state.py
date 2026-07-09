"""LangGraph 工作流状态定义"""

from typing import TypedDict


class EvaluationState(TypedDict, total=False):
    """评估工作流状态

    所有字段都是可选的（total=False），因为不同节点逐步填充状态。
    """

    # 输入
    job_id: str
    triggered_by: str
    task_id: str
    mode: str  # "new_only" | "all"

    # 收集阶段产出
    job_info: dict[str, object]  # 岗位信息
    applications: list[dict[str, object]]  # 待评估的申请列表（含 structured_resume）

    # 评估阶段产出
    evaluation_results: list[dict[str, object]]  # 每份简历的评估结果
    evaluated_count: int  # 已评估数量（用于进度更新）

    # 筛选阶段产出
    screening_result: dict[str, object]  # 排序结果 + cutoff_score

    # 复评阶段产出
    review_adjustments: list[dict[str, object]]  # 边界候选人调整

    # 错误处理
    errors: list[str]  # 累积的错误信息
