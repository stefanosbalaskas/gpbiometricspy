test_that("create_gazepoint_biometrics_report_tables works from workflow object", {
  folder <- tempfile("gazepoint_report_tables_")
  dir.create(folder)

  file_one <- file.path(folder, "User 0_all_gaze.csv")

  writeLines(
    c(
      "USER,MEDIA_ID,CNT,GSR_US,GSRV,HR,HRV,DIAL,DIALV,TTL0,TTLV,",
      "U1,1,1,2.0,1,70,1,0.1,1,1007,1,",
      "U1,1,2,2.2,1,72,1,0.2,1,1008,1,"
    ),
    file_one,
    useBytes = TRUE
  )

  workflow <- run_gazepoint_biometrics_workflow(
    path = folder,
    group_columns = c("USER", "MEDIA_ID")
  )

  tables <- create_gazepoint_biometrics_report_tables(workflow)

  expect_s3_class(tables, "gazepoint_biometrics_report_tables")
  expect_true(is.data.frame(tables$overview))
  expect_true(is.data.frame(tables$diagnostics))
  expect_true(is.data.frame(tables$channels))
  expect_true(is.data.frame(tables$quality))
  expect_true(is.data.frame(tables$sampling))
  expect_true(is.data.frame(tables$window_recommendations))
  expect_true(is.data.frame(tables$participant_recommendations))
  expect_true(is.data.frame(tables$ttl_events))

  expect_true("final_status" %in% names(tables$diagnostics))
  expect_true("signal" %in% names(tables$channels))
  expect_true("usable_pct" %in% names(tables$quality))
  expect_true("time_column" %in% names(tables$sampling))
  expect_true("recommendation" %in% names(tables$window_recommendations))
  expect_true("participant_recommendation" %in% names(tables$participant_recommendations))
  expect_true("ttl_value" %in% names(tables$ttl_events))
})


test_that("create_gazepoint_biometrics_report_tables works from separate components", {
  dat <- data.frame(
    GSR_US = c(1.1, 1.2),
    GSRV = c(1, 1),
    HR = c(70, 72),
    HRV = c(1, 1),
    DIAL = c(1, 1),
    DIALV = c(1, 1),
    CNT = c(1, 2)
  )

  validation <- validate_gazepoint_biometrics(dat)

  quality <- combine_gazepoint_tables(list(
    audit_gazepoint_gsr_quality(dat)
  ))

  sampling <- audit_gazepoint_biometric_sampling(
    dat,
    time_column = "CNT",
    time_unit = "samples"
  )

  diagnostics <- data.frame(
    final_status = "pass",
    diagnostic_reasons = "workflow diagnostics passed",
    validation_issue_count = 0,
    stringsAsFactors = FALSE
  )

  tables <- create_gazepoint_biometrics_report_tables(
    validation = validation,
    quality = quality,
    sampling = sampling,
    diagnostics = diagnostics
  )

  expect_true(is.data.frame(tables$overview))
  expect_true(is.data.frame(tables$diagnostics))
  expect_true(is.data.frame(tables$channels))
  expect_true(is.data.frame(tables$quality))
  expect_true(is.data.frame(tables$sampling))
  expect_true(is.data.frame(tables$window_recommendations))
  expect_true("message" %in% names(tables$window_recommendations))
  expect_equal(tables$diagnostics$final_status, "pass")
})


test_that("create_gazepoint_biometrics_report_tables returns placeholders when optional tables are missing", {
  validation <- validate_gazepoint_biometrics(
    data.frame(
      GSR_US = c(1.1, 1.2),
      GSRV = c(1, 1),
      CNT = c(1, 2)
    )
  )

  tables <- create_gazepoint_biometrics_report_tables(
    validation = validation
  )

  expect_true(is.data.frame(tables$diagnostics))
  expect_true(is.data.frame(tables$sampling))
  expect_true("message" %in% names(tables$diagnostics))
  expect_true("message" %in% names(tables$sampling))
})


test_that("create_gazepoint_biometrics_report_tables limits TTL event rows", {
  ttl_events <- data.frame(
    row_index = 1:5,
    event_order = 1:5,
    ttl_channel = "TTL0",
    ttl_value = 1001:1005,
    previous_ttl_value = c(NA, 1001:1004),
    CNT = 1:5,
    ttl_validity = 1
  )

  tables <- create_gazepoint_biometrics_report_tables(
    ttl_events = ttl_events,
    max_ttl_events = 2
  )

  expect_equal(nrow(tables$ttl_events), 2)
})


test_that("create_gazepoint_biometrics_report_tables rejects invalid workflow object", {
  expect_error(
    create_gazepoint_biometrics_report_tables(workflow = list()),
    "workflow"
  )
})
