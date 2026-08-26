
test_that("sampling-rate estimators work", {
  ms <- seq(0, 1000, by = 10)
  est <- estimate_gazepoint_samplerate_mstimer(ms)
  expect_equal(round(est$sampling_rate_hz), 100)

  dt <- as.POSIXct("2026-01-01 00:00:00", tz = "UTC") + seq(0, 1, by = 0.01)
  est2 <- estimate_gazepoint_samplerate_datetime(dt)
  expect_equal(round(est2$sampling_rate_hz), 100)
})

test_that("scaling, flipping, smoothing, filtering, and baseline removal work", {
  fs <- 100
  t <- seq(0, 5, by = 1 / fs)
  x <- 0.5 * sin(2 * pi * 0.2 * t) + sin(2 * pi * 1.2 * t)^8

  expect_equal(length(scale_gazepoint_ppg_signal(x)), length(x))
  expect_equal(length(flip_gazepoint_ppg_signal(x)), length(x))
  expect_equal(length(remove_gazepoint_ppg_baseline_wander(x, fs)), length(x))
  expect_equal(length(smooth_gazepoint_ppg_signal(x, fs)), length(x))
  expect_equal(length(filter_gazepoint_ppg_signal(x, fs, type = "lowpass", high_hz = 5)), length(x))
  expect_equal(length(filter_gazepoint_ppg_signal(x, fs, type = "highpass", low_hz = 0.5)), length(x))
  expect_equal(length(filter_gazepoint_ppg_signal(x, fs, type = "bandpass", low_hz = 0.5, high_hz = 5)), length(x))
})

test_that("RR cleaning and frequency measures work", {
  rr <- c(800, 810, 790, 805, 2000, 795, 805, 800, 790, 810)
  cleaned <- clean_gazepoint_rr_intervals(rr, method = "iqr")
  expect_true(is.data.frame(cleaned))
  expect_true("accepted" %in% names(cleaned))

  freq <- compute_gazepoint_ppg_frequency_measures(
    rr_ms = rep(c(800, 820, 790, 810), 20),
    method = "welch"
  )

  expect_true(is.data.frame(freq))
  expect_true("lf" %in% names(freq))
  expect_true("hf" %in% names(freq))
})

test_that("full HeartPy-style process works", {
  fs <- 100
  t <- seq(0, 30, by = 1 / fs)
  pulse <- sin(2 * pi * 1.2 * t)^8 + 0.02 * sin(2 * pi * 6 * t)
  d <- data.frame(participant = "P01", time_s = t, pulse = pulse)

  out <- process_gazepoint_ppg_heartpy_style(
    d,
    signal_col = "pulse",
    time_col = "time_s",
    group_cols = "participant",
    sampling_rate_hz = fs,
    high_precision = FALSE
  )

  expect_true(is.list(out))
  expect_true(is.data.frame(out$peaks))
  expect_true(is.data.frame(out$measures))
  expect_true(is.data.frame(out$frequency))
  expect_true(is.data.frame(out$quality))
})

test_that("segmentwise processing works", {
  fs <- 100
  t <- seq(0, 70, by = 1 / fs)
  pulse <- sin(2 * pi * 1.2 * t)^8
  d <- data.frame(participant = "P01", time_s = t, pulse = pulse)

  seg <- process_gazepoint_ppg_segmentwise(
    d,
    signal_col = "pulse",
    time_col = "time_s",
    group_cols = "participant",
    sampling_rate_hz = fs,
    window_seconds = 20,
    overlap = 0.5,
    min_segment_seconds = 10,
    high_precision = FALSE
  )

  expect_true(is.list(seg))
  expect_true(is.data.frame(seg$segments))
  expect_gt(nrow(seg$segments), 1)
  expect_true(is.data.frame(seg$measures))
})

test_that("binary quality checker works", {
  m <- data.frame(group = "all", n_peaks = 20, bpm = 72)
  q <- check_gazepoint_ppg_binary_quality(measures = m)
  expect_true(is.data.frame(q))
  expect_true(q$quality_pass[1])
})

