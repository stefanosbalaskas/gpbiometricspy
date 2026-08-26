#' Create a Gazepoint Biometrics reporting checklist
#'
#' Creates a compact reporting checklist for Gazepoint Biometrics exports. The
#' checklist summarises detected biometric channels, validation issues, signal
#' quality, missingness, available workflow domains, and interpretation
#' cautions. It is intended to support transparent manuscript reporting and
#' reviewer-facing methods documentation.
#'
#' @param data A data frame or a path to a Gazepoint CSV export.
#' @param require_active_signal Logical. Should inactive biometric channels be
#'   flagged in the validation output?
#'
#' @return A list with `overview`, `channels`, `quality`, `missingness`,
#'   `validation_issues`, `workflow_capabilities`, `feature_inventory`,
#'   `reporting_guidance`, and `interpretation_cautions`.
#'
#' @export
create_gazepoint_biometrics_checklist <- function(data,
                                                  require_active_signal = TRUE) {
  dat <- coerce_gazepoint_biometrics_data(data)

  validation <- validate_gazepoint_biometrics(
    dat,
    require_active_signal = require_active_signal
  )

  channels <- validation$active_channels

  quality <- combine_gazepoint_tables(list(
    audit_gazepoint_gsr_quality(dat),
    audit_gazepoint_hr_quality(dat),
    audit_gazepoint_engagement_dial(dat)
  ))

  missingness <- audit_gazepoint_biometric_missingness(dat)

  feature_inventory <- create_gazepoint_biometrics_feature_inventory()

  workflow_capabilities <- gpbiometrics_checklist_capabilities(
    feature_inventory
  )

  reporting_guidance <- gpbiometrics_checklist_reporting_guidance()

  overview <- data.frame(
    n_rows = nrow(dat),
    n_columns = ncol(dat),
    active_gsr_eda = is_signal_active(channels, "gsr_eda"),
    active_heart_rate = is_signal_active(channels, "heart_rate"),
    active_engagement_dial = is_signal_active(channels, "engagement_dial"),
    active_ttl_marker = is_signal_active(channels, "ttl_marker"),
    validation_issue_count = nrow(validation$issues),
    workflow_domain_count = feature_inventory$overview$domain_count,
    available_workflow_domains = sum(
      workflow_capabilities$status == "complete",
      na.rm = TRUE
    ),
    feature_inventory_status = feature_inventory$overview$status,
    stringsAsFactors = FALSE
  )

  cautions <- data.frame(
    topic = c(
      "GSR/EDA",
      "SCR events",
      "Heart rate",
      "Heart-rate variability",
      "IBI/RR intervals",
      "Engagement dial",
      "AOI-linked biometrics",
      "Pupil diameter",
      "Eye tracking",
      "Interoperability",
      "Plotting and visual inspection"
    ),
    caution = c(
      "GSR/EDA should be interpreted as physiological arousal or electrodermal activity, not emotional valence by itself.",
      "SCR detections are signal-processing events and should be reported with threshold, latency-window, and sensitivity settings.",
      "Heart-rate changes require baseline, task-context, and signal-quality interpretation.",
      "Heart-rate variability should be derived only from appropriate interbeat-interval or pulse information, not from a validity flag.",
      "IBI/RR intervals should be filtered for implausible values, repeated export rows, and short-duration windows before HRV interpretation.",
      "Engagement-dial values are self-reported or user-controlled continuous responses and should not be treated as automatic physiology.",
      "AOI-linked biometric summaries describe signal values during AOI exposure and do not establish emotional valence, preference, or cognitive evaluation by themselves.",
      "Pupil diameter may reflect luminance, arousal, cognitive load, fatigue, or other processes.",
      "Eye-tracking measures indicate visual attention and timing, not direct cognitive evaluation by themselves.",
      "External interoperability helpers prepare or cross-check data; external package outputs should be reported with software versions and settings.",
      "Plots are intended for quality control, synchronization checks, and transparent reporting, not as standalone inferential evidence."
    ),
    stringsAsFactors = FALSE
  )

  out <- list(
    overview = overview,
    channels = channels,
    quality = quality,
    missingness = missingness,
    validation_issues = validation$issues,
    workflow_capabilities = workflow_capabilities,
    feature_inventory = feature_inventory,
    reporting_guidance = reporting_guidance,
    interpretation_cautions = cautions
  )

  class(out) <- c("gazepoint_biometrics_checklist", "list")
  out
}


#' Create Gazepoint Biometrics methods text
#'
#' Creates a compact draft methods paragraph describing Gazepoint Biometrics
#' data processing. The text is intentionally cautious and avoids making
#' emotional or cognitive claims from physiological or eye-tracking measures
#' alone.
#'
#' @param checklist A checklist produced by
#'   `create_gazepoint_biometrics_checklist()`. If `NULL`, `data` must be
#'   supplied.
#' @param data Optional data frame or path to a Gazepoint CSV export used to
#'   create the checklist when `checklist = NULL`.
#' @param include_cautions Logical. Should interpretation cautions be appended?
#'
#' @return A character string containing draft methods text.
#'
#' @export
create_gazepoint_biometrics_methods_text <- function(checklist = NULL,
                                                     data = NULL,
                                                     include_cautions = TRUE) {
  if (is.null(checklist)) {
    if (is.null(data)) {
      stop("Either `checklist` or `data` must be supplied.", call. = FALSE)
    }

    checklist <- create_gazepoint_biometrics_checklist(data)
  }

  if (!inherits(checklist, "gazepoint_biometrics_checklist")) {
    stop(
      "`checklist` must be produced by create_gazepoint_biometrics_checklist().",
      call. = FALSE
    )
  }

  overview <- checklist$overview

  active_signals <- c(
    if (isTRUE(overview$active_gsr_eda)) "GSR/EDA",
    if (isTRUE(overview$active_heart_rate)) "heart rate",
    if (isTRUE(overview$active_engagement_dial)) "engagement dial",
    if (isTRUE(overview$active_ttl_marker)) "TTL markers"
  )

  if (length(active_signals) == 0L) {
    signal_text <- "no active biometric channels"
  } else {
    signal_text <- paste(active_signals, collapse = ", ")
  }

  capability_text <- gpbiometrics_methods_capability_sentence(checklist)

  text <- paste0(
    "Gazepoint Biometrics exports were imported and screened using gpbiometrics. ",
    "The processed table contained ",
    overview$n_rows,
    " rows and ",
    overview$n_columns,
    " columns. ",
    "Detected active channels included ",
    signal_text,
    ". ",
    "Biometric channels were checked for missing values, zero/inactive rows, ",
    "validity flags, implausible values, sudden jumps, flatlining, and usable ",
    "sample coverage. GSR/EDA summaries prioritised the Gazepoint conductance ",
    "column when available, heart-rate summaries treated raw HRV as a vendor or ",
    "validity field rather than a heart-rate-variability metric, and ",
    "engagement-dial summaries were treated as continuous user-controlled ",
    "response values. ",
    capability_text
  )

  if (isTRUE(include_cautions)) {
    text <- paste0(
      text,
      " Physiological and eye-tracking measures were interpreted conservatively: ",
      "GSR/EDA and SCR features were treated as electrodermal or ",
      "arousal-related signal information rather than emotional valence, ",
      "heart-rate and IBI-derived HRV summaries were interpreted relative to ",
      "baseline, signal quality, and window duration, AOI-linked biometric ",
      "summaries were treated as descriptive signal-by-region summaries, and ",
      "eye-tracking measures were treated as indicators of visual attention rather ",
      "than direct evidence of cognitive evaluation."
    )
  }

  text
}


gpbiometrics_checklist_capabilities <- function(feature_inventory) {
  if (!inherits(feature_inventory, "gazepoint_biometrics_feature_inventory")) {
    return(data.frame())
  }

  out <- feature_inventory$domain_summary

  if (!is.data.frame(out) || nrow(out) == 0) {
    return(data.frame())
  }

  out$reporting_relevance <- vapply(
    out$domain,
    gpbiometrics_checklist_domain_relevance,
    character(1)
  )

  out
}


gpbiometrics_checklist_domain_relevance <- function(domain) {
  switch(
    domain,
    import_and_schema = "Import, schema detection, and active-channel reporting.",
    quality_and_readiness = "Missingness, sampling, activity, time-ordering, and readiness checks.",
    preprocessing = "Baseline correction, smoothing, EDA decomposition, and conservative signal conversion.",
    eda_scr = "EDA quality, SCR detection, event-window summaries, nonresponder screening, and SCR sensitivity checks.",
    ibi_hr_hrv = "HR/IBI quality, implausible-IBI filtering, HR-IBI consistency checks, and IBI-derived HRV features.",
    ttl_alignment = "TTL extraction, event alignment, and multimodal timeline inspection.",
    aoi_biometrics = "AOI-linked biometric summaries, model-preparation tables, and AOI-biometric plotting.",
    modelling_and_windows = "Window summaries, multimodal model tables, and LME-ready data preparation.",
    reporting = "Workflow summaries, report tables, methods text, readiness gates, and report bundles.",
    interoperability = "Optional RHRV and NeuroKit2-compatible export or cross-check workflows.",
    plotting = "Contract-standardised ggplot outputs with stored plot data, settings, and interpretation notes.",
    "General package capability."
  )
}


gpbiometrics_checklist_reporting_guidance <- function() {
  data.frame(
    section = c(
      "Data source",
      "Signal quality",
      "EDA/SCR",
      "IBI/HR/HRV",
      "TTL alignment",
      "AOI-linked biometrics",
      "Modelling",
      "Interoperability",
      "Plots",
      "Interpretation"
    ),
    guidance = c(
      "Report Gazepoint export type, imported files, detected channels, row counts, and software/package versions.",
      "Report missingness, inactive channels, validity flags, sampling checks, time ordering, and exclusion criteria.",
      "Report GSR/GSR_US choice, preprocessing, SCR thresholds, response windows, and threshold-sensitivity checks when used.",
      "Report IBI source, plausibility filtering, HR-IBI consistency checks, HRV window duration, and whether HRV was derived from genuine IBI/RR intervals.",
      "Report TTL/event columns, alignment rules, event windows, and whether CNT or timestamp resets were handled within groups.",
      "Report AOI definitions, AOI exposure thresholds, signal summaries, and whether AOI-linked outputs were descriptive or model-based.",
      "Report model family, grouping structure, outcome transformations, standardisation choices, and random-effects structure where applicable.",
      "Report external package names, versions, settings, and whether interoperability helpers only prepared input or executed cross-checks.",
      "Use stored plot data/settings for reproducibility and describe plots as QC/reporting aids rather than inferential evidence.",
      "Avoid inferring emotional valence, preference, trust, scrutiny, or cognitive evaluation from biometric or eye-tracking signals alone."
    ),
    stringsAsFactors = FALSE
  )
}

gpbiometrics_methods_capability_sentence <- function(checklist) {
  if (!is.list(checklist) ||
      !"workflow_capabilities" %in% names(checklist) ||
      !is.data.frame(checklist$workflow_capabilities)) {
    return("")
  }

  capabilities <- checklist$workflow_capabilities

  complete_domains <- capabilities$domain[
    capabilities$status == "complete"
  ]

  if (length(complete_domains) == 0) {
    return("")
  }

  domain_labels <- vapply(
    complete_domains,
    gpbiometrics_methods_domain_label,
    character(1)
  )

  domain_text <- paste(domain_labels, collapse = ", ")

  paste0(
    "The available workflow inventory covered ",
    length(complete_domains),
    " complete processing domains: ",
    domain_text,
    ". These include quality/readiness checks, EDA/SCR event workflows, ",
    "IBI/HR/HRV processing, TTL alignment, AOI-linked biometric summaries, ",
    "analysis-ready model tables, interoperability exports, and ",
    "contract-standardised plots with stored plot data and settings."
  )
}


gpbiometrics_methods_domain_label <- function(domain) {
  switch(
    domain,
    import_and_schema = "import and schema detection",
    quality_and_readiness = "quality and readiness",
    preprocessing = "preprocessing",
    eda_scr = "EDA/SCR",
    ibi_hr_hrv = "IBI/HR/HRV",
    ttl_alignment = "TTL alignment",
    aoi_biometrics = "AOI-linked biometrics",
    modelling_and_windows = "modelling and window summaries",
    reporting = "reporting",
    interoperability = "interoperability",
    plotting = "plotting",
    gsub("_", " ", domain)
  )
}

is_signal_active <- function(channels, signal) {
  if (!is.data.frame(channels) || !"signal" %in% names(channels) ||
      !"active" %in% names(channels)) {
    return(FALSE)
  }

  value <- channels$active[channels$signal == signal]

  if (length(value) == 0L || is.na(value[1])) {
    return(FALSE)
  }

  isTRUE(value[1])
}
