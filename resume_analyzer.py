import json
import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict

# ==================== 依赖导入 ====================
try:
    import docx
    from docx import Document
    from docx.shared import Pt
    from docx.oxml.shared import OxmlElement, qn
except ImportError:
    docx = None

try:
    import fitz
except ImportError:
    fitz = None

try:
    import easyocr
except ImportError:
    easyocr = None

try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None

# ==================== 简历评分Agent ====================
class ResumeAnalyzerAgent:
    DIMENSIONS = {
        "硬件": ["单片机", "FPGA", "ARM", "硬件设计", "电路", "PCB", "嵌入式", "传感器"],
        "系统软件": ["Linux", "Windows", "驱动", "内核", "Shell", "系统优化", "批处理"],
        "AI": ["机器学习", "深度学习", "TensorFlow", "PyTorch", "CV", "NLP", "大模型", "LLM"]
    }

    GRADE = {
        "A": (90, 100),
        "B": (80, 89),
        "C": (70, 79),
        "D": (60, 69),
        "E": (0, 59)
    }

    def __init__(self):
        self.results = {}

    def _score(self, text, keys):
        cnt = sum(1 for k in keys if re.search(rf'\b{re.escape(k)}\b', text, re.I))
        return min(100, cnt * 12)

    def _grade(self, s):
        for g, (lo, hi) in self.GRADE.items():
            if lo <= s <= hi:
                return g
        return "E"

    def _comment(self, dim, g):
        return {
            "A": f"{dim}能力优秀，专业扎实",
            "B": f"{dim}能力良好，可胜任工作",
            "C": f"{dim}能力一般，需加强实践",
            "D": f"{dim}基础薄弱，需系统学习",
            "E": f"{dim}无明显相关能力"
        }[g]

    def analyze(self, name, text):
        hw = self._score(text, self.DIMENSIONS["硬件"])
        sw = self._score(text, self.DIMENSIONS["系统软件"])
        ai = self._score(text, self.DIMENSIONS["AI"])
        avg = (hw + sw + ai) // 3

        gh, gs, ga = self._grade(hw), self._grade(sw), self._grade(ai)
        gavg = self._grade(avg)

        brief = f"硬件{gh}，系统{gs}，AI{ga}；综合{gavg}。"

        res = {
            "硬件得分": hw, "硬件等级": gh, "硬件评语": self._comment("硬件", gh),
            "系统得分": sw, "系统等级": gs, "系统评语": self._comment("系统软件", gs),
            "AI得分": ai, "AI等级": ga, "AI评语": self._comment("AI", ga),
            "综合等级": gavg,
            "简评": brief
        }
        self.results[name] = res
        return res

# ==================== 文本提取 ====================
class TextExtractor:
    @staticmethod
    def extract(path):
        ext = path.lower().split(".")[-1]
        try:
            if ext == "txt":
                with open(path, "r", encoding="utf-8") as f: return f.read()
            if ext == "docx":
                doc = docx.Document(path)
                return "\n".join(p.text for p in doc.paragraphs)
            if ext == "pdf":
                doc = fitz.open(path)
                return "\n".join(page.get_text() for page in doc)
            if ext in ["jpg", "jpeg", "png"]:
                reader = easyocr.Reader(["ch_sim", "en"], verbose=False)
                return " ".join(reader.readtext(path, detail=0))
        except:
            return ""
        return ""

# ==================== 导出工具 ====================
class Exporter:
    @staticmethod
    def add_comment_to_docx(src_path, out_path, res):
        doc = Document(src_path)
        comment = (
            f"【硬件】{res['硬件等级']}：{res['硬件评语']}\n"
            f"【系统软件】{res['系统等级']}：{res['系统评语']}\n"
            f"【AI】{res['AI等级']}：{res['AI评语']}\n"
            f"【综合】{res['综合等级']}：{res['简评']}"
        )
        para = doc.paragraphs[0] if doc.paragraphs else doc.add_paragraph()
        run = para.runs[0] if para.runs else para.add_run(para.text)
        comment_el = OxmlElement('w:commentRangeStart')
        para._p.append(comment_el)
        doc.add_paragraph(f"HR智能分析批注：{comment}")
        doc.save(out_path)

    @staticmethod
    def create_analysis_docx(out_path, name, res):
        doc = Document()
        doc.add_heading(f"简历分析报告：{name}", 0)
        p = doc.add_paragraph()
        p.add_run(f"硬件：{res['硬件等级']} | {res['硬件评语']}\n").bold = True
        p.add_run(f"系统软件：{res['系统等级']} | {res['系统评语']}\n").bold = True
        p.add_run(f"AI：{res['AI等级']} | {res['AI评语']}\n").bold = True
        p.add_run(f"综合评级：{res['综合等级']}\n").bold = True
        p.add_run(f"简评：{res['简评']}")
        doc.save(out_path)

    @staticmethod
    def create_excel(out_path, results):
        wb = Workbook()
        ws = wb.active
        ws.title = "简历评级"
        headers = ["姓名", "硬件等级", "系统软件等级", "AI等级", "综合等级", "简评"]
        ws.append(headers)
        for name, res in results.items():
            ws.append([
                name, res['硬件等级'], res['系统等级'], res['AI等级'], res['综合等级'], res['简评']
            ])
        wb.save(out_path)

# ==================== GUI界面 ====================
class ResumeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("HR简历智能分析系统")
        self.root.geometry("800x600")
        self.agent = ResumeAnalyzerAgent()
        self.files = []
        self.out_dir = os.path.expanduser("~/Desktop")

        # 标题
        ttk.Label(root, text="简历分析：硬件 / 系统软件 / AI", font=("黑体",14,"bold")).pack(pady=10)

        # 文件区域
        frame = ttk.LabelFrame(root, text="简历文件", padding=15)
        frame.pack(fill=tk.BOTH, expand=True, padx=20)
        self.listbox = tk.Listbox(frame, height=6, font=("",10))
        self.listbox.pack(fill=tk.BOTH, expand=True)
        ttk.Button(frame, text="添加文件", command=self.add_files).pack(pady=5)

        # 输出目录
        dir_frame = ttk.Frame(root)
        dir_frame.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(dir_frame, text="输出目录：").pack(side=tk.LEFT)
        self.dir_var = tk.StringVar(value=self.out_dir)
        ttk.Entry(dir_frame, textvariable=self.dir_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(dir_frame, text="更改", command=self.choose_dir).pack(side=tk.RIGHT)

        # 按钮
        btn_frame = ttk.Frame(root)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="开始分析", command=self.do_analyze, width=12).grid(row=0,column=0,padx=10)
        ttk.Button(btn_frame, text="清空", command=self.do_clear, width=12).grid(row=0,column=1,padx=10)

        # 日志
        log_frame = ttk.LabelFrame(root, text="日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        self.log = tk.Text(log_frame, height=8)
        self.log.pack(fill=tk.BOTH, expand=True)

    def log_print(self, s):
        self.log.insert(tk.END, s+"\n")
        self.log.see(tk.END)
        self.root.update()

    def add_files(self):
        fs = filedialog.askopenfilenames(filetypes=[
            ("所有支持", "*.txt *.docx *.pdf *.jpg *.jpeg *.png"),
            ("Word", "*.docx"), ("PDF", "*.pdf"), ("图片", "*.jpg *.png"), ("文本", "*.txt")
        ])
        for f in fs:
            if f not in self.files:
                self.files.append(f)
                self.listbox.insert(tk.END, os.path.basename(f))
                self.log_print(f"已添加：{os.path.basename(f)}")

    def choose_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.out_dir = d
            self.dir_var.set(d)
            self.log_print(f"输出目录：{d}")

    def do_analyze(self):
        if not self.files:
            messagebox.showwarning("提示","请选择文件")
            return
        if not docx or not fitz or not easyocr or not Workbook:
            messagebox.showerror("缺少库","请安装依赖")
            return

        self.agent.results.clear()
        self.log_print("开始分析...")

        # 分析所有文件
        for path in self.files:
            name = os.path.splitext(os.path.basename(path))[0]
            text = TextExtractor.extract(path)
            if not text:
                self.log_print(f"⚠ {name} 读取失败")
                continue
            self.agent.analyze(name, text)
            self.log_print(f"✅ {name} 分析完成")

        cnt = len(self.agent.results)
        if cnt == 0:
            messagebox.showwarning("结果","无有效简历")
            return

        # ================== 输出规则 ==================
        if cnt == 1:
            name, res = next(iter(self.agent.results.items()))
            src_path = next(p for p in self.files if name in p)
            ext = src_path.lower().split(".")[-1]

            if ext == "docx":
                out = os.path.join(self.out_dir, f"【已批注】{name}.docx")
                Exporter.add_comment_to_docx(src_path, out, res)
                self.log_print(f"已生成批注文档：{out}")
            else:
                out = os.path.join(self.out_dir, f"【分析报告】{name}.docx")
                Exporter.create_analysis_docx(out, name, res)
                self.log_print(f"已生成分析文档：{out}")
        else:
            out = os.path.join(self.out_dir, "简历综合评级表.xlsx")
            Exporter.create_excel(out, self.agent.results)
            self.log_print(f"已生成多简历Excel：{out}")

        messagebox.showinfo("完成", f"共分析 {cnt} 份简历\n输出完成！")

    def do_clear(self):
        self.files.clear()
        self.agent.results.clear()
        self.listbox.delete(0, tk.END)
        self.log.delete(1.0, tk.END)
        self.log_print("已清空")

# ==================== 启动 ====================
if __name__ == "__main__":
    root = tk.Tk()
    app = ResumeGUI(root)
    root.mainloop()     