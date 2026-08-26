#' Diagnose a Gazepoint Biometrics workflow
#'
#' Creates a compact diagnostic readiness summary from a Gazepoint Biometrics
#' workflow object. The function does not change or remove data. It returns a
#' one-row decision table with pass/review/fail status and concise reasons.
#'
#' @param workflow A workflow object produced by
#'   `run_gazepoint_biometrics_workflow()`.
#' @param require_gsr Should GSR/EDA be required for a pass status?
#' @param require_hr Should heart rate be required for a pass status?
#' @param require_dial Should engagement dial be required for a pass status?
#' @param max_exclude_window_pct Maximum acceptable percentage of excluded
#'   windows before the workflow is marked as fail.
#' @param max_review_window_pct Maximum acceptable percentage of review windows
#'   before the workflow is marked as review.
#'
#' @return A one-row data frame with diagnostic status and reasons.
#'
#' @export
diagnose_gazepoint_biometrics_workflow <- function(workflow,
                                                   require_gsr = TRUE,
                                                   require_hr = TRUE,
                                                   require_dial = FALSE,
                                                   max_exclude_window_pct = 25,
                                                   max_review_window_pct = 25) {
  if (!inherits(workflow, "gazepoint_biometrics_workflow")) {
    stop(
      "`workflow` must be produced by run_gazepoint_biometrics_workflow().",
      call. = FALSE
    )
  }

  validation_issues <- nrow(workflow$validation$issues)

  active_channels <- workflow$validation$active_channels

  gsr_active <- is_signal_active(active_channels, "gsr_eda")
  hr_active <- is_signal_active(active_channels, "heart_rate")
  dial_active <- is_signal_active(active_channels, "engagement_dial")
  ttl_active <- is_signal_active(active_channels, "ttl_marker")

  required_channel_failures <- character(0)

  if (isTRUE(require_gsr) && !isTRUE(gsr_active)) {
    required_channel_failures <- c(required_channel_failures, "GSR/EDA inactive")
  }

  if (isTRUE(require_hr) && !isTRUE(hr_active)) {
    required_channel_failures <- c(required_channel_failures, "heart rate inactive")
  }

  if (isTRUE(require_dial) && !isTRUE(dial_active)) {
    required_channel_failures <- c(required_channel_failures, "engagement dial inactive")
  }

  quality <- workflow$quality

  low_quality_signals <- character(0)

  if (is.data.frame(quality) && "signal" %in% names(quality) && "usable_pct" %in% names(quality)) {
    low_quality <- quality[!is.na(quality$usable_pct) & quality$usable_pct < 50, , drop = FALSE]

    if (nrow(low_quality) > 0L) {
      low_quality_signals <- unique(low_quality$signal)
    }
  }

  sampling <- workflow$sampling

  sampling_problem_rows <- 0L

  if (is.data.frame(sampling)) {
    bad_sampling <- rep(FALSE, nrow(sampling))

    if ("duplicate_time_rows" %in% names(sampling)) {
      bad_sampling <- bad_sampling | (!is.na(sampling$duplicate_time_rows) & sampling$duplicate_time_rows > 0)
    }

    if ("zero_interval_rows" %in% names(sampling)) {
      bad_sampling <- bad_sampling | (!is.na(sampling$zero_interval_rows) & sampling$zero_interval_rows > 0)
    }

    if ("negative_interval_rows" %in% names(sampling)) {
      bad_sampling <- bad_sampling | (!is.na(sampling$negative_interval_rows) & sampling$negative_interval_rows > 0)
    }

    if ("rate_status" %in% names(sampling)) {
      bad_sampling <- bad_sampling | sampling$rate_status == "outside_tolerance"
    }

    sampling_problem_rows <- sum(bad_sampling, na.rm = TRUE)
  }

  exclusion_summary <- summarise_workflow_exclusion_status(workflow)

  ttl_event_count <- ifelse(
    !is.null(workflow$ttl_events) && is.data.frame(workflow$ttl_events),
    nrow(workflow$ttl_events),
    NA_integer_
  )

  reasons <- character(0)
  fail_reasons <- character(0)
  review_reasons <- character(0)

  if (validation_issues > 0L) {
    fail_reasons <- c(fail_reasons, paste0(validation_issues, " validation issue(s)"))
  }

  if (length(required_channel_failures) > 0L) {
    fail_reasons <- c(fail_reasons, paste(required_channel_failures, collapse = "; "))
  }

  if (exclusion_summary$exclude_window_pct > max_exclude_window_pct) {
    fail_reasons <- c(
      fail_reasons,
      paste0(
        "excluded windows exceed ",
        max_exclude_window_pct,
        "% threshold"
      )
    )
  }

  if (length(low_quality_signals) > 0L) {
    review_reasons <- c(
      review_reasons,
      paste0(
        "low usable coverage in ",
        paste(low_quality_signals, collapse = ", ")
      )
    )
  }

  if (sampling_problem_rows > 0L) {
    review_reasons <- c(
      review_reasons,
      paste0(sampling_problem_rows, " sampling/timing problem row(s)")
    )
  }

  if (exclusion_summary$review_window_pct > max_review_window_pct) {
    review_reasons <- c(
      review_reasons,
      paste0(
        "review windows exceed ",
        max_review_window_pct,
        "% threshold"
      )
    )
  }

  if (is.na(ttl_event_count)) {
    review_reasons <- c(review_reasons, "TTL events not extracted")
  }

  final_status <- if (length(fail_reasons) > 0L) {
    "fail"
  } else if (length(review_reasons) > 0L) {
    "review"
  } else {
    "pass"
  }

  reasons <- c(fail_reasons, review_reasons)

  if (length(reasons) == 0L) {
    reasons <- "workflow diagnostics passed"
  }

  data.frame(
    final_status = final_status,
    diagnostic_reasons = paste(reasons, collapse = "; "),
    validation_issue_count = validation_issues,
    active_gsr_eda = gsr_active,
    active_heart_rate = hr_active,
    active_engagement_dial = dial_active,
    active_ttl_marker = ttl_active,
    low_quality_signal_count = length(low_quality_signals),
    sampling_problem_rows = sampling_problem_rows,
    n_windows = exclusion_summary$n_windows,
    keep_windows = exclusion_summary$keep_windows,
    review_windows = exclusion_summary$review_windows,
    exclude_windows = exclusion_summary$exclude_windows,
    exclude_window_pct = exclusion_summary$exclude_window_pct,
    review_window_pct = exclusion_summary$review_window_pct,
    ttl_event_count = ttl_event_count,
    stringsAsFactors = FALSE
  )
}


summarise_workflow_exclusion_status <- function(workflow) {
  empty <- data.frame(
    n_windows = NA_integer_,
    keep_windows = NA_integer_,
    review_windows = NA_integer_,
    exclude_windows = NA_integer_,
    exclude_window_pct = NA_real_,
    review_window_pct = NA_real_,
    stringsAsFactors = FALSE
  )

  exclusions <- workflow$exclusion_recommendations

  if (is.null(exclusions) ||
      !is.list(exclusions) ||
      !is.data.frame(exclusions$window_recommendations)) {
    return(empty)
  }

  rec <- exclusions$window_recommendations$recommendation

  n_windows <- length(rec)
  keep_windows <- sum(rec == "keep")
  review_windows <- sum(rec == "review")
  exclude_windows <- sum(rec == "exclude")

  data.frame(
    n_windows = n_windows,
    keep_windows = keep_windows,
    review_windows = review_windows,
    exclude_windows = exclude_windows,
    exclude_window_pct = safe_pct(exclude_windows, n_windows),
    review_window_pct = safe_pct(review_windows, n_windows),
    stringsAsFactors = FALSE
  )
}
