
test_that("align_gazepoint_streams_by_events estimates linear alignment", {
  ref <- data.frame(time_s = seq(0, 10, by = 1), GSR = seq(0, 10, by = 1))
  target <- data.frame(time_s = 0.2 + 1.01 * seq(0, 10, by = 1), PPG = seq(0, 10, by = 1))

  ref_events <- data.frame(event_id = c("A", "B", "C"), event_time = c(1, 5, 9))
  target_events <- data.frame(event_id = c("A", "B", "C"), event_time = 0.2 + 1.01 * c(1, 5, 9))

  out <- align_gazepoint_streams_by_events(
    reference = ref,
    target = target,
    reference_events = ref_events,
    target_events = target_events,
    event_id_col = "event_id"
  )

  expect_true(inherits(out, "gazepoint_stream_alignment"))
  expect_true(abs(out$diagnostics$slope_target_per_reference - 1.01) < 1e-8)
  expect_true(abs(out$diagnostics$intercept_s - 0.2) < 1e-8)
  expect_true("target_time_aligned_s" %in% names(out$target_aligned))
})

test_that("align_gazepoint_streams_by_events falls back to offset alignment", {
  ref <- data.frame(time_s = 0:5)
  target <- data.frame(time_s = 0.5 + 0:5)

  out <- align_gazepoint_streams_by_events(
    ref,
    target,
    reference_events = c(1),
    target_events = c(1.5)
  )

  expect_equal(out$diagnostics$method, "offset")
  expect_true(abs(out$diagnostics$intercept_s - 0.5) < 1e-8)
})

test_that("build_gazepoint_aoi_timecourse summarizes AOI proportions", {
  dat <- data.frame(
    participant = "P01",
    trial = "T1",
    time_s = seq(0, 0.9, by = 0.1),
    AOI = c("left", "left", "center", "center", "left", "right", "right", "right", "center", "center")
  )

  out <- build_gazepoint_aoi_timecourse(
    dat,
    group_cols = c("participant", "trial"),
    bin_width_s = 0.5
  )

  expect_true(all(c("left", "center", "right") %in% out$AOI))
  expect_true(all(c("bin_start_s", "aoi_prop") %in% names(out)))
  expect_true(any(out$aoi_prop > 0, na.rm = TRUE))
})

test_that("build_gazepoint_aoi_timecourse can derive AOIs from rectangles", {
  dat <- data.frame(
    time_s = seq(0, 0.4, by = 0.1),
    gaze_x = c(0.1, 0.2, 0.8, 0.9, 0.5),
    gaze_y = c(0.5, 0.5, 0.5, 0.5, 0.5)
  )

  defs <- data.frame(
    AOI = c("left", "right"),
    xmin = c(0, 0.7),
    xmax = c(0.3, 1),
    ymin = c(0, 0),
    ymax = c(1, 1)
  )

  out <- build_gazepoint_aoi_timecourse(
    dat,
    aoi_definitions = defs,
    bin_width_s = 0.5
  )

  expect_true(all(c("left", "right") %in% out$AOI))
})

test_that("summarize_gazepoint_eventlocked_multimodal summarizes one data frame", {
  time <- seq(0, 5, by = 0.1)
  dat <- data.frame(
    time_s = time,
    GSR = 1 + exp(-((time - 2)^2) / 0.1),
    pupil_left = 3 + 0.2 * exp(-((time - 2.2)^2) / 0.2)
  )

  events <- data.frame(event_id = "E1", event_time = 2)

  out <- summarize_gazepoint_eventlocked_multimodal(
    dat,
    events,
    signal_cols = c("GSR", "pupil_left"),
    pre_s = 1,
    post_s = 1,
    summary_window_s = c(0, 1)
  )

  expect_true(inherits(out, "gazepoint_eventlocked_multimodal"))
  expect_equal(length(unique(out$summary$signal)), 2)
  expect_true(all(out$summary$n_samples > 0))
  expect_true(nrow(out$samples) > 0)
})

test_that("summarize_gazepoint_eventlocked_multimodal supports named stream lists", {
  time <- seq(0, 4, by = 0.1)

  streams <- list(
    physiology = data.frame(time_s = time, GSR = sin(time)),
    eye = data.frame(time_s = time, pupil_left = 3 + cos(time) / 10)
  )

  events <- data.frame(event_id = c("E1", "E2"), event_time = c(1, 3))

  out <- summarize_gazepoint_eventlocked_multimodal(
    streams,
    events,
    signal_cols = list(physiology = "GSR", eye = "pupil_left"),
    pre_s = 0.5,
    post_s = 0.5
  )

  expect_true(all(c("physiology", "eye") %in% out$summary$modality))
  expect_equal(length(unique(out$summary$event_id)), 2)
})

test_that("create_gazepoint_quality_dashboard combines and exports components", {
  dat <- data.frame(
    time_s = seq(0, 1, by = 0.1),
    GSR = c(1, 1, NA, 1.2, 1.3, 1.2, 1.1, NA, 1.0, 1.1, 1.2),
    PPG = sin(seq(0, 1, by = 0.1))
  )

  audit <- audit_gazepoint_biometrics_file(
    data = dat,
    expected_modalities = c("time", "eda", "ppg")
  )

  missingness <- summarize_gazepoint_missingness(dat, signal_cols = c("GSR", "PPG"))

  out_dir <- tempfile("gp_quality_dashboard_")

  dash <- create_gazepoint_quality_dashboard(
    audit = audit,
    missingness = missingness,
    output_dir = out_dir
  )

  expect_true(inherits(dash, "gazepoint_quality_dashboard"))
  expect_true(file.exists(file.path(out_dir, "quality_dashboard_overview.csv")))
  expect_true(file.exists(file.path(out_dir, "quality_dashboard_missingness.csv")))
  expect_true(dash$overview$has_audit)
})

