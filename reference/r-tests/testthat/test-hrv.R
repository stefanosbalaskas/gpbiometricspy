test_that("summarise_gazepoint_ibi_hrv_windows computes IBI-derived summaries", {
  dat <- data.frame(
    source_participant = c("User 1", "User 1", "User 1", "User 1"),
    MEDIA_ID = c(0, 0, 0, 0),
    IBI = c(1.0, 1.1, 0.9, 1.0),
    HRV = c(1, 1, 1, 1)
  )

  out <- summarise_gazepoint_ibi_hrv_windows(
    dat,
    group_columns = c("source_participant", "MEDIA_ID")
  )

  expect_equal(nrow(out), 1)
  expect_equal(out$ibi_usable_rows, 4)
  expect_equal(out$mean_ibi_sec, 1.0, tolerance = 1e-8)
  expect_equal(out$mean_hr_from_ibi_bpm, mean(60 / c(1.0, 1.1, 0.9, 1.0)), tolerance = 1e-8)
  expect_true("sdnn_ms" %in% names(out))
  expect_true("rmssd_ms" %in% names(out))
  expect_true("pnn50" %in% names(out))
})


test_that("summarise_gazepoint_ibi_hrv_windows excludes invalid and implausible IBI values", {
  dat <- data.frame(
    source_participant = c("User 1", "User 1", "User 1", "User 1"),
    MEDIA_ID = c(0, 0, 0, 0),
    IBI = c(1.0, 0, 3.0, 1.2),
    HRV = c(1, 1, 1, 0)
  )

  out <- summarise_gazepoint_ibi_hrv_windows(
    dat,
    group_columns = c("source_participant", "MEDIA_ID")
  )

  expect_equal(out$ibi_usable_rows, 1)
  expect_equal(out$mean_ibi_sec, 1.0, tolerance = 1e-8)
  expect_equal(out$ibi_usable_pct, 25, tolerance = 1e-8)
})


test_that("summarise_gazepoint_ibi_hrv_windows supports multiple windows", {
  dat <- data.frame(
    source_participant = c("User 1", "User 1", "User 2", "User 2"),
    MEDIA_ID = c(0, 0, 0, 0),
    IBI = c(1.0, 1.1, 0.8, 0.9),
    HRV = c(1, 1, 1, 1)
  )

  out <- summarise_gazepoint_ibi_hrv_windows(
    dat,
    group_columns = c("source_participant", "MEDIA_ID")
  )

  expect_equal(nrow(out), 2)
  expect_true(all(c("User 1", "User 2") %in% out$source_participant))
})


test_that("summarise_gazepoint_ibi_hrv_windows rejects missing IBI column", {
  dat <- data.frame(
    source_participant = "User 1",
    MEDIA_ID = 0,
    HRV = 1
  )

  expect_error(
    summarise_gazepoint_ibi_hrv_windows(
      dat,
      group_columns = c("source_participant", "MEDIA_ID")
    ),
    "ibi_column"
  )
})


test_that("summarise_gazepoint_ibi_hrv_windows rejects missing grouping columns", {
  dat <- data.frame(
    IBI = c(1.0, 1.1),
    HRV = c(1, 1)
  )

  expect_error(
    summarise_gazepoint_ibi_hrv_windows(
      dat,
      group_columns = "source_participant"
    ),
    "group_columns"
  )
})
