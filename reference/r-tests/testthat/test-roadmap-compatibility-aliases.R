
test_that("standardize_gazepoint_columns delegates to the standardizer", {
  dat <- data.frame(
    TIME = c(0, 1),
    GSR_US = c(1, 2)
  )

  out <- standardize_gazepoint_columns(dat)

  expect_true(is.data.frame(out))
  expect_equal(nrow(out), nrow(dat))
})

test_that("validate_gazepoint_format reports required and optional columns", {
  dat <- data.frame(
    time_s = c(0, 1, 2),
    GSR = c(1, 1.1, 1.2)
  )

  out <- validate_gazepoint_format(
    dat,
    required_cols = c("time_s", "GSR"),
    optional_cols = c("PPG", "pupil_left")
  )

  expect_true(inherits(out, "gazepoint_format_validation"))
  expect_true(out$valid)
  expect_equal(length(out$missing_required), 0)
  expect_true("PPG" %in% out$missing_optional)
})

test_that("validate_gazepoint_format fails when required columns are absent", {
  dat <- data.frame(
    time_s = c(0, 1, 2),
    GSR = c(1, 1.1, 1.2)
  )

  out <- validate_gazepoint_format(
    dat,
    required_cols = c("time_s", "PPG")
  )

  expect_false(out$valid)
  expect_true("PPG" %in% out$missing_required)
})

test_that("interpolate_gazepoint_pupil_blinks interpolates internal pupil gaps", {
  dat <- data.frame(
    time_s = seq(0, 0.5, by = 0.1),
    pupil_left = c(3, NA, NA, 3.3, 3.4, 3.5),
    blink = c(FALSE, TRUE, TRUE, FALSE, FALSE, FALSE)
  )

  out <- interpolate_gazepoint_pupil_blinks(
    dat,
    pupil_cols = "pupil_left",
    time_col = "time_s",
    blink_col = "blink",
    max_gap_s = 0.25
  )

  expect_true("pupil_left_interp" %in% names(out))
  expect_true("pupil_left_was_interpolated" %in% names(out))
  expect_true(all(is.finite(out$pupil_left_interp[2:3])))
  expect_true(all(out$pupil_left_was_interpolated[2:3]))
})

test_that("interpolate_gazepoint_pupil_blinks respects max gap threshold", {
  dat <- data.frame(
    time_s = seq(0, 1.0, by = 0.1),
    pupil_left = c(3, rep(NA, 5), 3.6, 3.7, 3.8, 3.9, 4.0)
  )

  out <- interpolate_gazepoint_pupil_blinks(
    dat,
    pupil_cols = "pupil_left",
    time_col = "time_s",
    max_gap_s = 0.20
  )

  expect_true(all(is.na(out$pupil_left_interp[2:6])))
  expect_false(any(out$pupil_left_was_interpolated[2:6]))
})

test_that("clean_gazepoint_pupil provides short-name pupil cleaning", {
  dat <- data.frame(
    time_s = seq(0, 0.4, by = 0.1),
    pupil_left = c(3, NA, 3.2, 3.3, 3.4)
  )

  out <- clean_gazepoint_pupil(
    dat,
    pupil_cols = "pupil_left",
    time_col = "time_s",
    max_gap_s = 0.20
  )

  expect_true("pupil_left_clean" %in% names(out))
  expect_true(is.finite(out$pupil_left_clean[2]))
})

test_that("respiration_from_ppg delegates to conservative respiration estimator", {
  fs <- 20
  time <- seq(0, 90, by = 1 / fs)
  ppg <- sin(2 * pi * 0.20 * time)

  out <- respiration_from_ppg(ppg, sampling_rate_hz = fs)

  expect_true(is.list(out))
  expect_true("summary" %in% names(out))
  expect_true(abs(out$summary$respiration_rate_bpm - 12) < 1)
})

test_that("prepare_gazepoint_mixed_model_data prepares factors and numeric predictors", {
  dat <- data.frame(
    participant = rep(c("P01", "P02"), each = 3),
    trial = rep(1:3, 2),
    condition = rep(c("A", "B", "A"), 2),
    outcome = c(1, 2, 3, 2, NA, 4),
    pupil = c(3.1, 3.2, 3.3, 3.0, 3.1, 3.4)
  )

  out <- prepare_gazepoint_mixed_model_data(
    dat,
    outcome_cols = "outcome",
    participant_col = "participant",
    trial_col = "trial",
    condition_cols = "condition",
    numeric_cols = "pupil",
    center_numeric = TRUE,
    scale_numeric = TRUE
  )

  expect_true(inherits(out, "gazepoint_mixed_model_data"))
  expect_true(is.factor(out$participant))
  expect_true(is.factor(out$condition))
  expect_equal(nrow(out), 5)
  expect_true("pupil_c" %in% names(out))
  expect_true("pupil_z" %in% names(out))
})

