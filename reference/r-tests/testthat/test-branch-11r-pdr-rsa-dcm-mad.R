test_that("extract_gazepoint_pdr_signals returns PDR summaries", {
  set.seed(1)

  time <- seq(0, 60, by = 0.05)
  respiration <- 1 + 0.15 * sin(2 * pi * 0.25 * time)
  ppg <- respiration * sin(2 * pi * 1.2 * time) + 0.02 * rnorm(length(time))

  dat <- data.frame(
    participant = "p1",
    time = time,
    HRP = ppg
  )

  out <- extract_gazepoint_pdr_signals(
    dat,
    ppg_col = "HRP",
    time_col = "time",
    group_cols = "participant",
    sampling_rate = 20,
    min_peak_distance_s = 0.4
  )

  expect_s3_class(out, "gazepoint_pdr_signals")
  expect_true(nrow(out$pulse_features) > 10)
  expect_true("proxy_resp_rate_hz" %in% names(out$pdr_summary))
  expect_true(out$overview$status %in% c("pdr_extraction_complete", "pdr_extraction_partial"))
})

test_that("calculate_gazepoint_rsa returns respiration-informed RSA proxies", {
  set.seed(1)

  time_ppg <- seq(0, 60, by = 0.05)
  respiration <- 1 + 0.15 * sin(2 * pi * 0.25 * time_ppg)
  ppg <- respiration * sin(2 * pi * 1.2 * time_ppg) + 0.02 * rnorm(length(time_ppg))

  ppg_dat <- data.frame(
    participant = "p1",
    time = time_ppg,
    HRP = ppg
  )

  pdr <- extract_gazepoint_pdr_signals(
    ppg_dat,
    ppg_col = "HRP",
    time_col = "time",
    group_cols = "participant",
    sampling_rate = 20,
    min_peak_distance_s = 0.4
  )

  ibi_time <- seq(0, 60, by = 1)
  ibi_dat <- data.frame(
    participant = "p1",
    time = ibi_time,
    IBI = 0.8 + 0.05 * sin(2 * pi * 0.25 * ibi_time)
  )

  rsa <- calculate_gazepoint_rsa(
    ibi_dat,
    ibi_col = "IBI",
    time_col = "time",
    group_cols = "participant",
    pdr = pdr
  )

  expect_s3_class(rsa, "gazepoint_rsa_proxy")
  expect_true("rsa_pb_log_power_proxy" %in% names(rsa$rsa_summary))
  expect_true(rsa$overview$status %in% c("rsa_proxy_complete", "rsa_proxy_partial"))
})

test_that("extended nonlinear HRV features include ApEn, DFA, and MSE", {
  dat <- data.frame(
    participant = "p1",
    IBI = 0.8 + 0.04 * sin(seq(0, 10 * pi, length.out = 80)) + rnorm(80, sd = 0.005)
  )

  out <- extract_gazepoint_hrv_nonlinear(
    dat,
    ibi_col = "IBI",
    group_cols = "participant",
    mse_scales = 1:3
  )

  expect_s3_class(out, "gazepoint_hrv_nonlinear")
  expect_true("approximate_entropy" %in% names(out$features))
  expect_true("dfa_alpha" %in% names(out$features))
  expect_true("mse_mean" %in% names(out$features))
  expect_true("mse_scale_1" %in% names(out$features))
})

test_that("flag_gazepoint_mad_artifacts flags wearable artifact typology", {
  x <- c(
    seq(1, 1.2, length.out = 10),
    rep(1.2, 8),
    5,
    1.3,
    1.31,
    8,
    8.1,
    8.2
  )

  dat <- data.frame(
    participant = "p1",
    time = seq_along(x),
    GSR_US = x
  )

  out <- flag_gazepoint_mad_artifacts(
    dat,
    eda_col = "GSR_US",
    time_col = "time",
    group_cols = "participant",
    mad_multiplier = 4,
    flatline_tolerance = 1e-8,
    flatline_min_run = 4
  )

  expect_s3_class(out, "gazepoint_mad_artifact_flags")
  expect_true("mad_artifact" %in% names(out))
  expect_true(any(out$mad_artifact))
  expect_true(any(out$mad_artifact_type %in% c("flatline", "needle", "step", "wall", "multiple")))
})

test_that("prepare_gazepoint_pspm_dcm_input creates signal and event tables", {
  dat <- data.frame(
    participant = "p1",
    session = "s1",
    time = seq(0, 10, by = 0.5),
    GSR_US = 1 + sin(seq(0, 10, by = 0.5)) * 0.1,
    event_onset = rep(c(2, 6, NA), length.out = 21),
    event_duration = 0,
    condition = rep(c("A", "B", "none"), length.out = 21)
  )

  out <- prepare_gazepoint_pspm_dcm_input(
    dat,
    eda_col = "GSR_US",
    time_col = "time",
    event_onset_col = "event_onset",
    event_duration_col = "event_duration",
    event_name_col = "condition",
    participant_col = "participant",
    session_col = "session"
  )

  expect_s3_class(out, "gazepoint_pspm_dcm_input")
  expect_true(nrow(out$signal_table) > 0)
  expect_true(nrow(out$event_table) > 0)
  expect_equal(out$overview$status, "pspm_dcm_input_prepared")
})
