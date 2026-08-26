test_that("correct_gazepoint_eda_temperature returns temperature-adjusted EDA", {
  dat <- data.frame(
    participant = "p1",
    time = seq_len(60),
    GSR_US = 1 + 0.05 * seq_len(60) + rnorm(60, sd = 0.01),
    ambient_temp = 20 + 0.1 * seq_len(60)
  )

  out <- correct_gazepoint_eda_temperature(
    dat,
    eda_col = "GSR_US",
    temperature_cols = "ambient_temp",
    group_cols = "participant",
    time_col = "time"
  )

  expect_s3_class(out, "gazepoint_eda_temperature_corrected")
  expect_true("eda_temperature_adjusted" %in% names(out))
  expect_equal(
    attr(out, "eda_temperature_overview")$status,
    "eda_temperature_correction_complete"
  )
})

test_that("extract_gazepoint_beats_kmeans detects pulse beat candidates", {
  time <- seq(0, 20, by = 0.02)
  pulse <- rep(0, length(time))

  beat_times <- seq(1, 19, by = 1)

  for (bt in beat_times) {
    pulse <- pulse + exp(-0.5 * ((time - bt) / 0.03)^2)
  }

  dat <- data.frame(
    participant = "p1",
    time = time,
    HRP = pulse + rnorm(length(time), sd = 0.02)
  )

  out <- extract_gazepoint_beats_kmeans(
    dat,
    pulse_col = "HRP",
    time_col = "time",
    group_cols = "participant",
    min_distance_s = 0.5,
    seed = 1
  )

  expect_s3_class(out, "gazepoint_kmeans_beats")
  expect_true(nrow(out$beat_table) > 5)
  expect_true("ibi_s" %in% names(out$interval_table))
})

test_that("audit_gazepoint_stabilization_period flags initial period", {
  dat <- data.frame(
    participant = "p1",
    CNT = seq(0, 1200, by = 10),
    GSR_US = rnorm(121)
  )

  out <- audit_gazepoint_stabilization_period(
    dat,
    time_col = "CNT",
    group_cols = "participant",
    stabilization_minutes = 10,
    action = "flag"
  )

  expect_s3_class(out, "gazepoint_stabilization_audit")
  expect_true("in_stabilization_period" %in% names(out))
  expect_true(any(out$in_stabilization_period))
  expect_true(any(!out$in_stabilization_period))
})

test_that("regress_gazepoint_pupil_luminance adjusts pupil for luminance", {
  dat <- data.frame(
    participant = "p1",
    time = seq_len(80),
    pupil = 3 + 0.4 * scale(seq_len(80))[, 1] + rnorm(80, sd = 0.05),
    luminance = scale(seq_len(80))[, 1]
  )

  out <- regress_gazepoint_pupil_luminance(
    dat,
    pupil_col = "pupil",
    luminance_col = "luminance",
    group_cols = "participant",
    time_col = "time"
  )

  expect_s3_class(out, "gazepoint_pupil_luminance_adjusted")
  expect_true("pupil_luminance_adjusted" %in% names(out))
  expect_equal(
    attr(out, "pupil_luminance_overview")$status,
    "pupil_luminance_regression_complete"
  )
})

test_that("model_gazepoint_hrv_ipfm creates impulse train and spectrum", {
  dat <- data.frame(
    participant = "p1",
    IBI = rep(0.8, 60) + rnorm(60, sd = 0.02)
  )

  out <- model_gazepoint_hrv_ipfm(
    dat,
    ibi_col = "IBI",
    group_cols = "participant",
    output_sampling_rate = 4,
    max_frequency = 0.5
  )

  expect_s3_class(out, "gazepoint_hrv_ipfm")
  expect_true(nrow(out$impulse_table) > 0)
  expect_true("frequency_hz" %in% names(out$spectrum_table))
  expect_equal(out$overview$status, "ipfm_model_created")
})
