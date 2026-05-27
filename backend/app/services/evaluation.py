import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.database import async_session
from app.models.application import Application
from app.models.job import Job
from app.services.agent.multi_agent_graph import multi_agent_graph
from app.services.agent.state import MultiAgentState

async def run_batch_evaluation(job_id: str):
    """后台任务：评估指定岗位的未评分简历"""
    # 在后台任务中创建独立的数据库会话
    async with async_session() as db:
        # 1. 获取岗位信息（用于评估上下文）
        job = await db.get(Job, job_id)
        if not job:
            print(f"岗位 {job_id} 不存在，评估任务终止")
            return

        # 2. 获取该岗位所有未评估的申请
        stmt = select(Application).where(
            Application.job_id == job_id,
            Application.match_score.is_(None)
        )
        result = await db.execute(stmt)
        applications = result.scalars().all()

        if not applications:
            print(f"岗位 {job_id} 没有待评估的简历")
            return

        print(f"开始评估岗位 {job_id}，共 {len(applications)} 份简历")

        # 3. 分批处理（每批最多5个，防止 token 超限）
        batch_size = 5
        for i in range(0, len(applications), batch_size):
            batch = applications[i:i+batch_size]
            candidates = [
                {
                    "id": str(app.id),
                    "structured_resume": app.structured_resume,
                    "resume_text": app.resume_text
                }
                for app in batch
            ]

            # 4. 初始化多智能体状态
            initial_state = MultiAgentState(
                messages=[],
                user_id="system",
                job_id=job_id,
                candidates=candidates,
                structured_candidates=[],
                scores=[],
                recommendations=[],
                hr_decision=None,
                next_action="evaluate",
                iteration_count=0,
                error=None,
            )

            # 5. 运行多智能体图（必须提供 config 用于检查点）
            config = {
                "configurable": {
                    "thread_id": f"eval_{job_id}_{int(time.time())}_{i}"
                }
            }
            final_state = await multi_agent_graph.ainvoke(initial_state, config)
            scores = final_state.get("scores", [])

            # 6. 将评分写回数据库
            for score in scores:
                await db.execute(
                    update(Application)
                    .where(Application.id == score["applicant_id"])
                    .values(
                        match_score=score["score"],
                        ai_suggestions=score.get("reason", "")
                    )
                )
            await db.commit()
            print(f"  第 {i+1}-{min(i+batch_size, len(applications))} 份简历评估完成")

        print(f"岗位 {job_id} 评估任务全部完成")