test_that("check_gazepoint_biometric_columns detects known columns", {
  dat <- data.frame(
    TIME = c(0.01, 0.02),
    GSR = c(500000, 510000),
    GSR_US = c(2.0, 1.96),
    GSRV = c(1, 1),
    HR = c(75, 76),
    HRV = c(1, 1),
    HRP = c(0.1, 0.2),
    IBI = c(0.80, 0.79),
    DIAL = c(0.2, 0.4),
    DIALV = c(1, 1)
  )

  cols <- check_gazepoint_biometric_columns(dat)

  expect_true(cols$present[cols$column == "GSR_US"])
  expect_true(cols$present[cols$column == "HR"])
  expect_true(cols$present[cols$column == "IBI"])
  expect_true(cols$present[cols$column == "DIAL"])
})


test_that("detect_active_biometric_channels identifies active signals", {
  dat <- data.frame(
    GSR_US = c(2.0, 2.1, 2.2),
    GSRV = c(1, 1, 1),
    HR = c(75, 76, 77),
    HRV = c(1, 1, 1),
    DIAL = c(0.1, 0.2, 0.3),
    DIALV = c(1, 1, 1)
  )

  active <- detect_active_biometric_channels(dat)

  expect_true(active$active[active$signal == "gsr_eda"])
  expect_true(active$active[active$signal == "heart_rate"])
  expect_true(active$active[active$signal == "engagement_dial"])
})


test_that("detect_active_biometric_channels identifies inactive signals", {
  dat <- data.frame(
    GSR_US = c(0, 0, 0),
    GSRV = c(0, 0, 0),
    HR = c(0, 0, 0),
    HRV = c(0, 0, 0),
    DIAL = c(0, 0, 0),
    DIALV = c(0, 0, 0)
  )

  active <- detect_active_biometric_channels(dat)

  expect_false(active$active[active$signal == "gsr_eda"])
  expect_false(active$active[active$signal == "heart_rate"])
  expect_false(active$active[active$signal == "engagement_dial"])
})


test_that("import_gazepoint_biometrics imports CSV and drops empty trailing column", {
  tmp <- tempfile(fileext = ".csv")

  writeLines(
    c(
      "TIME,GSR_US,GSRV,HR,HRV,DIAL,DIALV,",
      "0.01,2.0,1,75,1,0.1,1,",
      "0.02,2.1,1,76,1,0.2,1,"
    ),
    tmp,
    useBytes = TRUE
  )

  dat <- import_gazepoint_biometrics(tmp)

  expect_s3_class(dat, "gazepoint_biometrics")
  expect_true("GSR_US" %in% names(dat))
  expect_true("HR" %in% names(dat))
  expect_true("DIAL" %in% names(dat))
  expect_false(any(names(dat) == ""))

  cols <- attr(dat, "biometric_columns")
  expect_true(is.data.frame(cols))
})
test_that("detect_active_biometric_channels reports a clear summary column", {
  dat <- data.frame(
    GSR = c(500000, 510000, 520000),
    GSR_US = c(1.1, 1.2, 1.3),
    GSRV = c(1, 1, 1),
    HR = c(70, 72, 74),
    HRV = c(1, 1, 1),
    DIAL = c(0.1, 0.2, 0.3),
    DIALV = c(1, 1, 1)
  )

  out <- detect_active_biometric_channels(dat)

  gsr <- out[out$signal == "gsr_eda", ]

  expect_equal(gsr$summary_column, "GSR_US")
  expect_equal(gsr$min_value, 1.1)
  expect_equal(gsr$max_value, 1.3)
})
