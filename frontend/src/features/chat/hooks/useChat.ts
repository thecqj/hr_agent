import { useState, useRef, useCallback } from "react";

import type { ChatMessage, ChatCard, ProgressInfo } from "@/features/chat/types/chat";
import { sendChatMessage } from "@/features/chat/api/chat";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback((text: string) => {
    if (isProcessing) return;

    // Add user message
    const userMsg: ChatMessage = {
      role: "user",
      content: text,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsProcessing(true);

    // Track the current assistant message being built
    let assistantContent = "";
    let assistantCards: ChatCard[] | undefined;
    let assistantProgress: ProgressInfo | undefined;

    const controller = sendChatMessage(
      text,
      (eventType, data) => {
        switch (eventType) {
          case "thinking":
            assistantContent = (data.status as string) || "思考中...";
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent,
                  progress: { status: assistantContent },
                };
              } else {
                updated.push({
                  role: "assistant",
                  content: assistantContent,
                  progress: { status: assistantContent },
                  timestamp: Date.now(),
                });
              }
              return updated;
            });
            break;

          case "intent":
            assistantContent = "正在处理您的请求...";
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent,
                  progress: { status: assistantContent },
                };
              }
              return updated;
            });
            break;

          case "progress":
            assistantProgress = {
              status: (data.status as string) || "处理中...",
              evaluated_count: data.evaluated_count as number | undefined,
              total_count: data.total_count as number | undefined,
            };
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantProgress!.status,
                  progress: assistantProgress,
                };
              }
              return updated;
            });
            break;

          case "result":
            assistantContent = (data.reply_message as string) || "";
            assistantCards = data.cards as ChatCard[] | undefined;
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent,
                  cards: assistantCards,
                  progress: undefined,
                  timestamp: Date.now(),
                };
              }
              return updated;
            });
            break;

          case "error":
            assistantContent = `❌ ${(data.message as string) || "发生错误"}`;
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent,
                  progress: undefined,
                  timestamp: Date.now(),
                };
              }
              return updated;
            });
            break;
        }
      },
      (error) => {
        const errorMsg: ChatMessage = {
          role: "assistant",
          content: `❌ 连接中断：${error.message}`,
          timestamp: Date.now(),
        };
        setMessages((prev) => {
          // Remove any in-progress assistant message
          const filtered = prev.filter(
            (m) => !(m.role === "assistant" && m.progress)
          );
          return [...filtered, errorMsg];
        });
        setIsProcessing(false);
      },
      () => {
        setIsProcessing(false);
        abortControllerRef.current = null;
      },
    );

    abortControllerRef.current = controller;
  }, [isProcessing]);

  const disconnect = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsProcessing(false);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    isProcessing,
    sendMessage,
    disconnect,
    clearMessages,
  };
}
