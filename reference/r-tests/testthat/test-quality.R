test_that("audit_gazepoint_gsr_quality audits active GSR_US signal", {
  dat <- data.frame(
    GSR_US = c(2.0, 2.1, 2.2, NA, 0),
    GSRV = c(1, 1, 1, 0, 0)
  )

  audit <- audit_gazepoint_gsr_quality(dat)

  expect_equal(audit$signal, "gsr_eda")
  expect_equal(audit$value_column, "GSR_US")
  expect_equal(audit$n_rows, 5)
  expect_equal(audit$missing_rows, 1)
  expect_equal(audit$zero_rows, 1)
  expect_equal(audit$usable_rows, 3)
})


test_that("audit_gazepoint_gsr_quality falls back to GSR when GSR_US is absent", {
  dat <- data.frame(
    GSR = c(500000, 510000, 520000),
    GSRV = c(1, 1, 1)
  )

  audit <- audit_gazepoint_gsr_quality(
    dat,
    min_value = 1,
    max_value = 1000000
  )

  expect_equal(audit$value_column, "GSR")
  expect_equal(audit$usable_rows, 3)
})


test_that("audit_gazepoint_hr_quality flags impossible heart-rate values", {
  dat <- data.frame(
    HR = c(75, 76, 300, 0, NA),
    HRV = c(1, 1, 1, 0, 0)
  )

  audit <- audit_gazepoint_hr_quality(dat)

  expect_equal(audit$signal, "heart_rate")
  expect_equal(audit$n_rows, 5)
  expect_equal(audit$high_rows, 1)
  expect_equal(audit$zero_rows, 1)
  expect_equal(audit$missing_rows, 1)
  expect_equal(audit$usable_rows, 2)
})


test_that("audit_gazepoint_hr_quality detects large jumps", {
  dat <- data.frame(
    HR = c(75, 76, 130, 131),
    HRV = c(1, 1, 1, 1)
  )

  audit <- audit_gazepoint_hr_quality(dat, jump_threshold = 25)

  expect_equal(audit$large_jump_rows, 1)
})


test_that("audit_gazepoint_engagement_dial audits dial range", {
  dat <- data.frame(
    DIAL = c(0.1, 0.2, 1.2, 0, NA),
    DIALV = c(1, 1, 1, 0, 0)
  )

  audit <- audit_gazepoint_engagement_dial(dat)

  expect_equal(audit$signal, "engagement_dial")
  expect_equal(audit$high_rows, 1)
  expect_equal(audit$zero_rows, 1)
  expect_equal(audit$missing_rows, 1)
  expect_equal(audit$usable_rows, 2)
})


test_that("quality audits return empty audit when value column is missing", {
  dat <- data.frame(
    X = c(1, 2, 3)
  )

  audit <- audit_gazepoint_hr_quality(dat)

  expect_equal(audit$signal, "heart_rate")
  expect_equal(audit$issue, "value_column_missing")
  expect_equal(audit$usable_rows, 0)
})
test_that("quality audits summarise usable values rather than inactive zeros", {
  dat <- data.frame(
    GSR_US = c(0, 2, 4),
    GSRV = c(0, 1, 1),
    HR = c(0, 70, 80),
    HRV = c(0, 1, 1)
  )

  gsr <- audit_gazepoint_gsr_quality(dat)
  hr <- audit_gazepoint_hr_quality(dat)

  expect_equal(gsr$usable_rows, 2)
  expect_equal(gsr$min_value, 2)
  expect_equal(gsr$max_value, 4)
  expect_equal(gsr$mean_value, 3)

  expect_equal(hr$usable_rows, 2)
  expect_equal(hr$min_value, 70)
  expect_equal(hr$max_value, 80)
  expect_equal(hr$mean_value, 75)
})
