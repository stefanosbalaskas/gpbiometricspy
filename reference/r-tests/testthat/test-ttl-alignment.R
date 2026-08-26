test_that("align_gazepoint_biometrics_to_ttl detects standardized TTL rising edges", {
  dat <- data.frame(
    participant = "P1",
    trial = 1,
    time_ms = seq(0, 900, by = 100),
    ttl_marker = c(0, 0, 1, 1, 0, 0, 1, 0, 0, 0),
    ttl_validity_flag = 1,
    GSR_US = seq(1, 2, length.out = 10)
  )

  res <- align_gazepoint_biometrics_to_ttl(
    dat,
    time_col = "time_ms",
    group_cols = c("participant", "trial"),
    pre_window_ms = 100,
    post_window_ms = 200
  )

  expect_s3_class(res, "gazepoint_biometrics_ttl_alignment")
  expect_equal(res$overview$status, "ttl_events_aligned")
  expect_equal(nrow(res$events), 2)
  expect_equal(unique(res$aligned_data$ttl_event_id), c("ttl_event_1", "ttl_event_2"))
  expect_true(0 %in% res$aligned_data$event_relative_sample_index)
  expect_true("pre_event" %in% res$aligned_data$event_window_position)
  expect_true("event" %in% res$aligned_data$event_window_position)
  expect_true("post_event" %in% res$aligned_data$event_window_position)
})

test_that("align_gazepoint_biometrics_to_ttl detects raw TTL0-TTL6 columns", {
  dat <- data.frame(
    subject = "S1",
    MEDIA_ID = "M1",
    time_ms = seq(0, 900, by = 100),
    TTL0 = c(0, 0, 1, 1, 0, 0, 0, 0, 0, 0),
    TTL1 = c(0, 0, 0, 0, 0, 0, 1, 0, 0, 0),
    TTLV = 1,
    HR = seq(70, 79)
  )

  res <- align_gazepoint_biometrics_to_ttl(
    dat,
    time_col = "time_ms",
    pre_window_ms = 100,
    post_window_ms = 100
  )

  expect_equal(nrow(res$events), 2)
  expect_true("TTL0" %in% res$events$event_ttl_column)
  expect_true("TTL1" %in% res$events$event_ttl_column)
  expect_equal(res$settings$ttl_valid_col, "TTLV")
})

test_that("align_gazepoint_biometrics_to_ttl supports a user-specified event column", {
  dat <- data.frame(
    participant = rep(c("P1", "P2"), each = 5),
    trial = rep(1, 10),
    time_ms = rep(seq(0, 400, by = 100), 2),
    marker = c(0, "start", 0, 0, 0, 0, "start", 0, 0, 0),
    GSR_US = seq(1, 2, length.out = 10)
  )

  res <- align_gazepoint_biometrics_to_ttl(
    dat,
    event_col = "marker",
    event_value = "start",
    time_col = "time_ms",
    group_cols = c("participant", "trial"),
    pre_window_ms = 100,
    post_window_ms = 100
  )

  expect_equal(nrow(res$events), 2)
  expect_equal(sort(unique(res$events$participant)), c("P1", "P2"))
  expect_equal(res$settings$event_source, "user_event_col")
})

test_that("align_gazepoint_biometrics_to_ttl uses TTL validity conservatively", {
  dat <- data.frame(
    time_ms = seq(0, 400, by = 100),
    TTL0 = c(0, 1, 0, 0, 0),
    TTLV = c(1, 0, 1, 1, 1),
    GSR_US = seq(1, 1.4, length.out = 5)
  )

  res <- align_gazepoint_biometrics_to_ttl(
    dat,
    time_col = "time_ms",
    pre_window_ms = 100,
    post_window_ms = 100
  )

  expect_equal(res$overview$status, "no_ttl_events_detected")
  expect_equal(nrow(res$events), 0)
  expect_equal(nrow(res$aligned_data), 0)
})

test_that("align_gazepoint_biometrics_to_ttl falls back to sample windows without time", {
  dat <- data.frame(
    participant = "P1",
    marker = c(0, 1, 0, 0, 0),
    HR = c(70, 72, 73, 74, 75)
  )

  res <- align_gazepoint_biometrics_to_ttl(
    dat,
    event_col = "marker",
    group_cols = "participant",
    pre_window_samples = 1,
    post_window_samples = 1
  )

  expect_equal(nrow(res$events), 1)
  expect_equal(
    res$aligned_data$event_relative_sample_index,
    c(-1, 0, 1)
  )
  expect_true(all(is.na(res$aligned_data$event_relative_time_ms)))
})
