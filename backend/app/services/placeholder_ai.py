from app.config import settings


def placeholder_message() -> str:
    return settings.AI_PLACEHOLDER_MESSAGE


async def parse_resume_placeholder(filename: str) -> dict:
    """简历解析占位实现：字段保持与历史结构兼容。"""
    return {
        "name": "待补全",
        "work_experience_years": 0,
        "education_level": None,
        "contact": {
            "phone": None,
            "email": None,
            "wechat": None,
            "other": None,
        },
        "work_experience": [],
        "project_experience": [],
        "education": [],
        "certificates": [],
        "skills": [],
        "self_evaluation": f"{placeholder_message()} 文件: {filename}",
    }


async def chat_placeholder(payload: dict, user_role: str, user_id: str) -> dict:
    message = payload.get("message", "")
    return {
        "type": "final",
        "content": f"{placeholder_message()} role={user_role}, user={user_id}, input={message}",
        "done": True,
    }


async def batch_screening_placeholder(job_id: str, candidates_count: int = 0) -> dict:
    return {
        "status": "completed",
        "recommendations": [],
        "message": f"{placeholder_message()} job_id={job_id}, candidates={candidates_count}",
    }


async def evaluate_placeholder(job_id: str) -> dict:
    return {
        "message": f"{placeholder_message()} 已登记评估请求 job_id={job_id}",
    }
