# Multimodal event-alignment example

TTL markers, eye-tracking channels and physiology can be aligned on the same timeline and summarized around events.

```python
import gpbiometricspy as gp

dat = gp.load_kiosk_demo(participants=["synthetic_kiosk_p001"]).iloc[:1800].copy()

events = gp.extract_gazepoint_ttl_events(
    dat,
    ttl_columns=["TTL0"],
    group_columns=["participant_id"],
)

summary = gp.summarize_gazepoint_eventlocked_multimodal(
    dat,
    events=events,
    time_col="TIME",
    event_time_col="TIME",
    signal_cols=["GSR_US", "HR", "LPMM"],
    group_cols=["participant_id"],
)

fig = gp.plot_gazepoint_multimodal_timeline(
    dat,
    time_col="TIME",
    signal_cols=["GSR_US", "HR", "LPMM"],
    group_cols=["participant_id"],
)
```

![Multimodal timeline](../assets/generated/multimodal-timeline.png)

See also the [Multimodal event dashboard](../articles/multimodal-event-dashboard.md).
