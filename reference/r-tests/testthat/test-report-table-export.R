test_that("write_gazepoint_biometrics_report_tables writes named data frames", {
  output_dir <- tempfile("gazepoint_report_tables_")

  tables <- list(
    overview = data.frame(n_rows = 2, n_columns = 5),
    quality = data.frame(signal = "gsr_eda", usable_pct = 100),
    missing = data.frame(message = "No table supplied.")
  )

  index <- write_gazepoint_biometrics_report_tables(
    tables = tables,
    output_dir = output_dir,
    prefix = "test_report"
  )

  expect_true(is.data.frame(index))
  expect_equal(nrow(index), 3)
  expect_equal(sum(index$written), 2)
  expect_equal(
    index$skipped_reason[index$table == "missing"],
    "message_only_table"
  )

  written_files <- index$file[index$written]

  expect_true(all(file.exists(written_files)))

  overview <- utils::read.csv(
    index$file[index$table == "overview"],
    stringsAsFactors = FALSE
  )

  expect_equal(overview$n_rows, 2)
})


test_that("write_gazepoint_biometrics_report_tables can write workflow report tables", {
  folder <- tempfile("gazepoint_report_export_")
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

  output_dir <- tempfile("gazepoint_report_tables_")

  index <- write_gazepoint_biometrics_report_tables(
    tables = workflow,
    output_dir = output_dir,
    prefix = "workflow_report"
  )

  expect_true(is.data.frame(index))
  expect_true(any(index$table == "overview"))
  expect_true(any(index$table == "quality"))
  expect_true(any(index$written))
  expect_true(all(file.exists(index$file[index$written])))
})


test_that("write_gazepoint_biometrics_report_tables respects overwrite false", {
  output_dir <- tempfile("gazepoint_report_tables_")

  tables <- list(
    overview = data.frame(n_rows = 2)
  )

  first <- write_gazepoint_biometrics_report_tables(
    tables = tables,
    output_dir = output_dir,
    prefix = "test_report"
  )

  second <- write_gazepoint_biometrics_report_tables(
    tables = tables,
    output_dir = output_dir,
    prefix = "test_report",
    overwrite = FALSE
  )

  expect_true(first$written)
  expect_false(second$written)
  expect_equal(second$skipped_reason, "file_exists")
})


test_that("write_gazepoint_biometrics_report_tables can include message tables", {
  output_dir <- tempfile("gazepoint_report_tables_")

  tables <- list(
    missing = data.frame(message = "No table supplied.")
  )

  index <- write_gazepoint_biometrics_report_tables(
    tables = tables,
    output_dir = output_dir,
    include_empty_message_tables = TRUE
  )

  expect_true(index$written)
  expect_true(file.exists(index$file))
})


test_that("write_gazepoint_biometrics_report_tables rejects invalid input", {
  expect_error(
    write_gazepoint_biometrics_report_tables(
      tables = data.frame(x = 1),
      output_dir = tempfile("gazepoint_report_tables_")
    ),
    "tables"
  )
})
