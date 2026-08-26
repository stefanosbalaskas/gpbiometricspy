test_that("convert_gazepoint_gsr_to_conductance converts ohms automatically from resistance-like column", {
  df <- data.frame(
    GSR_OHMS = c(1000000, 500000, NA, 0, -1, Inf)
  )

  out <- convert_gazepoint_gsr_to_conductance(df)

  expect_true("GSR_US" %in% names(out))
  expect_equal(out$GSR_US[1:2], c(1, 2))
  expect_true(is.na(out$GSR_US[3]))
  expect_true(is.na(out$GSR_US[4]))
  expect_true(is.na(out$GSR_US[5]))
  expect_true(is.na(out$GSR_US[6]))

  summary <- attr(out, "gsr_conversion_summary")
  expect_s3_class(summary, "data.frame")
  expect_equal(summary$status, "conductance_created")
  expect_equal(summary$n_converted, 2)
  expect_equal(summary$n_invalid, 3)
})


test_that("convert_gazepoint_gsr_to_conductance converts kilo-ohms when explicitly requested", {
  df <- data.frame(
    GSR = c(1000, 500, NA)
  )

  out <- convert_gazepoint_gsr_to_conductance(
    df,
    gsr_col = "GSR",
    input_unit = "kohms"
  )

  expect_equal(out$GSR_US[1:2], c(1, 2))
  expect_true(is.na(out$GSR_US[3]))

  summary <- attr(out, "gsr_conversion_summary")
  expect_equal(summary$input_unit, "kohms")
  expect_equal(summary$status, "conductance_created")
})


test_that("convert_gazepoint_gsr_to_conductance does not auto-convert generic GSR", {
  df <- data.frame(
    GSR = c(1000000, 500000)
  )

  out <- convert_gazepoint_gsr_to_conductance(df, gsr_col = "GSR")

  expect_false("GSR_US" %in% names(out))
  summary <- attr(out, "gsr_conversion_summary")
  expect_equal(summary$status, "unit_not_confirmed")
})


test_that("convert_gazepoint_gsr_to_conductance leaves existing conductance unchanged by default", {
  df <- data.frame(
    GSR_US = c(1, 2, 3),
    GSR_OHMS = c(1000000, 500000, 333333.3)
  )

  out <- convert_gazepoint_gsr_to_conductance(df)

  expect_equal(out$GSR_US, c(1, 2, 3))
  summary <- attr(out, "gsr_conversion_summary")
  expect_equal(summary$status, "conductance_column_already_present")
})


test_that("convert_gazepoint_gsr_to_conductance can overwrite existing conductance", {
  df <- data.frame(
    GSR_US = c(10, 10),
    GSR_OHMS = c(1000000, 500000)
  )

  out <- convert_gazepoint_gsr_to_conductance(df, overwrite = TRUE)

  expect_equal(out$GSR_US, c(1, 2))
  summary <- attr(out, "gsr_conversion_summary")
  expect_equal(summary$status, "conductance_created")
})


test_that("convert_gazepoint_gsr_to_conductance can copy microsiemens values", {
  df <- data.frame(
    EDA = c(1.1, 1.2, NA)
  )

  out <- convert_gazepoint_gsr_to_conductance(
    df,
    gsr_col = "EDA",
    input_unit = "microsiemens",
    output_col = "conductance_us"
  )

  expect_equal(out$conductance_us, c(1.1, 1.2, NA))
  summary <- attr(out, "gsr_conversion_summary")
  expect_equal(summary$input_unit, "microsiemens")
})


test_that("convert_gazepoint_gsr_to_conductance validates arguments", {
  df <- data.frame(GSR = 1:3)

  expect_error(
    convert_gazepoint_gsr_to_conductance(1:3),
    "`data` must be"
  )

  expect_error(
    convert_gazepoint_gsr_to_conductance(df, gsr_col = "missing"),
    "not found"
  )

  expect_error(
    convert_gazepoint_gsr_to_conductance(df, output_col = ""),
    "`output_col`"
  )

  expect_error(
    convert_gazepoint_gsr_to_conductance(df, overwrite = NA),
    "`overwrite`"
  )

  expect_error(
    convert_gazepoint_gsr_to_conductance(data.frame(GSR_OHMS = letters[1:3])),
    "must be numeric"
  )
})


test_that("summarise_gazepoint_gsr_tonic_phasic creates tonic and phasic columns", {
  df <- data.frame(
    CNT = 1:10,
    GSR_US = c(1, 1.1, 1.0, 1.2, 2.0, 1.3, 1.2, 1.1, 1.0, 1.1)
  )

  out <- summarise_gazepoint_gsr_tonic_phasic(
    df,
    window_n = 3,
    peak_threshold = 0.4
  )

  expect_type(out, "list")
  expect_s3_class(out$data, "data.frame")
  expect_s3_class(out$summary, "data.frame")
  expect_true(all(c(
    "gsr_tonic",
    "gsr_phasic",
    "gsr_phasic_peak",
    "gsr_phasic_peak_threshold"
  ) %in% names(out$data)))

  expect_true(any(out$data$gsr_phasic_peak))
  expect_equal(out$settings$gsr_col, "GSR_US")
  expect_equal(out$summary$group, "all")
})


test_that("summarise_gazepoint_gsr_tonic_phasic respects groups", {
  df <- data.frame(
    USER = rep(c("P1", "P2"), each = 5),
    CNT = rep(1:5, 2),
    GSR_US = c(1, 1, 2, 1, 1, 2, 2, 3, 2, 2)
  )

  out <- summarise_gazepoint_gsr_tonic_phasic(
    df,
    group_cols = "USER",
    time_col = "CNT",
    window_n = 3,
    peak_threshold = 0.4
  )

  expect_equal(nrow(out$summary), 2)
  expect_true(all(out$summary$group %in% c("P1", "P2")))
  expect_true("gsr_phasic" %in% names(out$data))
})


test_that("summarise_gazepoint_gsr_tonic_phasic can use explicit GSR column", {
  df <- data.frame(
    custom_eda = c(1, 1.2, 1.1, 1.8, 1.1)
  )

  out <- summarise_gazepoint_gsr_tonic_phasic(
    df,
    gsr_col = "custom_eda",
    window_n = 3
  )

  expect_equal(out$settings$gsr_col, "custom_eda")
  expect_equal(out$summary$source_column, "custom_eda")
})


test_that("summarise_gazepoint_gsr_tonic_phasic handles missing values", {
  df <- data.frame(
    GSR_US = c(1, NA, 1.2, 2.0, NA, 1.1)
  )

  out <- summarise_gazepoint_gsr_tonic_phasic(
    df,
    window_n = 3,
    peak_threshold = 0.2
  )

  expect_equal(nrow(out$data), 6)
  expect_true(sum(!is.na(out$data$gsr_tonic)) >= 4)
  expect_true(sum(!is.na(out$data$gsr_phasic)) >= 4)
})


test_that("summarise_gazepoint_gsr_tonic_phasic validates arguments", {
  df <- data.frame(GSR_US = c(1, 2, 3))

  expect_error(
    summarise_gazepoint_gsr_tonic_phasic(1:3),
    "`data` must be"
  )

  expect_error(
    summarise_gazepoint_gsr_tonic_phasic(df, gsr_col = "missing"),
    "not found"
  )

  expect_error(
    summarise_gazepoint_gsr_tonic_phasic(df, window_n = 0),
    "`window_n`"
  )

  expect_error(
    summarise_gazepoint_gsr_tonic_phasic(df, peak_threshold = "high"),
    "`peak_threshold`"
  )

  expect_error(
    summarise_gazepoint_gsr_tonic_phasic(df, output_prefix = ""),
    "`output_prefix`"
  )

  expect_error(
    summarise_gazepoint_gsr_tonic_phasic(data.frame(GSR_US = letters[1:3])),
    "must be numeric"
  )
})


test_that("summarise_gazepoint_gsr_tonic_phasic requires a detectable GSR column", {
  df <- data.frame(
    HR = c(70, 71, 72)
  )

  expect_error(
    summarise_gazepoint_gsr_tonic_phasic(df),
    "No GSR/EDA column"
  )
})
