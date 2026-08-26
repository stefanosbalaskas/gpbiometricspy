
test_that("compute_gazepoint_scr_habituation estimates decreasing slope", {
  dat <- data.frame(
    participant = rep(c("P01", "P02"), each = 5),
    trial = rep(1:5, 2),
    scr_amplitude = c(1, .8, .6, .4, .2, 2, 1.8, 1.5, 1.2, 1)
  )

  out <- compute_gazepoint_scr_habituation(
    dat,
    amplitude_col = "scr_amplitude",
    trial_col = "trial",
    subject_col = "participant"
  )

  expect_equal(nrow(out), 2)
  expect_true(all(out$habituation_slope < 0))
  expect_true(all(out$last_first_ratio < 1))
})

test_that("compute_gazepoint_scr_habituation accepts vector input", {
  out <- compute_gazepoint_scr_habituation(c(1, .8, .6, .4))
  expect_equal(nrow(out), 1)
  expect_true(out$habituation_slope < 0)
})

test_that("summarize_gazepoint_scr_recovery returns peak and recovery metrics", {
  time <- seq(0, 10, by = .1)
  gsr <- exp(-((time - 3)^2) / .05) * .8
  gsr[time > 3] <- gsr[time > 3] * exp(-(time[time > 3] - 3) / 2)
  dat <- data.frame(time_s = time, GSR = gsr)

  out <- summarize_gazepoint_scr_recovery(dat, events = 2, pre = 1, post = 6)

  expect_equal(nrow(out), 1)
  expect_true(out$peak_amplitude > .1)
  expect_true(is.finite(out$peak_latency_s))
})

test_that("summarize_gazepoint_pupil_events computes pupil response metrics", {
  time <- seq(0, 8, by = .1)
  pupil <- 3 + exp(-((time - 3)^2) / .2) * .5
  dat <- data.frame(time_s = time, LPD = pupil)

  out <- summarize_gazepoint_pupil_events(dat, events = 2, pre = 1, post = 4, pupil_col = "LPD")

  expect_equal(nrow(out), 1)
  expect_true(out$pupil_peak_dilation > .2)
  expect_true(out$pupil_auc > 0)
})

test_that("summarize_gazepoint_tracking computes validity ratios", {
  dat <- data.frame(
    participant = c("P01", "P01", "P01", "P02"),
    LPD = c(3, NA, 3, 3),
    LPV = c(1, 0, 1, 1),
    BPOGX = c(.1, .2, 2, .3),
    BPOGY = c(.1, .2, .3, .4)
  )

  out <- summarize_gazepoint_tracking(dat, pupil_cols = "LPD", group_cols = "participant")

  expect_equal(nrow(out), 2)
  expect_true(out$tracking_ratio[out$participant == "P01"] < 1)
  expect_equal(out$tracking_ratio[out$participant == "P02"], 1)
})

test_that("audit_gazepoint_pupil_luminance flags strong correlations", {
  dat <- data.frame(
    LPD = 1:10,
    luminance = 1:10
  )

  out <- audit_gazepoint_pupil_luminance(dat, pupil_col = "LPD", luminance_col = "luminance", threshold = .3)

  expect_true(out$flag_luminance_confound)
  expect_true(out$correlation > .9)
})

test_that("extract_gazepoint_ppg_morphology extracts pulse rows", {
  time <- seq(0, 10, by = .01)
  ppg <- sin(2 * pi * 1 * time)
  dat <- data.frame(time_s = time, PPG = ppg)

  out <- extract_gazepoint_ppg_morphology(dat, min_peak_distance_s = .5)

  expect_true(is.data.frame(out))
  expect_true(nrow(out) >= 5)
  expect_true(all(out$pulse_amplitude > 0, na.rm = TRUE))
  expect_true(all(out$rise_time_s >= 0, na.rm = TRUE))
})

test_that("flag_gazepoint_ppg_quality returns segment quality flags", {
  time <- seq(0, 20, by = .1)
  ppg <- sin(time)
  ppg[time >= 10 & time < 20] <- 1
  dat <- data.frame(time_s = time, PPG = ppg)

  out <- flag_gazepoint_ppg_quality(dat, window_s = 10, flat_sd_threshold = .001)

  expect_true(is.data.frame(out))
  expect_true(nrow(out) >= 2)
  expect_true(any(!out$quality_ok))
})

test_that("import_gazepoint_event_log reads csv and standardizes columns", {
  tmp <- tempfile(fileext = ".csv")
  writeLines(c("trial,onset,condition", "T1,1,A", "T2,2,B"), tmp)

  out <- import_gazepoint_event_log(tmp, time_col = "onset", event_col = "condition", id_col = "trial")

  expect_equal(out$event_id, c("T1", "T2"))
  expect_equal(out$event_label, c("A", "B"))
  expect_equal(out$event_time, c(1, 2))
})

test_that("match_gazepoint_events_to_biometrics returns windows and summaries", {
  dat <- data.frame(
    time_s = seq(0, 10, by = 1),
    GSR = seq(0, 1, length.out = 11)
  )
  events <- data.frame(trial = "T1", onset = 5, condition = "A")

  windows <- match_gazepoint_events_to_biometrics(
    dat,
    events,
    pre = 1,
    post = 1,
    event_time_col = "onset",
    event_id_col = "trial",
    return = "windows"
  )

  summary <- match_gazepoint_events_to_biometrics(
    dat,
    events,
    pre = 1,
    post = 1,
    event_time_col = "onset",
    event_id_col = "trial",
    return = "summary"
  )

  expect_equal(nrow(windows), 3)
  expect_equal(summary$n_samples, 3)
  expect_true("GSR_mean" %in% names(summary))
})

test_that("assert_gazepoint_columns validates required columns", {
  dat <- data.frame(time_s = 1:3, GSR = 1:3)

  expect_true(assert_gazepoint_columns(dat, required = c("time_s", "GSR")))
  expect_error(assert_gazepoint_columns(dat, required = c("time_s", "PPG")))

  summary <- assert_gazepoint_columns(
    dat,
    required = c("time_s", "PPG"),
    optional = "GSR",
    mode = "summary"
  )

  expect_true(is.data.frame(summary))
  expect_false(summary$present[summary$column == "PPG"])
})

test_that("gpbiometrics_info returns package metadata", {
  info <- gpbiometrics_info(print = FALSE)

  expect_true(is.list(info))
  expect_equal(info$package, "gpbiometrics")
  expect_true(nzchar(info$version))
})

