/**
 * A stylized orca silhouette, reused as the landing page's scroll-parallax
 * motif (LandingPage.tsx) and the login page's art-panel centerpiece
 * (LoginPage.tsx). Pure inline SVG, single `currentColor` path plus one
 * translucent eye-patch ellipse, so it inherits whatever text colour its
 * wrapper sets and needs no image asset (CSS/SVG-only build - see
 * scrollcraft/builds/orca-landing/BRIEF.md).
 */
export function OrcaMark({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 200 100" aria-hidden="true" focusable="false">
      <path
        d="M5,55 C10,42 18,36 25,35 C40,32 55,31 70,30 C74,18 80,6 85,2 C90,10 94,22 100,32
           C115,34 132,37 150,40 C162,34 178,26 195,20 C188,32 180,40 175,48 C182,54 190,58 195,62
           C178,58 163,58 150,55 C140,62 128,66 115,67 C112,76 104,84 95,85 C92,76 90,68 88,66
           C82,68 74,69 65,69 C50,69 40,68 32,66 C22,64 12,60 5,55 Z"
        fill="currentColor"
      />
      <ellipse cx="24" cy="44" rx="5" ry="3" fill="rgba(0,0,0,0.28)" transform="rotate(-12 24 44)" />
    </svg>
  );
}

export default OrcaMark;
