test_that("audit_gazepoint_time_resets passes monotonic time within groups", {
  dat <- data.frame(
    source_file = rep(c("a.csv", "b.csv"), each = 5),
    CNT = rep(seq_len(5), 2),
    GSR_US = seq(1, 2, length.out = 10)
  )

  res <- audit_gazepoint_time_resets(
    dat,
    time_col = "CNT",
    group_cols = "source_file"
  )

  expect_s3_class(res, "gazepoint_time_reset_audit")
  expect_equal(res$overview$status, "pass")
  expect_equal(res$overview$negative_steps, 0)
  expect_equal(res$overview$segment_count, 2)
})

test_that("audit_gazepoint_time_resets detects reset within a group", {
  dat <- data.frame(
    source_file = "a.csv",
    CNT = c(1, 2, 3, 1, 2, 3),
    GSR_US = seq(1, 2, length.out = 6)
  )

  res <- audit_gazepoint_time_resets(
    dat,
    time_col = "CNT",
    group_cols = "source_file",
    return_reindexed_time = TRUE
  )

  expect_equal(res$overview$status, "warn_time_irregularities_detected")
  expect_equal(res$overview$negative_steps, 1)
  expect_equal(res$overview$segment_count, 2)
  expect_true("time_reindexed_within_segment" %in% names(res$data_with_segments))
  expect_equal(
    res$data_with_segments$time_reindexed_within_segment,
    c(0, 1, 2, 0, 1, 2)
  )
})

test_that("audit_gazepoint_time_resets handles duplicate time according to allow_ties", {
  dat <- data.frame(
    CNT = c(1, 2, 2, 3),
    HR = c(70, 71, 72, 73)
  )

  res_ties_allowed <- audit_gazepoint_time_resets(
    dat,
    time_col = "CNT",
    allow_ties = TRUE
  )

  res_ties_not_allowed <- audit_gazepoint_time_resets(
    dat,
    time_col = "CNT",
    allow_ties = FALSE
  )

  expect_equal(res_ties_allowed$overview$status, "pass")
  expect_equal(res_ties_allowed$overview$duplicate_steps, 1)

  expect_equal(res_ties_not_allowed$overview$status, "warn_time_irregularities_detected")
  expect_equal(res_ties_not_allowed$overview$nonmonotonic_steps, 1)
})

test_that("audit_gazepoint_time_resets fails for nonnumeric time", {
  dat <- data.frame(
    time_label = c("a", "b", "c"),
    GSR_US = c(1, 2, 3)
  )

  res <- audit_gazepoint_time_resets(
    dat,
    time_col = "time_label"
  )

  expect_equal(res$overview$status, "fail_no_numeric_time")
  expect_equal(res$overview$nonfinite_time_rows, 3)
})

test_that("audit_gazepoint_signal_activity detects all-zero inactive groups", {
  dat <- data.frame(
    source_file = rep(c("inactive.csv", "active.csv"), each = 5),
    GSR_US = c(rep(0, 5), seq(1, 2, length.out = 5)),
    HR = c(rep(0, 5), seq(70, 75, length.out = 5))
  )

  res <- audit_gazepoint_signal_activity(
    dat,
    signal_cols = c("GSR_US", "HR"),
    group_cols = "source_file"
  )

  expect_s3_class(res, "gazepoint_signal_activity_audit")
  expect_equal(res$overview$status, "warn_inactive_groups_detected")
  expect_equal(res$overview$no_active_group_count, 1)
  expect_true(any(res$inactive_groups$source_file == "inactive.csv"))
  expect_true(any(res$signal_by_group$status == "inactive_all_zero"))
})

test_that("audit_gazepoint_signal_activity distinguishes constant nonzero from active signals", {
  dat <- data.frame(
    participant = rep(c("P1", "P2"), each = 5),
    GSR_US = c(rep(1, 5), seq(1, 2, length.out = 5)),
    HR = c(rep(70, 5), seq(70, 75, length.out = 5))
  )

  res <- audit_gazepoint_signal_activity(
    dat,
    signal_cols = c("GSR_US", "HR"),
    group_cols = "participant"
  )

  p1_status <- unique(res$signal_by_group$status[res$signal_by_group$participant == "P1"])
  p2_status <- unique(res$signal_by_group$status[res$signal_by_group$participant == "P2"])

  expect_true(all(p1_status == "inactive_constant"))
  expect_true(all(p2_status == "active"))
})

test_that("audit_gazepoint_signal_activity detects low variation when nonzero uniqueness is low", {
  dat <- data.frame(
    source_file = "a.csv",
    GSR_US = c(0, 0, 1, 1, 1, 1),
    HR = c(70, 71, 72, 73, 74, 75)
  )

  res <- audit_gazepoint_signal_activity(
    dat,
    signal_cols = c("GSR_US", "HR"),
    group_cols = "source_file",
    min_unique_nonzero = 2
  )

  expect_true(any(res$signal_by_group$signal == "GSR_US" & res$signal_by_group$status == "low_variation"))
  expect_true(any(res$signal_by_group$signal == "HR" & res$signal_by_group$status == "active"))
})

test_that("audit_gazepoint_signal_activity auto-detects Gazepoint biometric signals", {
  dat <- data.frame(
    source_file = "a.csv",
    GSR_US = seq(1, 2, length.out = 10),
    HR = seq(70, 80, length.out = 10),
    unrelated = letters[1:10]
  )

  res <- audit_gazepoint_signal_activity(
    dat,
    group_cols = "source_file"
  )

  expect_true(all(c("GSR_US", "HR") %in% res$settings$signal_cols))
  expect_false("unrelated" %in% res$settings$signal_cols)
  expect_equal(res$overview$status, "pass")
})
