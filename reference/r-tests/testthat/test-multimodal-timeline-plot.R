test_that("plot_gazepoint_multimodal_timeline returns ggplot with inferred signals", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    participant = "P1",
    trial = 1,
    time_ms = seq(0, 900, by = 100),
    GSR_US = seq(1, 2, length.out = 10),
    HR = seq(70, 79),
    IBI = seq(850, 760, length.out = 10)
  )

  p <- plot_gazepoint_multimodal_timeline(
    dat,
    time_col = "time_ms",
    group_cols = c("participant", "trial")
  )

  expect_s3_class(p, "ggplot")
  plot_data <- attr(p, "plot_data")
  settings <- attr(p, "settings")

  expect_true(is.data.frame(plot_data))
  expect_equal(sort(unique(plot_data$.data_signal)), c("GSR_US", "HR", "IBI"))
  expect_equal(settings$time_col, "time_ms")
  expect_true(settings$standardise)
})

test_that("plot_gazepoint_multimodal_timeline supports event-relative time marker", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    event_relative_time_ms = seq(-200, 300, by = 100),
    GSR_US = seq(1, 1.5, length.out = 6),
    HR = seq(70, 75)
  )

  p <- plot_gazepoint_multimodal_timeline(dat)

  settings <- attr(p, "settings")

  expect_s3_class(p, "ggplot")
  expect_equal(settings$time_col, "event_relative_time_ms")
  expect_equal(settings$event_times, 0)
})

test_that("plot_gazepoint_multimodal_timeline supports explicit event column", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    time_ms = seq(0, 400, by = 100),
    marker = c(0, 1, 0, 0, 1),
    GSR_US = seq(1, 1.4, length.out = 5)
  )

  p <- plot_gazepoint_multimodal_timeline(
    dat,
    time_col = "time_ms",
    signal_cols = "GSR_US",
    event_col = "marker"
  )

  settings <- attr(p, "settings")

  expect_s3_class(p, "ggplot")
  expect_equal(settings$event_times, c(100, 400))
})

test_that("plot_gazepoint_multimodal_timeline errors when no signal is available", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    time_ms = 1:3,
    participant = "P1"
  )

  expect_error(
    plot_gazepoint_multimodal_timeline(dat),
    "No biometric signal columns"
  )
})
