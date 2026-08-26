test_that("prepare_gazepoint_ledalab_input prepares grouped conductance tables", {
  dat <- data.frame(
    participant = rep(c("p1", "p2"), each = 20),
    CNT = rep(seq_len(20), times = 2),
    GSR_US = c(seq(1, 2, length.out = 20), seq(2, 3, length.out = 20))
  )

  out <- prepare_gazepoint_ledalab_input(
    dat,
    eda_col = "GSR_US",
    time_col = "CNT",
    group_cols = "participant",
    sampling_rate = 60
  )

  expect_s3_class(out, "gazepoint_ledalab_input")
  expect_s3_class(out, "gazepoint_external_eda_input")
  expect_equal(out$overview$status, "ledalab_input_prepared")
  expect_equal(out$overview$group_count, 2)
  expect_equal(out$overview$ready_group_count, 2)
  expect_true(is.data.frame(out$signal_table))
  expect_true(is.data.frame(out$group_summary))
  expect_true(all(c("time_s", "conductance_us", "group_id") %in% names(out$signal_table)))
  expect_true(all(is.finite(out$signal_table$time_s)))
  expect_equal(unique(out$signal_table$conductance_unit), "microsiemens")
})

test_that("prepare_gazepoint_pspm_input prepares sample-index-only data when no time column exists", {
  dat <- data.frame(
    participant = rep(c("p1", "p2"), each = 10),
    GSR_US = c(seq(1, 2, length.out = 10), seq(2, 3, length.out = 10))
  )

  out <- prepare_gazepoint_pspm_input(
    dat,
    eda_col = "GSR_US",
    group_cols = "participant",
    sampling_rate = 10
  )

  expect_s3_class(out, "gazepoint_pspm_input")
  expect_equal(out$overview$status, "pspm_input_prepared")
  expect_true(all(is.finite(out$signal_table$time_s)))
  expect_equal(unique(out$signal_table$detected_time_unit), "sample_index")
})

test_that("prepare_gazepoint_cvxeda_input adds y column for cvxEDA-style workflows", {
  dat <- data.frame(
    participant = "p1",
    time_s = seq(0, 1.9, by = 0.1),
    GSR_US = seq(1, 2, length.out = 20)
  )

  out <- prepare_gazepoint_cvxeda_input(
    dat,
    eda_col = "GSR_US",
    time_col = "time_s",
    group_cols = "participant"
  )

  expect_s3_class(out, "gazepoint_cvxeda_input")
  expect_equal(out$overview$status, "cvxeda_input_prepared")
  expect_true("y" %in% names(out$signal_table))
  expect_equal(out$signal_table$y, out$signal_table$conductance_us)
})

test_that("external EDA bridges can write optional CSV outputs", {
  dat <- data.frame(
    participant = "p1",
    CNT = seq_len(10),
    GSR_US = seq(1, 2, length.out = 10)
  )

  out_dir <- tempfile("eda_bridge_")

  out <- prepare_gazepoint_ledalab_input(
    dat,
    eda_col = "GSR_US",
    time_col = "CNT",
    group_cols = "participant",
    sampling_rate = 60,
    output_dir = out_dir,
    prefix = "test_bridge"
  )

  expect_equal(nrow(out$manifest), 2)
  expect_true(all(file.exists(out$manifest$path)))
})

test_that("external EDA bridges can conservatively convert verified resistance-like GSR", {
  dat <- data.frame(
    participant = "p1",
    CNT = seq_len(3),
    GSR = c(1000000, 500000, 250000)
  )

  out <- prepare_gazepoint_ledalab_input(
    dat,
    eda_col = "GSR",
    time_col = "CNT",
    group_cols = "participant",
    sampling_rate = 60,
    convert_resistance_to_us = TRUE
  )

  expect_equal(out$signal_table$conductance_us, c(1, 2, 4))
  expect_true(all(out$signal_table$used_resistance_conversion))
  expect_equal(
    unique(out$signal_table$conductance_unit),
    "microsiemens_converted_from_resistance"
  )
})

test_that("classify_gazepoint_eda_response_pattern gives descriptive labels only", {
  dat <- data.frame(
    participant = rep(c("none", "low", "moderate", "high"), each = 4),
    scr_amplitude_us = c(
      0, 0.002, 0.003, 0.004,
      0.02, 0.03, 0.04, 0.04,
      0.08, 0.10, 0.15, 0.18,
      0.25, 0.30, 0.40, 0.50
    )
  )

  out <- classify_gazepoint_eda_response_pattern(
    dat,
    response_col = "scr_amplitude_us",
    group_cols = "participant",
    summary_function = "max_abs",
    no_response_threshold = 0.01,
    low_response_threshold = 0.05,
    moderate_response_threshold = 0.20
  )

  expect_s3_class(out, "gazepoint_eda_response_pattern")
  expect_equal(out$overview$status, "eda_response_patterns_classified")

  patterns <- out$classifications$response_pattern
  names(patterns) <- out$classifications$participant

  expect_equal(patterns[["none"]], "no_detectable_response")
  expect_equal(patterns[["low"]], "low_response")
  expect_equal(patterns[["moderate"]], "moderate_response")
  expect_equal(patterns[["high"]], "high_response")

  expect_true(all(grepl("does not infer emotion", out$classifications$interpretation)))
})

test_that("classify_gazepoint_eda_response_pattern handles missing finite values conservatively", {
  dat <- data.frame(
    participant = "p1",
    scr_amplitude_us = c(NA_real_, NA_real_)
  )

  out <- classify_gazepoint_eda_response_pattern(
    dat,
    response_col = "scr_amplitude_us",
    group_cols = "participant"
  )

  expect_equal(out$overview$status, "eda_response_patterns_not_classified")
  expect_equal(out$classifications$response_pattern, "unclassified_no_finite_response")
  expect_equal(out$classifications$status, "fail_no_finite_response_values")
})

test_that("external EDA bridges error clearly when no EDA column is available", {
  dat <- data.frame(
    participant = "p1",
    CNT = seq_len(5),
    HR = 60 + seq_len(5)
  )

  expect_error(
    prepare_gazepoint_ledalab_input(dat, time_col = "CNT"),
    "No EDA/conductance column"
  )
})
