import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useChat } from "@/features/chat/hooks/useChat";
import { ChatMessages } from "./ChatMessages";
import { ChatInput } from "./ChatInput";

interface ChatWindowProps {
  onClose: () => void;
}

export function ChatWindow({ onClose }: ChatWindowProps) {
  const { messages, isProcessing, sendMessage } = useChat();

  return (
    <div className="absolute bottom-16 right-0 w-[380px] h-[520px] bg-card border rounded-xl shadow-xl flex flex-col overflow-hidden z-50">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-primary/5">
        <h3 className="font-semibold text-sm">HR 智能助手</h3>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Messages */}
      <ChatMessages messages={messages} />

      {/* Input */}
      <ChatInput onSend={sendMessage} disabled={isProcessing} />
    </div>
  );
}
