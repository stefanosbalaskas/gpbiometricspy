test_that("standardise_gazepoint_biometric_names standardises character vectors", {
  input <- c("time ms", "heart rate", "eda uS", "rr interval", "engagement dial")
  output <- standardise_gazepoint_biometric_names(input)

  expect_equal(output, c("TIME_MS", "HR", "GSR_US", "IBI", "ENGAGEMENT"))
})


test_that("standardise_gazepoint_biometric_names can rename data frames", {
  df <- data.frame(
    `time ms` = 1:3,
    `heart rate` = c(70, 71, 72),
    check.names = FALSE
  )

  renamed <- standardise_gazepoint_biometric_names(df)

  expect_s3_class(renamed, "data.frame")
  expect_equal(names(renamed), c("TIME_MS", "HR"))
})


test_that("standardise_gazepoint_biometric_names can return a mapping table", {
  df <- data.frame(
    `time ms` = 1:3,
    `heart rate` = c(70, 71, 72),
    check.names = FALSE
  )

  mapping <- standardise_gazepoint_biometric_names(df, rename = FALSE)

  expect_s3_class(mapping, "data.frame")
  expect_equal(mapping$original_name, c("time ms", "heart rate"))
  expect_equal(mapping$standard_name, c("TIME_MS", "HR"))
  expect_true(all(mapping$changed))
})


test_that("standardise_gazepoint_biometric_names supports snake style", {
  output <- standardise_gazepoint_biometric_names(
    c("time ms", "heart rate", "eda uS"),
    style = "snake"
  )

  expect_equal(output, c("time_ms", "hr", "gsr_us"))
})


test_that("standardise_gazepoint_biometric_names makes duplicates unique", {
  output <- standardise_gazepoint_biometric_names(c("GSR", "eda"))

  expect_equal(output, c("GSR", "GSR_1"))
})


test_that("detect_gazepoint_time_columns detects counters and timestamps", {
  out <- detect_gazepoint_time_columns(c("CNT", "TIME", "TIME_MS", "GSR"))

  expect_s3_class(out, "data.frame")
  expect_true(all(c("CNT", "TIME", "TIME_MS") %in% out$column))
  expect_true("sample_counter" %in% out$role)
  expect_true("timestamp" %in% out$role)
  expect_true("seconds" %in% out$unit_hint)
  expect_true("milliseconds" %in% out$unit_hint)
})


test_that("detect_gazepoint_time_columns returns empty table when no time column exists", {
  out <- detect_gazepoint_time_columns(c("GSR", "HR", "ENGAGEMENT"))

  expect_s3_class(out, "data.frame")
  expect_equal(nrow(out), 0)
  expect_equal(
    names(out),
    c("column", "standard_name", "role", "unit_hint", "confidence", "reason")
  )
})


test_that("detect_gazepoint_biometric_timebase estimates rate from seconds", {
  df <- data.frame(
    CNT = 1:6,
    TIME = seq(0, by = 1 / 60, length.out = 6),
    GSR = seq(100, 105)
  )

  out <- detect_gazepoint_biometric_timebase(df)

  expect_type(out, "list")
  expect_equal(out$overview$primary_time_column, "TIME")
  expect_equal(out$overview$unit, "seconds")
  expect_equal(round(out$overview$sampling_rate_hz), 60)
  expect_equal(out$overview$status, "timebase_detected")
})


test_that("detect_gazepoint_biometric_timebase estimates rate from milliseconds", {
  df <- data.frame(
    TIME_MS = seq(0, by = 16.6667, length.out = 6),
    HR = c(70, 70, 71, 71, 72, 72)
  )

  out <- detect_gazepoint_biometric_timebase(df)

  expect_equal(out$overview$primary_time_column, "TIME_MS")
  expect_equal(out$overview$unit, "milliseconds")
  expect_equal(round(out$overview$sampling_rate_hz), 60)
})


test_that("detect_gazepoint_biometric_timebase handles no usable timebase", {
  df <- data.frame(
    GSR = c(1, 2, 3),
    HR = c(70, 71, 72)
  )

  out <- detect_gazepoint_biometric_timebase(df)

  expect_equal(out$overview$status, "no_timebase_detected")
  expect_true(is.na(out$overview$primary_time_column))
  expect_true(length(out$warnings) >= 1)
})


test_that("detect_gazepoint_biometric_schema reports active biometric channels", {
  df <- data.frame(
    CNT = 1:6,
    TIME = seq(0, by = 1 / 60, length.out = 6),
    GSR = c(100, 101, 102, 103, 102, 101),
    HR = c(70, 70, 71, 71, 72, 72),
    HRV = c(1, 1, 1, 1, 1, 1),
    ENGAGEMENT = c(50, 51, 52, 53, 54, 55),
    TTL = c(0, 0, 1, 0, 1, 0)
  )

  out <- detect_gazepoint_biometric_schema(df)

  expect_type(out, "list")
  expect_s3_class(out$overview, "data.frame")
  expect_s3_class(out$columns, "data.frame")
  expect_true(out$overview$has_gsr_eda)
  expect_true(out$overview$has_heart_rate)
  expect_true(out$overview$has_hrv_flag)
  expect_true(out$overview$has_engagement_dial)
  expect_true(out$overview$has_ttl_marker)
  expect_true(out$overview$active_gsr_eda)
  expect_true(out$overview$active_heart_rate)
  expect_true(out$overview$active_engagement_dial)
  expect_true(out$overview$active_ttl_marker)
  expect_equal(out$overview$status, "biometric_schema_detected")
})


test_that("detect_gazepoint_biometric_schema detects numbered TTL marker columns", {
  df <- data.frame(
    CNT = 1:5,
    GSR = c(1, 1.1, 1.2, 1.1, 1),
    TTL0 = c(0, 0, 1, 0, 0),
    TTL1 = c(0, 1, 0, 0, 0),
    TTLV = c(1, 1, 1, 1, 1)
  )

  out <- detect_gazepoint_biometric_schema(df)

  expect_true(out$overview$has_ttl_marker)
  expect_true(out$overview$active_ttl_marker)

  ttl_rows <- out$columns[
    out$columns$column %in% c("TTL0", "TTL1", "TTLV"),
    ,
    drop = FALSE
  ]

  expect_equal(nrow(ttl_rows), 3)
  expect_true("TTL0" %in% ttl_rows$column)
  expect_true("TTL1" %in% ttl_rows$column)
  expect_true("TTLV" %in% ttl_rows$column)

  numbered_ttl_rows <- ttl_rows[ttl_rows$column %in% c("TTL0", "TTL1"), ]

  expect_true(all(grepl("^TTL(_[0-9]+)?$", numbered_ttl_rows$standard_name)))

  expect_true(all(numbered_ttl_rows$signal_group == "ttl_marker"))

  expect_equal(
    ttl_rows$standard_name[ttl_rows$column == "TTLV"],
    "TTLV"
  )

  expect_equal(
    ttl_rows$signal_group[ttl_rows$column == "TTLV"],
    "ttl_validity_flag"
  )
})


test_that("detect_gazepoint_biometric_schema keeps HRV interpretation conservative", {
  df <- data.frame(
    CNT = 1:3,
    TIME = c(0, 0.016, 0.032),
    HR = c(70, 71, 72),
    HRV = c(1, 1, 1)
  )

  out <- detect_gazepoint_biometric_schema(df)

  hrv_row <- out$columns[out$columns$standard_name == "HRV", , drop = FALSE]

  expect_equal(hrv_row$signal_group, "heart_rate_validity_flag")
  expect_match(hrv_row$interpretation_note, "validity/vendor flag")
  expect_true(any(grepl("Treat raw HRV columns", out$notes)))
})


test_that("schema helpers reject unsupported inputs", {
  expect_error(
    standardise_gazepoint_biometric_names(1:3),
    "`data` must be"
  )

  expect_error(
    detect_gazepoint_time_columns(1:3),
    "`data` must be"
  )

  expect_error(
    detect_gazepoint_biometric_timebase(c("CNT", "TIME")),
    "`data` must be"
  )

  expect_error(
    detect_gazepoint_biometric_schema(c("CNT", "TIME")),
    "`data` must be"
  )
})
