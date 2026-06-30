import { useCallback, useEffect, useRef, useState } from "react";

interface Position {
  x: number;
  y: number;
}

interface Size {
  width: number;
  height: number;
}

interface BubblePosition {
  side: "left" | "right";
  offset: number;  // horizontal offset from the edge
  top: number;     // vertical position from top of viewport
}

const BUBBLE_SIZE = 48;
const EDGE_MARGIN = 24;
const MIN_TOP = 24;
const DRAG_THRESHOLD = 5; // px to distinguish drag from click

const CHAT_WINDOW_MIN_SIZE: Size = { width: 320, height: 400 };
const CHAT_WINDOW_MAX_SIZE: Size = { width: 800, height: 700 };

function loadJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

/** Hook for draggable chat bubble — free drag, horizontal edge snap, vertical keep */
export function useBubbleDrag() {
  const defaultTop = typeof window !== "undefined"
    ? window.innerHeight - BUBBLE_SIZE - EDGE_MARGIN
    : 600;

  const [position, setPosition] = useState<BubblePosition>(
    () => loadJson("chat-bubble-position", {
      side: "right" as const,
      offset: EDGE_MARGIN,
      top: defaultTop,
    })
  );
  const [isDragging, setIsDragging] = useState(false);
  const startX = useRef(0);
  const startY = useRef(0);
  const startOffset = useRef(0);
  const startTop = useRef(0);

  // Callback for window position updates when bubble moves
  const onBubbleMoveRef = useRef<((dx: number, dy: number) => void) | null>(null);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    // Only respond to primary button on the bubble element itself
    if (e.button !== 0) return;
    setIsDragging(true);
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    startX.current = e.clientX;
    startY.current = e.clientY;
    startOffset.current = position.offset;
    startTop.current = position.top;
  }, [position.offset, position.top]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!isDragging) return;
    const dx = e.clientX - startX.current;
    const dy = e.clientY - startY.current;

    // Use threshold to distinguish drag from click/text-selection
    if (Math.abs(dx) <= DRAG_THRESHOLD && Math.abs(dy) <= DRAG_THRESHOLD) return;

    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    // Calculate new horizontal offset
    let newOffset: number;
    if (position.side === "right") {
      newOffset = Math.max(EDGE_MARGIN, Math.min(
        viewportWidth - EDGE_MARGIN - BUBBLE_SIZE,
        startOffset.current - dx,
      ));
    } else {
      newOffset = Math.max(EDGE_MARGIN, Math.min(
        viewportWidth - EDGE_MARGIN - BUBBLE_SIZE,
        startOffset.current + dx,
      ));
    }

    // Calculate new vertical position (free)
    const newTop = Math.max(MIN_TOP, Math.min(
      viewportHeight - BUBBLE_SIZE - EDGE_MARGIN,
      startTop.current + dy,
    ));

    setPosition((prev) => ({ ...prev, offset: newOffset, top: newTop }));

    // Notify window to follow
    if (onBubbleMoveRef.current) {
      onBubbleMoveRef.current(
        newOffset - startOffset.current,
        newTop - startTop.current,
      );
    }
  }, [position.side, isDragging]);

  const handlePointerUp = useCallback(() => {
    if (!isDragging) return;
    setIsDragging(false);

    // Use functional setState to read latest position (avoids stale closure)
    setPosition((prev) => {
      const viewportWidth = window.innerWidth;

      let newSide: "left" | "right";
      if (prev.side === "right") {
        const distanceFromRight = prev.offset;
        const distanceFromLeft = viewportWidth - prev.offset - BUBBLE_SIZE;
        newSide = distanceFromLeft < distanceFromRight ? "left" : "right";
      } else {
        const distanceFromLeft = prev.offset;
        const distanceFromRight = viewportWidth - prev.offset - BUBBLE_SIZE;
        newSide = distanceFromRight < distanceFromLeft ? "right" : "left";
      }

      return {
        ...prev,
        side: newSide,
        offset: EDGE_MARGIN,
      };
    });
  }, [isDragging]);

  // Persist to localStorage on change
  useEffect(() => {
    localStorage.setItem("chat-bubble-position", JSON.stringify(position));
  }, [position]);

  const style: React.CSSProperties =
    position.side === "right"
      ? { position: "fixed", top: position.top, right: position.offset, zIndex: 40 }
      : { position: "fixed", top: position.top, left: position.offset, zIndex: 40 };

  const snapping = !isDragging;

  return {
    style: {
      ...style,
      transition: snapping ? "right 0.3s ease, left 0.3s ease" : "none",
    },
    handlers: {
      onPointerDown: handlePointerDown,
      onPointerMove: handlePointerMove,
      onPointerUp: handlePointerUp,
    },
    side: position.side,
    top: position.top,
    isDragging,
    onBubbleMoveRef,
  };
}

/** Hook for movable + resizable chat window, with bubble-follow support */
export function useChatWindowDragResize(
  bubbleSide: "left" | "right",
  bubbleTop: number,
  onBubbleMoveRef: React.MutableRefObject<((dx: number, dy: number) => void) | null>,
) {
  const [state, setState] = useState<{ position: Position; size: Size }>(() => {
    const saved = loadJson<{ position: Position; size: Size } | null>("chat-window-state", null);
    if (saved) return saved;
    const vw = typeof window !== "undefined" ? window.innerWidth : 1024;
    const vh = typeof window !== "undefined" ? window.innerHeight : 768;
    const defaultSize = { width: 380, height: 520 };
    const defaultPos: Position =
      bubbleSide === "right"
        ? { x: vw - defaultSize.width - EDGE_MARGIN, y: vh - defaultSize.height - BUBBLE_SIZE - EDGE_MARGIN * 2 - 16 }
        : { x: EDGE_MARGIN, y: vh - defaultSize.height - BUBBLE_SIZE - EDGE_MARGIN * 2 - 16 };
    return { position: defaultPos, size: defaultSize };
  });

  // Track the offset between window and bubble for follow behavior
  const windowBubbleOffset = useRef({ dx: 0, dy: 0 });

  // Persist to localStorage
  useEffect(() => {
    localStorage.setItem("chat-window-state", JSON.stringify(state));
  }, [state]);

  // Register bubble-move callback so window follows when bubble is dragged
  useEffect(() => {
    onBubbleMoveRef.current = (dx: number, dy: number) => {
      setState((prev) => {
        const newX = prev.position.x + dx;
        const newY = prev.position.y + dy;
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        return {
          ...prev,
          position: {
            x: Math.max(0, Math.min(vw - prev.size.width, newX)),
            y: Math.max(0, Math.min(vh - prev.size.height, newY)),
          },
        };
      });
    };
    return () => {
      onBubbleMoveRef.current = null;
    };
  }, [onBubbleMoveRef]);

  // --- Move logic (window header drag) ---
  const moveDragging = useRef(false);
  const moveStart = useRef({ x: 0, y: 0 });

  const handleMoveStart = useCallback((e: React.PointerEvent) => {
    // Only respond to primary button
    if (e.button !== 0) return;
    moveDragging.current = true;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    moveStart.current = { x: e.clientX - state.position.x, y: e.clientY - state.position.y };

    // Track offset from bubble position
    windowBubbleOffset.current = { dx: state.position.x, dy: state.position.y - bubbleTop };
  }, [state.position, bubbleSide, bubbleTop]);

  const handleMove = useCallback((e: React.PointerEvent) => {
    if (!moveDragging.current) return;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const newX = Math.max(0, Math.min(vw - state.size.width, e.clientX - moveStart.current.x));
    const newY = Math.max(0, Math.min(vh - state.size.height, e.clientY - moveStart.current.y));
    setState((prev) => ({ ...prev, position: { x: newX, y: newY } }));

    // Update offset for future bubble-follow
    windowBubbleOffset.current = { dx: newX, dy: newY - bubbleTop };
  }, [state.size, bubbleTop]);

  const handleMoveEnd = useCallback(() => {
    moveDragging.current = false;
  }, []);

  // --- Resize logic ---
  const resizeDragging = useRef(false);
  const resizeStart = useRef({ x: 0, y: 0, width: 0, height: 0 });

  const handleResizeStart = useCallback((e: React.PointerEvent) => {
    e.stopPropagation();
    resizeDragging.current = true;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    resizeStart.current = { x: e.clientX, y: e.clientY, width: state.size.width, height: state.size.height };
  }, [state.size]);

  const handleResize = useCallback((e: React.PointerEvent) => {
    if (!resizeDragging.current) return;
    const dx = e.clientX - resizeStart.current.x;
    const dy = e.clientY - resizeStart.current.y;
    const newWidth = Math.max(CHAT_WINDOW_MIN_SIZE.width, Math.min(CHAT_WINDOW_MAX_SIZE.width, resizeStart.current.width + dx));
    const newHeight = Math.max(CHAT_WINDOW_MIN_SIZE.height, Math.min(CHAT_WINDOW_MAX_SIZE.height, resizeStart.current.height + dy));
    setState((prev) => ({ ...prev, size: { width: newWidth, height: newHeight } }));
  }, []);

  const handleResizeEnd = useCallback(() => {
    resizeDragging.current = false;
  }, []);

  return {
    position: state.position,
    size: state.size,
    moveHandlers: {
      onPointerDown: handleMoveStart,
      onPointerMove: handleMove,
      onPointerUp: handleMoveEnd,
    },
    resizeHandlers: {
      onPointerDown: handleResizeStart,
      onPointerMove: handleResize,
      onPointerUp: handleResizeEnd,
    },
  };
}
