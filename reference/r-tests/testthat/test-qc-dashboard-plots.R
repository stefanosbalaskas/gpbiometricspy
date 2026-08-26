test_that("plot_gazepoint_signal_activity returns a contracted ggplot", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    participant = rep(c("p1", "p2"), each = 20),
    GSR_US = c(rep(0, 10), seq_len(10), rep(1, 20)),
    HR = c(60 + seq_len(20), rep(70, 20))
  )

  p <- plot_gazepoint_signal_activity(
    dat,
    signal_cols = c("GSR_US", "HR"),
    group_cols = "participant",
    metric = "nonzero_prop"
  )

  expect_s3_class(p, "gazepoint_plot")
  expect_true(isTRUE(attr(p, "gazepoint_plot_contract")))
  expect_equal(attr(p, "plot_type"), "signal_activity")
  expect_true(is.data.frame(attr(p, "plot_data")))
  expect_true(all(c("signal", ".plot_value", ".plot_group") %in% names(attr(p, "plot_data"))))
})

test_that("plot_gazepoint_signal_activity accepts an existing activity audit", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    participant = rep(c("p1", "p2"), each = 10),
    GSR_US = c(rep(0, 10), seq_len(10)),
    HR = 60 + seq_len(20)
  )

  audit <- audit_gazepoint_signal_activity(
    dat,
    signal_cols = c("GSR_US", "HR"),
    group_cols = "participant"
  )

  p <- plot_gazepoint_signal_activity(
    audit,
    metric = "active_signal"
  )

  expect_s3_class(p, "gazepoint_plot")
  expect_equal(attr(p, "plot_type"), "signal_activity")
})

test_that("plot_gazepoint_time_resets returns a contracted ggplot", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    participant = "p1",
    time_ms = c(1, 2, 3, 1, 2, 3),
    GSR_US = seq_len(6)
  )

  p <- plot_gazepoint_time_resets(
    dat,
    time_col = "time_ms",
    group_cols = "participant"
  )

  expect_s3_class(p, "gazepoint_plot")
  expect_true(isTRUE(attr(p, "gazepoint_plot_contract")))
  expect_equal(attr(p, "plot_type"), "time_resets")
  expect_true(is.data.frame(attr(p, "plot_data")))
  expect_true(any(attr(p, "plot_data")$.any_time_issue))
})

test_that("plot_gazepoint_time_resets accepts an existing time-reset audit", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    participant = "p1",
    time_ms = c(1, 2, 3, 4, 5),
    GSR_US = seq_len(5)
  )

  audit <- audit_gazepoint_time_resets(
    dat,
    time_col = "time_ms",
    group_cols = "participant"
  )

  p <- plot_gazepoint_time_resets(audit)

  expect_s3_class(p, "gazepoint_plot")
  expect_equal(attr(p, "plot_type"), "time_resets")
  expect_false(any(attr(p, "plot_data")$.any_time_issue))
})

test_that("plot_gazepoint_biometric_report_dashboard returns a lightweight dashboard", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    participant = rep(c("p1", "p2"), each = 20),
    time_ms = rep(seq_len(20), times = 2),
    GSR_US = c(rep(0, 10), seq_len(10), rep(1, 20)),
    HR = c(60 + seq_len(20), rep(70, 20))
  )

  dashboard <- plot_gazepoint_biometric_report_dashboard(
    data = dat,
    signal_cols = c("GSR_US", "HR"),
    group_cols = "participant",
    time_col = "time_ms"
  )

  expect_s3_class(dashboard, "gazepoint_biometric_plot_dashboard")
  expect_equal(dashboard$overview$status, "dashboard_created")
  expect_equal(dashboard$overview$plot_count, 2)
  expect_named(dashboard$plots, c("signal_activity", "time_resets"))
  expect_equal(nrow(dashboard$errors), 0)

  expect_true(all(vapply(
    dashboard$plots,
    function(x) isTRUE(attr(x, "gazepoint_plot_contract")),
    logical(1)
  )))
})

test_that("plot_gazepoint_biometric_report_dashboard can continue after plot errors", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    participant = "p1",
    time_ms = seq_len(10),
    GSR_US = seq_len(10)
  )

  dashboard <- plot_gazepoint_biometric_report_dashboard(
    data = dat,
    signal_cols = "missing_signal",
    group_cols = "participant",
    time_col = "time_ms",
    continue_on_error = TRUE
  )

  expect_s3_class(dashboard, "gazepoint_biometric_plot_dashboard")
  expect_equal(dashboard$overview$status, "partial_dashboard_created")
  expect_equal(dashboard$overview$plot_count, 1)
  expect_equal(dashboard$overview$error_count, 1)
  expect_true("time_resets" %in% names(dashboard$plots))
  expect_equal(dashboard$errors$plot, "signal_activity")
})
