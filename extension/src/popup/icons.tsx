import React from "react";

interface IconProps {
  size?: number;
}

const baseProps = {
  fill: "none" as const,
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export const Mic = ({ size = 14 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" {...baseProps} aria-hidden>
    <rect x="9" y="2" width="6" height="12" rx="3" />
    <path d="M5 11a7 7 0 0 0 14 0" />
    <line x1="12" y1="18" x2="12" y2="22" />
    <line x1="8" y1="22" x2="16" y2="22" />
  </svg>
);

export const MicOff = ({ size = 14 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" {...baseProps} aria-hidden>
    <line x1="2" y1="2" x2="22" y2="22" />
    <path d="M9 5a3 3 0 0 1 6 0v6" />
    <path d="M15 13.5A3 3 0 0 1 9 13V9" />
    <path d="M19 11a7 7 0 0 1-1.05 3.7" />
    <path d="M5 11a7 7 0 0 0 11.4 5.4" />
    <line x1="12" y1="18" x2="12" y2="22" />
    <line x1="8" y1="22" x2="16" y2="22" />
  </svg>
);

export const ChevronRight = ({ size = 12 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" {...baseProps} aria-hidden>
    <polyline points="9 6 15 12 9 18" />
  </svg>
);

export const ChevronDown = ({ size = 12 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" {...baseProps} aria-hidden>
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

export const Check = ({ size = 11 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <polyline points="20 6 9 17 4 12" />
  </svg>
);
