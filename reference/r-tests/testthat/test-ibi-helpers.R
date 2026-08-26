test_that("audit_gazepoint_ibi_quality audits valid millisecond IBI data", {
  df <- data.frame(
    USER = rep(c("P1", "P2"), each = 4),
    IBI = c(800, 810, 790, 805, 900, 910, 905, 920)
  )

  out <- audit_gazepoint_ibi_quality(df, group_cols = "USER")

  expect_type(out, "list")
  expect_s3_class(out$overview, "data.frame")
  expect_s3_class(out$samples, "data.frame")
  expect_s3_class(out$group_summary, "data.frame")

  expect_equal(out$overview$ibi_column, "IBI")
  expect_equal(out$overview$unit, "milliseconds")
  expect_equal(out$overview$n_valid_ibi, 8)
  expect_equal(out$overview$status, "ibi_quality_ok")
  expect_equal(nrow(out$group_summary), 2)
  expect_true(all(out$samples$valid_ibi))
})


test_that("audit_gazepoint_ibi_quality detects seconds automatically", {
  df <- data.frame(
    IBI = c(0.8, 0.81, 0.79, 0.805)
  )

  out <- audit_gazepoint_ibi_quality(df)

  expect_equal(out$overview$unit, "seconds")
  expect_equal(out$samples$ibi_ms, c(800, 810, 790, 805))
  expect_equal(out$overview$status, "ibi_quality_ok")
})


test_that("audit_gazepoint_ibi_quality flags implausible and missing intervals", {
  df <- data.frame(
    IBI = c(800, NA, 0, 250, 2500, Inf, 810)
  )

  out <- audit_gazepoint_ibi_quality(df)

  expect_equal(out$overview$n_missing_ibi, 1)
  expect_equal(out$overview$n_nonpositive_ibi, 1)
  expect_equal(out$overview$n_below_min_ibi, 1)
  expect_equal(out$overview$n_above_max_ibi, 1)
  expect_equal(out$overview$n_nonfinite_ibi, 1)
  expect_equal(out$overview$status, "ibi_quality_issues_detected")

  expect_true("missing_ibi" %in% out$samples$status)
  expect_true("nonpositive_ibi" %in% out$samples$status)
  expect_true("below_min_ibi" %in% out$samples$status)
  expect_true("above_max_ibi" %in% out$samples$status)
  expect_true("nonfinite_ibi" %in% out$samples$status)
})


test_that("audit_gazepoint_ibi_quality flags large jumps within ordered groups", {
  df <- data.frame(
    USER = c("P1", "P1", "P1", "P1"),
    TIME = c(1, 2, 3, 4),
    IBI = c(800, 810, 1500, 1510)
  )

  out <- audit_gazepoint_ibi_quality(
    df,
    group_cols = "USER",
    time_col = "TIME",
    max_jump_ms = 500
  )

  expect_true(out$samples$large_jump_ibi[3])
  expect_false(out$samples$large_jump_ibi[4])
  expect_equal(out$overview$n_large_jump_ibi, 1)
  expect_equal(out$overview$status, "ibi_quality_issues_detected")
})


test_that("audit_gazepoint_ibi_quality does not treat HRV as IBI", {
  df <- data.frame(
    HRV = c(1, 1, 1, 0),
    HR = c(70, 71, 72, 73)
  )

  expect_error(
    audit_gazepoint_ibi_quality(df),
    "No IBI/RR interval column"
  )
})


test_that("audit_gazepoint_ibi_quality validates arguments", {
  df <- data.frame(IBI = c(800, 810, 790))

  expect_error(
    audit_gazepoint_ibi_quality(1:3),
    "`data` must be"
  )

  expect_error(
    audit_gazepoint_ibi_quality(df, ibi_col = "missing"),
    "not found"
  )

  expect_error(
    audit_gazepoint_ibi_quality(data.frame(IBI = letters[1:3])),
    "must be numeric"
  )

  expect_error(
    audit_gazepoint_ibi_quality(df, min_ibi_ms = 0),
    "`min_ibi_ms`"
  )

  expect_error(
    audit_gazepoint_ibi_quality(df, min_ibi_ms = 1000, max_ibi_ms = 500),
    "`min_ibi_ms` must be smaller"
  )
})


test_that("summarise_gazepoint_ibi_windows summarises valid IBI windows", {
  df <- data.frame(
    USER = rep(c("P1", "P2"), each = 4),
    IBI = c(800, 810, 790, 805, 900, 910, 905, 920)
  )

  out <- summarise_gazepoint_ibi_windows(df, group_cols = "USER")

  expect_type(out, "list")
  expect_s3_class(out$overview, "data.frame")
  expect_s3_class(out$windows, "data.frame")
  expect_s3_class(out$samples, "data.frame")

  expect_equal(out$overview$window_count, 2)
  expect_equal(out$overview$sufficient_window_count, 2)
  expect_equal(out$overview$status, "ibi_windows_summarised")
  expect_true(all(out$windows$status == "sufficient_ibi_window"))
  expect_true(all(c("sdnn_ms", "rmssd_ms", "pnn20", "pnn50") %in% names(out$windows)))
})


test_that("summarise_gazepoint_ibi_windows can summarise all rows as one window", {
  df <- data.frame(
    IBI = c(800, 810, 790, 805)
  )

  out <- summarise_gazepoint_ibi_windows(df)

  expect_equal(nrow(out$windows), 1)
  expect_equal(out$windows$group, "all")
  expect_equal(out$windows$n_valid_ibi, 4)
  expect_equal(out$overview$status, "ibi_windows_summarised")
})


test_that("summarise_gazepoint_ibi_windows excludes large jumps by default", {
  df <- data.frame(
    IBI = c(800, 810, 1500, 1510)
  )

  out <- summarise_gazepoint_ibi_windows(
    df,
    max_jump_ms = 500,
    min_valid_ibi = 2
  )

  expect_true(out$samples$large_jump_ibi[3])
  expect_equal(out$windows$n_valid_ibi, 3)
  expect_equal(out$overview$status, "ibi_windows_summarised")
})


test_that("summarise_gazepoint_ibi_windows can keep large jumps when requested", {
  df <- data.frame(
    IBI = c(800, 810, 1500, 1510)
  )

  out <- summarise_gazepoint_ibi_windows(
    df,
    max_jump_ms = 500,
    exclude_large_jumps = FALSE
  )

  expect_equal(out$windows$n_valid_ibi, 4)
})


test_that("summarise_gazepoint_ibi_windows marks insufficient windows", {
  df <- data.frame(
    USER = c("P1", "P1", "P2", "P2"),
    IBI = c(800, NA, 900, NA)
  )

  out <- summarise_gazepoint_ibi_windows(
    df,
    group_cols = "USER",
    min_valid_ibi = 2
  )

  expect_equal(out$overview$sufficient_window_count, 0)
  expect_equal(out$overview$status, "no_sufficient_ibi_windows")
  expect_true(all(out$windows$status == "insufficient_ibi_window"))
})


test_that("summarise_gazepoint_ibi_windows validates arguments", {
  df <- data.frame(IBI = c(800, 810, 790))

  expect_error(
    summarise_gazepoint_ibi_windows(1:3),
    "`data` must be"
  )

  expect_error(
    summarise_gazepoint_ibi_windows(df, group_cols = "missing"),
    "not found"
  )

  expect_error(
    summarise_gazepoint_ibi_windows(df, exclude_large_jumps = NA),
    "`exclude_large_jumps`"
  )

  expect_error(
    summarise_gazepoint_ibi_windows(df, min_valid_ibi = 0),
    "`min_valid_ibi`"
  )
})


test_that("summarise_gazepoint_ibi_windows documents conservative HRV interpretation", {
  df <- data.frame(
    IBI = c(800, 810, 790, 805)
  )

  out <- summarise_gazepoint_ibi_windows(df)

  expect_match(out$settings$note, "genuine IBI/RR intervals")
  expect_match(out$settings$note, "not calculated from raw HRV")
})
