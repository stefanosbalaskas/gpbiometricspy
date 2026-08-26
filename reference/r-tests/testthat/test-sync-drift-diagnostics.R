test_that("estimate_gazepoint_signal_lag detects a simple delayed signal", {
  n <- 120
  time_ms <- seq_len(n)

  x <- rep(0, n)
  y <- rep(0, n)

  x[30:50] <- 1
  y[35:55] <- 1

  dat <- data.frame(
    participant = "p1",
    time_ms = time_ms,
    x = x,
    y = y
  )

  out <- estimate_gazepoint_signal_lag(
    dat,
    signal_x_col = "x",
    signal_y_col = "y",
    time_col = "time_ms",
    group_cols = "participant",
    max_lag = 10,
    lag_step = 1,
    min_complete_pairs = 20
  )

  expect_s3_class(out, "gazepoint_signal_lag")
  expect_equal(out$overview$status, "estimated")
  expect_equal(nrow(out$lag_by_group), 1)
  expect_equal(out$lag_by_group$status, "estimated")
  expect_equal(out$lag_by_group$estimated_lag, 5)
  expect_true(nrow(out$lag_profile) > 0)
  expect_true(all(abs(out$lag_profile$lag) <= 10))
})

test_that("estimate_gazepoint_signal_lag handles insufficient data conservatively", {
  dat <- data.frame(
    time_ms = 1:5,
    x = c(1, 2, 3, 4, 5),
    y = c(1, 2, 3, 4, 5)
  )

  out <- estimate_gazepoint_signal_lag(
    dat,
    signal_x_col = "x",
    signal_y_col = "y",
    time_col = "time_ms",
    max_lag = 2,
    lag_step = 1,
    min_complete_pairs = 20
  )

  expect_s3_class(out, "gazepoint_signal_lag")
  expect_equal(out$overview$status, "no_valid_estimates")
  expect_equal(out$lag_by_group$status, "insufficient_data")
  expect_true(is.na(out$lag_by_group$estimated_lag))
})

test_that("audit_gazepoint_biometric_sync_drift summarizes lag variability", {
  make_group <- function(participant, delay) {
    n <- 140
    x <- rep(0, n)
    y <- rep(0, n)

    x[40:60] <- 1
    y[(40 + delay):(60 + delay)] <- 1

    data.frame(
      participant = participant,
      time_ms = seq_len(n),
      x = x,
      y = y
    )
  }

  dat <- rbind(
    make_group("p1", 2),
    make_group("p2", 6)
  )

  out <- audit_gazepoint_biometric_sync_drift(
    dat,
    time_col = "time_ms",
    group_cols = "participant",
    signal_pairs = data.frame(signal_x = "x", signal_y = "y"),
    max_lag = 8,
    lag_step = 1,
    drift_tolerance = 2,
    min_complete_pairs = 20,
    include_reset_segments = FALSE
  )

  expect_s3_class(out, "gazepoint_biometric_sync_drift_audit")
  expect_true(all(c(
    "overview",
    "checks",
    "time_reset_audit",
    "lag_by_group",
    "lag_profile",
    "drift_summary",
    "settings"
  ) %in% names(out)))

  expect_equal(out$overview$signal_pair_count, 1)
  expect_equal(out$overview$lag_estimate_rows, 2)
  expect_equal(nrow(out$drift_summary), 1)
  expect_equal(out$drift_summary$status, "drift_exceeds_tolerance")
  expect_true(out$drift_summary$lag_range > 2)
})

test_that("audit_gazepoint_biometric_sync_drift is conservative without signal pairs", {
  dat <- data.frame(
    time_ms = seq_len(20),
    x = seq_len(20)
  )

  out <- audit_gazepoint_biometric_sync_drift(
    dat,
    time_col = "time_ms",
    signal_cols = "x"
  )

  expect_s3_class(out, "gazepoint_biometric_sync_drift_audit")
  expect_equal(out$overview$status, "no_signal_pairs")
  expect_equal(out$overview$signal_pair_count, 0)
  expect_equal(nrow(out$lag_by_group), 0)
  expect_equal(nrow(out$drift_summary), 0)
})
