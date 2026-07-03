import { useEffect, useRef } from "react";

import type { ChatMessage } from "@/features/chat/types/chat";
import { AssistantMessage } from "./AssistantMessage";

interface ChatMessagesProps {
  messages: ChatMessage[];
}

export function ChatMessages({ messages }: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-3">
      {messages.length === 0 && (
        <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
          👋 你好！我是 HR 智能助手，可以帮你查询岗位、筛选简历、评估候选人。有什么我能帮你的吗？
        </div>
      )}
      {messages.map((msg, i) =>
        msg.role === "user" ? (
          <div key={i} className="flex justify-end">
            <div className="max-w-[85%] bg-primary text-primary-foreground rounded-2xl rounded-br-sm px-3.5 py-2.5">
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ) : (
          <AssistantMessage key={i} message={msg} />
        )
      )}
      <div ref={bottomRef} />
    </div>
  );
}
