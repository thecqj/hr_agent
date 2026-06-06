from app.services.placeholder_ai import evaluate_placeholder


async def run_batch_evaluation(job_id: str) -> None:
    """后台任务占位：保留调用链，后续可替换为真实评估。"""
    await evaluate_placeholder(job_id)
