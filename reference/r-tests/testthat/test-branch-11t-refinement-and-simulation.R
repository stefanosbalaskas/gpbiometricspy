test_that("optimize_gazepoint_cvxeda_tau selects a best tau per group", {
  time <- seq(0, 120, by = 0.5)
  eda <- 1 + 0.01 * sin(2 * pi * 0.05 * time) +
    0.05 * exp(-pmax(0, time - 20) / 3) +
    0.03 * exp(-pmax(0, time - 70) / 3)

  dat <- data.frame(
    participant = "p1",
    time = time,
    GSR_US = eda
  )

  out <- optimize_gazepoint_cvxeda_tau(
    dat,
    eda_col = "GSR_US",
    time_col = "time",
    group_cols = "participant",
    tau0_grid = c(2, 3, 4),
    sampling_rate = 2
  )

  expect_s3_class(out, "gazepoint_cvxeda_tau_optimization")
  expect_equal(nrow(out$best_tau), 1)
  expect_true(out$best_tau$tau0 %in% c(2, 3, 4))
  expect_true("rmse" %in% names(out$optimization_table))
})

test_that("test_gazepoint_hrv_nonlinearity returns surrogate test output", {
  set.seed(1)

  dat <- data.frame(
    participant = "p1",
    IBI = 0.8 + 0.04 * sin(seq(0, 8 * pi, length.out = 80)) +
      stats::rnorm(80, sd = 0.005)
  )

  out <- test_gazepoint_hrv_nonlinearity(
    dat,
    ibi_col = "IBI",
    group_cols = "participant",
    metric = "sample_entropy",
    n_surrogates = 9,
    surrogate_method = "shuffle",
    seed = 1
  )

  expect_s3_class(out, "gazepoint_hrv_nonlinearity_test")
  expect_equal(nrow(out$results), 1)
  expect_equal(nrow(out$surrogate_statistics), 9)
  expect_true("p_two_sided" %in% names(out$results))
})

test_that("simulate_gazepoint_biometrics returns synthetic data and ground truth", {
  out <- simulate_gazepoint_biometrics(
    n_seconds = 20,
    sampling_rate = 20,
    scr_onsets = c(5, 12),
    seed = 1
  )

  expect_s3_class(out, "gazepoint_biometrics_simulation")
  expect_true(nrow(out$data) > 0)
  expect_true("GSR_US" %in% names(out$data))
  expect_true("HRP" %in% names(out$data))
  expect_equal(nrow(out$ground_truth$scr_events), 2)
})

test_that("chunk_gazepoint_biometrics assigns fixed analysis chunks", {
  dat <- data.frame(
    participant = rep(c("p1", "p2"), each = 121),
    CNT = rep(seq(0, 120, by = 1), 2),
    GSR_US = stats::rnorm(242)
  )

  out <- chunk_gazepoint_biometrics(
    dat,
    time_col = "CNT",
    group_cols = "participant",
    chunk_seconds = 60,
    include_partial = TRUE
  )

  expect_s3_class(out, "gazepoint_biometric_chunks")
  expect_true("chunk_id" %in% names(out))
  expect_true("episode_id" %in% names(out))
  expect_true(nrow(attr(out, "chunk_summary")) >= 4)
})
