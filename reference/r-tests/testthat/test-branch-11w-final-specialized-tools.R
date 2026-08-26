test_that("plot_gazepoint_eda_gram creates EDA-gram output", {
  time <- seq(0, 120, by = 1)
  eda <- sin(2 * pi * 0.1 * time) + rnorm(length(time), sd = 0.02)

  dat <- data.frame(
    participant = "p1",
    time = time,
    GSR_US = eda
  )

  out <- plot_gazepoint_eda_gram(
    dat,
    eda_col = "GSR_US",
    time_col = "time",
    group_cols = "participant",
    sampling_rate = 1,
    window_seconds = 30,
    step_seconds = 15,
    frequency_bins = 16,
    plot = FALSE
  )

  expect_s3_class(out, "gazepoint_eda_gram")
  expect_true(nrow(out$gram_table) > 0)
  expect_true("power" %in% names(out$gram_table))
})

test_that("extract_gazepoint_hrv_rcmse returns scale-wise entropy", {
  dat <- data.frame(
    participant = "p1",
    IBI = 0.8 + 0.04 * sin(seq(0, 10 * pi, length.out = 100)) +
      rnorm(100, sd = 0.005)
  )

  out <- extract_gazepoint_hrv_rcmse(
    dat,
    ibi_col = "IBI",
    group_cols = "participant",
    scales = 1:4,
    min_intervals = 20
  )

  expect_s3_class(out, "gazepoint_hrv_rcmse")
  expect_equal(nrow(out$rcmse_by_scale), 4)
  expect_true("mean_rcmse" %in% names(out$summary))
})

test_that("run_gazepoint_automated_statistics selects exploratory tests", {
  dat <- data.frame(
    condition = rep(c("A", "B", "C"), each = 12),
    feature_1 = c(rnorm(12, 0), rnorm(12, 1), rnorm(12, 1.5)),
    feature_2 = c(rnorm(12, 0), rnorm(12, 0), rnorm(12, 0.2))
  )

  out <- run_gazepoint_automated_statistics(
    dat,
    outcome_cols = c("feature_1", "feature_2"),
    group_col = "condition"
  )

  expect_s3_class(out, "gazepoint_automated_statistics")
  expect_equal(nrow(out$test_table), 2)
  expect_true("p_adjusted" %in% names(out$test_table))
})

test_that("analyze_gazepoint_ac_susceptance handles AC EDA components", {
  dat <- data.frame(
    participant = "p1",
    frequency = rep(c(10, 20), each = 20),
    conductance = rnorm(40, mean = 1, sd = 0.05),
    susceptance = rnorm(40, mean = 0.2, sd = 0.02)
  )

  out <- analyze_gazepoint_ac_susceptance(
    dat,
    conductance_col = "conductance",
    susceptance_col = "susceptance",
    frequency_col = "frequency",
    group_cols = "participant"
  )

  expect_s3_class(out, "gazepoint_ac_susceptance")
  expect_true("ac_eda_admittance_magnitude" %in% names(out$timeseries))
  expect_true(nrow(out$summary) >= 2)
})

test_that("run_gazepoint_online_design_optimization recommends a condition", {
  candidates <- data.frame(
    condition = c("attention", "no_attention", "control"),
    expected_utility = c(0.70, 0.55, 0.40),
    cost = c(0.05, 0.02, 0.01)
  )

  out <- run_gazepoint_online_design_optimization(
    candidates,
    condition_col = "condition",
    utility_col = "expected_utility",
    cost_col = "cost",
    previous_assignments = c("attention", "attention", "control")
  )

  expect_s3_class(out, "gazepoint_online_design_optimization")
  expect_equal(nrow(out$recommendation), 1)
  expect_true("optimization_rank" %in% names(out$ranked_candidates))
})
