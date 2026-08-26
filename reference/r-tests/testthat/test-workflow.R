test_that("run_gazepoint_biometrics_workflow runs end-to-end on folder exports", {
  folder <- tempfile("gazepoint_workflow_")
  dir.create(folder)

  file_one <- file.path(folder, "User 0_all_gaze.csv")
  file_two <- file.path(folder, "User 0_fixations.csv")

  writeLines(
    c(
      "USER,MEDIA_ID,CNT,GSR_US,GSRV,HR,HRV,DIAL,DIALV,TTL0,TTLV,",
      "U1,1,1,2.0,1,70,1,0.1,1,1007,1,",
      "U1,1,2,2.2,1,72,1,0.2,1,1008,1,"
    ),
    file_one,
    useBytes = TRUE
  )

  writeLines(
    c(
      "USER,MEDIA_ID,CNT,FPOGX,FPOGY,FPOGS,FPOGD,FPOGID,GSR_US,GSRV,HR,HRV,DIAL,DIALV,TTL0,TTLV,",
      "U1,1,3,0.5,0.6,0.01,0.20,1,2.4,1,74,1,0.3,1,1008,1,",
      "U1,1,4,0.6,0.7,0.03,0.30,2,2.6,1,76,1,0.4,1,1009,1,"
    ),
    file_two,
    useBytes = TRUE
  )

  workflow <- run_gazepoint_biometrics_workflow(
    path = folder,
    group_columns = c("USER", "MEDIA_ID"),
    include_fixations = TRUE
  )

  expect_s3_class(workflow, "gazepoint_biometrics_workflow")
  expect_true(is.data.frame(workflow$overview))
  expect_true(is.data.frame(workflow$data))
  expect_true(is.list(workflow$validation))
  expect_true(is.data.frame(workflow$missingness))
  expect_true(is.data.frame(workflow$quality))
  expect_true(is.data.frame(workflow$sampling))
  expect_true(is.data.frame(workflow$windows))
  expect_s3_class(
    workflow$exclusion_recommendations,
    "gazepoint_biometric_exclusion_recommendations"
  )
  expect_true(is.data.frame(workflow$ttl_events))
  expect_s3_class(workflow$checklist, "gazepoint_biometrics_checklist")
  expect_type(workflow$methods_text, "character")

  expect_equal(workflow$overview$n_rows, 4)
  expect_equal(workflow$overview$source_file_count, 2)
  expect_true(workflow$overview$has_sampling_audit)
  expect_true(workflow$overview$sampling_group_count > 0)
  expect_true(workflow$overview$has_window_summaries)
  expect_true(workflow$overview$has_exclusion_recommendations)
  expect_true(workflow$overview$has_ttl_events)
  expect_true(workflow$overview$ttl_event_count > 0)
  expect_equal(nrow(workflow$windows), 1)
  expect_true("gsr_mean_value" %in% names(workflow$windows))
})


test_that("summarise_gazepoint_biometrics_workflow summarises workflow object", {
  folder <- tempfile("gazepoint_workflow_")
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

  summary <- summarise_gazepoint_biometrics_workflow(workflow)

  expect_true(is.data.frame(summary))
  expect_equal(nrow(summary), 1)
  expect_equal(summary$n_rows, 2)
  expect_true(summary$active_gsr_eda)
  expect_true(summary$active_heart_rate)
  expect_true(summary$active_engagement_dial)
  expect_true(summary$active_ttl_marker)
  expect_true(summary$has_sampling_audit)
  expect_true(summary$sampling_group_count > 0)
  expect_true(summary$has_window_summaries)
  expect_true(summary$has_exclusion_recommendations)
  expect_true(summary$has_ttl_events)
  expect_true(summary$ttl_event_count > 0)
})


test_that("run_gazepoint_biometrics_workflow can skip exclusion recommendations", {
  folder <- tempfile("gazepoint_workflow_")
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
    group_columns = c("USER", "MEDIA_ID"),
    create_exclusion_recommendations = FALSE
  )

  expect_true(is.data.frame(workflow$windows))
  expect_null(workflow$exclusion_recommendations)
  expect_false(workflow$overview$has_exclusion_recommendations)

  summary <- summarise_gazepoint_biometrics_workflow(workflow)

  expect_false(summary$has_exclusion_recommendations)
})


test_that("run_gazepoint_biometrics_workflow can skip TTL extraction", {
  folder <- tempfile("gazepoint_workflow_")
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
    group_columns = c("USER", "MEDIA_ID"),
    extract_ttl_events = FALSE
  )

  expect_null(workflow$ttl_events)
  expect_false(workflow$overview$has_ttl_events)
  expect_true(is.na(workflow$overview$ttl_event_count))

  summary <- summarise_gazepoint_biometrics_workflow(workflow)

  expect_false(summary$has_ttl_events)
  expect_true(is.na(summary$ttl_event_count))
})


test_that("run_gazepoint_biometrics_workflow can skip sampling audit", {
  folder <- tempfile("gazepoint_workflow_")
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
    group_columns = c("USER", "MEDIA_ID"),
    audit_sampling = FALSE
  )

  expect_null(workflow$sampling)
  expect_false(workflow$overview$has_sampling_audit)
  expect_true(is.na(workflow$overview$sampling_group_count))

  summary <- summarise_gazepoint_biometrics_workflow(workflow)

  expect_false(summary$has_sampling_audit)
  expect_true(is.na(summary$sampling_group_count))
})


test_that("summarise_gazepoint_biometrics_workflow rejects invalid object", {
  expect_error(
    summarise_gazepoint_biometrics_workflow(list()),
    "must be produced"
  )
})
