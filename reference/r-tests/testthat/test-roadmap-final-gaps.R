test_that("gaze validation consolidates normalized-coordinate checks", {
  data <- data.frame(
    participant = rep("P01", 5),
    trial = rep("T01", 5),
    time_s = seq(0, 0.04, by = 0.01),
    gaze_x = c(0.2, 0.4, 1.2, NA, 0.5),
    gaze_y = c(0.3, 0.5, 0.6, NA, 0.5),
    valid = c(TRUE, TRUE, TRUE, TRUE, FALSE)
  )

  out <- validate_gazepoint_gaze(
    data,
    group_cols = c("participant", "trial"),
    expected_sampling_rate_hz = 100
  )

  expect_s3_class(out, "gazepoint_gaze_validation")
  expect_equal(out$summary$n_samples, 5)
  expect_equal(out$summary$out_of_range_rate, 1 / 5)
  expect_equal(out$summary$missing_gaze_rate, 2 / 5)
  expect_true(out$data$.gaze_out_of_range[3])
  expect_true(out$data$.gaze_invalid[4])
  expect_true(out$data$.gaze_invalid[5])
})

test_that("gaze validation detects duplicate and nonmonotonic time", {
  data <- data.frame(
    time_ms = c(0, 10, 10, 5, 30),
    gaze_x = rep(0.5, 5),
    gaze_y = rep(0.5, 5)
  )

  out <- validate_gazepoint_gaze(data)

  expect_equal(out$summary$duplicate_time_count, 1)
  expect_equal(out$summary$nonmonotonic_time_count, 1)
  expect_equal(
    out$checks$status[out$checks$check == "monotonic_time"],
    "fail"
  )
})

test_that("pixel range checks require dimensions", {
  data <- data.frame(
    time_ms = c(0, 10, 20),
    gaze_x = c(100, 2000, 300),
    gaze_y = c(100, 500, 1200)
  )

  no_screen <- validate_gazepoint_gaze(data)
  expect_false(no_screen$settings$range_assessed)

  with_screen <- validate_gazepoint_gaze(
    data,
    coordinate_system = "pixels",
    screen_width_px = 1920,
    screen_height_px = 1080
  )
  expect_equal(with_screen$summary$out_of_range_rate, 2 / 3)
})

test_that("fixations are summarized by participant trial and AOI", {
  fixations <- data.frame(
    participant = c("P01", "P01", "P01", "P01"),
    trial = c("T01", "T01", "T01", "T01"),
    aoi = c("claim", "claim", "evidence", "evidence"),
    start_ms = c(100, 300, 500, 800),
    end_ms = c(200, 450, 650, 900),
    duration_ms = c(100, 150, 150, 100),
    event_onset_ms = rep(50, 4)
  )

  out <- summarise_gazepoint_fixations_by_aoi(
    fixations,
    start_col = "start_ms",
    end_col = "end_ms",
    duration_col = "duration_ms",
    event_onset_col = "event_onset_ms"
  )

  expect_s3_class(out, "gazepoint_fixation_aoi_summary")
  expect_equal(nrow(out), 2)
  expect_equal(out$fixation_count, c(2, 2))
  expect_equal(out$total_fixation_duration_ms, c(250, 250))
  expect_equal(out$dwell_proportion, c(0.5, 0.5))
  expect_equal(out$first_fixation_latency_ms, c(50, 450))
})

test_that("fixation durations can be derived from start and end", {
  fixations <- data.frame(
    aoi = c("A", "A"),
    start_s = c(0.1, 0.4),
    end_s = c(0.2, 0.6)
  )

  out <- summarise_gazepoint_fixations_by_aoi(
    fixations,
    start_col = "start_s",
    end_col = "end_s",
    time_unit = "seconds"
  )

  expect_equal(out$total_fixation_duration_ms, 300)
  expect_equal(out$mean_fixation_duration_ms, 150)
})

test_that("unassigned fixations are configurable", {
  fixations <- data.frame(
    aoi = c("A", NA, ""),
    start_ms = c(0, 100, 200),
    duration_ms = c(50, 50, 50)
  )

  excluded <- summarise_gazepoint_fixations_by_aoi(
    fixations,
    start_col = "start_ms",
    duration_col = "duration_ms"
  )
  expect_equal(nrow(excluded), 1)

  included <- summarise_gazepoint_fixations_by_aoi(
    fixations,
    start_col = "start_ms",
    duration_col = "duration_ms",
    include_unassigned = TRUE
  )
  expect_equal(sort(included$aoi), c("A", "UNASSIGNED"))
})

test_that("American fixation-summary alias matches British spelling", {
  fixations <- data.frame(
    aoi = c("A", "B"),
    start_ms = c(0, 100),
    duration_ms = c(50, 60)
  )

  british <- summarise_gazepoint_fixations_by_aoi(
    fixations,
    start_col = "start_ms",
    duration_col = "duration_ms"
  )
  american <- summarize_gazepoint_fixations_by_aoi(
    fixations,
    start_col = "start_ms",
    duration_col = "duration_ms"
  )

  expect_equal(unclass(american), unclass(british))
})

test_that("BIDS eye wrapper provides a dry-run specification", {
  data <- data.frame(time_s = 0:2, gaze_x = 0.1, gaze_y = 0.2)

  out <- prepare_gazepoint_bids_eye(
    data,
    output_dir = tempdir(),
    execute = FALSE
  )

  expect_s3_class(out, "gazepoint_bids_wrapper_spec")
  expect_equal(out$modality, "eye")
  expect_false(out$executed)
})

test_that("BIDS physiology wrapper provides a dry-run specification", {
  data <- data.frame(time_s = 0:2, GSR = 1:3)

  out <- prepare_gazepoint_bids_physio(
    data,
    output_dir = tempdir(),
    execute = FALSE
  )

  expect_s3_class(out, "gazepoint_bids_wrapper_spec")
  expect_equal(out$modality, "physio")
})

test_that("MNE FIF writer supports dependency-free dry runs", {
  data <- data.frame(
    time_s = c(0, 0.01, 0.02),
    gaze_x = c(0.1, 0.2, 0.3),
    pupil = c(3.0, 3.1, 3.2)
  )

  prepared <- prepare_gazepoint_mne_input(data)

  out <- write_gazepoint_mne_fif(
    prepared,
    tempfile(pattern = "gazepoint_", fileext = "_raw.fif"),
    execute = FALSE
  )

  expect_s3_class(out, "gazepoint_mne_fif_export")
  expect_false(out$executed)
  expect_equal(out$n_channels, 2)
  expect_equal(out$n_samples, 3)
  expect_match(out$python_script, "mne.io.RawArray")
  expect_match(out$python_script, "raw.save")
})

test_that("MNE FIF writer rejects nonfinite data", {
  data <- data.frame(
    time_s = c(0, 0.01, 0.02),
    pupil = c(3.0, NA, 3.2)
  )

  prepared <- prepare_gazepoint_mne_input(
    data,
    missing = "allow"
  )

  expect_error(
    write_gazepoint_mne_fif(
      prepared,
      tempfile(pattern = "gazepoint_", fileext = "_raw.fif"),
      execute = FALSE
    ),
    "finite"
  )
})

test_that("LSL clock estimator supports dependency-free dry runs", {
  out <- estimate_gazepoint_lsl_clock_offsets(
    stream_name = "Gazepoint",
    n_estimates = 3,
    execute = FALSE
  )

  expect_s3_class(out, "gazepoint_lsl_clock_offsets")
  expect_false(out$executed)
  expect_equal(out$n_estimates, 3)
  expect_match(out$python_script, "time_correction")
})

test_that("LSL parser returns numeric estimates", {
  lines <- c(
    "PYLSL_VERSION\t1.17.6",
    paste(
      "ESTIMATE", "Gazepoint", "Gaze", "gp01", "uid1", "host1",
      "1", "0.0012", "100.5",
      sep = "\t"
    ),
    paste(
      "ESTIMATE", "Gazepoint", "Gaze", "gp01", "uid1", "host1",
      "2", "0.0010", "100.6",
      sep = "\t"
    )
  )

  parsed <- gpbiometrics:::.gp_gap_parse_lsl_output(lines)

  expect_equal(nrow(parsed), 2)
  expect_equal(parsed$offset_s, c(0.0012, 0.0010))
  expect_equal(parsed$estimate_index, 1:2)
})
