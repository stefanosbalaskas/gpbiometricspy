
test_that("flag_gazepoint_hrv_segments flags implausible RR windows", {
  rr <- c(rep(800, 30), 250, rep(820, 10), 3000, rep(810, 20))

  out <- flag_gazepoint_hrv_segments(
    rr,
    window_s = NULL,
    min_beats = 20,
    min_duration_s = 20,
    max_artifact_prop = 0.01
  )

  expect_equal(nrow(out), 1)
  expect_false(out$quality_ok)
  expect_true(grepl("implausible_rr", out$reasons))
})

test_that("flag_gazepoint_hrv_segments supports grouped data and clean segments", {
  dat <- data.frame(
    participant = rep(c("P01", "P02"), each = 40),
    rr_ms = c(rep(800, 40), rep(850, 39), 250)
  )

  out <- flag_gazepoint_hrv_segments(
    dat,
    rr_col = "rr_ms",
    group_cols = "participant",
    window_s = NULL,
    min_beats = 20,
    min_duration_s = 20
  )

  expect_equal(nrow(out), 2)
  expect_true(out$quality_ok[out$participant == "P01"])
  expect_false(out$quality_ok[out$participant == "P02"])
})

test_that("compute_gazepoint_scr_latency detects peak and onset", {
  time <- seq(0, 8, by = 0.1)
  eda <- rep(1, length(time))
  response <- ifelse(time >= 2 & time <= 5, exp(-((time - 3)^2) / 0.3), 0)
  dat <- data.frame(time_s = time, GSR = eda + response)
  events <- data.frame(event_id = "E1", event_time = 2)

  out <- compute_gazepoint_scr_latency(
    dat,
    events,
    baseline_window_s = c(-1, 0),
    response_window_s = c(0, 4),
    onset_threshold = 0.05
  )

  expect_true(out$response_detected)
  expect_true(abs(out$peak_latency_s - 1) < 0.15)
  expect_true(out$peak_amplitude > 0.9)
})

test_that("compute_gazepoint_scr_latency handles no-response trials", {
  dat <- data.frame(time_s = seq(0, 5, by = 0.1), GSR = 1)
  events <- data.frame(event_id = "E1", event_time = 2)

  out <- compute_gazepoint_scr_latency(dat, events, onset_threshold = 0.05)

  expect_false(out$response_detected)
  expect_true(out$peak_amplitude < 0.05)
})

test_that("compute_gazepoint_signal_lag_matrix detects known lag", {
  time <- seq(0, 20, by = 0.05)
  x <- sin(2 * pi * 0.2 * time)
  y <- sin(2 * pi * 0.2 * (time - 0.5))
  dat <- data.frame(time_s = time, x = x, y = y)

  out <- compute_gazepoint_signal_lag_matrix(
    dat,
    signal_cols = c("x", "y"),
    max_lag_s = 1,
    lag_step_s = 0.05,
    min_overlap = 50
  )

  expect_equal(nrow(out), 1)
  expect_true(abs(abs(out$best_lag_s) - 0.5) < 0.1)
  expect_true(abs(out$best_correlation) > 0.9)
})

test_that("compute_gazepoint_signal_lag_matrix supports grouped data", {
  time <- seq(0, 5, by = 0.1)
  dat <- rbind(
    data.frame(participant = "P01", time_s = time, a = sin(time), b = sin(time)),
    data.frame(participant = "P02", time_s = time, a = cos(time), b = cos(time))
  )

  out <- compute_gazepoint_signal_lag_matrix(
    dat,
    signal_cols = c("a", "b"),
    group_cols = "participant",
    max_lag_s = 0.5,
    lag_step_s = 0.1
  )

  expect_equal(nrow(out), 2)
  expect_true(all(abs(out$best_correlation) > 0.9))
})

test_that("estimate_gazepoint_respiration_from_ppg detects respiratory modulation", {
  fs <- 50
  time <- seq(0, 120, by = 1 / fs)
  ppg <- 0.8 * sin(2 * pi * 0.25 * time) + 0.2 * sin(2 * pi * 1.2 * time)
  dat <- data.frame(time_s = time, PPG = ppg)

  out <- estimate_gazepoint_respiration_from_ppg(dat)

  expect_true(is.list(out))
  expect_true(abs(out$summary$respiration_rate_bpm - 15) < 1)
  expect_true(nrow(out$spectrum) > 0)
})

test_that("estimate_gazepoint_respiration_from_ppg supports vector input", {
  fs <- 20
  time <- seq(0, 90, by = 1 / fs)
  ppg <- sin(2 * pi * 0.20 * time)

  out <- estimate_gazepoint_respiration_from_ppg(ppg, sampling_rate_hz = fs)

  expect_true(abs(out$summary$respiration_rate_bpm - 12) < 1)
})

