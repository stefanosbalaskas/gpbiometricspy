test_that("sync_gazepoint_biometrics_with_gaze joins biometric columns to gaze data", {
  biometrics <- data.frame(
    USER = c("U1", "U1", "U2"),
    MEDIA_ID = c(1, 2, 1),
    CNT = c(10, 20, 10),
    GSR_US = c(2.0, 2.2, 1.5),
    GSRV = c(1, 1, 1),
    HR = c(75, 76, 80),
    HRV = c(1, 1, 1),
    DIAL = c(0.1, 0.2, 0.3),
    DIALV = c(1, 1, 1)
  )

  gaze <- data.frame(
    USER = c("U1", "U2"),
    MEDIA_ID = c(1, 1),
    CNT = c(10, 10),
    BPOGX = c(0.5, 0.6),
    BPOGY = c(0.4, 0.3)
  )

  out <- sync_gazepoint_biometrics_with_gaze(
    biometrics = biometrics,
    gaze = gaze,
    by = c("USER", "MEDIA_ID", "CNT")
  )

  expect_s3_class(out, "gazepoint_biometrics_sync")
  expect_equal(nrow(out), 2)
  expect_true("GSR_US" %in% names(out))
  expect_true("HR" %in% names(out))
  expect_true("DIAL" %in% names(out))
  expect_true("BPOGX" %in% names(out))

  summary <- attr(out, "sync_summary")
  expect_true(is.data.frame(summary))
  expect_equal(summary$n_gaze_rows, 2)
  expect_equal(summary$n_biometric_rows, 3)
  expect_equal(summary$n_output_rows, 2)
})


test_that("sync_gazepoint_biometrics_with_gaze preserves unmatched gaze rows when all_x is TRUE", {
  biometrics <- data.frame(
    USER = "U1",
    MEDIA_ID = 1,
    CNT = 10,
    GSR_US = 2.0,
    GSRV = 1
  )

  gaze <- data.frame(
    USER = c("U1", "U1"),
    MEDIA_ID = c(1, 1),
    CNT = c(10, 11),
    BPOGX = c(0.5, 0.6)
  )

  out <- sync_gazepoint_biometrics_with_gaze(
    biometrics = biometrics,
    gaze = gaze,
    by = c("USER", "MEDIA_ID", "CNT"),
    all_x = TRUE
  )

  expect_equal(nrow(out), 2)
  expect_true(any(is.na(out$GSR_US)))
})


test_that("join_gazepoint_biometrics_to_master wraps sync function", {
  biometrics <- data.frame(
    USER = "U1",
    MEDIA_ID = 1,
    GSR_US = 2.0,
    GSRV = 1,
    HR = 75,
    HRV = 1
  )

  master <- data.frame(
    USER = "U1",
    MEDIA_ID = 1,
    dwell_time = 1200
  )

  out <- join_gazepoint_biometrics_to_master(
    master = master,
    biometrics = biometrics,
    by = c("USER", "MEDIA_ID")
  )

  expect_s3_class(out, "gazepoint_biometrics_sync")
  expect_true("dwell_time" %in% names(out))
  expect_true("GSR_US" %in% names(out))
  expect_true("HR" %in% names(out))
})


test_that("sync_gazepoint_biometrics_with_gaze rejects missing biometric join keys", {
  biometrics <- data.frame(
    USER = "U1",
    GSR_US = 2.0
  )

  gaze <- data.frame(
    USER = "U1",
    MEDIA_ID = 1
  )

  expect_error(
    sync_gazepoint_biometrics_with_gaze(
      biometrics = biometrics,
      gaze = gaze,
      by = c("USER", "MEDIA_ID")
    ),
    "biometrics"
  )
})


test_that("sync_gazepoint_biometrics_with_gaze rejects missing gaze join keys", {
  biometrics <- data.frame(
    USER = "U1",
    MEDIA_ID = 1,
    GSR_US = 2.0
  )

  gaze <- data.frame(
    USER = "U1",
    BPOGX = 0.5
  )

  expect_error(
    sync_gazepoint_biometrics_with_gaze(
      biometrics = biometrics,
      gaze = gaze,
      by = c("USER", "MEDIA_ID")
    ),
    "gaze"
  )
})
