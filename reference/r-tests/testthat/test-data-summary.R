test_that("import_gazepoint_data_summary parses metadata and sections", {
  tmp <- tempfile(fileext = ".csv")

  writeLines(
    c(
      "Gazepoint Analysis,v7.2.0",
      "Processed on,Thu Jun 11 23:50:26 2026",
      "",
      "Note: -1 values indicate an AOI that was never viewed",
      "AOI Summary",
      "Media ID, Media Name,AOI ID,AOI Name,Viewers (#),Ave Time Viewed (sec),",
      "0,NewMedia0,2,AOI 2,2,1.400,",
      "1,NewMedia1,0,AOI 0,2,2.235,",
      "",
      "AOI Statistics (for each user)",
      "Media ID, Media Name,AOI ID,AOI Name,User ID,User Name,Time Viewed (sec),Fixations (#),Ave Dial (0-1),Ave GSR (kOhm),Ave Heart Rate (BPM),Ave Interbeat Interval (s),Ave Left Pupil (mm),Ave Right Pupil (mm),",
      "0,NewMedia0,2,AOI 2,4,User 4,0.937,3,1.000,815880.062,88.442,0.678,7.041,5.707,",
      "0,NewMedia0,2,AOI 2,5,User 5,1.863,7,1.000,362668.094,87.988,0.681,4.605,5.451,"
    ),
    tmp,
    useBytes = TRUE
  )

  out <- import_gazepoint_data_summary(tmp)

  expect_s3_class(out, "gazepoint_data_summary")
  expect_true(is.data.frame(out$metadata))
  expect_true(is.data.frame(out$aoi_summary))
  expect_true(is.data.frame(out$aoi_statistics))

  expect_equal(out$metadata$software, "Gazepoint Analysis")
  expect_equal(out$metadata$version, "v7.2.0")
  expect_equal(nrow(out$aoi_summary), 2)
  expect_equal(nrow(out$aoi_statistics), 2)

  expect_true("Ave Dial (0-1)" %in% names(out$aoi_statistics))
  expect_true("Ave GSR (kOhm)" %in% names(out$aoi_statistics))
  expect_true("Ave Heart Rate (BPM)" %in% names(out$aoi_statistics))
  expect_true("Ave Interbeat Interval (s)" %in% names(out$aoi_statistics))

  expect_equal(out$aoi_statistics[["Ave Heart Rate (BPM)"]][1], 88.442)
  expect_equal(out$aoi_statistics[["Ave Dial (0-1)"]][1], 1)
})


test_that("import_gazepoint_data_summary preserves source file column", {
  tmp <- tempfile("Data_Summary_export_test_", fileext = ".csv")

  writeLines(
    c(
      "Gazepoint Analysis,v7.2.0",
      "Processed on,example",
      "",
      "AOI Summary",
      "Media ID,AOI ID,Viewers (#),",
      "0,2,2,",
      "",
      "AOI Statistics (for each user)",
      "Media ID,AOI ID,User ID,Ave Dial (0-1),",
      "0,2,4,1.000,"
    ),
    tmp,
    useBytes = TRUE
  )

  out <- import_gazepoint_data_summary(tmp)

  expect_true("source_file" %in% names(out$aoi_summary))
  expect_true("source_file" %in% names(out$aoi_statistics))
  expect_equal(out$aoi_summary$source_file[1], basename(tmp))
})


test_that("import_gazepoint_data_summary returns empty section when section is absent", {
  tmp <- tempfile(fileext = ".csv")

  writeLines(
    c(
      "Gazepoint Analysis,v7.2.0",
      "Processed on,example"
    ),
    tmp,
    useBytes = TRUE
  )

  out <- import_gazepoint_data_summary(tmp)

  expect_true(is.data.frame(out$aoi_summary))
  expect_true(is.data.frame(out$aoi_statistics))
  expect_equal(nrow(out$aoi_summary), 0)
  expect_equal(nrow(out$aoi_statistics), 0)
})


test_that("import_gazepoint_data_summary rejects missing file", {
  expect_error(
    import_gazepoint_data_summary("missing_data_summary.csv"),
    "File does not exist"
  )
})
