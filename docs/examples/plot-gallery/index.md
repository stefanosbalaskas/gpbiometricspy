# Plot gallery moved

The plot gallery now lives at the site-level route: [open the current plot gallery](../../plot-gallery/).

<script>
(() => {
  const target = new URL("../../plot-gallery/", window.location.href);
  target.hash = window.location.hash || "";
  window.location.replace(target.toString());
})();
</script>

<noscript>
<p>JavaScript is disabled. Use the link above to open the current plot gallery.</p>
</noscript>
