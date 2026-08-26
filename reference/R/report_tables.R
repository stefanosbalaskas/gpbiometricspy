#' Create Gazepoint Biometrics report tables
#'
#' Creates compact report-ready tables from a Gazepoint Biometrics workflow
#' object or from separate workflow components. The function does not write
#' files. It returns cleaned tables that can be printed, exported, or inserted
#' into reports and supplementary materials.
#'
#' @param workflow Optional workflow object produced by
#'   `run_gazepoint_biometrics_workflow()`.
#' @param validation Optional validation object produced by
#'   `validate_gazepoint_biometrics()`.
#' @param quality Optional quality-audit table.
#' @param sampling Optional sampling/timing audit table produced by
#'   `audit_gazepoint_biometric_sampling()`.
#' @param diagnostics Optional diagnostic table produced by
#'   `diagnose_gazepoint_biometrics_workflow()`.
#' @param exclusion_recommendations Optional object produced by
#'   `recommend_gazepoint_biometric_exclusions()`.
#' @param ttl_events Optional TTL event table produced by
#'   `extract_gazepoint_ttl_events()`.
#' @param max_ttl_events Maximum number of TTL events to include in the compact
#'   TTL event table.
#'
#' @return A list of report-ready tables.
#'
#' @export
create_gazepoint_biometrics_report_tables <- function(workflow = NULL,
                                                      validation = NULL,
                                                      quality = NULL,
                                                      sampling = NULL,
                                                      diagnostics = NULL,
                                                      exclusion_recommendations = NULL,
                                                      ttl_events = NULL,
                                                      max_ttl_events = 20) {
  if (!is.null(workflow)) {
    if (!inherits(workflow, "gazepoint_biometrics_workflow")) {
      stop(
        "`workflow` must be produced by run_gazepoint_biometrics_workflow().",
        call. = FALSE
      )
    }

    validation <- workflow$validation
    quality <- workflow$quality
    sampling <- workflow$sampling
    diagnostics <- diagnose_gazepoint_biometrics_workflow(workflow)
    exclusion_recommendations <- workflow$exclusion_recommendations
    ttl_events <- workflow$ttl_events
    overview <- workflow$overview
  } else {
    overview <- NULL
  }

  out <- list(
    overview = create_report_overview_table(overview, validation),
    diagnostics = create_report_diagnostics_table(diagnostics),
    channels = create_report_channel_table(validation),
    quality = create_report_quality_table(quality),
    sampling = create_report_sampling_table(sampling),
    window_recommendations = create_report_window_recommendation_table(
      exclusion_recommendations
    ),
    participant_recommendations = create_report_participant_recommendation_table(
      exclusion_recommendations
    ),
    ttl_events = create_report_ttl_event_table(
      ttl_events,
      max_ttl_events = max_ttl_events
    )
  )

  class(out) <- c("gazepoint_biometrics_report_tables", "list")
  out
}


create_report_overview_table <- function(overview,
                                         validation) {
  if (!is.null(overview) && is.data.frame(overview)) {
    return(overview)
  }

  if (!is.null(validation) && is.list(validation) && is.data.frame(validation$overview)) {
    return(validation$overview)
  }

  data.frame(
    message = "No overview information supplied.",
    stringsAsFactors = FALSE
  )
}


create_report_diagnostics_table <- function(diagnostics) {
  if (is.null(diagnostics) || !is.data.frame(diagnostics)) {
    return(data.frame(
      message = "No workflow diagnostics table supplied.",
      stringsAsFactors = FALSE
    ))
  }

  keep_columns <- intersect(
    c(
      "final_status",
      "diagnostic_reasons",
      "validation_issue_count",
      "active_gsr_eda",
      "active_heart_rate",
      "active_engagement_dial",
      "active_ttl_marker",
      "low_quality_signal_count",
      "sampling_problem_rows",
      "n_windows",
      "keep_windows",
      "review_windows",
      "exclude_windows",
      "exclude_window_pct",
      "review_window_pct",
      "ttl_event_count"
    ),
    names(diagnostics)
  )

  diagnostics[, keep_columns, drop = FALSE]
}


create_report_channel_table <- function(validation) {
  if (is.null(validation) ||
      !is.list(validation) ||
      !is.data.frame(validation$active_channels)) {
    return(data.frame(
      message = "No active-channel table supplied.",
      stringsAsFactors = FALSE
    ))
  }

  channels <- validation$active_channels

  keep_columns <- intersect(
    c(
      "signal",
      "present",
      "active",
      "summary_column",
      "validity_columns",
      "valid_rows",
      "nonzero_rows",
      "min_value",
      "max_value"
    ),
    names(channels)
  )

  channels[, keep_columns, drop = FALSE]
}


create_report_quality_table <- function(quality) {
  if (is.null(quality) || !is.data.frame(quality)) {
    return(data.frame(
      message = "No quality-audit table supplied.",
      stringsAsFactors = FALSE
    ))
  }

  keep_columns <- intersect(
    c(
      "signal",
      "issue",
      "value_column",
      "validity_column",
      "n_rows",
      "zero_rows",
      "zero_pct",
      "valid_rows",
      "invalid_rows",
      "usable_rows",
      "usable_pct",
      "min_value",
      "max_value",
      "mean_value",
      "flatline"
    ),
    names(quality)
  )

  quality[, keep_columns, drop = FALSE]
}


create_report_sampling_table <- function(sampling) {
  if (is.null(sampling) || !is.data.frame(sampling)) {
    return(data.frame(
      message = "No sampling/timing audit table supplied.",
      stringsAsFactors = FALSE
    ))
  }

  keep_columns <- intersect(
    c(
      "source_file",
      "source_participant",
      "USER",
      "USERID",
      "participant",
      "subject",
      "MEDIA_ID",
      "MEDIA_NAME",
      "group",
      "time_column",
      "time_unit",
      "n_rows",
      "missing_time_rows",
      "missing_time_pct",
      "duplicate_time_rows",
      "zero_interval_rows",
      "negative_interval_rows",
      "monotonic_non_decreasing",
      "strictly_increasing",
      "median_interval_seconds",
      "estimated_rate_hz",
      "expected_rate_hz",
      "rate_deviation_hz",
      "rate_status"
    ),
    names(sampling)
  )

  sampling[, keep_columns, drop = FALSE]
}


create_report_window_recommendation_table <- function(exclusion_recommendations) {
  if (is.null(exclusion_recommendations) ||
      !is.list(exclusion_recommendations) ||
      !is.data.frame(exclusion_recommendations$window_recommendations)) {
    return(data.frame(
      message = "No window-level exclusion recommendations supplied.",
      stringsAsFactors = FALSE
    ))
  }

  windows <- exclusion_recommendations$window_recommendations

  keep_columns <- intersect(
    c(
      "source_participant",
      "USER",
      "USERID",
      "participant",
      "subject",
      "MEDIA_ID",
      "MEDIA_NAME",
      "gsr_usable_pct",
      "hr_usable_pct",
      "dial_usable_pct",
      "recommendation",
      "recommendation_reason"
    ),
    names(windows)
  )

  windows[, keep_columns, drop = FALSE]
}


create_report_participant_recommendation_table <- function(exclusion_recommendations) {
  if (is.null(exclusion_recommendations) ||
      !is.list(exclusion_recommendations) ||
      !is.data.frame(exclusion_recommendations$participant_recommendations)) {
    return(data.frame(
      message = "No participant-level exclusion recommendations supplied.",
      stringsAsFactors = FALSE
    ))
  }

  exclusion_recommendations$participant_recommendations
}


create_report_ttl_event_table <- function(ttl_events,
                                          max_ttl_events = 20) {
  if (is.null(ttl_events) || !is.data.frame(ttl_events)) {
    return(data.frame(
      message = "No TTL event table supplied.",
      stringsAsFactors = FALSE
    ))
  }

  keep_columns <- intersect(
    c(
      "source_participant",
      "USER",
      "USERID",
      "MEDIA_ID",
      "MEDIA_NAME",
      "row_index",
      "event_order",
      "ttl_channel",
      "ttl_value",
      "previous_ttl_value",
      "CNT",
      "TIME",
      "TIME_TICK",
      "ttl_validity"
    ),
    names(ttl_events)
  )

  ttl_events <- ttl_events[, keep_columns, drop = FALSE]

  if (!is.null(max_ttl_events) &&
      is.finite(max_ttl_events) &&
      nrow(ttl_events) > max_ttl_events) {
    ttl_events <- ttl_events[seq_len(max_ttl_events), , drop = FALSE]
  }

  ttl_events
}
