import { useRef, useState, useEffect } from "react";
import { MessageCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ChatWindow } from "./ChatWindow";
import { useBubbleDrag } from "@/features/chat/hooks/useDragResize";
import { useChat } from "@/features/chat/hooks/useChat";

export function ChatBubble() {
  const [isOpen, setIsOpen] = useState(false);
  const {
    style,
    handlers,
    side,
    top,
    isDragging: bubbleIsDragging,
    onBubbleMoveRef,
  } = useBubbleDrag();

  const chat = useChat();

  // Validate session on first open
  const hasValidated = useRef(false);
  useEffect(() => {
    if (isOpen && !hasValidated.current) {
      hasValidated.current = true;
      chat.validateSession();
    }
  }, [isOpen, chat.validateSession]);

  const didDrag = useRef(false);
  const pointerStartPos = useRef({ x: 0, y: 0 });

  const handlePointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    // Prevent event from propagating to window underneath
    e.stopPropagation();
    didDrag.current = false;
    pointerStartPos.current = { x: e.clientX, y: e.clientY };
    handlers.onPointerDown(e);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    const dx = Math.abs(e.clientX - pointerStartPos.current.x);
    const dy = Math.abs(e.clientY - pointerStartPos.current.y);
    if (dx > 5 || dy > 5) didDrag.current = true;
    handlers.onPointerMove(e);
  };

  const handlePointerUp = () => {
    handlers.onPointerUp();
    // Toggle open/close on click (non-drag). We must do this in pointerUp
    // instead of onClick because setPointerCapture on the outer div causes
    // the browser click event to fire on the div, not the Button child.
    if (!didDrag.current) {
      setIsOpen((prev) => !prev);
    }
  };

  return (
    <>
      {isOpen && (
        <ChatWindow
          onMinimize={() => setIsOpen(false)}
          onClose={chat.closeSession}
          bubbleSide={side}
          bubbleTop={top}
          onBubbleMoveRef={onBubbleMoveRef}
          chat={chat}
        />
      )}
      <div
        style={style}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        className="touch-none"
      >
        <Button
          size="icon"
          className="h-12 w-12 rounded-full shadow-lg touch-none"
        >
          <MessageCircle className="h-6 w-6" />
        </Button>
      </div>
    </>
  );
}
