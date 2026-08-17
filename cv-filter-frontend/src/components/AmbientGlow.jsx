/**
 * Lavender wash behind the near-black canvas.
 *
 * Sits at z-0 rather than a negative z-index — behind a painted background
 * a negative layer is simply never visible. Page content goes above it.
 */
const AmbientGlow = ({ variant = 'page' }) => {
  if (variant === 'focus') {
    // Progress screen: tight, brighter, centred on the ring.
    return (
      <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
        <div className="glow-orb glow-a left-1/2 top-1/2 h-140 w-140 -translate-x-1/2 -translate-y-1/2 opacity-70" />
        <div className="glow-orb glow-b left-1/2 top-1/2 h-225 w-225 -translate-x-1/2 -translate-y-1/2 opacity-40" />
      </div>
    )
  }

  // A single wide wash bled off the top edge, centred on the content column.
  // No floor glow: a second source at the bottom reads as a halo rather than
  // ambient light, since nothing down there justifies it.
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
      <div className="glow-orb glow-a left-1/2 -top-96 h-180 w-325 -translate-x-1/2 opacity-50" />
    </div>
  )
}

export default AmbientGlow
