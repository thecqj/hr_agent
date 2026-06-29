import { useCallback, useEffect, useRef, useState } from "react";

interface Position {
  x: number;
  y: number;
}

interface Size {
  width: number;
  height: number;
}

const BUBBLE_SIZE = 48; // h-12 w-12 = 48px
const EDGE_MARGIN = 24;

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

/** Hook for draggable chat bubble — horizontal drag only, snaps to nearest edge */
export function useBubbleDrag() {
  const [position, setPosition] = useState<{ side: "left" | "right"; offset: number }>(
    () => loadJson("chat-bubble-position", { side: "right", offset: EDGE_MARGIN })
  );
  const [isDragging, setIsDragging] = useState(false);
  const startX = useRef(0);
  const startOffset = useRef(0);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    setIsDragging(true);
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    startX.current = e.clientX;
    startOffset.current = position.offset;
  }, [position.offset]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!isDragging) return;
    const dx = e.clientX - startX.current;
    const viewportWidth = window.innerWidth;

    if (position.side === "right") {
      // Moving right → offset increases (further from right edge)
      // Moving left → offset decreases (closer to right edge)
      const newOffset = Math.max(EDGE_MARGIN, Math.min(viewportWidth - EDGE_MARGIN - BUBBLE_SIZE, startOffset.current - dx));
      setPosition((prev) => ({ ...prev, offset: newOffset }));
    } else {
      // Left side: offset from left edge
      const newOffset = Math.max(EDGE_MARGIN, Math.min(viewportWidth - EDGE_MARGIN - BUBBLE_SIZE, startOffset.current + dx));
      setPosition((prev) => ({ ...prev, offset: newOffset }));
    }
  }, [position.side, isDragging]);

  const handlePointerUp = useCallback(() => {
    if (!isDragging) return;
    setIsDragging(false);
    const viewportWidth = window.innerWidth;

    // Snap to nearest edge
    if (position.side === "right") {
      const distanceFromRight = position.offset;
      const distanceFromLeft = viewportWidth - position.offset - BUBBLE_SIZE;
      if (distanceFromLeft < distanceFromRight) {
        setPosition({ side: "left", offset: EDGE_MARGIN });
      } else {
        setPosition({ side: "right", offset: EDGE_MARGIN });
      }
    } else {
      const distanceFromLeft = position.offset;
      const distanceFromRight = viewportWidth - position.offset - BUBBLE_SIZE;
      if (distanceFromRight < distanceFromLeft) {
        setPosition({ side: "right", offset: EDGE_MARGIN });
      } else {
        setPosition({ side: "left", offset: EDGE_MARGIN });
      }
    }
  }, [position.side, position.offset, isDragging]);

  // Persist to localStorage on change
  useEffect(() => {
    localStorage.setItem("chat-bubble-position", JSON.stringify(position));
  }, [position]);

  const style: React.CSSProperties =
    position.side === "right"
      ? { position: "fixed", bottom: EDGE_MARGIN, right: position.offset, zIndex: 40 }
      : { position: "fixed", bottom: EDGE_MARGIN, left: position.offset, zIndex: 40 };

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
  };
}

/** Hook for movable + resizable chat window */
export function useChatWindowDragResize(bubbleSide: "left" | "right") {
  const [state, setState] = useState<{ position: Position; size: Size }>(() => {
    const saved = loadJson<{ position: Position; size: Size } | null>("chat-window-state", null);
    if (saved) return saved;
    // Compute default position
    const vw = typeof window !== "undefined" ? window.innerWidth : 1024;
    const vh = typeof window !== "undefined" ? window.innerHeight : 768;
    const defaultSize = { width: 380, height: 520 };
    const defaultPos: Position =
      bubbleSide === "right"
        ? { x: vw - defaultSize.width - EDGE_MARGIN, y: vh - defaultSize.height - BUBBLE_SIZE - EDGE_MARGIN * 2 - 16 }
        : { x: EDGE_MARGIN, y: vh - defaultSize.height - BUBBLE_SIZE - EDGE_MARGIN * 2 - 16 };
    return { position: defaultPos, size: defaultSize };
  });

  // Persist to localStorage
  useEffect(() => {
    localStorage.setItem("chat-window-state", JSON.stringify(state));
  }, [state]);

  // --- Move logic ---
  const moveDragging = useRef(false);
  const moveStart = useRef({ x: 0, y: 0 });

  const handleMoveStart = useCallback((e: React.PointerEvent) => {
    moveDragging.current = true;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    moveStart.current = { x: e.clientX - state.position.x, y: e.clientY - state.position.y };
  }, [state.position]);

  const handleMove = useCallback((e: React.PointerEvent) => {
    if (!moveDragging.current) return;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const newX = Math.max(0, Math.min(vw - state.size.width, e.clientX - moveStart.current.x));
    const newY = Math.max(0, Math.min(vh - state.size.height, e.clientY - moveStart.current.y));
    setState((prev) => ({ ...prev, position: { x: newX, y: newY } }));
  }, [state.size]);

  const handleMoveEnd = useCallback(() => {
    moveDragging.current = false;
  }, []);

  // --- Resize logic ---
  const resizeDragging = useRef(false);
  const resizeStart = useRef({ x: 0, y: 0, width: 0, height: 0 });

  const handleResizeStart = useCallback((e: React.PointerEvent) => {
    e.stopPropagation();
    resizeDragging.current = true;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
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
