test_that("detect_gazepoint_scr_peaks detects a simple SCR-like peak", {
  dat <- data.frame(
    source_file = "simple.csv",
    CNT = seq_len(21),
    GSR_US_PHASIC = c(
      rep(0, 5),
      0.02, 0.05, 0.10, 0.06, 0.02, 0,
      rep(0, 10)
    )
  )

  res <- detect_gazepoint_scr_peaks(
    dat,
    phasic_col = "GSR_US_PHASIC",
    time_col = "CNT",
    group_cols = "source_file",
    amplitude_min = 0.03
  )

  expect_s3_class(res, "gazepoint_scr_peak_detection")
  expect_equal(res$overview$status, "peaks_detected")
  expect_equal(res$overview$detected_peaks, 1)
  expect_equal(res$peaks$amplitude, 0.10)
  expect_equal(res$peaks$status, "detected")
})

test_that("detect_gazepoint_scr_peaks prefers GSR_US_PHASIC when available", {
  dat <- data.frame(
    CNT = seq_len(12),
    GSR_US = c(1, 1.01, 1.02, 1.03, 1.04, 1.05, 1.04, 1.03, 1.02, 1.01, 1, 1),
    GSR_US_PHASIC = c(0, 0, 0.01, 0.04, 0.08, 0.03, 0, 0, 0, 0, 0, 0)
  )

  res <- detect_gazepoint_scr_peaks(
    dat,
    time_col = "CNT",
    amplitude_min = 0.02
  )

  expect_equal(res$overview$source_signal, "GSR_US_PHASIC")
  expect_equal(res$settings$source_signal, "GSR_US_PHASIC")
  expect_equal(res$overview$detected_peaks, 1)
})

test_that("detect_gazepoint_scr_peaks falls back to GSR_US when phasic is absent", {
  dat <- data.frame(
    CNT = seq_len(12),
    GSR_US = c(1, 1.01, 1.02, 1.08, 1.02, 1.00, 1, 1, 1, 1, 1, 1)
  )

  res <- detect_gazepoint_scr_peaks(
    dat,
    time_col = "CNT",
    amplitude_min = 0.03
  )

  expect_equal(res$overview$source_signal, "GSR_US")
  expect_equal(res$overview$detected_peaks, 1)
})

test_that("detect_gazepoint_scr_peaks ignores below-threshold peaks", {
  dat <- data.frame(
    CNT = seq_len(12),
    GSR_US_PHASIC = c(0, 0, 0.005, 0.01, 0.005, 0, 0, 0, 0, 0, 0, 0)
  )

  res <- detect_gazepoint_scr_peaks(
    dat,
    phasic_col = "GSR_US_PHASIC",
    time_col = "CNT",
    amplitude_min = 0.05
  )

  expect_equal(res$overview$status, "candidate_peaks_below_threshold")
  expect_equal(res$overview$detected_peaks, 0)
  expect_equal(nrow(res$peaks), 0)
})

test_that("detect_gazepoint_scr_peaks handles grouped data independently", {
  dat <- data.frame(
    source_file = rep(c("a.csv", "b.csv"), each = 12),
    CNT = rep(seq_len(12), 2),
    GSR_US_PHASIC = c(
      c(0, 0, 0.01, 0.07, 0.02, 0, 0, 0, 0, 0, 0, 0),
      c(0, 0, 0.02, 0.09, 0.03, 0, 0, 0, 0, 0, 0, 0)
    )
  )

  res <- detect_gazepoint_scr_peaks(
    dat,
    phasic_col = "GSR_US_PHASIC",
    time_col = "CNT",
    group_cols = "source_file",
    amplitude_min = 0.03
  )

  expect_equal(res$overview$detected_peaks, 2)
  expect_equal(nrow(res$group_summary), 2)
  expect_true(all(res$group_summary$detected_peaks == 1))
})

test_that("detect_gazepoint_scr_peaks reports incomplete recovery", {
  dat <- data.frame(
    CNT = seq_len(8),
    GSR_US_PHASIC = c(0, 0.02, 0.05, 0.10, 0.09, 0.08, 0.07, 0.06)
  )

  res <- detect_gazepoint_scr_peaks(
    dat,
    phasic_col = "GSR_US_PHASIC",
    time_col = "CNT",
    amplitude_min = 0.03
  )

  expect_equal(res$overview$detected_peaks, 1)
  expect_equal(res$peaks$status, "detected_incomplete_recovery")
  expect_true(is.na(res$peaks$recovery_time_after_peak))
})

test_that("detect_gazepoint_scr_peaks supports negative phasic baselines", {
  dat <- data.frame(
    CNT = seq_len(12),
    GSR_US_PHASIC = c(-0.03, -0.02, 0, 0.05, 0.10, 0.03, -0.01, -0.02, -0.02, -0.02, -0.02, -0.02)
  )

  res <- detect_gazepoint_scr_peaks(
    dat,
    phasic_col = "GSR_US_PHASIC",
    time_col = "CNT",
    amplitude_min = 0.05
  )

  expect_equal(res$overview$detected_peaks, 1)
  expect_true(res$peaks$amplitude >= 0.10)
})

test_that("detect_gazepoint_scr_peaks can enforce a minimum distance between peaks", {
  dat <- data.frame(
    CNT = seq_len(15),
    GSR_US_PHASIC = c(
      0, 0, 0.01, 0.08, 0.02,
      0.04, 0.12, 0.03, 0, 0,
      0.01, 0.09, 0.02, 0, 0
    )
  )

  res_no_distance <- detect_gazepoint_scr_peaks(
    dat,
    phasic_col = "GSR_US_PHASIC",
    time_col = "CNT",
    amplitude_min = 0.03,
    min_peak_distance = 1
  )

  res_with_distance <- detect_gazepoint_scr_peaks(
    dat,
    phasic_col = "GSR_US_PHASIC",
    time_col = "CNT",
    amplitude_min = 0.03,
    min_peak_distance = 5
  )

  expect_true(res_no_distance$overview$detected_peaks > res_with_distance$overview$detected_peaks)
  expect_equal(res_with_distance$overview$detected_peaks, 2)
  expect_true(all(diff(res_with_distance$peaks$peak_index) >= 5))
})

test_that("detect_gazepoint_scr_peaks errors for nonnumeric signal", {
  dat <- data.frame(
    CNT = seq_len(5),
    GSR_US_PHASIC = letters[1:5]
  )

  expect_error(
    detect_gazepoint_scr_peaks(dat, phasic_col = "GSR_US_PHASIC"),
    "numeric or numeric-coercible"
  )
})
