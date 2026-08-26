test_that("standardise_gazepoint_zscore creates within-participant z scores", {
  dat <- data.frame(
    source_participant = rep(c("p1", "p2"), each = 5),
    SCR_Amplitude = c(1, 2, 3, 4, 5, 10, 20, 30, 40, 50)
  )

  out <- standardise_gazepoint_zscore(dat)

  expect_true("SCR_Amplitude_Z" %in% names(out))

  by_id <- split(out, out$source_participant)

  expect_equal(mean(by_id$p1$SCR_Amplitude_Z), 0, tolerance = 1e-10)
  expect_equal(stats::sd(by_id$p1$SCR_Amplitude_Z), 1, tolerance = 1e-10)
  expect_equal(mean(by_id$p2$SCR_Amplitude_Z), 0, tolerance = 1e-10)
  expect_equal(stats::sd(by_id$p2$SCR_Amplitude_Z), 1, tolerance = 1e-10)
})

test_that("standardise_gazepoint_range_correction rescales within participant", {
  dat <- data.frame(
    source_participant = rep(c("p1", "p2"), each = 3),
    SCR_Amplitude = c(1, 2, 3, 10, 20, 30)
  )

  out <- standardise_gazepoint_range_correction(
    dat,
    signal_col = "SCR_Amplitude"
  )

  expect_true("SCR_Amplitude_Range_Corrected" %in% names(out))

  p1 <- out$SCR_Amplitude_Range_Corrected[out$source_participant == "p1"]
  p2 <- out$SCR_Amplitude_Range_Corrected[out$source_participant == "p2"]

  expect_equal(p1, c(0, 0.5, 1))
  expect_equal(p2, c(0, 0.5, 1))

  summary <- attr(out, "range_correction_summary")
  expect_equal(summary$status, "range_correction_complete")
})

test_that("standardise_gazepoint_range_correction handles zero ranges", {
  dat <- data.frame(
    source_participant = "p1",
    SCR_Amplitude = rep(1, 4)
  )

  out <- standardise_gazepoint_range_correction(
    dat,
    signal_col = "SCR_Amplitude"
  )

  expect_true(all(is.na(out$SCR_Amplitude_Range_Corrected)))
  expect_equal(attr(out, "range_correction_summary")$status, "range_correction_failed")
})
