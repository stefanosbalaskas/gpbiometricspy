test_that("synthetic kiosk demo exports are available and importable", {
  demo_dir <- system.file(
    "extdata",
    "gazepoint_biometrics_kiosk_demo_exports",
    package = "gpbiometrics"
  )

  expect_true(dir.exists(demo_dir))

  all_gaze_files <- list.files(demo_dir, pattern = "_all_gaze\\.csv$", full.names = TRUE)

  expect_equal(length(all_gaze_files), 36)

  overview_file <- file.path(demo_dir, "synthetic_kiosk_overview.csv")
  trial_design_file <- file.path(demo_dir, "synthetic_kiosk_trial_design.csv")
  readme_file <- file.path(demo_dir, "README.txt")

  expect_true(file.exists(overview_file))
  expect_true(file.exists(trial_design_file))
  expect_true(file.exists(readme_file))

  first_file <- all_gaze_files[1]

  dat <- import_gazepoint_biometrics(first_file)

  expect_s3_class(dat, "data.frame")
  expect_equal(ncol(dat), 67)
  expect_true(nrow(dat) > 0)

  expected_columns <- c(
    "MEDIA_ID", "MEDIA_NAME", "CNT", "TIME", "FPOGX", "FPOGY",
    "AOI", "LPMM", "RPMM", "GSR_US", "HR", "IBI",
    "DIAL", "TTL0", "TTL1", "TTL2", "TTL3", "TTL4", "TTL5", "TTL6",
    "interface_complexity", "feedback_clarity", "synthetic_scenario"
  )

  expect_true(all(expected_columns %in% names(dat)))

  validation <- validate_gazepoint_biometrics(dat)

  expect_equal(validation$overview$issue_count, 0)
  expect_true(validation$overview$active_signal_count >= 3)
})
