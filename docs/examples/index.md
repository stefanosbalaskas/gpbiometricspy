# Examples

<div class="gp-page-intro">
These examples are the practical front door to `gpbiometricspy`. Every route uses bundled synthetic/public demonstration data or deterministic simulation, so you can inspect the workflow and rendered output before introducing private participant data.
</div>

<div class="gp-route-grid">
<a class="gp-route-card" href="eda-scr/"><span class="gp-route-label">EDA / SCR</span><h3>Conductance to response events</h3><p>Inspect quality, decompose EDA, detect candidate SCRs, and retain visual diagnostics.</p></a>
<a class="gp-route-card" href="ppg-hrv/"><span class="gp-route-label">PPG / HRV</span><h3>Waveform to beat intervals</h3><p>Detect pulse peaks, inspect RR/IBI geometry, and generate standard HRV diagnostics with source guardrails.</p></a>
<a class="gp-route-card" href="pupil-gaze/"><span class="gp-route-label">Eye tracking</span><h3>Pupil, gaze, AOI and saccades</h3><p>Inspect pupil/gaze channels, aggregate AOI-linked measures, and use gaze diagnostics without inferring latent states.</p></a>
<a class="gp-route-card" href="multimodal/"><span class="gp-route-label">Alignment</span><h3>Events and synchronized streams</h3><p>Extract markers, audit timebases, align multimodal channels, and build event-locked summaries.</p></a>
<a class="gp-route-card" href="quality-reporting/"><span class="gp-route-label">Evidence</span><h3>QC and reproducible reporting</h3><p>Make missingness, signal activity, timing issues, design coverage, and report-ready evidence visible.</p></a>
<a class="gp-route-card" href="interoperability/"><span class="gp-route-label">Ecosystem</span><h3>External toolbox handoffs</h3><p>Prepare explicit bridges for HeartPy, pyPPG, NeuroKit, MNE, LSL/XDF, BIDS-oriented workflows, and related tools.</p></a>
</div>

## Choose by what you have

| Starting data | Example | Primary evidence produced |
|---|---|---|
| EDA/GSR waveform | [EDA / GSR / SCR](eda-scr.md) | quality, decomposition, candidate response events |
| PPG waveform or intervals | [PPG / HRV](ppg-hrv.md) | peak/interval diagnostics and HRV-ready series |
| Pupil/gaze/AOI columns | [Pupil / gaze / AOI](pupil-gaze.md) | missingness/validity, AOI summaries, gaze diagnostics |
| TTL/task events + signals | [Multimodal](multimodal.md) | event identity, timebase/alignment evidence, event windows |
| Any completed dataset | [QC + reporting](quality-reporting.md) | auditable QC, design coverage, figures, reporting inputs |
| External analysis ecosystem | [Interoperability](interoperability.md) | explicit backend-ready structures and version-aware handoffs |

## Visual outputs generated in CI

<div class="gp-visual-grid">
<a class="gp-visual-card" href="../plot-gallery/#eda-and-scr"><img src="../assets/generated/eda-decomposition.png" alt="EDA tonic and phasic decomposition"><div class="gp-visual-card-body"><strong>EDA decomposition</strong><span>Observed, tonic and phasic components.</span></div></a>
<a class="gp-visual-card" href="../plot-gallery/#ppg-and-hrv"><img src="../assets/generated/ppg-peak-detection.png" alt="PPG waveform with detected pulse peaks"><div class="gp-visual-card-body"><strong>PPG peak detection</strong><span>Waveform and accepted pulse events.</span></div></a>
<a class="gp-visual-card" href="../plot-gallery/#pupil-gaze-and-aois"><img src="../assets/generated/pupil-gaze-overview.png" alt="Pupil and gaze signal overview"><div class="gp-visual-card-body"><strong>Pupil + gaze</strong><span>Standardised eye-tracking channels.</span></div></a>
<a class="gp-visual-card" href="../plot-gallery/#multimodal-alignment"><img src="../assets/generated/multimodal-timeline.png" alt="Multimodal timeline with physiology pupil and event markers"><div class="gp-visual-card-body"><strong>Multimodal timeline</strong><span>Signals inspected on an explicit shared timeline.</span></div></a>
</div>

## From example to research workflow

1. Reproduce the example unchanged.
2. Replace only the input mapping—not the scientific meaning of variables.
3. Run the [new-dataset validation guide](../guides/validate-dataset.md).
4. Preserve QC/provenance evidence before preprocessing.
5. Move to the deeper article linked from the example.
6. Use the [API reference](../api/index.md) only when you need exact signatures or less common options.

For a visual survey first, open the [Plot gallery](../plot-gallery.md). For the 26 executable frozen R-companion workflows, browse [Articles and tutorials](../articles/index.md). For conceptual design guidance, use the [Python-native explanation articles](../articles/python-native/index.md).
