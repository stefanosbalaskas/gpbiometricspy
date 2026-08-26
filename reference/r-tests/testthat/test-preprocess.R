test_that("baseline_correct_gazepoint_gsr baseline-corrects GSR_US", {
  dat <- data.frame(
    trial = c(1, 1, 1, 1),
    GSR_US = c(2.0, 2.2, 2.5, 2.7),
    GSRV = c(1, 1, 1, 1),
    baseline = c(TRUE, TRUE, FALSE, FALSE)
  )

  out <- baseline_correct_gazepoint_gsr(
    dat,
    baseline_rows = dat$baseline
  )

  expect_true("GSR_US_baseline_corrected" %in% names(out))
  expect_equal(out$GSR_US_baseline_corrected[1], -0.1, tolerance = 1e-8)
  expect_equal(out$GSR_US_baseline_corrected[2], 0.1, tolerance = 1e-8)
  expect_equal(out$GSR_US_baseline_corrected[3], 0.4, tolerance = 1e-8)

  baseline_summary <- attr(out, "baseline_summary")
  expect_true(is.data.frame(baseline_summary))
  expect_equal(baseline_summary$baseline_usable_rows, 2)
  expect_equal(baseline_summary$baseline_value, 2.1, tolerance = 1e-8)
})


test_that("baseline_correct_gazepoint_hr baseline-corrects HR", {
  dat <- data.frame(
    HR = c(70, 72, 80, 82),
    HRV = c(1, 1, 1, 1),
    baseline = c(TRUE, TRUE, FALSE, FALSE)
  )

  out <- baseline_correct_gazepoint_hr(
    dat,
    baseline_rows = dat$baseline
  )

  expect_true("HR_baseline_corrected" %in% names(out))
  expect_equal(out$HR_baseline_corrected[1], -1, tolerance = 1e-8)
  expect_equal(out$HR_baseline_corrected[2], 1, tolerance = 1e-8)
  expect_equal(out$HR_baseline_corrected[3], 9, tolerance = 1e-8)

  baseline_summary <- attr(out, "baseline_summary")
  expect_equal(baseline_summary$baseline_value, 71, tolerance = 1e-8)
})


test_that("baseline correction supports groups", {
  dat <- data.frame(
    participant = c("P1", "P1", "P1", "P2", "P2", "P2"),
    HR = c(70, 72, 80, 60, 62, 70),
    HRV = c(1, 1, 1, 1, 1, 1),
    baseline = c(TRUE, TRUE, FALSE, TRUE, TRUE, FALSE)
  )

  out <- baseline_correct_gazepoint_hr(
    dat,
    baseline_rows = dat$baseline,
    group_columns = "participant"
  )

  expect_equal(out$HR_baseline_corrected[3], 9, tolerance = 1e-8)
  expect_equal(out$HR_baseline_corrected[6], 9, tolerance = 1e-8)

  baseline_summary <- attr(out, "baseline_summary")
  expect_equal(nrow(baseline_summary), 2)
})


test_that("baseline correction excludes invalid and zero baseline rows", {
  dat <- data.frame(
    HR = c(0, 70, 90),
    HRV = c(0, 1, 1),
    baseline = c(TRUE, TRUE, FALSE)
  )

  out <- baseline_correct_gazepoint_hr(
    dat,
    baseline_rows = dat$baseline
  )

  expect_equal(out$HR_baseline_corrected[3], 20, tolerance = 1e-8)

  baseline_summary <- attr(out, "baseline_summary")
  expect_equal(baseline_summary$baseline_usable_rows, 1)
  expect_equal(baseline_summary$baseline_value, 70, tolerance = 1e-8)
})


test_that("smooth_gazepoint_biometrics computes centered moving average", {
  dat <- data.frame(
    HR = c(70, 72, 74, 76, 78)
  )

  out <- smooth_gazepoint_biometrics(
    dat,
    value_column = "HR",
    window = 3
  )

  expect_true("HR_smoothed" %in% names(out))
  expect_equal(out$HR_smoothed[1], 71, tolerance = 1e-8)
  expect_equal(out$HR_smoothed[3], 74, tolerance = 1e-8)
  expect_equal(out$HR_smoothed[5], 77, tolerance = 1e-8)
})


test_that("smooth_gazepoint_biometrics rejects even window", {
  dat <- data.frame(
    HR = c(70, 72, 74)
  )

  expect_error(
    smooth_gazepoint_biometrics(dat, value_column = "HR", window = 4),
    "positive odd integer"
  )
})
