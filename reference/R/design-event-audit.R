utils::globalVariables(c(
  "condition", "participant", "trial", "event", "n", "plot_y",
  "n_trials", "n_participants", "n_units", "coverage_prop",
  "complete", "issue", "severity"
))

#' Audit Gazepoint experiment design structure
#'
#' Check whether an imported or prepared Gazepoint workflow table contains the
#' expected participant, trial, condition, and optional session structure before
#' modelling, event-locking, or time-course analysis.
#'
#' @param data A data frame containing trial-, event-, or sample-level records.
#' @param participant_col Name of the participant identifier column.
#' @param trial_col Optional name of the trial identifier column.
#' @param condition_col Optional name of the condition column.
#' @param session_col Optional name of the session/block column.
#' @param expected_conditions Optional character vector of expected conditions.
#' @param min_trials_per_condition Minimum acceptable number of trials per
#'   participant-condition cell when `trial_col` and `condition_col` are supplied.
#'
#' @return A list with class `"gazepoint_experiment_design_audit"`.
#'
#' @examples
#' dat <- data.frame(
#'   participant = rep(paste0("P", 1:4), each = 4),
#'   trial = rep(1:4, times = 4),
#'   condition = rep(c("A", "B"), times = 8)
#' )
#'
#' audit_gazepoint_experiment_design(
#'   dat,
#'   participant_col = "participant",
#'   trial_col = "trial",
#'   condition_col = "condition",
#'   expected_conditions = c("A", "B")
#' )
#'
#' @export
audit_gazepoint_experiment_design <- function(data,
                                              participant_col,
                                              trial_col = NULL,
                                              condition_col = NULL,
                                              session_col = NULL,
                                              expected_conditions = NULL,
                                              min_trials_per_condition = 1L) {
  .gp_dea_assert_data_frame(data)
  participant_col <- .gp_dea_required_column(data, participant_col, "participant_col")
  trial_col <- .gp_dea_optional_column(data, trial_col, "trial_col")
  condition_col <- .gp_dea_optional_column(data, condition_col, "condition_col")
  session_col <- .gp_dea_optional_column(data, session_col, "session_col")

  if (!is.numeric(min_trials_per_condition) ||
      length(min_trials_per_condition) != 1L ||
      is.na(min_trials_per_condition) ||
      min_trials_per_condition < 0) {
    stop("`min_trials_per_condition` must be a non-negative number.", call. = FALSE)
  }

  expected_conditions <- .gp_dea_optional_vector(expected_conditions, "expected_conditions")

  participants <- as.character(data[[participant_col]])
  conditions <- if (!is.null(condition_col)) {
    as.character(data[[condition_col]])
  } else {
    rep(NA_character_, NROW(data))
  }

  trials <- if (!is.null(trial_col)) {
    as.character(data[[trial_col]])
  } else {
    as.character(seq_len(NROW(data)))
  }

  sessions <- if (!is.null(session_col)) {
    as.character(data[[session_col]])
  } else {
    rep(NA_character_, NROW(data))
  }

  unit_data <- data.frame(
    participant = participants,
    trial = trials,
    condition = conditions,
    session = sessions,
    stringsAsFactors = FALSE
  )

  unit_data <- unique(unit_data)

  participant_summary <- .gp_dea_participant_summary(unit_data, condition_col, session_col)
  condition_summary <- .gp_dea_condition_summary(unit_data, condition_col)

  participant_condition_counts <- .gp_dea_participant_condition_counts(
    unit_data,
    condition_col = condition_col,
    expected_conditions = expected_conditions
  )

  overview <- data.frame(
    n_rows = NROW(data),
    n_participants = length(unique(stats::na.omit(participants))),
    n_trials = length(unique(stats::na.omit(trials))),
    n_unique_participant_trials = NROW(unique(unit_data[, c("participant", "trial"), drop = FALSE])),
    n_conditions = if (!is.null(condition_col)) {
      length(unique(stats::na.omit(conditions)))
    } else {
      NA_integer_
    },
    n_sessions = if (!is.null(session_col)) {
      length(unique(stats::na.omit(sessions)))
    } else {
      NA_integer_
    },
    has_trial_column = !is.null(trial_col),
    has_condition_column = !is.null(condition_col),
    has_session_column = !is.null(session_col),
    stringsAsFactors = FALSE
  )

  warnings <- .gp_dea_design_warnings(
    overview = overview,
    participant_condition_counts = participant_condition_counts,
    condition_summary = condition_summary,
    expected_conditions = expected_conditions,
    min_trials_per_condition = min_trials_per_condition,
    has_condition = !is.null(condition_col),
    has_trial = !is.null(trial_col)
  )

  settings <- data.frame(
    participant_col = participant_col,
    trial_col = .gp_dea_null_to_na(trial_col),
    condition_col = .gp_dea_null_to_na(condition_col),
    session_col = .gp_dea_null_to_na(session_col),
    expected_conditions = .gp_dea_collapse(expected_conditions),
    min_trials_per_condition = min_trials_per_condition,
    stringsAsFactors = FALSE
  )

  out <- list(
    overview = overview,
    participant_summary = participant_summary,
    condition_summary = condition_summary,
    participant_condition_counts = participant_condition_counts,
    warnings = warnings,
    settings = settings
  )

  class(out) <- "gazepoint_experiment_design_audit"
  out
}

#' Audit Gazepoint event coverage
#'
#' Check whether expected events, TTL markers, AOI events, or task events are
#' present across participant/trial/condition units.
#'
#' @param data A data frame containing event-, trial-, or sample-level records.
#' @param event_col Name of the event/marker column.
#' @param participant_col Optional participant identifier column.
#' @param trial_col Optional trial identifier column.
#' @param condition_col Optional condition column.
#' @param expected_events Optional character vector of expected event labels.
#' @param unit_cols Optional character vector of columns defining event-coverage
#'   units. If supplied, this overrides `participant_col`, `trial_col`, and
#'   `condition_col` for unit construction.
#'
#' @return A list with class `"gazepoint_event_coverage_audit"`.
#'
#' @export
audit_gazepoint_event_coverage <- function(data,
                                           event_col,
                                           participant_col = NULL,
                                           trial_col = NULL,
                                           condition_col = NULL,
                                           expected_events = NULL,
                                           unit_cols = NULL) {
  .gp_dea_assert_data_frame(data)
  event_col <- .gp_dea_required_column(data, event_col, "event_col")
  participant_col <- .gp_dea_optional_column(data, participant_col, "participant_col")
  trial_col <- .gp_dea_optional_column(data, trial_col, "trial_col")
  condition_col <- .gp_dea_optional_column(data, condition_col, "condition_col")

  if (!is.null(unit_cols)) {
    if (!is.character(unit_cols) || length(unit_cols) == 0L) {
      stop("`unit_cols` must be NULL or a non-empty character vector.", call. = FALSE)
    }

    missing_cols <- setdiff(unit_cols, names(data))
    if (length(missing_cols) > 0L) {
      stop(
        "`unit_cols` contains missing column(s): ",
        paste(missing_cols, collapse = ", "),
        call. = FALSE
      )
    }
  }

  expected_events <- .gp_dea_optional_vector(expected_events, "expected_events")

  if (is.null(expected_events)) {
    expected_events <- sort(unique(as.character(stats::na.omit(data[[event_col]]))))
  }

  if (length(expected_events) == 0L) {
    expected_events <- character(0)
  }

  if (is.null(unit_cols)) {
    unit_cols <- c(participant_col, trial_col, condition_col)
    unit_cols <- unit_cols[!vapply(unit_cols, is.null, logical(1))]
  }

  if (length(unit_cols) == 0L) {
    unit_table <- data.frame(
      unit_id = "all_rows",
      stringsAsFactors = FALSE
    )
    event_source <- data.frame(
      unit_id = rep("all_rows", NROW(data)),
      event = as.character(data[[event_col]]),
      stringsAsFactors = FALSE
    )
  } else {
    unit_table <- unique(data[, unit_cols, drop = FALSE])
    unit_table$unit_id <- .gp_dea_make_unit_id(unit_table, unit_cols)

    event_source <- data[, c(unit_cols, event_col), drop = FALSE]
    event_source$unit_id <- .gp_dea_make_unit_id(event_source, unit_cols)
    event_source$event <- as.character(event_source[[event_col]])
  }

  unit_ids <- unique(unit_table$unit_id)

  coverage_rows <- lapply(unit_ids, function(unit_id) {
    present_events <- unique(stats::na.omit(event_source$event[event_source$unit_id == unit_id]))

    data.frame(
      unit_id = unit_id,
      event = expected_events,
      present = expected_events %in% present_events,
      stringsAsFactors = FALSE
    )
  })

  coverage <- if (length(coverage_rows) == 0L) {
    data.frame(
      unit_id = character(0),
      event = character(0),
      present = logical(0),
      stringsAsFactors = FALSE
    )
  } else {
    do.call(rbind, coverage_rows)
  }

  event_summary <- if (NROW(coverage) == 0L) {
    data.frame(
      event = expected_events,
      n_units_present = integer(length(expected_events)),
      n_units_total = length(unit_ids),
      coverage_prop = numeric(length(expected_events)),
      stringsAsFactors = FALSE
    )
  } else {
    out <- stats::aggregate(
      present ~ event,
      data = coverage,
      FUN = sum
    )
    names(out) <- c("event", "n_units_present")
    out$n_units_total <- length(unit_ids)
    out$coverage_prop <- if (length(unit_ids) > 0L) {
      out$n_units_present / length(unit_ids)
    } else {
      NA_real_
    }
    out[order(out$event), , drop = FALSE]
  }

  unit_summary <- if (NROW(coverage) == 0L) {
    data.frame(
      unit_id = unit_ids,
      n_events_present = integer(length(unit_ids)),
      n_events_expected = length(expected_events),
      complete = logical(length(unit_ids)),
      stringsAsFactors = FALSE
    )
  } else {
    out <- stats::aggregate(
      present ~ unit_id,
      data = coverage,
      FUN = sum
    )
    names(out) <- c("unit_id", "n_events_present")
    out$n_events_expected <- length(expected_events)
    out$complete <- out$n_events_present >= out$n_events_expected
    out[order(out$unit_id), , drop = FALSE]
  }

  overview <- data.frame(
    n_rows = NROW(data),
    n_units = length(unit_ids),
    n_expected_events = length(expected_events),
    n_events_observed = length(unique(stats::na.omit(as.character(data[[event_col]])))),
    n_complete_units = sum(unit_summary$complete, na.rm = TRUE),
    complete_unit_prop = if (length(unit_ids) > 0L) {
      sum(unit_summary$complete, na.rm = TRUE) / length(unit_ids)
    } else {
      NA_real_
    },
    stringsAsFactors = FALSE
  )

  warnings <- .gp_dea_event_warnings(
    overview = overview,
    event_summary = event_summary,
    unit_summary = unit_summary
  )

  settings <- data.frame(
    event_col = event_col,
    participant_col = .gp_dea_null_to_na(participant_col),
    trial_col = .gp_dea_null_to_na(trial_col),
    condition_col = .gp_dea_null_to_na(condition_col),
    unit_cols = .gp_dea_collapse(unit_cols),
    expected_events = .gp_dea_collapse(expected_events),
    stringsAsFactors = FALSE
  )

  out <- list(
    overview = overview,
    event_summary = event_summary,
    unit_summary = unit_summary,
    coverage = coverage,
    warnings = warnings,
    settings = settings
  )

  class(out) <- "gazepoint_event_coverage_audit"
  out
}

#' Audit Gazepoint condition balance
#'
#' Summarise condition balance across participants and trials before modelling,
#' event-window summaries, or two-condition time-course workflows.
#'
#' @param data A data frame containing trial-, event-, or sample-level records.
#' @param participant_col Name of the participant identifier column.
#' @param condition_col Name of the condition column.
#' @param trial_col Optional trial identifier column.
#' @param expected_conditions Optional character vector of expected conditions.
#'
#' @return A list with class `"gazepoint_condition_balance_audit"`.
#'
#' @export
audit_gazepoint_condition_balance <- function(data,
                                              participant_col,
                                              condition_col,
                                              trial_col = NULL,
                                              expected_conditions = NULL) {
  .gp_dea_assert_data_frame(data)
  participant_col <- .gp_dea_required_column(data, participant_col, "participant_col")
  condition_col <- .gp_dea_required_column(data, condition_col, "condition_col")
  trial_col <- .gp_dea_optional_column(data, trial_col, "trial_col")
  expected_conditions <- .gp_dea_optional_vector(expected_conditions, "expected_conditions")

  if (is.null(expected_conditions)) {
    expected_conditions <- sort(unique(as.character(stats::na.omit(data[[condition_col]]))))
  }

  trial_id <- if (!is.null(trial_col)) {
    as.character(data[[trial_col]])
  } else {
    as.character(seq_len(NROW(data)))
  }

  unit_data <- unique(data.frame(
    participant = as.character(data[[participant_col]]),
    condition = as.character(data[[condition_col]]),
    trial = trial_id,
    stringsAsFactors = FALSE
  ))

  participant_condition_counts <- .gp_dea_participant_condition_counts(
    unit_data,
    condition_col = condition_col,
    expected_conditions = expected_conditions
  )

  condition_counts <- stats::aggregate(
    trial ~ condition,
    data = unit_data,
    FUN = length
  )
  names(condition_counts) <- c("condition", "n_trials")

  participant_counts <- stats::aggregate(
    participant ~ condition,
    data = unique(unit_data[, c("participant", "condition"), drop = FALSE]),
    FUN = length
  )
  names(participant_counts) <- c("condition", "n_participants")

  condition_summary <- merge(
    condition_counts,
    participant_counts,
    by = "condition",
    all = TRUE
  )

  condition_summary$n_trials[is.na(condition_summary$n_trials)] <- 0L
  condition_summary$n_participants[is.na(condition_summary$n_participants)] <- 0L
  condition_summary <- condition_summary[order(condition_summary$condition), , drop = FALSE]

  min_trials <- min(condition_summary$n_trials, na.rm = TRUE)
  max_trials <- max(condition_summary$n_trials, na.rm = TRUE)

  overview <- data.frame(
    n_participants = length(unique(stats::na.omit(unit_data$participant))),
    n_conditions = length(unique(stats::na.omit(unit_data$condition))),
    n_trials = NROW(unit_data),
    min_trials_per_condition = min_trials,
    max_trials_per_condition = max_trials,
    trial_imbalance_ratio = if (min_trials > 0) max_trials / min_trials else Inf,
    complete_participant_condition_grid = all(
      participant_condition_counts$n_trials > 0
    ),
    stringsAsFactors = FALSE
  )

  warnings <- .gp_dea_balance_warnings(
    overview = overview,
    participant_condition_counts = participant_condition_counts,
    condition_summary = condition_summary,
    expected_conditions = expected_conditions
  )

  settings <- data.frame(
    participant_col = participant_col,
    condition_col = condition_col,
    trial_col = .gp_dea_null_to_na(trial_col),
    expected_conditions = .gp_dea_collapse(expected_conditions),
    stringsAsFactors = FALSE
  )

  out <- list(
    overview = overview,
    condition_summary = condition_summary,
    participant_condition_counts = participant_condition_counts,
    warnings = warnings,
    settings = settings
  )

  class(out) <- "gazepoint_condition_balance_audit"
  out
}

#' Plot Gazepoint design and event-coverage audits
#'
#' Create compact diagnostic plots from design, condition-balance, or
#' event-coverage audit objects.
#'
#' @param audit Object returned by `audit_gazepoint_experiment_design()`,
#'   `audit_gazepoint_event_coverage()`, or
#'   `audit_gazepoint_condition_balance()`.
#' @param type Plot type. Supported values depend on the audit object:
#'   `"condition_counts"`, `"participant_trials"`, `"event_coverage"`,
#'   and `"warnings"`.
#'
#' @return A `ggplot` object.
#'
#' @export
plot_gazepoint_design_coverage <- function(audit,
                                           type = c(
                                             "condition_counts",
                                             "participant_trials",
                                             "event_coverage",
                                             "warnings"
                                           )) {
  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    stop("Package `ggplot2` is required for plotting.", call. = FALSE)
  }

  type <- match.arg(type)

  if (type == "condition_counts") {
    if (!inherits(audit, "gazepoint_experiment_design_audit") &&
        !inherits(audit, "gazepoint_condition_balance_audit")) {
      stop(
        "`condition_counts` requires a design or condition-balance audit.",
        call. = FALSE
      )
    }

    df <- audit$condition_summary

    if (NROW(df) == 0L || !"condition" %in% names(df)) {
      stop("No condition summary is available to plot.", call. = FALSE)
    }

    y_col <- if ("n_trials" %in% names(df)) "n_trials" else "n_units"
    df$plot_y <- df[[y_col]]

    return(
      ggplot2::ggplot(df, ggplot2::aes(x = condition, y = plot_y)) +
        ggplot2::geom_col() +
        ggplot2::labs(
          x = "Condition",
          y = "Number of trials or units",
          title = "Gazepoint condition coverage"
        ) +
        ggplot2::theme_minimal()
    )
  }

  if (type == "participant_trials") {
    if (!inherits(audit, "gazepoint_experiment_design_audit") &&
        !inherits(audit, "gazepoint_condition_balance_audit")) {
      stop(
        "`participant_trials` requires a design or condition-balance audit.",
        call. = FALSE
      )
    }

    df <- audit$participant_condition_counts

    if (NROW(df) == 0L) {
      stop("No participant-condition summary is available to plot.", call. = FALSE)
    }

    return(
      ggplot2::ggplot(df, ggplot2::aes(
        x = participant,
        y = n_trials,
        fill = condition
      )) +
        ggplot2::geom_col(position = "dodge") +
        ggplot2::coord_flip() +
        ggplot2::labs(
          x = "Participant",
          y = "Number of trials",
          fill = "Condition",
          title = "Participant-level condition balance"
        ) +
        ggplot2::theme_minimal()
    )
  }

  if (type == "event_coverage") {
    if (!inherits(audit, "gazepoint_event_coverage_audit")) {
      stop("`event_coverage` requires an event-coverage audit.", call. = FALSE)
    }

    df <- audit$event_summary

    if (NROW(df) == 0L) {
      stop("No event summary is available to plot.", call. = FALSE)
    }

    return(
      ggplot2::ggplot(df, ggplot2::aes(x = event, y = coverage_prop)) +
        ggplot2::geom_col() +
        ggplot2::coord_flip() +
        ggplot2::labs(
          x = "Event",
          y = "Coverage proportion",
          title = "Gazepoint event coverage"
        ) +
        ggplot2::ylim(0, 1) +
        ggplot2::theme_minimal()
    )
  }

  warnings <- audit$warnings

  if (is.null(warnings) || NROW(warnings) == 0L) {
    warnings <- data.frame(
      severity = "none",
      issue = "no_warnings",
      message = "No warnings recorded.",
      stringsAsFactors = FALSE
    )
  }

  df <- as.data.frame(table(warnings$severity), stringsAsFactors = FALSE)
  names(df) <- c("severity", "n")

  ggplot2::ggplot(df, ggplot2::aes(x = severity, y = n)) +
    ggplot2::geom_col() +
    ggplot2::labs(
      x = "Severity",
      y = "Number of warnings",
      title = "Gazepoint audit warning summary"
    ) +
    ggplot2::theme_minimal()
}

#' @export
print.gazepoint_experiment_design_audit <- function(x, ...) {
  cat("Gazepoint experiment design audit\n")
  cat("---------------------------------\n")
  print(x$overview, row.names = FALSE)

  if (NROW(x$warnings) > 0L) {
    cat("\nWarnings\n")
    print(x$warnings, row.names = FALSE)
  } else {
    cat("\nNo design warnings detected.\n")
  }

  invisible(x)
}

#' @export
print.gazepoint_event_coverage_audit <- function(x, ...) {
  cat("Gazepoint event coverage audit\n")
  cat("------------------------------\n")
  print(x$overview, row.names = FALSE)

  if (NROW(x$warnings) > 0L) {
    cat("\nWarnings\n")
    print(x$warnings, row.names = FALSE)
  } else {
    cat("\nNo event-coverage warnings detected.\n")
  }

  invisible(x)
}

#' @export
print.gazepoint_condition_balance_audit <- function(x, ...) {
  cat("Gazepoint condition balance audit\n")
  cat("---------------------------------\n")
  print(x$overview, row.names = FALSE)

  if (NROW(x$warnings) > 0L) {
    cat("\nWarnings\n")
    print(x$warnings, row.names = FALSE)
  } else {
    cat("\nNo condition-balance warnings detected.\n")
  }

  invisible(x)
}

.gp_dea_assert_data_frame <- function(data) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (NROW(data) == 0L) {
    stop("`data` must contain at least one row.", call. = FALSE)
  }

  invisible(TRUE)
}

.gp_dea_required_column <- function(data, col, name) {
  if (!is.character(col) || length(col) != 1L || is.na(col) || !nzchar(col)) {
    stop("`", name, "` must be a non-empty column name.", call. = FALSE)
  }

  if (!col %in% names(data)) {
    stop("`", name, "` was not found in `data`: ", col, call. = FALSE)
  }

  col
}

.gp_dea_optional_column <- function(data, col, name) {
  if (is.null(col)) {
    return(NULL)
  }

  .gp_dea_required_column(data, col, name)
}

.gp_dea_optional_vector <- function(x, name) {
  if (is.null(x)) {
    return(NULL)
  }

  if (!is.character(x) || length(x) == 0L || any(is.na(x)) || any(!nzchar(x))) {
    stop("`", name, "` must be NULL or a non-empty character vector.", call. = FALSE)
  }

  unique(as.character(x))
}

.gp_dea_participant_summary <- function(unit_data, condition_col, session_col) {
  participant_summary <- stats::aggregate(
    trial ~ participant,
    data = unit_data,
    FUN = length
  )
  names(participant_summary) <- c("participant", "n_trials")

  if (!is.null(condition_col)) {
    condition_counts <- stats::aggregate(
      condition ~ participant,
      data = unique(unit_data[, c("participant", "condition"), drop = FALSE]),
      FUN = length
    )
    names(condition_counts) <- c("participant", "n_conditions")
    participant_summary <- merge(participant_summary, condition_counts, by = "participant", all.x = TRUE)
  } else {
    participant_summary$n_conditions <- NA_integer_
  }

  if (!is.null(session_col)) {
    session_counts <- stats::aggregate(
      session ~ participant,
      data = unique(unit_data[, c("participant", "session"), drop = FALSE]),
      FUN = length
    )
    names(session_counts) <- c("participant", "n_sessions")
    participant_summary <- merge(participant_summary, session_counts, by = "participant", all.x = TRUE)
  } else {
    participant_summary$n_sessions <- NA_integer_
  }

  participant_summary[order(participant_summary$participant), , drop = FALSE]
}

.gp_dea_condition_summary <- function(unit_data, condition_col) {
  if (is.null(condition_col)) {
    return(data.frame(
      condition = character(0),
      n_trials = integer(0),
      n_participants = integer(0),
      stringsAsFactors = FALSE
    ))
  }

  condition_counts <- stats::aggregate(
    trial ~ condition,
    data = unit_data,
    FUN = length
  )
  names(condition_counts) <- c("condition", "n_trials")

  participant_counts <- stats::aggregate(
    participant ~ condition,
    data = unique(unit_data[, c("participant", "condition"), drop = FALSE]),
    FUN = length
  )
  names(participant_counts) <- c("condition", "n_participants")

  out <- merge(condition_counts, participant_counts, by = "condition", all = TRUE)
  out[order(out$condition), , drop = FALSE]
}

.gp_dea_participant_condition_counts <- function(unit_data,
                                                 condition_col,
                                                 expected_conditions) {
  if (is.null(condition_col)) {
    return(data.frame(
      participant = unique(unit_data$participant),
      condition = NA_character_,
      n_trials = NA_integer_,
      stringsAsFactors = FALSE
    ))
  }

  participants <- sort(unique(stats::na.omit(unit_data$participant)))

  if (is.null(expected_conditions)) {
    expected_conditions <- sort(unique(stats::na.omit(unit_data$condition)))
  }

  grid <- expand.grid(
    participant = participants,
    condition = expected_conditions,
    stringsAsFactors = FALSE
  )

  counts <- stats::aggregate(
    trial ~ participant + condition,
    data = unit_data,
    FUN = length
  )
  names(counts) <- c("participant", "condition", "n_trials")

  out <- merge(grid, counts, by = c("participant", "condition"), all.x = TRUE)
  out$n_trials[is.na(out$n_trials)] <- 0L
  out[order(out$participant, out$condition), , drop = FALSE]
}

.gp_dea_design_warnings <- function(overview,
                                    participant_condition_counts,
                                    condition_summary,
                                    expected_conditions,
                                    min_trials_per_condition,
                                    has_condition,
                                    has_trial) {
  out <- list()

  if (!has_trial) {
    out[[length(out) + 1L]] <- .gp_dea_warning(
      "info",
      "no_trial_column",
      "No trial column was supplied; row index was used as a trial proxy."
    )
  }

  if (!has_condition) {
    out[[length(out) + 1L]] <- .gp_dea_warning(
      "info",
      "no_condition_column",
      "No condition column was supplied; condition-balance checks were skipped."
    )
  }

  if (has_condition && !is.null(expected_conditions)) {
    observed <- condition_summary$condition
    missing_conditions <- setdiff(expected_conditions, observed)

    if (length(missing_conditions) > 0L) {
      out[[length(out) + 1L]] <- .gp_dea_warning(
        "warning",
        "missing_expected_conditions",
        paste0(
          "Expected condition(s) not observed: ",
          paste(missing_conditions, collapse = ", "),
          "."
        )
      )
    }
  }

  if (has_condition && has_trial && NROW(participant_condition_counts) > 0L) {
    low_cells <- participant_condition_counts$n_trials < min_trials_per_condition

    if (any(low_cells, na.rm = TRUE)) {
      out[[length(out) + 1L]] <- .gp_dea_warning(
        "warning",
        "low_participant_condition_cells",
        paste0(
          sum(low_cells, na.rm = TRUE),
          " participant-condition cell(s) had fewer than ",
          min_trials_per_condition,
          " trial(s)."
        )
      )
    }
  }

  .gp_dea_bind_warnings(out)
}

.gp_dea_event_warnings <- function(overview, event_summary, unit_summary) {
  out <- list()

  if (overview$n_expected_events == 0L) {
    out[[length(out) + 1L]] <- .gp_dea_warning(
      "warning",
      "no_expected_events",
      "No expected events were supplied or detected."
    )
  }

  if (NROW(event_summary) > 0L) {
    missing_events <- event_summary$event[event_summary$n_units_present == 0L]

    if (length(missing_events) > 0L) {
      out[[length(out) + 1L]] <- .gp_dea_warning(
        "warning",
        "events_never_observed",
        paste0(
          "Expected event(s) were never observed: ",
          paste(missing_events, collapse = ", "),
          "."
        )
      )
    }

    partial_events <- event_summary$event[
      event_summary$n_units_present > 0L &
        event_summary$n_units_present < event_summary$n_units_total
    ]

    if (length(partial_events) > 0L) {
      out[[length(out) + 1L]] <- .gp_dea_warning(
        "info",
        "partial_event_coverage",
        paste0(
          "Event(s) had incomplete unit coverage: ",
          paste(partial_events, collapse = ", "),
          "."
        )
      )
    }
  }

  if (NROW(unit_summary) > 0L) {
    incomplete_units <- sum(!unit_summary$complete, na.rm = TRUE)

    if (incomplete_units > 0L) {
      out[[length(out) + 1L]] <- .gp_dea_warning(
        "warning",
        "incomplete_event_units",
        paste0(
          incomplete_units,
          " unit(s) did not contain all expected events."
        )
      )
    }
  }

  .gp_dea_bind_warnings(out)
}

.gp_dea_balance_warnings <- function(overview,
                                     participant_condition_counts,
                                     condition_summary,
                                     expected_conditions) {
  out <- list()

  missing_conditions <- setdiff(expected_conditions, condition_summary$condition)

  if (length(missing_conditions) > 0L) {
    out[[length(out) + 1L]] <- .gp_dea_warning(
      "warning",
      "missing_expected_conditions",
      paste0(
        "Expected condition(s) not observed: ",
        paste(missing_conditions, collapse = ", "),
        "."
      )
    )
  }

  missing_cells <- participant_condition_counts$n_trials == 0L

  if (any(missing_cells, na.rm = TRUE)) {
    out[[length(out) + 1L]] <- .gp_dea_warning(
      "warning",
      "missing_participant_condition_cells",
      paste0(
        sum(missing_cells, na.rm = TRUE),
        " participant-condition cell(s) had zero trials."
      )
    )
  }

  if (is.finite(overview$trial_imbalance_ratio) &&
      overview$trial_imbalance_ratio > 2) {
    out[[length(out) + 1L]] <- .gp_dea_warning(
      "info",
      "condition_trial_imbalance",
      paste0(
        "The largest condition contained more than twice the trials of ",
        "the smallest condition."
      )
    )
  }

  if (!isTRUE(overview$complete_participant_condition_grid)) {
    out[[length(out) + 1L]] <- .gp_dea_warning(
      "warning",
      "incomplete_participant_condition_grid",
      "Not every participant has at least one trial in every expected condition."
    )
  }

  .gp_dea_bind_warnings(out)
}

.gp_dea_warning <- function(severity, issue, message) {
  data.frame(
    severity = severity,
    issue = issue,
    message = message,
    stringsAsFactors = FALSE
  )
}

.gp_dea_bind_warnings <- function(x) {
  if (length(x) == 0L) {
    return(data.frame(
      severity = character(0),
      issue = character(0),
      message = character(0),
      stringsAsFactors = FALSE
    ))
  }

  do.call(rbind, x)
}

.gp_dea_make_unit_id <- function(data, cols) {
  if (length(cols) == 0L) {
    return(rep("all_rows", NROW(data)))
  }

  vals <- data[, cols, drop = FALSE]
  vals[] <- lapply(vals, function(x) {
    x <- as.character(x)
    x[is.na(x)] <- "(missing)"
    x
  })

  apply(vals, 1L, paste, collapse = " | ")
}

.gp_dea_null_to_na <- function(x) {
  if (is.null(x)) NA_character_ else as.character(x)
}

.gp_dea_collapse <- function(x) {
  if (is.null(x) || length(x) == 0L) {
    return(NA_character_)
  }

  paste(as.character(x), collapse = "; ")
}
