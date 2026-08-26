
test_that("downsample_gazepoint_data aggregates within groups", {
  demo <- data.frame(
    participant = rep(c("P01", "P02"), each = 10),
    time_ms = rep(0:9, 2),
    pupil = c(1:10, 11:20),
    gsr = c(21:30, 31:40)
  )

  out <- downsample_gazepoint_data(
    demo,
    time_col = "time_ms",
    signal_cols = c("pupil", "gsr"),
    group_cols = "participant",
    interval = 5,
    method = "mean"
  )

  expect_s3_class(out, "gazepoint_downsampled_data")
  expect_equal(nrow(out), 4)

  expect_equal(
    out$time_ms[out$participant == "P01"],
    c(0, 5)
  )

  expect_equal(
    out$time_ms[out$participant == "P02"],
    c(0, 5)
  )

  expect_equal(
    out$pupil[out$participant == "P01"],
    c(3, 8)
  )

  expect_equal(
    out$pupil[out$participant == "P02"],
    c(13, 18)
  )

  expect_equal(out$n_source_rows, rep(5L, 4))

  log <- attr(out, "downsample_log")
  settings <- attr(out, "downsample_settings")

  expect_true(is.data.frame(log))
  expect_equal(nrow(log), 2)
  expect_equal(log$n_input_rows, c(10, 10))
  expect_equal(log$n_output_rows, c(2, 2))
  expect_equal(log$mean_source_rows_per_bin, c(5, 5))

  expect_equal(settings$interval, 5)
  expect_equal(settings$method, "mean")
  expect_equal(settings$group_cols, "participant")
})

test_that("downsample_gazepoint_data supports centred bins and missing values", {
  demo <- data.frame(
    time_s = c(10, 11, 12, 13),
    pupil = c(1, NA, 3, 5)
  )

  out <- downsample_gazepoint_data(
    demo,
    time_col = "time_s",
    signal_cols = "pupil",
    interval = 2,
    method = "mean",
    na_rm = TRUE,
    time_value = "center",
    origin = 10
  )

  expect_equal(out$time_s, c(11, 13))
  expect_equal(out$pupil, c(1, 4))
  expect_equal(out$n_source_rows, c(2L, 2L))

  out_keep_na <- downsample_gazepoint_data(
    demo,
    time_col = "time_s",
    signal_cols = "pupil",
    interval = 2,
    method = "mean",
    na_rm = FALSE,
    origin = 10
  )

  expect_true(is.na(out_keep_na$pupil[1]))
  expect_equal(out_keep_na$pupil[2], 4)
})

test_that("downsample_gazepoint_data supports median, first, and last", {
  demo <- data.frame(
    time_s = 0:3,
    signal = c(1, 100, 3, 5)
  )

  median_out <- downsample_gazepoint_data(
    demo,
    time_col = "time_s",
    signal_cols = "signal",
    interval = 2,
    method = "median"
  )

  first_out <- downsample_gazepoint_data(
    demo,
    time_col = "time_s",
    signal_cols = "signal",
    interval = 2,
    method = "first"
  )

  last_out <- downsample_gazepoint_data(
    demo,
    time_col = "time_s",
    signal_cols = "signal",
    interval = 2,
    method = "last"
  )

  expect_equal(median_out$signal, c(50.5, 4))
  expect_equal(first_out$signal, c(1, 3))
  expect_equal(last_out$signal, c(100, 5))
})

test_that("downsample_gazepoint_data validates inputs", {
  demo <- data.frame(
    time_s = 0:3,
    signal = 1:4,
    label = letters[1:4]
  )

  expect_error(
    downsample_gazepoint_data(
      demo,
      time_col = "label",
      signal_cols = "signal",
      interval = 2
    ),
    "numeric"
  )

  expect_error(
    downsample_gazepoint_data(
      demo,
      time_col = "time_s",
      signal_cols = "label",
      interval = 2
    ),
    "numeric"
  )

  expect_error(
    downsample_gazepoint_data(
      demo,
      time_col = "time_s",
      signal_cols = "signal",
      interval = 0
    ),
    "positive"
  )

  expect_error(
    downsample_gazepoint_data(
      demo,
      time_col = "time_s",
      signal_cols = "time_s",
      interval = 2
    ),
    "must not include"
  )

  expect_error(
    downsample_gazepoint_data(
      demo,
      time_col = "time_s",
      signal_cols = "signal",
      group_cols = "time_s",
      interval = 2
    ),
    "must not include"
  )
})
