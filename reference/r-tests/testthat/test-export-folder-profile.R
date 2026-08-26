test_that("profile_gazepoint_export_folder profiles a synthetic folder", {
  tmp <- tempfile("gazepoint_export_folder_")
  dir.create(tmp)

  dat1 <- data.frame(
    CNT = seq_len(10),
    TIME = seq(0, 0.15, length.out = 10),
    TTL0 = c(0, 0, 1, rep(0, 7)),
    AOI = rep(c("button", "text"), each = 5),
    FPOGX = runif(10),
    FPOGY = runif(10),
    LPMM = rnorm(10, 3, 0.1),
    GSR_US = c(0, 0, runif(8)),
    HR = rep(70, 10),
    IBI = rep(850, 10),
    HRP = sin(seq(0, 2 * pi, length.out = 10)),
    DIAL = seq(0, 1, length.out = 10),
    stringsAsFactors = FALSE
  )

  dat2 <- dat1
  dat2$GSR_US <- 0
  dat2$AOI <- "menu"

  utils::write.csv(dat1, file.path(tmp, "participant_001.csv"), row.names = FALSE)
  utils::write.csv(dat2, file.path(tmp, "participant_002.csv"), row.names = FALSE)

  profile <- profile_gazepoint_export_folder(tmp)

  expect_s3_class(profile, "gazepoint_export_folder_profile")
  expect_true(is.data.frame(profile$overview))
  expect_true(is.data.frame(profile$files))
  expect_true(is.data.frame(profile$columns))
  expect_true(is.data.frame(profile$warnings))

  expect_equal(profile$overview$n_files, 2L)
  expect_equal(profile$overview$n_readable_files, 2L)
  expect_true(profile$overview$any_time_columns)
  expect_true(profile$overview$any_ttl_columns)
  expect_true(profile$overview$any_aoi_columns)
  expect_true(profile$overview$any_signal_columns)

  expect_true(any(profile$columns$role == "time"))
  expect_true(any(profile$columns$role == "ttl_event"))
  expect_true(any(profile$columns$role == "aoi"))
  expect_true(any(profile$columns$role == "gaze"))
  expect_true(any(profile$columns$role == "pupil"))
  expect_true(any(profile$columns$role == "eda_gsr"))
  expect_true(any(profile$columns$role == "heart_rate"))
  expect_true(any(profile$columns$role == "ibi_rr"))
  expect_true(any(profile$columns$role == "ppg_pulse"))
  expect_true(any(profile$columns$role == "engagement_dial"))
})

test_that("profile_gazepoint_export_folder handles empty matching results", {
  tmp <- tempfile("gazepoint_empty_folder_")
  dir.create(tmp)

  profile <- profile_gazepoint_export_folder(tmp)

  expect_s3_class(profile, "gazepoint_export_folder_profile")
  expect_equal(profile$overview$n_files, 0L)
  expect_equal(profile$overview$n_readable_files, 0L)
  expect_true(any(profile$warnings$issue == "no_matching_files"))
})

test_that("profile_gazepoint_export_folder records read errors", {
  tmp <- tempfile("gazepoint_bad_folder_")
  dir.create(tmp)

  bad_file <- file.path(tmp, "bad.csv")
  writeBin(as.raw(c(0xff, 0xfe, 0x00, 0x00)), bad_file)

  profile <- profile_gazepoint_export_folder(tmp)

  expect_s3_class(profile, "gazepoint_export_folder_profile")
  expect_equal(profile$overview$n_files, 1L)
  expect_true(profile$overview$n_read_errors >= 0L)
  expect_true("read_error" %in% names(profile$files))
})

test_that("compare_gazepoint_export_profiles compares profiles", {
  tmp1 <- tempfile("gazepoint_profile_a_")
  tmp2 <- tempfile("gazepoint_profile_b_")
  dir.create(tmp1)
  dir.create(tmp2)

  dat_a <- data.frame(
    CNT = 1:5,
    GSR_US = seq(0.1, 0.5, length.out = 5),
    HR = rep(70, 5)
  )

  dat_b <- data.frame(
    CNT = 1:5,
    AOI = rep("button", 5),
    LPMM = rnorm(5, 3, 0.1),
    DIAL = seq(0, 1, length.out = 5)
  )

  utils::write.csv(dat_a, file.path(tmp1, "a.csv"), row.names = FALSE)
  utils::write.csv(dat_b, file.path(tmp2, "b.csv"), row.names = FALSE)

  p1 <- profile_gazepoint_export_folder(tmp1)
  p2 <- profile_gazepoint_export_folder(tmp2)

  comparison <- compare_gazepoint_export_profiles(
    p1,
    p2,
    labels = c("eda_hr", "aoi_pupil")
  )

  expect_s3_class(comparison, "gazepoint_export_profile_comparison")
  expect_true(is.data.frame(comparison$overview))
  expect_true(is.data.frame(comparison$role_coverage))
  expect_true(is.data.frame(comparison$column_presence))
  expect_equal(length(unique(comparison$overview$profile)), 2L)
})

test_that("write_gazepoint_export_profile writes expected files", {
  tmp <- tempfile("gazepoint_write_source_")
  out <- tempfile("gazepoint_write_output_")
  dir.create(tmp)

  dat <- data.frame(
    CNT = 1:5,
    TTL0 = c(0, 1, 0, 0, 0),
    GSR_US = runif(5)
  )

  utils::write.csv(dat, file.path(tmp, "one.csv"), row.names = FALSE)

  profile <- profile_gazepoint_export_folder(tmp)

  written <- write_gazepoint_export_profile(
    profile,
    path = out,
    prefix = "test_profile",
    overwrite = TRUE
  )

  expect_true(is.data.frame(written))
  expect_equal(NROW(written), 5L)
  expect_true(all(file.exists(written$file)))
})

test_that("plot_gazepoint_export_profile returns ggplot objects", {
  skip_if_not_installed("ggplot2")

  tmp <- tempfile("gazepoint_plot_source_")
  dir.create(tmp)

  dat <- data.frame(
    CNT = 1:10,
    TTL0 = c(0, 1, rep(0, 8)),
    AOI = rep(c("a", "b"), each = 5),
    GSR_US = c(rep(0, 5), runif(5)),
    HR = rep(70, 10),
    stringsAsFactors = FALSE
  )

  utils::write.csv(dat, file.path(tmp, "plot.csv"), row.names = FALSE)

  profile <- profile_gazepoint_export_folder(tmp)

  expect_s3_class(plot_gazepoint_export_profile(profile, type = "files"), "ggplot")
  expect_s3_class(plot_gazepoint_export_profile(profile, type = "roles"), "ggplot")
  expect_s3_class(plot_gazepoint_export_profile(profile, type = "missingness"), "ggplot")
  expect_s3_class(plot_gazepoint_export_profile(profile, type = "activity"), "ggplot")
})

test_that("profile_gazepoint_export_folder validates inputs", {
  expect_error(
    profile_gazepoint_export_folder("not_a_real_folder"),
    "does not exist"
  )

  tmp <- tempfile("gazepoint_input_validation_")
  dir.create(tmp)

  expect_error(
    profile_gazepoint_export_folder(tmp, max_files = 0),
    "positive"
  )

  expect_error(
    profile_gazepoint_export_folder(tmp, max_rows = 0),
    "positive"
  )
})
