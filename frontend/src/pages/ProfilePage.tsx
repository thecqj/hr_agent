import { useCallback, useEffect, useRef, useState } from "react";
import { FileUp, Loader2, Plus, Pencil } from "lucide-react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useResumeListQuery, useUploadResumeMutation } from "@/features/resumes/hooks/useResumes";
import ResumeCard from "@/features/resumes/components/ResumeCard";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";
import { cn } from "@/lib/utils";

const ACCEPTED_TYPES = ".pdf,.docx,.txt";
const MAX_SIZE = 10 * 1024 * 1024;

export default function ProfilePage() {
  const navigate = useNavigate();
  const { setItems: setBreadcrumbItems } = useBreadcrumb();

  useEffect(() => {
    setBreadcrumbItems([{ label: "个人中心" }]);
  }, [setBreadcrumbItems]);

  const { data: resumeList, isLoading } = useResumeListQuery();
  const uploadMutation = useUploadResumeMutation();

  const [showChoiceDialog, setShowChoiceDialog] = useState(false);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [resumeName, setResumeName] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const resetUpload = () => {
    setResumeName("");
    setSelectedFile(null);
    setIsDragOver(false);
  };

  const handleCloseUploadDialog = () => {
    setShowUploadDialog(false);
    resetUpload();
  };

  const handleFileSelect = (file: File) => {
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ACCEPTED_TYPES.includes(ext)) {
      toast.error("不支持的文件格式，请上传 PDF、DOCX 或 TXT 文件");
      return;
    }
    if (file.size > MAX_SIZE) {
      toast.error("文件大小超过 10MB 限制");
      return;
    }
    setSelectedFile(file);
    if (!resumeName) {
      setResumeName(file.name.replace(/\.[^/.]+$/, ""));
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  }, []);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      toast.error("请选择简历文件");
      return;
    }
    if (!resumeName.trim()) {
      toast.error("请输入简历名称");
      return;
    }

    try {
      await uploadMutation.mutateAsync({ file: selectedFile, name: resumeName.trim() });
      handleCloseUploadDialog();
    } catch {
      // error handled by hook
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">个人中心</h1>
          <p className="text-sm text-muted-foreground mt-1">管理您的简历档案</p>
        </div>
        <Button onClick={() => setShowChoiceDialog(true)}>
          <Plus className="h-4 w-4 mr-1" />
          新建简历
        </Button>
      </div>

      <Separator className="mb-6" />

      {/* Resume list */}
      {isLoading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : resumeList && resumeList.items.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {resumeList.items.map((resume) => (
            <ResumeCard key={resume.id} resume={resume} />
          ))}
        </div>
      ) : (
        <Card className="p-12 text-center">
          <FileUp className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground mb-2">暂无简历</p>
          <p className="text-sm text-muted-foreground mb-4">创建您的第一份简历，开始智能投递之旅</p>
          <Button onClick={() => setShowChoiceDialog(true)}>
            <Plus className="h-4 w-4 mr-1" />
            新建简历
          </Button>
        </Card>
      )}

      {/* Choice dialog: upload or manual */}
      <Dialog open={showChoiceDialog} onOpenChange={setShowChoiceDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>新建简历</DialogTitle>
            <DialogDescription>选择创建简历的方式</DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-2 gap-4 py-4">
            <button
              onClick={() => {
                setShowChoiceDialog(false);
                setShowUploadDialog(true);
              }}
              className="flex flex-col items-center gap-3 p-6 rounded-lg border-2 border-dashed hover:border-primary hover:bg-primary/5 transition-colors cursor-pointer"
            >
              <FileUp className="h-10 w-10 text-primary" />
              <div className="text-center">
                <p className="font-medium text-sm">上传简历文件</p>
                <p className="text-xs text-muted-foreground mt-1">支持 PDF、DOCX、TXT</p>
              </div>
            </button>

            <button
              onClick={() => {
                setShowChoiceDialog(false);
                navigate("/profile/create");
              }}
              className="flex flex-col items-center gap-3 p-6 rounded-lg border-2 border-dashed hover:border-primary hover:bg-primary/5 transition-colors cursor-pointer"
            >
              <Pencil className="h-10 w-10 text-primary" />
              <div className="text-center">
                <p className="font-medium text-sm">手动填写简历</p>
                <p className="text-xs text-muted-foreground mt-1">逐项填写您的信息</p>
              </div>
            </button>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowChoiceDialog(false)}>
              取消
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Upload dialog */}
      <Dialog open={showUploadDialog} onOpenChange={handleCloseUploadDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>上传新简历</DialogTitle>
            <DialogDescription>
              支持 PDF、DOCX、TXT 格式，最大 10MB
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              className={cn(
                "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
                "hover:border-primary hover:bg-primary/5",
                isDragOver && "border-primary bg-primary/10",
                selectedFile && "border-green-300 bg-green-50 dark:bg-green-950/20 dark:border-green-700",
              )}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept={ACCEPTED_TYPES}
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFileSelect(file);
                }}
              />
              {selectedFile ? (
                <div>
                  <p className="text-sm font-medium text-green-700 dark:text-green-300">{selectedFile.name}</p>
                  <p className="text-xs text-muted-foreground mt-1">{(selectedFile.size / 1024 / 1024).toFixed(1)} MB</p>
                  <Button variant="ghost" size="sm" className="mt-2" onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}>
                    重新选择
                  </Button>
                </div>
              ) : (
                <div>
                  <FileUp className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">拖拽文件到此处，或<span className="text-primary">点击选择</span></p>
                </div>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="resume-name">简历名称 <span className="text-destructive">*</span></Label>
              <Input id="resume-name" placeholder="例如：通用简历、技术岗简历" value={resumeName} onChange={(e) => setResumeName(e.target.value)} />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleCloseUploadDialog}>取消</Button>
            <Button onClick={handleUpload} disabled={!selectedFile || !resumeName.trim() || uploadMutation.isPending}>
              {uploadMutation.isPending ? "上传中..." : "上传并解析"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
