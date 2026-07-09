import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FileUp, FileText, Loader2, Plus, Pencil, Clock, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import {
  useResumeListQuery,
  useUploadResumeMutation,
  useUpdateResumeDataMutation,
  useParseResumeMutation,
} from "@/features/resumes/hooks/useResumes";
import ResumeCard from "@/features/resumes/components/ResumeCard";
import ResumeEditForm from "@/features/resumes/components/ResumeEditForm";
import type { StructuredResume } from "@/features/applications/types/application";
import type { ParseResumeResponse } from "@/features/resumes/api/resumes";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";
import { cn } from "@/lib/utils";

const ACCEPTED_TYPES = ".pdf,.docx,.txt";
const MAX_SIZE = 10 * 1024 * 1024;

type UploadPhase =
  | { step: "choice" }
  | { step: "select_file" }
  | { step: "uploading"; fileName: string }
  | { step: "parsed"; data: ParseResumeResponse }
  | { step: "saving"; name: string }
  | { step: "error"; message: string };

function formatDate(dateStr: string) {
  const date = new Date(dateStr);
  return date.toLocaleDateString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit" });
}

export default function ProfilePage() {
  const navigate = useNavigate();
  const { setItems: setBreadcrumbItems } = useBreadcrumb();

  useEffect(() => {
    setBreadcrumbItems([{ label: "个人中心" }]);
  }, [setBreadcrumbItems]);

  const { data: resumeList, isLoading } = useResumeListQuery();
  const uploadMutation = useUploadResumeMutation();
  const updateDataMutation = useUpdateResumeDataMutation();
  const parseMutation = useParseResumeMutation();

  // Upload flow state
  const [showChoiceDialog, setShowChoiceDialog] = useState(false);
  const [uploadPhase, setUploadPhase] = useState<UploadPhase>({ step: "choice" });
  const [resumeName, setResumeName] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [editedData, setEditedData] = useState<StructuredResume | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Stats
  const items = resumeList?.items ?? [];
  const totalCount = items.length;
  const parsedCount = useMemo(() => items.filter((r) => r.file_type && !r.file_type.includes("txt")).length, [items]);
  const latestDate = items.length > 0 ? items[0].created_at : null;

  const resetUpload = () => {
    setUploadPhase({ step: "choice" });
    setResumeName("");
    setSelectedFile(null);
    setIsDragOver(false);
    setEditedData(null);
  };

  const handleCloseChoiceDialog = () => {
    setShowChoiceDialog(false);
  };

  const handleOpenUploadDialog = () => {
    setShowChoiceDialog(false);
    setUploadPhase({ step: "select_file" });
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
    setUploadPhase({ step: "uploading", fileName: file.name });
    setResumeName(file.name.replace(/\.[^/.]+$/, ""));

    // Parse the file
    parseMutation.mutate(file, {
      onSuccess: (result) => {
        setEditedData(result.structured_data);
        setUploadPhase({ step: "parsed", data: result });
      },
      onError: (error) => {
        setUploadPhase({
          step: "error",
          message: error instanceof Error ? error.message : "简历解析失败",
        });
      },
    });
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

  const handleSaveResume = async () => {
    if (!selectedFile) {
      toast.error("请选择简历文件");
      return;
    }
    if (!resumeName.trim()) {
      toast.error("请输入简历名称");
      return;
    }

    setUploadPhase({ step: "saving", name: resumeName.trim() });

    try {
      // 1. Upload file to create resume record
      const created = await uploadMutation.mutateAsync({
        file: selectedFile,
        name: resumeName.trim(),
      });

      // 2. If user edited data, save it
      if (editedData) {
        await updateDataMutation.mutateAsync({
          id: created.id,
          data: {
            name: resumeName.trim(),
            structured_data: editedData,
          },
        });
      }

      resetUpload();
    } catch {
      // Error handled by hooks
    }
  };

  const handleEditDataChange = (data: StructuredResume) => {
    setEditedData(data);
  };

  const handleCloseUploadDialog = () => {
    resetUpload();
  };

  // Determine dialog content based on upload phase
  const showUploadDialog = uploadPhase.step !== "choice";

  return (
    <div className="max-w-5xl mx-auto animate-in fade-in duration-500">
      {/* Header with gradient background */}
      <div className="relative mb-8 rounded-xl bg-gradient-to-br from-primary/5 via-primary/[0.02] to-background border p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">个人中心</h1>
            <p className="text-sm text-muted-foreground mt-1">管理您的简历档案，让投递更高效</p>
          </div>
          <Button onClick={() => setShowChoiceDialog(true)} size="default" className="shadow-sm">
            <Plus className="h-4 w-4 mr-1" />
            新建简历
          </Button>
        </div>

        {/* Stats cards */}
        <div className="grid grid-cols-3 gap-4 mt-6">
          <Card className="bg-background/80 backdrop-blur-sm border-0 shadow-sm">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                <FileText className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{totalCount}</p>
                <p className="text-xs text-muted-foreground">简历总数</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-background/80 backdrop-blur-sm border-0 shadow-sm">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-green-500/10 flex items-center justify-center">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{parsedCount}</p>
                <p className="text-xs text-muted-foreground">已解析</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-background/80 backdrop-blur-sm border-0 shadow-sm">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-amber-500/10 flex items-center justify-center">
                <Clock className="h-5 w-5 text-amber-600" />
              </div>
              <div>
                <p className="text-lg font-bold truncate">
                  {latestDate ? formatDate(latestDate) : "—"}
                </p>
                <p className="text-xs text-muted-foreground">最近上传</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <Separator className="mb-6" />

      {/* Resume list */}
      {isLoading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : items.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((resume, index) => (
            <div
              key={resume.id}
              className="animate-in fade-in slide-in-from-bottom-2 duration-300"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <ResumeCard resume={resume} />
            </div>
          ))}
        </div>
      ) : (
        <Card className="p-16 text-center border-dashed">
          <div className="flex flex-col items-center gap-3">
            <div className="h-16 w-16 rounded-full bg-primary/5 flex items-center justify-center">
              <FileUp className="h-8 w-8 text-primary/60" />
            </div>
            <p className="text-base font-medium text-muted-foreground">暂无简历</p>
            <p className="text-sm text-muted-foreground max-w-sm">
              上传您的简历文件或手动填写简历信息，开始智能投递之旅
            </p>
            <div className="flex gap-3 mt-2">
              <Button onClick={() => setShowChoiceDialog(true)}>
                <Plus className="h-4 w-4 mr-1" />
                新建简历
              </Button>
            </div>
          </div>
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
              onClick={handleOpenUploadDialog}
              className="flex flex-col items-center gap-3 p-6 rounded-lg border-2 border-dashed hover:border-primary hover:bg-primary/5 transition-colors cursor-pointer group"
            >
              <FileUp className="h-10 w-10 text-primary group-hover:scale-110 transition-transform" />
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
              className="flex flex-col items-center gap-3 p-6 rounded-lg border-2 border-dashed hover:border-primary hover:bg-primary/5 transition-colors cursor-pointer group"
            >
              <Pencil className="h-10 w-10 text-primary group-hover:scale-110 transition-transform" />
              <div className="text-center">
                <p className="font-medium text-sm">手动填写简历</p>
                <p className="text-xs text-muted-foreground mt-1">逐项填写您的信息</p>
              </div>
            </button>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleCloseChoiceDialog}>
              取消
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Upload dialog - multi-step */}
      <Dialog open={showUploadDialog} onOpenChange={(open) => { if (!open) handleCloseUploadDialog(); }}>
        <DialogContent className={cn(
          "sm:max-w-md",
          uploadPhase.step === "parsed" && "sm:max-w-2xl",
        )}>
          <DialogHeader>
            <DialogTitle>
              {uploadPhase.step === "uploading" && "正在解析简历"}
              {uploadPhase.step === "parsed" && "简历解析完成"}
              {uploadPhase.step === "saving" && "正在保存简历"}
              {uploadPhase.step === "error" && "解析失败"}
              {uploadPhase.step === "select_file" && "上传新简历"}
            </DialogTitle>
            <DialogDescription>
              {uploadPhase.step === "select_file" && "支持 PDF、DOCX、TXT 格式，最大 10MB"}
              {uploadPhase.step === "parsed" && "请检查并补充未能自动识别的信息"}
              {uploadPhase.step === "error" && "您仍然可以手动填写或重新上传"}
            </DialogDescription>
          </DialogHeader>

          {/* Step: select file */}
          {uploadPhase.step === "select_file" && (
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
                <div>
                  <FileUp className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">
                    拖拽文件到此处，或<span className="text-primary">点击选择</span>
                  </p>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={handleCloseUploadDialog}>取消</Button>
              </DialogFooter>
            </div>
          )}

          {/* Step: uploading */}
          {uploadPhase.step === "uploading" && (
            <div className="flex flex-col items-center gap-3 py-8">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">正在上传并解析简历...</p>
              <p className="text-xs text-muted-foreground">{uploadPhase.fileName}</p>
            </div>
          )}

          {/* Step: parsed - show edit form */}
          {uploadPhase.step === "parsed" && (
            <div className="space-y-4">
              {/* Resume name */}
              <div className="space-y-2">
                <Label>简历名称 <span className="text-destructive">*</span></Label>
                <Input
                  value={resumeName}
                  onChange={(e) => setResumeName(e.target.value)}
                  placeholder="例如：通用简历、技术岗简历"
                />
              </div>

              {/* Edit form */}
              {editedData && (
                <ResumeEditForm
                  data={uploadPhase.data.structured_data}
                  onChange={handleEditDataChange}
                />
              )}

              <DialogFooter className="gap-2 pt-2">
                <Button variant="outline" onClick={handleCloseUploadDialog}>取消</Button>
                <Button
                  onClick={handleSaveResume}
                  disabled={!resumeName.trim() || uploadMutation.isPending}
                >
                  {uploadMutation.isPending ? "保存中..." : "保存到简历库"}
                </Button>
              </DialogFooter>
            </div>
          )}

          {/* Step: saving */}
          {uploadPhase.step === "saving" && (
            <div className="flex flex-col items-center gap-3 py-8">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">正在保存简历...</p>
            </div>
          )}

          {/* Step: error */}
          {uploadPhase.step === "error" && (
            <div className="space-y-4 py-4">
              <div className="text-center">
                <p className="text-sm text-destructive font-medium">{uploadPhase.message}</p>
              </div>
              <DialogFooter className="gap-2">
                <Button variant="outline" onClick={handleCloseUploadDialog}>取消</Button>
                <Button onClick={() => setUploadPhase({ step: "select_file" })}>
                  重新上传
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
