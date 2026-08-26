test_that("detect_gazepoint_nonwear flags missing, zero, constant, and low-variance runs", {
  demo <- data.frame(
    participant = rep(c("P01", "P02"), each = 20),
    trial = rep(rep(1:2, each = 10), times = 2),
    time_ms = rep(seq(0, 900, by = 100), times = 4),
    pupil = c(
      seq(3.0, 3.9, length.out = 10),
      rep(NA_real_, 10),
      rep(2.8, 10),
      seq(3.1, 3.5, length.out = 10)
    ),
    gsr = c(
      seq(0.70, 0.79, length.out = 10),
      rep(0, 10),
      seq(0.80, 0.89, length.out = 10),
      c(rep(0.75, 5), seq(0.76, 0.80, length.out = 5))
    )
  )

  out <- detect_gazepoint_nonwear(
    demo,
    signal_cols = c("pupil", "gsr"),
    group_cols = c("participant", "trial"),
    time_col = "time_ms",
    min_run_length = 5,
    low_variance_threshold = 0.0001
  )

  expect_s3_class(out, "gazepoint_nonwear_detection")
  expect_named(out, c("intervals", "summary", "parameters"))

  expect_true(all(c(
    "participant", "trial", "signal", "run_type", "start_row",
    "end_row", "n_samples", "start_time", "end_time"
  ) %in% names(out$intervals)))

  expect_true(all(c(
    "participant", "trial", "signal", "n_samples", "n_intervals",
    "n_flagged_samples", "prop_flagged_samples"
  ) %in% names(out$summary)))

  expect_equal(nrow(out$summary), 8)
  expect_true("missing_run" %in% out$intervals$run_type)
  expect_true("zero_run" %in% out$intervals$run_type)
  expect_true("constant_run" %in% out$intervals$run_type)
  expect_true("low_variance_run" %in% out$intervals$run_type)

  pupil_missing <- out$intervals[
    out$intervals$participant == "P01" &
      out$intervals$trial == 2 &
      out$intervals$signal == "pupil" &
      out$intervals$run_type == "missing_run",
  ]

  expect_equal(nrow(pupil_missing), 1)
  expect_equal(pupil_missing$n_samples, 10)
  expect_equal(pupil_missing$start_time, 0)
  expect_equal(pupil_missing$end_time, 900)
})

test_that("detect_gazepoint_nonwear handles no-interval cases", {
  demo <- data.frame(
    time_ms = seq(0, 900, by = 100),
    signal = seq(1, 2, length.out = 10)
  )

  out <- detect_gazepoint_nonwear(
    demo,
    signal_cols = "signal",
    time_col = "time_ms",
    min_run_length = 5
  )

  expect_s3_class(out, "gazepoint_nonwear_detection")
  expect_equal(nrow(out$intervals), 0)
  expect_equal(nrow(out$summary), 1)
  expect_equal(out$summary$n_intervals, 0)
  expect_equal(out$summary$n_flagged_samples, 0)
})

test_that("summarize_gazepoint_nonwear aggregates by signal", {
  demo <- data.frame(
    participant = rep(c("P01", "P02"), each = 20),
    trial = rep(rep(1:2, each = 10), times = 2),
    time_ms = rep(seq(0, 900, by = 100), times = 4),
    pupil = c(
      seq(3.0, 3.9, length.out = 10),
      rep(NA_real_, 10),
      rep(2.8, 10),
      seq(3.1, 3.5, length.out = 10)
    ),
    gsr = c(
      seq(0.70, 0.79, length.out = 10),
      rep(0, 10),
      seq(0.80, 0.89, length.out = 10),
      c(rep(0.75, 5), seq(0.76, 0.80, length.out = 5))
    )
  )

  out <- detect_gazepoint_nonwear(
    demo,
    signal_cols = c("pupil", "gsr"),
    group_cols = c("participant", "trial"),
    time_col = "time_ms",
    min_run_length = 5,
    low_variance_threshold = 0.0001
  )

  summary <- summarize_gazepoint_nonwear(out, by = "signal")

  expect_equal(sort(summary$signal), c("gsr", "pupil"))
  expect_equal(summary$n_samples_total[summary$signal == "pupil"], 40)
  expect_equal(summary$n_samples_total[summary$signal == "gsr"], 40)
  expect_equal(summary$n_flagged_samples_total[summary$signal == "pupil"], 20)
  expect_equal(summary$n_flagged_samples_total[summary$signal == "gsr"], 15)
})

test_that("filter_gazepoint_signal applies moving average within groups", {
  demo <- data.frame(
    participant = rep(c("P01", "P02"), each = 5),
    time_ms = rep(seq(0, 400, by = 100), 2),
    pupil = c(1, 2, 3, 4, 5, 10, 10, 10, 10, 10)
  )

  out <- filter_gazepoint_signal(
    demo,
    signal_cols = "pupil",
    method = "moving_average",
    group_cols = "participant",
    time_col = "time_ms",
    window = 3,
    na_rm = FALSE
  )

  expect_s3_class(out, "gazepoint_filtered_signal")
  expect_true("pupil_moving_average" %in% names(out))
  expect_equal(out$pupil_moving_average[1:5], c(1.5, 2, 3, 4, 4.5))
  expect_equal(out$pupil_moving_average[6:10], rep(10, 5))

  log <- attr(out, "filter_log")
  expect_true(is.data.frame(log))
  expect_equal(nrow(log), 2)
  expect_equal(unique(log$method), "moving_average")
})

test_that("filter_gazepoint_signal applies rolling median and detrend", {
  demo <- data.frame(
    participant = rep("P01", 5),
    time_ms = seq(0, 400, by = 100),
    signal = c(1, 100, 3, 4, 5)
  )

  med <- filter_gazepoint_signal(
    demo,
    signal_cols = "signal",
    method = "rolling_median",
    time_col = "time_ms",
    window = 3,
    na_rm = FALSE
  )

  expect_s3_class(med, "gazepoint_filtered_signal")
  expect_true("signal_rolling_median" %in% names(med))
  expect_equal(med$signal_rolling_median[2], 3)

  detrended <- filter_gazepoint_signal(
    demo,
    signal_cols = "signal",
    method = "detrend",
    time_col = "time_ms"
  )

  expect_s3_class(detrended, "gazepoint_filtered_signal")
  expect_true("signal_detrend" %in% names(detrended))
  expect_equal(length(detrended$signal_detrend), nrow(demo))
})

test_that("upsample_gazepoint_data regularizes irregular time series", {
  irregular <- data.frame(
    participant = c("P01", "P01", "P01", "P02", "P02", "P02"),
    time_ms = c(0, 110, 250, 0, 100, 310),
    pupil = c(3.0, 3.1, 3.3, 2.9, 3.0, 3.2),
    gsr = c(0.7, 0.72, 0.75, 0.8, 0.81, 0.84)
  )

  out <- upsample_gazepoint_data(
    irregular,
    time_col = "time_ms",
    signal_cols = c("pupil", "gsr"),
    group_cols = "participant",
    interval = 50
  )

  expect_s3_class(out, "gazepoint_upsampled_data")
  expect_equal(nrow(out), 13)
  expect_equal(out$time_ms[out$participant == "P01"], seq(0, 250, by = 50))
  expect_equal(out$time_ms[out$participant == "P02"], seq(0, 300, by = 50))
  expect_equal(out$pupil[1], 3.0)
  expect_equal(out$gsr[1], 0.7)

  log <- attr(out, "upsample_log")
  expect_true(is.data.frame(log))
  expect_equal(log$n_output_rows[log$participant == "P01"], 6)
  expect_equal(log$n_output_rows[log$participant == "P02"], 7)
})

test_that("signal dropout preprocessing validates inputs", {
  demo <- data.frame(
    time_ms = 1:5,
    signal = 1:5,
    label = letters[1:5]
  )

  expect_error(
    detect_gazepoint_nonwear(demo, signal_cols = "missing"),
    "not found"
  )

  expect_error(
    detect_gazepoint_nonwear(demo, signal_cols = "label"),
    "numeric"
  )

  expect_error(
    filter_gazepoint_signal(demo, signal_cols = "label"),
    "numeric"
  )

  expect_error(
    filter_gazepoint_signal(
      transform(demo, signal_moving_average = 0),
      signal_cols = "signal",
      method = "moving_average"
    ),
    "already exists"
  )

  expect_error(
    upsample_gazepoint_data(demo, time_col = "label", signal_cols = "signal"),
    "numeric"
  )

  expect_error(
    upsample_gazepoint_data(demo, time_col = "time_ms", signal_cols = "label"),
    "numeric"
  )
})
