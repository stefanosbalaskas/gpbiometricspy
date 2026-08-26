test_that("prepare_gazepoint_pyppg_input prepares HRP waveform tables", {
  dat <- data.frame(
    participant = rep(c("p1", "p2"), each = 30),
    CNT = rep(1:30, times = 2),
    HRP = c(
      sin(seq(0, 2 * pi, length.out = 30)),
      cos(seq(0, 2 * pi, length.out = 30))
    )
  )

  out <- prepare_gazepoint_pyppg_input(
    dat,
    ppg_col = "HRP",
    time_col = "CNT",
    group_cols = "participant",
    sampling_rate = 60
  )

  expect_s3_class(out, "gazepoint_pyppg_input")
  expect_equal(out$overview$status, "pyppg_input_prepared")
  expect_equal(out$overview$group_count, 2)
  expect_equal(nrow(out$waveform_table), nrow(dat))
  expect_true(all(c("sample_index", "time_s", "ppg_signal") %in% names(out$waveform_table)))
  expect_true(all(is.finite(out$waveform_table$time_s)))
  expect_equal(unique(out$group_summary$status), "ready_for_pyppg_input")
})

test_that("prepare_gazepoint_pyppg_input can prepare sample-index-only output", {
  dat <- data.frame(
    participant = "p1",
    HRP = sin(seq(0, 2 * pi, length.out = 20))
  )

  out <- prepare_gazepoint_pyppg_input(
    dat,
    ppg_col = "HRP",
    group_cols = "participant"
  )

  expect_s3_class(out, "gazepoint_pyppg_input")
  expect_equal(out$overview$status, "pyppg_input_prepared")
  expect_equal(out$group_summary$status, "prepared_with_sample_index_only")
  expect_true(all(is.na(out$waveform_table$time_s)))
})

test_that("prepare_gazepoint_pyppg_input writes optional CSV outputs", {
  dat <- data.frame(
    participant = "p1",
    CNT = 1:20,
    HRP = sin(seq(0, 2 * pi, length.out = 20))
  )

  output_dir <- tempfile("pyppg_export_")

  out <- prepare_gazepoint_pyppg_input(
    dat,
    ppg_col = "HRP",
    time_col = "CNT",
    group_cols = "participant",
    sampling_rate = 60,
    output_dir = output_dir,
    prefix = "test_pyppg"
  )

  expect_equal(nrow(out$manifest), 2)
  expect_true(all(file.exists(out$manifest$path)))
  expect_true(any(grepl("waveform_table", out$manifest$item)))
  expect_true(any(grepl("group_summary", out$manifest$item)))
})

test_that("prepare_gazepoint_pyppg_input errors when no HRP or PPG column is available", {
  dat <- data.frame(
    time_ms = 1:10,
    HR = 70 + seq_len(10)
  )

  expect_error(
    prepare_gazepoint_pyppg_input(dat),
    "No usable HRP/PPG waveform column"
  )
})

test_that("assess_gazepoint_hrp_waveform_quality passes variable waveform data", {
  dat <- data.frame(
    participant = "p1",
    time_ms = seq(0, by = 10, length.out = 80),
    HRP = sin(seq(0, 6 * pi, length.out = 80))
  )

  out <- assess_gazepoint_hrp_waveform_quality(
    dat,
    hrp_col = "HRP",
    time_col = "time_ms",
    group_cols = "participant",
    min_rows = 20
  )

  expect_s3_class(out, "gazepoint_hrp_waveform_quality")
  expect_equal(out$overview$status, "pass")
  expect_equal(out$group_quality$status, "descriptive_quality_pass")
  expect_equal(nrow(out$row_flags), nrow(dat))
  expect_true(all(c(
    "flag_missing_or_nonfinite_hrp",
    "flag_large_time_gap"
  ) %in% names(out$row_flags)))
})

test_that("assess_gazepoint_hrp_waveform_quality flags flat waveform data", {
  dat <- data.frame(
    participant = "p1",
    time_ms = seq(0, by = 10, length.out = 50),
    HRP = rep(1, 50)
  )

  out <- assess_gazepoint_hrp_waveform_quality(
    dat,
    hrp_col = "HRP",
    time_col = "time_ms",
    group_cols = "participant",
    min_rows = 20
  )

  expect_s3_class(out, "gazepoint_hrp_waveform_quality")
  expect_equal(out$overview$status, "review_recommended")
  expect_equal(out$group_quality$status, "review_flat_signal")
})

test_that("assess_gazepoint_hrp_waveform_quality flags low finite signal", {
  dat <- data.frame(
    participant = "p1",
    time_ms = seq(0, by = 10, length.out = 50),
    HRP = c(rep(NA_real_, 30), sin(seq(0, 2 * pi, length.out = 20)))
  )

  out <- assess_gazepoint_hrp_waveform_quality(
    dat,
    hrp_col = "HRP",
    time_col = "time_ms",
    group_cols = "participant",
    min_rows = 20,
    min_finite_prop = 0.80
  )

  expect_equal(out$overview$status, "fail_review_required")
  expect_equal(out$group_quality$status, "fail_low_finite_signal")
  expect_true(any(out$row_flags$flag_missing_or_nonfinite_hrp))
})

test_that("assess_gazepoint_hrp_waveform_quality flags large time gaps", {
  dat <- data.frame(
    participant = "p1",
    time_ms = c(seq(0, by = 10, length.out = 30), seq(1000, by = 10, length.out = 30)),
    HRP = sin(seq(0, 4 * pi, length.out = 60))
  )

  out <- assess_gazepoint_hrp_waveform_quality(
    dat,
    hrp_col = "HRP",
    time_col = "time_ms",
    group_cols = "participant",
    min_rows = 20
  )

  expect_equal(out$overview$status, "review_recommended")
  expect_equal(out$group_quality$status, "review_time_gaps")
  expect_true(any(out$row_flags$flag_large_time_gap))
})
