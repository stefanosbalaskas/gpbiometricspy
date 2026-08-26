
test_that("PsPM-style marker extraction and combination work", {
  fs <- 10
  t <- seq(0, 10, by = 1 / fs)
  marker_a <- rep(0, length(t))
  marker_b <- rep(0, length(t))

  marker_a[t >= 2 & t < 2.3] <- 1
  marker_b[t >= 5 & t < 5.2] <- 9

  d <- data.frame(
    participant = "P01",
    time_s = t,
    marker_a = marker_a,
    marker_b = marker_b,
    scr = sin(t)
  )

  markers <- extract_gazepoint_markerinfo_pspm_style(
    d,
    marker_cols = c("marker_a", "marker_b"),
    time_col = "time_s",
    group_cols = "participant"
  )

  expect_true(is.data.frame(markers))
  expect_true(nrow(markers) >= 2)
  expect_true(all(c("marker_channel", "time_s", "marker_code") %in% names(markers)))

  combined <- combine_gazepoint_marker_channels_pspm_style(
    d,
    marker_cols = c("marker_a", "marker_b"),
    time_col = "time_s",
    group_cols = "participant"
  )

  expect_true(is.list(combined))
  expect_true(is.data.frame(combined$data))
  expect_true("pspm_marker" %in% names(combined$data))
  expect_true(is.data.frame(combined$markers))
})

test_that("PsPM-style trim split and merge helpers work", {
  d <- data.frame(
    time_s = c(seq(0, 2, by = 0.1), seq(10, 12, by = 0.1)),
    scr = rnorm(42)
  )

  trimmed <- trim_gazepoint_biometrics_pspm_style(
    d,
    start_s = 0.5,
    end_s = 1.5,
    time_col = "time_s",
    reset_time = TRUE
  )

  expect_true(is.data.frame(trimmed))
  expect_equal(min(trimmed$time_s), 0)

  split_out <- split_gazepoint_sessions_pspm_style(
    d,
    time_col = "time_s",
    gap_seconds = 2
  )

  expect_true(is.list(split_out))
  expect_true(nrow(split_out$sessions) == 2)

  merged <- merge_gazepoint_recordings_pspm_style(
    list(trimmed, trimmed),
    time_col = "time_s",
    gap_seconds = 1
  )

  expect_true(is.data.frame(merged))
  expect_true("pspm_recording" %in% names(merged))
  expect_equal(length(unique(merged$pspm_recording)), 2)
})

test_that("PsPM-style SCR preprocessing works", {
  fs <- 50
  t <- seq(0, 20, by = 1 / fs)
  scr <- 1 + 0.01 * t + 0.2 * exp(-((t - 8) ^ 2) / 0.8)
  scr[100:110] <- 100
  scr[400:440] <- scr[400]

  d <- data.frame(time_s = t, gsr = scr)

  out <- preprocess_gazepoint_scr_pspm_style(
    d,
    signal_col = "gsr",
    time_col = "time_s",
    sampling_rate_hz = fs,
    range = c(0, 20)
  )

  expect_true(is.list(out))
  expect_true(is.data.frame(out$signal))
  expect_true(is.data.frame(out$summary))
  expect_true("scr_processed" %in% names(out$signal))
  expect_true(any(out$signal$pspm_artifact))
})

test_that("PsPM-style segment extraction works", {
  fs <- 20
  t <- seq(0, 20, by = 1 / fs)
  y <- sin(t)

  d <- data.frame(time_s = t, scr = y)
  events <- data.frame(
    event_id = 1:2,
    onset_time_s = c(5, 12),
    condition = c("A", "B")
  )

  seg <- extract_gazepoint_segments_pspm_style(
    d,
    events = events,
    signal_col = "scr",
    time_col = "time_s",
    event_id_col = "event_id",
    condition_col = "condition",
    pre_s = 1,
    post_s = 2
  )

  expect_true(is.data.frame(seg))
  expect_true(all(c("event_id", "relative_time_s", "value_baseline_corrected") %in% names(seg)))
  expect_true(length(unique(seg$event_id)) == 2)
})

test_that("PsPM-style convolution GLM and export work", {
  fs <- 20
  t <- seq(0, 60, by = 1 / fs)

  events <- data.frame(
    onset_time_s = c(5, 15, 25, 35, 45),
    condition = c("A", "B", "A", "B", "A")
  )

  design <- create_gazepoint_pspm_glm_design(
    events = events,
    time = t,
    response = "scr",
    response_length_s = 8
  )

  y <- 0.5 * design$pspm_A - 0.2 * design$pspm_B + rnorm(length(t), 0, 0.01)
  d <- data.frame(time_s = t, scr = y)

  fit <- fit_gazepoint_convolution_glm(
    data = d,
    design = design,
    signal_col = "scr",
    time_col = "time_s"
  )

  expect_true(inherits(fit, "gazepoint_pspm_glm"))
  expect_true(is.data.frame(fit$coefficients))
  expect_true(is.data.frame(fit$summary))
  expect_true(fit$summary$r_squared[1] > 0.5)

  out_csv <- tempfile(fileext = ".csv")
  files <- export_gazepoint_pspm_model_estimates(fit, out_csv)
  expect_true(is.data.frame(files))
  expect_true(file.exists(out_csv))

  out_rds <- tempfile(fileext = ".rds")
  files_rds <- export_gazepoint_pspm_model_estimates(fit, out_rds)
  expect_true(file.exists(out_rds))
  expect_true(is.data.frame(files_rds))
})

