test_that("monocular gaze and pupil data are prepared", {
  data <- data.frame(
    participant = rep("P01", 4),
    trial = rep("T01", 4),
    time_s = c(0, 0.1, 0.2, 0.3),
    gaze_x = c(0.2, 0.4, 0.6, NA),
    gaze_y = c(0.5, 0.5, 0.5, NA),
    pupil = c(3.0, 3.1, 3.2, NA)
  )

  out <- prepare_gazepoint_gazer_input(
    data
  )

  expect_s3_class(
    out,
    "gazepoint_gazer_input"
  )

  expect_equal(
    names(out$data)[1:6],
    c(
      "subject",
      "trial",
      "time",
      "x",
      "y",
      "pupil"
    )
  )

  expect_equal(
    out$data$time,
    c(0, 100, 200, 300)
  )

  expect_equal(
    out$row_audit$finite_gaze_pair_count,
    c(1, 1, 1, 0)
  )

  expect_equal(
    out$row_audit$finite_pupil_count,
    c(1, 1, 1, 0)
  )
})

test_that("binocular gaze and pupil columns retain eye names", {
  data <- data.frame(
    participant = rep("P01", 3),
    trial = rep("T01", 3),
    time_ms = c(0, 20, 40),
    LPOGX = c(0.2, 0.3, 0.4),
    LPOGY = c(0.5, 0.5, 0.5),
    RPOGX = c(0.21, 0.31, 0.41),
    RPOGY = c(0.49, 0.49, 0.49),
    LPD = c(3.0, 3.1, 3.2),
    RPD = c(3.1, 3.2, 3.3)
  )

  out <- prepare_gazepoint_gazer_input(
    data
  )

  expect_true(
    all(
      c(
        "x_left",
        "y_left",
        "x_right",
        "y_right",
        "pupil_left",
        "pupil_right"
      ) %in% names(out$data)
    )
  )

  expect_equal(
    out$manifest$summary$gaze_pair_count,
    2
  )

  expect_true(
    out$manifest$summary$binocular_gaze
  )

  expect_true(
    out$manifest$summary$binocular_pupil
  )
})

test_that("pupil-only data are supported", {
  data <- data.frame(
    participant = rep("P01", 3),
    trial = rep("T01", 3),
    time_ms = c(0, 10, 20),
    pupil_left = c(3.0, 3.1, 3.2),
    pupil_right = c(3.1, 3.2, 3.3)
  )

  out <- prepare_gazepoint_gazer_input(
    data
  )

  expect_false(
    any(
      c(
        "x",
        "y",
        "x_left",
        "y_left"
      ) %in% names(out$data)
    )
  )

  expect_true(
    all(
      c(
        "pupil_left",
        "pupil_right"
      ) %in% names(out$data)
    )
  )

  expect_equal(
    out$manifest$summary$gaze_pair_count,
    0
  )
})

test_that("validity and blink flags are audited and optionally masked", {
  data <- data.frame(
    participant = rep("P01", 4),
    trial = rep("T01", 4),
    time_ms = c(0, 10, 20, 30),
    LPOGX = c(0.2, 0.3, 0.4, 0.5),
    LPOGY = c(0.5, 0.5, 0.5, 0.5),
    RPOGX = c(0.2, 0.3, 0.4, 0.5),
    RPOGY = c(0.5, 0.5, 0.5, 0.5),
    LPD = c(3.0, 3.1, -1, 3.3),
    RPD = c(3.0, 3.1, 3.2, 3.3),
    LPV = c(1, 0, 1, 1),
    RPV = c(1, 1, 1, 1),
    blink_left = c(0, 0, 0, 1),
    blink_right = c(0, 0, 0, 0)
  )

  preserved <- prepare_gazepoint_gazer_input(
    data,
    invalid_pupil_values = -1,
    mask_invalid = FALSE
  )

  expect_equal(
    preserved$data$pupil_left[2],
    3.1
  )

  expect_equal(
    preserved$row_audit$invalid_validity_count[2],
    1
  )

  expect_equal(
    preserved$row_audit$explicit_invalid_channel_count[3],
    1
  )

  expect_equal(
    preserved$row_audit$blink_count[4],
    1
  )

  masked <- prepare_gazepoint_gazer_input(
    data,
    invalid_pupil_values = -1,
    mask_invalid = TRUE
  )

  expect_true(
    is.na(masked$data$x_left[2])
  )

  expect_true(
    is.na(masked$data$pupil_left[2])
  )

  expect_true(
    is.na(masked$data$pupil_left[3])
  )

  expect_true(
    is.na(masked$data$x_left[4])
  )
})

test_that("sample counters require and use a sampling rate", {
  data <- data.frame(
    participant = rep("P01", 4),
    trial = rep("T01", 4),
    CNT = 100:103,
    gaze_x = c(0.2, 0.3, 0.4, 0.5),
    gaze_y = c(0.5, 0.5, 0.5, 0.5)
  )

  expect_error(
    prepare_gazepoint_gazer_input(
      data
    ),
    "sampling_rate_hz"
  )

  out <- prepare_gazepoint_gazer_input(
    data,
    sampling_rate_hz = 50,
    rezero_time = TRUE
  )

  expect_equal(
    out$data$time,
    c(0, 20, 40, 60)
  )

  expect_equal(
    out$sampling$effective_sampling_rate_hz,
    50
  )
})

test_that("subject-trial-time rows must be unique", {
  data <- data.frame(
    participant = rep("P01", 3),
    trial = rep("T01", 3),
    time_ms = c(0, 10, 10),
    gaze_x = c(0.2, 0.3, 0.4),
    gaze_y = c(0.5, 0.5, 0.5)
  )

  expect_error(
    prepare_gazepoint_gazer_input(
      data
    ),
    "must be unique"
  )
})

test_that("irregular sampling is rejected or retained explicitly", {
  data <- data.frame(
    participant = rep("P01", 4),
    trial = rep("T01", 4),
    time_ms = c(0, 10, 20, 50),
    gaze_x = c(0.2, 0.3, 0.4, 0.5),
    gaze_y = c(0.5, 0.5, 0.5, 0.5)
  )

  expect_error(
    prepare_gazepoint_gazer_input(
      data
    ),
    "Irregular"
  )

  out <- prepare_gazepoint_gazer_input(
    data,
    irregular = "allow"
  )

  expect_equal(
    out$sampling$irregular_interval_count,
    1
  )

  expect_equal(
    out$manifest$summary$irregular_group_count,
    1
  )
})

test_that("rows are ordered and provenance is retained", {
  data <- data.frame(
    participant = rep("P01", 4),
    trial = rep("T01", 4),
    time_ms = c(30, 0, 20, 10),
    gaze_x = c(0.5, 0.2, 0.4, 0.3),
    gaze_y = c(0.5, 0.5, 0.5, 0.5)
  )

  out <- prepare_gazepoint_gazer_input(
    data
  )

  expect_equal(
    out$data$time,
    c(0, 10, 20, 30)
  )

  expect_true(
    out$manifest$summary$source_order_changed
  )

  expect_equal(
    sort(out$row_audit$prepared_row),
    1:4
  )
})

test_that("other columns are retained", {
  data <- data.frame(
    participant = rep("P01", 4),
    trial = rep(c("T01", "T02"), each = 2),
    time_ms = rep(c(0, 10), 2),
    gaze_x = c(0.2, 0.3, 0.4, 0.5),
    gaze_y = c(0.5, 0.5, 0.5, 0.5),
    Condition = rep(c("A", "B"), each = 2),
    AOI = c("left", "right", "left", "right")
  )

  out <- prepare_gazepoint_gazer_input(
    data,
    other_cols = c(
      "Condition",
      "AOI"
    )
  )

  expect_true(
    all(
      c(
        "Condition",
        "AOI"
      ) %in% names(out$data)
    )
  )

  expect_equal(
    out$settings$other_cols,
    c(
      "Condition",
      "AOI"
    )
  )
})

test_that("an actual gazeR table can be requested", {
  namespace <- tryCatch(
    getNamespace("gazer"),
    error = function(e) NULL
  )

  if (is.null(namespace)) {
    skip("The GitHub-hosted gazeR package is not installed.")
  }

  data <- data.frame(
    participant = rep("P01", 4),
    trial = rep("T01", 4),
    time_ms = c(0, 10, 20, 30),
    gaze_x = c(0.2, 0.3, 0.4, 0.5),
    gaze_y = c(0.5, 0.5, 0.5, 0.5),
    pupil = c(3.0, 3.1, 3.2, 3.3)
  )

  out <- prepare_gazepoint_gazer_input(
    data,
    create_object = TRUE
  )

  expect_true(
    is.data.frame(out$object)
  )

  expect_true(
    out$manifest$summary$object_created
  )

  expect_equal(
    out$settings$gazer_package$version,
    "0.2.4"
  )
})

test_that("input validation is explicit", {
  expect_error(
    prepare_gazepoint_gazer_input(
      data.frame()
    ),
    "at least one sample"
  )

  missing_trial <- data.frame(
    participant = rep("P01", 3),
    time_ms = c(0, 10, 20),
    gaze_x = c(0.2, 0.3, 0.4),
    gaze_y = c(0.5, 0.5, 0.5)
  )

  expect_error(
    prepare_gazepoint_gazer_input(
      missing_trial
    ),
    "trial"
  )

  incomplete_gaze <- data.frame(
    participant = rep("P01", 3),
    trial = rep("T01", 3),
    time_ms = c(0, 10, 20),
    gaze_x = c(0.2, 0.3, 0.4)
  )

  expect_error(
    prepare_gazepoint_gazer_input(
      incomplete_gaze
    ),
    "incomplete"
  )

  nonnumeric <- data.frame(
    participant = rep("P01", 3),
    trial = rep("T01", 3),
    time_ms = c(0, 10, 20),
    gaze_x = c("0.2", "0.3", "0.4"),
    gaze_y = c(0.5, 0.5, 0.5)
  )

  expect_error(
    prepare_gazepoint_gazer_input(
      nonnumeric
    ),
    "must be numeric"
  )
})
