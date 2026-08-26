
test_that("create_gazepoint_trial_regressors creates event-level features", {
  dat <- data.frame(
    time_s = seq(0, 10, by = 1),
    GSR = seq(0, 1, length.out = 11),
    PPG = seq(10, 20, length.out = 11)
  )

  design <- data.frame(
    trial = c("T1", "T2"),
    onset = c(2, 7),
    condition = c("A", "B")
  )

  out <- create_gazepoint_trial_regressors(
    dat,
    design,
    pre = 1,
    post = 2,
    event_time_col = "onset",
    event_id_col = "trial"
  )

  expect_true(is.data.frame(out))
  expect_equal(nrow(out), 2)
  expect_true(all(c("trial_id", "event_time", "GSR_mean", "PPG_mean", "n_samples") %in% names(out)))
  expect_equal(out$trial_id, c("T1", "T2"))
  expect_true(all(out$n_samples > 0))
})

test_that("create_gazepoint_trial_regressors accepts numeric event vector", {
  dat <- data.frame(time_s = 0:10, signal = 0:10)

  out <- create_gazepoint_trial_regressors(
    dat,
    design = c(2, 5),
    pre = 0,
    post = 1,
    signal_cols = "signal"
  )

  expect_equal(nrow(out), 2)
  expect_true("signal_mean" %in% names(out))
})

test_that("report_gazepoint_data_quality writes html and csv reports", {
  tmp <- tempfile("gp_quality_")

  dat <- data.frame(
    time_s = 1:5,
    GSR = c(1, NA, 3, 4, 100),
    label = letters[1:5]
  )

  out <- report_gazepoint_data_quality(
    dat,
    output_dir = tmp,
    formats = c("html", "csv")
  )

  expect_true(file.exists(out$paths$html))
  expect_true(file.exists(out$paths$missingness_csv))
  expect_true(file.exists(out$paths$numeric_summary_csv))
  expect_true(file.exists(out$paths$outlier_summary_csv))
  expect_true(is.data.frame(out$missingness))
  expect_true(is.data.frame(out$numeric_summary))
})

test_that("report_gazepoint_data_quality handles list inputs", {
  tmp <- tempfile("gp_quality_list_")

  dat <- list(
    biometrics = data.frame(time_s = 1:3, GSR = c(1, 2, NA)),
    gaze = data.frame(time_s = 1:3, BPOGX = c(.1, .2, .3))
  )

  out <- report_gazepoint_data_quality(
    dat,
    output_dir = tmp,
    formats = "csv"
  )

  expect_true(file.exists(out$paths$missingness_csv))
  expect_true(all(c("biometrics", "gaze") %in% out$missingness$table))
})

test_that("report_gazepoint_data_quality can create a PDF plot file", {
  tmp <- tempfile("gp_quality_pdf_")

  dat <- data.frame(time_s = 1:5, GSR = c(1, 2, 3, 4, 5))

  out <- report_gazepoint_data_quality(
    dat,
    output_dir = tmp,
    formats = "pdf"
  )

  expect_true(file.exists(out$paths$pdf))
  expect_true(file.info(out$paths$pdf)$size > 0)
})

test_that("preprocess_gazepoint_all imputes numeric missing values", {
  dat <- data.frame(
    time_s = 1:5,
    GSR = c(1, NA, 3, 4, 5)
  )

  out <- preprocess_gazepoint_all(
    dat,
    clean_pupil = FALSE,
    filter_gaze = FALSE,
    verbose = FALSE
  )

  expect_true(is.data.frame(out))
  expect_false(anyNA(out$GSR))
  expect_true("GSR_was_imputed" %in% names(out))

  log <- attr(out, "preprocessing_log")
  expect_true(is.data.frame(log))
  expect_true("impute_missing" %in% log$step)
})

test_that("preprocess_gazepoint_all handles lists of data frames", {
  dat <- list(
    biometrics = data.frame(time_s = 1:4, GSR = c(1, NA, 3, 4)),
    gaze = data.frame(time_s = 1:3, BPOGX = c(.1, .2, .3), BPOGY = c(.1, .2, .3))
  )

  out <- preprocess_gazepoint_all(
    dat,
    clean_pupil = FALSE,
    filter_gaze = TRUE,
    verbose = FALSE
  )

  expect_true(is.list(out))
  expect_false(anyNA(out$biometrics$GSR))
  expect_true("gaze_valid" %in% names(out$gaze))

  log <- attr(out, "preprocessing_log")
  expect_true(is.data.frame(log))
  expect_true(any(log$step == "filter_gaze"))
})

test_that("preprocess_gazepoint_all can clean pupil when pupil columns exist", {
  dat <- data.frame(
    time_s = 1:5,
    LPD = c(3, NA, 3.2, 30, 3.3)
  )

  out <- preprocess_gazepoint_all(
    dat,
    impute_missing = FALSE,
    clean_pupil = TRUE,
    filter_gaze = FALSE,
    verbose = FALSE
  )

  expect_true(any(grepl("LPD_clean", names(out))))
  expect_true("LPD_was_blink" %in% names(out))
})

