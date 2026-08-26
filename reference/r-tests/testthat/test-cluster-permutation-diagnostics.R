test_that("simulate_gazepoint_cluster_timecourse_data creates a complete two-condition grid", {
  dat <- simulate_gazepoint_cluster_timecourse_data(
    n_subjects = 6,
    n_time = 20,
    effect_start = 8,
    effect_end = 12,
    seed = 123
  )

  expect_s3_class(dat, "data.frame")
  expect_equal(nrow(dat), 6 * 2 * 20)
  expect_true(all(c("subject", "condition", "time", "value", "true_effect") %in% names(dat)))
  expect_equal(length(unique(dat$subject)), 6)
  expect_equal(length(unique(dat$condition)), 2)
  expect_equal(length(unique(dat$time)), 20)
})

test_that("audit_gazepoint_timecourse_grid detects complete and incomplete grids", {
  dat <- simulate_gazepoint_cluster_timecourse_data(
    n_subjects = 5,
    n_time = 12,
    seed = 123
  )

  audit <- audit_gazepoint_timecourse_grid(
    dat,
    subject = subject,
    condition = condition,
    time = time,
    value = value
  )

  expect_s3_class(audit, "gazepoint_timecourse_grid_audit")
  expect_true(audit$summary$complete_grid)
  expect_equal(audit$summary$n_subjects, 5)
  expect_equal(audit$summary$n_conditions, 2)
  expect_equal(audit$summary$n_time_bins, 12)

  dat_missing <- dat[-1, ]

  audit_missing <- audit_gazepoint_timecourse_grid(
    dat_missing,
    subject = subject,
    condition = condition,
    time = time,
    value = value
  )

  expect_false(audit_missing$summary$complete_grid)
  expect_gt(audit_missing$summary$missing_cells, 0)
})

test_that("diagnose_gazepoint_cluster_design returns design checks", {
  dat <- simulate_gazepoint_cluster_timecourse_data(
    n_subjects = 10,
    n_time = 15,
    seed = 123
  )

  diag <- diagnose_gazepoint_cluster_design(
    dat,
    subject = subject,
    condition = condition,
    time = time,
    value = value
  )

  expect_s3_class(diag, "gazepoint_cluster_design_diagnostic")
  expect_true(is.data.frame(diag$checks))
  expect_true(diag$passed)
  expect_true("two_conditions" %in% diag$checks$check)
  expect_true("complete_grid" %in% diag$checks$check)
})

test_that("cluster reporting and null-distribution plotting work with a real result", {
  dat <- simulate_gazepoint_cluster_timecourse_data(
    n_subjects = 10,
    n_time = 30,
    effect_start = 12,
    effect_end = 20,
    effect_size = 0.9,
    noise_sd = 0.25,
    seed = 123
  )

  result <- run_gazepoint_cluster_permutation(
    dat,
    outcome_col = "value",
    time_col = "time",
    condition_col = "condition",
    participant_col = "subject",
    n_permutations = 49,
    cluster_forming_alpha = 0.05,
    seed = 123
  )

  report <- report_gazepoint_cluster_permutation(result)

  expect_s3_class(report, "gazepoint_cluster_report")
  expect_type(report$text, "character")
  expect_true(grepl("global null", report$text))
  expect_true(grepl("descriptively", report$text))

  p <- plot_gazepoint_cluster_null_distribution(result)

  expect_s3_class(p, "ggplot")
})

test_that("threshold sensitivity returns one summary row per threshold", {
  dat <- simulate_gazepoint_cluster_timecourse_data(
    n_subjects = 8,
    n_time = 25,
    effect_start = 10,
    effect_end = 16,
    effect_size = 0.8,
    noise_sd = 0.3,
    seed = 123
  )

  sensitivity <- run_gazepoint_cluster_threshold_sensitivity(
    dat,
    dv = value,
    time = time,
    condition = condition,
    subject = subject,
    thresholds = c(0.025, 0.05),
    n_permutations = 39,
    seed = 123
  )

  expect_s3_class(sensitivity, "gazepoint_cluster_threshold_sensitivity")
  expect_equal(nrow(sensitivity$summary), 2)
  expect_equal(sensitivity$summary$threshold, c(0.025, 0.05))
  expect_true(all(c("n_clusters", "min_p_value", "n_significant") %in% names(sensitivity$summary)))
})

test_that("export_gazepoint_cluster_results writes expected files", {
  dat <- simulate_gazepoint_cluster_timecourse_data(
    n_subjects = 8,
    n_time = 25,
    effect_start = 10,
    effect_end = 16,
    effect_size = 0.8,
    noise_sd = 0.3,
    seed = 123
  )

  result <- run_gazepoint_cluster_permutation(
    dat,
    outcome_col = "value",
    time_col = "time",
    condition_col = "condition",
    participant_col = "subject",
    n_permutations = 39,
    cluster_forming_alpha = 0.05,
    seed = 123
  )

  out_dir <- tempfile("gp_cluster_export_test_")

  exported <- export_gazepoint_cluster_results(
    result,
    path = out_dir,
    prefix = "test_cluster",
    overwrite = TRUE
  )

  expect_s3_class(exported, "data.frame")

  expected_files <- c(
    "test_cluster_clusters.csv",
    "test_cluster_timewise_statistics.csv",
    "test_cluster_null_distribution.csv",
    "test_cluster_parameters.csv",
    "test_cluster_report.txt"
  )

  expect_true(all(expected_files %in% list.files(out_dir)))
})
