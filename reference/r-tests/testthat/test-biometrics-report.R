test_that("create_gazepoint_biometrics_report creates a report from data", {
  df <- data.frame(
    CNT = 1:5,
    GSR = c(1, 1.1, 1.2, 1.1, 1),
    HR = c(70, 71, 72, 71, 70),
    DIAL = c(40, 42, 44, 43, 41)
  )

  report <- create_gazepoint_biometrics_report(df)

  expect_s3_class(report, "gazepoint_biometrics_report")
  expect_s3_class(report$overview, "data.frame")
  expect_type(report$sections, "list")
  expect_type(report$tables, "list")
  expect_type(report$objects, "list")

  expect_equal(report$overview$n_rows, 5)
  expect_equal(report$overview$n_columns, 4)
  expect_true(report$overview$has_data)
  expect_true("schema_overview" %in% names(report$tables))
  expect_true("signal_validity" %in% names(report$tables))
})


test_that("create_gazepoint_biometrics_report can include supplied methods text and checklist", {
  df <- data.frame(
    CNT = 1:3,
    HR = c(70, 71, 72)
  )

  checklist <- data.frame(
    item = c("Sampling reported", "Artefact handling reported"),
    status = c("pass", "warn")
  )

  report <- create_gazepoint_biometrics_report(
    data = df,
    methods_text = "Biometric data were processed using gpbiometrics.",
    checklist = checklist
  )

  methods_section <- paste(report$sections$methods, collapse = "\n")
  checklist_section <- paste(report$sections$checklist, collapse = "\n")

  expect_match(methods_section, "gpbiometrics")
  expect_match(checklist_section, "Sampling reported")
  expect_match(checklist_section, "Artefact handling reported")
  expect_true(report$overview$has_methods_text)
  expect_true(report$overview$has_checklist)
})


test_that("create_gazepoint_biometrics_report collects user-supplied report tables", {
  df <- data.frame(
    CNT = 1:3,
    GSR = c(1, 2, 3)
  )

  extra_tables <- list(
    custom_summary = data.frame(
      metric = "mean_gsr",
      value = 2
    )
  )

  report <- create_gazepoint_biometrics_report(
    data = df,
    report_tables = extra_tables
  )

  expect_true("custom_summary" %in% names(report$tables))
  expect_equal(report$tables$custom_summary$metric, "mean_gsr")
})


test_that("create_gazepoint_biometrics_report supports workflow objects", {
  workflow <- list(
    overview = data.frame(
      n_rows = 10,
      status = "workflow_ok"
    )
  )

  report <- create_gazepoint_biometrics_report(workflow = workflow)

  expect_true(report$overview$has_workflow)
  expect_true("workflow_overview" %in% names(report$tables))
  expect_equal(report$tables$workflow_overview$status, "workflow_ok")
})


test_that("create_gazepoint_biometrics_report writes markdown output", {
  df <- data.frame(
    CNT = 1:3,
    HR = c(70, 71, 72)
  )

  path <- tempfile(fileext = ".md")

  report <- create_gazepoint_biometrics_report(
    data = df,
    output_file = path,
    format = "markdown"
  )

  expect_true(file.exists(path))
  text <- readLines(path, warn = FALSE)

  expect_true(any(grepl("# Gazepoint Biometrics report", text)))
  expect_true(any(grepl("Interpretation cautions", text)))
  expect_equal(report$output_file, normalizePath(path, winslash = "/", mustWork = FALSE))
})


test_that("create_gazepoint_biometrics_report writes html output", {
  df <- data.frame(
    CNT = 1:3,
    HR = c(70, 71, 72)
  )

  path <- tempfile(fileext = ".html")

  report <- create_gazepoint_biometrics_report(
    data = df,
    output_file = path,
    format = "html"
  )

  expect_true(file.exists(path))
  text <- readLines(path, warn = FALSE)

  expect_true(any(grepl("<!doctype html>", text, fixed = TRUE)))
  expect_true(any(grepl("<pre>", text, fixed = TRUE)))
  expect_equal(report$settings$format, "html")
})


test_that("create_gazepoint_biometrics_report protects existing files", {
  path <- tempfile(fileext = ".md")
  writeLines("existing", path)

  expect_error(
    create_gazepoint_biometrics_report(output_file = path),
    "already exists"
  )

  report <- create_gazepoint_biometrics_report(
    output_file = path,
    overwrite = TRUE
  )

  expect_true(file.exists(path))
  expect_s3_class(report, "gazepoint_biometrics_report")
})


test_that("create_gazepoint_biometrics_report validates arguments", {
  expect_error(
    create_gazepoint_biometrics_report(data = 1:3),
    "`data` must be"
  )

  expect_error(
    create_gazepoint_biometrics_report(title = ""),
    "`title`"
  )

  expect_error(
    create_gazepoint_biometrics_report(subtitle = 1),
    "`subtitle`"
  )

  expect_error(
    create_gazepoint_biometrics_report(output_file = ""),
    "`output_file`"
  )

  expect_error(
    create_gazepoint_biometrics_report(include_timestamp = NA),
    "`include_timestamp`"
  )

  expect_error(
    create_gazepoint_biometrics_report(overwrite = NA),
    "`overwrite`"
  )

  expect_error(
    create_gazepoint_biometrics_report(max_table_rows = 0),
    "`max_table_rows`"
  )
})


test_that("create_gazepoint_biometrics_report includes conservative interpretation cautions", {
  report <- create_gazepoint_biometrics_report()

  cautions <- paste(report$settings$cautions, collapse = " ")

  expect_match(cautions, "GSR/EDA")
  expect_match(cautions, "not emotional valence")
  expect_match(cautions, "Raw HRV")
  expect_match(cautions, "genuine IBI/RR")
  expect_match(cautions, "visual attention")
})
