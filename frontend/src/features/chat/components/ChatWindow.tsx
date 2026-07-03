import { useState } from "react";
import { Minus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ChatMessages } from "./ChatMessages";
import { ChatInput } from "./ChatInput";
import { useChatWindowDragResize } from "@/features/chat/hooks/useDragResize";
import type { UseChatReturn } from "@/features/chat/hooks/useChat";

interface ChatWindowProps {
  onMinimize: () => void;
  onClose: () => Promise<void>;
  bubbleSide: "left" | "right";
  chat: UseChatReturn;
}

export function ChatWindow({
  onMinimize,
  onClose,
  bubbleSide,
  chat,
}: ChatWindowProps) {
  const { messages, isProcessing, sendMessage } = chat;
  const { position, size, moveHandlers, resizeHandlers } = useChatWindowDragResize(
    bubbleSide,
  );
  const [showCloseDialog, setShowCloseDialog] = useState(false);

  const handleCloseClick = () => {
    setShowCloseDialog(true);
  };

  const handleConfirmClose = async () => {
    setShowCloseDialog(false);
    await onClose();
  };

  const handleCancelClose = () => {
    setShowCloseDialog(false);
  };

  return (
    <>
      <div
        className="fixed bg-card border rounded-xl shadow-xl flex flex-col overflow-hidden z-50"
        style={{
          left: position.x,
          top: position.y,
          width: size.width,
          height: size.height,
        }}
      >
        {/* Header — draggable */}
        <div
          className="flex items-center justify-between px-4 py-3 border-b bg-primary/5 cursor-grab active:cursor-grabbing touch-none shrink-0"
          onPointerDown={(e) => {
            e.stopPropagation();
            moveHandlers.onPointerDown(e);
          }}
          onPointerMove={(e) => {
            e.stopPropagation();
            moveHandlers.onPointerMove(e);
          }}
          onPointerUp={() => {
            moveHandlers.onPointerUp();
          }}
        >
          <h3 className="font-semibold text-sm select-none">HR 智能助手</h3>
          <div className="flex items-center gap-1">
            {/* Minimize button */}
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onPointerDown={(e) => e.stopPropagation()}
              onClick={(e) => {
                e.stopPropagation();
                onMinimize();
              }}
            >
              <Minus className="h-4 w-4" />
            </Button>
            {/* Close button */}
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onPointerDown={(e) => e.stopPropagation()}
              onClick={(e) => {
                e.stopPropagation();
                handleCloseClick();
              }}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Messages */}
        <ChatMessages messages={messages} />

        {/* Input */}
        <ChatInput onSend={sendMessage} disabled={isProcessing} />

        {/* Resize handle */}
        <div
          className="absolute bottom-0 right-0 w-4 h-4 cursor-nwse-resize touch-none"
          onPointerDown={(e) => {
            e.stopPropagation();
            resizeHandlers.onPointerDown(e);
          }}
          onPointerMove={(e) => {
            e.stopPropagation();
            resizeHandlers.onPointerMove(e);
          }}
          onPointerUp={() => {
            resizeHandlers.onPointerUp();
          }}
        >
          <svg className="w-3 h-3 text-muted-foreground/50 absolute bottom-0.5 right-0.5" viewBox="0 0 6 6" fill="currentColor">
            <circle cx="5" cy="1" r="0.7" />
            <circle cx="5" cy="3.5" r="0.7" />
            <circle cx="2.5" cy="3.5" r="0.7" />
            <circle cx="5" cy="6" r="0.7" />
            <circle cx="2.5" cy="6" r="0.7" />
            <circle cx="0" cy="6" r="0.7" />
          </svg>
        </div>
      </div>

      {/* Close confirmation dialog */}
      <Dialog open={showCloseDialog} onOpenChange={setShowCloseDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>关闭对话</DialogTitle>
            <DialogDescription>
              {isProcessing
                ? "对话正在进行中，关闭将中断当前操作并清空对话记录。确定关闭吗？"
                : "关闭将清空当前对话记录，下次打开将开始全新对话。确定关闭吗？"}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={handleCancelClose}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleConfirmClose}>
              确定关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
