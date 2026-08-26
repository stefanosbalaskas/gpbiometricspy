test_that("biometrics checklist includes workflow capabilities and guidance", {
  dat <- data.frame(
    GSR_US = c(0, 1.1, 1.2, 1.3),
    HR = c(70, 71, 72, 73),
    IBI = c(0.80, 0.82, 0.81, 0.83),
    DIAL = c(0, 1, 1, 1),
    TTL0 = c(1, 0, 0, 0)
  )

  checklist <- create_gazepoint_biometrics_checklist(dat)

  expect_s3_class(checklist, "gazepoint_biometrics_checklist")
  expect_true("workflow_capabilities" %in% names(checklist))
  expect_true("feature_inventory" %in% names(checklist))
  expect_true("reporting_guidance" %in% names(checklist))

  expect_true(is.data.frame(checklist$workflow_capabilities))
  expect_true(is.data.frame(checklist$reporting_guidance))
  expect_s3_class(
    checklist$feature_inventory,
    "gazepoint_biometrics_feature_inventory"
  )

  expect_true("eda_scr" %in% checklist$workflow_capabilities$domain)
  expect_true("ibi_hr_hrv" %in% checklist$workflow_capabilities$domain)
  expect_true("aoi_biometrics" %in% checklist$workflow_capabilities$domain)
  expect_true("interoperability" %in% checklist$workflow_capabilities$domain)
  expect_true("plotting" %in% checklist$workflow_capabilities$domain)
})

test_that("methods text mentions expanded workflow capabilities cautiously", {
  dat <- data.frame(
    GSR_US = c(0, 1.1, 1.2, 1.3),
    HR = c(70, 71, 72, 73),
    IBI = c(0.80, 0.82, 0.81, 0.83),
    DIAL = c(0, 1, 1, 1),
    TTL0 = c(1, 0, 0, 0)
  )

  checklist <- create_gazepoint_biometrics_checklist(dat)

  text <- create_gazepoint_biometrics_methods_text(
    checklist = checklist,
    include_cautions = TRUE
  )

  expect_true(is.character(text))
  expect_length(text, 1)
  expect_match(text, "EDA/SCR", fixed = TRUE)
  expect_match(text, "IBI/HR/HRV", fixed = TRUE)
  expect_match(text, "AOI-linked biometric", fixed = TRUE)
  expect_match(text, "contract-standardised plots", fixed = TRUE)
  expect_match(text, "emotional valence", fixed = TRUE)
})

test_that("reporting guidance covers key manuscript sections", {
  dat <- data.frame(
    GSR_US = c(0, 1.1, 1.2, 1.3),
    HR = c(70, 71, 72, 73),
    IBI = c(0.80, 0.82, 0.81, 0.83),
    DIAL = c(0, 1, 1, 1),
    TTL0 = c(1, 0, 0, 0)
  )

  checklist <- create_gazepoint_biometrics_checklist(dat)

  expect_true("EDA/SCR" %in% checklist$reporting_guidance$section)
  expect_true("IBI/HR/HRV" %in% checklist$reporting_guidance$section)
  expect_true("AOI-linked biometrics" %in% checklist$reporting_guidance$section)
  expect_true("Interoperability" %in% checklist$reporting_guidance$section)
  expect_true("Plots" %in% checklist$reporting_guidance$section)
})

test_that("report bundle README includes expanded workflow cautions", {
  skip_if_not_installed("ggplot2")

  output_dir <- tempfile("gpbiometrics_bundle_")
  dir.create(output_dir)

  bundle <- export_gazepoint_biometrics_report_bundle(
    output_dir = output_dir,
    prefix = "test_bundle",
    tables = list(example = data.frame(x = 1:2)),
    include_readme = TRUE,
    include_session_info = FALSE,
    overwrite = TRUE
  )

  expect_s3_class(bundle, "gazepoint_biometrics_report_bundle")
  expect_equal(bundle$overview$status, "bundle_exported")

  readme_path <- bundle$manifest$path[
    bundle$manifest$item == "README"
  ]

  expect_true(file.exists(readme_path))

  readme_text <- paste(readLines(readme_path, warn = FALSE), collapse = "\n")

  expect_match(readme_text, "SCR peak/event-window", fixed = TRUE)
  expect_match(readme_text, "IBI-derived HRV", fixed = TRUE)
  expect_match(readme_text, "AOI-linked biometric", fixed = TRUE)
  expect_match(readme_text, "Contract-standardised ggplot", fixed = TRUE)
})
