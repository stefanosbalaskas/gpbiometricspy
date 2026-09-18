(function () {
  function isTypingTarget(target) {
    return Boolean(
      target &&
        (target.matches?.("input, textarea, select") || target.isContentEditable)
    );
  }

  function initApiFilter() {
    const input = document.querySelector("[data-api-filter]");
    if (!input || input.dataset.gpReady === "true") return;

    const rows = Array.from(document.querySelectorAll("[data-api-row]"));
    const count = document.querySelector("[data-api-result-count]");
    const toolbar = input.closest(".gp-api-toolbar");
    const tableWrap = document.querySelector(".gp-api-table-wrap");
    if (!rows.length || !toolbar || !tableWrap) return;

    input.dataset.gpReady = "true";

    const clear = document.createElement("button");
    clear.type = "button";
    clear.className = "gp-api-clear";
    clear.dataset.apiClear = "";
    clear.textContent = "Clear";
    clear.setAttribute("aria-label", "Clear API search and domain filter");
    clear.hidden = true;
    if (count) {
      toolbar.insertBefore(clear, count);
      count.setAttribute("aria-live", "polite");
      count.setAttribute("aria-atomic", "true");
    } else {
      toolbar.appendChild(clear);
    }

    const empty = document.createElement("div");
    empty.className = "gp-api-empty";
    empty.dataset.apiEmpty = "";
    empty.setAttribute("role", "status");
    empty.textContent = "No functions match this search and domain. Clear the filters or try a broader term.";
    empty.hidden = true;
    tableWrap.insertAdjacentElement("afterend", empty);

    const domainCounts = new Map();
    rows.forEach((row) => {
      const domain = row.cells[1]?.textContent.trim() || "Other";
      row.dataset.apiDomain = domain;
      domainCounts.set(domain, (domainCounts.get(domain) || 0) + 1);
    });

    const cardOrder = Array.from(
      document.querySelectorAll(".gp-api-domain-card h3")
    )
      .map((heading) => heading.textContent.trim())
      .filter((domain) => domainCounts.has(domain));
    const remainingDomains = Array.from(domainCounts.keys()).filter(
      (domain) => !cardOrder.includes(domain)
    );
    const domains = [...cardOrder, ...remainingDomains];

    const facets = document.createElement("div");
    facets.className = "gp-api-facets";
    facets.dataset.apiFacets = "";
    facets.setAttribute("role", "group");
    facets.setAttribute("aria-label", "Filter functions by scientific domain");

    function makeFacet(domain, label, domainCount) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "gp-api-facet";
      button.dataset.apiDomainFilter = domain;
      button.setAttribute("aria-pressed", domain === "all" ? "true" : "false");
      const labelNode = document.createElement("span");
      labelNode.textContent = label;
      const countNode = document.createElement("strong");
      countNode.textContent = String(domainCount);
      button.append(labelNode, countNode);
      return button;
    }

    facets.appendChild(makeFacet("all", "All", rows.length));
    domains.forEach((domain) => {
      facets.appendChild(makeFacet(domain, domain, domainCounts.get(domain)));
    });
    tableWrap.insertAdjacentElement("beforebegin", facets);

    const shareNote = document.createElement("p");
    shareNote.className = "gp-api-share-note";
    shareNote.dataset.apiShareNote = "";
    shareNote.textContent =
      "Filters update this page URL. Bookmark or share the current view to reopen the same domain and search.";
    facets.insertAdjacentElement("afterend", shareNote);

    const facetButtons = Array.from(
      facets.querySelectorAll("[data-api-domain-filter]")
    );
    const validDomains = new Set(domains);
    let activeDomain = "all";

    function readUrlState() {
      const params = new URLSearchParams(window.location.search);
      const requestedDomain = params.get("domain") || "all";
      return {
        domain: validDomains.has(requestedDomain) ? requestedDomain : "all",
        query: params.get("q") || "",
      };
    }

    function writeUrlState(mode = "replace") {
      const url = new URL(window.location.href);
      const query = input.value.trim();

      if (activeDomain === "all") {
        url.searchParams.delete("domain");
      } else {
        url.searchParams.set("domain", activeDomain);
      }
      if (query) {
        url.searchParams.set("q", query);
      } else {
        url.searchParams.delete("q");
      }

      const method = mode === "push" ? "pushState" : "replaceState";
      window.history[method]({}, "", url);
    }

    function applyFilter(options = {}) {
      const query = input.value.trim().toLowerCase();
      let visible = 0;

      rows.forEach((row) => {
        const textMatch = !query || row.textContent.toLowerCase().includes(query);
        const domainMatch =
          activeDomain === "all" || row.dataset.apiDomain === activeDomain;
        const match = textMatch && domainMatch;
        row.hidden = !match;
        if (match) visible += 1;
      });

      facetButtons.forEach((button) => {
        const selected = button.dataset.apiDomainFilter === activeDomain;
        button.setAttribute("aria-pressed", selected ? "true" : "false");
      });

      if (count) {
        count.textContent = `${visible} function${visible === 1 ? "" : "s"}`;
      }
      clear.hidden = !query && activeDomain === "all";
      empty.hidden = visible !== 0;

      if (options.syncUrl) writeUrlState(options.historyMode);
    }

    function restoreFromUrl() {
      const state = readUrlState();
      activeDomain = state.domain;
      input.value = state.query;
      applyFilter();
    }

    function resetFilters(options = {}) {
      activeDomain = "all";
      input.value = "";
      applyFilter({ syncUrl: true });
      if (options.focus) input.focus();
    }

    facetButtons.forEach((button) => {
      button.addEventListener("click", () => {
        activeDomain = button.dataset.apiDomainFilter || "all";
        applyFilter({ syncUrl: true, historyMode: "push" });
      });
    });
    input.addEventListener("input", () => applyFilter({ syncUrl: true }));
    input.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        resetFilters({ focus: true });
      }
    });
    input.addEventListener("gp-api-restore", restoreFromUrl);
    clear.addEventListener("click", () => resetFilters({ focus: true }));

    restoreFromUrl();
    writeUrlState();
  }

  if (document.documentElement.dataset.gpApiShortcutReady !== "true") {
    document.documentElement.dataset.gpApiShortcutReady = "true";
    document.addEventListener("keydown", (event) => {
      if (
        event.key === "/" &&
        !event.altKey &&
        !event.ctrlKey &&
        !event.metaKey &&
        !event.shiftKey &&
        !isTypingTarget(event.target)
      ) {
        const input = document.querySelector("[data-api-filter]");
        if (input) {
          event.preventDefault();
          input.focus();
        }
      }
    });
  }

  if (document.documentElement.dataset.gpApiHistoryReady !== "true") {
    document.documentElement.dataset.gpApiHistoryReady = "true";
    window.addEventListener("popstate", () => {
      const input = document.querySelector("[data-api-filter]");
      input?.dispatchEvent(new Event("gp-api-restore"));
    });
  }

  if (typeof document$ !== "undefined") {
    document$.subscribe(initApiFilter);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initApiFilter);
  } else {
    initApiFilter();
  }
})();
