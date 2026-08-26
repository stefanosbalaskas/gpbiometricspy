test_that("advanced cluster guardrails fail safely", {
  expect_error(
    run_gazepoint_cluster_permutation_anova(),
    "not implemented"
  )

  expect_error(
    run_gazepoint_cluster_permutation_lmer(),
    "not implemented"
  )

  expect_error(
    run_gazepoint_tfce(),
    "not implemented"
  )

  expect_error(
    run_gazepoint_multidimensional_cluster_permutation(),
    "not implemented"
  )

  expect_error(
    estimate_gazepoint_cluster_onset(),
    "not implemented"
  )

  expect_error(
    estimate_gazepoint_cluster_offset(),
    "not implemented"
  )

  expect_error(
    run_gazepoint_cluster_permutation_covariate_adjusted(),
    "not implemented"
  )

  expect_error(
    run_gazepoint_cluster_permutation_parallel(),
    "not implemented"
  )
})

test_that("MNE cluster export returns long data, difference matrix, and metadata", {
  dat <- simulate_gazepoint_cluster_timecourse_data(
    n_subjects = 5,
    n_time = 10,
    effect_start = 4,
    effect_end = 7,
    seed = 123
  )

  exported <- export_gazepoint_mne_cluster_input(
    dat,
    outcome_col = value,
    time_col = time,
    condition_col = condition,
    participant_col = subject
  )

  expect_type(exported, "list")
  expect_true(all(c("long", "difference_matrix", "metadata") %in% names(exported)))
  expect_s3_class(exported$long, "data.frame")
  expect_s3_class(exported$difference_matrix, "data.frame")
  expect_s3_class(exported$metadata, "data.frame")
  expect_equal(nrow(exported$difference_matrix), 5)
})

test_that("permuco and permutes exports return long data and metadata", {
  dat <- simulate_gazepoint_cluster_timecourse_data(
    n_subjects = 5,
    n_time = 10,
    seed = 123
  )

  permuco_export <- export_gazepoint_permuco_cluster_input(
    dat,
    outcome_col = value,
    time_col = time,
    condition_col = condition,
    participant_col = subject
  )

  permutes_export <- export_gazepoint_permutes_cluster_input(
    dat,
    outcome_col = value,
    time_col = time,
    condition_col = condition,
    participant_col = subject
  )

  expect_type(permuco_export, "list")
  expect_type(permutes_export, "list")

  expect_true(all(c("long", "metadata") %in% names(permuco_export)))
  expect_true(all(c("long", "metadata") %in% names(permutes_export)))

  expect_equal(nrow(permuco_export$long), 5 * 2 * 10)
  expect_equal(nrow(permutes_export$long), 5 * 2 * 10)
})

test_that("external export helpers write files when path is supplied", {
  dat <- simulate_gazepoint_cluster_timecourse_data(
    n_subjects = 5,
    n_time = 10,
    seed = 123
  )

  out_dir <- tempfile("gp_advanced_cluster_export_")

  written <- export_gazepoint_mne_cluster_input(
    dat,
    outcome_col = value,
    time_col = time,
    condition_col = condition,
    participant_col = subject,
    path = out_dir,
    overwrite = TRUE
  )

  expect_s3_class(written, "data.frame")
  expect_true(file.exists(file.path(out_dir, "gazepoint_mne_cluster_long.csv")))
  expect_true(file.exists(file.path(out_dir, "gazepoint_mne_cluster_difference_matrix.csv")))
  expect_true(file.exists(file.path(out_dir, "gazepoint_mne_cluster_metadata.csv")))
})
