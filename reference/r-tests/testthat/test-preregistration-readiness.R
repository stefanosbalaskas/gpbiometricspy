test_that("create_gazepoint_preregistration_checklist creates default checklist", {
  checklist <- create_gazepoint_preregistration_checklist(
    study_id = "study-001",
    include_optional = TRUE
  )

  expect_s3_class(checklist, "gazepoint_preregistration_checklist")
  expect_equal(nrow(checklist), 14)
  expect_true(all(c(
    "study_id", "domain", "item_id", "item", "required",
    "evidence_key", "required_fields", "status", "notes"
  ) %in% names(checklist)))
  expect_true(all(checklist$study_id == "study-001"))
  expect_equal(sum(checklist$required), 10)
  expect_equal(sum(!checklist$required), 4)
  expect_true("design_conditions" %in% checklist$item_id)
  expect_true("analysis_manifest" %in% checklist$item_id)
})

test_that("create_gazepoint_preregistration_checklist can omit optional items", {
  checklist <- create_gazepoint_preregistration_checklist(
    study_id = "study-002",
    include_optional = FALSE
  )

  expect_s3_class(checklist, "gazepoint_preregistration_checklist")
  expect_equal(nrow(checklist), 10)
  expect_true(all(checklist$required))
  expect_false("analysis_manifest" %in% checklist$item_id)
})

test_that("create_gazepoint_preregistration_checklist accepts custom items", {
  checklist <- create_gazepoint_preregistration_checklist(
    study_id = "custom-study",
    include_optional = FALSE,
    custom_items = data.frame(
      domain = "device_sync",
      item_id = "ttl_sync_plan",
      item = "TTL synchronization plan is documented.",
      required = TRUE,
      evidence_key = "sync",
      required_fields = "ttl_column,rule"
    )
  )

  expect_s3_class(checklist, "gazepoint_preregistration_checklist")
  expect_equal(nrow(checklist), 11)
  expect_true("ttl_sync_plan" %in% checklist$item_id)
  custom_row <- checklist[checklist$item_id == "ttl_sync_plan", ]
  expect_equal(custom_row$domain, "device_sync")
  expect_true(custom_row$required)
  expect_equal(custom_row$evidence_key, "sync")
})

test_that("audit_gazepoint_preregistration_consistency checks supplied evidence", {
  checklist <- create_gazepoint_preregistration_checklist(
    study_id = "demo-study",
    include_optional = TRUE
  )

  evidence <- list(
    design = data.frame(
      condition = c("A", "B"),
      participant = c("P01", "P02"),
      trial = c(1, 1)
    ),
    sampling = data.frame(
      sample_size = 40,
      inclusion_criteria = "valid Gazepoint export"
    ),
    outcomes = data.frame(
      outcome = "eda_peak_count",
      role = "primary"
    ),
    preprocessing = data.frame(
      step = c("import", "qc"),
      decision = c("read exports", "flag missingness")
    ),
    quality_control = data.frame(
      metric = "prop_missing",
      rule = "<= .20"
    ),
    exclusions = data.frame(
      rule = "prop_missing > .20",
      action = "flag for review"
    ),
    reporting = data.frame(
      item = "QC table",
      decision = "include in supplement"
    ),
    dictionary = data.frame(
      variable = "eda_peak_count",
      description = "Count of detected EDA peaks"
    )
  )

  audit <- audit_gazepoint_preregistration_consistency(
    checklist,
    evidence = evidence
  )

  expect_s3_class(audit, "gazepoint_preregistration_audit")
  expect_named(audit, c("checklist", "item_results", "summary", "parameters"))
  expect_equal(nrow(audit$item_results), 14)
  expect_equal(audit$summary$n_required, 10)
  expect_equal(audit$summary$n_required_complete, 7)
  expect_equal(audit$summary$n_missing_required, 3)
  expect_equal(audit$summary$n_optional_complete, 1)
  expect_equal(audit$summary$readiness_score, 0.7)
  expect_equal(audit$summary$readiness_label, "partly_complete")

  design_row <- audit$item_results[audit$item_results$item_id == "design_conditions", ]
  expect_true(design_row$has_evidence)
  expect_true(design_row$evidence_complete)
  expect_equal(design_row$audit_status, "complete_required")
  expect_true(design_row$audit_pass)

  missing_row <- audit$item_results[audit$item_results$item_id == "missing_data_plan", ]
  expect_false(missing_row$has_evidence)
  expect_equal(missing_row$audit_status, "missing_required")
  expect_false(missing_row$audit_pass)

  optional_row <- audit$item_results[audit$item_results$item_id == "analysis_manifest", ]
  expect_equal(optional_row$audit_status, "missing_optional")
  expect_false(optional_row$audit_pass)
})

test_that("audit_gazepoint_preregistration_consistency checks required fields", {
  checklist <- create_gazepoint_preregistration_checklist(include_optional = FALSE)

  evidence <- list(
    design = data.frame(condition = "A", participant = "P01"),
    sampling = data.frame(sample_size = 40, inclusion_criteria = "valid export"),
    outcomes = data.frame(outcome = "eda_peak_count", role = "primary"),
    preprocessing = data.frame(step = "import", decision = "read exports"),
    quality_control = data.frame(metric = "prop_missing", rule = "<= .20"),
    exclusions = data.frame(rule = "prop_missing > .20", action = "flag"),
    missingness = data.frame(variable = "eda", handling = "flag"),
    time_windows = data.frame(window_start = 0, window_end = 2),
    analysis = data.frame(outcome = "eda_peak_count", model = "lm"),
    reporting = data.frame(item = "QC table", decision = "include")
  )

  audit <- audit_gazepoint_preregistration_consistency(
    checklist,
    evidence = evidence,
    require_required_fields = TRUE
  )

  design_row <- audit$item_results[audit$item_results$item_id == "design_conditions", ]
  expect_equal(design_row$audit_status, "incomplete_required")
  expect_equal(design_row$missing_fields, "trial")
  expect_false(design_row$audit_pass)

  audit_no_field_check <- audit_gazepoint_preregistration_consistency(
    checklist,
    evidence = evidence,
    require_required_fields = FALSE
  )

  design_row2 <- audit_no_field_check$item_results[
    audit_no_field_check$item_results$item_id == "design_conditions",
  ]
  expect_equal(design_row2$audit_status, "complete_required")
  expect_true(design_row2$audit_pass)
})

test_that("summarize_gazepoint_preregistration_readiness summarizes by domain", {
  checklist <- create_gazepoint_preregistration_checklist(include_optional = TRUE)

  evidence <- list(
    design = data.frame(condition = "A", participant = "P01", trial = 1),
    sampling = data.frame(sample_size = 40, inclusion_criteria = "valid export"),
    outcomes = data.frame(outcome = "eda_peak_count", role = "primary"),
    preprocessing = data.frame(step = "import", decision = "read exports"),
    quality_control = data.frame(metric = "prop_missing", rule = "<= .20"),
    exclusions = data.frame(rule = "prop_missing > .20", action = "flag"),
    reporting = data.frame(item = "QC table", decision = "include"),
    dictionary = data.frame(variable = "eda_peak_count", description = "EDA peak count")
  )

  audit <- audit_gazepoint_preregistration_consistency(checklist, evidence = evidence)
  domain_summary <- summarize_gazepoint_preregistration_readiness(audit, by = "domain")

  expect_s3_class(domain_summary, "gazepoint_preregistration_readiness")
  expect_true("domain" %in% names(domain_summary))
  expect_true("readiness_score" %in% names(domain_summary))
  expect_true("readiness_label" %in% names(domain_summary))

  design <- domain_summary[domain_summary$domain == "design", ]
  analysis <- domain_summary[domain_summary$domain == "analysis", ]
  reproducibility <- domain_summary[domain_summary$domain == "reproducibility", ]

  expect_equal(design$readiness_score, 1)
  expect_equal(design$readiness_label, "complete")
  expect_equal(analysis$readiness_score, 0)
  expect_equal(analysis$readiness_label, "early_stage")
  expect_true(is.na(reproducibility$readiness_score))
  expect_equal(reproducibility$readiness_label, "not_applicable")
})

test_that("summarize_gazepoint_preregistration_readiness accepts item-level data", {
  item_results <- data.frame(
    domain = c("design", "design", "qc"),
    item_id = c("a", "b", "c"),
    required = c(TRUE, TRUE, FALSE),
    audit_status = c("complete_required", "missing_required", "missing_optional"),
    audit_pass = c(TRUE, FALSE, FALSE)
  )

  summary <- summarize_gazepoint_preregistration_readiness(
    item_results,
    by = "domain"
  )

  expect_s3_class(summary, "gazepoint_preregistration_readiness")
  design <- summary[summary$domain == "design", ]
  qc <- summary[summary$domain == "qc", ]

  expect_equal(design$n_required, 2)
  expect_equal(design$n_required_complete, 1)
  expect_equal(design$readiness_score, 0.5)
  expect_equal(design$readiness_label, "partly_complete")
  expect_true(is.na(qc$readiness_score))
})

test_that("preregistration readiness helpers validate inputs", {
  expect_error(
    create_gazepoint_preregistration_checklist(study_id = c("a", "b")),
    "study_id"
  )

  expect_error(
    create_gazepoint_preregistration_checklist(include_optional = NA),
    "include_optional"
  )

  expect_error(
    create_gazepoint_preregistration_checklist(custom_items = data.frame(domain = "x")),
    "missing required"
  )

  checklist <- create_gazepoint_preregistration_checklist()

  expect_error(
    audit_gazepoint_preregistration_consistency(
      checklist,
      evidence = list(data.frame(x = 1))
    ),
    "named list"
  )

  expect_error(
    audit_gazepoint_preregistration_consistency(
      checklist,
      evidence = list(design = data.frame(x = 1)),
      require_required_fields = NA
    ),
    "require_required_fields"
  )

  expect_error(
    audit_gazepoint_preregistration_consistency(
      data.frame(x = 1),
      evidence = list()
    ),
    "missing required"
  )

  expect_error(
    summarize_gazepoint_preregistration_readiness(data.frame(x = 1)),
    "missing required"
  )

  expect_error(
    summarize_gazepoint_preregistration_readiness(
      data.frame(required = TRUE, audit_status = "complete_required", audit_pass = TRUE),
      by = "missing"
    ),
    "not found"
  )
})
