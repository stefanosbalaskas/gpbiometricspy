test_that("summarise_gazepoint_hrv_features computes time-domain features from IBI seconds", {
  df <- data.frame(
    participant = "P1",
    time = 1:4,
    IBI = c(1.0, 1.1, 0.9, 1.0)
  )

  out <- summarise_gazepoint_hrv_features(
    df,
    group_cols = "participant",
    time_col = "time"
  )

  expect_s3_class(out, "gazepoint_hrv_features")
  expect_s3_class(out$overview, "data.frame")
  expect_s3_class(out$features, "data.frame")

  expect_equal(out$overview$status, "hrv_features_available")
  expect_equal(out$features$n_valid_ibi, 4)
  expect_equal(out$features$unit_detected, "seconds")
  expect_equal(out$features$mean_ibi_ms, 1000)
  expect_equal(out$features$mean_hr_bpm_from_ibi, 60)
  expect_equal(round(out$features$rmssd_ms, 3), round(sqrt(20000), 3))
  expect_equal(out$features$pnn50_percent, 100)
})


test_that("summarise_gazepoint_hrv_features detects IBI and ignores raw HRV", {
  df <- data.frame(
    HRV = c(1, 1, 1, 1),
    IBI = c(900, 1000, 1100, 1000)
  )

  out <- summarise_gazepoint_hrv_features(df)

  expect_equal(out$settings$ibi_col, "IBI")
  expect_equal(out$features$unit_detected, "milliseconds")
  expect_equal(out$features$mean_ibi_ms, 1000)
})


test_that("summarise_gazepoint_hrv_features supports groups", {
  df <- data.frame(
    participant = rep(c("P1", "P2"), each = 4),
    time = rep(1:4, 2),
    IBI = c(1.0, 1.1, 0.9, 1.0, 0.8, 0.85, 0.9, 0.95)
  )

  out <- summarise_gazepoint_hrv_features(
    df,
    group_cols = "participant",
    time_col = "time"
  )

  expect_equal(out$overview$group_count, 2)
  expect_equal(nrow(out$features), 2)
  expect_true(all(out$features$status == "hrv_features_computed"))
})


test_that("summarise_gazepoint_hrv_features orders values by time", {
  df <- data.frame(
    time = c(3, 1, 2),
    IBI = c(1.2, 1.0, 1.1)
  )

  out <- summarise_gazepoint_hrv_features(
    df,
    time_col = "time",
    min_valid_ibi = 3
  )

  expect_equal(out$features$mean_ibi_ms, 1100)
  expect_equal(out$features$n_valid_ibi, 3)
})


test_that("summarise_gazepoint_hrv_features flags insufficient and invalid IBI", {
  df <- data.frame(
    IBI = c(0.2, 1.0, 3.0, NA)
  )

  out <- summarise_gazepoint_hrv_features(
    df,
    min_ibi_ms = 300,
    max_ibi_ms = 2000,
    min_valid_ibi = 3
  )

  expect_equal(out$features$n_valid_ibi, 1)
  expect_equal(out$features$n_out_of_range_ibi, 2)
  expect_equal(out$features$n_missing_ibi, 1)
  expect_equal(out$features$status, "insufficient_valid_ibi")
  expect_equal(out$overview$status, "insufficient_valid_ibi")
})


test_that("summarise_gazepoint_hrv_features supports explicit millisecond unit", {
  df <- data.frame(
    rr_ms = c(800, 850, 900, 950)
  )

  out <- summarise_gazepoint_hrv_features(
    df,
    ibi_col = "rr_ms",
    ibi_unit = "milliseconds"
  )

  expect_equal(out$features$unit_detected, "milliseconds")
  expect_equal(out$features$mean_ibi_ms, 875)
})


test_that("summarise_gazepoint_hrv_features validates arguments", {
  expect_error(
    summarise_gazepoint_hrv_features(1:3),
    "`data` must be"
  )

  df <- data.frame(IBI = c(1, 1.1, 1.0))

  expect_error(
    summarise_gazepoint_hrv_features(df, ibi_col = "missing"),
    "not found"
  )

  expect_error(
    summarise_gazepoint_hrv_features(data.frame(HRV = c(1, 1, 1))),
    "No IBI/RR interval"
  )

  expect_error(
    summarise_gazepoint_hrv_features(data.frame(HRV = c(1, 1, 1)), ibi_col = "HRV"),
    "validity/vendor flag"
  )

  expect_error(
    summarise_gazepoint_hrv_features(
      data.frame(IBI = letters[1:3]),
      ibi_col = "IBI"
    ),
    "`ibi_col` must be numeric"
  )

  expect_error(
    summarise_gazepoint_hrv_features(df, min_ibi_ms = 0),
    "`min_ibi_ms`"
  )

  expect_error(
    summarise_gazepoint_hrv_features(df, max_ibi_ms = 0),
    "`max_ibi_ms`"
  )

  expect_error(
    summarise_gazepoint_hrv_features(df, min_ibi_ms = 2000, max_ibi_ms = 300),
    "smaller"
  )

  expect_error(
    summarise_gazepoint_hrv_features(df, min_valid_ibi = 0),
    "`min_valid_ibi`"
  )
})
