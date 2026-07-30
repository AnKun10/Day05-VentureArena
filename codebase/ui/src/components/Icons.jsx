// ============================================================
// ICON SET — thay toàn bộ emoji ở phần "khung" của app (nav, nút, nhãn).
// Emoji render khác nhau trên mỗi hệ điều hành và không canh được baseline;
// icon stroke 1.75 / viewBox 24 cho nét đồng đều ở mọi cỡ.
// Dùng: <Icon.Calendar className="h-4 w-4" />
// ============================================================

function Svg({ children, className = "h-4 w-4", ...rest }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  );
}

const Icon = {
  News: (p) => (
    <Svg {...p}>
      <path d="M4 5.5A1.5 1.5 0 0 1 5.5 4h9A1.5 1.5 0 0 1 16 5.5V18a2 2 0 0 0 2 2H6a2 2 0 0 1-2-2z" />
      <path d="M16 8h2.5A1.5 1.5 0 0 1 20 9.5V18a2 2 0 0 1-2 2" />
      <path d="M7.5 8h5M7.5 11.5h5M7.5 15h3" />
    </Svg>
  ),
  Calendar: (p) => (
    <Svg {...p}>
      <rect x="3.5" y="5" width="17" height="15.5" rx="2.5" />
      <path d="M3.5 9.5h17M8 3.5v3M16 3.5v3" />
    </Svg>
  ),
  Library: (p) => (
    <Svg {...p}>
      <path d="M3.5 7.5A2 2 0 0 1 5.5 5.5h3.2a2 2 0 0 1 1.6.8l.9 1.2h5.3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-11a2 2 0 0 1-2-2z" />
    </Svg>
  ),
  Search: (p) => (
    <Svg {...p}>
      <circle cx="11" cy="11" r="6.25" />
      <path d="m20 20-3.6-3.6" />
    </Svg>
  ),
  Bell: (p) => (
    <Svg {...p}>
      <path d="M18 8.5a6 6 0 1 0-12 0c0 4.2-1.5 5.5-1.5 5.5h15S18 12.7 18 8.5" />
      <path d="M10.3 18a2 2 0 0 0 3.4 0" />
    </Svg>
  ),
  Help: (p) => (
    <Svg {...p}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M9.8 9.6a2.3 2.3 0 1 1 3.1 2.2c-.6.3-.9.8-.9 1.5v.3" />
      <path d="M12 17h.01" />
    </Svg>
  ),
  Chat: (p) => (
    <Svg {...p}>
      <path d="M20 12.5c0 3.9-3.6 7-8 7a9 9 0 0 1-2.6-.4L5 20.5l1.2-3.2A6.6 6.6 0 0 1 4 12.5c0-3.9 3.6-7 8-7s8 3.1 8 7" />
    </Svg>
  ),
  Send: (p) => (
    <Svg {...p}>
      <path d="M20 4 10.5 13.5" />
      <path d="M20 4l-6 16-3.5-6.5L4 10z" />
    </Svg>
  ),
  Close: (p) => (
    <Svg {...p}>
      <path d="M6.5 6.5 17.5 17.5M17.5 6.5 6.5 17.5" />
    </Svg>
  ),
  ChevronLeft: (p) => (
    <Svg {...p}>
      <path d="m14 6-6 6 6 6" />
    </Svg>
  ),
  ChevronRight: (p) => (
    <Svg {...p}>
      <path d="m10 6 6 6-6 6" />
    </Svg>
  ),
  ChevronDown: (p) => (
    <Svg {...p}>
      <path d="m6 9.5 6 6 6-6" />
    </Svg>
  ),
  ArrowRight: (p) => (
    <Svg {...p}>
      <path d="M4.5 12h15M13.5 6l6 6-6 6" />
    </Svg>
  ),
  External: (p) => (
    <Svg {...p}>
      <path d="M14 4.5h5.5V10" />
      <path d="M19.5 4.5 11 13" />
      <path d="M18 14.5v4a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6h4" />
    </Svg>
  ),
  Heart: (p) => (
    <Svg {...p}>
      <path d="M12 19s-6.8-4-6.8-8.4A3.7 3.7 0 0 1 12 8.4a3.7 3.7 0 0 1 6.8 2.2C18.8 15 12 19 12 19" />
    </Svg>
  ),
  Comment: (p) => (
    <Svg {...p}>
      <path d="M20 12c0 3.9-3.6 7-8 7a9 9 0 0 1-2.6-.4L5 20l1.2-3.2A6.6 6.6 0 0 1 4 12c0-3.9 3.6-7 8-7s8 3.1 8 7" />
    </Svg>
  ),
  Flame: (p) => (
    <Svg {...p}>
      <path d="M12 3.5s4.8 3.2 4.8 7.6c0 1.3-.5 2.3-1.2 3 .1-1.6-.8-3-2.1-3.7.3 1.9-.9 2.9-1.8 3.7-1 .9-1.6 1.7-1.6 3 0 1.9 1.7 3.4 3.9 3.4-3.8.6-6.8-1.7-6.8-5 0-4.6 4.8-5.5 4.8-12" />
    </Svg>
  ),
  Clock: (p) => (
    <Svg {...p}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 1.8" />
    </Svg>
  ),
  Pin: (p) => (
    <Svg {...p}>
      <path d="M12 21s6-5.3 6-10a6 6 0 1 0-12 0c0 4.7 6 10 6 10" />
      <circle cx="12" cy="11" r="2.3" />
    </Svg>
  ),
  Video: (p) => (
    <Svg {...p}>
      <rect x="3" y="6" width="12.5" height="12" rx="2.5" />
      <path d="m15.5 10.5 5-2.7v8.4l-5-2.7z" />
    </Svg>
  ),
  Slides: (p) => (
    <Svg {...p}>
      <rect x="3.5" y="4.5" width="17" height="11" rx="2" />
      <path d="M12 15.5v4M8.5 19.5h7" />
    </Svg>
  ),
  Doc: (p) => (
    <Svg {...p}>
      <path d="M13.5 3.5H7A1.5 1.5 0 0 0 5.5 5v14A1.5 1.5 0 0 0 7 20.5h10a1.5 1.5 0 0 0 1.5-1.5V8.5z" />
      <path d="M13.5 3.5v5h5M9 13h6M9 16.5h4" />
    </Svg>
  ),
  Link: (p) => (
    <Svg {...p}>
      <path d="M10 13.5a3.5 3.5 0 0 0 5 .3l2.5-2.5a3.5 3.5 0 0 0-5-5L11 7.8" />
      <path d="M14 10.5a3.5 3.5 0 0 0-5-.3L6.5 12.7a3.5 3.5 0 0 0 5 5l1.4-1.5" />
    </Svg>
  ),
  Check: (p) => (
    <Svg {...p}>
      <path d="m5 12.5 4.5 4.5L19 7.5" />
    </Svg>
  ),
  Alert: (p) => (
    <Svg {...p}>
      <path d="M10.6 4.4 3.3 17a1.6 1.6 0 0 0 1.4 2.4h14.6a1.6 1.6 0 0 0 1.4-2.4L13.4 4.4a1.6 1.6 0 0 0-2.8 0" />
      <path d="M12 9.5v4M12 16.8h.01" />
    </Svg>
  ),
  Ban: (p) => (
    <Svg {...p}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="m6 6 12 12" />
    </Svg>
  ),
  Inbox: (p) => (
    <Svg {...p}>
      <path d="M3.5 13.5h4l1.3 2.4h6.4l1.3-2.4h4" />
      <path d="M5.9 5.5h12.2a1.5 1.5 0 0 1 1.4 1l1 7v4a1.5 1.5 0 0 1-1.5 1.5h-14A1.5 1.5 0 0 1 3.5 17.5v-4l1-7a1.5 1.5 0 0 1 1.4-1" />
    </Svg>
  ),
  Filter: (p) => (
    <Svg {...p}>
      <path d="M4 6.5h16M7 12h10M10 17.5h4" />
    </Svg>
  ),
  Sparkle: (p) => (
    <Svg {...p}>
      <path d="M12 4.5 13.6 9 18 10.5 13.6 12 12 16.5 10.4 12 6 10.5 10.4 9z" />
      <path d="M18.5 16.5 19.2 18.4 21 19l-1.8.7-.7 1.8-.7-1.8L16 19l1.8-.6z" />
    </Svg>
  ),
  User: (p) => (
    <Svg {...p}>
      <circle cx="12" cy="8.5" r="3.75" />
      <path d="M5 20a7 7 0 0 1 14 0" />
    </Svg>
  ),
  Dots: (p) => (
    <Svg {...p}>
      <circle cx="12" cy="5.5" r="1.2" fill="currentColor" stroke="none" />
      <circle cx="12" cy="12" r="1.2" fill="currentColor" stroke="none" />
      <circle cx="12" cy="18.5" r="1.2" fill="currentColor" stroke="none" />
    </Svg>
  ),
  Bot: (p) => (
    <Svg {...p}>
      <rect x="4" y="7.5" width="16" height="11.5" rx="3" />
      <path d="M12 3.5v4M8.8 12.5h.01M15.2 12.5h.01M9.5 16h5" />
    </Svg>
  ),
};

export default Icon;