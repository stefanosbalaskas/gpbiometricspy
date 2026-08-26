test_that("summarise_gazepoint_aoi_biometrics summarises signals by AOI", {
  dat <- data.frame(
    participant = c("P1", "P1", "P1", "P1", "P2", "P2"),
    MEDIA_ID = c(1, 1, 1, 1, 1, 1),
    AOI = c("claim", "claim", "logo", "logo", "claim", "logo"),
    GSR_US = c(1, 2, 3, 4, 5, 6),
    HR = c(70, 72, 74, 76, 78, 80)
  )

  res <- summarise_gazepoint_aoi_biometrics(
    dat,
    aoi_col = "AOI",
    signal_cols = c("GSR_US", "HR"),
    group_cols = c("participant", "MEDIA_ID"),
    min_rows = 1
  )

  expect_s3_class(res, "gazepoint_aoi_biometrics_summary")
  expect_equal(res$overview$signal_count, 2)
  expect_true(nrow(res$summary) > 0)
  expect_true(all(c("mean_value", "median_value", "signal", "aoi_label") %in% names(res$summary)))
})

test_that("summarise_gazepoint_aoi_biometrics can filter AOI labels", {
  dat <- data.frame(
    participant = "P1",
    AOI = c("claim", "claim", "logo"),
    GSR_US = c(1, 2, 3)
  )

  res <- summarise_gazepoint_aoi_biometrics(
    dat,
    aoi_col = "AOI",
    signal_cols = "GSR_US",
    group_cols = "participant",
    valid_aoi_values = "claim"
  )

  expect_equal(unique(res$summary$aoi_label), "claim")
  expect_equal(res$overview$aoi_count, 1)
})

test_that("summarise_gazepoint_aoi_biometrics warns for low-row summaries", {
  dat <- data.frame(
    participant = "P1",
    AOI = c("claim", "logo"),
    GSR_US = c(1, 2)
  )

  res <- summarise_gazepoint_aoi_biometrics(
    dat,
    aoi_col = "AOI",
    signal_cols = "GSR_US",
    group_cols = "participant",
    min_rows = 2
  )

  expect_equal(res$overview$status, "warn_low_rows_in_some_summaries")
  expect_true(any(res$summary$summary_status == "warn_low_rows"))
})

test_that("summarise_gazepoint_aoi_biometrics handles no retained AOI rows", {
  dat <- data.frame(
    participant = "P1",
    AOI = c(NA, ""),
    GSR_US = c(1, 2)
  )

  res <- summarise_gazepoint_aoi_biometrics(
    dat,
    aoi_col = "AOI",
    signal_cols = "GSR_US",
    group_cols = "participant"
  )

  expect_equal(res$overview$status, "fail_no_aoi_rows")
  expect_equal(nrow(res$summary), 0)
})

test_that("prepare_gazepoint_aoi_biometrics_model_data prepares model data", {
  dat <- data.frame(
    participant = c("P1", "P1", "P2", "P2"),
    AOI = c("claim", "logo", "claim", "logo"),
    GSR_US = c(1, 2, 3, 4)
  )

  summary <- summarise_gazepoint_aoi_biometrics(
    dat,
    aoi_col = "AOI",
    signal_cols = "GSR_US",
    group_cols = "participant"
  )

  model_data <- prepare_gazepoint_aoi_biometrics_model_data(
    summary,
    outcome_col = "mean_value",
    predictor_cols = c("aoi_label", "signal"),
    factor_cols = c("aoi_label", "signal"),
    group_cols = "participant",
    standardise_outcome = TRUE,
    standardise_within = "signal"
  )

  expect_s3_class(model_data, "gazepoint_aoi_biometrics_model_data")
  expect_equal(model_data$overview$status, "aoi_biometrics_model_data_prepared")
  expect_equal(model_data$overview$standardise_within, "signal")
  expect_true("mean_value_z" %in% names(model_data$model_data))
  expect_true(is.factor(model_data$model_data$aoi_label))
})

test_that("prepare_gazepoint_aoi_biometrics_model_data standardises within signal", {
  dat <- data.frame(
    participant = c("P1", "P1", "P2", "P2"),
    AOI = c("claim", "logo", "claim", "logo"),
    GSR_US = c(1, 2, 3, 4),
    HR = c(70, 72, 74, 76)
  )

  summary <- summarise_gazepoint_aoi_biometrics(
    dat,
    aoi_col = "AOI",
    signal_cols = c("GSR_US", "HR"),
    group_cols = "participant"
  )

  model_data <- prepare_gazepoint_aoi_biometrics_model_data(
    summary,
    outcome_col = "mean_value",
    predictor_cols = c("aoi_label", "signal"),
    factor_cols = c("aoi_label", "signal"),
    group_cols = "participant",
    standardise_outcome = TRUE,
    standardise_within = "signal"
  )

  by_signal_mean <- tapply(
    model_data$model_data$mean_value_z,
    model_data$model_data$signal,
    mean,
    na.rm = TRUE
  )

  expect_equal(model_data$overview$standardise_within, "signal")
  expect_true(all(abs(by_signal_mean) < 1e-10))
})

test_that("prepare_gazepoint_aoi_biometrics_model_data can standardise across all rows", {
  dat <- data.frame(
    participant = c("P1", "P1", "P2", "P2"),
    AOI = c("claim", "logo", "claim", "logo"),
    GSR_US = c(1, 2, 3, 4),
    HR = c(70, 72, 74, 76)
  )

  summary <- summarise_gazepoint_aoi_biometrics(
    dat,
    aoi_col = "AOI",
    signal_cols = c("GSR_US", "HR"),
    group_cols = "participant"
  )

  model_data <- prepare_gazepoint_aoi_biometrics_model_data(
    summary,
    outcome_col = "mean_value",
    predictor_cols = c("aoi_label", "signal"),
    factor_cols = c("aoi_label", "signal"),
    group_cols = "participant",
    standardise_outcome = TRUE,
    standardise_within = "all"
  )

  expect_equal(model_data$overview$standardise_within, "all")
  expect_true(abs(mean(model_data$model_data$mean_value_z, na.rm = TRUE)) < 1e-10)
})

test_that("prepare_gazepoint_aoi_biometrics_model_data can filter by min_rows", {
  dat <- data.frame(
    participant = "P1",
    AOI = c("claim", "claim", "logo"),
    GSR_US = c(1, 2, 3)
  )

  summary <- summarise_gazepoint_aoi_biometrics(
    dat,
    aoi_col = "AOI",
    signal_cols = "GSR_US",
    group_cols = "participant"
  )

  model_data <- prepare_gazepoint_aoi_biometrics_model_data(
    summary,
    outcome_col = "mean_value",
    predictor_cols = "aoi_label",
    min_rows = 2
  )

  expect_true(all(model_data$model_data$n_rows >= 2))
})

test_that("plot_gazepoint_aoi_biometrics returns ggplot objects", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    participant = c("P1", "P1", "P2", "P2"),
    AOI = c("claim", "logo", "claim", "logo"),
    GSR_US = c(1, 2, 3, 4),
    HR = c(70, 72, 74, 76)
  )

  summary <- summarise_gazepoint_aoi_biometrics(
    dat,
    aoi_col = "AOI",
    signal_cols = c("GSR_US", "HR"),
    group_cols = "participant"
  )

  p <- plot_gazepoint_aoi_biometrics(
    summary,
    value_col = "mean_value",
    plot_type = "point",
    group_col = "participant"
  )

  expect_s3_class(p, "ggplot")
  expect_true(is.data.frame(attr(p, "plot_data")))
})

test_that("plot_gazepoint_aoi_biometrics supports model-data objects", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    participant = c("P1", "P1", "P2", "P2"),
    AOI = c("claim", "logo", "claim", "logo"),
    GSR_US = c(1, 2, 3, 4)
  )

  summary <- summarise_gazepoint_aoi_biometrics(
    dat,
    aoi_col = "AOI",
    signal_cols = "GSR_US",
    group_cols = "participant"
  )

  model_data <- prepare_gazepoint_aoi_biometrics_model_data(
    summary,
    standardise_outcome = TRUE,
    standardise_within = "signal"
  )

  p <- plot_gazepoint_aoi_biometrics(
    model_data,
    value_col = "mean_value_z",
    plot_type = "boxplot"
  )

  expect_s3_class(p, "ggplot")
})

test_that("AOI-biometric helpers validate inputs", {
  dat <- data.frame(
    AOI = "claim",
    GSR_US = 1
  )

  expect_error(
    summarise_gazepoint_aoi_biometrics(dat, aoi_col = "missing"),
    "`aoi_col`"
  )

  expect_error(
    summarise_gazepoint_aoi_biometrics(dat, signal_cols = "missing"),
    "`signal_cols`"
  )

  expect_error(
    prepare_gazepoint_aoi_biometrics_model_data(dat, outcome_col = "missing"),
    "`outcome_col`"
  )

  expect_error(
    prepare_gazepoint_aoi_biometrics_model_data(
      data.frame(
        aoi_label = "claim",
        mean_value = 1
      ),
      outcome_col = "mean_value",
      standardise_outcome = TRUE,
      standardise_within = "signal"
    ),
    "`standardise_within = \"signal\"` requires a `signal` column"
  )

  testthat::skip_if_not_installed("ggplot2")
  expect_error(
    plot_gazepoint_aoi_biometrics(dat, value_col = "missing"),
    "Required plotting columns"
  )
})
