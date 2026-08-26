test_that("create_gazepoint_analysis_decision_log creates an empty structured log", {
  log <- create_gazepoint_analysis_decision_log(
    study_id = "study_001",
    analyst = "analyst_a",
    description = "Demo decision log"
  )

  expect_s3_class(log, "gazepoint_analysis_decision_log")
  expect_s3_class(log, "data.frame")
  expect_equal(NROW(log), 0L)

  expect_equal(attr(log, "study_id"), "study_001")
  expect_equal(attr(log, "analyst"), "analyst_a")
  expect_equal(attr(log, "description"), "Demo decision log")

  expect_true(all(c(
    "decision_id",
    "timestamp",
    "stage",
    "object_type",
    "object_id",
    "decision",
    "reason",
    "function_name",
    "parameter",
    "value",
    "reviewer_note"
  ) %in% names(log)))
})

test_that("add_gazepoint_decision adds sequential decision records", {
  log <- create_gazepoint_analysis_decision_log(study_id = "study_001")

  log <- add_gazepoint_decision(
    log,
    stage = "quality_control",
    object_type = "channel",
    object_id = "GSR",
    decision = "retained",
    reason = "Signal activity audit passed",
    function_name = "assess_gazepoint_signal_activity",
    parameter = "min_active_prop",
    value = 0.80,
    reviewer_note = "GSR retained after activity screening.",
    timestamp = "2026-01-01 10:00:00 UTC"
  )

  log <- add_gazepoint_decision(
    log,
    stage = "preprocessing",
    object_type = "signal",
    object_id = "pupil",
    decision = "baseline_corrected",
    reason = "Baseline window available",
    function_name = "baseline_correct_gazepoint_pupil",
    parameter = "baseline_window",
    value = c(start = -1000, end = 0),
    reviewer_note = "Pupil signal baseline corrected.",
    timestamp = "2026-01-01 10:05:00 UTC"
  )

  expect_s3_class(log, "gazepoint_analysis_decision_log")
  expect_equal(NROW(log), 2L)
  expect_equal(log$decision_id, c(1L, 2L))
  expect_equal(log$stage, c("quality_control", "preprocessing"))
  expect_equal(log$object_type, c("channel", "signal"))
  expect_equal(log$decision, c("retained", "baseline_corrected"))
  expect_equal(log$value[1], "0.8")
  expect_equal(log$value[2], "start=-1000; end=0")
})

test_that("add_gazepoint_decision preserves log metadata", {
  log <- create_gazepoint_analysis_decision_log(
    study_id = "study_meta",
    analyst = "analyst_meta",
    description = "Metadata preservation"
  )

  log <- add_gazepoint_decision(
    log,
    stage = "modelling",
    object_type = "model",
    object_id = "model_1",
    decision = "model_ready_table_created",
    reason = "Trial-level regressors available",
    timestamp = "2026-01-01 10:00:00 UTC"
  )

  expect_equal(attr(log, "study_id"), "study_meta")
  expect_equal(attr(log, "analyst"), "analyst_meta")
  expect_equal(attr(log, "description"), "Metadata preservation")
  expect_true(!is.null(attr(log, "created_at")))
  expect_true(!is.null(attr(log, "package_version")))
})

test_that("summarise_gazepoint_decision_log summarises decision counts", {
  log <- create_gazepoint_analysis_decision_log(
    study_id = "study_summary",
    analyst = "analyst_summary"
  )

  log <- add_gazepoint_decision(
    log,
    stage = "quality_control",
    object_type = "trial",
    object_id = "trial_001",
    decision = "excluded",
    reason = "Missing signal window",
    function_name = "audit_gazepoint_event_coverage",
    timestamp = "2026-01-01 10:00:00 UTC"
  )

  log <- add_gazepoint_decision(
    log,
    stage = "quality_control",
    object_type = "trial",
    object_id = "trial_002",
    decision = "excluded",
    reason = "Missing signal window",
    function_name = "audit_gazepoint_event_coverage",
    timestamp = "2026-01-01 10:01:00 UTC"
  )

  log <- add_gazepoint_decision(
    log,
    stage = "cluster_permutation",
    object_type = "cluster_test",
    object_id = "A_vs_B",
    decision = "reported_descriptively",
    reason = "Cluster timing is descriptive only",
    function_name = "run_gazepoint_cluster_permutation",
    timestamp = "2026-01-01 10:02:00 UTC"
  )

  summary <- summarise_gazepoint_decision_log(log)

  expect_s3_class(summary, "gazepoint_analysis_decision_log_summary")
  expect_equal(summary$overview$n_decisions, 3L)
  expect_equal(summary$overview$study_id, "study_summary")

  expect_true("quality_control" %in% summary$by_stage$stage)
  expect_true("cluster_permutation" %in% summary$by_stage$stage)
  expect_equal(
    summary$by_stage$n[summary$by_stage$stage == "quality_control"],
    2L
  )

  expect_true("excluded" %in% summary$by_decision$decision)
  expect_equal(
    summary$by_decision$n[summary$by_decision$decision == "excluded"],
    2L
  )
})

test_that("summarise_gazepoint_decision_log handles empty logs", {
  log <- create_gazepoint_analysis_decision_log(study_id = "empty_study")

  summary <- summarise_gazepoint_decision_log(log)

  expect_s3_class(summary, "gazepoint_analysis_decision_log_summary")
  expect_equal(summary$overview$n_decisions, 0L)
  expect_equal(NROW(summary$by_stage), 0L)
  expect_equal(NROW(summary$by_object_type), 0L)
  expect_equal(NROW(summary$by_decision), 0L)
  expect_equal(NROW(summary$by_function), 0L)
})

test_that("write_gazepoint_decision_log writes CSV and optional summary", {
  log <- create_gazepoint_analysis_decision_log(
    study_id = "write_study",
    analyst = "writer"
  )

  log <- add_gazepoint_decision(
    log,
    stage = "reporting",
    object_type = "report",
    object_id = "supplement",
    decision = "qc_summary_written",
    reason = "Reviewer-facing quality-control summary created",
    function_name = "write_gazepoint_decision_log",
    timestamp = "2026-01-01 10:00:00 UTC"
  )

  tmp_dir <- tempfile("decision_log_output_")
  csv_path <- file.path(tmp_dir, "decision_log.csv")
  txt_path <- file.path(tmp_dir, "decision_log_summary.txt")

  written <- write_gazepoint_decision_log(
    log,
    path = csv_path,
    summary_path = txt_path,
    overwrite = TRUE
  )

  expect_true(is.data.frame(written))
  expect_equal(NROW(written), 2L)
  expect_true(all(file.exists(written$file)))

  read_back <- utils::read.csv(csv_path, stringsAsFactors = FALSE)
  expect_equal(NROW(read_back), 1L)
  expect_equal(read_back$decision, "qc_summary_written")

  txt <- readLines(txt_path, warn = FALSE)
  expect_true(any(grepl("Gazepoint analysis decision log", txt)))
  expect_true(any(grepl("Number of decisions: 1", txt)))
})

test_that("write_gazepoint_decision_log protects existing files", {
  log <- create_gazepoint_analysis_decision_log(study_id = "overwrite_study")

  tmp <- tempfile(fileext = ".csv")
  writeLines("existing", tmp)

  expect_error(
    write_gazepoint_decision_log(log, path = tmp, overwrite = FALSE),
    "already exist"
  )

  written <- write_gazepoint_decision_log(log, path = tmp, overwrite = TRUE)
  expect_true(file.exists(written$file))
})

test_that("analysis decision log functions validate inputs", {
  expect_error(
    add_gazepoint_decision(
      data.frame(),
      stage = "quality_control",
      object_type = "trial",
      decision = "excluded"
    ),
    "must be created"
  )

  log <- create_gazepoint_analysis_decision_log()

  expect_error(
    add_gazepoint_decision(
      log,
      stage = "",
      object_type = "trial",
      decision = "excluded"
    ),
    "stage"
  )

  expect_error(
    add_gazepoint_decision(
      log,
      stage = "quality_control",
      object_type = "",
      decision = "excluded"
    ),
    "object_type"
  )

  expect_error(
    add_gazepoint_decision(
      log,
      stage = "quality_control",
      object_type = "trial",
      decision = ""
    ),
    "decision"
  )

  expect_error(
    summarise_gazepoint_decision_log(data.frame()),
    "must be created"
  )

  expect_error(
    write_gazepoint_decision_log(log, path = ""),
    "non-empty"
  )
})
