const base = { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true } as const;

export const SparkIcon = () => (
  <svg {...base} strokeWidth={2}><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" /></svg>
);
export const SendIcon = () => (
  <svg {...base} strokeWidth={2.4}><path d="M12 19V5M5 12l7-7 7 7" /></svg>
);
export const BackIcon = () => (
  <svg {...base} strokeWidth={2.2}><path d="m15 18-6-6 6-6" /></svg>
);
export const PinIcon = () => (
  <svg {...base} strokeWidth={2}><path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z" /><circle cx="12" cy="10" r="2.5" /></svg>
);
export const ImageIcon = () => (
  <svg {...base} strokeWidth={1.7}><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="9" cy="10" r="1.6" /><path d="m21 16-5-5-8 8" /></svg>
);
export const LocateIcon = () => (
  <svg {...base} strokeWidth={2}><circle cx="12" cy="12" r="9" /><path d="m15.5 8.5-2 5-5 2 2-5 5-2Z" /></svg>
);
