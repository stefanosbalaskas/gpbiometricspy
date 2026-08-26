test_that("export_gazepoint_biometrics_report_bundle writes tables and manifest", {
  out_dir <- tempfile("gpbiometrics_bundle_")

  tables <- list(
    overview = data.frame(status = "ok", rows = 10),
    quality = data.frame(signal = c("GSR_US", "HR"), missing_prop = c(0, 0.1))
  )

  res <- export_gazepoint_biometrics_report_bundle(
    output_dir = out_dir,
    prefix = "test_bundle",
    tables = tables,
    text = list(methods = c("Methods text.", "Caution text.")),
    include_readme = TRUE,
    include_session_info = FALSE
  )

  expect_s3_class(res, "gazepoint_biometrics_report_bundle")
  expect_equal(res$overview$status, "bundle_exported")
  expect_true(file.exists(file.path(out_dir, "test_bundle_tables_overview.csv")))
  expect_true(file.exists(file.path(out_dir, "test_bundle_tables_quality.csv")))
  expect_true(file.exists(file.path(out_dir, "test_bundle_text_methods.txt")))
  expect_true(file.exists(file.path(out_dir, "test_bundle_README.txt")))
  expect_true(file.exists(file.path(out_dir, "test_bundle_manifest.csv")))
})

test_that("export_gazepoint_biometrics_report_bundle prevents accidental overwrite", {
  out_dir <- tempfile("gpbiometrics_bundle_")
  dir.create(out_dir)

  existing <- file.path(out_dir, "test_bundle_tables_overview.csv")
  writeLines("existing", existing)

  expect_error(
    export_gazepoint_biometrics_report_bundle(
      output_dir = out_dir,
      prefix = "test_bundle",
      tables = list(overview = data.frame(x = 1)),
      include_readme = FALSE,
      include_session_info = FALSE,
      overwrite = FALSE
    ),
    "File already exists"
  )
})

test_that("run_gazepoint_biometrics_real_data_readiness passes adequate synthetic data", {
  dat <- data.frame(
    time_ms = seq(0, 14900, by = 100),
    GSR_US = seq(1, 2, length.out = 150),
    HR = seq(70, 80, length.out = 150),
    IBI = seq(850, 760, length.out = 150),
    TTL0 = c(rep(0, 50), 1, rep(0, 99)),
    TTLV = 1
  )

  res <- run_gazepoint_biometrics_real_data_readiness(
    dat,
    min_rows = 100,
    min_active_signal_count = 2,
    max_missing_prop = 0.25
  )

  expect_s3_class(res, "gazepoint_biometrics_real_data_readiness")
  expect_equal(res$overview$final_status, "pass")
  expect_equal(res$overview$decision, "ready_for_analysis_with_standard_cautions")
  expect_true(any(res$checks$check == "ttl_markers" & res$checks$status == "pass"))
})

test_that("run_gazepoint_biometrics_real_data_readiness warns for GSR-only and HRV-without-IBI", {
  dat <- data.frame(
    time_ms = seq(0, 11900, by = 100),
    GSR = seq(1000000, 500000, length.out = 120),
    HRV = rep(1, 120)
  )

  res <- run_gazepoint_biometrics_real_data_readiness(
    dat,
    min_rows = 100,
    min_active_signal_count = 1
  )

  expect_equal(res$overview$final_status, "warn")
  expect_true(any(res$checks$check == "gsr_conductance_channel" & res$checks$status == "warn"))
  expect_true(any(res$checks$check == "hrv_ibi_caution" & res$checks$status == "warn"))
})

test_that("run_gazepoint_biometrics_real_data_readiness fails for too few rows", {
  dat <- data.frame(
    time_ms = seq(0, 900, by = 100),
    GSR_US = seq(1, 2, length.out = 10)
  )

  res <- run_gazepoint_biometrics_real_data_readiness(
    dat,
    min_rows = 100,
    min_active_signal_count = 1
  )

  expect_equal(res$overview$final_status, "fail")
  expect_true(any(res$checks$check == "row_count" & res$checks$status == "fail"))
})

test_that("run_gazepoint_biometrics_real_data_readiness can extract data from workflow-like list", {
  dat <- data.frame(
    time_ms = seq(0, 9900, by = 100),
    GSR_US = seq(1, 2, length.out = 100),
    HR = seq(70, 75, length.out = 100)
  )

  workflow <- list(
    overview = data.frame(status = "ok"),
    biometrics = dat
  )

  res <- run_gazepoint_biometrics_real_data_readiness(
    workflow_result = workflow,
    min_rows = 100,
    min_active_signal_count = 2
  )

  expect_equal(res$overview$final_status, "pass")
})

test_that("run_gazepoint_biometrics_real_data_readiness checks time order within source groups", {
  dat <- data.frame(
    source_file = rep(c("file_a.csv", "file_b.csv"), each = 100),
    CNT = rep(seq_len(100), 2),
    GSR_US = seq(1, 2, length.out = 200),
    HR = seq(70, 80, length.out = 200),
    TTL0 = c(1, rep(0, 199))
  )

  res <- run_gazepoint_biometrics_real_data_readiness(
    dat,
    min_rows = 100,
    min_active_signal_count = 2,
    time_col = "CNT"
  )

  expect_equal(res$overview$final_status, "pass")
  expect_true(any(res$checks$check == "time_column" & res$checks$status == "pass"))
})

test_that("run_gazepoint_biometrics_real_data_readiness still warns for negative time steps within groups", {
  dat <- data.frame(
    source_file = rep("file_a.csv", 120),
    CNT = c(seq_len(60), seq_len(60)),
    GSR_US = seq(1, 2, length.out = 120),
    HR = seq(70, 80, length.out = 120),
    TTL0 = c(1, rep(0, 119))
  )

  res <- run_gazepoint_biometrics_real_data_readiness(
    dat,
    min_rows = 100,
    min_active_signal_count = 2,
    time_col = "CNT"
  )

  expect_equal(res$overview$final_status, "warn")
  expect_true(any(res$checks$check == "time_column" & res$checks$status == "warn"))
})
