'use client';

import { type MouseEvent, type ReactNode, useRef } from 'react';

interface GlowingShadowProps {
  children: ReactNode;
}

export function GlowingShadow({ children }: GlowingShadowProps) {
  const cardRef = useRef<HTMLDivElement>(null);

  const handleMouseMove = (event: MouseEvent<HTMLDivElement>) => {
    const card = cardRef.current;
    if (!card) return;

    const rect = card.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;
    card.style.setProperty('--glow-x', `${x}%`);
    card.style.setProperty('--glow-y', `${y}%`);
    card.style.setProperty('--glow-opacity', '1');
  };

  const handleMouseLeave = () => {
    const card = cardRef.current;
    if (!card) return;
    card.style.setProperty('--glow-opacity', '0');
    card.style.setProperty('--glow-x', '50%');
    card.style.setProperty('--glow-y', '50%');
  };

  return (
    <>
      <style jsx>{`
        .glow-card {
          --card-radius: 0.75rem;
          --border-width: 1px;
          --glow-x: 50%;
          --glow-y: 50%;
          --glow-opacity: 0;
          --border-color: rgba(15, 23, 42, 0.08);
          --glow-color: rgba(56, 189, 248, 0.75);
          position: relative;
          border-radius: var(--card-radius);
          padding: var(--border-width);
          background: radial-gradient(
              240px circle at var(--glow-x) var(--glow-y),
              var(--glow-color),
              transparent 65%
            ),
            linear-gradient(var(--border-color), var(--border-color));
          transition: box-shadow 0.25s ease, background 0.25s ease;
        }

        .glow-card:hover {
          box-shadow: 0 12px 32px rgba(56, 189, 248, 0.28);
        }

        .glow-card::before {
          content: '';
          position: absolute;
          inset: 0;
          border-radius: inherit;
          background: radial-gradient(
            220px circle at var(--glow-x) var(--glow-y),
            rgba(125, 211, 252, 0.95),
            transparent 65%
          );
          opacity: var(--glow-opacity);
          transition: opacity 0.25s ease;
          pointer-events: none;
        }

        .glow-card-content {
          position: relative;
          background: white;
          border-radius: calc(var(--card-radius) - var(--border-width));
          overflow: hidden;
          height: 100%;
        }

        :global(.dark) .glow-card {
          --border-color: rgba(148, 163, 184, 0.18);
          --glow-color: rgba(56, 189, 248, 0.7);
        }

        :global(.dark) .glow-card-content {
          background: rgb(9 9 11);
        }
      `}</style>

      <div
        ref={cardRef}
        className="glow-card"
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        <div className="glow-card-content">{children}</div>
      </div>
    </>
  );
}
