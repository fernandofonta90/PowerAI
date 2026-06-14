// Sparkle de cuatro puntas — símbolo de IA del design system (familia AI.Q).
// Regla del sparkle: marca presencia de IA, nunca decora.

export function Sparkle({
  className = "h-4 w-4",
  title,
}: {
  className?: string;
  title?: string;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="currentColor"
      role={title ? "img" : "presentation"}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      <path d="M12 2c.5 4.5 2.5 6.5 7 7-4.5.5-6.5 2.5-7 7-.5-4.5-2.5-6.5-7-7 4.5-.5 6.5-2.5 7-7z" />
    </svg>
  );
}
