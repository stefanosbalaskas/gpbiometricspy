test_that("run_gazepoint_scr_threshold_sensitivity creates full parameter grid", {
  dat <- data.frame(
    participant = "P1",
    CNT = seq_len(20),
    GSR_US_PHASIC = c(rep(0, 5), 0.02, 0.08, 0.02, rep(0, 12))
  )

  res <- run_gazepoint_scr_threshold_sensitivity(
    dat,
    phasic_col = "GSR_US_PHASIC",
    time_col = "CNT",
    group_cols = "participant",
    amplitude_min_values = c(0.01, 0.05),
    min_peak_distance_values = c(1, 5),
    include_event_windows = FALSE
  )

  expect_s3_class(res, "gazepoint_scr_threshold_sensitivity")
  expect_equal(res$overview$grid_rows, 4)
  expect_equal(nrow(res$sensitivity_grid), 4)
  expect_true(all(res$sensitivity_grid$status == "sensitivity_completed"))
})

test_that("run_gazepoint_scr_threshold_sensitivity shows stricter amplitude thresholds reduce detections", {
  dat <- data.frame(
    participant = "P1",
    CNT = seq_len(20),
    GSR_US_PHASIC = c(rep(0, 5), 0.02, 0.08, 0.02, rep(0, 12))
  )

  res <- run_gazepoint_scr_threshold_sensitivity(
    dat,
    phasic_col = "GSR_US_PHASIC",
    time_col = "CNT",
    group_cols = "participant",
    amplitude_min_values = c(0.01, 0.10),
    min_peak_distance_values = 1,
    include_event_windows = FALSE
  )

  low <- res$sensitivity_grid$detected_peaks[
    res$sensitivity_grid$amplitude_min == 0.01
  ]

  high <- res$sensitivity_grid$detected_peaks[
    res$sensitivity_grid$amplitude_min == 0.10
  ]

  expect_true(low > high)
})

test_that("run_gazepoint_scr_threshold_sensitivity can include event-window summaries", {
  dat <- data.frame(
    participant = "P1",
    CNT = seq_len(20),
    GSR_US_PHASIC = c(rep(0, 5), 0.02, 0.08, 0.02, rep(0, 12))
  )

  events <- data.frame(
    participant = "P1",
    event_time = 5
  )

  res <- run_gazepoint_scr_threshold_sensitivity(
    dat,
    phasic_col = "GSR_US_PHASIC",
    time_col = "CNT",
    group_cols = "participant",
    amplitude_min_values = c(0.01, 0.05),
    min_peak_distance_values = 1,
    events = events,
    event_time_col = "event_time",
    analysis_window = c(0, 6),
    response_window = c(1, 4),
    include_event_windows = TRUE
  )

  expect_equal(res$overview$grid_rows, 2)
  expect_true(all(res$sensitivity_grid$event_count == 1))
  expect_true(all(res$sensitivity_grid$response_events >= 0))
  expect_true(nrow(res$event_window_summary) >= 1)
})

test_that("run_gazepoint_scr_threshold_sensitivity supports collapsed TTL event windows", {
  dat <- data.frame(
    participant = "P1",
    CNT = seq_len(20),
    TTL0 = c(0, 1, 1, rep(0, 17)),
    TTL1 = c(0, 1, 1, rep(0, 17)),
    GSR_US_PHASIC = c(rep(0, 3), 0.02, 0.08, 0.02, rep(0, 14))
  )

  res <- run_gazepoint_scr_threshold_sensitivity(
    dat,
    phasic_col = "GSR_US_PHASIC",
    time_col = "CNT",
    group_cols = "participant",
    amplitude_min_values = 0.01,
    min_peak_distance_values = 1,
    ttl_cols = c("TTL0", "TTL1"),
    analysis_window = c(0, 6),
    response_window = c(1, 4),
    collapse_simultaneous_events = TRUE,
    include_event_windows = TRUE
  )

  expect_equal(res$sensitivity_grid$event_count, 1)
  expect_equal(res$sensitivity_grid$response_events, 1)
})

test_that("run_gazepoint_scr_threshold_sensitivity can retain objects", {
  dat <- data.frame(
    participant = "P1",
    CNT = seq_len(20),
    GSR_US_PHASIC = c(rep(0, 5), 0.02, 0.08, 0.02, rep(0, 12))
  )

  res <- run_gazepoint_scr_threshold_sensitivity(
    dat,
    phasic_col = "GSR_US_PHASIC",
    time_col = "CNT",
    group_cols = "participant",
    amplitude_min_values = 0.01,
    min_peak_distance_values = 1,
    include_event_windows = FALSE,
    keep_objects = TRUE
  )

  expect_true(is.list(res$objects))
  expect_equal(length(res$objects), 1)
  expect_s3_class(res$objects[[1]]$peaks, "gazepoint_scr_peak_detection")
})

test_that("run_gazepoint_scr_threshold_sensitivity validates inputs", {
  dat <- data.frame(
    CNT = seq_len(5),
    GSR_US_PHASIC = rep(0, 5)
  )

  expect_error(
    run_gazepoint_scr_threshold_sensitivity(
      dat,
      amplitude_min_values = -1
    ),
    "`amplitude_min_values`"
  )

  expect_error(
    run_gazepoint_scr_threshold_sensitivity(
      dat,
      min_peak_distance_values = 0
    ),
    "`min_peak_distance_values`"
  )
})
