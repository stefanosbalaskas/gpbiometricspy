test_that("summarise_gazepoint_scr_event_windows links peaks to supplied events", {
  events <- data.frame(
    participant = "P1",
    event_time = 10,
    condition = "stimulus"
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

  res <- summarise_gazepoint_scr_event_windows(
    scr_peaks = peaks,
    events = events,
    event_time_col = "event_time",
    event_label_col = "condition",
    group_cols = "participant",
    analysis_window = c(0, 6),
    response_window = c(1, 4)
  )

  expect_s3_class(res, "gazepoint_scr_event_window_summary")
  expect_equal(res$overview$status, "scr_event_windows_summarised")
  expect_equal(res$event_table$response_flag, 1)
  expect_equal(res$event_table$scr_amplitude, 0.05)
  expect_equal(res$event_table$scr_latency, 2)
  expect_equal(res$event_table$event_label, "stimulus")
})

test_that("summarise_gazepoint_scr_event_windows returns no response when peak is outside response window", {
  events <- data.frame(
    participant = "P1",
    event_time = 10
  )

  peaks <- data.frame(
    participant = "P1",
    peak_id = 1,
    peak_time = 15,
    onset_time = 14,
    amplitude = 0.05,
    rise_time = 1,
    recovery_time_after_peak = 3,
    status = "detected"
  )

  res <- summarise_gazepoint_scr_event_windows(
    scr_peaks = peaks,
    events = events,
    event_time_col = "event_time",
    group_cols = "participant",
    analysis_window = c(0, 6),
    response_window = c(1, 4)
  )

  expect_equal(res$overview$status, "warn_no_scr_responses")
  expect_equal(res$event_table$response_flag, 0)
  expect_equal(res$event_table$n_candidate_peaks, 1)
  expect_equal(res$event_table$n_response_window_peaks, 0)
  expect_equal(res$event_table$event_status, "no_peaks_in_response_window")
})

test_that("summarise_gazepoint_scr_event_windows selects largest amplitude by default", {
  events <- data.frame(
    participant = "P1",
    event_time = 10
  )

  peaks <- data.frame(
    participant = "P1",
    peak_id = c(1, 2),
    peak_time = c(12, 13),
    onset_time = c(11, 12),
    amplitude = c(0.03, 0.08),
    rise_time = c(1, 1),
    recovery_time_after_peak = c(2, 2),
    status = c("detected", "detected")
  )

  res <- summarise_gazepoint_scr_event_windows(
    scr_peaks = peaks,
    events = events,
    event_time_col = "event_time",
    group_cols = "participant",
    analysis_window = c(0, 6),
    response_window = c(1, 4)
  )

  expect_equal(res$event_table$selected_peak_id, "2")
  expect_equal(res$event_table$scr_amplitude, 0.08)
})

test_that("summarise_gazepoint_scr_event_windows can select first peak", {
  events <- data.frame(
    participant = "P1",
    event_time = 10
  )

  peaks <- data.frame(
    participant = "P1",
    peak_id = c(1, 2),
    peak_time = c(12, 13),
    onset_time = c(11, 12),
    amplitude = c(0.03, 0.08),
    rise_time = c(1, 1),
    recovery_time_after_peak = c(2, 2),
    status = c("detected", "detected")
  )

  res <- summarise_gazepoint_scr_event_windows(
    scr_peaks = peaks,
    events = events,
    event_time_col = "event_time",
    group_cols = "participant",
    analysis_window = c(0, 6),
    response_window = c(1, 4),
    peak_selection = "first_peak"
  )

  expect_equal(res$event_table$selected_peak_id, "1")
  expect_equal(res$event_table$scr_amplitude, 0.03)
})

test_that("summarise_gazepoint_scr_event_windows respects group matching", {
  events <- data.frame(
    participant = c("P1", "P2"),
    event_time = c(10, 10)
  )

  peaks <- data.frame(
    participant = c("P1", "P2"),
    peak_id = c(1, 1),
    peak_time = c(12, 20),
    onset_time = c(11, 19),
    amplitude = c(0.05, 0.10),
    rise_time = c(1, 1),
    recovery_time_after_peak = c(2, 2),
    status = c("detected", "detected")
  )

  res <- summarise_gazepoint_scr_event_windows(
    scr_peaks = peaks,
    events = events,
    event_time_col = "event_time",
    group_cols = "participant",
    analysis_window = c(0, 6),
    response_window = c(1, 4)
  )

  expect_equal(res$overview$event_count, 2)
  expect_equal(res$overview$response_events, 1)
  expect_equal(res$event_table$response_flag[res$event_table$participant == "P1"], 1)
  expect_equal(res$event_table$response_flag[res$event_table$participant == "P2"], 0)
})

test_that("summarise_gazepoint_scr_event_windows accepts peak-detection objects", {
  dat <- data.frame(
    participant = "P1",
    CNT = seq_len(20),
    GSR_US_PHASIC = c(rep(0, 10), 0.02, 0.08, 0.02, rep(0, 7))
  )

  peaks <- detect_gazepoint_scr_peaks(
    dat,
    phasic_col = "GSR_US_PHASIC",
    time_col = "CNT",
    group_cols = "participant",
    amplitude_min = 0.03
  )

  events <- data.frame(
    participant = "P1",
    event_time = 10
  )

  res <- summarise_gazepoint_scr_event_windows(
    scr_peaks = peaks,
    events = events,
    event_time_col = "event_time",
    group_cols = "participant",
    analysis_window = c(0, 6),
    response_window = c(1, 4)
  )

  expect_equal(res$overview$response_events, 1)
  expect_true(res$event_table$scr_amplitude > 0)
})

test_that("summarise_gazepoint_scr_event_windows derives rising TTL events", {
  dat <- data.frame(
    participant = "P1",
    CNT = seq_len(10),
    TTL1 = c(0, 1, 1, 0, 0, 1, 0, 0, 0, 0)
  )

  peaks <- data.frame(
    participant = "P1",
    peak_id = c(1, 2),
    peak_time = c(4, 8),
    onset_time = c(3, 7),
    amplitude = c(0.05, 0.07),
    rise_time = c(1, 1),
    recovery_time_after_peak = c(2, 2),
    status = c("detected", "detected")
  )

  res <- summarise_gazepoint_scr_event_windows(
    data = dat,
    scr_peaks = peaks,
    time_col = "CNT",
    group_cols = "participant",
    ttl_cols = "TTL1",
    analysis_window = c(0, 4),
    response_window = c(1, 3)
  )

  expect_equal(res$overview$event_count, 2)
  expect_equal(res$overview$response_events, 2)
  expect_equal(res$events$event_time, c(2, 6))
})

test_that("summarise_gazepoint_scr_event_windows handles no TTL events", {
  dat <- data.frame(
    participant = "P1",
    CNT = seq_len(10),
    TTL1 = rep(0, 10)
  )

  peaks <- data.frame(
    participant = "P1",
    peak_id = 1,
    peak_time = 4,
    onset_time = 3,
    amplitude = 0.05,
    rise_time = 1,
    recovery_time_after_peak = 2,
    status = "detected"
  )

  res <- summarise_gazepoint_scr_event_windows(
    data = dat,
    scr_peaks = peaks,
    time_col = "CNT",
    group_cols = "participant",
    ttl_cols = "TTL1",
    analysis_window = c(0, 4),
    response_window = c(1, 3)
  )

  expect_equal(res$overview$status, "fail_no_events")
  expect_equal(nrow(res$event_table), 0)
})

test_that("summarise_gazepoint_scr_event_windows can collapse simultaneous TTL events", {
  dat <- data.frame(
    participant = "P1",
    CNT = seq_len(10),
    TTL0 = c(0, 1, 1, 0, 0, 1, 0, 0, 0, 0),
    TTL1 = c(0, 1, 1, 0, 0, 1, 0, 0, 0, 0)
  )

  peaks <- data.frame(
    participant = "P1",
    peak_id = c(1, 2),
    peak_time = c(4, 8),
    onset_time = c(3, 7),
    amplitude = c(0.05, 0.07),
    rise_time = c(1, 1),
    recovery_time_after_peak = c(2, 2),
    status = c("detected", "detected")
  )

  res_uncollapsed <- summarise_gazepoint_scr_event_windows(
    data = dat,
    scr_peaks = peaks,
    time_col = "CNT",
    group_cols = "participant",
    ttl_cols = c("TTL0", "TTL1"),
    analysis_window = c(0, 4),
    response_window = c(1, 3),
    collapse_simultaneous_events = FALSE
  )

  res_collapsed <- summarise_gazepoint_scr_event_windows(
    data = dat,
    scr_peaks = peaks,
    time_col = "CNT",
    group_cols = "participant",
    ttl_cols = c("TTL0", "TTL1"),
    analysis_window = c(0, 4),
    response_window = c(1, 3),
    collapse_simultaneous_events = TRUE
  )

  expect_equal(res_uncollapsed$overview$event_count, 4)
  expect_equal(res_collapsed$overview$event_count, 2)
  expect_equal(res_collapsed$overview$response_events, 2)
  expect_true(all(res_collapsed$events$collapsed_event_count == 2))
  expect_true(all(res_collapsed$events$event_label == "TTL0+TTL1"))
})

test_that("summarise_gazepoint_scr_event_windows validates nested windows", {
  events <- data.frame(
    event_time = 10
  )

  peaks <- data.frame(
    peak_id = 1,
    peak_time = 12,
    onset_time = 11,
    amplitude = 0.05,
    rise_time = 1,
    recovery_time_after_peak = 2,
    status = "detected"
  )

  expect_error(
    summarise_gazepoint_scr_event_windows(
      scr_peaks = peaks,
      events = events,
      event_time_col = "event_time",
      analysis_window = c(0, 4),
      response_window = c(-1, 5)
    ),
    "`response_window` must fall inside `analysis_window`"
  )
})

test_that("summarise_gazepoint_scr_event_windows validates collapse_simultaneous_events", {
  events <- data.frame(
    event_time = 10
  )

  peaks <- data.frame(
    peak_id = 1,
    peak_time = 12,
    amplitude = 0.05
  )

  expect_error(
    summarise_gazepoint_scr_event_windows(
      scr_peaks = peaks,
      events = events,
      event_time_col = "event_time",
      collapse_simultaneous_events = NA
    ),
    "`collapse_simultaneous_events` must be TRUE or FALSE"
  )
})
