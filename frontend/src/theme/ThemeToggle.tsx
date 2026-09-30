import { useTheme } from "./ThemeContext";

/** Sun/moon switch - a persistent setting, not a one-off action (see index.css `.theme-toggle`). */
export function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, toggleTheme } = useTheme();
  const isLight = theme === "light";
  return (
    <button
      type="button"
      className={`theme-toggle ${className}`}
      onClick={toggleTheme}
      role="switch"
      aria-checked={isLight}
      aria-label={isLight ? "Switch to dark theme" : "Switch to light theme"}
      title={isLight ? "Switch to dark theme" : "Switch to light theme"}
    >
      <span aria-hidden>{isLight ? "☀" : "☾"}</span>
    </button>
  );
}
