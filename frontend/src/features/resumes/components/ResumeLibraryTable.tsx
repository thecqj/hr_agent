import { useState } from "react";
import { CheckCircle2, Eye, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useResumeListQuery, useResumeDetailQuery } from "@/features/resumes/hooks/useResumes";
import { getResumeDetail } from "@/features/resumes/api/resumes";
import type { ParseResumeResponse } from "@/features/resumes/api/resumes";
import type { StructuredResume } from "@/features/applications/types/application";

interface ResumeLibraryTableProps {
  onSelect: (data: ParseResumeResponse) => void;
}

function formatDate(dateStr: string) {
  const date = new Date(dateStr);
  return date.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

/** 生成简历结构化数据的文本摘要 */
function getResumeSummary(data: StructuredResume): string {
  const parts: string[] = [];
  if (data.work_experience_years) parts.push(`${data.work_experience_years}年经验`);
  if (data.education_level) parts.push(data.education_level);
  if (data.skills?.length) parts.push(data.skills.slice(0, 5).join("、"));
  return parts.join(" | ") || "暂无摘要";
}

export default function ResumeLibraryTable({ onSelect }: ResumeLibraryTableProps) {
  const { data: resumeList, isLoading } = useResumeListQuery();
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<ParseResumeResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const handlePreview = async (id: string) => {
    setPreviewId(id);
    setPreviewLoading(true);
    try {
      const detail = await getResumeDetail(id);
      if (detail.structured_data) {
        setPreviewData({
          parsed_text: detail.parsed_text || "",
          structured_data: detail.structured_data,
        });
      }
    } catch {
      // silently fail
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleSelect = async (id: string) => {
    try {
      const detail = await getResumeDetail(id);
      if (detail.structured_data) {
        onSelect({
          parsed_text: detail.parsed_text || "",
          structured_data: detail.structured_data,
        });
      }
    } catch {
      // silently fail
    }
  };

  const items = resumeList?.items ?? [];

  if (isLoading) {
    return (
      <div className="flex justify-center py-6">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-4">
        暂无已保存的简历，请先上传简历文件
      </p>
    );
  }

  return (
    <>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>简历名称</TableHead>
              <TableHead className="hidden sm:table-cell">文件名</TableHead>
              <TableHead className="hidden md:table-cell">上传时间</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((resume) => (
              <TableRow key={resume.id}>
                <TableCell className="font-medium">{resume.name}</TableCell>
                <TableCell className="hidden sm:table-cell text-sm text-muted-foreground truncate max-w-[180px]">
                  {resume.file_name}
                </TableCell>
                <TableCell className="hidden md:table-cell text-sm text-muted-foreground">
                  {formatDate(resume.created_at)}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handlePreview(resume.id)}
                    >
                      <Eye className="h-3.5 w-3.5 mr-1" />
                      预览
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleSelect(resume.id)}
                    >
                      <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                      选择
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Preview dialog */}
      <Dialog open={Boolean(previewId)} onOpenChange={(open) => { if (!open) { setPreviewId(null); setPreviewData(null); } }}>
        <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>简历预览</DialogTitle>
          </DialogHeader>

          {previewLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : previewData?.structured_data ? (
            <div className="space-y-4">
              {/* Basic info */}
              <div>
                <h4 className="text-sm font-semibold text-muted-foreground mb-1">基本信息</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div><span className="text-muted-foreground">姓名：</span>{previewData.structured_data.name || "—"}</div>
                  <div><span className="text-muted-foreground">工作年限：</span>{previewData.structured_data.work_experience_years || 0}年</div>
                  {previewData.structured_data.education_level && (
                    <div><span className="text-muted-foreground">最高学历：</span>{previewData.structured_data.education_level}</div>
                  )}
                </div>
              </div>

              {/* Contact */}
              {previewData.structured_data.contact && (
                <div>
                  <h4 className="text-sm font-semibold text-muted-foreground mb-1">联系方式</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    {previewData.structured_data.contact.phone && <div><span className="text-muted-foreground">手机：</span>{previewData.structured_data.contact.phone}</div>}
                    {previewData.structured_data.contact.email && <div><span className="text-muted-foreground">邮箱：</span>{previewData.structured_data.contact.email}</div>}
                  </div>
                </div>
              )}

              {/* Work Experience summary */}
              {(previewData.structured_data.work_experience?.length ?? 0) > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-muted-foreground mb-1">工作经历</h4>
                  <p className="text-sm">{previewData.structured_data.work_experience.length} 段</p>
                </div>
              )}

              {/* Skills */}
              {(previewData.structured_data.skills?.length ?? 0) > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-muted-foreground mb-1">专业技能</h4>
                  <div className="flex flex-wrap gap-1">
                    {previewData.structured_data.skills.map((s) => (
                      <span key={s} className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-primary/10 text-primary">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <p className="text-xs text-muted-foreground">{getResumeSummary(previewData.structured_data)}</p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">无法加载简历详情</p>
          )}

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => { setPreviewId(null); setPreviewData(null); }}>
              关闭
            </Button>
            {previewData && (
              <Button onClick={() => { onSelect(previewData); setPreviewId(null); setPreviewData(null); }}>
                使用此简历
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
