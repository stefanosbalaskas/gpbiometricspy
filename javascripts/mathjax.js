window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true,
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex",
  },
};

if (typeof document$ !== "undefined") {
  document$.subscribe(() => {
    if (window.MathJax && typeof window.MathJax.typesetPromise === "function") {
      if (typeof window.MathJax.typesetClear === "function") {
        window.MathJax.typesetClear();
      }
      if (typeof window.MathJax.texReset === "function") {
        window.MathJax.texReset();
      }
      window.MathJax.typesetPromise();
    }
  });
}
