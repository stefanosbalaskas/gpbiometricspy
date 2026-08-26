test_that("decompose_gazepoint_eda uses existing tonic and phasic columns", {
  df <- data.frame(
    CNT = 1:5,
    GSR_US = c(1, 1.1, 1.2, 1.1, 1),
    GSR_US_TONIC = c(1, 1, 1, 1, 1),
    GSR_US_PHASIC = c(0, 0.1, 0.2, 0.1, 0)
  )

  out <- decompose_gazepoint_eda(df, signal_col = "GSR_US")

  expect_s3_class(out, "data.frame")
  expect_true(all(c("eda_tonic", "eda_phasic", "eda_decomposition_method") %in% names(out)))
  expect_equal(out$eda_tonic, df$GSR_US_TONIC)
  expect_equal(out$eda_phasic, df$GSR_US_PHASIC)
  expect_equal(attr(out, "overview")$method, "existing_tonic_phasic_columns")
})


test_that("decompose_gazepoint_eda creates rolling median residual components", {
  df <- data.frame(
    CNT = 1:7,
    GSR_US = c(1, 1, 1, 2, 1, 1, 1)
  )

  out <- decompose_gazepoint_eda(
    df,
    signal_col = "GSR_US",
    time_col = "CNT",
    window_size = 3,
    output_prefix = "test_eda"
  )

  expect_true(all(c("test_eda_tonic", "test_eda_phasic") %in% names(out)))
  expect_equal(attr(out, "overview")$method, "rolling_median_residual")
  expect_equal(nrow(out), 7)
  expect_true(any(out$test_eda_phasic != 0, na.rm = TRUE))
})


test_that("decompose_gazepoint_eda supports grouping", {
  df <- data.frame(
    id = rep(c("P1", "P2"), each = 5),
    CNT = rep(1:5, 2),
    GSR_US = c(1, 1, 2, 1, 1, 2, 2, 3, 2, 2)
  )

  out <- decompose_gazepoint_eda(
    df,
    signal_col = "GSR_US",
    time_col = "CNT",
    group_cols = "id",
    window_size = 3
  )

  expect_equal(attr(out, "overview")$group_count, 2)
  expect_equal(nrow(out), nrow(df))
})


test_that("decompose_gazepoint_eda validates arguments", {
  df <- data.frame(GSR_US = c(1, 2, 3))

  expect_error(
    decompose_gazepoint_eda(1:3),
    "`data` must be"
  )

  expect_error(
    decompose_gazepoint_eda(df, signal_col = "missing"),
    "not found"
  )

  expect_error(
    decompose_gazepoint_eda(data.frame(GSR_US = letters[1:3]), signal_col = "GSR_US"),
    "`signal_col` must be numeric"
  )

  expect_error(
    decompose_gazepoint_eda(df, window_size = 0),
    "`window_size`"
  )

  expect_error(
    decompose_gazepoint_eda(df, output_prefix = ""),
    "`output_prefix`"
  )

  existing <- data.frame(
    GSR_US = c(1, 2, 3),
    eda_tonic = c(1, 1, 1)
  )

  expect_error(
    decompose_gazepoint_eda(existing, signal_col = "GSR_US"),
    "Output columns already exist"
  )
})


test_that("detect_gazepoint_scr_events detects SCR-like peaks from phasic column", {
  df <- data.frame(
    CNT = 1:20,
    GSR_US_PHASIC = c(
      rep(0, 5),
      0.2, 0.8, 0.2,
      rep(0, 4),
      0.3, 0.9, 0.2,
      rep(0, 5)
    )
  )

  out <- detect_gazepoint_scr_events(
    df,
    phasic_col = "GSR_US_PHASIC",
    time_col = "CNT",
    threshold = 0.5,
    min_peak_distance = 3
  )

  expect_s3_class(out, "gazepoint_scr_events")
  expect_equal(out$overview$n_events, 2)
  expect_equal(out$overview$status, "scr_events_detected")
  expect_true(all(out$events$peak_value >= 0.5))
})


test_that("detect_gazepoint_scr_events handles no events", {
  df <- data.frame(
    CNT = 1:10,
    GSR_US_PHASIC = rep(0, 10)
  )

  out <- detect_gazepoint_scr_events(
    df,
    phasic_col = "GSR_US_PHASIC",
    threshold = 0.5
  )

  expect_equal(out$overview$n_events, 0)
  expect_equal(out$overview$status, "no_scr_events_detected")
  expect_equal(nrow(out$events), 0)
})


test_that("detect_gazepoint_scr_events supports grouping", {
  df <- data.frame(
    id = rep(c("P1", "P2"), each = 10),
    CNT = rep(1:10, 2),
    GSR_US_PHASIC = c(
      0, 0, 0.8, 0, 0, 0, 0, 0, 0, 0,
      0, 0, 0, 0, 0, 0.9, 0, 0, 0, 0
    )
  )

  out <- detect_gazepoint_scr_events(
    df,
    phasic_col = "GSR_US_PHASIC",
    time_col = "CNT",
    group_cols = "id",
    threshold = 0.5,
    min_peak_distance = 3
  )

  expect_equal(out$overview$group_count, 2)
  expect_equal(out$overview$n_events, 2)
  expect_equal(nrow(out$group_summary), 2)
})


test_that("detect_gazepoint_scr_events can decompose when no phasic column is supplied", {
  df <- data.frame(
    CNT = 1:20,
    GSR_US = c(rep(1, 5), 1.2, 2, 1.2, rep(1, 12))
  )

  out <- detect_gazepoint_scr_events(
    df,
    signal_col = "GSR_US",
    time_col = "CNT",
    threshold = 0.3,
    min_peak_distance = 3,
    window_size = 3
  )

  expect_true(out$overview$decomposition_used)
  expect_s3_class(out$events, "data.frame")
})


test_that("detect_gazepoint_scr_events validates arguments", {
  df <- data.frame(GSR_US_PHASIC = c(0, 1, 0))

  expect_error(
    detect_gazepoint_scr_events(1:3),
    "`data` must be"
  )

  expect_error(
    detect_gazepoint_scr_events(df, phasic_col = "missing"),
    "not found"
  )

  expect_error(
    detect_gazepoint_scr_events(df, threshold = NA),
    "`threshold`"
  )

  expect_error(
    detect_gazepoint_scr_events(df, min_peak_distance = 0),
    "`min_peak_distance`"
  )

  expect_error(
    detect_gazepoint_scr_events(data.frame(GSR_US_PHASIC = letters[1:3]), phasic_col = "GSR_US_PHASIC"),
    "`phasic_col` must be numeric"
  )
})
