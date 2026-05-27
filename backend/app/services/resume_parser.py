import io
import traceback
import fitz  # PyMuPDF
import docx
from openai import AsyncOpenAI
from app.config import settings
import json


async def extract_text_from_file(content: bytes, filename: str) -> str:
    """从 PDF 或 Word 文件中提取文本"""
    print(f"[简历解析] 开始提取文件: {filename}, 大小: {len(content)} bytes")
    
    if filename.endswith('.pdf'):
        try:
            pdf = fitz.open(stream=content, filetype="pdf")
            text = ""
            for page_num, page in enumerate(pdf):
                page_text = page.get_text("text")
                text += page_text
                print(f"[简历解析] 已提取第 {page_num+1} 页，共 {len(page_text)} 字")
            pdf.close()
            print(f"[简历解析] PDF 提取完成，总字数: {len(text)}")
            return text
        except Exception as e:
            print(f"[简历解析] PDF 解析失败: {traceback.format_exc()}")
            raise ValueError(f"PDF 文件解析失败: {str(e)}")

    elif filename.endswith('.docx'):
        try:
            doc = docx.Document(io.BytesIO(content))
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text)
            text = "\n".join(full_text)
            print(f"[简历解析] DOCX 提取完成，总字数: {len(text)}")
            return text
        except Exception as e:
            print(f"[简历解析] DOCX 解析失败: {traceback.format_exc()}")
            raise ValueError(f"DOCX 文件解析失败: {str(e)}")

    else:
        raise ValueError("仅支持 PDF 和 Word 文件")


async def parse_resume_document(content: bytes, filename: str) -> dict:
    """解析简历文档，返回结构化数据"""
    print(f"[简历解析] ========== 开始解析简历 ==========")
    
    # 1. 提取文本
    try:
        text = await extract_text_from_file(content, filename)
    except Exception as e:
        print(f"[简历解析] 文本提取阶段失败: {str(e)}")
        raise ValueError(f"文本提取失败: {str(e)}")

    if not text or len(text.strip()) < 10:
        raise ValueError("简历内容过短或为空，请检查文件")

    # 2. 调用 LLM 解析
    print(f"[简历解析] 开始调用 AI 解析，文本长度: {len(text)} 字")
    
    try:
        client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=getattr(settings, "OPENAI_API_BASE", None)
        )

        prompt = f"""从以下简历文本中提取结构化信息，以JSON格式返回。
必须包含以下字段，如果某项没有则返回空值或空列表：

{{
  "name": "姓名",
  "work_experience_years": 工作年限（整数，无法确定则填0）,
  "education_level": "最高学历",
  "contact": {{
    "phone": "手机号",
    "email": "邮箱",
    "wechat": "微信",
    "other": "其他联系方式"
  }},
  "work_experience": [
    {{ "company": "公司", "position": "职位", "start_date": "开始日期(YYYY-MM)", "end_date": "结束日期(YYYY-MM，留空表示至今)", "description": "工作描述" }}
  ],
  "project_experience": [
    {{ "name": "项目名", "role": "角色", "start_date": "开始日期", "end_date": "结束日期", "description": "描述", "technologies": ["技术1", "技术2"] }}
  ],
  "education": [
    {{ "school": "学校", "major": "专业", "degree": "学位", "start_date": "入学日期", "end_date": "毕业日期" }}
  ],
  "certificates": [{{ "name": "证书名", "date": "获得日期" }}],
  "skills": ["技能1", "技能2"],
  "self_evaluation": "自我评价"
}}

简历内容：
{text[:2000]}
"""

        print(f"[简历解析] 发送请求到 AI 模型: {settings.AGENT_MODEL}")
        response = await client.chat.completions.create(
            model=settings.AGENT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
            timeout=30,
        )
        
        result_text = response.choices[0].message.content
        print(f"[简历解析] AI 返回结果长度: {len(result_text)} 字")
        
        result = json.loads(result_text)
        print(f"[简历解析] ========== 解析成功 ==========")
        return result
        
    except json.JSONDecodeError as e:
        print(f"[简历解析] AI 返回的不是有效 JSON: {str(e)}")
        print(f"[简历解析] 原始返回: {response.choices[0].message.content[:500] if response else 'N/A'}")
        raise ValueError(f"AI 返回格式错误，请重试")
    except Exception as e:
        print(f"[简历解析] AI 调用失败: {traceback.format_exc()}")
        raise ValueError(f"AI 解析失败: {str(e)}")