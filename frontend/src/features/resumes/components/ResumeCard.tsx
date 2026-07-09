import { useState } from "react";
import { FileText, Download, Pencil, Trash2, Check, X, File as FileIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { ResumeListItem } from "@/features/resumes/api/resumes";
import { useUpdateResumeMutation, useDeleteResumeMutation } from "@/features/resumes/hooks/useResumes";
import { downloadResume } from "@/features/resumes/api/resumes";
import { getApiErrorMessage } from "@/shared/api/error";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface ResumeCardProps {
  resume: ResumeListItem;
}

function getFileIcon(fileType: string) {
  if (fileType.includes("pdf")) return <FileText className="h-5 w-5 text-red-500" />;
  if (fileType.includes("word") || fileType.includes("docx")) return <FileText className="h-5 w-5 text-blue-500" />;
  return <FileIcon className="h-5 w-5 text-muted-foreground" />;
}

function getFileTypeBadge(fileType: string) {
  if (fileType.includes("pdf")) return { label: "PDF", variant: "destructive" as const };
  if (fileType.includes("word") || fileType.includes("docx")) return { label: "DOCX", variant: "default" as const };
  if (fileType.includes("text") || fileType.includes("txt")) return { label: "TXT", variant: "secondary" as const };
  return { label: "FILE", variant: "outline" as const };
}

function formatDate(dateStr: string) {
  const date = new Date(dateStr);
  return date.toLocaleDateString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit" });
}

export default function ResumeCard({ resume }: ResumeCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(resume.name);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const updateMutation = useUpdateResumeMutation();
  const deleteMutation = useDeleteResumeMutation();

  const fileBadge = getFileTypeBadge(resume.file_type);

  const handleSaveName = async () => {
    if (!editName.trim() || editName.trim() === resume.name) {
      setIsEditing(false);
      return;
    }
    try {
      await updateMutation.mutateAsync({ id: resume.id, name: editName.trim() });
      setIsEditing(false);
    } catch {
      // error handled by hook
    }
  };

  const handleCancelEdit = () => {
    setEditName(resume.name);
    setIsEditing(false);
  };

  const handleDownload = async () => {
    try {
      const data = await downloadResume(resume.id);
      const byteChars = atob(data.file_data);
      const byteNums = new Array(byteChars.length);
      for (let i = 0; i < byteChars.length; i++) {
        byteNums[i] = byteChars.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNums);
      const blob = new Blob([byteArray], { type: data.file_type });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = data.file_name;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "下载失败"));
    }
  };

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync(resume.id);
      setShowDeleteDialog(false);
    } catch {
      // error handled by hook
    }
  };

  return (
    <>
      <Card
        className={cn(
          "transition-all duration-200 border",
          isHovered && "shadow-md scale-[1.02]",
        )}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              {getFileIcon(resume.file_type)}
              <div className="flex-1 min-w-0">
                {isEditing ? (
                  <div className="flex items-center gap-1">
                    <Input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="h-7 text-sm"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleSaveName();
                        if (e.key === "Escape") handleCancelEdit();
                      }}
                    />
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleSaveName}>
                      <Check className="h-3.5 w-3.5 text-green-600" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleCancelEdit}>
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ) : (
                  <p className="font-medium text-sm truncate">{resume.name}</p>
                )}
                <p className="text-xs text-muted-foreground truncate mt-0.5">{resume.file_name}</p>
              </div>
            </div>
            <Badge variant={fileBadge.variant} className="text-[10px] px-1.5 py-0 h-5">
              {fileBadge.label}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="pb-3">
          <p className="text-xs text-muted-foreground">上传于 {formatDate(resume.created_at)}</p>
        </CardContent>
        <CardFooter className={cn(
          "flex gap-1 pt-0 transition-opacity duration-200",
          isHovered ? "opacity-100" : "opacity-70 lg:opacity-80",
        )}>
          <Button variant="ghost" size="sm" onClick={() => setIsEditing(true)}>
            <Pencil className="h-3.5 w-3.5 mr-1" />
            重命名
          </Button>
          <Button variant="ghost" size="sm" onClick={handleDownload}>
            <Download className="h-3.5 w-3.5 mr-1" />
            下载
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setShowDeleteDialog(true)} className="text-destructive hover:text-destructive">
            <Trash2 className="h-3.5 w-3.5 mr-1" />
            删除
          </Button>
        </CardFooter>
      </Card>

      {/* Delete confirmation dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              确定要删除简历「{resume.name}」吗？此操作不可撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleteMutation.isPending}>
              {deleteMutation.isPending ? "删除中..." : "确认删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
