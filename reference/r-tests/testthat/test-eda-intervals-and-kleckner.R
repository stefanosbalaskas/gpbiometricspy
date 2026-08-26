test_that("classify_gazepoint_scr_intervals classifies FIR SIR and TIR", {
  dat <- data.frame(
    stimulus_onset = 0,
    peak_time = c(1.5, 5, 8, 12, NA)
  )

  out <- classify_gazepoint_scr_intervals(
    dat,
    response_time_col = "peak_time",
    stimulus_onset_col = "stimulus_onset"
  )

  expect_equal(
    out$scr_interval,
    c("FIR", "SIR", "TIR", "outside_defined_intervals", "missing_latency")
  )

  summary <- attr(out, "scr_interval_summary")
  expect_equal(summary$fir_rows, 1)
  expect_equal(summary$sir_rows, 1)
  expect_equal(summary$tir_rows, 1)
})

test_that("flag_kleckner_eda_artifacts flags range and rapid-change artifacts", {
  dat <- data.frame(
    participant = "p1",
    time = 1:6,
    GSR_US = c(1, 1.1, 1.2, 200, 1.3, NA)
  )

  out <- flag_kleckner_eda_artifacts(
    dat,
    eda_col = "GSR_US",
    time_col = "time",
    group_cols = "participant",
    transition_padding = 0
  )

  expect_true(out$kleckner_range_artifact[4])
  expect_true(out$kleckner_nonfinite[6])
  expect_true(any(out$kleckner_artifact))

  summary <- attr(out, "kleckner_artifact_summary")
  expect_equal(summary$status, "kleckner_style_artifacts_flagged")
})
