import type { ChatMessage } from "@/features/chat/types/chat";
import { EvaluationCard } from "./EvaluationCard";
import { ProgressMessage } from "./ProgressMessage";

interface AssistantMessageProps {
  message: ChatMessage;
}

export function AssistantMessage({ message }: AssistantMessageProps) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] bg-muted rounded-2xl rounded-bl-sm px-3.5 py-2.5">
        {message.progress ? (
          <ProgressMessage progress={message.progress} />
        ) : (
          <>
            <p className="text-sm whitespace-pre-wrap leading-relaxed">
              {message.content}
            </p>
            {message.cards?.map((card, i) => (
              <EvaluationCard key={i} card={card} />
            ))}
          </>
        )}
      </div>
    </div>
  );
}
