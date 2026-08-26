test_that("audit_gazepoint_gsr_units flags conductance-like and resistance-like signals", {
  conductance <- data.frame(GSR_US = c(0.8, 1.2, 2.5, 4.0))
  out_c <- audit_gazepoint_gsr_units(conductance, gsr_col = "GSR_US")

  expect_s3_class(out_c, "gazepoint_gsr_unit_audit")
  expect_equal(out_c$overview$likely_unit, "conductance_microSiemens")

  resistance <- data.frame(GSR = c(500000, 1000000, 1500000, 2000000))
  out_r <- audit_gazepoint_gsr_units(resistance, gsr_col = "GSR", convert = TRUE)

  expect_equal(out_r$overview$likely_unit, "resistance_or_impedance_ohms")
  expect_true("GSR_converted_us" %in% names(out_r$data))
  expect_true(all(is.finite(out_r$data$GSR_converted_us)))
})

test_that("standardise_gazepoint_adaptive_ema adds normalized local signal columns", {
  dat <- data.frame(
    participant = rep(c("p1", "p2"), each = 30),
    time = rep(seq_len(30), 2),
    GSR_US = c(seq(1, 2, length.out = 30), seq(2, 4, length.out = 30))
  )

  out <- standardise_gazepoint_adaptive_ema(
    dat,
    signal_col = "GSR_US",
    group_cols = "participant",
    time_col = "time",
    alpha = 0.2
  )

  expect_s3_class(out, "gazepoint_adaptive_ema_normalised")
  expect_true("GSR_US_adaptive_ema" %in% names(out))
  expect_true("GSR_US_ema_center" %in% names(out))
  expect_equal(attr(out, "adaptive_ema_overview")$status, "adaptive_ema_normalization_complete")
})

test_that("run_gazepoint_scr_multiverse scores multiple specifications", {
  time <- rep(seq(-1, 5, by = 0.5), 4)
  trial <- rep(rep(1:2, each = length(seq(-1, 5, by = 0.5))), 2)
  participant <- rep(c("p1", "p2"), each = 2 * length(seq(-1, 5, by = 0.5)))
  condition <- rep(c("control", "treatment", "control", "treatment"), each = length(seq(-1, 5, by = 0.5)))

  signal <- 1 + ifelse(time >= 1 & time <= 3, 0.08, 0) + rnorm(length(time), sd = 0.005)

  dat <- data.frame(
    participant = participant,
    trial = paste(participant, trial, sep = "_"),
    condition = condition,
    time = time,
    GSR_US = signal
  )

  out <- run_gazepoint_scr_multiverse(
    dat,
    signal_col = "GSR_US",
    time_col = "time",
    trial_cols = c("participant", "trial"),
    condition_col = "condition",
    latency_windows = list(c(1, 3), c(1, 4)),
    thresholds = c(0.01, 0.05),
    baseline_methods = c("median", "none")
  )

  expect_s3_class(out, "gazepoint_scr_multiverse")
  expect_equal(out$overview$specification_count, 8)
  expect_true(nrow(out$scored_trials) > 0)
  expect_true(all(c("response_amplitude", "response_present") %in% names(out$scored_trials)))
})

test_that("prepare_gazepoint_artifact_svm_features and SVM bridge work with supplied function", {
  dat <- data.frame(
    participant = "p1",
    time = seq(0, 19),
    GSR_US = c(rep(1, 10), rep(10, 10))
  )

  features <- prepare_gazepoint_artifact_svm_features(
    dat,
    eda_col = "GSR_US",
    time_col = "time",
    group_cols = "participant",
    segment_seconds = 5,
    sampling_rate = 1
  )

  expect_s3_class(features, "gazepoint_artifact_svm_features")
  expect_true("detail_energy" %in% names(features))

  model_fun <- function(newdata) {
    as.numeric(newdata$mean_signal > 5)
  }

  flags <- flag_gazepoint_artifacts_svm(features, model = model_fun)

  expect_s3_class(flags, "gazepoint_artifact_svm_flags")
  expect_true("artifact_svm" %in% names(flags))
  expect_true(any(flags$artifact_svm %in% TRUE))
})

test_that("flag_gazepoint_artifacts_svm returns features without model", {
  dat <- data.frame(
    time = seq(0, 9),
    GSR_US = seq(1, 2, length.out = 10)
  )

  flags <- flag_gazepoint_artifacts_svm(
    dat,
    eda_col = "GSR_US",
    time_col = "time",
    segment_seconds = 5,
    sampling_rate = 1
  )

  expect_s3_class(flags, "gazepoint_artifact_svm_flags")
  expect_equal(attr(flags, "svm_artifact_overview")$status, "svm_features_prepared_no_model_supplied")
})

test_that("import_gazepoint_lsl_xdf fails clearly for missing files", {
  expect_error(
    import_gazepoint_lsl_xdf("missing_file.xdf"),
    "File does not exist"
  )
})
