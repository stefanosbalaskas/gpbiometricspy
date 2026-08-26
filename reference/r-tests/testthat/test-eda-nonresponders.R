test_that("screen_gazepoint_eda_nonresponders screens event-window data", {
  event_table <- data.frame(
    participant = c("P1", "P1", "P2", "P2"),
    response_flag = c(1, 0, 0, 0),
    scr_amplitude = c(0.05, NA, NA, NA)
  )

  res <- screen_gazepoint_eda_nonresponders(
    event_table,
    group_cols = "participant",
    min_events = 2,
    min_response_events = 1,
    min_response_rate = 0.1
  )

  expect_s3_class(res, "gazepoint_eda_nonresponder_screen")
  expect_equal(res$overview$group_count, 2)
  expect_equal(res$overview$candidate_nonresponder_count, 1)
  expect_equal(res$candidate_nonresponders$participant, "P2")
})

test_that("screen_gazepoint_eda_nonresponders accepts SCR event-window objects", {
  events <- data.frame(
    participant = c("P1", "P2"),
    event_time = c(10, 10)
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

  res <- screen_gazepoint_eda_nonresponders(
    windows,
    group_cols = "participant",
    min_events = 1,
    min_response_events = 1
  )

  expect_equal(res$overview$group_count, 2)
  expect_true("P2" %in% res$candidate_nonresponders$participant)
})

test_that("screen_gazepoint_eda_nonresponders can screen peak-only data", {
  peaks <- data.frame(
    participant = c("P1", "P1"),
    peak_time = c(10, 20),
    amplitude = c(0.05, 0.04),
    status = c("detected", "detected")
  )

  res <- screen_gazepoint_eda_nonresponders(
    peaks,
    group_cols = "participant",
    min_detected_peaks = 3
  )

  expect_equal(res$overview$candidate_nonresponder_count, 1)
  expect_equal(res$candidate_nonresponders$participant, "P1")
})

test_that("screen_gazepoint_eda_nonresponders validates thresholds", {
  dat <- data.frame(
    response_flag = 1,
    scr_amplitude = 0.05
  )

  expect_error(
    screen_gazepoint_eda_nonresponders(dat, min_response_rate = 2),
    "`min_response_rate`"
  )

  expect_error(
    screen_gazepoint_eda_nonresponders(dat, min_events = -1),
    "`min_events`"
  )
})
