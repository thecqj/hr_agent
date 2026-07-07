"""LLM 提示词模板"""

import json

EVALUATION_SYSTEM_PROMPT = """你是一位资深 HR 顾问，擅长技术岗位简历评估。

## 任务
根据岗位要求评估候选人简历，给出结构化评分。

## 评估维度
你必须对以下每个维度进行评分（0-100），并分配权重（权重之和必须 = 1.0）：
{dimensions_section}

## 评分基准
- 90+：极优秀，远超岗位要求
- 80-89：优秀，超出岗位要求
- 70-79：良好，基本满足岗位要求
- 60-69：一般，部分满足岗位要求但有不足
- 50-59：较弱，明显不足
- 50以下：严重不匹配

## 输出要求
严格按照以下 JSON 格式输出，不要输出任何其他内容：
{{
  "dimensions": [
    {{
      "name": "维度名称",
      "score": 85,
      "weight": 0.35,
      "reason": "评估理由"
    }}
  ],
  "weighted_total": 79.25,
  "suggestion": "recommend 或 reject 或 neutral",
  "summary": "一句话总结该候选人的匹配情况"
}}

## 偏见抑制
- 不基于性别、年龄、婚育状态做评判
- 仅关注与岗位要求直接相关的技能、经验和学历
- 对空窗期保持客观，不预设负面判断
"""

REVIEW_SYSTEM_PROMPT = """你是一位资深 HR 顾问，正在进行边界候选人复评。

## 任务
检查进面名单中靠近分数线的候选人是否应该进面，以及淘汰名单中靠近分数线的候选人是否不该被淘汰。

## 输出要求
对每个候选人给出判断，严格按照以下 JSON 格式输出：
{{
  "reviews": [
    {{
      "application_id": "申请ID",
      "action": "keep 或 adjust",
      "new_decision": "recommend 或 reject（action=adjust 时必填，keep 时为 null）",
      "reason": "判断理由"
    }}
  ]
}}

## 判断标准
- 仅在你有明确理由认为原决策有误时才 adjust
- 如果候选人确实处于边界且差距不大，倾向于 keep（维持原决策）
- adjust 时必须给出充分的理由
"""


def build_evaluation_user_prompt(
    job_info: dict[str, object],
    structured_resume: dict[str, object],
    dimensions: list[str],
) -> str:
    """构建简历评估的用户提示词"""
    dimensions_section = "\n".join(
        f"- **{d}**" for d in dimensions
    )
    system_text = EVALUATION_SYSTEM_PROMPT.format(dimensions_section=dimensions_section)

    # 用独立的 format 避免 {{}} 转义问题
    job_json = json.dumps(job_info, ensure_ascii=False, indent=2)
    resume_json = json.dumps(structured_resume, ensure_ascii=False, indent=2)

    # Extract requirements for emphasis (if available)
    requirements_text = job_info.get("requirements", "")

    return f"""{system_text}

## 岗位任职要求（主要评估标准）
{requirements_text if requirements_text else "见下方岗位完整信息"}

## 岗位完整信息
```json
{job_json}
```

## 候选人简历
```json
{resume_json}
```"""


def build_review_user_prompt(
    job_info: dict[str, object],
    borderline_recommend: list[dict[str, object]],
    borderline_reject: list[dict[str, object]],
    cutoff_score: float,
) -> str:
    """构建边界复评的用户提示词"""
    job_json = json.dumps(job_info, ensure_ascii=False, indent=2)
    recommend_json = json.dumps(borderline_recommend, ensure_ascii=False, indent=2)
    reject_json = json.dumps(borderline_reject, ensure_ascii=False, indent=2)

    return f"""{REVIEW_SYSTEM_PROMPT}

## 岗位要求
```json
{job_json}
```

## 进面分数线：{cutoff_score}

## 进面名单中的边界候选人（分数在分数线 ± 范围内）
```json
{recommend_json}
```

## 淘汰名单中的边界候选人（分数在分数线 ± 范围内）
```json
{reject_json}
```"""


PARSE_RESUME_SYSTEM_PROMPT = """你是一位专业的简历解析助手，擅长从原始简历文本中提取结构化信息。

## 任务
从提供的原始简历文本中提取以下信息并整理为结构化JSON格式：
1. 个人信息：姓名、性别、年龄、联系方式（电话/邮箱）、居住地
2. 教育背景：学校、专业、学历、毕业时间
3. 工作经历：公司名称、职位、工作时间、工作职责与业绩
4. 技能清单：专业技能、工具使用、语言能力
5. 求职意向：目标岗位、期望薪资、工作地点

## 输出要求
严格按照以下JSON格式输出，不要输出任何其他内容：
{
  "personal_info": {
    "name": "",
    "gender": "",
    "age": null,
    "phone": "",
    "email": "",
    "location": ""
  },
  "education": [
    {
      "school": "",
      "major": "",
      "degree": "",
      "graduation_date": ""
    }
  ],
  "work_experience": [
    {
      "company": "",
      "position": "",
      "start_date": "",
      "end_date": "",
      "responsibilities": "",
      "achievements": ""
    }
  ],
  "skills": [],
  "job_intention": {
    "target_position": "",
    "expected_salary": "",
    "work_location": ""
  }
}

## 注意事项
- 无法确定的信息留空或设为null
- 技能清单请用数组形式列出所有相关技能
- 工作经历请按时间倒序排列
- 仅提取简历中明确包含的信息，不要添加主观推测内容
"""
