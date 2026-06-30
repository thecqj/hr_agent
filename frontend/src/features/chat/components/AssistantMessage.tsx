import type { ChatCard, ChatMessage } from "@/features/chat/types/chat";
import { EvaluationCard } from "./EvaluationCard";
import { JobListCard } from "./JobListCard";
import { JobDetailCard } from "./JobDetailCard";
import { FunnelCard } from "./FunnelCard";
import { CandidateListCard } from "./CandidateListCard";
import { ConfirmCard } from "./ConfirmCard";
import { ProgressMessage } from "./ProgressMessage";

interface AssistantMessageProps {
  message: ChatMessage;
  onSendMessage?: (text: string) => void;
}

function renderCard(card: ChatCard, onSendMessage?: (text: string) => void) {
  switch (card.type) {
    case "evaluation_summary":
      return <EvaluationCard key={card.type} card={card} />;
    case "job_list":
      return <JobListCard key={card.type} card={card} />;
    case "job_detail":
      return <JobDetailCard key={card.type} card={card} />;
    case "funnel":
      return <FunnelCard key={card.type} card={card} />;
    case "candidate_list":
      return <CandidateListCard key={card.type} card={card} />;
    case "confirm":
      return (
        <ConfirmCard
          key={card.type}
          card={card}
          onConfirm={() => onSendMessage?.("确认")}
          onCancel={() => onSendMessage?.("取消")}
        />
      );
    default: {
      const _exhaustive: never = card;
      return null;
    }
  }
}

export function AssistantMessage({ message, onSendMessage }: AssistantMessageProps) {
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
              <div key={i}>{renderCard(card, onSendMessage)}</div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
