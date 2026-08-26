test_that("prepare_gazepoint_timecourse_test_data creates a complete grid", {
  set.seed(101)

  raw <- expand.grid(
    participant_id = sprintf("P%02d", 1:6),
    condition_name = c("A", "B"),
    time_ms = 1:10,
    trial = 1:2,
    KEEP.OUT.ATTRS = FALSE,
    stringsAsFactors = FALSE
  )

  raw$signal <- rnorm(nrow(raw))

  prepared <- prepare_gazepoint_timecourse_test_data(
    data = raw,
    outcome_col = "signal",
    time_col = "time_ms",
    condition_col = "condition_name",
    participant_col = "participant_id",
    condition_a = "A",
    condition_b = "B"
  )

  expect_s3_class(prepared, "gazepoint_timecourse_test_data")
  expect_equal(nrow(prepared), 6 * 2 * 10)
  expect_true(all(c("participant", "condition", "time", "value") %in% names(prepared)))
})

test_that("run_gazepoint_cluster_permutation returns expected structure", {
  set.seed(102)

  dat <- expand.grid(
    participant = sprintf("P%02d", 1:8),
    condition = c("A", "B"),
    time = 1:30,
    KEEP.OUT.ATTRS = FALSE,
    stringsAsFactors = FALSE
  )

  dat$value <- rnorm(nrow(dat), 0, 0.4)

  result <- run_gazepoint_cluster_permutation(
    data = dat,
    outcome_col = "value",
    time_col = "time",
    condition_col = "condition",
    participant_col = "participant",
    condition_a = "A",
    condition_b = "B",
    n_permutations = 49,
    seed = 202
  )

  expect_s3_class(result, "gazepoint_cluster_permutation")
  expect_true(all(c("timewise", "clusters", "null_distribution", "settings") %in% names(result)))
  expect_equal(length(result$null_distribution), 49)
  expect_equal(result$settings$design, "within")
})

test_that("cluster permutation detects a strong synthetic within-subject effect", {
  set.seed(103)

  n_subjects <- 12
  times <- 1:60

  dat <- expand.grid(
    participant = sprintf("P%02d", seq_len(n_subjects)),
    condition = c("A", "B"),
    time = times,
    KEEP.OUT.ATTRS = FALSE,
    stringsAsFactors = FALSE
  )

  subject_shift <- rnorm(n_subjects, 0, 0.15)
  names(subject_shift) <- sprintf("P%02d", seq_len(n_subjects))

  effect_window <- dat$time >= 25 & dat$time <= 38 & dat$condition == "A"

  dat$value <- subject_shift[dat$participant] +
    rnorm(nrow(dat), 0, 0.18) +
    ifelse(effect_window, 1.20, 0)

  result <- run_gazepoint_cluster_permutation(
    data = dat,
    outcome_col = "value",
    time_col = "time",
    condition_col = "condition",
    participant_col = "participant",
    condition_a = "A",
    condition_b = "B",
    n_permutations = 199,
    cluster_forming_alpha = 0.05,
    cluster_alpha = 0.05,
    seed = 303
  )

  clusters <- summarize_gazepoint_time_clusters(result)

  expect_true(nrow(clusters) >= 1)
  expect_true(any(clusters$significant))
  expect_true(any(clusters$start_time <= 30 & clusters$end_time >= 33))
})

test_that("cluster permutation handles null synthetic data conservatively for fixed seed", {
  set.seed(104)

  dat <- expand.grid(
    participant = sprintf("P%02d", 1:10),
    condition = c("A", "B"),
    time = 1:40,
    KEEP.OUT.ATTRS = FALSE,
    stringsAsFactors = FALSE
  )

  dat$value <- rnorm(nrow(dat), 0, 0.35)

  result <- run_gazepoint_cluster_permutation(
    data = dat,
    outcome_col = "value",
    time_col = "time",
    condition_col = "condition",
    participant_col = "participant",
    condition_a = "A",
    condition_b = "B",
    n_permutations = 99,
    seed = 404
  )

  clusters <- summarize_gazepoint_time_clusters(result)

  if (nrow(clusters)) {
    expect_false(any(clusters$significant))
  } else {
    expect_equal(nrow(clusters), 0)
  }
})

test_that("plot_gazepoint_cluster_permutation returns a ggplot object", {
  skip_if_not_installed("ggplot2")

  set.seed(105)

  dat <- expand.grid(
    participant = sprintf("P%02d", 1:8),
    condition = c("A", "B"),
    time = 1:25,
    KEEP.OUT.ATTRS = FALSE,
    stringsAsFactors = FALSE
  )

  dat$value <- rnorm(nrow(dat), 0, 0.25) +
    ifelse(dat$condition == "A" & dat$time >= 10 & dat$time <= 15, 1.0, 0)

  result <- run_gazepoint_cluster_permutation(
    data = dat,
    outcome_col = "value",
    time_col = "time",
    condition_col = "condition",
    participant_col = "participant",
    condition_a = "A",
    condition_b = "B",
    n_permutations = 49,
    seed = 505
  )

  p <- plot_gazepoint_cluster_permutation(result)

  expect_s3_class(p, "ggplot")
})
