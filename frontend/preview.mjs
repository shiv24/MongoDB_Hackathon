// In srcdoc's opaque origin, History API URL updates throw SecurityError.
// Keep those optional URL side effects from crashing otherwise local previews.
export const HISTORY_BRIDGE = `(() => {
  for (const name of ['pushState', 'replaceState']) {
    const original = history[name];
    history[name] = function (...args) {
      try { return original.apply(this, args); }
      catch (error) { if (error.name !== 'SecurityError') throw error; }
    };
  }
})();`;

export function previewDocument(artifact) {
  if (!artifact) return '';
  if (!(artifact.version >= 2)) return artifact.html;
  return artifact.html.replace('</head>', `<script>${HISTORY_BRIDGE}</script></head>`);
}
