test_that("summarise_gazepoint_full_biometric_windows combines multimodal and IBI summaries", {
  dat <- data.frame(
    source_participant = c("User 1", "User 1", "User 1"),
    MEDIA_ID = c(0, 0, 0),
    GSR_US = c(1.1, 1.2, 1.3),
    GSRV = c(1, 1, 1),
    HR = c(70, 72, 74),
    HRV = c(1, 1, 1),
    DIAL = c(1, 1, 1),
    DIALV = c(1, 1, 1),
    IBI = c(1.0, 1.1, 0.9)
  )

  out <- summarise_gazepoint_full_biometric_windows(
    dat,
    group_columns = c("source_participant", "MEDIA_ID")
  )

  expect_equal(nrow(out), 1)
  expect_true("gsr_mean_value" %in% names(out))
  expect_true("hr_mean_value" %in% names(out))
  expect_true("dial_mean_value" %in% names(out))
  expect_true("ibi_mean_ibi_sec" %in% names(out))
  expect_true("ibi_rmssd_ms" %in% names(out))
})


test_that("summarise_gazepoint_full_biometric_windows can omit IBI summaries", {
  dat <- data.frame(
    source_participant = c("User 1", "User 1"),
    MEDIA_ID = c(0, 0),
    GSR_US = c(1.1, 1.2),
    GSRV = c(1, 1),
    HR = c(70, 72),
    HRV = c(1, 1),
    DIAL = c(1, 1),
    DIALV = c(1, 1),
    IBI = c(1.0, 1.1)
  )

  out <- summarise_gazepoint_full_biometric_windows(
    dat,
    group_columns = c("source_participant", "MEDIA_ID"),
    include_ibi_hrv = FALSE
  )

  expect_true("gsr_mean_value" %in% names(out))
  expect_false("ibi_mean_ibi_sec" %in% names(out))
})


test_that("summarise_gazepoint_full_biometric_windows works without IBI column", {
  dat <- data.frame(
    source_participant = c("User 1", "User 1"),
    MEDIA_ID = c(0, 0),
    GSR_US = c(1.1, 1.2),
    GSRV = c(1, 1),
    HR = c(70, 72),
    HRV = c(1, 1),
    DIAL = c(1, 1),
    DIALV = c(1, 1)
  )

  out <- summarise_gazepoint_full_biometric_windows(
    dat,
    group_columns = c("source_participant", "MEDIA_ID")
  )

  expect_true("gsr_mean_value" %in% names(out))
  expect_false("ibi_mean_ibi_sec" %in% names(out))
})


test_that("summarise_gazepoint_full_biometric_windows rejects missing grouping columns", {
  dat <- data.frame(
    GSR_US = c(1.1, 1.2),
    GSRV = c(1, 1)
  )

  expect_error(
    summarise_gazepoint_full_biometric_windows(
      dat,
      group_columns = "source_participant"
    ),
    "group_columns"
  )
})
