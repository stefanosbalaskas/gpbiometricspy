test_that("audit_gazepoint_eda_artifacts passes clean conductance data", {
  dat <- data.frame(
    source_file = "clean.csv",
    CNT = seq_len(60),
    GSR_US = seq(1, 2, length.out = 60)
  )

  res <- audit_gazepoint_eda_artifacts(
    dat,
    signal_col = "GSR_US",
    time_col = "CNT",
    group_cols = "source_file",
    flat_run_length = 10,
    zero_run_length = 10
  )

  expect_s3_class(res, "gazepoint_eda_artifact_audit")
  expect_equal(res$overview$status, "pass")
  expect_equal(res$overview$artifact_rows, 0)
  expect_equal(nrow(res$artifact_runs), 0)
})

test_that("audit_gazepoint_eda_artifacts auto-detects GSR_US", {
  dat <- data.frame(
    CNT = seq_len(30),
    GSR = seq(1000000, 900000, length.out = 30),
    GSR_US = seq(1, 1.5, length.out = 30)
  )

  res <- audit_gazepoint_eda_artifacts(dat)

  expect_equal(res$overview$signal_col, "GSR_US")
  expect_equal(res$settings$signal_col, "GSR_US")
})

test_that("audit_gazepoint_eda_artifacts detects jumps and slopes", {
  dat <- data.frame(
    source_file = "jump.csv",
    CNT = seq_len(61),
    GSR_US = c(
      seq(1, 1.5, length.out = 30),
      8,
      seq(1.6, 2.0, length.out = 30)
    )
  )

  res <- audit_gazepoint_eda_artifacts(
    dat,
    signal_col = "GSR_US",
    time_col = "CNT",
    group_cols = "source_file",
    jump_threshold_sd = 4,
    slope_threshold_sd = 4,
    flat_run_length = 10,
    zero_run_length = 10
  )

  expect_equal(res$overview$status, "warn_artifacts_detected")
  expect_true(res$overview$jump_rows > 0)
  expect_true(res$overview$slope_rows > 0)
  expect_true(any(res$row_flags$flag_jump))
  expect_true(any(res$row_flags$flag_slope))
})

test_that("audit_gazepoint_eda_artifacts detects flatline and zero runs", {
  dat <- data.frame(
    source_file = "flat.csv",
    CNT = seq_len(30),
    GSR_US = c(rep(0, 10), seq(1, 2, length.out = 20))
  )

  res <- audit_gazepoint_eda_artifacts(
    dat,
    signal_col = "GSR_US",
    time_col = "CNT",
    group_cols = "source_file",
    flat_run_length = 5,
    zero_run_length = 5
  )

  expect_true(res$overview$flatline_run_rows >= 10)
  expect_true(res$overview$zero_run_rows >= 10)
  expect_true(any(res$artifact_runs$artifact_type == "flag_zero_run"))
})

test_that("audit_gazepoint_eda_artifacts detects negative conductance and bounds", {
  dat <- data.frame(
    CNT = seq_len(6),
    GSR_US = c(1, 1.1, -0.2, 1.2, 9, 1.3)
  )

  res <- audit_gazepoint_eda_artifacts(
    dat,
    signal_col = "GSR_US",
    time_col = "CNT",
    saturation_min = 0,
    saturation_max = 5,
    flat_run_length = 3,
    zero_run_length = 3
  )

  expect_true(res$overview$negative_conductance_rows >= 1)
  expect_true(res$overview$out_of_bounds_rows >= 2)
  expect_true(any(res$row_flags$flag_negative_conductance))
  expect_true(any(res$row_flags$flag_out_of_bounds))
})

test_that("audit_gazepoint_eda_artifacts allows negative phasic values by default", {
  dat <- data.frame(
    CNT = seq_len(10),
    GSR_US_PHASIC = c(-0.1, -0.05, 0, 0.05, 0.1, 0.05, 0, -0.03, -0.02, 0)
  )

  res <- audit_gazepoint_eda_artifacts(
    dat,
    signal_col = "GSR_US_PHASIC",
    time_col = "CNT",
    flat_run_length = 5,
    zero_run_length = 5
  )

  expect_false(any(res$row_flags$flag_negative_conductance))
  expect_true(res$settings$negative_allowed)
})

test_that("audit_gazepoint_eda_artifacts respects groups when computing jumps", {
  dat <- data.frame(
    source_file = rep(c("a.csv", "b.csv"), each = 5),
    CNT = rep(seq_len(5), 2),
    GSR_US = c(seq(1, 2, length.out = 5), seq(10, 11, length.out = 5))
  )

  res <- audit_gazepoint_eda_artifacts(
    dat,
    signal_col = "GSR_US",
    time_col = "CNT",
    group_cols = "source_file",
    jump_threshold_sd = 4,
    slope_threshold_sd = 4,
    flat_run_length = 3,
    zero_run_length = 3
  )

  expect_equal(res$overview$status, "pass")
  expect_equal(res$overview$jump_rows, 0)
  expect_equal(res$overview$slope_rows, 0)
})

test_that("audit_gazepoint_eda_artifacts errors for nonnumeric signal", {
  dat <- data.frame(
    CNT = seq_len(3),
    GSR_US = c("a", "b", "c")
  )

  expect_error(
    audit_gazepoint_eda_artifacts(dat, signal_col = "GSR_US"),
    "`signal_col` must contain numeric"
  )
})
