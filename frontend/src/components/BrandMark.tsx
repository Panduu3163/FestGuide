export function BrandEmblem({ size = 32, className = "" }: { size?: number; className?: string }) {
  return (
    <img
      src="/static/logo-mark.png"
      alt="FestGuide emblem"
      width={size}
      height={size}
      className={`shrink-0 object-contain select-none ${className}`}
    />
  );
}

export function BrandLockup({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5 select-none">
      <BrandEmblem size={compact ? 28 : 34} />
      <div className="leading-none">
        <div className="flex items-baseline font-extrabold tracking-tight text-sm sm:text-base">
          <span className="text-[var(--text)]">FEST</span>
          <span className="bg-gradient-to-r from-[#0f9d8a] via-[#14b8a6] to-[#c99a2e] bg-clip-text text-transparent">
            GUIDE
          </span>
        </div>
        {!compact && (
          <div className="text-[9px] font-mono-tab tracking-[0.22em] text-[var(--muted)] mt-0.5 uppercase">
            IIUC · CSE FEST 2026
          </div>
        )}
      </div>
    </div>
  );
}
