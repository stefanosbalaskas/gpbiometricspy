#' Format the gpbiometrics feature inventory for users
#'
#' Adds user-facing labels and interpretation metadata to the package feature
#' inventory. This helper is intentionally non-breaking: it does not replace the
#' core inventory object returned by `create_gazepoint_biometrics_feature_inventory()`.
#'
#' @param inventory Optional inventory object returned by
#'   `create_gazepoint_biometrics_feature_inventory()`. If `NULL`, a fresh
#'   inventory is created.
#' @param include_internal Logical. Passed to
#'   `create_gazepoint_biometrics_feature_inventory()` when `inventory = NULL`.
#' @param sort Logical. If `TRUE`, sort by domain, user level, and function name.
#'
#' @return A data frame with polished user-facing inventory columns.
#' @export
format_gazepoint_biometrics_feature_inventory <- function(inventory = NULL,
                                                          include_internal = FALSE,
                                                          sort = TRUE) {
  if (is.null(inventory)) {
    inventory <- create_gazepoint_biometrics_feature_inventory(
      include_internal = include_internal
    )
  }

  if (is.data.frame(inventory)) {
    tab <- inventory
  } else if (is.list(inventory) && "inventory" %in% names(inventory)) {
    tab <- inventory$inventory
  } else {
    stop(
      "`inventory` must be a data frame or an object returned by `create_gazepoint_biometrics_feature_inventory()`.",
      call. = FALSE
    )
  }

  required <- c("domain", "function_name", "available", "status")
  missing_required <- setdiff(required, names(tab))

  if (length(missing_required) > 0) {
    stop(
      "Inventory table is missing required columns: ",
      paste(missing_required, collapse = ", "),
      call. = FALSE
    )
  }

  out <- tab

  out$domain_label <- gpbiometrics_inventory_domain_label(out$domain)
  out$workflow_stage <- gpbiometrics_inventory_workflow_stage(out$domain)
  out$method_family <- vapply(
    out$function_name,
    gpbiometrics_inventory_method_family,
    character(1)
  )
  out$user_level <- vapply(
    out$function_name,
    gpbiometrics_inventory_user_level,
    character(1)
  )
  out$interpretation_caution <- vapply(
    out$function_name,
    gpbiometrics_inventory_caution,
    character(1)
  )

  out$availability_label <- ifelse(
    isTRUE_VECTOR(out$available),
    "Available",
    "Missing"
  )

  preferred_order <- c(
    "domain",
    "domain_label",
    "workflow_stage",
    "method_family",
    "user_level",
    "function_name",
    "interpretation_caution",
    "expected",
    "user_facing",
    "available",
    "availability_label",
    "status"
  )

  preferred_order <- preferred_order[preferred_order %in% names(out)]
  extra_cols <- setdiff(names(out), preferred_order)

  out <- out[, c(preferred_order, extra_cols), drop = FALSE]

  if (isTRUE(sort)) {
    level_rank <- match(out$user_level, c("Core", "Intermediate", "Advanced"))
    level_rank[is.na(level_rank)] <- 99

    out <- out[order(out$domain, level_rank, out$method_family, out$function_name), , drop = FALSE]
  }

  rownames(out) <- NULL
  out
}

#' Summarise the formatted gpbiometrics feature inventory
#'
#' @param formatted_inventory Optional table returned by
#'   `format_gazepoint_biometrics_feature_inventory()`.
#'
#' @return A list with domain, method-family, and user-level summaries.
#' @export
summarise_gazepoint_biometrics_feature_inventory <- function(formatted_inventory = NULL) {
  if (is.null(formatted_inventory)) {
    formatted_inventory <- format_gazepoint_biometrics_feature_inventory()
  }

  required <- c("domain", "domain_label", "method_family", "user_level", "available")
  missing_required <- setdiff(required, names(formatted_inventory))

  if (length(missing_required) > 0) {
    stop(
      "`formatted_inventory` is missing required columns: ",
      paste(missing_required, collapse = ", "),
      call. = FALSE
    )
  }

  domain_summary <- stats::aggregate(
    available ~ domain + domain_label,
    data = formatted_inventory,
    FUN = function(x) c(feature_count = length(x), available_features = sum(x))
  )

  domain_summary <- data.frame(
    domain = domain_summary$domain,
    domain_label = domain_summary$domain_label,
    feature_count = domain_summary$available[, "feature_count"],
    available_features = domain_summary$available[, "available_features"],
    stringsAsFactors = FALSE
  )

  domain_summary$missing_features <- domain_summary$feature_count -
    domain_summary$available_features
  domain_summary$completion_rate <- domain_summary$available_features /
    domain_summary$feature_count
  domain_summary$status <- ifelse(
    domain_summary$missing_features == 0,
    "complete",
    "incomplete"
  )

  method_summary <- stats::aggregate(
    available ~ method_family,
    data = formatted_inventory,
    FUN = function(x) c(feature_count = length(x), available_features = sum(x))
  )

  method_summary <- data.frame(
    method_family = method_summary$method_family,
    feature_count = method_summary$available[, "feature_count"],
    available_features = method_summary$available[, "available_features"],
    stringsAsFactors = FALSE
  )

  method_summary$missing_features <- method_summary$feature_count -
    method_summary$available_features

  user_level_summary <- stats::aggregate(
    available ~ user_level,
    data = formatted_inventory,
    FUN = function(x) c(feature_count = length(x), available_features = sum(x))
  )

  user_level_summary <- data.frame(
    user_level = user_level_summary$user_level,
    feature_count = user_level_summary$available[, "feature_count"],
    available_features = user_level_summary$available[, "available_features"],
    stringsAsFactors = FALSE
  )

  user_level_summary$missing_features <- user_level_summary$feature_count -
    user_level_summary$available_features

  list(
    overview = data.frame(
      feature_rows = nrow(formatted_inventory),
      domain_count = length(unique(formatted_inventory$domain)),
      method_family_count = length(unique(formatted_inventory$method_family)),
      user_level_count = length(unique(formatted_inventory$user_level)),
      available_features = sum(formatted_inventory$available),
      missing_features = sum(!formatted_inventory$available),
      status = if (all(formatted_inventory$available)) {
        "formatted_inventory_complete"
      } else {
        "formatted_inventory_incomplete"
      },
      stringsAsFactors = FALSE
    ),
    domain_summary = domain_summary,
    method_summary = method_summary,
    user_level_summary = user_level_summary
  )
}

gpbiometrics_inventory_domain_label <- function(domain) {
  labels <- c(
    import_and_schema = "Import and schema",
    quality_and_readiness = "Quality and readiness",
    preprocessing = "Preprocessing and correction",
    eda_scr = "EDA, GSR, and SCR",
    ibi_hr_hrv = "Pulse, IBI, HR, HRV, and respiration",
    ttl_alignment = "TTL and synchronisation",
    aoi_biometrics = "AOI and multimodal summaries",
    modelling_and_windows = "Windows and model-ready data",
    reporting = "Reporting and documentation",
    interoperability = "External interoperability",
    plotting = "Plotting and visual diagnostics"
  )

  unname(ifelse(domain %in% names(labels), labels[domain], domain))
}

gpbiometrics_inventory_workflow_stage <- function(domain) {
  stages <- c(
    import_and_schema = "1. Import",
    quality_and_readiness = "2. Quality control",
    preprocessing = "3. Preprocessing",
    eda_scr = "4. Signal features",
    ibi_hr_hrv = "4. Signal features",
    ttl_alignment = "5. Timing and alignment",
    aoi_biometrics = "6. Multimodal summaries",
    modelling_and_windows = "7. Analysis preparation",
    reporting = "8. Reporting",
    interoperability = "9. External bridges",
    plotting = "10. Visualisation"
  )

  unname(ifelse(domain %in% names(stages), stages[domain], "Other"))
}

gpbiometrics_inventory_method_family <- function(function_name) {
  fn <- tolower(function_name)

  if (grepl("import|schema|column|name|detect_active|simulate", fn)) {
    return("Import, schema, or simulation")
  }

  if (grepl("readiness|diagnose|validate|audit|missing|validity|dropout|exclusion|drift|stabilization", fn)) {
    return("Quality control and readiness")
  }

  if (grepl("standardi|filter|smooth|ema|baseline|correct|regress|denoise|artifact|temperature|luminance|preprocess", fn)) {
    return("Preprocessing and confound control")
  }

  if (grepl("eda|gsr|scr|skin|cvxeda|ledalab|pspm|tvsymp|susceptance|admittance", fn)) {
    return("EDA/GSR/SCR analysis")
  }

  if (grepl("ibi|hrv|heart|hr_|hrp|ppg|pulse|beat|rsa|respiration|ipfm|fuzzy|entropy|rcmse|rqa|lorenz|csi", fn)) {
    return("Cardiovascular and respiration analysis")
  }

  if (grepl("ttl|sync|align|lag|time_reset", fn)) {
    return("Timing and synchronisation")
  }

  if (grepl("aoi|multimodal", fn)) {
    return("AOI and multimodal summaries")
  }

  if (grepl("window|model|lme|hurdle|chunk|online_design|point_process|causality", fn)) {
    return("Model-ready data and advanced modelling")
  }

  if (grepl("report|bundle|checklist|preregistration|pipeline|statistics|export", fn)) {
    return("Reporting, export, and reproducibility")
  }

  if (grepl("plot|dashboard|gram|timeline", fn)) {
    return("Plotting and visual diagnostics")
  }

  "General helper"
}

gpbiometrics_inventory_user_level <- function(function_name) {
  fn <- tolower(function_name)

  advanced_patterns <- paste(
    c(
      "ceemdan",
      "kalman",
      "fuzzy",
      "rcmse",
      "rqa",
      "geometric",
      "nonlinear",
      "ipfm",
      "cvxeda",
      "pspm",
      "ledalab",
      "ctsi",
      "svm",
      "autoencoder",
      "wavelet",
      "tvsymp",
      "point_process",
      "causality",
      "surrogate",
      "doubly_stochastic",
      "spectral",
      "complexity",
      "susceptance",
      "admittance",
      "skin_potential",
      "bilateral",
      "online_design",
      "multiverse",
      "xdf"
    ),
    collapse = "|"
  )

  core_patterns <- paste(
    c(
      "^import_",
      "^detect_gazepoint_biometric",
      "^check_gazepoint_biometric",
      "^validate_",
      "^summarise_",
      "^run_gazepoint_biometrics_workflow",
      "^diagnose_gazepoint_biometrics_workflow",
      "^run_gazepoint_biometrics_real_data_readiness",
      "^create_gazepoint_biometrics_report",
      "^export_gazepoint_biometrics_report_bundle",
      "^create_gazepoint_biometrics_feature_inventory"
    ),
    collapse = "|"
  )

  if (grepl(advanced_patterns, fn)) {
    return("Advanced")
  }

  if (grepl(core_patterns, fn)) {
    return("Core")
  }

  "Intermediate"
}

gpbiometrics_inventory_caution <- function(function_name) {
  fn <- tolower(function_name)

  if (grepl("eda|gsr|scr|skin|cvxeda|ledalab|pspm|tvsymp|susceptance|admittance", fn)) {
    return("EDA/SCR outputs describe electrodermal dynamics; they do not directly infer emotion, stress, cognition, health status, or diagnosis.")
  }

  if (grepl("ibi|hrv|heart|hr_|hrp|ppg|pulse|beat|rsa|respiration|ipfm|fuzzy|entropy|rcmse|rqa|csi", fn)) {
    return("Cardiovascular and respiration outputs are physiological descriptors or proxies; they are not clinical or psychological labels.")
  }

  if (grepl("pupil|luminance", fn)) {
    return("Pupil outputs are strongly affected by luminance and visual context; residuals are not proof of cognitive-load-only effects.")
  }

  if (grepl("aoi|gaze|fixation|saccade", fn)) {
    return("AOI and gaze outputs describe visual timing/allocation; they do not prove comprehension, scrutiny, or preference.")
  }

  if (grepl("statistics|anova|kruskal|posthoc", fn)) {
    return("Automated statistics are exploratory convenience summaries and should be checked against the study design.")
  }

  if (grepl("online_design", fn)) {
    return("Online design output is decision support only and does not autonomously control experiments.")
  }

  if (grepl("import|schema|report|bundle|inventory|plot|dashboard|ttl|sync|align", fn)) {
    return("Use this output to document processing decisions; interpretation depends on the study design and signal quality.")
  }

  "Interpret conservatively and review assumptions before confirmatory use."
}

isTRUE_VECTOR <- function(x) {
  !is.na(x) & x
}
