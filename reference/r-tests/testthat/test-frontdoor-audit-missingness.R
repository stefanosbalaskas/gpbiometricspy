
test_that("summarize_gazepoint_missingness detects runs and long gaps", {
  dat <- data.frame(
    time_s = seq(0, 0.5, by = 0.1),
    GSR = c(1, NA, NA, 1.2, 1.3, NA),
    PPG = c(1, 1, 1, NA, 1, 1)
  )

  out <- summarize_gazepoint_missingness(
    dat,
    signal_cols = c("GSR", "PPG"),
    time_col = "time_s",
    long_gap_s = 0.15
  )

  gsr <- out[out$signal == "GSR", ]

  expect_equal(gsr$n_missing, 3)
  expect_equal(gsr$n_missing_runs, 2)
  expect_true(gsr$longest_missing_run_samples >= 2)
  expect_true(gsr$n_long_gaps >= 1)
})

test_that("summarize_gazepoint_missingness supports grouped summaries", {
  dat <- data.frame(
    participant = rep(c("P01", "P02"), each = 4),
    time_s = rep(seq(0, 0.3, by = 0.1), 2),
    pupil_left = c(1, NA, 1, 1, NA, NA, 2, 2)
  )

  out <- summarize_gazepoint_missingness(
    dat,
    signal_cols = "pupil_left",
    time_col = "time_s",
    group_cols = "participant"
  )

  expect_equal(nrow(out), 2)
  expect_true(out$n_missing[out$participant == "P02"] > out$n_missing[out$participant == "P01"])
})

test_that("detrend_gazepoint_signal removes linear drift", {
  dat <- data.frame(
    time_s = 1:100,
    GSR = 2 + 0.5 * (1:100)
  )

  out <- detrend_gazepoint_signal(dat, signal_col = "GSR", time_col = "time_s", method = "linear")

  fit <- stats::lm(GSR_detrended ~ time_s, data = out)

  expect_true(abs(stats::coef(fit)[2]) < 1e-10)
  expect_true(all(c("GSR_trend", "GSR_detrended") %in% names(out)))
})

test_that("detrend_gazepoint_signal supports grouped detrending", {
  dat <- data.frame(
    participant = rep(c("P01", "P02"), each = 10),
    time_s = rep(1:10, 2),
    signal = c(1:10, 10 + 2 * (1:10))
  )

  out <- detrend_gazepoint_signal(
    dat,
    signal_col = "signal",
    time_col = "time_s",
    group_cols = "participant",
    method = "linear"
  )

  p1 <- out[out$participant == "P01", ]
  p2 <- out[out$participant == "P02", ]

  expect_true(abs(stats::coef(stats::lm(signal_detrended ~ time_s, data = p1))[2]) < 1e-10)
  expect_true(abs(stats::coef(stats::lm(signal_detrended ~ time_s, data = p2))[2]) < 1e-10)
})

test_that("audit_gazepoint_biometrics_file returns preflight audit object", {
  dat <- data.frame(
    TIME = c(0, 0.1, 0.2, 0.3, 0.3),
    GSR_US = c(1, NA, 1.2, 1.3, 1.3),
    PPG = c(0, 1, 0, 1, 1),
    LPD = c(3, NA, NA, 3.2, 3.2)
  )

  dat <- rbind(dat, dat[5, ])

  out <- audit_gazepoint_biometrics_file(
    data = dat,
    expected_modalities = c("time", "eda", "ppg", "pupil", "gaze"),
    long_gap_s = 0.15
  )

  expect_true(inherits(out, "gazepoint_biometrics_audit"))
  expect_true(out$dimensions$n_rows == nrow(dat))
  expect_true(any(out$modalities$modality == "eda" & out$modalities$present))
  expect_true(any(grepl("Missing expected modalities", out$warnings)))
  expect_true(out$duplicate_rows$n_duplicate_rows >= 1)

  s <- summary(out)
  expect_true(s$n_warnings >= 1)
})

test_that("audit_gazepoint_biometrics_file reads CSV/TSV-style paths", {
  dat <- data.frame(
    TIME = c(0, 100, 200),
    GSR_US = c(1, 1.1, NA),
    PPG = c(0, 1, 0)
  )

  path <- tempfile(fileext = ".csv")
  utils::write.csv(dat, path, row.names = FALSE)

  out <- audit_gazepoint_biometrics_file(path = path, expected_modalities = c("time", "eda", "ppg"))

  expect_true(inherits(out, "gazepoint_biometrics_audit"))
  expect_true(out$dimensions$n_rows == 3)
  expect_true(any(out$modalities$present))
})

