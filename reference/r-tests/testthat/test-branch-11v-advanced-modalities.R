test_that("extract_gazepoint_bilateral_eda_asymmetry returns bilateral descriptors", {
  dat <- data.frame(
    participant = "p1",
    time = seq(0, 10, by = 0.5),
    EDA_left = 1 + sin(seq(0, 10, by = 0.5)) * 0.05,
    EDA_right = 1 + cos(seq(0, 10, by = 0.5)) * 0.04
  )

  out <- extract_gazepoint_bilateral_eda_asymmetry(
    dat,
    left_col = "EDA_left",
    right_col = "EDA_right",
    time_col = "time",
    group_cols = "participant"
  )

  expect_s3_class(out, "gazepoint_bilateral_eda_asymmetry")
  expect_true("beda_left_minus_right" %in% names(out$asymmetry_timeseries))
  expect_true("mean_left_minus_right" %in% names(out$summary))
  expect_equal(out$overview$status, "bilateral_eda_asymmetry_complete")
})

test_that("denoise_gazepoint_quantization_noise adds jittered columns", {
  dat <- data.frame(
    participant = "p1",
    IBI = rep(c(0.80, 0.81, 0.82), length.out = 30),
    GSR_US = rep(c(1.00, 1.01, 1.02), length.out = 30)
  )

  out <- denoise_gazepoint_quantization_noise(
    dat,
    signal_cols = c("IBI", "GSR_US"),
    resolution = c(IBI = 0.001, GSR_US = 0.01),
    seed = 1
  )

  expect_s3_class(out, "gazepoint_quantization_noise_adjusted")
  expect_true("IBI_quantization_jittered" %in% names(out))
  expect_true("GSR_US_quantization_jittered" %in% names(out))
  expect_equal(attr(out, "quantization_noise_overview")$status, "quantization_noise_reduction_complete")
})

test_that("extract_gazepoint_edr_pca returns ECG-derived respiration proxy components", {
  time <- seq(0, 20, by = 0.5)
  resp <- sin(2 * pi * 0.2 * time)

  dat <- data.frame(
    participant = "p1",
    time = time,
    qrs_amp = 1 + 0.1 * resp,
    qrs_width = 0.08 + 0.01 * resp,
    qrs_area = 0.5 + 0.05 * resp
  )

  out <- extract_gazepoint_edr_pca(
    dat,
    ecg_cols = c("qrs_amp", "qrs_width", "qrs_area"),
    time_col = "time",
    group_cols = "participant",
    n_components = 1
  )

  expect_s3_class(out, "gazepoint_edr_pca")
  expect_true("edr_pca_pc1" %in% names(out$edr_timeseries))
  expect_true("variance_explained" %in% names(out$component_summary))
  expect_equal(out$overview$status, "edr_pca_extracted")
})

test_that("analyze_gazepoint_skin_potential returns SPL and SPR descriptors", {
  time <- seq(0, 60, by = 0.5)
  sp <- 2 + 0.01 * sin(time)

  sp[which.min(abs(time - 10))] <- sp[which.min(abs(time - 10))] + 0.5
  sp[which.min(abs(time - 30))] <- sp[which.min(abs(time - 30))] - 0.6

  dat <- data.frame(
    participant = "p1",
    time = time,
    SP_mV = sp
  )

  out <- analyze_gazepoint_skin_potential(
    dat,
    sp_col = "SP_mV",
    time_col = "time",
    group_cols = "participant",
    response_direction = "both",
    response_threshold = 0.5,
    min_response_distance_s = 2
  )

  expect_s3_class(out, "gazepoint_skin_potential_analysis")
  expect_true("mean_spl" %in% names(out$level_summary))
  expect_true("skin_potential_response" %in% names(out$timeseries))
  expect_equal(out$overview$status, "skin_potential_analysis_complete")
})
