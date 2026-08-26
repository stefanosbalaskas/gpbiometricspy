test_that("extract_gazepoint_eda_spectral_power returns band-power summaries", {
  dat <- data.frame(
    participant = "p1",
    time = seq(0, 127),
    GSR_US = sin(2 * pi * 0.1 * seq(0, 127)) + rnorm(128, sd = 0.01)
  )

  out <- extract_gazepoint_eda_spectral_power(
    dat,
    eda_col = "GSR_US",
    time_col = "time",
    group_cols = "participant",
    sampling_rate = 1
  )

  expect_s3_class(out, "gazepoint_eda_spectral_power")
  expect_equal(out$overview$status, "eda_spectral_power_extracted")
  expect_true(is.finite(out$spectral_summary$band_power))
  expect_equal(out$spectral_summary$band_lower_hz, 0.045)
  expect_equal(out$spectral_summary$band_upper_hz, 0.25)
})

test_that("extract_gazepoint_hrv_nonlinear returns Poincare and entropy features", {
  dat <- data.frame(
    participant = "p1",
    IBI = 0.8 + sin(seq(0, 4 * pi, length.out = 60)) * 0.05
  )

  out <- extract_gazepoint_hrv_nonlinear(
    dat,
    ibi_col = "IBI",
    group_cols = "participant"
  )

  expect_s3_class(out, "gazepoint_hrv_nonlinear")
  expect_equal(out$overview$status, "nonlinear_hrv_extracted")
  expect_true(is.finite(out$features$sd1))
  expect_true(is.finite(out$features$sd2))
})

test_that("extract_gazepoint_eda_complexity returns EDA complexity features", {
  dat <- data.frame(
    participant = "p1",
    GSR_US = sin(seq(0, 8 * pi, length.out = 128)) + rnorm(128, sd = 0.05)
  )

  out <- extract_gazepoint_eda_complexity(
    dat,
    eda_col = "GSR_US",
    group_cols = "participant"
  )

  expect_s3_class(out, "gazepoint_eda_complexity")
  expect_equal(out$overview$status, "eda_complexity_extracted")
  expect_true(is.finite(out$features$dfa_alpha))
})

test_that("denoise_gazepoint_eda_wavelet adds denoised signal", {
  set.seed(1)
  dat <- data.frame(
    participant = "p1",
    GSR_US = sin(seq(0, 4 * pi, length.out = 64)) + rnorm(64, sd = 0.2)
  )

  out <- denoise_gazepoint_eda_wavelet(
    dat,
    eda_col = "GSR_US",
    group_cols = "participant"
  )

  expect_s3_class(out, "gazepoint_eda_wavelet_denoised")
  expect_true("GSR_US_wavelet_denoised" %in% names(out))
  expect_equal(attr(out, "wavelet_denoising_overview")$status, "eda_wavelet_denoising_complete")
})

test_that("audit_gazepoint_distributional_drift returns PSI and KS summaries", {
  dat <- data.frame(
    participant = rep("p1", 100),
    session = rep(c(1, 2), each = 50),
    GSR_US = c(rnorm(50, 1, 0.1), rnorm(50, 2, 0.1))
  )

  out <- audit_gazepoint_distributional_drift(
    dat,
    signal_cols = "GSR_US",
    session_col = "session",
    participant_col = "participant"
  )

  expect_s3_class(out, "gazepoint_distributional_drift")
  expect_true(is.data.frame(out$drift_summary))
  expect_true("psi" %in% names(out$drift_summary))
  expect_true(any(out$drift_summary$comparison_session == "2"))
})

test_that("run_gpbiometrics_shiny_annotator errors clearly without shiny or returns app", {
  if (!requireNamespace("shiny", quietly = TRUE)) {
    expect_error(run_gpbiometrics_shiny_annotator(), "shiny")
  } else {
    app <- run_gpbiometrics_shiny_annotator()
    expect_true(inherits(app, "shiny.appobj"))
  }
})
