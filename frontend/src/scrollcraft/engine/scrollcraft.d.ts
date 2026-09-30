// Ambient shim so the untouched, vanilla-JS scrollcraft engine (never
// converted to TS - the skill's own hard rule is "never edit the engine")
// can be imported for its side effect (it sets `window.ScrollCraft`) without
// enabling project-wide `allowJs`.
declare module "./scrollcraft.js";
