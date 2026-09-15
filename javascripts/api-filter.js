(function () {
  function initApiFilter() {
    const input = document.querySelector("[data-api-filter]");
    if (!input || input.dataset.gpReady === "true") return;

    input.dataset.gpReady = "true";
    const rows = Array.from(document.querySelectorAll("[data-api-row]"));
    const count = document.querySelector("[data-api-result-count]");

    function applyFilter() {
      const query = input.value.trim().toLowerCase();
      let visible = 0;

      rows.forEach((row) => {
        const match = !query || row.textContent.toLowerCase().includes(query);
        row.hidden = !match;
        if (match) visible += 1;
      });

      if (count) {
        count.textContent = `${visible} function${visible === 1 ? "" : "s"}`;
      }
    }

    input.addEventListener("input", applyFilter);
    applyFilter();
  }

  if (typeof document$ !== "undefined") {
    document$.subscribe(initApiFilter);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initApiFilter);
  } else {
    initApiFilter();
  }
})();
