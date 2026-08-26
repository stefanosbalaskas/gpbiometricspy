test_that("detect_gazepoint_blinks flags implausible and missing pupil values", {
  d <- data.frame(
    participant = rep("P01", 8),
    time = seq_len(8),
    pupil_left = c(3.1, 3.2, 0, 3.2, 8.5, 3.1, NA, 3.0),
    stringsAsFactors = FALSE
  )

  x <- detect_gazepoint_blinks(
    d,
    pupil_cols = "pupil_left",
    id_cols = "participant",
    min_pupil = 0,
    max_pupil = 8,
    mask = TRUE
  )

  expect_true(inherits(x, "gazepoint_blink_audit"))
  expect_true(inherits(x, "gazepoint_qc_object"))
  expect_true("pupil_left_blink_flag" %in% names(x$data))
  expect_true("pupil_left_blink_clean" %in% names(x$data))

  expect_equal(x$summary$n_samples, 8)
  expect_equal(x$summary$n_flagged, 3)
  expect_equal(x$summary$prop_flagged, 3 / 8)

  expect_true(x$data$pupil_left_blink_flag[3])
  expect_true(x$data$pupil_left_blink_flag[5])
  expect_true(x$data$pupil_left_blink_flag[7])
  expect_true(is.na(x$data$pupil_left_blink_clean[3]))
  expect_true(is.na(x$data$pupil_left_blink_clean[5]))
  expect_true(is.na(x$data$pupil_left_blink_clean[7]))
})


test_that("detect_gazepoint_blinks can use change thresholds and extensions", {
  d <- data.frame(
    participant = c(rep("P01", 5), rep("P02", 5)),
    time = rep(seq_len(5), 2),
    pupil_left = c(3, 3.1, 6.5, 3.2, 3.1, 3, 3.1, 3.2, 3.3, 3.4),
    stringsAsFactors = FALSE
  )

  x <- detect_gazepoint_blinks(
    d,
    pupil_cols = "pupil_left",
    id_cols = "participant",
    min_pupil = 0,
    max_pupil = Inf,
    change_threshold = 2,
    extend_samples = 1,
    mask = FALSE
  )

  expect_true("pupil_left_blink_flag" %in% names(x$data))
  expect_false("pupil_left_blink_clean" %in% names(x$data))

  # The rapid jump in P01 is flagged and extended locally.
  expect_true(all(x$data$pupil_left_blink_flag[2:4]))
  expect_false(any(x$data$pupil_left_blink_flag[6:10]))
})


test_that("detect_gazepoint_blinks resolves pupil columns and validates inputs", {
  d <- data.frame(
    pupil_left = c(3, 0, 3.2),
    pupil_right = c(3.1, 3.2, NA),
    label = c("a", "b", "c"),
    stringsAsFactors = FALSE
  )

  x <- detect_gazepoint_blinks(d)
  expect_equal(x$summary$pupil_col, c("pupil_left", "pupil_right"))

  expect_error(
    detect_gazepoint_blinks(d, pupil_cols = "missing_col"),
    "not found"
  )

  expect_error(
    detect_gazepoint_blinks(d, pupil_cols = "label"),
    "numeric"
  )

  expect_error(
    detect_gazepoint_blinks(d, extend_samples = -1),
    "non-negative"
  )

  expect_error(
    detect_gazepoint_blinks(d, change_threshold = -1),
    "non-negative"
  )
})


test_that("smooth_gazepoint_pupil applies centred moving averages", {
  d <- data.frame(
    participant = rep("P01", 5),
    pupil_left = c(1, 2, 3, 4, 5),
    stringsAsFactors = FALSE
  )

  x <- smooth_gazepoint_pupil(
    d,
    pupil_cols = "pupil_left",
    id_cols = "participant",
    window = 3
  )

  expect_true(inherits(x, "gazepoint_pupil_smoothing"))
  expect_true(inherits(x, "gazepoint_qc_object"))
  expect_true("pupil_left_smooth" %in% names(x$data))
  expect_equal(x$data$pupil_left_smooth, c(1.5, 2, 3, 4, 4.5))
  expect_equal(x$summary$n_smoothed_nonmissing, 5)
})


test_that("smooth_gazepoint_pupil respects group boundaries", {
  d <- data.frame(
    participant = c("P01", "P01", "P02", "P02"),
    pupil_left = c(1, 3, 10, 20),
    stringsAsFactors = FALSE
  )

  x <- smooth_gazepoint_pupil(
    d,
    pupil_cols = "pupil_left",
    id_cols = "participant",
    window = 3
  )

  expect_equal(x$data$pupil_left_smooth, c(2, 2, 15, 15))
})


test_that("smooth_gazepoint_pupil validates smoothing settings", {
  d <- data.frame(pupil_left = c(1, 2, 3))

  expect_error(
    smooth_gazepoint_pupil(d, pupil_cols = "pupil_left", window = 2),
    "odd integer"
  )

  expect_error(
    smooth_gazepoint_pupil(d, pupil_cols = "pupil_left", window = 3, min_nonmissing = 4),
    "cannot be larger"
  )

  expect_error(
    smooth_gazepoint_pupil(d, pupil_cols = "missing_col"),
    "not found"
  )
})


test_that("plot_gazepoint_missingness returns a ggplot object", {
  testthat::skip_if_not_installed("ggplot2")

  d <- data.frame(
    participant = rep(c("P01", "P02"), each = 5),
    time = rep(seq_len(5), 2),
    pupil_left = c(3, NA, 3.2, 3.1, NA, 3.3, 3.2, NA, 3.1, 3.0),
    eda = c(1, 1.1, NA, 1.2, 1.3, 1.2, NA, 1.1, 1.0, 1.1),
    stringsAsFactors = FALSE
  )

  p <- plot_gazepoint_missingness(
    d,
    cols = c("pupil_left", "eda"),
    time_col = "time",
    id_col = "participant",
    max_points = 10
  )

  expect_true(inherits(p, "ggplot"))
})


test_that("plot_gazepoint_missingness validates plotting inputs", {
  testthat::skip_if_not_installed("ggplot2")

  d <- data.frame(
    time = 1:3,
    pupil_left = c(3, NA, 3.2)
  )

  expect_error(
    plot_gazepoint_missingness(d, cols = "missing_col"),
    "not found"
  )

  expect_error(
    plot_gazepoint_missingness(d, cols = "pupil_left", max_points = 0),
    "positive integer"
  )
})


test_that("validate_gazepoint_metadata passes clean metadata", {
  d <- data.frame(
    participant = c("P01", "P01", "P02", "P02"),
    trial = c(1, 2, 1, 2),
    time = c(1, 2, 1, 2),
    pupil_left = c(3.1, 3.2, 3.0, 3.1),
    stringsAsFactors = FALSE
  )

  x <- validate_gazepoint_metadata(
    d,
    required_cols = c("participant", "trial", "time"),
    expected_cols = "pupil_left",
    id_cols = "participant",
    time_col = "time",
    unique_cols = c("participant", "trial")
  )

  expect_true(inherits(x, "gazepoint_metadata_validation"))
  expect_true(inherits(x, "gazepoint_qc_object"))
  expect_equal(x$status, "pass")
  expect_equal(length(x$problems), 0)
  expect_equal(length(x$warnings), 0)
  expect_equal(x$summary$n_rows, 4)
})


test_that("validate_gazepoint_metadata reports missing required and expected columns", {
  d <- data.frame(
    participant = c("P01", "P02"),
    time = c(1, 2),
    stringsAsFactors = FALSE
  )

  x <- validate_gazepoint_metadata(
    d,
    required_cols = c("participant", "trial"),
    expected_cols = c("eda", "pupil_left"),
    id_cols = "participant",
    time_col = "time"
  )

  expect_equal(x$status, "review")
  expect_true(any(grepl("Missing required columns", x$problems)))
  expect_true(any(grepl("Missing expected columns", x$warnings)))
  expect_equal(x$summary$n_missing_required, 1)
  expect_equal(x$summary$n_missing_expected, 2)
})


test_that("validate_gazepoint_metadata reports ID, time, and duplicate-key problems", {
  d <- data.frame(
    participant = c("P01", "P01", "", "P02"),
    trial = c(1, 1, 1, 2),
    time = c(1, 0, 1, 2),
    stringsAsFactors = FALSE
  )

  x <- validate_gazepoint_metadata(
    d,
    required_cols = c("participant", "trial", "time"),
    id_cols = "participant",
    time_col = "time",
    unique_cols = c("participant", "trial")
  )

  expect_equal(x$status, "review")
  expect_true(any(grepl("Missing values detected in ID column", x$problems)))
  expect_true(any(grepl("not monotonically increasing", x$problems)))
  expect_true(any(grepl("Duplicate rows detected", x$problems)))
})


test_that("validate_gazepoint_metadata can allow missing IDs", {
  d <- data.frame(
    participant = c("P01", NA),
    time = c(1, 2),
    stringsAsFactors = FALSE
  )

  x <- validate_gazepoint_metadata(
    d,
    required_cols = c("participant", "time"),
    id_cols = "participant",
    time_col = "time",
    allow_missing_ids = TRUE
  )

  expect_equal(x$status, "pass")
  expect_equal(length(x$problems), 0)
})


test_that("print methods return objects invisibly", {
  d <- data.frame(
    participant = rep("P01", 3),
    time = 1:3,
    pupil_left = c(3, 0, 3.2),
    stringsAsFactors = FALSE
  )

  blink <- detect_gazepoint_blinks(d, pupil_cols = "pupil_left")
  smooth <- smooth_gazepoint_pupil(d, pupil_cols = "pupil_left", window = 3)
  meta <- validate_gazepoint_metadata(
    d,
    required_cols = c("participant", "time"),
    id_cols = "participant",
    time_col = "time"
  )

  expect_invisible(print(blink))
  expect_invisible(print(smooth))
  expect_invisible(print(meta))
})
