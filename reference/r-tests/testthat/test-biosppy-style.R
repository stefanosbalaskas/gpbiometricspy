
test_that("BioSPPy-style EDA helpers work", {
  fs <- 50
  t <- seq(0, 30, by = 1 / fs)
  eda <- 1 + 0.01 * t
  eda <- eda + 0.4 * exp(-((t - 8) ^ 2) / 0.8)
  eda <- eda + 0.3 * exp(-((t - 18) ^ 2) / 1.0)

  d <- data.frame(participant = "P01", time_s = t, gsr = eda)

  events <- extract_gazepoint_eda_events_biosppy_style(
    d,
    signal_col = "gsr",
    time_col = "time_s",
    group_cols = "participant",
    sampling_rate_hz = fs,
    min_amplitude = 0.02
  )

  expect_true(is.data.frame(events))

  recovery <- estimate_gazepoint_eda_recovery_times(
    d,
    events = events,
    signal_col = "gsr",
    time_col = "time_s",
    group_cols = "participant",
    sampling_rate_hz = fs
  )

  expect_true(is.data.frame(recovery))

  out <- run_gazepoint_biosppy_eda(
    d,
    signal_col = "gsr",
    time_col = "time_s",
    group_cols = "participant",
    sampling_rate_hz = fs
  )

  expect_true(is.list(out))
  expect_true(is.data.frame(out$signal))
  expect_true(is.data.frame(out$summary))
})

test_that("BioSPPy-style PPG helpers work", {
  fs <- 100
  t <- seq(0, 20, by = 1 / fs)
  ppg <- sin(2 * pi * 1.2 * t)^8 + 0.02 * sin(2 * pi * 6 * t)

  d <- data.frame(participant = "P01", time_s = t, ppg = ppg)

  out <- run_gazepoint_biosppy_ppg(
    d,
    signal_col = "ppg",
    time_col = "time_s",
    group_cols = "participant",
    sampling_rate_hz = fs
  )

  expect_true(is.list(out))
  expect_true(is.data.frame(out$signal))
  expect_true(is.data.frame(out$peaks))
  expect_true(is.data.frame(out$onsets))
  expect_true(is.list(out$templates))

  templates <- extract_gazepoint_ppg_templates(
    d,
    signal_col = "ppg",
    time_col = "time_s",
    sampling_rate_hz = fs,
    peaks = out$peaks
  )

  expect_true(is.list(templates))
  expect_true(is.matrix(templates$templates))

  onsets <- detect_gazepoint_ppg_onsets(
    d,
    signal_col = "ppg",
    time_col = "time_s",
    sampling_rate_hz = fs,
    peaks = out$peaks
  )

  expect_true(is.data.frame(onsets))
})

test_that("BioSPPy-style RRI helpers work", {
  rri <- c(800, 810, 790, 805, 2000, 795, 805, 800, 790, 810)

  detrended <- detrend_gazepoint_rri_window(rri, window_seconds = 5)
  expect_true(is.data.frame(detrended))
  expect_true("rri_detrended_ms" %in% names(detrended))

  corrected <- correct_gazepoint_rri_artifacts_local(rri, method = "local_median")
  expect_true(is.data.frame(corrected))
  expect_true("rri_corrected_ms" %in% names(corrected))
  expect_true(any(corrected$artifact))
})

test_that("BioSPPy-style generic signal helpers work", {
  fs <- 100
  t <- seq(0, 10, by = 1 / fs)
  x <- sin(2 * pi * 1.5 * t)
  y <- sin(2 * pi * 1.5 * t + pi / 6)

  psd <- compute_gazepoint_signal_power_spectrum(x, sampling_rate_hz = fs)
  expect_true(is.data.frame(psd))
  expect_true(all(c("frequency_hz", "power") %in% names(psd)))

  bp <- compute_gazepoint_signal_band_power(
    psd,
    bands = list(alpha = c(1, 2))
  )
  expect_true(is.data.frame(bp))
  expect_true("power" %in% names(bp))

  plv <- compute_gazepoint_signal_phase_locking(
    x,
    y,
    sampling_rate_hz = fs,
    band = c(1, 2)
  )
  expect_true(is.data.frame(plv))
  expect_true(is.finite(plv$phase_locking_value[1]))

  cc <- compute_gazepoint_signal_correlation(x, y, lag_max = 20)
  expect_true(is.data.frame(cc))
  expect_true("correlation" %in% names(cc))
})

