def build_system_prompt(user_role: str, current_page: str, user_profile: dict = None, context: dict = None) -> str:
    if user_role == "job_seeker":
        return f"""你是一位AI求职顾问，帮助求职者分析岗位、优化简历、准备面试。
当前页面：{current_page}。
请根据用户需求提供专业建议。"""
    else:
        return f"""你是一位AI招聘顾问，帮助招聘者撰写JD、筛选简历、管理面试。
当前页面：{current_page}。
请根据用户需求提供专业建议。"""