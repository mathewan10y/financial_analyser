import { useState, useEffect, useRef } from 'react';

interface TypewriterTextProps {
  text: string;
  speed?: number;
  onComplete?: () => void;
  className?: string;
}

export default function TypewriterText({
  text,
  speed = 12,
  onComplete,
  className = '',
}: TypewriterTextProps) {
  const [displayedLength, setDisplayedLength] = useState(0);
  const textRef = useRef(text);
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    textRef.current = text;
    setDisplayedLength(0);

    if (!text) return;

    let currentIndex = 0;
    const interval = setInterval(() => {
      currentIndex += 1;
      setDisplayedLength(currentIndex);

      if (currentIndex >= text.length) {
        clearInterval(interval);
        onCompleteRef.current?.();
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed]);

  const handleFlush = () => {
    setDisplayedLength(text.length);
    onCompleteRef.current?.();
  };

  const isTyping = displayedLength < text.length;
  const currentText = text.slice(0, displayedLength);

  return (
    <span
      onClick={handleFlush}
      title={isTyping ? "Click to reveal full text" : undefined}
      className={`cursor-pointer select-text ${className}`}
    >
      {currentText}
      {isTyping && (
        <span className="inline-block text-emerald-400 font-bold ml-0.5 animate-pulse">
          ▊
        </span>
      )}
    </span>
  );
}
