test_that("plot_gazepoint_biometric_signals prepares signal plot data", {
  df <- data.frame(
    CNT = 1:5,
    GSR = c(1, 1.1, 1.2, 1.1, 1),
    HR = c(70, 71, 72, 71, 70)
  )

  out <- plot_gazepoint_biometric_signals(
    df,
    time_col = "CNT",
    plot = FALSE
  )

  expect_s3_class(out, "gazepoint_biometric_signal_plot")
  expect_s3_class(out$overview, "data.frame")
  expect_s3_class(out$plot_data, "data.frame")
  expect_s3_class(out$signal_summary, "data.frame")

  expect_equal(out$overview$n_rows, 5)
  expect_equal(out$overview$plotted_rows, 5)
  expect_equal(out$overview$signal_column_count, 2)
  expect_equal(out$settings$time_col, "CNT")
  expect_true(all(c("GSR", "HR") %in% names(out$plot_data)))
})


test_that("plot_gazepoint_biometric_signals supports explicit signal columns", {
  df <- data.frame(
    time = 1:4,
    custom_signal = c(1, 2, 3, 4)
  )

  out <- plot_gazepoint_biometric_signals(
    df,
    signal_cols = "custom_signal",
    time_col = "time",
    plot = FALSE
  )

  expect_equal(out$settings$signal_cols, "custom_signal")
  expect_equal(out$overview$signal_column_count, 1)
})


test_that("plot_gazepoint_biometric_signals downsamples large data for display", {
  df <- data.frame(
    CNT = 1:100,
    GSR = seq(1, 2, length.out = 100)
  )

  out <- plot_gazepoint_biometric_signals(
    df,
    time_col = "CNT",
    max_points = 10,
    plot = FALSE
  )

  expect_equal(out$overview$n_rows, 100)
  expect_true(out$overview$plotted_rows <= 10)
})


test_that("plot_gazepoint_biometric_signals can standardize signals", {
  df <- data.frame(
    CNT = 1:5,
    GSR = c(1, 2, 3, 4, 5)
  )

  out <- plot_gazepoint_biometric_signals(
    df,
    time_col = "CNT",
    standardize = TRUE,
    plot = FALSE
  )

  expect_equal(round(mean(out$plot_data$GSR), 10), 0)
  expect_equal(round(stats::sd(out$plot_data$GSR), 10), 1)
})


test_that("plot_gazepoint_biometric_signals can draw without error", {
  df <- data.frame(
    CNT = 1:5,
    GSR = c(1, 1.1, 1.2, 1.1, 1),
    HR = c(70, 71, 72, 71, 70)
  )

  path <- tempfile(fileext = ".png")
  grDevices::png(path)
  expect_silent(
    plot_gazepoint_biometric_signals(
      df,
      time_col = "CNT",
      plot = TRUE
    )
  )
  grDevices::dev.off()

  expect_true(file.exists(path))
})


test_that("plot_gazepoint_biometric_signals validates arguments", {
  df <- data.frame(GSR = c(1, 2, 3))

  expect_error(
    plot_gazepoint_biometric_signals(1:3),
    "`data` must be"
  )

  expect_error(
    plot_gazepoint_biometric_signals(df, signal_cols = "missing"),
    "not found"
  )

  expect_error(
    plot_gazepoint_biometric_signals(df, time_col = "missing"),
    "not found"
  )

  expect_error(
    plot_gazepoint_biometric_signals(df, max_points = 0),
    "`max_points`"
  )

  expect_error(
    plot_gazepoint_biometric_signals(df, standardize = NA),
    "`standardize`"
  )

  expect_error(
    plot_gazepoint_biometric_signals(df, plot = NA),
    "`plot`"
  )

  expect_error(
    plot_gazepoint_biometric_signals(data.frame(label = letters[1:3])),
    "No biometric signal"
  )

  expect_error(
    plot_gazepoint_biometric_signals(
      data.frame(GSR = letters[1:3]),
      signal_cols = "GSR"
    ),
    "must be numeric"
  )
})


test_that("plot_gazepoint_biometric_quality summarises explicit quality columns", {
  df <- data.frame(
    CNT = 1:5,
    HR_valid = c(1, 1, 0, 1, 0),
    biometric_dropout_any = c(FALSE, TRUE, FALSE, FALSE, TRUE)
  )

  out <- plot_gazepoint_biometric_quality(
    df,
    quality_cols = c("HR_valid", "biometric_dropout_any"),
    plot = FALSE
  )

  expect_s3_class(out, "gazepoint_biometric_quality_plot")
  expect_s3_class(out$overview, "data.frame")
  expect_s3_class(out$quality_summary, "data.frame")
  expect_s3_class(out$plot_data, "data.frame")

  expect_equal(out$overview$quality_column_count, 2)
  expect_equal(out$overview$status, "quality_flags_present")
  expect_equal(out$quality_summary$n_flagged[out$quality_summary$column == "HR_valid"], 2)
  expect_equal(out$quality_summary$n_flagged[out$quality_summary$column == "biometric_dropout_any"], 2)
})


test_that("plot_gazepoint_biometric_quality can derive missingness from signals", {
  df <- data.frame(
    CNT = 1:5,
    GSR = c(1, NA, 1.2, 1.1, NA)
  )

  out <- plot_gazepoint_biometric_quality(
    df,
    signal_cols = "GSR",
    plot = FALSE
  )

  expect_true(out$overview$derived_from_signals)
  expect_equal(out$quality_summary$n_flagged, 2)
  expect_equal(out$quality_summary$source, "derived_signal_missingness")
})


test_that("plot_gazepoint_biometric_quality supports group summaries", {
  df <- data.frame(
    USER = rep(c("P1", "P2"), each = 3),
    GSR_missing = c(FALSE, TRUE, FALSE, TRUE, TRUE, FALSE)
  )

  out <- plot_gazepoint_biometric_quality(
    df,
    quality_cols = "GSR_missing",
    group_col = "USER",
    plot = FALSE
  )

  expect_equal(nrow(out$group_summary), 2)
  expect_true(all(out$group_summary$group %in% c("P1", "P2")))
  expect_equal(out$overview$group_count, 2)
})


test_that("plot_gazepoint_biometric_quality can draw without error", {
  df <- data.frame(
    CNT = 1:5,
    HR_valid = c(1, 1, 0, 1, 0)
  )

  path <- tempfile(fileext = ".png")
  grDevices::png(path)
  expect_silent(
    plot_gazepoint_biometric_quality(
      df,
      quality_cols = "HR_valid",
      plot = TRUE
    )
  )
  grDevices::dev.off()

  expect_true(file.exists(path))
})


test_that("plot_gazepoint_biometric_quality validates arguments", {
  df <- data.frame(GSR = c(1, 2, 3))

  expect_error(
    plot_gazepoint_biometric_quality(1:3),
    "`data` must be"
  )

  expect_error(
    plot_gazepoint_biometric_quality(df, quality_cols = "missing"),
    "not found"
  )

  expect_error(
    plot_gazepoint_biometric_quality(df, signal_cols = "missing"),
    "not found"
  )

  expect_error(
    plot_gazepoint_biometric_quality(df, group_col = "missing"),
    "not found"
  )

  expect_error(
    plot_gazepoint_biometric_quality(df, dropout_prefix = ""),
    "`dropout_prefix`"
  )

  expect_error(
    plot_gazepoint_biometric_quality(df, max_points = 0),
    "`max_points`"
  )

  expect_error(
    plot_gazepoint_biometric_quality(df, plot = NA),
    "`plot`"
  )

  expect_error(
    plot_gazepoint_biometric_quality(data.frame(label = letters[1:3])),
    "No quality columns or signal columns"
  )
})
