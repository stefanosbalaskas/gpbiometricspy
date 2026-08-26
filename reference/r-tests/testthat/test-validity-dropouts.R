test_that("summarise_gazepoint_biometric_validity detects active signals", {
  df <- data.frame(
    USER = rep(c("P1", "P2"), each = 4),
    GSR = c(1, 2, NA, 4, 2, 3, 4, 5),
    HR = c(70, 71, 72, NA, 80, 81, 82, 83),
    HRV = c(1, 1, 0, 1, 1, 1, 1, 1),
    ENGAGEMENT = c(50, 51, 52, 53, 50, 50, 50, 50)
  )

  out <- summarise_gazepoint_biometric_validity(df, group_cols = "USER")

  expect_type(out, "list")
  expect_s3_class(out$overview, "data.frame")
  expect_s3_class(out$signals, "data.frame")
  expect_s3_class(out$validity_flags, "data.frame")
  expect_s3_class(out$group_summary, "data.frame")

  expect_equal(out$overview$signal_column_count, 3)
  expect_equal(out$overview$validity_flag_column_count, 1)
  expect_true(out$overview$active_signal_count >= 2)
  expect_equal(out$overview$status, "biometric_signals_available")

  expect_true(all(c("GSR", "HR", "ENGAGEMENT") %in% out$signals$column))
  expect_true("HRV" %in% out$validity_flags$column)
})


test_that("summarise_gazepoint_biometric_validity treats HRV conservatively", {
  df <- data.frame(
    HR = c(70, 71, 72, 73),
    HRV = c(1, 1, 0, 1)
  )

  out <- summarise_gazepoint_biometric_validity(df)

  expect_equal(out$validity_flags$standard_name, "HRV")
  expect_match(out$validity_flags$interpretation_note, "validity/vendor flag")
  expect_true(any(grepl("Raw HRV columns", out$settings$notes)))
})


test_that("summarise_gazepoint_biometric_validity handles no detected signals", {
  df <- data.frame(
    USER = c("P1", "P2"),
    CONDITION = c("A", "B")
  )

  out <- summarise_gazepoint_biometric_validity(df)

  expect_equal(out$overview$signal_column_count, 0)
  expect_equal(out$overview$active_signal_count, 0)
  expect_equal(out$overview$status, "no_biometric_signal_columns_detected")
  expect_equal(nrow(out$signals), 0)
})


test_that("summarise_gazepoint_biometric_validity reports constant signals as limited", {
  df <- data.frame(
    GSR = c(1, 1, 1, 1),
    HR = c(70, 70, 70, 70)
  )

  out <- summarise_gazepoint_biometric_validity(df)

  expect_true(all(out$signals$status == "constant_or_low_variability_signal"))
  expect_equal(out$overview$status, "no_active_biometric_signals_detected")
})


test_that("summarise_gazepoint_biometric_validity can use explicit signal columns", {
  df <- data.frame(
    custom_signal = c(1, 2, 3, 4),
    validity_flag = c(1, 1, 0, 1)
  )

  out <- summarise_gazepoint_biometric_validity(
    df,
    signal_cols = "custom_signal",
    validity_cols = "validity_flag"
  )

  expect_equal(out$overview$signal_column_count, 1)
  expect_equal(out$overview$validity_flag_column_count, 1)
  expect_equal(out$signals$column, "custom_signal")
  expect_equal(out$validity_flags$column, "validity_flag")
})


test_that("summarise_gazepoint_biometric_validity validates arguments", {
  df <- data.frame(GSR = 1:3)

  expect_error(
    summarise_gazepoint_biometric_validity(1:3),
    "`data` must be"
  )

  expect_error(
    summarise_gazepoint_biometric_validity(df, signal_cols = "missing"),
    "not found"
  )

  expect_error(
    summarise_gazepoint_biometric_validity(df, active_min_unique = 0),
    "`active_min_unique`"
  )
})


test_that("flag_gazepoint_biometric_dropouts flags missing runs", {
  df <- data.frame(
    CNT = 1:8,
    GSR = c(1, NA, NA, NA, 2, 3, 4, 5),
    HR = c(70, 71, 72, 73, 74, 75, 76, 77)
  )

  out <- flag_gazepoint_biometric_dropouts(
    df,
    signal_cols = c("GSR", "HR"),
    min_missing_run = 3,
    min_flatline_run = 3
  )

  expect_true(all(out$biometric_dropout_GSR_missing[2:4]))
  expect_false(any(out$biometric_dropout_HR_missing))
  expect_true(all(out$biometric_dropout_any[2:4]))

  summary <- attr(out, "dropout_summary")
  expect_s3_class(summary, "data.frame")
  expect_equal(summary$n_missing_dropout[summary$column == "GSR"], 3)
})


test_that("flag_gazepoint_biometric_dropouts flags flatline runs", {
  df <- data.frame(
    CNT = 1:8,
    GSR = c(1, 2, 3, 4, 5, 6, 7, 8),
    HR = c(70, 70, 70, 71, 72, 72, 72, 72)
  )

  out <- flag_gazepoint_biometric_dropouts(
    df,
    signal_cols = c("GSR", "HR"),
    min_missing_run = 3,
    min_flatline_run = 3
  )

  expect_true(all(out$biometric_dropout_HR_flatline[1:3]))
  expect_true(all(out$biometric_dropout_HR_flatline[5:8]))
  expect_false(any(out$biometric_dropout_GSR_flatline))

  summary <- attr(out, "dropout_summary")
  expect_equal(summary$n_flatline_dropout[summary$column == "HR"], 7)
})


test_that("flag_gazepoint_biometric_dropouts respects grouping", {
  df <- data.frame(
    USER = rep(c("P1", "P2"), each = 3),
    CNT = c(1, 2, 3, 1, 2, 3),
    GSR = c(1, NA, NA, 2, NA, 3)
  )

  out <- flag_gazepoint_biometric_dropouts(
    df,
    signal_cols = "GSR",
    group_cols = "USER",
    min_missing_run = 2,
    min_flatline_run = 3
  )

  expect_true(all(out$biometric_dropout_GSR_missing[2:3]))
  expect_false(out$biometric_dropout_GSR_missing[5])
})


test_that("flag_gazepoint_biometric_dropouts can order within group by time", {
  df <- data.frame(
    USER = c("P1", "P1", "P1"),
    TIME = c(3, 1, 2),
    GSR = c(NA, 1, NA)
  )

  out <- flag_gazepoint_biometric_dropouts(
    df,
    signal_cols = "GSR",
    group_cols = "USER",
    time_col = "TIME",
    min_missing_run = 2,
    min_flatline_run = 3
  )

  expect_true(out$biometric_dropout_GSR_missing[1])
  expect_true(out$biometric_dropout_GSR_missing[3])
  expect_false(out$biometric_dropout_GSR_missing[2])
})


test_that("flag_gazepoint_biometric_dropouts handles no detected signals", {
  df <- data.frame(USER = c("P1", "P2"))

  out <- flag_gazepoint_biometric_dropouts(df)

  expect_true("biometric_dropout_any" %in% names(out))
  expect_false(any(out$biometric_dropout_any))
  expect_equal(nrow(attr(out, "dropout_summary")), 0)
})


test_that("flag_gazepoint_biometric_dropouts validates arguments", {
  df <- data.frame(GSR = 1:3)

  expect_error(
    flag_gazepoint_biometric_dropouts(1:3),
    "`data` must be"
  )

  expect_error(
    flag_gazepoint_biometric_dropouts(df, signal_cols = "missing"),
    "not found"
  )

  expect_error(
    flag_gazepoint_biometric_dropouts(df, min_missing_run = 0),
    "`min_missing_run`"
  )

  expect_error(
    flag_gazepoint_biometric_dropouts(df, min_flatline_run = 1.5),
    "`min_flatline_run`"
  )

  expect_error(
    flag_gazepoint_biometric_dropouts(df, constant_tolerance = -1),
    "`constant_tolerance`"
  )
})
