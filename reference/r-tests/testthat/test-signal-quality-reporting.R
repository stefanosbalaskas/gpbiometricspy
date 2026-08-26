test_that("compute_gazepoint_signal_quality returns transparent segment metrics", {
  dat <- data.frame(
    participant = rep(c("P01", "P02"), each = 20),
    trial = rep(rep(1:2, each = 10), times = 2),
    condition = rep(c("A", "B"), each = 10, times = 2),
    pupil = c(
      seq(3.00, 3.09, length.out = 10),
      c(rep(NA_real_, 5), seq(3.10, 3.14, length.out = 5)),
      rep(2.90, 10),
      c(seq(3.00, 3.07, length.out = 8), 8, -1)
    ),
    gsr = c(
      seq(0.70, 0.79, length.out = 10),
      seq(0.80, 0.89, length.out = 10),
      c(rep(NA_real_, 6), seq(0.90, 0.93, length.out = 4)),
      rep(0.75, 10)
    )
  )

  quality <- compute_gazepoint_signal_quality(
    dat,
    signal_cols = c("pupil", "gsr"),
    group_cols = c("participant", "trial", "condition"),
    long_missing_run_threshold = 5,
    long_constant_run_threshold = 5
  )

  expect_s3_class(quality, "gazepoint_signal_quality")
  expect_equal(nrow(quality), 8)
  expect_true(all(c(
    "signal",
    "n_samples",
    "n_missing",
    "prop_missing",
    "finite_prop",
    "flatline_prop",
    "long_missing_run",
    "long_constant_run",
    "spike_count",
    "extreme_z_count"
  ) %in% names(quality)))

  p01_t2_pupil <- quality[
    quality$participant == "P01" &
      quality$trial == 2 &
      quality$signal == "pupil",
  ]

  expect_equal(p01_t2_pupil$n_samples, 10)
  expect_equal(p01_t2_pupil$n_missing, 5)
  expect_equal(p01_t2_pupil$prop_missing, 0.5)
  expect_equal(p01_t2_pupil$long_missing_run, 5)
  expect_true(p01_t2_pupil$contains_long_missing_run)

  p02_t1_pupil <- quality[
    quality$participant == "P02" &
      quality$trial == 1 &
      quality$signal == "pupil",
  ]

  expect_equal(p02_t1_pupil$long_constant_run, 10)
  expect_true(p02_t1_pupil$contains_long_constant_run)
})

test_that("compute_gazepoint_signal_quality validates inputs", {
  dat <- data.frame(
    participant = "P01",
    pupil = 3.1,
    label = "bad"
  )

  expect_error(
    compute_gazepoint_signal_quality(dat, signal_cols = "missing"),
    "not found"
  )

  expect_error(
    compute_gazepoint_signal_quality(dat, signal_cols = "label"),
    "numeric"
  )

  expect_error(
    compute_gazepoint_signal_quality(
      dat,
      signal_cols = "pupil",
      group_cols = "missing_group"
    ),
    "not found"
  )

  expect_error(
    compute_gazepoint_signal_quality(
      dat,
      signal_cols = "pupil",
      flatline_tolerance = -1
    ),
    "non-negative"
  )
})

test_that("classify_gazepoint_signal_quality applies visible rules without removing rows", {
  quality <- data.frame(
    participant = c("P01", "P02", "P03"),
    signal = c("pupil", "pupil", "gsr"),
    n_samples = c(100, 100, 100),
    prop_missing = c(0.00, 0.30, 0.70),
    finite_prop = c(1.00, 0.70, 0.30),
    flatline_prop = c(0.00, 0.10, 0.10),
    long_missing_run = c(0, 12, 60),
    long_constant_run = c(0, 0, 0),
    spike_count = c(0, 0, 0),
    extreme_z_count = c(0, 0, 0)
  )

  classified <- classify_gazepoint_signal_quality(quality)

  expect_s3_class(classified, "gazepoint_signal_quality_classification")
  expect_equal(nrow(classified), nrow(quality))
  expect_equal(
    classified$quality_label,
    c("pass", "review", "exclude_candidate")
  )
  expect_true("failing_rules" %in% names(classified))
  expect_true("quality_warnings" %in% names(classified))
  expect_true(length(attr(classified, "rules")) > 0)
})

test_that("classify_gazepoint_signal_quality accepts user-defined rules", {
  quality <- data.frame(
    signal = "pupil",
    n_samples = 100,
    prop_missing = 0.15,
    finite_prop = 0.85,
    flatline_prop = 0.00,
    long_missing_run = 0,
    long_constant_run = 0,
    spike_count = 0,
    extreme_z_count = 0
  )

  classified <- classify_gazepoint_signal_quality(
    quality,
    rules = list(prop_missing_review_at_or_above = 0.10)
  )

  expect_equal(classified$quality_label, "review")
  expect_match(classified$failing_rules, "Missingness review threshold")

  expect_error(
    classify_gazepoint_signal_quality(
      quality,
      rules = list(prop_missing_review_at_or_above = "bad")
    ),
    "single finite numeric"
  )
})

test_that("summarize_gazepoint_signal_quality returns reporting summaries", {
  quality <- data.frame(
    signal = c("pupil", "pupil", "gsr"),
    condition = c("A", "B", "A"),
    n_samples = c(10, 20, 30),
    prop_missing = c(0.0, 0.2, 0.5),
    finite_prop = c(1.0, 0.8, 0.5),
    flatline_prop = c(0.0, 0.1, 0.2),
    long_missing_run = c(0, 3, 6),
    long_constant_run = c(0, 4, 8),
    spike_count = c(0, 1, 2),
    extreme_z_count = c(0, 1, 2),
    quality_label = c("pass", "review", "exclude_candidate")
  )

  summary_signal <- summarize_gazepoint_signal_quality(quality, by = "signal")
  summary_condition <- summarize_gazepoint_signal_quality(
    quality,
    by = c("signal", "condition")
  )

  expect_equal(nrow(summary_signal), 2)
  expect_equal(nrow(summary_condition), 3)
  expect_true(all(c(
    "n_segments",
    "n_samples_total",
    "prop_missing_mean",
    "pass_n",
    "review_n",
    "exclude_candidate_n"
  ) %in% names(summary_signal)))

  expect_error(
    summarize_gazepoint_signal_quality(quality, by = "missing"),
    "not found"
  )
})

test_that("plot_gazepoint_signal_quality returns ggplot objects", {
  skip_if_not_installed("ggplot2")

  quality <- data.frame(
    participant = c("P01", "P02", "P03"),
    signal = c("pupil", "pupil", "gsr"),
    prop_missing = c(0.0, 0.2, 0.5),
    quality_label = c("pass", "review", "exclude_candidate")
  )

  p_metric <- plot_gazepoint_signal_quality(
    quality,
    metric = "prop_missing",
    x = "participant",
    colour = "quality_label"
  )

  p_label <- plot_gazepoint_signal_quality(
    quality,
    metric = "quality_label",
    x = "signal"
  )

  expect_s3_class(p_metric, "ggplot")
  expect_s3_class(p_label, "ggplot")

  expect_error(
    plot_gazepoint_signal_quality(quality, metric = "missing"),
    "not found"
  )
})
