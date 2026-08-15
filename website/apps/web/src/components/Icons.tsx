type IconProps = {
  className?: string;
};

/** Shared stroke icons. 24×24 grid, currentColor, no external icon package. */
function Svg({
  className = "h-5 w-5",
  children,
  fill = "none",
}: IconProps & { children: React.ReactNode; fill?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill={fill}
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export const PlayIcon = ({ className }: IconProps) => (
  <Svg className={className} fill="currentColor">
    <path d="M8 5.6v12.8a.7.7 0 0 0 1.07.6l10-6.4a.7.7 0 0 0 0-1.2l-10-6.4A.7.7 0 0 0 8 5.6Z" stroke="none" />
  </Svg>
);

export const PauseIcon = ({ className }: IconProps) => (
  <Svg className={className} fill="currentColor">
    <rect x="6.5" y="5" width="3.8" height="14" rx="1.3" stroke="none" />
    <rect x="13.7" y="5" width="3.8" height="14" rx="1.3" stroke="none" />
  </Svg>
);

/** Rewind 15s — arrow curls anticlockwise. */
export const Back15Icon = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M12 5a7.5 7.5 0 1 1-7.3 9.2" />
    <path d="M4.4 5.2v3.6h3.6" />
    <text
      x="12"
      y="15.4"
      textAnchor="middle"
      fontSize="7"
      fontWeight="700"
      fill="currentColor"
      stroke="none"
      fontFamily="inherit"
    >
      15
    </text>
  </Svg>
);

/** Forward 15s — mirror of the rewind glyph. */
export const Forward15Icon = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M12 5a7.5 7.5 0 1 0 7.3 9.2" />
    <path d="M19.6 5.2v3.6H16" />
    <text
      x="12"
      y="15.4"
      textAnchor="middle"
      fontSize="7"
      fontWeight="700"
      fill="currentColor"
      stroke="none"
      fontFamily="inherit"
    >
      15
    </text>
  </Svg>
);

export const BookmarkIcon = ({
  className,
  filled = false,
}: IconProps & { filled?: boolean }) => (
  <Svg className={className} fill={filled ? "currentColor" : "none"}>
    <path d="M6.5 4.8h11a1 1 0 0 1 1 1v13.4l-6.5-3.6-6.5 3.6V5.8a1 1 0 0 1 1-1Z" />
  </Svg>
);

export const ShareIcon = ({ className }: IconProps) => (
  <Svg className={className}>
    <circle cx="17.5" cy="6" r="2.6" />
    <circle cx="6.5" cy="12" r="2.6" />
    <circle cx="17.5" cy="18" r="2.6" />
    <path d="m8.9 10.7 6.2-3.4M8.9 13.3l6.2 3.4" />
  </Svg>
);

export const DownloadIcon = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M12 4v10" />
    <path d="m8 10.5 4 4 4-4" />
    <path d="M4.8 18.6h14.4" />
  </Svg>
);

export const CaptionsIcon = ({ className }: IconProps) => (
  <Svg className={className}>
    <rect x="3" y="5.5" width="18" height="13" rx="3" />
    <path d="M10 10.6a2.4 2.4 0 1 0 0 2.8M17 10.6a2.4 2.4 0 1 0 0 2.8" />
  </Svg>
);

export const TextIcon = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M6.5 3.5h7.6L19 8.4v12.1H6.5z" />
    <path d="M13.8 3.6v5h5" />
    <path d="M9.4 13h6.2M9.4 16.4h4.2" />
  </Svg>
);

export const SearchIcon = ({ className }: IconProps) => (
  <Svg className={className}>
    <circle cx="11" cy="11" r="6.3" />
    <path d="m15.8 15.8 3.7 3.7" />
  </Svg>
);

export const ListIcon = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M9 6.5h11M9 12h11M9 17.5h11" />
    <circle cx="4.6" cy="6.5" r="1.1" fill="currentColor" stroke="none" />
    <circle cx="4.6" cy="12" r="1.1" fill="currentColor" stroke="none" />
    <circle cx="4.6" cy="17.5" r="1.1" fill="currentColor" stroke="none" />
  </Svg>
);

export const ChevronIcon = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="m6.5 9.5 5.5 5.5 5.5-5.5" />
  </Svg>
);

export const SpeedIcon = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M4.2 17a8.5 8.5 0 1 1 15.6 0" />
    <path d="m12 12.8 4-4.2" />
    <circle cx="12" cy="13.6" r="1.5" fill="currentColor" stroke="none" />
  </Svg>
);

export const ArrowRightIcon = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M19 12H5" />
    <path d="m11 6-6 6 6 6" />
  </Svg>
);

export const ArrowLeftIcon = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M5 12h14" />
    <path d="m13 6 6 6-6 6" />
  </Svg>
);

export const WaveIcon = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M4 11v2M8 8v8M12 5.5v13M16 8v8M20 11v2" />
  </Svg>
);
