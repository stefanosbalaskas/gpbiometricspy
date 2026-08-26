test_that("create_gazepoint_methods_section creates conservative methods text", {
  dat <- expand.grid(
    participant = paste0("P", 1:3),
    condition = c("A", "B"),
    trial = 1:2,
    event = c("stimulus", "response"),
    stringsAsFactors = FALSE
  )

  design_audit <- audit_gazepoint_experiment_design(
    dat,
    participant_col = "participant",
    trial_col = "trial",
    condition_col = "condition",
    expected_conditions = c("A", "B")
  )

  event_audit <- audit_gazepoint_event_coverage(
    dat,
    event_col = "event",
    participant_col = "participant",
    trial_col = "trial",
    expected_events = c("stimulus", "response")
  )

  condition_audit <- audit_gazepoint_condition_balance(
    dat,
    participant_col = "participant",
    condition_col = "condition",
    trial_col = "trial",
    expected_conditions = c("A", "B")
  )

  decision_log <- create_gazepoint_analysis_decision_log(
    study_id = "methods_test",
    analyst = "tester"
  )

  decision_log <- add_gazepoint_decision(
    decision_log,
    stage = "quality_control",
    object_type = "trial",
    object_id = "all",
    decision = "retained",
    reason = "Synthetic records complete",
    timestamp = "2026-01-01 10:00:00 UTC"
  )

  text <- create_gazepoint_methods_section(
    design_audit = design_audit,
    event_audit = event_audit,
    condition_audit = condition_audit,
    decision_log = decision_log,
    validation = list(
      test = "PASS 2322",
      check = "0 errors, 0 warnings, 0 notes"
    )
  )

  expect_s3_class(text, "gazepoint_report_text")
  expect_true(is.character(text))
  expect_true(any(grepl("gpbiometrics", text)))
  expect_true(any(grepl("experiment-design audit", text)))
  expect_true(any(grepl("Event coverage", text)))
  expect_true(any(grepl("Condition balance", text)))
  expect_true(any(grepl("structured analysis decision log", text)))
  expect_true(any(grepl("Package validation", text)))
  expect_true(any(grepl("not interpreted as direct measures", text)))
  expect_equal(attr(text, "template"), "methods_section")
})

test_that("create_gazepoint_methods_section can use export profiles", {
  tmp <- tempfile("gazepoint_report_profile_")
  dir.create(tmp)

  dat <- data.frame(
    CNT = 1:5,
    TIME = seq(0, 0.4, length.out = 5),
    TTL0 = c(0, 1, 0, 0, 0),
    GSR_US = seq(0.1, 0.5, length.out = 5),
    HR = rep(70, 5)
  )

  utils::write.csv(dat, file.path(tmp, "one.csv"), row.names = FALSE)

  profile <- profile_gazepoint_export_folder(tmp)

  text <- create_gazepoint_methods_section(
    export_profile = profile,
    include_guardrails = FALSE
  )

  expect_s3_class(text, "gazepoint_report_text")
  expect_true(any(grepl("export folder was profiled", text)))
  expect_false(any(grepl("not interpreted as direct measures", text)))
})

test_that("create_gazepoint_qc_supplement creates section text", {
  dat <- expand.grid(
    participant = paste0("P", 1:2),
    condition = c("A", "B"),
    trial = 1:2,
    event = c("stimulus", "response"),
    stringsAsFactors = FALSE
  )

  design_audit <- audit_gazepoint_experiment_design(
    dat,
    participant_col = "participant",
    trial_col = "trial",
    condition_col = "condition"
  )

  event_audit <- audit_gazepoint_event_coverage(
    dat,
    event_col = "event",
    participant_col = "participant",
    trial_col = "trial",
    expected_events = c("stimulus", "response")
  )

  condition_audit <- audit_gazepoint_condition_balance(
    dat,
    participant_col = "participant",
    condition_col = "condition",
    trial_col = "trial"
  )

  decision_log <- create_gazepoint_analysis_decision_log(
    study_id = "qc_test"
  )

  decision_log <- add_gazepoint_decision(
    decision_log,
    stage = "reporting",
    object_type = "supplement",
    object_id = "qc",
    decision = "created",
    reason = "QC supplement generated",
    timestamp = "2026-01-01 10:00:00 UTC"
  )

  text <- create_gazepoint_qc_supplement(
    design_audit = design_audit,
    event_audit = event_audit,
    condition_audit = condition_audit,
    decision_log = decision_log
  )

  expect_s3_class(text, "gazepoint_report_text")
  expect_true(any(grepl("Gazepoint workflow quality-control supplement", text)))
  expect_true(any(grepl("Experiment-design audit", text)))
  expect_true(any(grepl("Event-coverage audit", text)))
  expect_true(any(grepl("Condition-balance audit", text)))
  expect_true(any(grepl("Analysis decision log", text)))
  expect_equal(attr(text, "template"), "qc_supplement")
})

test_that("create_gazepoint_qc_supplement handles no supplied objects", {
  text <- create_gazepoint_qc_supplement()

  expect_s3_class(text, "gazepoint_report_text")
  expect_true(any(grepl("No audit objects were supplied", text)))
})

test_that("create_gazepoint_reproducibility_statement creates conservative text", {
  decision_log <- create_gazepoint_analysis_decision_log(
    study_id = "repro_test"
  )

  decision_log <- add_gazepoint_decision(
    decision_log,
    stage = "preprocessing",
    object_type = "signal",
    object_id = "GSR",
    decision = "baseline_corrected",
    reason = "Pre-event window available",
    timestamp = "2026-01-01 10:00:00 UTC"
  )

  text <- create_gazepoint_reproducibility_statement(
    decision_log = decision_log,
    repository_url = "https://example.org/repo",
    validation = list(
      test = "PASS 2322",
      check = "0 errors, 0 warnings, 0 notes"
    ),
    data_statement = "Synthetic demonstration data were used for software checks."
  )

  expect_s3_class(text, "gazepoint_report_text")
  expect_true(any(grepl("Analyses were supported by gpbiometrics", text)))
  expect_true(any(grepl("repository", text, ignore.case = TRUE)))
  expect_true(any(grepl("structured analysis decision log", text)))
  expect_true(any(grepl("Package validation", text)))
  expect_true(any(grepl("Synthetic demonstration data", text)))
  expect_true(any(grepl("not as automatic labels", text)))
  expect_equal(attr(text, "template"), "reproducibility_statement")
})

test_that("create_gazepoint_reproducibility_statement can omit guardrails", {
  text <- create_gazepoint_reproducibility_statement(
    include_guardrails = FALSE
  )

  expect_s3_class(text, "gazepoint_report_text")
  expect_false(any(grepl("not as automatic labels", text)))
})

test_that("create_gazepoint_audit_report_section creates integrated audit text", {
  dat <- expand.grid(
    participant = paste0("P", 1:3),
    condition = c("A", "B"),
    trial = 1:2,
    event = c("stimulus", "response"),
    stringsAsFactors = FALSE
  )

  design_audit <- audit_gazepoint_experiment_design(
    dat,
    participant_col = "participant",
    trial_col = "trial",
    condition_col = "condition"
  )

  event_audit <- audit_gazepoint_event_coverage(
    dat,
    event_col = "event",
    participant_col = "participant",
    trial_col = "trial",
    expected_events = c("stimulus", "response")
  )

  condition_audit <- audit_gazepoint_condition_balance(
    dat,
    participant_col = "participant",
    condition_col = "condition",
    trial_col = "trial"
  )

  decision_log <- create_gazepoint_analysis_decision_log(
    study_id = "audit_report_test"
  )

  decision_log <- add_gazepoint_decision(
    decision_log,
    stage = "analysis",
    object_type = "workflow",
    object_id = "main",
    decision = "audited",
    reason = "Audit report generated",
    timestamp = "2026-01-01 10:00:00 UTC"
  )

  text <- create_gazepoint_audit_report_section(
    design_audit = design_audit,
    event_audit = event_audit,
    condition_audit = condition_audit,
    decision_log = decision_log
  )

  expect_s3_class(text, "gazepoint_report_text")
  expect_true(any(grepl("Gazepoint workflow audit summary", text)))
  expect_true(any(grepl("design audit", text)))
  expect_true(any(grepl("event-coverage audit", text)))
  expect_true(any(grepl("condition-balance audit", text)))
  expect_true(any(grepl("decision log", text)))
  expect_true(any(grepl("No audit warnings", text)))
  expect_equal(attr(text, "template"), "audit_report_section")
})

test_that("create_gazepoint_audit_report_section reports warning summaries", {
  dat <- data.frame(
    participant = c("P1", "P2"),
    trial = c(1, 1),
    condition = c("A", "A"),
    event = c("stimulus", "stimulus"),
    stringsAsFactors = FALSE
  )

  design_audit <- audit_gazepoint_experiment_design(
    dat,
    participant_col = "participant",
    trial_col = "trial",
    condition_col = "condition",
    expected_conditions = c("A", "B")
  )

  event_audit <- audit_gazepoint_event_coverage(
    dat,
    event_col = "event",
    participant_col = "participant",
    trial_col = "trial",
    expected_events = c("stimulus", "response")
  )

  text <- create_gazepoint_audit_report_section(
    design_audit = design_audit,
    event_audit = event_audit,
    include_warnings = TRUE
  )

  expect_s3_class(text, "gazepoint_report_text")
  expect_true(any(grepl("warning records", text)))
})

test_that("create_gazepoint_audit_report_section handles no supplied objects", {
  text <- create_gazepoint_audit_report_section()

  expect_s3_class(text, "gazepoint_report_text")
  expect_true(any(grepl("No audit objects were supplied", text)))
})

test_that("reviewer report templates validate inputs", {
  expect_error(
    create_gazepoint_methods_section(export_profile = data.frame()),
    "export_profile"
  )

  expect_error(
    create_gazepoint_methods_section(design_audit = data.frame()),
    "design_audit"
  )

  expect_error(
    create_gazepoint_methods_section(event_audit = data.frame()),
    "event_audit"
  )

  expect_error(
    create_gazepoint_methods_section(condition_audit = data.frame()),
    "condition_audit"
  )

  expect_error(
    create_gazepoint_methods_section(decision_log = data.frame()),
    "decision_log"
  )

  expect_error(
    create_gazepoint_methods_section(package_version = ""),
    "package_version"
  )

  expect_error(
    create_gazepoint_methods_section(include_guardrails = NA),
    "include_guardrails"
  )

  expect_error(
    create_gazepoint_reproducibility_statement(
      validation = list("PASS")
    ),
    "named list"
  )

  expect_error(
    create_gazepoint_qc_supplement(title = ""),
    "title"
  )
})

test_that("print.gazepoint_report_text returns invisibly", {
  text <- create_gazepoint_audit_report_section()

  expect_s3_class(text, "gazepoint_report_text")
  expect_output(print(text), "Gazepoint workflow audit summary")
  expect_invisible(print(text))
})
