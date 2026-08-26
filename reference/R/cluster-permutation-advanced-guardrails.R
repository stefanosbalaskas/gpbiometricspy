# Advanced cluster-permutation guardrails and interoperability helpers

.gp_ac_stop_unsupported <- function(function_name, reason, alternative = NULL) {
  message <- paste0(
    "`", function_name, "()` is not implemented as a runnable inferential ",
    "engine in gpbiometrics yet.\n\n",
    reason,
    "\n\nThe current validated scope is the conservative within-subject, ",
    "two-condition, one-dimensional time-course workflow implemented in ",
    "`run_gazepoint_cluster_permutation()`."
  )

  if (!is.null(alternative)) {
    message <- paste0(message, "\n\nRecommended alternative: ", alternative)
  }

  stop(message, call. = FALSE)
}

.gp_ac_col_name <- function(expr, env) {
  if (is.character(expr) && length(expr) == 1L) {
    return(expr)
  }

  if (is.name(expr)) {
    nm <- as.character(expr)

    if (exists(nm, envir = env, inherits = FALSE)) {
      val <- get(nm, envir = env, inherits = FALSE)
      if (is.character(val) && length(val) == 1L) {
        return(val)
      }
    }

    return(nm)
  }

  if (is.call(expr) && identical(expr[[1L]], as.name("$"))) {
    return(as.character(expr[[3L]]))
  }

  stop(
    "Column arguments must be bare column names or single character strings.",
    call. = FALSE
  )
}

.gp_ac_check_data <- function(data, columns) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (nrow(data) == 0L) {
    stop("`data` must contain at least one row.", call. = FALSE)
  }

  missing <- setdiff(columns, names(data))

  if (length(missing) > 0L) {
    stop(
      "Missing required column(s): ",
      paste(missing, collapse = ", "),
      call. = FALSE
    )
  }

  invisible(TRUE)
}

.gp_ac_prepare_long_timecourse <- function(data,
                                           outcome_col,
                                           time_col,
                                           condition_col,
                                           participant_col,
                                           aggregate = TRUE) {
  .gp_ac_check_data(
    data,
    c(outcome_col, time_col, condition_col, participant_col)
  )

  out <- data.frame(
    participant = as.character(data[[participant_col]]),
    condition = as.character(data[[condition_col]]),
    time = data[[time_col]],
    value = suppressWarnings(as.numeric(data[[outcome_col]])),
    stringsAsFactors = FALSE
  )

  if (anyNA(out$participant)) {
    stop("`participant_col` contains missing values.", call. = FALSE)
  }

  if (anyNA(out$condition)) {
    stop("`condition_col` contains missing values.", call. = FALSE)
  }

  if (anyNA(out$time)) {
    stop("`time_col` contains missing values.", call. = FALSE)
  }

  if (anyNA(out$value)) {
    stop("`outcome_col` must be numeric and contain no missing values.", call. = FALSE)
  }

  if (isTRUE(aggregate)) {
    out <- stats::aggregate(
      value ~ participant + condition + time,
      data = out,
      FUN = mean
    )
  }

  out <- out[order(out$participant, out$condition, out$time), ]
  rownames(out) <- NULL
  out
}

.gp_ac_write_outputs <- function(outputs, path, prefix, overwrite) {
  if (is.null(path)) {
    return(invisible(outputs))
  }

  if (!dir.exists(path)) {
    dir.create(path, recursive = TRUE, showWarnings = FALSE)
  }

  if (!dir.exists(path)) {
    stop("Could not create output directory: ", path, call. = FALSE)
  }

  files <- file.path(path, paste0(prefix, "_", names(outputs), ".csv"))

  if (!isTRUE(overwrite)) {
    existing <- files[file.exists(files)]

    if (length(existing) > 0L) {
      stop(
        "Refusing to overwrite existing file(s): ",
        paste(existing, collapse = ", "),
        ". Set `overwrite = TRUE` to replace them.",
        call. = FALSE
      )
    }
  }

  for (i in seq_along(outputs)) {
    utils::write.csv(outputs[[i]], files[[i]], row.names = FALSE)
  }

  invisible(data.frame(
    component = names(outputs),
    file = files,
    stringsAsFactors = FALSE
  ))
}

.gp_ac_make_difference_matrix <- function(long_data,
                                          condition_a = NULL,
                                          condition_b = NULL) {
  conditions <- sort(unique(long_data$condition))

  if (length(conditions) != 2L) {
    stop(
      "Difference-matrix export requires exactly two conditions. Found: ",
      paste(conditions, collapse = ", "),
      call. = FALSE
    )
  }

  if (is.null(condition_a)) {
    condition_a <- conditions[1L]
  }

  if (is.null(condition_b)) {
    condition_b <- conditions[2L]
  }

  if (!all(c(condition_a, condition_b) %in% conditions)) {
    stop("`condition_a` and `condition_b` must both be present in the data.", call. = FALSE)
  }

  wide <- stats::reshape(
    long_data,
    idvar = c("participant", "time"),
    timevar = "condition",
    direction = "wide"
  )

  col_a <- paste0("value.", condition_a)
  col_b <- paste0("value.", condition_b)

  if (!all(c(col_a, col_b) %in% names(wide))) {
    stop("Could not construct paired condition columns.", call. = FALSE)
  }

  wide$difference <- wide[[col_b]] - wide[[col_a]]

  diff_wide <- stats::reshape(
    wide[c("participant", "time", "difference")],
    idvar = "participant",
    timevar = "time",
    direction = "wide"
  )

  diff_wide <- diff_wide[order(diff_wide$participant), ]
  rownames(diff_wide) <- NULL

  attr(diff_wide, "condition_a") <- condition_a
  attr(diff_wide, "condition_b") <- condition_b

  diff_wide
}

#' Guardrail for cluster-permutation ANOVA
#'
#' This function is intentionally not implemented as a runnable inferential
#' engine. It exists to make the unsupported scope explicit.
#'
#' @param ... Ignored.
#'
#' @return This function always errors.
#' @export
run_gazepoint_cluster_permutation_anova <- function(...) {
  .gp_ac_stop_unsupported(
    "run_gazepoint_cluster_permutation_anova",
    paste(
      "Cluster-permutation ANOVA requires design-specific exchangeability",
      "rules, factorial effects, interaction contrasts, and careful handling",
      "of repeated-measures structure. Implementing this naively would risk",
      "invalid inference."
    ),
    alternative = paste(
      "Use the current two-condition `run_gazepoint_cluster_permutation()`",
      "or export data for a dedicated package such as permuco."
    )
  )
}

#' Guardrail for mixed-model cluster permutation
#'
#' This function is intentionally not implemented as a runnable inferential
#' engine.
#'
#' @param ... Ignored.
#'
#' @return This function always errors.
#' @export
run_gazepoint_cluster_permutation_lmer <- function(...) {
  .gp_ac_stop_unsupported(
    "run_gazepoint_cluster_permutation_lmer",
    paste(
      "Trial-level mixed-model cluster permutation requires a full regression",
      "permutation framework, random-effects specification, convergence",
      "handling, and preferably Freedman-Lane or related residual-permutation",
      "schemes. This is outside the validated scope of gpbiometrics."
    ),
    alternative = paste(
      "Use subject-level aggregation with `run_gazepoint_cluster_permutation()`",
      "or export trial-level data for a specialized mixed-model permutation",
      "workflow."
    )
  )
}

#' Guardrail for threshold-free cluster enhancement
#'
#' This function is intentionally not implemented as a runnable inferential
#' engine.
#'
#' @param ... Ignored.
#'
#' @return This function always errors.
#' @export
run_gazepoint_tfce <- function(...) {
  .gp_ac_stop_unsupported(
    "run_gazepoint_tfce",
    paste(
      "TFCE avoids a fixed cluster-forming threshold but introduces additional",
      "parameters and validation requirements. It should not be added until",
      "the fixed-threshold cluster workflow has been reviewed and validated."
    ),
    alternative = paste(
      "Use `run_gazepoint_cluster_threshold_sensitivity()` to inspect",
      "sensitivity to fixed cluster-forming thresholds."
    )
  )
}

#' Guardrail for multidimensional cluster permutation
#'
#' This function is intentionally not implemented as a runnable inferential
#' engine.
#'
#' @param ... Ignored.
#'
#' @return This function always errors.
#' @export
run_gazepoint_multidimensional_cluster_permutation <- function(...) {
  .gp_ac_stop_unsupported(
    "run_gazepoint_multidimensional_cluster_permutation",
    paste(
      "Multidimensional clustering, such as time by AOI or time by signal,",
      "requires explicit adjacency definitions and different null-distribution",
      "construction. The current validated implementation clusters only along",
      "one time dimension."
    ),
    alternative = paste(
      "Run the current one-dimensional time-course workflow separately and",
      "report the family of analyses transparently."
    )
  )
}

#' Guardrail against exact cluster-onset estimation
#'
#' Cluster-permutation timing should be interpreted descriptively, not as a
#' precise onset estimate.
#'
#' @param ... Ignored.
#'
#' @return This function always errors.
#' @export
estimate_gazepoint_cluster_onset <- function(...) {
  .gp_ac_stop_unsupported(
    "estimate_gazepoint_cluster_onset",
    paste(
      "Cluster boundaries are not valid precise estimates of effect onset.",
      "Returning an onset estimate would encourage overinterpretation of",
      "cluster timing."
    ),
    alternative = paste(
      "Use `summarize_gazepoint_time_clusters()` and describe the reported",
      "time range as descriptive only."
    )
  )
}

#' Guardrail against exact cluster-offset estimation
#'
#' Cluster-permutation timing should be interpreted descriptively, not as a
#' precise offset estimate.
#'
#' @param ... Ignored.
#'
#' @return This function always errors.
#' @export
estimate_gazepoint_cluster_offset <- function(...) {
  .gp_ac_stop_unsupported(
    "estimate_gazepoint_cluster_offset",
    paste(
      "Cluster boundaries are not valid precise estimates of effect offset.",
      "Returning an offset estimate would encourage overinterpretation of",
      "cluster timing."
    ),
    alternative = paste(
      "Use `summarize_gazepoint_time_clusters()` and describe the reported",
      "time range as descriptive only."
    )
  )
}

#' Guardrail for covariate-adjusted cluster permutation
#'
#' This function is intentionally not implemented as a runnable inferential
#' engine.
#'
#' @param ... Ignored.
#'
#' @return This function always errors.
#' @export
run_gazepoint_cluster_permutation_covariate_adjusted <- function(...) {
  .gp_ac_stop_unsupported(
    "run_gazepoint_cluster_permutation_covariate_adjusted",
    paste(
      "Covariate-adjusted cluster permutation requires a formal regression",
      "permutation scheme and careful treatment of nuisance predictors.",
      "Naively permuting adjusted data can invalidate the test."
    ),
    alternative = paste(
      "Use the current unadjusted two-condition cluster workflow, report",
      "covariate-adjusted models separately, or export data for a specialized",
      "regression-permutation package."
    )
  )
}

#' Guardrail for high-performance cluster permutation
#'
#' This function is intentionally not implemented as a separate backend.
#'
#' @param ... Ignored.
#'
#' @return This function always errors.
#' @export
run_gazepoint_cluster_permutation_parallel <- function(...) {
  .gp_ac_stop_unsupported(
    "run_gazepoint_cluster_permutation_parallel",
    paste(
      "A parallel backend must reproduce the same null-distribution logic as",
      "the serial implementation, including reproducible random-number streams",
      "and identical cluster-mass calculations. This has not yet been validated."
    ),
    alternative = paste(
      "Use `run_gazepoint_cluster_permutation()` with a moderate number of",
      "permutations and a fixed `seed`."
    )
  )
}

#' Export time-course data for MNE cluster-permutation workflows
#'
#' Prepares participant-level condition differences in a wide matrix format
#' commonly used by MNE-style one-sample cluster-permutation workflows.
#'
#' @param data A data frame.
#' @param outcome_col Numeric outcome column.
#' @param time_col Time-bin column.
#' @param condition_col Condition column.
#' @param participant_col Participant identifier column.
#' @param condition_a Reference condition. If `NULL`, the first sorted condition
#'   is used.
#' @param condition_b Comparison condition. If `NULL`, the second sorted
#'   condition is used.
#' @param path Optional output directory. If `NULL`, files are not written.
#' @param prefix File-name prefix used when `path` is supplied.
#' @param overwrite Should existing files be overwritten?
#' @param aggregate Should repeated participant-condition-time cells be averaged?
#'
#' @return A list containing long data, a wide difference matrix, and metadata,
#'   invisibly if files are written.
#' @export
export_gazepoint_mne_cluster_input <- function(data,
                                               outcome_col,
                                               time_col,
                                               condition_col,
                                               participant_col,
                                               condition_a = NULL,
                                               condition_b = NULL,
                                               path = NULL,
                                               prefix = "gazepoint_mne_cluster",
                                               overwrite = FALSE,
                                               aggregate = TRUE) {
  env <- parent.frame()

  outcome_name <- .gp_ac_col_name(substitute(outcome_col), env)
  time_name <- .gp_ac_col_name(substitute(time_col), env)
  condition_name <- .gp_ac_col_name(substitute(condition_col), env)
  participant_name <- .gp_ac_col_name(substitute(participant_col), env)

  long_data <- .gp_ac_prepare_long_timecourse(
    data = data,
    outcome_col = outcome_name,
    time_col = time_name,
    condition_col = condition_name,
    participant_col = participant_name,
    aggregate = aggregate
  )

  difference_matrix <- .gp_ac_make_difference_matrix(
    long_data,
    condition_a = condition_a,
    condition_b = condition_b
  )

  metadata <- data.frame(
    field = c(
      "source",
      "intended_workflow",
      "condition_a",
      "condition_b",
      "difference_definition",
      "timing_warning"
    ),
    value = c(
      "gpbiometrics",
      "MNE-style one-sample cluster test on participant-level differences",
      attr(difference_matrix, "condition_a"),
      attr(difference_matrix, "condition_b"),
      "condition_b - condition_a",
      "Cluster timing is descriptive and should not be interpreted as precise onset or offset."
    ),
    stringsAsFactors = FALSE
  )

  outputs <- list(
    long = long_data,
    difference_matrix = difference_matrix,
    metadata = metadata
  )

  written <- .gp_ac_write_outputs(
    outputs = outputs,
    path = path,
    prefix = prefix,
    overwrite = overwrite
  )

  if (!is.null(path)) {
    return(written)
  }

  outputs
}

#' Export time-course data for permuco cluster workflows
#'
#' Prepares conservative long-format participant-level time-course data and
#' metadata for external analysis in packages such as `permuco`.
#'
#' @param data A data frame.
#' @param outcome_col Numeric outcome column.
#' @param time_col Time-bin column.
#' @param condition_col Condition column.
#' @param participant_col Participant identifier column.
#' @param path Optional output directory.
#' @param prefix File-name prefix.
#' @param overwrite Should existing files be overwritten?
#' @param aggregate Should repeated participant-condition-time cells be averaged?
#'
#' @return A list containing long data and metadata, or a file table if `path`
#'   is supplied.
#' @export
export_gazepoint_permuco_cluster_input <- function(data,
                                                   outcome_col,
                                                   time_col,
                                                   condition_col,
                                                   participant_col,
                                                   path = NULL,
                                                   prefix = "gazepoint_permuco_cluster",
                                                   overwrite = FALSE,
                                                   aggregate = TRUE) {
  env <- parent.frame()

  outcome_name <- .gp_ac_col_name(substitute(outcome_col), env)
  time_name <- .gp_ac_col_name(substitute(time_col), env)
  condition_name <- .gp_ac_col_name(substitute(condition_col), env)
  participant_name <- .gp_ac_col_name(substitute(participant_col), env)

  long_data <- .gp_ac_prepare_long_timecourse(
    data = data,
    outcome_col = outcome_name,
    time_col = time_name,
    condition_col = condition_name,
    participant_col = participant_name,
    aggregate = aggregate
  )

  metadata <- data.frame(
    field = c(
      "source",
      "intended_workflow",
      "suggested_columns",
      "scope_warning",
      "timing_warning"
    ),
    value = c(
      "gpbiometrics",
      "External permuco cluster workflow",
      "participant, condition, time, value",
      "Use external documentation to specify a valid permutation model and exchangeability scheme.",
      "Cluster timing is descriptive and should not be interpreted as precise onset or offset."
    ),
    stringsAsFactors = FALSE
  )

  outputs <- list(
    long = long_data,
    metadata = metadata
  )

  written <- .gp_ac_write_outputs(
    outputs = outputs,
    path = path,
    prefix = prefix,
    overwrite = overwrite
  )

  if (!is.null(path)) {
    return(written)
  }

  outputs
}

#' Export time-course data for permutes cluster workflows
#'
#' Prepares conservative long-format participant-level time-course data and
#' metadata for external analysis in packages such as `permutes`.
#'
#' @param data A data frame.
#' @param outcome_col Numeric outcome column.
#' @param time_col Time-bin column.
#' @param condition_col Condition column.
#' @param participant_col Participant identifier column.
#' @param path Optional output directory.
#' @param prefix File-name prefix.
#' @param overwrite Should existing files be overwritten?
#' @param aggregate Should repeated participant-condition-time cells be averaged?
#'
#' @return A list containing long data and metadata, or a file table if `path`
#'   is supplied.
#' @export
export_gazepoint_permutes_cluster_input <- function(data,
                                                    outcome_col,
                                                    time_col,
                                                    condition_col,
                                                    participant_col,
                                                    path = NULL,
                                                    prefix = "gazepoint_permutes_cluster",
                                                    overwrite = FALSE,
                                                    aggregate = TRUE) {
  env <- parent.frame()

  outcome_name <- .gp_ac_col_name(substitute(outcome_col), env)
  time_name <- .gp_ac_col_name(substitute(time_col), env)
  condition_name <- .gp_ac_col_name(substitute(condition_col), env)
  participant_name <- .gp_ac_col_name(substitute(participant_col), env)

  long_data <- .gp_ac_prepare_long_timecourse(
    data = data,
    outcome_col = outcome_name,
    time_col = time_name,
    condition_col = condition_name,
    participant_col = participant_name,
    aggregate = aggregate
  )

  metadata <- data.frame(
    field = c(
      "source",
      "intended_workflow",
      "suggested_columns",
      "scope_warning",
      "timing_warning"
    ),
    value = c(
      "gpbiometrics",
      "External permutes cluster workflow",
      "participant, condition, time, value",
      "Use external documentation to specify a valid permutation or mixed-model permutation workflow.",
      "Cluster timing is descriptive and should not be interpreted as precise onset or offset."
    ),
    stringsAsFactors = FALSE
  )

  outputs <- list(
    long = long_data,
    metadata = metadata
  )

  written <- .gp_ac_write_outputs(
    outputs = outputs,
    path = path,
    prefix = prefix,
    overwrite = overwrite
  )

  if (!is.null(path)) {
    return(written)
  }

  outputs
}
