export default function HeroIllustration() {
  return (
    <svg
      viewBox="0 0 500 400"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="w-full h-auto max-w-lg"
    >
      {/* Dashboard frame */}
      <rect x="20" y="20" width="460" height="360" rx="16" className="fill-muted/50 stroke-border" strokeWidth="1.5" />

      {/* Top bar */}
      <rect x="20" y="20" width="460" height="48" rx="16" className="fill-muted" />
      <circle cx="52" cy="44" r="8" className="fill-primary/30" />
      <rect x="72" y="38" width="80" height="12" rx="4" className="fill-muted-foreground/20" />

      {/* Chart area */}
      <rect x="48" y="88" width="300" height="200" rx="8" className="fill-background stroke-border" strokeWidth="1" />

      {/* Candlesticks */}
      <line x1="80" y1="130" x2="80" y2="240" className="stroke-muted-foreground/20" strokeWidth="1" />
      <rect x="72" y="150" width="16" height="60" rx="2" className="fill-green-500/70" />
      <line x1="120" y1="140" x2="120" y2="250" className="stroke-muted-foreground/20" strokeWidth="1" />
      <rect x="112" y="160" width="16" height="50" rx="2" className="fill-red-500/70" />
      <line x1="160" y1="120" x2="160" y2="230" className="stroke-muted-foreground/20" strokeWidth="1" />
      <rect x="152" y="140" width="16" height="55" rx="2" className="fill-green-500/70" />
      <line x1="200" y1="110" x2="200" y2="220" className="stroke-muted-foreground/20" strokeWidth="1" />
      <rect x="192" y="130" width="16" height="45" rx="2" className="fill-green-500/70" />
      <line x1="240" y1="125" x2="240" y2="235" className="stroke-muted-foreground/20" strokeWidth="1" />
      <rect x="232" y="145" width="16" height="50" rx="2" className="fill-red-500/70" />
      <line x1="280" y1="100" x2="280" y2="210" className="stroke-muted-foreground/20" strokeWidth="1" />
      <rect x="272" y="115" width="16" height="55" rx="2" className="fill-green-500/70" />
      <line x1="320" y1="105" x2="320" y2="200" className="stroke-muted-foreground/20" strokeWidth="1" />
      <rect x="312" y="120" width="16" height="40" rx="2" className="fill-green-500/70" />

      {/* MA line */}
      <polyline
        points="80,180 120,190 160,170 200,155 240,165 280,140 320,135"
        className="stroke-primary"
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Side panel: pie chart */}
      <rect x="368" y="88" width="100" height="100" rx="8" className="fill-background stroke-border" strokeWidth="1" />
      <circle cx="418" cy="138" r="30" className="stroke-primary/40" strokeWidth="12" fill="none" strokeDasharray="60 188.5" />
      <circle cx="418" cy="138" r="30" className="stroke-green-500/40" strokeWidth="12" fill="none" strokeDasharray="40 188.5" strokeDashoffset="-60" />

      {/* Side panel: stats */}
      <rect x="368" y="200" width="100" height="88" rx="8" className="fill-background stroke-border" strokeWidth="1" />
      <rect x="380" y="216" width="50" height="8" rx="3" className="fill-muted-foreground/20" />
      <rect x="380" y="232" width="70" height="12" rx="3" className="fill-primary/30" />
      <rect x="380" y="252" width="50" height="8" rx="3" className="fill-muted-foreground/20" />
      <rect x="380" y="268" width="60" height="12" rx="3" className="fill-green-500/30" />

      {/* Bottom bar */}
      <rect x="48" y="308" width="420" height="48" rx="8" className="fill-background stroke-border" strokeWidth="1" />
      <rect x="64" y="324" width="60" height="16" rx="4" className="fill-muted-foreground/15" />
      <rect x="140" y="324" width="60" height="16" rx="4" className="fill-muted-foreground/15" />
      <rect x="216" y="324" width="60" height="16" rx="4" className="fill-muted-foreground/15" />
    </svg>
  );
}
