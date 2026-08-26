test_that("prepare_gazepoint_scr_hurdle_model_data prepares response and amplitude datasets", {
  event_table <- data.frame(
    participant = c("P1", "P1", "P2", "P2"),
    condition = c("A", "B", "A", "B"),
    event_id = paste0("e", 1:4),
    response_flag = c(1, 0, 1, 0),
    scr_amplitude = c(0.05, NA, 0.08, NA),
    scr_latency = c(2, NA, 3, NA),
    scr_rise_time = c(1, NA, 1, NA),
    scr_recovery_time = c(4, NA, 5, NA)
  )

  res <- prepare_gazepoint_scr_hurdle_model_data(
    event_table,
    predictor_cols = "condition",
    factor_cols = c("participant", "condition"),
    group_cols = "participant"
  )

  expect_s3_class(res, "gazepoint_scr_hurdle_model_data")
  expect_equal(res$overview$status, "scr_hurdle_model_data_prepared")
  expect_equal(nrow(res$response_model_data), 4)
  expect_equal(nrow(res$amplitude_model_data), 2)
  expect_true(all(res$amplitude_model_data$scr_response_binary == 1))
  expect_true(is.factor(res$response_model_data$condition))
})

test_that("prepare_gazepoint_scr_hurdle_model_data accepts event-window summary objects", {
  events <- data.frame(
    participant = "P1",
    event_time = 10
  )

  peaks <- data.frame(
    participant = "P1",
    peak_id = 1,
    peak_time = 12,
    onset_time = 11,
    amplitude = 0.05,
    rise_time = 1,
    recovery_time_after_peak = 3,
    status = "detected"
  )

  windows <- summarise_gazepoint_scr_event_windows(
    scr_peaks = peaks,
    events = events,
    event_time_col = "event_time",
    group_cols = "participant",
    analysis_window = c(0, 6),
    response_window = c(1, 4)
  )

  res <- prepare_gazepoint_scr_hurdle_model_data(
    windows,
    group_cols = "participant"
  )

  expect_equal(res$overview$input_events, 1)
  expect_equal(res$overview$response_events, 1)
  expect_equal(nrow(res$amplitude_model_data), 1)
})

test_that("prepare_gazepoint_scr_hurdle_model_data applies log transforms", {
  event_table <- data.frame(
    event_id = paste0("e", 1:3),
    response_flag = c(1, 1, 0),
    scr_amplitude = c(0.05, 0.10, NA)
  )

  res <- prepare_gazepoint_scr_hurdle_model_data(
    event_table,
    amplitude_transform = "log",
    amplitude_offset = 1e-6
  )

  expect_equal(nrow(res$amplitude_model_data), 2)
  expect_equal(
    res$amplitude_model_data$scr_amplitude_model,
    log(res$amplitude_model_data$scr_amplitude_raw + 1e-6)
  )
})

test_that("prepare_gazepoint_scr_hurdle_model_data can keep rows with missing predictors when requested", {
  event_table <- data.frame(
    event_id = paste0("e", 1:3),
    condition = c("A", NA, "B"),
    response_flag = c(1, 0, 1),
    scr_amplitude = c(0.05, NA, 0.08)
  )

  res_drop <- prepare_gazepoint_scr_hurdle_model_data(
    event_table,
    predictor_cols = "condition",
    drop_missing_predictors = TRUE
  )

  res_keep <- prepare_gazepoint_scr_hurdle_model_data(
    event_table,
    predictor_cols = "condition",
    drop_missing_predictors = FALSE
  )

  expect_equal(nrow(res_drop$response_model_data), 2)
  expect_equal(nrow(res_keep$response_model_data), 3)
})

test_that("prepare_gazepoint_scr_hurdle_model_data creates model formula text", {
  event_table <- data.frame(
    participant = c("P1", "P2"),
    condition = c("A", "B"),
    event_id = c("e1", "e2"),
    response_flag = c(1, 0),
    scr_amplitude = c(0.05, NA)
  )

  res <- prepare_gazepoint_scr_hurdle_model_data(
    event_table,
    predictor_cols = "condition",
    group_cols = "participant"
  )

  expect_true(any(grepl("scr_response_binary ~ condition", res$model_formulas$formula)))
  expect_true(any(grepl("\\(1 \\| participant\\)", res$model_formulas$formula)))
})

test_that("prepare_gazepoint_scr_hurdle_model_data warns through status when no positive amplitudes exist", {
  event_table <- data.frame(
    event_id = paste0("e", 1:3),
    response_flag = c(0, 0, 0),
    scr_amplitude = c(NA, NA, NA)
  )

  res <- prepare_gazepoint_scr_hurdle_model_data(event_table)

  expect_equal(res$overview$status, "warn_no_positive_amplitude_rows")
  expect_equal(nrow(res$response_model_data), 3)
  expect_equal(nrow(res$amplitude_model_data), 0)
})

test_that("prepare_gazepoint_scr_hurdle_model_data validates required columns", {
  event_table <- data.frame(
    event_id = "e1",
    response_flag = 1
  )

  expect_error(
    prepare_gazepoint_scr_hurdle_model_data(event_table),
    "`amplitude_col` was not found"
  )
})

test_that("prepare_gazepoint_scr_hurdle_model_data validates requested predictors", {
  event_table <- data.frame(
    event_id = "e1",
    response_flag = 1,
    scr_amplitude = 0.05
  )

  expect_error(
    prepare_gazepoint_scr_hurdle_model_data(
      event_table,
      predictor_cols = "condition"
    ),
    "Requested columns were not found"
  )
})
