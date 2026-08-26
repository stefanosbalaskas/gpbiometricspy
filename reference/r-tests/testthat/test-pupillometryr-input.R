test_that("binocular Gazepoint pupil data are prepared", {
  data <- data.frame(
    participant = rep("P01", 4),
    trial = rep("T01", 4),
    condition = rep("target", 4),
    time_s = c(0, 0.1, 0.2, 0.3),
    pupil_left = c(3.1, 3.2, NA, 3.4),
    pupil_right = c(3.0, 3.1, NA, 3.3)
  )

  out <- prepare_gazepoint_pupillometryr_input(
    data
  )

  expect_s3_class(
    out,
    "gazepoint_pupillometryr_input"
  )

  expect_equal(
    names(out$data)[1:4],
    c(
      "Subject",
      "Trial",
      "Time",
      "Condition"
    )
  )

  expect_equal(
    out$data$Time,
    c(0, 100, 200, 300)
  )

  expect_true(
    all(
      c(
        "Pupil_Left",
        "Pupil_Right",
        "Pupil_Mean"
      ) %in% names(out$data)
    )
  )

  expect_equal(
    out$data$Pupil_Mean[1],
    3.05
  )

  expect_true(
    is.na(out$data$Pupil_Mean[3])
  )
})

test_that("single pupil columns are supported", {
  data <- data.frame(
    subject = rep("S01", 3),
    trial_id = rep("A", 3),
    Type = rep("easy", 3),
    time_ms = c(0, 20, 40),
    BPD = c(3.0, 3.1, 3.2)
  )

  out <- prepare_gazepoint_pupillometryr_input(
    data
  )

  expect_true(
    "Pupil" %in% names(out$data)
  )

  expect_false(
    "Pupil_Mean" %in% names(out$data)
  )

  expect_equal(
    out$data$Pupil,
    data$BPD
  )
})

test_that("validity and blink columns are audited and optionally masked", {
  data <- data.frame(
    participant = rep("P01", 4),
    trial = rep("T01", 4),
    condition = rep("A", 4),
    time_ms = c(0, 10, 20, 30),
    LPD = c(3.0, 3.1, -1, 3.3),
    RPD = c(3.0, 3.1, 3.2, 3.3),
    LPV = c(1, 0, 1, 1),
    RPV = c(1, 1, 1, 1),
    left_blink = c(0, 0, 0, 1),
    right_blink = c(0, 0, 0, 0)
  )

  preserved <- prepare_gazepoint_pupillometryr_input(
    data,
    invalid_pupil_values = -1,
    validity_cols = c("LPV", "RPV"),
    blink_cols = c(
      "left_blink",
      "right_blink"
    ),
    mask_invalid = FALSE
  )

  expect_equal(
    preserved$data$Pupil_Left[2],
    3.1
  )

  expect_equal(
    preserved$row_audit$invalid_validity_count[2],
    1
  )

  expect_equal(
    preserved$row_audit$explicit_invalid_count[3],
    1
  )

  expect_equal(
    preserved$row_audit$blink_count[4],
    1
  )

  masked <- prepare_gazepoint_pupillometryr_input(
    data,
    invalid_pupil_values = -1,
    validity_cols = c("LPV", "RPV"),
    blink_cols = c(
      "left_blink",
      "right_blink"
    ),
    mask_invalid = TRUE
  )

  expect_true(
    is.na(masked$data$Pupil_Left[2])
  )

  expect_true(
    is.na(masked$data$Pupil_Left[3])
  )

  expect_true(
    is.na(masked$data$Pupil_Left[4])
  )
})

test_that("one shared validity or blink column can apply to all pupils", {
  data <- data.frame(
    participant = rep("P01", 3),
    trial = rep("T01", 3),
    condition = rep("A", 3),
    time_ms = c(0, 10, 20),
    LPD = c(3.0, 3.1, 3.2),
    RPD = c(3.0, 3.1, 3.2),
    valid = c(1, 0, 1),
    blink = c(0, 0, 1)
  )

  out <- prepare_gazepoint_pupillometryr_input(
    data,
    validity_cols = "valid",
    blink_cols = "blink",
    mask_invalid = TRUE
  )

  expect_true(
    is.na(out$data$Pupil_Left[2])
  )

  expect_true(
    is.na(out$data$Pupil_Right[2])
  )

  expect_true(
    is.na(out$data$Pupil_Left[3])
  )

  expect_true(
    is.na(out$data$Pupil_Right[3])
  )
})

test_that("sample counters require and use a sampling rate", {
  data <- data.frame(
    participant = rep("P01", 4),
    trial = rep("T01", 4),
    condition = rep("A", 4),
    CNT = 100:103,
    LPD = c(3.0, 3.1, 3.2, 3.3)
  )

  expect_error(
    prepare_gazepoint_pupillometryr_input(
      data
    ),
    "sampling_rate_hz"
  )

  out <- prepare_gazepoint_pupillometryr_input(
    data,
    sampling_rate_hz = 50,
    rezero_time = TRUE
  )

  expect_equal(
    out$data$Time,
    c(0, 20, 40, 60)
  )

  expect_equal(
    out$sampling$effective_sampling_rate_hz,
    50
  )
})

test_that("participant-trial-time rows must be unique", {
  data <- data.frame(
    participant = rep("P01", 3),
    trial = rep("T01", 3),
    condition = rep("A", 3),
    time_ms = c(0, 10, 10),
    LPD = c(3.0, 3.1, 3.2)
  )

  expect_error(
    prepare_gazepoint_pupillometryr_input(
      data
    ),
    "must be unique"
  )
})

test_that("condition must be constant within participant-trial", {
  data <- data.frame(
    participant = rep("P01", 3),
    trial = rep("T01", 3),
    condition = c("A", "B", "A"),
    time_ms = c(0, 10, 20),
    LPD = c(3.0, 3.1, 3.2)
  )

  expect_error(
    prepare_gazepoint_pupillometryr_input(
      data
    ),
    "Condition must be constant"
  )
})

test_that("irregular sampling is rejected or retained explicitly", {
  data <- data.frame(
    participant = rep("P01", 4),
    trial = rep("T01", 4),
    condition = rep("A", 4),
    time_ms = c(0, 10, 20, 50),
    LPD = c(3.0, 3.1, 3.2, 3.3)
  )

  expect_error(
    prepare_gazepoint_pupillometryr_input(
      data
    ),
    "Irregular"
  )

  out <- prepare_gazepoint_pupillometryr_input(
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

test_that("rows are ordered and source provenance is retained", {
  data <- data.frame(
    participant = rep("P01", 4),
    trial = rep("T01", 4),
    condition = rep("A", 4),
    time_ms = c(30, 0, 20, 10),
    LPD = c(3.3, 3.0, 3.2, 3.1)
  )

  out <- prepare_gazepoint_pupillometryr_input(
    data
  )

  expect_equal(
    out$data$Time,
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
    condition = rep(c("A", "B"), each = 2),
    time_ms = rep(c(0, 10), 2),
    LPD = c(3.0, 3.1, 3.2, 3.3),
    Item = rep(c("word1", "word2"), each = 2),
    Block = rep(c("one", "two"), each = 2)
  )

  out <- prepare_gazepoint_pupillometryr_input(
    data,
    other_cols = c("Item", "Block")
  )

  expect_true(
    all(
      c("Item", "Block") %in%
        names(out$data)
    )
  )

  expect_equal(
    out$settings$other_cols,
    c("Item", "Block")
  )
})

test_that("an actual PupillometryR object can be requested", {
  skip_if_not_installed("PupillometryR")

  data <- data.frame(
    participant = rep("P01", 4),
    trial = rep("T01", 4),
    condition = rep("A", 4),
    time_ms = c(0, 10, 20, 30),
    LPD = c(3.0, 3.1, 3.2, 3.3),
    RPD = c(3.0, 3.1, 3.2, 3.3)
  )

  out <- prepare_gazepoint_pupillometryr_input(
    data,
    create_object = TRUE
  )

  expect_false(
    is.null(out$object)
  )

  expect_true(
    out$manifest$summary$object_created
  )
})

test_that("input validation is explicit", {
  expect_error(
    prepare_gazepoint_pupillometryr_input(
      data.frame()
    ),
    "at least one sample"
  )

  missing_condition <- data.frame(
    participant = rep("P01", 3),
    trial = rep("T01", 3),
    time_ms = c(0, 10, 20),
    LPD = c(3.0, 3.1, 3.2)
  )

  expect_error(
    prepare_gazepoint_pupillometryr_input(
      missing_condition
    ),
    "condition"
  )

  bad_time <- data.frame(
    participant = rep("P01", 3),
    trial = rep("T01", 3),
    condition = rep("A", 3),
    time_ms = c("0", "10", "20"),
    LPD = c(3.0, 3.1, 3.2)
  )

  expect_error(
    prepare_gazepoint_pupillometryr_input(
      bad_time
    ),
    "numeric"
  )

  no_pupil <- data.frame(
    participant = rep("P01", 3),
    trial = rep("T01", 3),
    condition = rep("A", 3),
    time_ms = c(0, 10, 20)
  )

  expect_error(
    prepare_gazepoint_pupillometryr_input(
      no_pupil
    ),
    "pupil column"
  )
})
