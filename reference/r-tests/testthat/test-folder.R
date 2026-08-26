test_that("import_gazepoint_biometric_folder imports multiple biometric files", {
  folder <- tempfile("gazepoint_folder_")
  dir.create(folder)

  file_one <- file.path(folder, "User 0_all_gaze.csv")
  file_two <- file.path(folder, "User 0_fixations.csv")
  file_summary <- file.path(folder, "Data_Summary_export_test.csv")

  writeLines(
    c(
      "TIME,GSR_US,GSRV,HR,HRV,DIAL,DIALV,",
      "0.01,2.0,1,75,1,0.1,1,",
      "0.02,2.1,1,76,1,0.2,1,"
    ),
    file_one,
    useBytes = TRUE
  )

  writeLines(
    c(
      "TIME,FPOGX,FPOGY,FPOGS,FPOGD,FPOGID,GSR_US,GSRV,HR,HRV,DIAL,DIALV,",
      "0.03,0.5,0.6,0.01,0.20,1,2.2,1,77,1,0.3,1,",
      "0.04,0.6,0.7,0.03,0.30,2,2.3,1,78,1,0.4,1,"
    ),
    file_two,
    useBytes = TRUE
  )

  writeLines(
    c(
      "Gazepoint Analysis,v7.2.0",
      "Processed on,example",
      "AOI Summary"
    ),
    file_summary,
    useBytes = TRUE
  )

  dat <- import_gazepoint_biometric_folder(folder)

  expect_s3_class(dat, "gazepoint_biometrics_folder")
  expect_equal(nrow(dat), 4)
  expect_true("source_file" %in% names(dat))
  expect_true("source_type" %in% names(dat))
  expect_true("source_participant" %in% names(dat))
  expect_true(all(c("GSR_US", "HR", "DIAL") %in% names(dat)))
  expect_false(any(grepl("Data_Summary", dat$source_file)))

  expect_true(all(c("all_gaze", "fixations") %in% unique(dat$source_type)))
  expect_true("User 0" %in% unique(dat$source_participant))

  active <- attr(dat, "active_channels")
  expect_true(is.data.frame(active))
  expect_true(active$active[active$signal == "gsr_eda"])
  expect_true(active$active[active$signal == "heart_rate"])
  expect_true(active$active[active$signal == "engagement_dial"])
})


test_that("import_gazepoint_biometric_folder rejects missing folders", {
  expect_error(
    import_gazepoint_biometric_folder("folder_that_does_not_exist"),
    "Folder does not exist"
  )
})


test_that("import_gazepoint_biometric_folder skips non-biometric CSV files", {
  folder <- tempfile("gazepoint_folder_")
  dir.create(folder)

  file_one <- file.path(folder, "User 0_all_gaze.csv")

  writeLines(
    c(
      "TIME,X,Y,",
      "0.01,1,2,",
      "0.02,3,4,"
    ),
    file_one,
    useBytes = TRUE
  )

  expect_error(
    import_gazepoint_biometric_folder(folder),
    "none contained known Gazepoint Biometrics columns"
  )
})
