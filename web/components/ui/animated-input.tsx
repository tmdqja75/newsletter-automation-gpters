'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import Image from 'next/image';

export function OrbInput() {
  const [value, setValue] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(true);

  // Keep the placeholders stable across renders
  const placeholders = useMemo(
    () => [
      'Ask anything...',
      "What's on your mind?",
      'How can I help you?',
      'What would you like to know?',
    ],
    []
  );

  // Config: tweak the animation to taste
  const CHAR_DELAY = 75; // ms between characters while typing
  const IDLE_DELAY_AFTER_FINISH = 2200; // ms to wait after a full sentence is shown

  // Refs to hold active timers so they can be cleaned up
  const intervalRef = useRef<number | null>(null);
  const timeoutRef = useRef<number | null>(null);

  useEffect(() => {
    // clear any stale timers (helps with StrictMode double-invoke in dev)
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    const current = placeholders[placeholderIndex];
    if (!current) {
      return;
    }

    const chars = Array.from(current);
    let charIndex = 0;

    // Use requestAnimationFrame to avoid setState during effect initialization
    requestAnimationFrame(() => {
      setDisplayedText('');
      setIsTyping(true);
    });

    // type character-by-character using a derived slice to avoid any chance of appending undefined
    intervalRef.current = window.setInterval(() => {
      if (charIndex < chars.length) {
        const next = chars.slice(0, charIndex + 1).join('');
        setDisplayedText(next);
        charIndex += 1;
      } else {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        setIsTyping(false);

        // after a brief pause, advance to the next placeholder
        timeoutRef.current = window.setTimeout(() => {
          setPlaceholderIndex((prev) => (prev + 1) % placeholders.length);
        }, IDLE_DELAY_AFTER_FINISH);
      }
    }, CHAR_DELAY);

    // Cleanup on unmount or when placeholderIndex changes
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [placeholderIndex, placeholders]);

  return (
    <div className="relative">
      <div
        className={`flex items-center gap-4 rounded-full border border-gray-300 bg-black p-6 shadow-lg transition-all duration-300 ease-out ${
          isFocused ? 'scale-[1.02] border-gray-600 shadow-xl' : 'shadow-lg'
        }`}
      >
        <div className="relative flex-shrink-0">
          <div className="h-16 w-16 scale-100 overflow-hidden rounded-full transition-all duration-300">
            <Image
              src="https://media.giphy.com/media/26gsuUjoEBmLrNBxC/giphy.gif"
              alt="Animated orb"
              width={64}
              height={64}
              className="h-full w-full object-cover"
              unoptimized
            />
          </div>
        </div>

        <div className="h-12 w-px bg-gray-600" />

        <div className="w-[500px] flex-1">
          <input
            data-testid="orb-input"
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={`${displayedText}${isTyping ? '|' : ''}`}
            aria-label="Ask a question"
            className="w-full border-none bg-transparent text-xl font-light text-white placeholder-gray-400 outline-none"
          />
        </div>
      </div>
    </div>
  );
}

export default OrbInput;
