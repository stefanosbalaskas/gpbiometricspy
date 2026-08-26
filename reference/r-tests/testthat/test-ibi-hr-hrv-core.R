test_that("filter_gazepoint_ibi_implausible flags implausible IBI values", {
  dat <- data.frame(
    participant = "P1",
    IBI = c(1000, 1020, 250, 1050, 2500, 1080)
  )

  res <- filter_gazepoint_ibi_implausible(
    dat,
    ibi_col = "IBI",
    group_cols = "participant",
    min_ibi_ms = 300,
    max_ibi_ms = 2000,
    max_change_ms = 500,
    max_change_prop = 0.5
  )

  expect_s3_class(res, "gazepoint_ibi_filter")
  expect_equal(res$overview$detected_unit, "ms")
  expect_true(any(res$row_flags$flag_too_low))
  expect_true(any(res$row_flags$flag_too_high))
  expect_true("IBI_clean_ms" %in% names(res$data))
})

test_that("filter_gazepoint_ibi_implausible detects seconds automatically", {
  dat <- data.frame(
    participant = "P1",
    IBI = c(1.0, 1.1, 0.9)
  )

  res <- filter_gazepoint_ibi_implausible(
    dat,
    ibi_col = "IBI",
    group_cols = "participant"
  )

  expect_equal(res$overview$detected_unit, "seconds")
  expect_equal(res$row_flags$ibi_ms, c(1000, 1100, 900))
})

test_that("filter_gazepoint_ibi_implausible respects validity flags", {
  dat <- data.frame(
    participant = "P1",
    IBI = c(1000, 1000, 1000),
    IBIV = c(1, 0, 1)
  )

  res <- filter_gazepoint_ibi_implausible(
    dat,
    ibi_col = "IBI",
    validity_col = "IBIV",
    group_cols = "participant"
  )

  expect_equal(sum(res$row_flags$flag_invalid_validity), 1)
  expect_equal(sum(is.na(res$data$IBI_clean_ms)), 1)
})

test_that("compare_gazepoint_hr_ibi_consistency detects matching and mismatching rows", {
  dat <- data.frame(
    participant = "P1",
    HR = c(60, 60, 100),
    IBI = c(1000, 1000, 1000)
  )

  res <- compare_gazepoint_hr_ibi_consistency(
    dat,
    hr_col = "HR",
    ibi_col = "IBI",
    group_cols = "participant",
    max_abs_diff_bpm = 10
  )

  expect_s3_class(res, "gazepoint_hr_ibi_consistency")
  expect_equal(res$overview$comparable_rows, 3)
  expect_equal(res$overview$inconsistent_rows, 1)
  expect_true(any(res$row_diagnostics$flag_inconsistent))
})

test_that("compare_gazepoint_hr_ibi_consistency accepts filtered IBI objects", {
  dat <- data.frame(
    participant = "P1",
    HR = c(60, 55),
    IBI = c(1000, 1090)
  )

  filtered <- filter_gazepoint_ibi_implausible(
    dat,
    ibi_col = "IBI",
    group_cols = "participant"
  )

  res <- compare_gazepoint_hr_ibi_consistency(
    filtered,
    hr_col = "HR",
    ibi_col = "IBI_clean_ms",
    group_cols = "participant"
  )

  expect_equal(res$overview$comparable_rows, 2)
})

test_that("extract_gazepoint_hrv_features collapses repeated IBI values by default", {
  dat <- data.frame(
    participant = "P1",
    IBI_clean_ms = c(
      1000, 1000, 1000,
      1020, 1020,
      980, 980,
      1010
    )
  )

  res <- extract_gazepoint_hrv_features(
    dat,
    ibi_col = "IBI_clean_ms",
    group_cols = "participant",
    min_intervals = 3,
    min_duration_s = 0
  )

  expect_equal(res$features$input_interval_rows, 8)
  expect_equal(res$features$used_intervals_after_collapse, 4)
  expect_true(res$features$collapsed_repeated_intervals)
  expect_equal(res$features$n_intervals, 4)
  expect_equal(res$features$feature_status, "features_computed")
})

test_that("extract_gazepoint_hrv_features can retain repeated IBI values", {
  dat <- data.frame(
    participant = "P1",
    IBI_clean_ms = c(
      1000, 1000, 1000,
      1020, 1020,
      980, 980,
      1010
    )
  )

  res <- extract_gazepoint_hrv_features(
    dat,
    ibi_col = "IBI_clean_ms",
    group_cols = "participant",
    min_intervals = 3,
    min_duration_s = 0,
    collapse_repeated_intervals = FALSE
  )

  expect_equal(res$features$input_interval_rows, 8)
  expect_equal(res$features$used_intervals_after_collapse, 8)
  expect_false(res$features$collapsed_repeated_intervals)
  expect_equal(res$features$n_intervals, 8)
  expect_equal(res$features$feature_status, "features_computed")
})

test_that("extract_gazepoint_hrv_features validates repeated interval options", {
  dat <- data.frame(
    participant = "P1",
    IBI_clean_ms = c(1000, 1010, 990)
  )

  expect_error(
    extract_gazepoint_hrv_features(
      dat,
      ibi_col = "IBI_clean_ms",
      collapse_repeated_intervals = NA
    ),
    "`collapse_repeated_intervals` must be TRUE or FALSE"
  )

  expect_error(
    extract_gazepoint_hrv_features(
      dat,
      ibi_col = "IBI_clean_ms",
      repeated_tolerance_ms = -1
    ),
    "`repeated_tolerance_ms` must be a single non-negative finite number"
  )
})

test_that("extract_gazepoint_hrv_features computes time-domain features", {
  dat <- data.frame(
    participant = "P1",
    IBI_clean_ms = c(1000, 1020, 980, 1010, 990)
  )

  res <- extract_gazepoint_hrv_features(
    dat,
    ibi_col = "IBI_clean_ms",
    group_cols = "participant",
    min_intervals = 3,
    min_duration_s = 0
  )

  expect_s3_class(res, "gazepoint_hrv_feature_extraction")
  expect_equal(res$overview$status, "hrv_features_computed")
  expect_equal(res$features$n_intervals, 5)
  expect_true(is.finite(res$features$sdnn_ms))
  expect_true(is.finite(res$features$rmssd_ms))
})

test_that("extract_gazepoint_hrv_features warns for short HRV duration", {
  dat <- data.frame(
    participant = "P1",
    IBI_clean_ms = c(1000, 1020, 980, 1010, 990)
  )

  res <- extract_gazepoint_hrv_features(
    dat,
    ibi_col = "IBI_clean_ms",
    group_cols = "participant",
    min_intervals = 3,
    min_duration_s = 30
  )

  expect_equal(res$overview$status, "warn_short_hrv_duration")
  expect_equal(res$overview$short_duration_groups, 1)
  expect_equal(res$features$feature_status, "warn_short_hrv_duration")
  expect_true(is.finite(res$features$rmssd_ms))
})

test_that("extract_gazepoint_hrv_features reports insufficient intervals", {
  dat <- data.frame(
    participant = "P1",
    IBI_clean_ms = c(1000, 1020)
  )

  res <- extract_gazepoint_hrv_features(
    dat,
    ibi_col = "IBI_clean_ms",
    group_cols = "participant",
    min_intervals = 3
  )

  expect_equal(res$overview$status, "fail_no_hrv_features_computed")
  expect_equal(res$features$feature_status, "insufficient_intervals")
})

test_that("extract_gazepoint_hrv_features works by group", {
  dat <- data.frame(
    participant = c(rep("P1", 4), rep("P2", 4)),
    IBI_clean_ms = c(1000, 1010, 990, 1005, 800, 810, 790, 805)
  )

  res <- extract_gazepoint_hrv_features(
    dat,
    ibi_col = "IBI_clean_ms",
    group_cols = "participant",
    min_intervals = 3,
    min_duration_s = 0
  )

  expect_equal(nrow(res$features), 2)
  expect_true(all(res$features$feature_status == "features_computed"))
})

test_that("IBI/HR/HRV helpers validate inputs", {
  dat <- data.frame(
    IBI = c(1000, 1010)
  )

  expect_error(
    filter_gazepoint_ibi_implausible(dat, ibi_col = "missing"),
    "`ibi_col`"
  )

  expect_error(
    compare_gazepoint_hr_ibi_consistency(dat),
    "`hr_col`"
  )

  expect_error(
    extract_gazepoint_hrv_features(dat, ibi_col = "missing"),
    "`ibi_col`"
  )

  expect_error(
    extract_gazepoint_hrv_features(
      dat,
      ibi_col = "IBI",
      min_duration_s = -1
    ),
    "`min_duration_s` must be a single non-negative finite number"
  )
})
