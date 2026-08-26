test_that("plot_gazepoint_eda_decomposition returns a ggplot object", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    participant = "P1",
    CNT = seq_len(20),
    GSR_US = seq(1, 2, length.out = 20),
    GSR_US_TONIC = seq(1, 1.5, length.out = 20),
    GSR_US_PHASIC = sin(seq(0, pi, length.out = 20))
  )

  p <- plot_gazepoint_eda_decomposition(
    dat,
    time_col = "CNT",
    signal_cols = c("GSR_US", "GSR_US_TONIC", "GSR_US_PHASIC"),
    group_cols = "participant",
    standardise = TRUE
  )

  expect_s3_class(p, "ggplot")
  expect_true(is.data.frame(attr(p, "plot_data")))
  expect_equal(
    unique(attr(p, "plot_data")$.data_signal),
    c("GSR_US", "GSR_US_TONIC", "GSR_US_PHASIC")
  )
})

test_that("plot_gazepoint_eda_decomposition handles constant channels", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    CNT = seq_len(10),
    GSR_US = rep(0, 10),
    GSR_US_PHASIC = rep(0, 10)
  )

  p <- plot_gazepoint_eda_decomposition(
    dat,
    time_col = "CNT",
    standardise = TRUE
  )

  expect_s3_class(p, "ggplot")
  expect_true(all(attr(p, "plot_data")$.data_value == 0))
})

test_that("plot_gazepoint_scr_events overlays SCR peak markers", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    participant = "P1",
    CNT = seq_len(20),
    GSR_US_PHASIC = c(rep(0, 5), 0.02, 0.08, 0.02, rep(0, 12))
  )

  peaks <- data.frame(
    participant = "P1",
    peak_time = 7,
    amplitude = 0.08,
    status = "detected"
  )

  events <- data.frame(
    participant = "P1",
    event_time = 5
  )

  p <- plot_gazepoint_scr_events(
    dat,
    scr_peaks = peaks,
    events = events,
    time_col = "CNT",
    signal_col = "GSR_US_PHASIC",
    group_cols = "participant"
  )

  expect_s3_class(p, "ggplot")
  expect_true(is.data.frame(attr(p, "plot_data")))
  expect_true(is.data.frame(attr(p, "peak_data")))
  expect_true(is.data.frame(attr(p, "event_data")))
  expect_equal(nrow(attr(p, "peak_data")), 1)
  expect_equal(nrow(attr(p, "event_data")), 1)
})

test_that("plot_gazepoint_scr_events accepts peak-detection objects", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    participant = "P1",
    CNT = seq_len(20),
    GSR_US_PHASIC = c(rep(0, 5), 0.02, 0.08, 0.02, rep(0, 12))
  )

  peaks <- detect_gazepoint_scr_peaks(
    dat,
    phasic_col = "GSR_US_PHASIC",
    time_col = "CNT",
    group_cols = "participant",
    amplitude_min = 0.03
  )

  p <- plot_gazepoint_scr_events(
    dat,
    scr_peaks = peaks,
    time_col = "CNT",
    group_cols = "participant"
  )

  expect_s3_class(p, "ggplot")
  expect_true(nrow(attr(p, "peak_data")) >= 1)
})
