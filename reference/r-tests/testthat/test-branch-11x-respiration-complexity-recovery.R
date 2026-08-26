test_that("extract_gazepoint_respiration_ceemdan returns respiration proxy", {
  time <- seq(0, 120, by = 0.1)
  signal <- sin(2 * pi * 0.25 * time) + 0.2 * sin(2 * pi * 1.2 * time)

  dat <- data.frame(
    participant = "p1",
    time = time,
    signal = signal
  )

  out <- extract_gazepoint_respiration_ceemdan(
    dat,
    signal_col = "signal",
    time_col = "time",
    group_cols = "participant",
    sampling_rate = 10,
    respiration_band = c(0.1, 0.5)
  )

  expect_s3_class(out, "gazepoint_respiration_ceemdan")
  expect_true(nrow(out$respiration_timeseries) > 0)
  expect_true("proxy_respiration_rate_hz" %in% names(out$summary))
})

test_that("fuse_gazepoint_respiration_kalman fuses two respiration proxies", {
  time <- seq(0, 60, by = 0.5)
  true_resp <- sin(2 * pi * 0.25 * time)

  dat <- data.frame(
    participant = "p1",
    time = time,
    pdr = true_resp + rnorm(length(time), sd = 0.1),
    edr = true_resp + rnorm(length(time), sd = 0.1)
  )

  out <- fuse_gazepoint_respiration_kalman(
    dat,
    primary_col = "pdr",
    secondary_col = "edr",
    time_col = "time",
    group_cols = "participant"
  )

  expect_s3_class(out, "gazepoint_respiration_kalman_fused")
  expect_true("respiration_kalman_fused" %in% names(out))
  expect_equal(
    attr(out, "kalman_respiration_overview")$status,
    "kalman_respiration_fusion_complete"
  )
})

test_that("extract_gazepoint_hrv_fuzzy_csi returns FuzzyEn and CSI", {
  dat <- data.frame(
    participant = "p1",
    IBI = 0.8 + 0.04 * sin(seq(0, 8 * pi, length.out = 80)) +
      rnorm(80, sd = 0.005)
  )

  out <- extract_gazepoint_hrv_fuzzy_csi(
    dat,
    ibi_col = "IBI",
    group_cols = "participant"
  )

  expect_s3_class(out, "gazepoint_hrv_fuzzy_csi")
  expect_true("fuzzy_entropy" %in% names(out$features))
  expect_true("csi" %in% names(out$features))
  expect_true(is.finite(out$features$csi))
})

test_that("detect_gazepoint_doubly_stochastic_changepoints returns score table", {
  time <- seq(0, 120, by = 1)
  signal <- c(rnorm(61, 0, 0.1), rnorm(60, 2, 0.1))

  dat <- data.frame(
    participant = "p1",
    time = time,
    signal = signal
  )

  out <- detect_gazepoint_doubly_stochastic_changepoints(
    dat,
    signal_col = "signal",
    time_col = "time",
    group_cols = "participant",
    window_seconds = 10,
    step_seconds = 5,
    threshold_mad_multiplier = 3
  )

  expect_s3_class(out, "gazepoint_doubly_stochastic_changepoints")
  expect_true(nrow(out$score_table) > 0)
  expect_true("change_score" %in% names(out$score_table))
})

test_that("extract_gazepoint_scr_recovery_times returns rec_t2 and rec_tc", {
  time <- seq(0, 40, by = 0.5)
  response_time <- pmax(0, time - 5)

  eda <- 1 + ifelse(
    time >= 5,
    exp(-response_time / 8) - exp(-response_time / 0.8),
    0
  )

  eda <- eda / max(eda)

  dat <- data.frame(
    participant = "p1",
    time = time,
    GSR_US = eda,
    onset = c(5, rep(NA_real_, length(time) - 1))
  )

  out <- extract_gazepoint_scr_recovery_times(
    dat,
    eda_col = "GSR_US",
    time_col = "time",
    event_onset_col = "onset",
    group_cols = "participant",
    peak_window_s = 10,
    recovery_window_s = 30
  )

  expect_s3_class(out, "gazepoint_scr_recovery_times")
  expect_true("rec_t2" %in% names(out$recovery_table))
  expect_true("rec_tc" %in% names(out$recovery_table))
})
