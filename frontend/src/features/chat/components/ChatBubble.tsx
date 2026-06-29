import { useRef, useState } from "react";
import { MessageCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ChatWindow } from "./ChatWindow";
import { useBubbleDrag } from "@/features/chat/hooks/useDragResize";

export function ChatBubble() {
  const [isOpen, setIsOpen] = useState(false);
  const { style, handlers, side } = useBubbleDrag();
  const didDrag = useRef(false);
  const pointerStartPos = useRef({ x: 0, y: 0 });

  const handlePointerDown = (e: React.PointerEvent) => {
    didDrag.current = false;
    pointerStartPos.current = { x: e.clientX, y: e.clientY };
    handlers.onPointerDown(e);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    const dx = Math.abs(e.clientX - pointerStartPos.current.x);
    if (dx > 5) didDrag.current = true;
    handlers.onPointerMove(e);
  };

  const handlePointerUp = () => {
    handlers.onPointerUp();
  };

  const handleClick = () => {
    if (!didDrag.current) setIsOpen(!isOpen);
  };

  return (
    <div style={style} onPointerDown={handlePointerDown} onPointerMove={handlePointerMove} onPointerUp={handlePointerUp} className="touch-none">
      {isOpen && <ChatWindow onClose={() => setIsOpen(false)} bubbleSide={side} />}
      <Button
        size="icon"
        className="h-12 w-12 rounded-full shadow-lg touch-none"
        onClick={handleClick}
      >
        <MessageCircle className="h-6 w-6" />
      </Button>
    </div>
  );
}
