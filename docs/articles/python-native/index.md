# Python-native explanation articles

<div class="gp-page-intro">
These articles explain design choices that emerged during the Python development line. They are intentionally separate from the 26 frozen R vignette companions: they do not alter the 406-export parity contract and are not presented as ports of R documentation.
</div>

<div class="gp-route-grid">
<a class="gp-route-card" href="research-pipeline-blueprint/"><span class="gp-route-label">Architecture</span><h3>Research pipeline blueprint</h3><p>Why ingestion, measurement evidence, processing, alignment, modelling, and reporting are kept as explicit stages.</p></a>
<a class="gp-route-card" href="measurement-before-modelling/"><span class="gp-route-label">Measurement</span><h3>Measurement before modelling</h3><p>Why timebase, signal quality, source identity, and design support constrain what a statistical model can mean.</p></a>
<a class="gp-route-card" href="model-selection-location-scale/"><span class="gp-route-label">Statistics</span><h3>Choosing a location–scale model</h3><p>How random intercepts, heavy tails, location slopes, scale slopes, joint slopes, and crossed effects answer different questions.</p></a>
<a class="gp-route-card" href="reproducible-multimodal-study/"><span class="gp-route-label">Multimodal</span><h3>Reproducible multimodal studies</h3><p>A provenance-first architecture for clocks, anchors, event windows, signal processing, and evidence bundles.</p></a>
</div>

## How these differ from tutorials and reference pages

- **Tutorials** tell you what to do to achieve a successful learning outcome.
- **How-to guides** help you complete a concrete research task.
- **API reference** describes exact software behavior and signatures.
- **These explanation articles** connect the scientific and architectural reasoning behind those choices.

For the original frozen R-companion inventory, return to [Articles and tutorials](../index.md).
