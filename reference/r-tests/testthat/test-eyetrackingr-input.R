test_that("categorical AOIs are converted to logical eyetrackingR columns", {
  data <- data.frame(
    participant = rep("P01", 5),
    trial = rep("T01", 5),
    time_s = c(0, 0.1, 0.2, 0.3, 0.4),
    gaze_x = c(0.2, 0.5, 0.8, NA, 0.4),
    gaze_y = c(0.5, 0.5, 0.5, NA, 0.6),
    AOI = c(
      "left",
      "center",
      "right",
      NA,
      "outside"
    )
  )

  out <- prepare_gazepoint_eyetrackingr_input(
    data
  )

  expect_s3_class(
    out,
    "gazepoint_eyetrackingr_input"
  )

  expect_equal(
    names(out$data)[1:4],
    c(
      "ParticipantName",
      "Trial",
      "Time_ms",
      "TrackLoss"
    )
  )

  expect_equal(
    out$data$Time_ms,
    c(0, 100, 200, 300, 400)
  )

  expect_named(
    out$data[5:7],
    c("left", "center", "right")
  )

  expect_true(out$data$TrackLoss[4])
  expect_false(out$data$left[4])
  expect_true(out$row_audit$non_aoi_look[5])
})

test_that("validity flags contribute conservatively to track loss", {
  data <- data.frame(
    participant = rep("P01", 4),
    trial = rep("T01", 4),
    time_ms = c(0, 10, 20, 30),
    BPOGX = c(0.2, 0.3, 0.4, 0.5),
    BPOGY = c(0.5, 0.5, 0.5, 0.5),
    BPOGV = c(1, 0, 1, NA),
    AOI = c("left", "left", "right", "right")
  )

  out <- prepare_gazepoint_eyetrackingr_input(
    data
  )

  expect_equal(
    out$data$TrackLoss,
    c(FALSE, TRUE, FALSE, TRUE)
  )

  expect_true(
    out$row_audit$invalid_validity[2]
  )

  expect_true(
    out$row_audit$missing_validity_value[4]
  )
})

test_that("explicit track-loss columns are supported", {
  data <- data.frame(
    subject = rep("S01", 4),
    trial_id = rep("A", 4),
    time_ms = c(0, 20, 40, 60),
    TrackLoss = c(0, 1, 0, 0),
    AOI = c("target", "target", "distractor", "outside")
  )

  out <- prepare_gazepoint_eyetrackingr_input(
    data,
    x_col = NULL,
    y_col = NULL
  )

  expect_equal(
    out$data$TrackLoss,
    c(FALSE, TRUE, FALSE, FALSE)
  )

  expect_true(out$data$target[1])
  expect_false(out$data$target[2])
  expect_true(out$row_audit$non_aoi_look[4])
})

test_that("existing AOI columns are converted and overlap is audited", {
  data <- data.frame(
    participant = rep("P01", 3),
    trial = rep("T01", 3),
    time_ms = c(0, 10, 20),
    TrackLoss = FALSE,
    Target = c(1, 0, 1),
    Distractor = c(0, 1, 0)
  )

  out <- prepare_gazepoint_eyetrackingr_input(
    data,
    aoi_cols = c(
      "Target",
      "Distractor"
    )
  )

  expect_type(out$data$Target, "logical")
  expect_type(out$data$Distractor, "logical")

  overlapping <- data
  overlapping$Distractor[1] <- 1

  expect_error(
    prepare_gazepoint_eyetrackingr_input(
      overlapping,
      aoi_cols = c(
        "Target",
        "Distractor"
      )
    ),
    "More than one AOI"
  )

  allowed <- prepare_gazepoint_eyetrackingr_input(
    overlapping,
    aoi_cols = c(
      "Target",
      "Distractor"
    ),
    allow_aoi_overlap = TRUE
  )

  expect_equal(
    allowed$row_audit$aoi_membership_count[1],
    2
  )
})

test_that("sample counters require and use a sampling rate", {
  data <- data.frame(
    participant = rep("P01", 4),
    trial = rep("T01", 4),
    CNT = 100:103,
    TrackLoss = FALSE,
    AOI = rep("target", 4)
  )

  expect_error(
    prepare_gazepoint_eyetrackingr_input(
      data
    ),
    "sampling_rate_hz"
  )

  out <- prepare_gazepoint_eyetrackingr_input(
    data,
    sampling_rate_hz = 50,
    rezero_time = TRUE
  )

  expect_equal(
    out$data$Time_ms,
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
    time_ms = c(0, 10, 10),
    TrackLoss = FALSE,
    AOI = c("left", "left", "right")
  )

  expect_error(
    prepare_gazepoint_eyetrackingr_input(
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
    TrackLoss = FALSE,
    AOI = rep("target", 4)
  )

  expect_error(
    prepare_gazepoint_eyetrackingr_input(
      data
    ),
    "Irregular"
  )

  out <- prepare_gazepoint_eyetrackingr_input(
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

test_that("rows are sorted and source provenance is retained", {
  data <- data.frame(
    participant = rep("P01", 4),
    trial = rep("T01", 4),
    time_ms = c(30, 0, 20, 10),
    TrackLoss = FALSE,
    AOI = c("right", "left", "right", "left")
  )

  out <- prepare_gazepoint_eyetrackingr_input(
    data
  )

  expect_equal(
    out$data$Time_ms,
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

test_that("item and predictor columns are retained", {
  data <- data.frame(
    participant = rep("P01", 4),
    trial = rep(c("T01", "T02"), each = 2),
    time_ms = rep(c(0, 10), 2),
    TrackLoss = FALSE,
    AOI = c("target", "other", "target", "other"),
    Item = rep(c("word1", "word2"), each = 2),
    Condition = rep(c("A", "B"), each = 2)
  )

  out <- prepare_gazepoint_eyetrackingr_input(
    data,
    item_cols = "Item",
    predictor_cols = "Condition"
  )

  expect_true(
    all(c("Item", "Condition") %in% names(out$data))
  )

  expect_equal(
    out$settings$item_cols,
    "Item"
  )

  expect_equal(
    out$settings$predictor_cols,
    "Condition"
  )
})

test_that("an actual eyetrackingR object can be requested", {
  skip_if_not_installed("eyetrackingR")

  data <- data.frame(
    participant = rep("P01", 4),
    trial = rep("T01", 4),
    time_ms = c(0, 10, 20, 30),
    TrackLoss = FALSE,
    AOI = c("target", "target", "other", "other")
  )

  out <- prepare_gazepoint_eyetrackingr_input(
    data,
    create_object = TRUE
  )

  expect_false(is.null(out$object))
  expect_true(out$manifest$summary$object_created)
})

test_that("input validation is explicit", {
  expect_error(
    prepare_gazepoint_eyetrackingr_input(
      data.frame()
    ),
    "at least one sample"
  )

  missing_aoi <- data.frame(
    participant = rep("P01", 3),
    trial = rep("T01", 3),
    time_ms = c(0, 10, 20),
    TrackLoss = FALSE
  )

  expect_error(
    prepare_gazepoint_eyetrackingr_input(
      missing_aoi
    ),
    "AOI"
  )

  bad_time <- data.frame(
    participant = rep("P01", 3),
    trial = rep("T01", 3),
    time_ms = c("0", "10", "20"),
    TrackLoss = FALSE,
    AOI = "target"
  )

  expect_error(
    prepare_gazepoint_eyetrackingr_input(
      bad_time
    ),
    "numeric"
  )

  bad_binary <- data.frame(
    participant = rep("P01", 3),
    trial = rep("T01", 3),
    time_ms = c(0, 10, 20),
    TrackLoss = FALSE,
    Target = c(0, 2, 1)
  )

  expect_error(
    prepare_gazepoint_eyetrackingr_input(
      bad_binary,
      aoi_cols = "Target"
    ),
    "only 0, 1"
  )
})
