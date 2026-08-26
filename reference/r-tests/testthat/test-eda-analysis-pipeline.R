test_that("create_gazepoint_eda_analysis_pipeline returns six phases", {
  out <- create_gazepoint_eda_analysis_pipeline()

  expect_s3_class(out, "gazepoint_eda_analysis_pipeline")
  expect_equal(out$overview$status, "eda_analysis_pipeline_created")
  expect_equal(out$overview$phase_count, 6)
  expect_equal(nrow(out$phases), 6)
  expect_true(all(c("phase", "phase_name", "purpose") %in% names(out$phases)))
  expect_true(is.data.frame(out$function_map))
  expect_true(is.data.frame(out$model_templates))
  expect_true(is.data.frame(out$reporting_guidance))
  expect_true(is.data.frame(out$interpretation_guardrails))
})

test_that("create_gazepoint_eda_analysis_pipeline includes expected phase helpers", {
  out <- create_gazepoint_eda_analysis_pipeline()

  expected <- c(
    "import_gazepoint_biometrics",
    "audit_gazepoint_time_resets",
    "audit_gazepoint_signal_activity",
    "audit_gazepoint_eda_artifacts",
    "detect_gazepoint_scr_peaks",
    "summarise_gazepoint_scr_event_windows",
    "classify_gazepoint_eda_response_pattern",
    "prepare_gazepoint_cvxeda_input",
    "align_gazepoint_biometrics_to_ttl",
    "estimate_gazepoint_signal_lag",
    "prepare_gazepoint_scr_hurdle_model_data",
    "prepare_gazepoint_biometrics_lme_data",
    "export_gazepoint_biometrics_report_bundle",
    "create_gazepoint_biometrics_methods_text"
  )

  expect_true(all(expected %in% out$function_map$function_name))
  expect_true(all(out$function_map$available))
})

test_that("create_gazepoint_eda_analysis_pipeline can omit bridges and templates", {
  out <- create_gazepoint_eda_analysis_pipeline(
    include_external_bridges = FALSE,
    include_model_templates = FALSE,
    include_reporting_guidance = FALSE
  )

  expect_false("prepare_gazepoint_cvxeda_input" %in% out$function_map$function_name)
  expect_equal(nrow(out$model_templates), 0)
  expect_equal(nrow(out$reporting_guidance), 0)
  expect_false(out$settings$include_external_bridges)
  expect_false(out$settings$include_model_templates)
  expect_false(out$settings$include_reporting_guidance)
})

test_that("create_gazepoint_eda_analysis_pipeline includes conservative model templates", {
  out <- create_gazepoint_eda_analysis_pipeline()

  expect_true(any(out$model_templates$package == "brms"))
  expect_true(any(out$model_templates$package == "lme4"))
  expect_true(any(grepl("hurdle_lognormal", out$model_templates$template)))
  expect_true(any(grepl("lme4::lmer", out$model_templates$template)))

  all_template_text <- paste(out$model_templates$notes, collapse = " ")
  expect_true(grepl("Template only", all_template_text))
})

test_that("create_gazepoint_eda_analysis_pipeline includes interpretation guardrails", {
  out <- create_gazepoint_eda_analysis_pipeline()

  expect_true(any(out$interpretation_guardrails$signal_or_method == "GSR/EDA"))
  expect_true(any(grepl("not emotional valence", out$interpretation_guardrails$conservative_interpretation)))
  expect_true(any(grepl("not direct cognition", out$interpretation_guardrails$conservative_interpretation)))
  expect_true(any(grepl("not causal timing", out$interpretation_guardrails$conservative_interpretation)))
})

test_that("create_gazepoint_eda_analysis_pipeline validates logical arguments", {
  expect_error(
    create_gazepoint_eda_analysis_pipeline(include_external_bridges = NA),
    "include_external_bridges"
  )

  expect_error(
    create_gazepoint_eda_analysis_pipeline(include_model_templates = "yes"),
    "include_model_templates"
  )

  expect_error(
    create_gazepoint_eda_analysis_pipeline(include_reporting_guidance = c(TRUE, FALSE)),
    "include_reporting_guidance"
  )
})
