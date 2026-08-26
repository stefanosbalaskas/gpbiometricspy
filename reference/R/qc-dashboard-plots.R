#' Plot Gazepoint biometric signal activity
#'
#' Plots signal-activity summaries produced by
#' [audit_gazepoint_signal_activity()], or computes them from a biometric data
#' frame. The plot is intended for quality-control review of signal
#' availability, missingness, zero activity, and basic activity status. It does
#' not infer emotion, valence, cognition, preference, trust, or physiological
#' diagnosis.
#'
#' @param data A Gazepoint biometric data frame, or an
#'   `audit_gazepoint_signal_activity()` result.
#' @param signal_cols Optional signal columns used when `data` is a raw data
#'   frame.
#' @param group_cols Optional grouping columns used when `data` is a raw data
#'   frame.
#' @param metric Summary metric to plot.
#' @param max_groups Maximum number of groups to display.
#' @param title Optional plot title.
#'
#' @return A ggplot object with the package plot contract attached.
#' @export
plot_gazepoint_signal_activity <- function(data,
                                           signal_cols = NULL,
                                           group_cols = NULL,
                                           metric = c(
                                             "active_signal",
                                             "nonzero_prop",
                                             "missing_prop",
                                             "n_unique_finite"
                                           ),
                                           max_groups = 30,
                                           title = NULL) {
  gpbiometrics_require_ggplot2()

  metric <- match.arg(metric)

  if (!is.numeric(max_groups) || length(max_groups) != 1 ||
      is.na(max_groups) || max_groups < 1) {
    stop("`max_groups` must be a single positive number.", call. = FALSE)
  }

  activity <- gpbiometrics_qc_plot_extract_signal_activity(
    data = data,
    signal_cols = signal_cols,
    group_cols = group_cols
  )

  plot_data <- as.data.frame(activity$signal_by_group, stringsAsFactors = FALSE)

  if (nrow(plot_data) == 0) {
    stop("No signal-activity rows were available for plotting.", call. = FALSE)
  }

  plot_data <- gpbiometrics_qc_plot_ensure_activity_metrics(plot_data)

  if (!metric %in% names(plot_data)) {
    stop("Metric `", metric, "` was not found in the signal-activity summary.", call. = FALSE)
  }

  plot_data$.plot_group <- gpbiometrics_qc_plot_group_label(plot_data)
  plot_data$.plot_value <- gpbiometrics_qc_plot_metric_to_numeric(plot_data[[metric]])
  plot_data$.plot_metric <- metric

  selected_groups <- unique(plot_data$.plot_group)

  if (length(selected_groups) > max_groups) {
    selected_groups <- selected_groups[seq_len(max_groups)]
    plot_data <- plot_data[plot_data$.plot_group %in% selected_groups, , drop = FALSE]
  }

  if (is.null(title)) {
    title <- "Gazepoint biometric signal activity"
  }

  p <- ggplot2::ggplot(
    plot_data,
    ggplot2::aes(x = .data$signal, y = .data$.plot_value)
  ) +
    ggplot2::geom_col() +
    ggplot2::facet_wrap(stats::as.formula("~ .plot_group"), scales = "free_x") +
    ggplot2::labs(
      title = title,
      subtitle = "QC summary only; signal activity is not evidence of emotion, valence, cognition, or preference.",
      x = "Signal",
      y = metric
    ) +
    ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 45, hjust = 1))

  settings <- list(
    plot_type = "signal_activity",
    metric = metric,
    signal_cols = signal_cols,
    group_cols = group_cols,
    max_groups = max_groups,
    interpretation_notes = c(
      "Signal activity plots summarize availability and basic variation.",
      "They do not infer emotion, valence, cognition, trust, preference, or physiological diagnosis."
    )
  )

  standardise_gazepoint_plot_contract(
    plot = p,
    plot_data = plot_data,
    settings = settings,
    interpretation_notes = settings$interpretation_notes,
    plot_type = "signal_activity"
  )
}

#' Plot Gazepoint time resets and time-order flags
#'
#' Plots row-level time/counter progression and flags from
#' [audit_gazepoint_time_resets()], or computes them from a biometric data
#' frame. The plot is intended for synchronization and file-structure QC. It
#' does not establish causal timing or true physiological latency.
#'
#' @param data A Gazepoint biometric data frame, or an
#'   `audit_gazepoint_time_resets()` result.
#' @param time_col Optional time or counter column used when `data` is a raw
#'   data frame.
#' @param group_cols Optional grouping columns used when `data` is a raw data
#'   frame.
#' @param max_groups Maximum number of groups to display.
#' @param title Optional plot title.
#'
#' @return A ggplot object with the package plot contract attached.
#' @export
plot_gazepoint_time_resets <- function(data,
                                       time_col = NULL,
                                       group_cols = NULL,
                                       max_groups = 30,
                                       title = NULL) {
  gpbiometrics_require_ggplot2()

  if (!is.numeric(max_groups) || length(max_groups) != 1 ||
      is.na(max_groups) || max_groups < 1) {
    stop("`max_groups` must be a single positive number.", call. = FALSE)
  }

  reset_audit <- gpbiometrics_qc_plot_extract_time_resets(
    data = data,
    time_col = time_col,
    group_cols = group_cols
  )

  plot_data <- as.data.frame(reset_audit$row_flags, stringsAsFactors = FALSE)

  if (nrow(plot_data) == 0) {
    stop("No time-reset rows were available for plotting.", call. = FALSE)
  }

  if (!"time_value" %in% names(plot_data)) {
    stop("The time-reset audit must contain a `time_value` column.", call. = FALSE)
  }

  if ("group_row_index" %in% names(plot_data)) {
    plot_data$.plot_index <- plot_data$group_row_index
  } else {
    plot_data$.plot_index <- seq_len(nrow(plot_data))
  }

  plot_data$.plot_group <- gpbiometrics_qc_plot_group_label(plot_data)

  issue_cols <- intersect(
    c(
      "flag_nonfinite_time",
      "flag_negative_step",
      "flag_duplicate_time",
      "flag_nonmonotonic",
      "flag_short_segment"
    ),
    names(plot_data)
  )

  if (length(issue_cols) == 0) {
    plot_data$.any_time_issue <- FALSE
  } else {
    issue_data <- plot_data[issue_cols]
    issue_data[] <- lapply(issue_data, function(x) {
      x <- as.logical(x)
      x[is.na(x)] <- FALSE
      x
    })

    plot_data$.any_time_issue <- rowSums(issue_data) > 0
  }

  selected_groups <- unique(plot_data$.plot_group)

  if (length(selected_groups) > max_groups) {
    selected_groups <- selected_groups[seq_len(max_groups)]
    plot_data <- plot_data[plot_data$.plot_group %in% selected_groups, , drop = FALSE]
  }

  if (is.null(title)) {
    title <- "Gazepoint time/counter reset diagnostics"
  }

  p <- ggplot2::ggplot(
    plot_data,
    ggplot2::aes(x = .data$.plot_index, y = .data$time_value)
  ) +
    ggplot2::geom_line(ggplot2::aes(group = .data$.plot_group)) +
    ggplot2::geom_point(ggplot2::aes(shape = .data$.any_time_issue)) +
    ggplot2::facet_wrap(stats::as.formula("~ .plot_group"), scales = "free_x") +
    ggplot2::labs(
      title = title,
      subtitle = "QC summary only; time-order flags do not establish causal timing or physiological latency.",
      x = "Row index within group",
      y = "Time/counter value",
      shape = "Time issue"
    )

  settings <- list(
    plot_type = "time_resets",
    time_col = time_col,
    group_cols = group_cols,
    max_groups = max_groups,
    interpretation_notes = c(
      "Time-reset plots summarize time/counter ordering and reset flags.",
      "They support synchronization QC only and do not establish causal timing or true physiological latency."
    )
  )

  standardise_gazepoint_plot_contract(
    plot = p,
    plot_data = plot_data,
    settings = settings,
    interpretation_notes = settings$interpretation_notes,
    plot_type = "time_resets"
  )
}

#' Create a lightweight Gazepoint biometric QC plot dashboard
#'
#' Creates a lightweight dashboard object containing QC plots for signal activity
#' and time-reset diagnostics. This is a structured list of ggplot objects, not a
#' Shiny application. The dashboard is intended for report preparation and manual
#' QC review.
#'
#' @param data Optional Gazepoint biometric data frame.
#' @param signal_activity Optional result from
#'   [audit_gazepoint_signal_activity()].
#' @param time_resets Optional result from [audit_gazepoint_time_resets()].
#' @param signal_cols Optional signal columns used when computing signal
#'   activity from `data`.
#' @param group_cols Optional grouping columns.
#' @param time_col Optional time or counter column.
#' @param include_signal_activity If `TRUE`, include a signal-activity plot.
#' @param include_time_resets If `TRUE`, include a time-reset plot.
#' @param max_groups Maximum number of groups to display in each plot.
#' @param continue_on_error If `TRUE`, plot failures are recorded in `errors`
#'   rather than stopping the dashboard.
#' @param title_prefix Optional title prefix.
#'
#' @return A list with `overview`, `plots`, `errors`, `inputs`, and `settings`.
#' @export
plot_gazepoint_biometric_report_dashboard <- function(data = NULL,
                                                      signal_activity = NULL,
                                                      time_resets = NULL,
                                                      signal_cols = NULL,
                                                      group_cols = NULL,
                                                      time_col = NULL,
                                                      include_signal_activity = TRUE,
                                                      include_time_resets = TRUE,
                                                      max_groups = 30,
                                                      continue_on_error = TRUE,
                                                      title_prefix = "Gazepoint biometric QC") {
  gpbiometrics_require_ggplot2()

  if (!is.logical(include_signal_activity) ||
      length(include_signal_activity) != 1 ||
      is.na(include_signal_activity)) {
    stop("`include_signal_activity` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.logical(include_time_resets) ||
      length(include_time_resets) != 1 ||
      is.na(include_time_resets)) {
    stop("`include_time_resets` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.logical(continue_on_error) ||
      length(continue_on_error) != 1 ||
      is.na(continue_on_error)) {
    stop("`continue_on_error` must be TRUE or FALSE.", call. = FALSE)
  }

  if (is.null(data) && is.null(signal_activity) && is.null(time_resets)) {
    stop(
      "Supply `data`, `signal_activity`, `time_resets`, or a combination of these.",
      call. = FALSE
    )
  }

  plots <- list()
  errors <- data.frame(
    plot = character(),
    message = character(),
    stringsAsFactors = FALSE
  )

  if (isTRUE(include_signal_activity)) {
    signal_input <- if (!is.null(signal_activity)) signal_activity else data

    signal_result <- tryCatch(
      plot_gazepoint_signal_activity(
        data = signal_input,
        signal_cols = signal_cols,
        group_cols = group_cols,
        max_groups = max_groups,
        title = paste(title_prefix, "- signal activity")
      ),
      error = function(e) e
    )

    if (inherits(signal_result, "error")) {
      if (!isTRUE(continue_on_error)) {
        stop(conditionMessage(signal_result), call. = FALSE)
      }

      errors <- rbind(
        errors,
        data.frame(
          plot = "signal_activity",
          message = conditionMessage(signal_result),
          stringsAsFactors = FALSE
        )
      )
    } else {
      plots$signal_activity <- signal_result
    }
  }

  if (isTRUE(include_time_resets)) {
    time_input <- if (!is.null(time_resets)) time_resets else data

    time_result <- tryCatch(
      plot_gazepoint_time_resets(
        data = time_input,
        time_col = time_col,
        group_cols = group_cols,
        max_groups = max_groups,
        title = paste(title_prefix, "- time resets")
      ),
      error = function(e) e
    )

    if (inherits(time_result, "error")) {
      if (!isTRUE(continue_on_error)) {
        stop(conditionMessage(time_result), call. = FALSE)
      }

      errors <- rbind(
        errors,
        data.frame(
          plot = "time_resets",
          message = conditionMessage(time_result),
          stringsAsFactors = FALSE
        )
      )
    } else {
      plots$time_resets <- time_result
    }
  }

  plot_contract_ok <- vapply(
    plots,
    function(x) isTRUE(attr(x, "gazepoint_plot_contract")),
    logical(1)
  )

  status <- if (length(plots) == 0) {
    "no_plots_created"
  } else if (nrow(errors) > 0) {
    "partial_dashboard_created"
  } else {
    "dashboard_created"
  }

  overview <- data.frame(
    plot_count = length(plots),
    error_count = nrow(errors),
    all_plot_contracts_ok = if (length(plot_contract_ok) == 0) {
      NA
    } else {
      all(plot_contract_ok)
    },
    status = status,
    interpretation = paste(
      "Dashboard plots are lightweight QC aids for manual review and reporting.",
      "They do not infer emotion, valence, cognition, trust, preference, or physiological diagnosis."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      plots = plots,
      errors = errors,
      inputs = list(
        data_supplied = !is.null(data),
        signal_activity_supplied = !is.null(signal_activity),
        time_resets_supplied = !is.null(time_resets)
      ),
      settings = list(
        signal_cols = signal_cols,
        group_cols = group_cols,
        time_col = time_col,
        include_signal_activity = include_signal_activity,
        include_time_resets = include_time_resets,
        max_groups = max_groups,
        continue_on_error = continue_on_error,
        title_prefix = title_prefix
      )
    ),
    class = c("gazepoint_biometric_plot_dashboard", "list")
  )
}

gpbiometrics_qc_plot_extract_signal_activity <- function(data,
                                                         signal_cols = NULL,
                                                         group_cols = NULL) {
  if (is.list(data) && is.data.frame(data$signal_by_group)) {
    return(data)
  }

  if (!is.data.frame(data)) {
    stop(
      "`data` must be a data frame or an audit_gazepoint_signal_activity() result.",
      call. = FALSE
    )
  }

  audit_gazepoint_signal_activity(
    data = data,
    signal_cols = signal_cols,
    group_cols = group_cols
  )
}

gpbiometrics_qc_plot_extract_time_resets <- function(data,
                                                     time_col = NULL,
                                                     group_cols = NULL) {
  if (is.list(data) && is.data.frame(data$row_flags)) {
    return(data)
  }

  if (!is.data.frame(data)) {
    stop(
      "`data` must be a data frame or an audit_gazepoint_time_resets() result.",
      call. = FALSE
    )
  }

  audit_gazepoint_time_resets(
    data = data,
    time_col = time_col,
    group_cols = group_cols
  )
}

gpbiometrics_qc_plot_group_label <- function(dat) {
  if ("group_id" %in% names(dat)) {
    out <- as.character(dat$group_id)
    out[is.na(out) | !nzchar(out)] <- "all"
    return(out)
  }

  candidates <- intersect(
    c(
      "source_file",
      "source_participant",
      "participant",
      "subject",
      "subject_id",
      "USER",
      "USER_FILE",
      "MEDIA_ID",
      "MEDIA_NAME",
      "stimulus",
      "stimulus_id",
      "trial",
      "trial_id",
      "trial_global",
      "reset_segment_index"
    ),
    names(dat)
  )

  if (length(candidates) == 0) {
    return(rep("all", nrow(dat)))
  }

  group_dat <- dat[candidates]

  group_dat[] <- lapply(group_dat, function(x) {
    x_chr <- as.character(x)
    x_chr[is.na(x_chr)] <- "<NA>"
    x_chr
  })

  apply(group_dat, 1, paste, collapse = "||")
}

gpbiometrics_qc_plot_metric_to_numeric <- function(x) {
  if (is.logical(x)) {
    out <- as.numeric(x)
    out[is.na(out)] <- 0
    return(out)
  }

  if (is.character(x)) {
    lower_x <- tolower(x)
    if (all(lower_x %in% c("true", "false", "active", "inactive", "pass", "fail", NA))) {
      return(as.numeric(lower_x %in% c("true", "active", "pass")))
    }
  }

  suppressWarnings(as.numeric(x))
}

gpbiometrics_qc_plot_ensure_activity_metrics <- function(plot_data) {
  plot_data <- as.data.frame(plot_data, stringsAsFactors = FALSE)

  if (!"missing_prop" %in% names(plot_data) && all(c("n_missing", "n") %in% names(plot_data))) {
    n <- suppressWarnings(as.numeric(plot_data$n))
    n_missing <- suppressWarnings(as.numeric(plot_data$n_missing))
    plot_data$missing_prop <- ifelse(is.finite(n) & n > 0, n_missing / n, NA_real_)
  }

  if (!"nonzero_prop" %in% names(plot_data) && all(c("n_nonzero", "n") %in% names(plot_data))) {
    n <- suppressWarnings(as.numeric(plot_data$n))
    n_nonzero <- suppressWarnings(as.numeric(plot_data$n_nonzero))
    plot_data$nonzero_prop <- ifelse(is.finite(n) & n > 0, n_nonzero / n, NA_real_)
  }

  if (!"active_signal" %in% names(plot_data)) {
    if ("is_active" %in% names(plot_data)) {
      plot_data$active_signal <- as.logical(plot_data$is_active)
    } else if ("active" %in% names(plot_data)) {
      plot_data$active_signal <- as.logical(plot_data$active)
    } else if ("status" %in% names(plot_data)) {
      status <- tolower(as.character(plot_data$status))
      plot_data$active_signal <- !grepl(
        "inactive|insufficient|missing|flat|constant|unavailable|fail",
        status
      )
      plot_data$active_signal[is.na(status)] <- FALSE
    } else if ("signal_status" %in% names(plot_data)) {
      status <- tolower(as.character(plot_data$signal_status))
      plot_data$active_signal <- !grepl(
        "inactive|insufficient|missing|flat|constant|unavailable|fail",
        status
      )
      plot_data$active_signal[is.na(status)] <- FALSE
    } else if ("n_unique_nonzero" %in% names(plot_data)) {
      n_unique_nonzero <- suppressWarnings(as.numeric(plot_data$n_unique_nonzero))
      plot_data$active_signal <- is.finite(n_unique_nonzero) & n_unique_nonzero >= 2
    } else if ("n_unique_finite" %in% names(plot_data)) {
      n_unique_finite <- suppressWarnings(as.numeric(plot_data$n_unique_finite))
      plot_data$active_signal <- is.finite(n_unique_finite) & n_unique_finite >= 2
    } else if ("nonzero_prop" %in% names(plot_data)) {
      nonzero_prop <- suppressWarnings(as.numeric(plot_data$nonzero_prop))
      plot_data$active_signal <- is.finite(nonzero_prop) & nonzero_prop > 0
    } else {
      plot_data$active_signal <- FALSE
    }
  }

  plot_data$active_signal[is.na(plot_data$active_signal)] <- FALSE

  plot_data
}
