import { useCallback, useRef, useState } from "react";
import { FileUp, Loader2, CheckCircle2, AlertCircle, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useParseResumeMutation, useResumeListQuery } from "@/features/resumes/hooks/useResumes";
import type { ParseResumeResponse } from "@/features/resumes/api/resumes";
import { cn } from "@/lib/utils";

type UploadStatus = "idle" | "uploading" | "parsed" | "error";

interface ResumeUploaderProps {
  onParsed: (data: ParseResumeResponse) => void;
  onReset?: () => void;
}

const ACCEPTED_TYPES = ".pdf,.docx,.txt";
const MAX_SIZE = 10 * 1024 * 1024; // 10MB

export default function ResumeUploader({ onParsed, onReset }: ResumeUploaderProps) {
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [fileName, setFileName] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const parseMutation = useParseResumeMutation();
  const { data: resumeList } = useResumeListQuery();

  const handleFile = useCallback(async (file: File) => {
    // Validate type
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ACCEPTED_TYPES.includes(ext)) {
      setStatus("error");
      setErrorMessage("不支持的文件格式，请上传 PDF、DOCX 或 TXT 文件");
      return;
    }

    // Validate size
    if (file.size > MAX_SIZE) {
      setStatus("error");
      setErrorMessage("文件大小超过 10MB 限制");
      return;
    }

    setFileName(file.name);
    setStatus("uploading");
    setErrorMessage("");

    try {
      const result = await parseMutation.mutateAsync(file);
      setStatus("parsed");
      onParsed(result);
    } catch (error) {
      setStatus("error");
      setErrorMessage(error instanceof Error ? error.message : "简历解析失败，请手动填写");
    }
  }, [parseMutation, onParsed]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    // Reset input so same file can be re-selected
    e.target.value = "";
  };

  const handleReset = () => {
    setStatus("idle");
    setFileName("");
    setErrorMessage("");
    onReset?.();
  };

  // Parsed state
  if (status === "parsed") {
    return (
      <Card className="p-4 border-green-200 bg-green-50 dark:bg-green-950/20 dark:border-green-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
            <div>
              <p className="text-sm font-medium text-green-800 dark:text-green-300">
                已从简历自动填充
              </p>
              <p className="text-xs text-green-600 dark:text-green-400">{fileName}</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={handleReset}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Drag & drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={handleClick}
        className={cn(
          "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
          "hover:border-primary hover:bg-primary/5",
          isDragOver && "border-primary bg-primary/10",
          status === "error" && "border-destructive bg-destructive/5",
          status === "uploading" && "border-muted-foreground/30 pointer-events-none opacity-70",
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_TYPES}
          className="hidden"
          onChange={handleFileChange}
        />

        {status === "uploading" ? (
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">正在解析简历...</p>
            <p className="text-xs text-muted-foreground">{fileName}</p>
          </div>
        ) : status === "error" ? (
          <div className="flex flex-col items-center gap-2">
            <AlertCircle className="h-8 w-8 text-destructive" />
            <p className="text-sm font-medium text-destructive">解析失败</p>
            <p className="text-xs text-muted-foreground">{errorMessage}</p>
            <Button variant="outline" size="sm" className="mt-2" onClick={(e) => { e.stopPropagation(); handleReset(); }}>
              重新上传
            </Button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <FileUp className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm font-medium">
              拖拽简历文件到此处，或<span className="text-primary">点击选择文件</span>
            </p>
            <p className="text-xs text-muted-foreground">
              支持 PDF、DOCX、TXT 格式，最大 10MB
            </p>
          </div>
        )}
      </div>

      {/* Resume library selector */}
      {resumeList && resumeList.items.length > 0 && (
        <div className="text-center">
          <span className="text-xs text-muted-foreground">或</span>
          <div className="mt-2 flex flex-wrap gap-2 justify-center">
            {resumeList.items.map((resume) => (
              <Button
                key={resume.id}
                variant="outline"
                size="sm"
                onClick={async () => {
                  setStatus("uploading");
                  setFileName(resume.file_name);
                  try {
                    const { getResumeDetail } = await import("@/features/resumes/api/resumes");
                    const detail = await getResumeDetail(resume.id);
                    if (detail.structured_data) {
                      setStatus("parsed");
                      onParsed({
                        parsed_text: detail.parsed_text || "",
                        structured_data: detail.structured_data,
                      });
                    }
                  } catch {
                    setStatus("error");
                    setErrorMessage("加载简历失败");
                  }
                }}
              >
                {resume.name}
              </Button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}