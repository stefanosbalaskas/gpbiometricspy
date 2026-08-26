test_that("audit_gazepoint_biometric_sampling estimates sampling rate from seconds", {
  dat <- data.frame(
    source_participant = rep("User 1", 4),
    MEDIA_ID = rep(0, 4),
    TIME = c(0, 1 / 60, 2 / 60, 3 / 60)
  )

  out <- audit_gazepoint_biometric_sampling(
    dat,
    group_columns = c("source_participant", "MEDIA_ID"),
    time_column = "TIME",
    time_unit = "seconds",
    expected_rate_hz = 60,
    tolerance_hz = 1
  )

  expect_equal(nrow(out), 1)
  expect_equal(out$estimated_rate_hz, 60, tolerance = 1e-8)
  expect_equal(out$rate_status, "within_tolerance")
  expect_true(out$strictly_increasing)
})


test_that("audit_gazepoint_biometric_sampling supports milliseconds", {
  dat <- data.frame(
    TIME_TICK = c(0, 16.6667, 33.3334, 50.0001)
  )

  out <- audit_gazepoint_biometric_sampling(
    dat,
    time_column = "TIME_TICK",
    time_unit = "milliseconds",
    expected_rate_hz = 60,
    tolerance_hz = 1
  )

  expect_equal(nrow(out), 1)
  expect_equal(out$rate_status, "within_tolerance")
  expect_true(out$estimated_rate_hz > 59)
  expect_true(out$estimated_rate_hz < 61)
})


test_that("audit_gazepoint_biometric_sampling detects duplicate and nonmonotonic rows", {
  dat <- data.frame(
    TIME = c(0, 0.1, 0.1, 0.05)
  )

  out <- audit_gazepoint_biometric_sampling(
    dat,
    time_column = "TIME",
    time_unit = "seconds"
  )

  expect_equal(out$duplicate_time_rows, 1)
  expect_equal(out$zero_interval_rows, 1)
  expect_equal(out$negative_interval_rows, 1)
  expect_false(out$monotonic_non_decreasing)
  expect_false(out$strictly_increasing)
})


test_that("audit_gazepoint_biometric_sampling works with sample/order columns without rate estimation", {
  dat <- data.frame(
    CNT = c(1, 2, 3, 4)
  )

  out <- audit_gazepoint_biometric_sampling(
    dat,
    time_column = "CNT",
    time_unit = "samples"
  )

  expect_equal(out$rate_status, "not_estimated")
  expect_true(is.na(out$estimated_rate_hz))
  expect_true(out$strictly_increasing)
})


test_that("audit_gazepoint_biometric_sampling supports grouped output", {
  dat <- data.frame(
    source_participant = c("User 1", "User 1", "User 2", "User 2"),
    TIME = c(0, 0.1, 0, 0.2)
  )

  out <- audit_gazepoint_biometric_sampling(
    dat,
    group_columns = "source_participant",
    time_column = "TIME",
    time_unit = "seconds"
  )

  expect_equal(nrow(out), 2)
  expect_true(all(c("User 1", "User 2") %in% out$source_participant))
})


test_that("audit_gazepoint_biometric_sampling rejects missing timing column", {
  dat <- data.frame(
    GSR_US = c(1.1, 1.2)
  )

  expect_error(
    audit_gazepoint_biometric_sampling(dat),
    "No timing"
  )
})


test_that("audit_gazepoint_biometric_sampling rejects missing group columns", {
  dat <- data.frame(
    TIME = c(0, 0.1)
  )

  expect_error(
    audit_gazepoint_biometric_sampling(
      dat,
      group_columns = "source_participant"
    ),
    "group_columns"
  )
})
