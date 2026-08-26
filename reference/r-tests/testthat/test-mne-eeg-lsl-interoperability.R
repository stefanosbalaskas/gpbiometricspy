test_that("MNE events are prepared from an event table", {
  events <- data.frame(
    event_time_s = c(1, 2, 3),
    event_label = c(
      "stimulus/A",
      "stimulus/B",
      "response"
    )
  )

  out <- prepare_gazepoint_mne_events(
    events,
    sampling_rate_hz = 100
  )

  expect_s3_class(
    out,
    "gazepoint_mne_events"
  )

  expect_equal(
    dim(out$events),
    c(3L, 3L)
  )

  expect_equal(
    out$events[, 1L],
    c(100L, 200L, 300L)
  )

  expect_equal(
    out$events[, 2L],
    c(0L, 0L, 0L)
  )

  expect_equal(
    unname(out$event_id),
    1:3
  )
})

test_that("MNE event dictionaries can be supplied explicitly", {
  events <- data.frame(
    event_time_s = c(1, 2),
    event_label = c("left", "right")
  )

  out <- prepare_gazepoint_mne_events(
    events,
    sampling_rate_hz = 1000,
    event_id = c(
      left = 11,
      right = 12
    )
  )

  expect_equal(
    out$events[, 3L],
    c(11L, 12L)
  )

  expect_equal(
    unname(out$event_id[c("left", "right")]),
    c(11L, 12L)
  )
})

test_that("continuous marker columns produce onset events", {
  data <- data.frame(
    time_s = seq(0, 0.5, by = 0.1),
    TTL0 = c(0, 1, 1, 0, 2, 2)
  )

  out <- prepare_gazepoint_mne_events(
    data,
    marker_cols = "TTL0",
    sampling_rate_hz = 10
  )

  expect_equal(
    nrow(out$events),
    2
  )

  expect_equal(
    out$table$event_label,
    c(
      "TTL0",
      "TTL0/2"
    )
  )

  expect_equal(
    out$events[, 1L],
    c(1L, 4L)
  )
})

test_that("MNE event files can be exported", {
  events <- data.frame(
    event_time_s = c(0.1, 0.2),
    event_label = c("A", "B")
  )

  path <- tempfile(
    fileext = ".txt"
  )

  out <- prepare_gazepoint_mne_events(
    events,
    sampling_rate_hz = 100,
    export_csv = path
  )

  expect_true(
    file.exists(path)
  )

  written <- utils::read.table(
    path,
    header = FALSE
  )

  expect_equal(
    ncol(written),
    3
  )

  expect_true(
    out$audit$exported
  )
})

test_that("repeated MNE event samples are rejected by default", {
  events <- data.frame(
    event_time_s = c(1, 1),
    event_label = c("A", "B")
  )

  expect_error(
    prepare_gazepoint_mne_events(
      events,
      sampling_rate_hz = 100
    ),
    "Repeated"
  )
})

test_that("MNE channel matrices and types are prepared", {
  data <- data.frame(
    time_s = c(0, 0.01, 0.02, 0.03),
    gaze_x = c(0.2, 0.3, 0.4, 0.5),
    pupil_left = c(3.0, 3.1, 3.2, 3.3),
    GSR = c(5, 5.1, 5.2, 5.3),
    TTL0 = c(0, 1, 0, 0)
  )

  out <- prepare_gazepoint_mne_input(
    data
  )

  expect_s3_class(
    out,
    "gazepoint_mne_input"
  )

  expect_equal(
    dim(out$data),
    c(4L, 4L)
  )

  expect_equal(
    out$channel_info$channel_type,
    c(
      "eyegaze",
      "pupil",
      "gsr",
      "stim"
    )
  )

  expect_equal(
    out$info_spec$sfreq,
    100,
    tolerance = 1e-8
  )
})

test_that("MNE scale factors are explicit", {
  data <- data.frame(
    time_ms = c(0, 10, 20),
    PPG = c(1, 2, 3)
  )

  out <- prepare_gazepoint_mne_input(
    data,
    channel_cols = "PPG",
    scale_factors = 0.001
  )

  expect_equal(
    as.numeric(out$data[1, ]),
    c(0.001, 0.002, 0.003)
  )

  expect_equal(
    out$channel_info$scale_factor,
    0.001
  )
})

test_that("irregular MNE input is rejected or audited", {
  data <- data.frame(
    time_ms = c(0, 10, 20, 50),
    pupil = c(3.0, 3.1, 3.2, 3.3)
  )

  expect_error(
    prepare_gazepoint_mne_input(
      data
    ),
    "Irregular"
  )

  out <- prepare_gazepoint_mne_input(
    data,
    irregular = "allow"
  )

  expect_true(
    out$sampling$irregular_interval_count > 0
  )
})

test_that("missing MNE channel values require explicit allowance", {
  data <- data.frame(
    time_ms = c(0, 10, 20),
    pupil = c(3.0, NA, 3.2)
  )

  expect_error(
    prepare_gazepoint_mne_input(
      data
    ),
    "Non-finite"
  )

  out <- prepare_gazepoint_mne_input(
    data,
    missing = "allow"
  )

  expect_true(
    is.na(out$data[1, 2])
  )
})

test_that("constant-offset EEG alignment is applied", {
  gaze <- data.frame(
    time_s = c(0, 1, 2, 3),
    pupil = c(3.0, 3.1, 3.2, 3.3)
  )

  gp_events <- data.frame(
    event_id = c("A", "B", "C"),
    event_time_s = c(0.5, 1.5, 2.5)
  )

  eeg_events <- data.frame(
    event_id = c("A", "B", "C"),
    event_time_s = c(0.7, 1.7, 2.7)
  )

  out <- align_gazepoint_to_eeg(
    gaze,
    gp_events,
    eeg_events,
    method = "offset"
  )

  expect_s3_class(
    out,
    "gazepoint_eeg_alignment"
  )

  expect_equal(
    out$mapping$intercept_s,
    0.2,
    tolerance = 1e-10
  )

  expect_equal(
    out$data$time_eeg_s,
    gaze$time_s + 0.2,
    tolerance = 1e-10
  )
})

test_that("linear EEG alignment estimates drift", {
  gaze <- data.frame(
    time_s = 0:4
  )

  gp_events <- data.frame(
    event_id = LETTERS[1:5],
    event_time_s = 0:4
  )

  eeg_events <- data.frame(
    event_id = LETTERS[1:5],
    event_time_s =
      0.1 +
      1.001 *
      (0:4)
  )

  out <- align_gazepoint_to_eeg(
    gaze,
    gp_events,
    eeg_events,
    method = "linear"
  )

  expect_equal(
    out$mapping$intercept_s,
    0.1,
    tolerance = 1e-10
  )

  expect_equal(
    out$mapping$slope,
    1.001,
    tolerance = 1e-10
  )

  expect_equal(
    out$audit$drift_ppm,
    1000,
    tolerance = 1e-6
  )
})

test_that("EEG sample columns can be converted to time", {
  gaze <- data.frame(
    time_s = 0:2
  )

  gp_events <- data.frame(
    event_id = c("A", "B", "C"),
    event_time_s = c(0, 1, 2)
  )

  eeg_events <- data.frame(
    event_id = c("A", "B", "C"),
    sample = c(10, 110, 210)
  )

  out <- align_gazepoint_to_eeg(
    gaze,
    gp_events,
    eeg_events,
    eeg_event_sample_col = "sample",
    eeg_sampling_rate_hz = 100,
    method = "offset"
  )

  expect_equal(
    out$mapping$intercept_s,
    0.1,
    tolerance = 1e-10
  )

  expect_true(
    "time_eeg_s_sample" %in%
      names(out$data)
  )
})

test_that("methods text includes supplied acquisition details", {
  text <- create_gazepoint_eye_methods_text(
    sampling_rate_hz = 60,
    calibration_points = 9,
    screen_resolution = c(1920, 1080),
    viewing_distance_cm = 60,
    preprocessing = c(
      "blink flagging",
      "short-gap interpolation"
    ),
    synchronization = "TTL markers"
  )

  expect_s3_class(
    text,
    "gazepoint_eye_methods_text"
  )

  expect_match(
    as.character(text),
    "60 Hz"
  )

  expect_match(
    as.character(text),
    "9-point calibration"
  )

  expect_match(
    as.character(text),
    "1920 x 1080"
  )

  expect_match(
    as.character(text),
    "TTL markers"
  )
})

test_that("future-tense methods text is supported", {
  text <- create_gazepoint_eye_methods_text(
    sampling_rate_hz = 60,
    tense = "future"
  )

  expect_match(
    as.character(text),
    "will be recorded"
  )
})

test_that("session information records gpbiometrics and R", {
  out <- session_info_gazepoint(
    packages = "testthat",
    include_loaded = FALSE
  )

  expect_s3_class(
    out,
    "gazepoint_session_info"
  )

  expect_true(
    "gpbiometrics" %in%
      out$packages$package
  )

  expect_true(
    "testthat" %in%
      out$packages$package
  )

  expect_true(
    "r_version" %in%
      out$system$field
  )
})

test_that("LSL streams receive explicit offset and lag correction", {
  streams <- list(
    gaze = data.frame(
      time_s = c(0, 1, 2),
      x = c(0.2, 0.3, 0.4)
    ),
    eeg = data.frame(
      time_s = c(0.1, 1.1, 2.1),
      eeg = c(1, 2, 3)
    )
  )

  out <- sync_gazepoint_signals_via_lsl(
    streams,
    reference = "gaze",
    clock_offsets_s = c(
      gaze = 0,
      eeg = -0.1
    )
  )

  expect_s3_class(
    out,
    "gazepoint_lsl_sync"
  )

  expect_equal(
    out$streams$gaze$.lsl_time_relative_s,
    c(0, 1, 2)
  )

  expect_equal(
    out$streams$eeg$.lsl_time_relative_s,
    c(0, 1, 2),
    tolerance = 1e-10
  )
})

test_that("LSL streams can be merged by nearest timestamp", {
  streams <- list(
    gaze = data.frame(
      time_s = c(0, 1, 2),
      x = c(0.2, 0.3, 0.4)
    ),
    marker = data.frame(
      time_s = c(0.05, 1.05, 2.05),
      marker = c("A", "B", "C")
    )
  )

  out <- sync_gazepoint_signals_via_lsl(
    streams,
    reference = "gaze",
    merge = "nearest",
    tolerance_s = 0.1
  )

  expect_true(
    is.data.frame(out$merged)
  )

  expect_equal(
    out$merged$marker__marker,
    c("A", "B", "C")
  )

  expect_equal(
    out$merged$marker__time_difference_s,
    rep(0.05, 3),
    tolerance = 1e-10
  )
})

test_that("pyxdf-style stream lists are supported", {
  streams <- list(
    gaze = list(
      time_stamps = c(10, 10.1, 10.2),
      time_series = matrix(
        c(
          0.2, 0.5,
          0.3, 0.5,
          0.4, 0.5
        ),
        ncol = 2,
        byrow = TRUE,
        dimnames = list(
          NULL,
          c("x", "y")
        )
      )
    )
  )

  out <- sync_gazepoint_signals_via_lsl(
    streams
  )

  expect_equal(
    names(out$streams$gaze)[1:2],
    c("x", "y")
  )

  expect_equal(
    out$streams$gaze$.lsl_time_relative_s,
    c(0, 0.1, 0.2),
    tolerance = 1e-10
  )
})

test_that("linear LSL dejittering is explicit", {
  streams <- list(
    gaze = data.frame(
      time_s = c(0, 0.101, 0.199, 0.301),
      x = 1:4
    )
  )

  out <- sync_gazepoint_signals_via_lsl(
    streams,
    dejitter = "linear",
    nominal_rates_hz = 10
  )

  expect_equal(
    diff(
      out$streams$gaze$
        .lsl_time_corrected_s
    ),
    rep(0.1, 3),
    tolerance = 1e-10
  )
})
