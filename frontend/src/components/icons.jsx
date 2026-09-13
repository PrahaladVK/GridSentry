const base = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

export function IconGrid(props) {
  return (
    <svg {...base} {...props}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  );
}

export function IconTrendingUp(props) {
  return (
    <svg {...base} {...props}>
      <polyline points="3 17 9 11 13 15 21 6" />
      <polyline points="14 6 21 6 21 13" />
    </svg>
  );
}

export function IconAlertTriangle(props) {
  return (
    <svg {...base} {...props}>
      <path d="M10.3 3.9 2.6 18a1.6 1.6 0 0 0 1.4 2.4h16a1.6 1.6 0 0 0 1.4-2.4L13.7 3.9a1.6 1.6 0 0 0-2.8 0Z" />
      <line x1="12" y1="9.5" x2="12" y2="13.5" />
      <line x1="12" y1="16.5" x2="12.01" y2="16.5" />
    </svg>
  );
}

export function IconClipboard(props) {
  return (
    <svg {...base} {...props}>
      <rect x="5" y="4" width="14" height="17" rx="2" />
      <path d="M9 4V3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1" />
      <line x1="8" y1="10" x2="16" y2="10" />
      <line x1="8" y1="14" x2="16" y2="14" />
      <line x1="8" y1="18" x2="13" y2="18" />
    </svg>
  );
}

export function IconFlask(props) {
  return (
    <svg {...base} {...props}>
      <path d="M9 3h6" />
      <path d="M10 3v6.2L4.6 18a2 2 0 0 0 1.7 3h11.4a2 2 0 0 0 1.7-3L14 9.2V3" />
      <line x1="7.5" y1="14.5" x2="16.5" y2="14.5" />
    </svg>
  );
}

export function IconShield(props) {
  return (
    <svg {...base} {...props}>
      <path d="M12 2.5 5 5.2v6c0 4.7 3 8.2 7 9.3 4-1.1 7-4.6 7-9.3v-6L12 2.5Z" />
      <polyline points="9 12 11.2 14.2 15.5 9.5" />
    </svg>
  );
}

export function IconSnowflake(props) {
  return (
    <svg {...base} {...props}>
      <line x1="12" y1="2" x2="12" y2="22" />
      <line x1="5" y1="7" x2="19" y2="17" />
      <line x1="19" y1="7" x2="5" y2="17" />
    </svg>
  );
}

export function IconMoon(props) {
  return (
    <svg {...base} {...props}>
      <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z" />
    </svg>
  );
}

export function IconBarChart(props) {
  return (
    <svg {...base} {...props}>
      <line x1="4" y1="20" x2="20" y2="20" />
      <rect x="6" y="12" width="3" height="8" />
      <rect x="10.5" y="7" width="3" height="13" />
      <rect x="15" y="4" width="3" height="16" />
    </svg>
  );
}

export function IconRefresh(props) {
  return (
    <svg {...base} {...props}>
      <polyline points="23 4 23 10 17 10" />
      <polyline points="1 20 1 14 7 14" />
      <path d="M3.5 9a8.5 8.5 0 0 1 14.6-4.6L23 10" />
      <path d="M20.5 15a8.5 8.5 0 0 1-14.6 4.6L1 14" />
    </svg>
  );
}

export function IconWrench(props) {
  return (
    <svg {...base} {...props}>
      <path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L4 17l3 3 5.3-5.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2-2 2.6-2.6Z" />
    </svg>
  );
}
