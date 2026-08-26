test_that("prepare_gazepoint_biometrics_lme_data prepares baseline-corrected model data", {
  dat <- data.frame(
    participant = rep(paste0("P", 1:6), each = 2),
    stimulus = rep(c("ad_a", "ad_b"), 6),
    trial = rep(1:2, 6),
    condition = rep(c("control", "claim"), 6),
    window_label = rep(c("baseline", "task"), 6),
    trial_order = seq_len(12),
    gsr_mean = seq(1, 2.1, length.out = 12),
    gsr_baseline = rep(seq(0.8, 1.3, length.out = 6), each = 2)
  )

  res <- prepare_gazepoint_biometrics_lme_data(
    dat,
    outcome_col = "gsr_mean",
    condition_cols = "condition",
    covariate_cols = "trial_order",
    participant_col = "participant",
    stimulus_col = "stimulus",
    window_col = "window_label",
    baseline_col = "gsr_baseline",
    baseline_correct = TRUE,
    scale_continuous = TRUE,
    min_rows = 4
  )

  expect_s3_class(res, "gazepoint_biometrics_lme_data")
  expect_equal(res$overview$status, "ready")
  expect_true("gsr_mean_baseline_corrected" %in% names(res$model_data))
  expect_true("z_trial_order" %in% names(res$model_data))
  expect_true(inherits(res$model_formula, "formula"))
  expect_equal(nrow(res$model_data), 12)
  expect_true(all(res$model_data$lme_complete_case))
})

test_that("prepare_gazepoint_biometrics_lme_data flags limited complete rows conservatively", {
  dat <- data.frame(
    participant = c("P1", "P1", "P2"),
    condition = c("a", "b", "a"),
    hr_mean = c(70, NA, 75)
  )

  res <- prepare_gazepoint_biometrics_lme_data(
    dat,
    outcome_col = "hr_mean",
    condition_cols = "condition",
    participant_col = "participant",
    min_rows = 3
  )

  expect_equal(res$overview$complete_model_rows, 2)
  expect_equal(res$overview$status, "limited_complete_rows")
  expect_equal(nrow(res$model_data), 2)
})

test_that("prepare_gazepoint_biometrics_lme_data keeps incomplete rows when requested", {
  dat <- data.frame(
    participant = c("P1", "P1", "P2"),
    condition = c("a", "b", "a"),
    hr_mean = c(70, NA, 75)
  )

  res <- prepare_gazepoint_biometrics_lme_data(
    dat,
    outcome_col = "hr_mean",
    condition_cols = "condition",
    participant_col = "participant",
    drop_missing = FALSE,
    min_rows = 1
  )

  expect_equal(nrow(res$model_data), 3)
  expect_equal(sum(res$model_data$lme_complete_case), 2)
})

test_that("prepare_gazepoint_biometrics_lme_data errors for missing outcome", {
  dat <- data.frame(
    participant = "P1",
    condition = "a",
    hr_mean = 70
  )

  expect_error(
    prepare_gazepoint_biometrics_lme_data(
      dat,
      outcome_col = "missing_outcome"
    ),
    "`outcome_col` was not found"
  )
})
