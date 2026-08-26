
test_that("detect_gazepoint_fixations detects known gaze events", {
  gaze <- data.frame(
    time_s = seq(0, 0.9, by = 0.1),
    gaze_x = c(
      0,
      0.01,
      0.02,
      0.03,
      1,
      1.01,
      1.02,
      1.03,
      1.04,
      1.05
    ),
    gaze_y = rep(0, 10)
  )

  out <- detect_gazepoint_fixations(
    gaze,
    time_col = "time_s",
    x_col = "gaze_x",
    y_col = "gaze_y",
    velocity_threshold = 2,
    min_fixation_duration_ms = 100,
    min_saccade_duration_ms = 50
  )

  expect_s3_class(out, "gazepoint_gaze_events")

  expect_named(
    out,
    c(
      "samples",
      "fixations",
      "saccades",
      "summary",
      "settings"
    )
  )

  expect_equal(nrow(out$fixations), 2)
  expect_equal(nrow(out$saccades), 1)

  expect_equal(
    out$samples$gaze_class,
    c(
      "fixation",
      "fixation",
      "fixation",
      "saccade",
      "saccade",
      "fixation",
      "fixation",
      "fixation",
      "fixation",
      "fixation"
    )
  )

  expect_equal(
    out$saccades$start_time,
    0.3,
    tolerance = 1e-12
  )

  expect_equal(
    out$saccades$end_time,
    0.4,
    tolerance = 1e-12
  )

  expect_equal(
    out$saccades$amplitude,
    0.97,
    tolerance = 1e-12
  )

  expect_equal(
    out$saccades$peak_velocity,
    9.7,
    tolerance = 1e-10
  )

  expect_equal(
    out$saccades$direction_deg,
    0,
    tolerance = 1e-12
  )

  expect_equal(out$summary$n_fixations, 2)
  expect_equal(out$summary$n_saccades, 1)
})

test_that("detect_gazepoint_fixations processes groups independently", {
  one <- data.frame(
    time_s = seq(0, 0.9, by = 0.1),
    gaze_x = c(
      0,
      0.01,
      0.02,
      0.03,
      1,
      1.01,
      1.02,
      1.03,
      1.04,
      1.05
    ),
    gaze_y = rep(0, 10),
    valid = 1
  )

  gaze <- rbind(
    transform(one, participant = "P01"),
    transform(one, participant = "P02")
  )

  out <- detect_gazepoint_fixations(
    gaze,
    time_col = "time_s",
    x_col = "gaze_x",
    y_col = "gaze_y",
    group_cols = "participant",
    valid_col = "valid",
    valid_values = 1,
    velocity_threshold = 2,
    min_fixation_duration_ms = 100,
    min_saccade_duration_ms = 50
  )

  expect_equal(nrow(out$summary), 2)
  expect_equal(out$summary$n_fixations, c(2, 2))
  expect_equal(out$summary$n_saccades, c(1, 1))

  expect_equal(
    sort(unique(out$saccades$participant)),
    c("P01", "P02")
  )
})

test_that("short gaze events are retained as unclassified samples", {
  gaze <- data.frame(
    time_s = seq(0, 0.4, by = 0.1),
    gaze_x = c(0, 0.01, 1, 1.01, 1.02),
    gaze_y = 0
  )

  out <- detect_gazepoint_fixations(
    gaze,
    time_col = "time_s",
    x_col = "gaze_x",
    y_col = "gaze_y",
    velocity_threshold = 2,
    min_fixation_duration_ms = 50,
    min_saccade_duration_ms = 150
  )

  expect_equal(nrow(out$saccades), 0)
  expect_true(
    any(out$samples$gaze_class == "unclassified")
  )
  expect_true(out$summary$n_unclassified_samples > 0)
})

test_that("time gaps split otherwise adjacent fixation events", {
  gaze <- data.frame(
    time_ms = c(0, 20, 40, 500, 520, 540),
    gaze_x = c(0, 0.01, 0.02, 0.02, 0.03, 0.04),
    gaze_y = 0
  )

  out <- detect_gazepoint_fixations(
    gaze,
    time_col = "time_ms",
    x_col = "gaze_x",
    y_col = "gaze_y",
    time_unit = "milliseconds",
    velocity_threshold = 2,
    min_fixation_duration_ms = 20,
    min_saccade_duration_ms = 10,
    max_gap_ms = 100
  )

  expect_equal(nrow(out$fixations), 2)
  expect_equal(out$summary$n_fixations, 2)
})

test_that("detect_gazepoint_saccades returns event table and attributes", {
  gaze <- data.frame(
    time_s = seq(0, 0.9, by = 0.1),
    gaze_x = c(
      0,
      0.01,
      0.02,
      0.03,
      1,
      1.01,
      1.02,
      1.03,
      1.04,
      1.05
    ),
    gaze_y = 0
  )

  out <- detect_gazepoint_saccades(
    gaze,
    time_col = "time_s",
    x_col = "gaze_x",
    y_col = "gaze_y",
    velocity_threshold = 2,
    min_fixation_duration_ms = 100,
    min_saccade_duration_ms = 50
  )

  expect_s3_class(
    out,
    "gazepoint_detected_saccades"
  )

  expect_equal(nrow(out), 1)

  expect_true(
    is.data.frame(attr(out, "gaze_event_summary"))
  )

  expect_true(
    is.list(attr(out, "gaze_event_settings"))
  )
})

test_that("detect_gazepoint_fixations validates inputs", {
  gaze <- data.frame(
    time_s = 0:3,
    gaze_x = 1:4,
    gaze_y = 1:4,
    label = letters[1:4]
  )

  expect_error(
    detect_gazepoint_fixations(
      gaze,
      time_col = "label",
      x_col = "gaze_x",
      y_col = "gaze_y",
      velocity_threshold = 2
    ),
    "numeric"
  )

  expect_error(
    detect_gazepoint_fixations(
      gaze,
      time_col = "time_s",
      x_col = "label",
      y_col = "gaze_y",
      velocity_threshold = 2
    ),
    "numeric"
  )

  expect_error(
    detect_gazepoint_fixations(
      gaze,
      time_col = "time_s",
      x_col = "gaze_x",
      y_col = "gaze_y",
      velocity_threshold = 0
    ),
    "positive"
  )

  expect_error(
    detect_gazepoint_fixations(
      gaze,
      time_col = "time_s",
      x_col = "gaze_x",
      y_col = "gaze_y",
      time_unit = "samples",
      velocity_threshold = 2
    ),
    "sampling_rate_hz"
  )

  expect_error(
    detect_gazepoint_fixations(
      transform(gaze, gaze_velocity = 0),
      time_col = "time_s",
      x_col = "gaze_x",
      y_col = "gaze_y",
      velocity_threshold = 2
    ),
    "already exist"
  )
})
