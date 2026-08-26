
test_that("standardize_gazepoint_column_names maps common aliases", {
  dat <- data.frame(
    TIME = 1:3,
    LPD = c(3, 3.1, 3.2),
    BPOGX = c(.1, .2, .3),
    BPOGY = c(.4, .5, .6),
    GSR_US = c(1, 2, 3)
  )

  out <- standardize_gazepoint_column_names(dat)

  expect_true(all(c("time_s", "pupil_left", "gaze_x", "gaze_y", "GSR") %in% names(out)))
  expect_true(is.data.frame(attr(out, "gazepoint_column_standardization")))
})

test_that("audit_gazepoint_export_schema reports present and missing roles", {
  dat <- data.frame(time_s = 1:3, GSR = 1:3)
  out <- audit_gazepoint_export_schema(dat, expected_roles = c("time_s", "GSR", "PPG"))

  expect_equal(out$status[out$role == "time_s"], "present")
  expect_equal(out$status[out$role == "PPG"], "missing")
})

test_that("simulate_gazepoint_multimodal_data returns expected tables", {
  sim <- simulate_gazepoint_multimodal_data(duration_s = 4, sampling_rate_hz = 10, seed = 123)

  expect_true(all(c("biometrics", "eye", "events", "fixations", "metadata") %in% names(sim)))
  expect_true(all(c("GSR", "PPG", "HR", "IBI") %in% names(sim$biometrics)))
  expect_true(all(c("pupil_left", "gaze_x", "AOI") %in% names(sim$eye)))
})

test_that("assess_gazepoint_sampling_irregularity detects large gaps", {
  dat <- data.frame(time_s = c(0, .1, .2, .3, 1.0, 1.1))
  out <- assess_gazepoint_sampling_irregularity(dat, time_col = "time_s")

  expect_true(out$n_large_gaps >= 1)
  expect_true(out$effective_rate_hz > 0)
})

test_that("diagnose_gazepoint_sync_drift estimates changing lag", {
  ref <- seq(0, 10, by = 1)
  target <- ref + 0.10 + 0.01 * ref

  out <- diagnose_gazepoint_sync_drift(ref, target)

  expect_true(is.list(out))
  expect_true(out$summary$drift_slope_s_per_s > 0)
  expect_equal(nrow(out$lag_table), length(ref))
})

test_that("summarize_gazepoint_aoi_dwell computes dwell and entries", {
  dat <- data.frame(
    participant = "P01",
    trial = "T1",
    time_s = seq(0, .5, by = .1),
    AOI = c("left", "left", "center", "center", "left", "left")
  )

  out <- summarize_gazepoint_aoi_dwell(dat, group_cols = c("participant", "trial"))

  expect_true(all(c("left", "center") %in% out$AOI))
  expect_true(out$dwell_time_s[out$AOI == "left"] > out$dwell_time_s[out$AOI == "center"])
  expect_true(out$entry_count[out$AOI == "left"] >= 2)
})

test_that("summarize_gazepoint_scanpath_metrics computes path metrics", {
  dat <- data.frame(
    participant = "P01",
    trial = "T1",
    time_s = 1:4,
    gaze_x = c(0, .2, .4, .1),
    gaze_y = c(0, .1, .2, .3),
    AOI = c("A", "A", "B", "A")
  )

  out <- summarize_gazepoint_scanpath_metrics(dat, group_cols = c("participant", "trial"))

  expect_true(out$path_length > 0)
  expect_true(out$saccade_count > 0)
  expect_true(out$aoi_transition_count >= 2)
})

test_that("create_gazepoint_analysis_manifest returns and writes manifest", {
  tmp <- tempfile(fileext = ".txt")
  input <- tempfile(fileext = ".csv")
  writeLines("x,y\n1,2", input)

  out <- create_gazepoint_analysis_manifest(
    files = input,
    settings = list(window_s = 5, threshold = .1),
    outputs = list(table = "features.csv"),
    path = tmp,
    include_session = FALSE
  )

  expect_true(file.exists(tmp))
  expect_true(is.list(out))
  expect_true(NROW(out$files) == 1)
})

test_that("compute_gazepoint_ppg_template_similarity returns beat similarities", {
  time <- seq(0, 10, by = .01)
  ppg <- sin(2 * pi * 1 * time)
  dat <- data.frame(time_s = time, PPG = ppg)
  peaks <- seq(.25, 9.25, by = 1)

  out <- compute_gazepoint_ppg_template_similarity(dat, peaks = peaks)

  expect_true(is.list(out))
  expect_true(nrow(out$beats) >= 8)
  expect_true(out$summary$mean_similarity > .95)
})

test_that("compute_gazepoint_hrv_wavelet_psd returns scale and band summaries", {
  rr <- 800 + 40 * sin(seq(0, 8 * pi, length.out = 128))
  out <- compute_gazepoint_hrv_wavelet_psd(rr)

  expect_true(is.list(out))
  expect_true(nrow(out$psd) > 0)
  expect_true(all(c("vlf", "lf", "hf") %in% out$band_power$band))
  expect_true(all(out$psd$wavelet_power >= 0))
})

