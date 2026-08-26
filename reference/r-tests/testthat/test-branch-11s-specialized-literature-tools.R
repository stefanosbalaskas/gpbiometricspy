test_that("extract_gazepoint_eda_tvsymp returns time-varying spectral EDA summaries", {
  set.seed(1)

  time <- seq(0, 180, by = 1)
  eda <- sin(2 * pi * 0.12 * time) + rnorm(length(time), sd = 0.05)

  dat <- data.frame(
    participant = "p1",
    time = time,
    GSR_US = eda
  )

  out <- extract_gazepoint_eda_tvsymp(
    dat,
    eda_col = "GSR_US",
    time_col = "time",
    group_cols = "participant",
    sampling_rate = 1,
    window_seconds = 60,
    step_seconds = 30
  )

  expect_s3_class(out, "gazepoint_eda_tvsymp")
  expect_true(nrow(out$tvsymp_timeseries) > 0)
  expect_true("tvsymp_power" %in% names(out$tvsymp_timeseries))
  expect_true("edasympn" %in% names(out$tvsymp_timeseries))
})

test_that("autoencoder denoising bridges apply user-supplied reconstruction functions", {
  dat <- data.frame(
    participant = "p1",
    time = seq_len(32),
    GSR_US = sin(seq(0, 2 * pi, length.out = 32)) + rnorm(32, sd = 0.1),
    HRP = sin(seq(0, 4 * pi, length.out = 32)) + rnorm(32, sd = 0.1)
  )

  model_fun <- function(x) {
    x * 0.5
  }

  eda <- denoise_gazepoint_eda_autoencoder(
    dat,
    eda_col = "GSR_US",
    group_cols = "participant",
    model = model_fun,
    window_samples = 16
  )

  ppg <- denoise_gazepoint_ppg_autoencoder(
    dat,
    ppg_col = "HRP",
    group_cols = "participant",
    model = model_fun,
    window_samples = 16
  )

  expect_s3_class(eda, "gazepoint_autoencoder_denoised")
  expect_s3_class(ppg, "gazepoint_autoencoder_denoised")
  expect_true("GSR_US_autoencoder_denoised" %in% names(eda))
  expect_true("HRP_autoencoder_denoised" %in% names(ppg))
  expect_equal(
    attr(eda, "autoencoder_denoising_overview")$status,
    "autoencoder_reconstruction_complete"
  )
})

test_that("extract_gazepoint_hrv_rqa returns recurrence features", {
  dat <- data.frame(
    participant = "p1",
    IBI = 0.8 + 0.04 * sin(seq(0, 8 * pi, length.out = 80))
  )

  out <- extract_gazepoint_hrv_rqa(
    dat,
    ibi_col = "IBI",
    group_cols = "participant",
    embedding_dimension = 2,
    delay = 1
  )

  expect_s3_class(out, "gazepoint_hrv_rqa")
  expect_true("recurrence_rate" %in% names(out$features))
  expect_true("determinism" %in% names(out$features))
  expect_true(is.finite(out$features$recurrence_rate))
})

test_that("extract_gazepoint_hrv_geometric returns HTI and TINN features", {
  dat <- data.frame(
    participant = "p1",
    IBI = 0.8 + rnorm(100, sd = 0.03)
  )

  out <- extract_gazepoint_hrv_geometric(
    dat,
    ibi_col = "IBI",
    group_cols = "participant"
  )

  expect_s3_class(out, "gazepoint_hrv_geometric")
  expect_true("hrv_triangular_index" %in% names(out$features))
  expect_true("tinn" %in% names(out$features))
  expect_true(is.finite(out$features$hrv_triangular_index))
})

test_that("plot_gazepoint_scr_specification_curve returns plot metadata", {
  specification_summary <- data.frame(
    specification_id = paste0("spec_", 1:5),
    mean_response_amplitude = c(0.02, 0.01, 0.04, 0.03, 0.05),
    response_rate = c(0.2, 0.1, 0.4, 0.3, 0.5)
  )

  out <- plot_gazepoint_scr_specification_curve(
    specification_summary,
    estimate_col = "mean_response_amplitude"
  )

  expect_s3_class(out, "gazepoint_scr_specification_curve_plot")
  expect_true("specification_rank" %in% names(out$plot_data))
  expect_equal(out$plot_data$mean_response_amplitude, sort(specification_summary$mean_response_amplitude))
})
