test_that("validate_gazepoint_biometrics validates active biometric data", {
  dat <- data.frame(
    TIME = c(0.01, 0.02, 0.03),
    GSR_US = c(2.0, 2.1, 2.2),
    GSRV = c(1, 1, 1),
    HR = c(75, 76, 77),
    HRV = c(1, 1, 1),
    DIAL = c(0.1, 0.2, 0.3),
    DIALV = c(1, 1, 1)
  )

  val <- validate_gazepoint_biometrics(dat, require_active_signal = TRUE)

  expect_s3_class(val, "gazepoint_biometrics_validation")
  expect_equal(val$overview$n_rows, 3)
  expect_equal(val$overview$active_signal_count, 3)
  expect_equal(nrow(val$issues), 0)
})


test_that("validate_gazepoint_biometrics reports inactive biometric data", {
  dat <- data.frame(
    TIME = c(0.01, 0.02, 0.03),
    GSR_US = c(0, 0, 0),
    GSRV = c(0, 0, 0),
    HR = c(0, 0, 0),
    HRV = c(0, 0, 0),
    DIAL = c(0, 0, 0),
    DIALV = c(0, 0, 0)
  )

  val <- validate_gazepoint_biometrics(dat, require_active_signal = TRUE)

  expect_true("no_active_biometric_signal" %in% val$issues$issue)
  expect_equal(val$overview$active_signal_count, 0)
})


test_that("validate_gazepoint_biometrics reports missing biometric columns", {
  dat <- data.frame(
    TIME = c(0.01, 0.02),
    X = c(1, 2),
    Y = c(3, 4)
  )

  val <- validate_gazepoint_biometrics(dat)

  expect_true("no_known_biometric_columns" %in% val$issues$issue)
})


test_that("audit_gazepoint_biometric_missingness summarises columns", {
  dat <- data.frame(
    GSR_US = c(2.0, NA, 0),
    GSRV = c(1, 0, 0),
    HR = c(75, NA, 0),
    HRV = c(1, 0, 0),
    DIAL = c(0.1, NA, 0),
    DIALV = c(1, 0, 0)
  )

  audit <- audit_gazepoint_biometric_missingness(dat)

  expect_true(is.data.frame(audit))
  expect_true("GSR_US" %in% audit$column)
  expect_true("HR" %in% audit$column)
  expect_true("DIAL" %in% audit$column)

  gsr <- audit[audit$column == "GSR_US", ]

  expect_equal(gsr$n_rows, 3)
  expect_equal(gsr$missing_rows, 1)
  expect_equal(gsr$zero_rows, 1)
})


test_that("audit_gazepoint_biometric_missingness returns empty table when no known columns exist", {
  dat <- data.frame(
    X = c(1, 2),
    Y = c(3, 4)
  )

  audit <- audit_gazepoint_biometric_missingness(dat)

  expect_true(is.data.frame(audit))
  expect_equal(nrow(audit), 0)
})
