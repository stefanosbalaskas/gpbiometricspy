test_that("prepare_gazepoint_multimodal_model_data summarises biometrics only", {
  biometrics <- data.frame(
    USER = c("U1", "U1", "U2", "U2"),
    MEDIA_ID = c(1, 1, 1, 1),
    GSR_US = c(2.0, 2.4, 1.0, 1.2),
    GSRV = c(1, 1, 1, 1),
    HR = c(70, 72, 80, 82),
    HRV = c(1, 1, 1, 1),
    DIAL = c(0.1, 0.2, 0.3, 0.4),
    DIALV = c(1, 1, 1, 1)
  )

  out <- prepare_gazepoint_multimodal_model_data(
    biometrics = biometrics,
    group_columns = c("USER", "MEDIA_ID")
  )

  expect_s3_class(out, "gazepoint_multimodal_model_data")
  expect_equal(nrow(out), 2)
  expect_true("gsr_mean_value" %in% names(out))
  expect_true("hr_mean_value" %in% names(out))
  expect_true("dial_mean_value" %in% names(out))

  summary <- attr(out, "model_data_summary")
  expect_true(is.data.frame(summary))
  expect_equal(summary$source, "biometrics_only")
})


test_that("prepare_gazepoint_multimodal_model_data merges eye-tracking summaries", {
  biometrics <- data.frame(
    USER = c("U1", "U1", "U2", "U2"),
    MEDIA_ID = c(1, 1, 1, 1),
    GSR_US = c(2.0, 2.4, 1.0, 1.2),
    GSRV = c(1, 1, 1, 1),
    HR = c(70, 72, 80, 82),
    HRV = c(1, 1, 1, 1),
    DIAL = c(0.1, 0.2, 0.3, 0.4),
    DIALV = c(1, 1, 1, 1)
  )

  eye_tracking <- data.frame(
    USER = c("U1", "U2"),
    MEDIA_ID = c(1, 1),
    dwell_time = c(1200, 900),
    fixation_count = c(8, 6)
  )

  out <- prepare_gazepoint_multimodal_model_data(
    biometrics = biometrics,
    eye_tracking = eye_tracking,
    group_columns = c("USER", "MEDIA_ID")
  )

  expect_equal(nrow(out), 2)
  expect_true("dwell_time" %in% names(out))
  expect_true("fixation_count" %in% names(out))
  expect_true("gsr_mean_value" %in% names(out))

  summary <- attr(out, "model_data_summary")
  expect_equal(summary$source, "eye_tracking_plus_biometrics")
  expect_true(summary$has_eye_tracking)
})


test_that("prepare_gazepoint_multimodal_model_data accepts already summarised biometrics", {
  biometric_summary <- data.frame(
    USER = c("U1", "U2"),
    MEDIA_ID = c(1, 1),
    gsr_mean_value = c(2.2, 1.1),
    hr_mean_value = c(71, 81),
    dial_mean_value = c(0.15, 0.35)
  )

  out <- prepare_gazepoint_multimodal_model_data(
    biometrics = biometric_summary,
    group_columns = c("USER", "MEDIA_ID"),
    biometric_is_summarised = TRUE
  )

  expect_equal(nrow(out), 2)
  expect_equal(out$gsr_mean_value[1], 2.2)
})


test_that("prepare_gazepoint_multimodal_model_data rejects missing group columns", {
  biometrics <- data.frame(
    GSR_US = c(2.0, 2.2),
    GSRV = c(1, 1)
  )

  expect_error(
    prepare_gazepoint_multimodal_model_data(
      biometrics = biometrics,
      group_columns = "USER"
    ),
    "group_columns"
  )
})


test_that("prepare_gazepoint_multimodal_model_data rejects missing eye-tracking merge keys", {
  biometrics <- data.frame(
    USER = c("U1", "U1"),
    MEDIA_ID = c(1, 1),
    GSR_US = c(2.0, 2.2),
    GSRV = c(1, 1),
    HR = c(70, 71),
    HRV = c(1, 1),
    DIAL = c(0.1, 0.2),
    DIALV = c(1, 1)
  )

  eye_tracking <- data.frame(
    USER = "U1",
    dwell_time = 1200
  )

  expect_error(
    prepare_gazepoint_multimodal_model_data(
      biometrics = biometrics,
      eye_tracking = eye_tracking,
      group_columns = c("USER", "MEDIA_ID")
    ),
    "eye_tracking"
  )
})
