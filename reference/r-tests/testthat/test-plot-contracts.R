test_that("standardise_gazepoint_plot_contract adds plot attributes", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    x = 1:3,
    y = c(2, 3, 4)
  )

  p <- ggplot2::ggplot(dat, ggplot2::aes(x = x, y = y)) +
    ggplot2::geom_point()

  p2 <- standardise_gazepoint_plot_contract(
    plot = p,
    plot_data = dat,
    settings = list(plot_type = "point", x = "x", y = "y"),
    interpretation_notes = "Test plot contract.",
    plot_type = "point"
  )

  expect_s3_class(p2, "gazepoint_plot")
  expect_s3_class(p2, "ggplot")
  expect_true(isTRUE(attr(p2, "gazepoint_plot_contract")))
  expect_true(is.data.frame(attr(p2, "plot_data")))
  expect_true(is.list(attr(p2, "settings")))
  expect_equal(attr(p2, "plot_type"), "point")
  expect_equal(attr(p2, "interpretation_notes"), "Test plot contract.")
})

test_that("check_gazepoint_plot_contract detects complete contracts", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    x = 1:3,
    y = c(2, 3, 4)
  )

  p <- ggplot2::ggplot(dat, ggplot2::aes(x = x, y = y)) +
    ggplot2::geom_point()

  p <- standardise_gazepoint_plot_contract(
    plot = p,
    plot_data = dat,
    settings = list(plot_type = "point"),
    interpretation_notes = "Complete contract.",
    plot_type = "point"
  )

  check <- check_gazepoint_plot_contract(p)

  expect_s3_class(check, "gazepoint_plot_contract_check")
  expect_equal(check$overview$status, "pass_plot_contract")
  expect_true(check$overview$is_ggplot)
  expect_true(check$overview$has_plot_data)
  expect_equal(check$overview$plot_data_rows, 3)
})

test_that("check_gazepoint_plot_contract can warn for partial contracts", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    x = 1:3,
    y = c(2, 3, 4)
  )

  p <- ggplot2::ggplot(dat, ggplot2::aes(x = x, y = y)) +
    ggplot2::geom_point()

  check <- check_gazepoint_plot_contract(
    p,
    require_plot_data = FALSE,
    require_settings = FALSE
  )

  expect_equal(check$overview$status, "warn_partial_plot_contract")
  expect_true(check$overview$is_ggplot)
})

test_that("check_gazepoint_plot_contract fails when required data are missing", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    x = 1:3,
    y = c(2, 3, 4)
  )

  p <- ggplot2::ggplot(dat, ggplot2::aes(x = x, y = y)) +
    ggplot2::geom_point()

  check <- check_gazepoint_plot_contract(p)

  expect_equal(check$overview$status, "fail_plot_contract")
  expect_false(check$overview$has_plot_data)
})

test_that("get_gazepoint_plot_data and settings extract stored attributes", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    x = 1:3,
    y = c(2, 3, 4)
  )

  p <- ggplot2::ggplot(dat, ggplot2::aes(x = x, y = y)) +
    ggplot2::geom_point()

  p <- standardise_gazepoint_plot_contract(
    plot = p,
    plot_data = dat,
    settings = list(plot_type = "point"),
    interpretation_notes = "Stored plot.",
    plot_type = "point"
  )

  expect_equal(get_gazepoint_plot_data(p), dat)
  expect_equal(get_gazepoint_plot_settings(p)$plot_type, "point")
})

test_that("plot-contract helpers validate inputs", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    x = 1:3,
    y = c(2, 3, 4)
  )

  p <- ggplot2::ggplot(dat, ggplot2::aes(x = x, y = y)) +
    ggplot2::geom_point()

  expect_error(
    standardise_gazepoint_plot_contract("not a plot"),
    "`plot` must be a ggplot object"
  )

  expect_error(
    standardise_gazepoint_plot_contract(p, plot_data = list()),
    "`plot_data` must be NULL or a data frame"
  )

  expect_error(
    check_gazepoint_plot_contract(p, require_plot_data = NA),
    "`require_plot_data` must be TRUE or FALSE"
  )

  expect_error(
    get_gazepoint_plot_data(p),
    "No `plot_data` data frame"
  )

  expect_error(
    get_gazepoint_plot_settings(p),
    "No `settings` list"
  )
})

test_that("plot_gazepoint_aoi_biometrics follows the plot contract", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    participant = c("P1", "P1", "P2", "P2"),
    AOI = c("claim", "logo", "claim", "logo"),
    GSR_US = c(1, 2, 3, 4),
    HR = c(70, 72, 74, 76)
  )

  summary <- summarise_gazepoint_aoi_biometrics(
    dat,
    aoi_col = "AOI",
    signal_cols = c("GSR_US", "HR"),
    group_cols = "participant"
  )

  p <- plot_gazepoint_aoi_biometrics(
    summary,
    value_col = "mean_value",
    plot_type = "point",
    group_col = "participant"
  )

  check <- check_gazepoint_plot_contract(p)

  expect_s3_class(p, "gazepoint_plot")
  expect_equal(check$overview$status, "pass_plot_contract")
  expect_true(is.data.frame(get_gazepoint_plot_data(p)))
  expect_true(is.list(get_gazepoint_plot_settings(p)))
})

test_that("plot_gazepoint_eda_decomposition follows the plot contract", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    participant = rep("P1", 10),
    CNT = 0:9,
    GSR_US = seq(1, 2, length.out = 10),
    GSR_US_TONIC = seq(0.9, 1.8, length.out = 10),
    GSR_US_PHASIC = c(0, 0.01, 0.02, 0.01, 0, 0.03, 0.04, 0.02, 0.01, 0)
  )

  p <- plot_gazepoint_eda_decomposition(
    data = dat,
    time_col = "CNT",
    signal_cols = c("GSR_US", "GSR_US_TONIC", "GSR_US_PHASIC"),
    group_cols = "participant",
    standardise = TRUE,
    max_points = 100,
    title = "EDA decomposition test"
  )

  check <- check_gazepoint_plot_contract(p)

  expect_s3_class(p, "gazepoint_plot")
  expect_equal(check$overview$status, "pass_plot_contract")
  expect_true(is.data.frame(get_gazepoint_plot_data(p)))
  expect_equal(attr(p, "plot_type"), "eda_decomposition")
})

test_that("plot_gazepoint_eda_decomposition follows the plot contract", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    participant = rep("P1", 10),
    CNT = 0:9,
    GSR_US = seq(1, 2, length.out = 10),
    GSR_US_TONIC = seq(0.9, 1.8, length.out = 10),
    GSR_US_PHASIC = c(0, 0.01, 0.02, 0.01, 0, 0.03, 0.04, 0.02, 0.01, 0)
  )

  p <- plot_gazepoint_eda_decomposition(
    data = dat,
    time_col = "CNT",
    signal_cols = c("GSR_US", "GSR_US_TONIC", "GSR_US_PHASIC"),
    group_cols = "participant",
    standardise = TRUE,
    max_points = 100,
    title = "EDA decomposition test"
  )

  check <- check_gazepoint_plot_contract(p)

  expect_s3_class(p, "gazepoint_plot")
  expect_equal(check$overview$status, "pass_plot_contract")
  expect_true(is.data.frame(get_gazepoint_plot_data(p)))
  expect_true(is.list(get_gazepoint_plot_settings(p)))
  expect_equal(attr(p, "plot_type"), "eda_decomposition")
})

test_that("plot_gazepoint_scr_events follows the plot contract", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    participant = rep("P1", 20),
    CNT = 0:19,
    GSR_US = c(
      1.00, 1.01, 1.03, 1.08, 1.05,
      1.02, 1.01, 1.00, 1.02, 1.04,
      1.10, 1.08, 1.04, 1.02, 1.01,
      1.00, 1.01, 1.02, 1.01, 1.00
    )
  )

  peaks <- data.frame(
    participant = "P1",
    peak_time = c(3, 10),
    peak_amplitude = c(0.08, 0.10)
  )

  p <- plot_gazepoint_scr_events(
    data = dat,
    scr_peaks = peaks,
    time_col = "CNT",
    signal_col = "GSR_US",
    group_cols = "participant",
    max_points = 100,
    title = "SCR events test"
  )

  check <- check_gazepoint_plot_contract(p)

  expect_s3_class(p, "gazepoint_plot")
  expect_equal(check$overview$status, "pass_plot_contract")
  expect_true(is.data.frame(get_gazepoint_plot_data(p)))
  expect_true(is.list(get_gazepoint_plot_settings(p)))
  expect_equal(attr(p, "plot_type"), "scr_events")
  expect_true(is.data.frame(attr(p, "peak_data")))
  expect_true(is.data.frame(attr(p, "event_data")))
})

test_that("plot_gazepoint_multimodal_timeline follows the plot contract", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(
    participant = rep("P1", 10),
    MEDIA_ID = rep(1, 10),
    CNT = 0:9,
    GSR_US = seq(1, 2, length.out = 10),
    HR = seq(70, 80, length.out = 10),
    TTL0 = c(1, rep(0, 9))
  )

  p <- plot_gazepoint_multimodal_timeline(
    data = dat,
    time_col = "CNT",
    signal_cols = c("GSR_US", "HR"),
    group_cols = c("participant", "MEDIA_ID"),
    event_col = "TTL0",
    standardise = TRUE,
    show_event_markers = TRUE,
    title = "Multimodal timeline test"
  )

  check <- check_gazepoint_plot_contract(p)

  expect_s3_class(p, "gazepoint_plot")
  expect_equal(check$overview$status, "pass_plot_contract")
  expect_true(is.data.frame(get_gazepoint_plot_data(p)))
  expect_true(is.list(get_gazepoint_plot_settings(p)))
  expect_equal(attr(p, "plot_type"), "multimodal_timeline")
  expect_true(is.data.frame(attr(p, "event_data")))
})
