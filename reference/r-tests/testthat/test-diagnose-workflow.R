test_that("diagnose_gazepoint_biometrics_workflow returns pass for clean workflow", {
  folder <- tempfile("gazepoint_diagnose_")
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

  out <- diagnose_gazepoint_biometrics_workflow(workflow)

  expect_true(is.data.frame(out))
  expect_equal(nrow(out), 1)
  expect_equal(out$final_status, "pass")
  expect_true(out$active_gsr_eda)
  expect_true(out$active_heart_rate)
})


test_that("diagnose_gazepoint_biometrics_workflow fails when excluded windows exceed threshold", {
  windows <- data.frame(
    source_participant = c("User 0", "User 0"),
    MEDIA_ID = c(0, 1),
    gsr_usable_pct = c(0, 0),
    hr_usable_pct = c(0, 0),
    dial_usable_pct = c(0, 0)
  )

  folder <- tempfile("gazepoint_diagnose_")
  dir.create(folder)

  file_one <- file.path(folder, "User 0_all_gaze.csv")

  writeLines(
    c(
      "USER,MEDIA_ID,CNT,GSR_US,GSRV,HR,HRV,DIAL,DIALV,TTL0,TTLV,",
      "U1,1,1,0,0,0,0,0,0,0,0,",
      "U1,1,2,0,0,0,0,0,0,0,0,"
    ),
    file_one,
    useBytes = TRUE
  )

  workflow <- run_gazepoint_biometrics_workflow(
    path = folder,
    group_columns = c("USER", "MEDIA_ID"),
    require_active_signal = FALSE
  )

  workflow$exclusion_recommendations <- recommend_gazepoint_biometric_exclusions(
    windows,
    data_is_window_summary = TRUE
  )

  out <- diagnose_gazepoint_biometrics_workflow(
    workflow,
    require_gsr = FALSE,
    require_hr = FALSE
  )

  expect_equal(out$final_status, "fail")
  expect_true(out$exclude_window_pct > 25)
})

test_that("diagnose_gazepoint_biometrics_workflow reviews low usable quality", {
  folder <- tempfile("gazepoint_diagnose_")
  dir.create(folder)

  file_one <- file.path(folder, "User 0_all_gaze.csv")

  writeLines(
    c(
      "USER,MEDIA_ID,CNT,GSR_US,GSRV,HR,HRV,DIAL,DIALV,TTL0,TTLV,",
      "U1,1,1,0,0,70,1,1,1,1007,1,",
      "U1,1,2,0,0,72,1,1,1,1008,1,",
      "U1,1,3,2.2,1,74,1,1,1,1009,1,"
    ),
    file_one,
    useBytes = TRUE
  )

  workflow <- run_gazepoint_biometrics_workflow(
    path = folder,
    group_columns = c("USER", "MEDIA_ID")
  )

  out <- diagnose_gazepoint_biometrics_workflow(
    workflow,
    max_exclude_window_pct = 100
  )

  expect_equal(out$final_status, "review")
  expect_true(out$low_quality_signal_count >= 1)
  expect_true(grepl("low usable coverage", out$diagnostic_reasons))
})

test_that("diagnose_gazepoint_biometrics_workflow rejects invalid object", {
  expect_error(
    diagnose_gazepoint_biometrics_workflow(list()),
    "workflow"
  )
})
