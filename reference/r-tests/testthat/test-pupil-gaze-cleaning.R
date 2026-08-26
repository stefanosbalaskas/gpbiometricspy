
test_that("detect_gazepoint_pupil_blinks returns blink intervals", {
  dat <- data.frame(
    participant = "P01",
    time_s = 0:9,
    LPD = c(3, 3.1, NA, NA, 3.2, 3.1, 3.0, 0, 3.1, 3.2),
    RPD = c(3, 3.1, NA, NA, 3.2, 3.1, 3.0, 0, 3.1, 3.2)
  )

  blinks <- detect_gazepoint_pupil_blinks(
    dat,
    pupil_cols = c("LPD", "RPD"),
    time_col = "time_s"
  )

  expect_true(is.data.frame(blinks))
  expect_equal(nrow(blinks), 2)
  expect_equal(blinks$onset_time, c(2, 7))
  expect_equal(blinks$n_samples, c(2, 1))
})

test_that("detect_gazepoint_pupil_blinks supports onsets and flags", {
  dat <- data.frame(
    time_s = 1:5,
    LPD = c(3, NA, NA, 3.1, 3.2)
  )

  onsets <- detect_gazepoint_pupil_blinks(
    dat,
    pupil_cols = "LPD",
    time_col = "time_s",
    return = "onsets"
  )

  flags <- detect_gazepoint_pupil_blinks(
    dat,
    pupil_cols = "LPD",
    time_col = "time_s",
    return = "flags"
  )

  expect_equal(onsets, 2)
  expect_equal(flags, c(FALSE, TRUE, TRUE, FALSE, FALSE))
})

test_that("clean_gazepoint_pupil_signal interpolates blinks and spikes", {
  dat <- data.frame(
    time_s = 1:7,
    LPD = c(3.0, 3.1, NA, NA, 3.2, 30, 3.3)
  )

  out <- clean_gazepoint_pupil_signal(
    dat,
    pupil_cols = "LPD",
    time_col = "time_s",
    spike_mad = 3
  )

  expect_true("LPD_clean" %in% names(out))
  expect_true("LPD_was_blink" %in% names(out))
  expect_true("LPD_was_spike" %in% names(out))
  expect_true("LPD_was_pupil_imputed" %in% names(out))
  expect_false(anyNA(out$LPD_clean))
  expect_true(any(out$LPD_was_blink))
  expect_true(any(out$LPD_was_spike))

  summary <- attr(out, "pupil_cleaning_summary")
  expect_true(is.data.frame(summary))
  expect_equal(summary$column, "LPD")
})

test_that("clean_gazepoint_pupil_signal respects grouping", {
  dat <- data.frame(
    participant = c("P01", "P01", "P01", "P02", "P02", "P02"),
    time_s = c(1, 2, 3, 1, 2, 3),
    LPD = c(3, NA, 5, 10, NA, 14)
  )

  out <- clean_gazepoint_pupil_signal(
    dat,
    pupil_cols = "LPD",
    time_col = "time_s",
    group_cols = "participant"
  )

  expect_equal(out$LPD_clean, c(3, 4, 5, 10, 12, 14))
})

test_that("summarize_gazepoint_fixations computes trial and AOI metrics", {
  fix <- data.frame(
    participant = c("P01", "P01", "P01", "P01"),
    trial = c("T1", "T1", "T1", "T2"),
    AOI = c("A", "A", "B", "A"),
    FPOGD = c(0.2, 0.3, 0.4, 0.5),
    FPOGX = c(0.1, 0.2, 0.7, 0.3),
    FPOGY = c(0.2, 0.4, 0.8, 0.3)
  )

  out <- summarize_gazepoint_fixations(fix)

  expect_true(is.data.frame(out))
  expect_true(all(c("n_fixations", "mean_duration_s", "x_dispersion", "y_dispersion") %in% names(out)))
  expect_equal(nrow(out), 3)

  row_a <- out[out$trial == "T1" & out$AOI == "A", ]
  expect_equal(row_a$n_fixations, 2)
  expect_equal(row_a$total_duration_s, 0.5)
})

test_that("summarize_gazepoint_fixations handles millisecond durations", {
  fix <- data.frame(
    trial = "T1",
    AOI = "A",
    duration_ms = c(200, 300),
    x = c(10, 20),
    y = c(5, 15)
  )

  out <- summarize_gazepoint_fixations(
    fix,
    duration_col = "duration_ms",
    x_col = "x",
    y_col = "y",
    group_cols = c("trial", "AOI")
  )

  expect_equal(out$total_duration_s, 0.5)
  expect_equal(out$x_dispersion, 10)
  expect_equal(out$y_dispersion, 10)
})

test_that("filter_gazepoint_gaze flags samples outside screen bounds", {
  gaze <- data.frame(
    time_s = 1:5,
    BPOGX = c(0.1, 0.2, 1.5, 0.3, 0.4),
    BPOGY = c(0.1, 0.2, 0.3, -0.2, 0.4)
  )

  out <- filter_gazepoint_gaze(
    gaze,
    screen_bounds = c(0, 1, 0, 1)
  )

  expect_true("gaze_valid" %in% names(out))
  expect_equal(out$gaze_valid, c(TRUE, TRUE, FALSE, FALSE, TRUE))
  expect_true(is.na(out$BPOGX_filtered[3]))
  expect_true(is.na(out$BPOGY_filtered[4]))
})

test_that("filter_gazepoint_gaze flags high velocity samples", {
  gaze <- data.frame(
    participant = "P01",
    time_s = 1:4,
    BPOGX = c(0.1, 0.2, 0.95, 0.96),
    BPOGY = c(0.1, 0.2, 0.95, 0.96)
  )

  out <- filter_gazepoint_gaze(
    gaze,
    group_cols = "participant",
    screen_bounds = c(0, 1, 0, 1),
    max_velocity = 0.5
  )

  expect_true(out$gaze_valid[1])
  expect_true(out$gaze_valid[2])
  expect_false(out$gaze_valid[3])
  expect_equal(out$gaze_filter_reason[3], "high_velocity")
})

test_that("filter_gazepoint_gaze can drop invalid rows", {
  gaze <- data.frame(
    time_s = 1:3,
    BPOGX = c(0.1, 2, 0.3),
    BPOGY = c(0.1, 0.2, 0.3)
  )

  out <- filter_gazepoint_gaze(
    gaze,
    screen_bounds = c(0, 1, 0, 1),
    drop_invalid = TRUE
  )

  expect_equal(nrow(out), 2)
  expect_true(all(out$gaze_valid))
})

