const COVERS: Record<string, React.ReactNode> = {
  "wearable-hub": (
    <svg viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" className="h-full w-full">
      <defs>
        <linearGradient id="cv1" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#1F3A72" />
          <stop offset="100%" stopColor="#06101F" />
        </linearGradient>
      </defs>
      <rect width="320" height="180" fill="url(#cv1)" />
      <circle cx="240" cy="90" r="70" fill="rgba(34,211,183,0.18)" />
      <circle cx="240" cy="90" r="44" fill="rgba(34,211,183,0.32)" />
      <circle cx="240" cy="90" r="20" fill="#22D3B7" />
      <text x="20" y="44" fill="#F7F9FC" fontFamily="Inter Display" fontSize="17" fontWeight="700">
        智能腕环
      </text>
      <text x="20" y="64" fill="#8590A8" fontFamily="Inter" fontSize="10">
        春季发布 · 预告
      </text>
    </svg>
  ),
  bootcamp: (
    <svg viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" className="h-full w-full">
      <defs>
        <linearGradient id="cv2" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#162844" />
          <stop offset="100%" stopColor="#06101F" />
        </linearGradient>
      </defs>
      <rect width="320" height="180" fill="url(#cv2)" />
      <g transform="translate(28 56)">
        <rect width="80" height="68" rx="8" fill="rgba(34,211,183,0.18)" />
        <rect x="100" width="80" height="68" rx="8" fill="rgba(56,189,248,0.18)" />
        <rect x="200" width="80" height="68" rx="8" fill="rgba(167,139,250,0.18)" />
      </g>
      <text x="20" y="40" fill="#F7F9FC" fontFamily="Inter Display" fontSize="17" fontWeight="700">
        销售工程师训练营
      </text>
    </svg>
  ),
  copilot: (
    <svg viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" className="h-full w-full">
      <defs>
        <linearGradient id="cv3" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#093d54" />
          <stop offset="100%" stopColor="#06101F" />
        </linearGradient>
      </defs>
      <rect width="320" height="180" fill="url(#cv3)" />
      <circle cx="160" cy="100" r="40" fill="none" stroke="#22D3B7" strokeWidth="1.5" />
      <circle cx="160" cy="100" r="64" fill="none" stroke="rgba(34,211,183,0.4)" strokeWidth="1.2" strokeDasharray="3 4" />
      <circle cx="160" cy="100" r="14" fill="#22D3B7" />
      <text x="20" y="40" fill="#F7F9FC" fontFamily="Inter Display" fontSize="17" fontWeight="700">
        AI Copilot 演示
      </text>
    </svg>
  ),
  "series-c": (
    <svg viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" className="h-full w-full">
      <defs>
        <linearGradient id="cv4" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#0E2E4A" />
          <stop offset="100%" stopColor="#06101F" />
        </linearGradient>
      </defs>
      <rect width="320" height="180" fill="url(#cv4)" />
      <text x="160" y="110" fill="#22D3B7" fontFamily="Inter Display" fontSize="44" fontWeight="700" textAnchor="middle">
        C 轮
      </text>
      <text x="160" y="138" fill="#8590A8" fontFamily="Inter" fontSize="11" textAnchor="middle" letterSpacing="3">
        TIKTOK · 预告
      </text>
    </svg>
  ),
  helios: (
    <svg viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" className="h-full w-full">
      <defs>
        <linearGradient id="cv5" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#0B2F4C" />
          <stop offset="100%" stopColor="#06101F" />
        </linearGradient>
      </defs>
      <rect width="320" height="180" fill="url(#cv5)" />
      <g transform="translate(230 30)">
        <circle r="42" fill="rgba(56,189,248,0.18)" />
        <circle r="22" fill="rgba(56,189,248,0.4)" />
      </g>
      <text x="20" y="100" fill="#F7F9FC" fontFamily="Inter Display" fontSize="18" fontWeight="700">
        Helios Logistics
      </text>
      <text x="20" y="124" fill="#8590A8" fontFamily="Inter" fontSize="11">
        Q3 客户案例
      </text>
    </svg>
  ),
  gdpr: (
    <svg viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" className="h-full w-full">
      <defs>
        <linearGradient id="cv6" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#1f2238" />
          <stop offset="100%" stopColor="#06101F" />
        </linearGradient>
      </defs>
      <rect width="320" height="180" fill="url(#cv6)" />
      <g transform="translate(28 28)" fill="none" stroke="#a78bfa" strokeWidth="1.5">
        <rect width="60" height="80" rx="6" />
        <path d="M10 24h40M10 40h40M10 56h28" />
      </g>
      <text x="108" y="80" fill="#F7F9FC" fontFamily="Inter Display" fontSize="17" fontWeight="700">
        GDPR 要点
      </text>
      <text x="108" y="100" fill="#8590A8" fontFamily="Inter" fontSize="11">
        合规培训 · 3 分钟
      </text>
    </svg>
  ),
};

export function ProjectCover({ cover }: { cover: string }) {
  return COVERS[cover] ?? (
    <div className="grid h-full w-full place-items-center bg-gradient-to-br from-navy-700 to-navy-900">
      <span className="font-display text-sm text-muted-foreground">无封面</span>
    </div>
  );
}
