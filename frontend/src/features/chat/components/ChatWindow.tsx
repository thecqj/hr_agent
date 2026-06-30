import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useChat } from "@/features/chat/hooks/useChat";
import { useChatWindowDragResize } from "@/features/chat/hooks/useDragResize";
import { ChatMessages } from "./ChatMessages";
import { ChatInput } from "./ChatInput";

interface ChatWindowProps {
  onClose: () => void;
  bubbleSide: "left" | "right";
}

export function ChatWindow({ onClose, bubbleSide }: ChatWindowProps) {
  const { messages, isProcessing, sendMessage } = useChat();
  const { position, size, moveHandlers, resizeHandlers } = useChatWindowDragResize(bubbleSide);

  return (
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
        {...moveHandlers}
      >
        <h3 className="font-semibold text-sm select-none">HR 智能助手</h3>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Messages */}
      <ChatMessages messages={messages} onSendMessage={sendMessage} />

      {/* Input */}
      <ChatInput onSend={sendMessage} disabled={isProcessing} />

      {/* Resize handle */}
      <div
        className="absolute bottom-0 right-0 w-4 h-4 cursor-nwse-resize touch-none"
        {...resizeHandlers}
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
  );
}
