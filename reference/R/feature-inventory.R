#' Create a gpbiometrics feature inventory
#'
#' Creates a structured inventory of implemented gpbiometrics helper functions.
#' This is useful for reporting, readiness checks, documentation, and package
#' development audits.
#'
#' @param include_internal Logical. If `TRUE`, also checks for non-exported
#'   internal helper names when they are included in the inventory.
#'
#' @return A list with `overview`, `inventory`, `domain_summary`,
#'   `missing_expected`, and `settings`.
#' @export
create_gazepoint_biometrics_feature_inventory <- function(include_internal = FALSE) {
  if (!is.logical(include_internal) ||
      length(include_internal) != 1 ||
      is.na(include_internal)) {
    stop("`include_internal` must be TRUE or FALSE.", call. = FALSE)
  }

  inventory <- gpbiometrics_feature_inventory_table()

  inventory$available <- vapply(
    inventory$function_name,
    gpbiometrics_feature_inventory_exists,
    logical(1),
    include_internal = include_internal
  )

  inventory$status <- ifelse(
    inventory$available,
    "available",
    "missing"
  )

  domain_summary <- gpbiometrics_feature_inventory_domain_summary(inventory)

  missing_expected <- inventory[
    !inventory$available & inventory$expected,
    ,
    drop = FALSE
  ]

  overview <- data.frame(
    feature_rows = nrow(inventory),
    domain_count = length(unique(inventory$domain)),
    available_features = sum(inventory$available, na.rm = TRUE),
    missing_expected_features = nrow(missing_expected),
    include_internal = include_internal,
    status = if (nrow(missing_expected) == 0) {
      "feature_inventory_complete"
    } else {
      "warn_expected_features_missing"
    },
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      inventory = inventory,
      domain_summary = domain_summary,
      missing_expected = missing_expected,
      settings = list(
        include_internal = include_internal,
        interpretation_notes = c(
          "The inventory checks whether major user-facing gpbiometrics helpers are available.",
          "A missing expected feature indicates a documentation or implementation mismatch.",
          "The inventory supports reporting and readiness-polish workflows; it does not analyse data."
        )
      )
    ),
    class = c("gazepoint_biometrics_feature_inventory", "list")
  )
}

gpbiometrics_feature_inventory_table <- function() {
  expected_by_domain <- list(
    import_and_schema = c(
      "import_gazepoint_biometrics",
      "import_gazepoint_biometric_folder",
      "import_gazepoint_data_summary",
      "check_gazepoint_biometric_columns",
      "import_gazepoint_lsl_xdf",
      "standardise_gazepoint_biometric_names",
      "detect_gazepoint_biometric_schema",
      "detect_gazepoint_time_columns",
      "simulate_gazepoint_biometrics",
      "detect_active_biometric_channels"
    ),


    quality_and_readiness = c(
      "validate_gazepoint_biometrics",
      "summarise_gazepoint_biometric_validity",
      "audit_gazepoint_biometric_missingness",
      "flag_gazepoint_biometric_dropouts",
      "audit_gazepoint_biometric_sampling",
      "audit_gazepoint_signal_activity",
      "audit_gazepoint_time_resets",
      "recommend_gazepoint_biometric_exclusions",
      "run_gazepoint_biometrics_real_data_readiness",
      "audit_gazepoint_distributional_drift",
      "audit_gazepoint_gsr_units",
      "prepare_gazepoint_artifact_svm_features",
      "flag_gazepoint_mad_artifacts",
      "flag_gazepoint_artifacts_svm"
    ),

    preprocessing = c(
      "standardise_gazepoint_zscore",
      "standardize_gazepoint_zscore",
      "standardise_gazepoint_range_correction",
      "standardize_gazepoint_range_correction",
      "baseline_correct_gazepoint_pupil",
      "standardise_gazepoint_adaptive_ema",
      "standardize_gazepoint_adaptive_ema",
      "baseline_correct_gazepoint_gsr",
      "baseline_correct_gazepoint_hr",
      "smooth_gazepoint_biometrics",
      "convert_gazepoint_gsr_to_conductance",
      "decompose_gazepoint_eda",
      "denoise_gazepoint_eda_wavelet",
      "denoise_gazepoint_eda_autoencoder",
      "denoise_gazepoint_ppg_autoencoder",
      "denoise_gazepoint_quantization_noise",
      "correct_gazepoint_eda_temperature",
      "audit_gazepoint_stabilization_period",
      "regress_gazepoint_pupil_luminance",
      "standardize_gazepoint_biometrics_within_unit",
      "standardise_gazepoint_biometrics_within_unit"
    ),

    eda_scr = c(
      "classify_gazepoint_eda_response_pattern",
      "classify_gazepoint_scr_intervals",
      "flag_kleckner_eda_artifacts",
      "audit_gazepoint_gsr_quality",
      "audit_gazepoint_eda_artifacts",
      "detect_gazepoint_scr_events",
      "detect_gazepoint_scr_peaks",
      "summarise_gazepoint_scr_event_windows",
      "prepare_gazepoint_scr_hurdle_model_data",
      "run_gazepoint_scr_threshold_sensitivity",
      "run_gazepoint_scr_multiverse",
      "screen_gazepoint_eda_nonresponders",
      "summarise_gazepoint_gsr_windows",
      "summarise_gazepoint_gsr_tonic_phasic",
      "extract_gazepoint_eda_spectral_power",
      "extract_gazepoint_eda_complexity",
      "extract_gazepoint_eda_tvsymp",
      "plot_gazepoint_eda_decomposition",
      "optimize_gazepoint_cvxeda_tau",
      "model_gazepoint_eda_point_process",
      "extract_gazepoint_bilateral_eda_asymmetry",
      "analyze_gazepoint_skin_potential",
      "analyze_gazepoint_ac_susceptance",
      "detect_gazepoint_doubly_stochastic_changepoints",
      "extract_gazepoint_scr_recovery_times",
      "plot_gazepoint_scr_events"
    ),

    ibi_hr_hrv = c(
      "audit_gazepoint_hr_quality",
      "assess_gazepoint_hrp_waveform_quality",
      "audit_gazepoint_ibi_quality",
      "filter_gazepoint_ibi_implausible",
      "compare_gazepoint_hr_ibi_consistency",
      "summarise_gazepoint_hr_windows",
      "summarise_gazepoint_ibi_windows",
      "summarise_gazepoint_ibi_hrv_windows",
      "extract_gazepoint_hrv_features",
      "extract_gazepoint_pdr_signals",
      "calculate_gazepoint_rsa",
      "test_gazepoint_hrv_nonlinearity",
      "extract_gazepoint_hrv_rqa",
      "extract_gazepoint_hrv_geometric",
      "extract_gazepoint_hrv_fragmentation",
      "extract_gazepoint_hrv_asymmetry",
      "model_gazepoint_hr_point_process",
      "analyze_gazepoint_cardiorespiratory_causality",
      "extract_gazepoint_edr_pca",
      "extract_gazepoint_hrv_rcmse",
      "extract_gazepoint_respiration_ceemdan",
      "fuse_gazepoint_respiration_kalman",
      "extract_gazepoint_hrv_fuzzy_csi",
      "extract_gazepoint_beats_kmeans",
      "model_gazepoint_hrv_ipfm",
      "extract_gazepoint_hrv_nonlinear"
    ),

    ttl_alignment = c(
      "extract_gazepoint_ttl_events",
      "align_gazepoint_biometrics_to_ttl",
      "estimate_gazepoint_signal_lag",
      "audit_gazepoint_biometric_sync_drift",
      "plot_gazepoint_multimodal_timeline"
    ),

    aoi_biometrics = c(
      "summarise_gazepoint_aoi_biometrics",
      "prepare_gazepoint_aoi_biometrics_model_data",
      "plot_gazepoint_aoi_biometrics"
    ),

    modelling_and_windows = c(
      "summarise_gazepoint_engagement_windows",
      "summarise_gazepoint_dial_windows",
      "summarise_gazepoint_multimodal_windows",
      "summarise_gazepoint_full_biometric_windows",
      "sync_gazepoint_biometrics_with_gaze",
      "join_gazepoint_biometrics_to_master",
      "chunk_gazepoint_biometrics",
      "run_gazepoint_online_design_optimization",
      "prepare_gazepoint_multimodal_model_data",
      "prepare_gazepoint_biometrics_lme_data"
    ),

    reporting = c(
      "create_gazepoint_preregistration_template",
      "run_gpbiometrics_shiny",
      "run_gpbiometrics_shiny_annotator",
      "run_gazepoint_biometrics_workflow",
      "summarise_gazepoint_biometrics_workflow",
      "diagnose_gazepoint_biometrics_workflow",
      "create_gazepoint_biometrics_checklist",
      "create_gazepoint_biometrics_methods_text",
      "create_gazepoint_eda_analysis_pipeline",
      "run_gazepoint_eda_analysis_pipeline",
      "create_gazepoint_biometrics_report_tables",
      "write_gazepoint_biometrics_report_tables",
      "create_gazepoint_biometrics_report",
      "run_gazepoint_automated_statistics",
      "export_gazepoint_biometrics_report_bundle"
    ),

    interoperability = c(
      "export_gazepoint_rhrv_input",
      "prepare_gazepoint_rhrv_input",
      "prepare_gazepoint_pyppg_input",
      "prepare_gazepoint_neurokit_eda_input",
      "run_gazepoint_neurokit_eda_crosscheck",
      "prepare_gazepoint_ledalab_input",
      "prepare_gazepoint_pspm_input",
      "prepare_gazepoint_pspm_dcm_input",
      "prepare_gazepoint_ctsi_input",
      "prepare_gazepoint_cvxeda_input"
    ),

    plotting = c(
      "plot_gazepoint_biometric_signals",
      "plot_gazepoint_biometric_quality",
      "plot_gazepoint_eda_decomposition",
      "plot_gazepoint_scr_events",
      "plot_gazepoint_multimodal_timeline",
      "plot_gazepoint_signal_activity",
      "plot_gazepoint_time_resets",
      "plot_gazepoint_biometric_report_dashboard",
      "plot_gazepoint_saccade_main_sequence",
      "standardise_gazepoint_plot_contract",
      "standardize_gazepoint_plot_contracts",
      "check_gazepoint_plot_contract",
      "plot_gazepoint_scr_specification_curve",
      "plot_gazepoint_eda_gram",
      "get_gazepoint_plot_data"
    )


  )

  inventory <- data.frame(
    domain = rep(names(expected_by_domain), lengths(expected_by_domain)),
    function_name = unlist(expected_by_domain, use.names = FALSE),
    expected = TRUE,
    user_facing = TRUE,
    stringsAsFactors = FALSE
  )

  rownames(inventory) <- NULL
  inventory
}

gpbiometrics_feature_inventory_exists <- function(function_name,
                                                  include_internal = FALSE) {
  ns <- tryCatch(
    asNamespace("gpbiometrics"),
    error = function(e) NULL
  )

  if (!is.null(ns) &&
      exists(function_name, envir = ns, mode = "function", inherits = FALSE)) {
    return(TRUE)
  }

  if (exists(function_name, mode = "function", inherits = TRUE)) {
    return(TRUE)
  }

  if (isTRUE(include_internal) && !is.null(ns)) {
    return(exists(function_name, envir = ns, mode = "function", inherits = TRUE))
  }

  FALSE
}

gpbiometrics_feature_inventory_domain_summary <- function(inventory) {
  domains <- unique(inventory$domain)

  out <- lapply(domains, function(domain) {
    d <- inventory[inventory$domain == domain, , drop = FALSE]


    data.frame(
      domain = domain,
      feature_count = nrow(d),
      available_features = sum(d$available, na.rm = TRUE),
      missing_features = sum(!d$available, na.rm = TRUE),
      completion_rate = if (nrow(d) > 0) {
        sum(d$available, na.rm = TRUE) / nrow(d)
      } else {
        NA_real_
      },
      status = if (all(d$available)) {
        "complete"
      } else if (any(d$available)) {
        "partial"
      } else {
        "missing"
      },
      stringsAsFactors = FALSE
    )


  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}
