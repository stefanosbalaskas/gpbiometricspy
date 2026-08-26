test_that("extract_gazepoint_hrv_fragmentation returns fragmentation features", {
  dat <- data.frame(
    participant = "p1",
    IBI = c(0.80, 0.82, 0.79, 0.83, 0.78, 0.84, 0.81, 0.85, 0.80, 0.86)
  )

  out <- extract_gazepoint_hrv_fragmentation(
    dat,
    ibi_col = "IBI",
    group_cols = "participant"
  )

  expect_s3_class(out, "gazepoint_hrv_fragmentation")
  expect_true("pip" %in% names(out$features))
  expect_true("ials" %in% names(out$features))
  expect_true(is.finite(out$features$pip))
})

test_that("extract_gazepoint_hrv_asymmetry returns run features", {
  dat <- data.frame(
    participant = "p1",
    IBI = c(0.80, 0.82, 0.84, 0.81, 0.79, 0.83, 0.85, 0.82, 0.80, 0.86)
  )

  out <- extract_gazepoint_hrv_asymmetry(
    dat,
    ibi_col = "IBI",
    group_cols = "participant"
  )

  expect_s3_class(out, "gazepoint_hrv_asymmetry")
  expect_true("guzik_index" %in% names(out$features))
  expect_true("porta_index" %in% names(out$features))
  expect_true(nrow(out$run_table) > 0)
})

test_that("model_gazepoint_eda_point_process summarises EDA events", {
  time <- seq(0, 60, by = 0.5)
  eda <- 1 + rnorm(length(time), sd = 0.005)
  events <- rep(0, length(time))
  events[time %in% c(10, 20, 35, 50)] <- 1

  dat <- data.frame(
    participant = "p1",
    time = time,
    GSR_US = eda,
    event = events
  )

  out <- model_gazepoint_eda_point_process(
    dat,
    eda_col = "GSR_US",
    time_col = "time",
    group_cols = "participant",
    event_indicator_col = "event"
  )

  expect_s3_class(out, "gazepoint_eda_point_process")
  expect_equal(nrow(out$event_table), 4)
  expect_true("inverse_gaussian_mu" %in% names(out$process_summary))
})

test_that("model_gazepoint_hr_point_process summarises heartbeat intervals", {
  dat <- data.frame(
    participant = "p1",
    IBI = rep(0.8, 30) + rnorm(30, sd = 0.02)
  )

  out <- model_gazepoint_hr_point_process(
    dat,
    ibi_col = "IBI",
    group_cols = "participant"
  )

  expect_s3_class(out, "gazepoint_hr_point_process")
  expect_true(nrow(out$beat_table) > 0)
  expect_true("inverse_gaussian_lambda" %in% names(out$process_summary))
})

test_that("analyze_gazepoint_cardiorespiratory_causality returns Granger-style summaries", {
  set.seed(1)

  n <- 120
  resp <- sin(seq(0, 8 * pi, length.out = n))
  cardiac <- c(rep(0, 3), resp[1:(n - 3)]) + rnorm(n, sd = 0.1)

  dat <- data.frame(
    participant = "p1",
    time = seq_len(n),
    resp = resp,
    cardiac = cardiac
  )

  out <- analyze_gazepoint_cardiorespiratory_causality(
    dat,
    respiration_col = "resp",
    cardiac_col = "cardiac",
    time_col = "time",
    group_cols = "participant",
    lag_order = 3,
    min_rows = 40
  )

  expect_s3_class(out, "gazepoint_cardiorespiratory_causality")
  expect_true("respiration_to_cardiac_p" %in% names(out$causality_summary))
  expect_equal(out$overview$status, "cardiorespiratory_directionality_estimated")
})

test_that("prepare_gazepoint_ctsi_input creates signal and config tables", {
  dat <- data.frame(
    participant = "p1",
    time = seq(0, 20, by = 0.5),
    GSR_US = 1 + sin(seq(0, 20, by = 0.5)) * 0.05,
    onset = rep(c(5, 10, NA), length.out = 41),
    condition = rep(c("A", "B", "none"), length.out = 41)
  )

  out <- prepare_gazepoint_ctsi_input(
    dat,
    eda_col = "GSR_US",
    time_col = "time",
    group_cols = "participant",
    event_onset_col = "onset",
    event_name_col = "condition",
    sampling_rate = 2
  )

  expect_s3_class(out, "gazepoint_ctsi_input")
  expect_true(nrow(out$signal_table) > 0)
  expect_true(nrow(out$ctsi_config) > 0)
  expect_equal(out$overview$status, "ctsi_input_prepared")
})
