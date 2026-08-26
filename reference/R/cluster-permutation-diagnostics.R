# Cluster-permutation diagnostics, reporting, simulation, and export helpers

if (getRversion() >= "2.15.1") {
  utils::globalVariables(c(
    "mass",
    ".gp_subject",
    ".gp_condition",
    ".gp_time",
    ".gp_value"
  ))
}

.gp_cpd_col_name <- function(expr, env) {
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

.gp_cpd_check_data_frame <- function(data) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (nrow(data) == 0L) {
    stop("`data` must contain at least one row.", call. = FALSE)
  }

  invisible(data)
}

.gp_cpd_check_columns <- function(data, columns) {
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

.gp_cpd_safe_numeric <- function(x) {
  suppressWarnings(as.numeric(x))
}

.gp_cpd_make_key <- function(data) {
  paste(data$subject, data$condition, data$time, sep = "\r")
}

.gp_cpd_first_existing <- function(x, names) {
  for (nm in names) {
    if (!is.null(x[[nm]])) {
      return(x[[nm]])
    }
  }

  NULL
}

.gp_cpd_extract_clusters <- function(result) {
  x <- .gp_cpd_first_existing(
    result,
    c(
      "clusters",
      "cluster_summary",
      "cluster_table",
      "significant_clusters"
    )
  )

  if (is.null(x)) {
    return(data.frame())
  }

  if (is.data.frame(x)) {
    clusters <- x
  } else if (is.list(x)) {
    if (length(x) == 0L) {
      return(data.frame())
    }

    clusters <- do.call(
      rbind,
      lapply(seq_along(x), function(i) {
        item <- x[[i]]

        if (is.null(item)) {
          return(NULL)
        }

        out <- as.data.frame(item, stringsAsFactors = FALSE)
        out$cluster_id <- i
        out
      })
    )

    if (is.null(clusters)) {
      clusters <- data.frame()
    }
  } else {
    return(data.frame())
  }

  if (nrow(clusters) > 0L && !"cluster_id" %in% names(clusters)) {
    clusters$cluster_id <- seq_len(nrow(clusters))
  }

  clusters
}

.gp_cpd_extract_timewise <- function(result) {
  x <- .gp_cpd_first_existing(
    result,
    c(
      "stat",
      "statistics",
      "timewise_statistics",
      "timewise",
      "observed_statistics",
      "T_obs"
    )
  )

  if (is.null(x)) {
    return(data.frame())
  }

  if (is.data.frame(x)) {
    return(x)
  }

  if (is.numeric(x)) {
    return(data.frame(
      index = seq_along(x),
      statistic = as.numeric(x)
    ))
  }

  data.frame()
}

.gp_cpd_extract_null_distribution <- function(result) {
  x <- .gp_cpd_first_existing(
    result,
    c(
      "null_distribution",
      "null_dist",
      "permutation_distribution",
      "H0",
      "max_cluster_mass_null"
    )
  )

  if (is.null(x)) {
    stop(
      "Could not find a null distribution in `result`. Expected one of: ",
      "`null_distribution`, `null_dist`, `permutation_distribution`, `H0`, ",
      "or `max_cluster_mass_null`.",
      call. = FALSE
    )
  }

  if (is.data.frame(x)) {
    numeric_columns <- names(x)[vapply(x, is.numeric, logical(1L))]

    preferred <- intersect(
      c(
        "max_cluster_mass",
        "max_abs_cluster_mass",
        "cluster_mass",
        "mass",
        "H0"
      ),
      numeric_columns
    )

    if (length(preferred) > 0L) {
      x <- x[[preferred[1L]]]
    } else if (length(numeric_columns) > 0L) {
      x <- x[[numeric_columns[1L]]]
    } else {
      stop("The null-distribution data frame has no numeric columns.", call. = FALSE)
    }
  }

  x <- as.numeric(unlist(x, use.names = FALSE))
  x <- x[is.finite(x)]

  if (length(x) == 0L) {
    stop("The null distribution contains no finite numeric values.", call. = FALSE)
  }

  x
}

.gp_cpd_mass_column <- function(clusters) {
  candidates <- c(
    "abs_mass",
    "absolute_mass",
    "cluster_mass_abs",
    "mass_abs",
    "cluster_mass",
    "mass",
    "cluster_stat",
    "statistic"
  )

  present <- intersect(candidates, names(clusters))

  if (length(present) == 0L) {
    return(NULL)
  }

  present[1L]
}

.gp_cpd_p_column <- function(clusters) {
  candidates <- c(
    "p.value",
    "p_value",
    "cluster_p",
    "cluster_p_value",
    "p"
  )

  present <- intersect(candidates, names(clusters))

  if (length(present) == 0L) {
    return(NULL)
  }

  present[1L]
}

.gp_cpd_p_values <- function(clusters) {
  if (!is.data.frame(clusters) || nrow(clusters) == 0L) {
    return(numeric())
  }

  p_col <- .gp_cpd_p_column(clusters)

  if (is.null(p_col)) {
    return(rep(NA_real_, nrow(clusters)))
  }

  suppressWarnings(as.numeric(clusters[[p_col]]))
}

.gp_cpd_cluster_mass <- function(clusters, cluster_id = 1L) {
  if (!is.data.frame(clusters) || nrow(clusters) == 0L) {
    return(NA_real_)
  }

  if ("cluster_id" %in% names(clusters)) {
    row <- which(clusters$cluster_id == cluster_id)[1L]
  } else {
    row <- cluster_id
  }

  if (is.na(row) || length(row) == 0L || row > nrow(clusters)) {
    return(NA_real_)
  }

  mass_col <- .gp_cpd_mass_column(clusters)

  if (is.null(mass_col)) {
    return(NA_real_)
  }

  abs(.gp_cpd_safe_numeric(clusters[[mass_col]][row]))
}

.gp_cpd_time_range <- function(clusters, row) {
  start_candidates <- c("start_time", "time_start", "start", "cluster_start")
  end_candidates <- c("end_time", "time_end", "end", "cluster_end")

  start_col <- intersect(start_candidates, names(clusters))
  end_col <- intersect(end_candidates, names(clusters))

  start_value <- NA
  end_value <- NA

  if (length(start_col) > 0L) {
    start_value <- clusters[[start_col[1L]]][row]
  }

  if (length(end_col) > 0L) {
    end_value <- clusters[[end_col[1L]]][row]
  }

  list(start = start_value, end = end_value)
}

.gp_cpd_format_p <- function(p, digits = 3L) {
  if (length(p) == 0L || is.na(p)) {
    return("NA")
  }

  if (p < 0.001) {
    return("< .001")
  }

  sub("^0", "", formatC(p, digits = digits, format = "f"))
}

.gp_cpd_params_to_data_frame <- function(params) {
  if (is.null(params) || length(params) == 0L) {
    return(data.frame())
  }

  data.frame(
    parameter = names(params),
    value = vapply(
      params,
      function(x) {
        paste(as.character(x), collapse = ", ")
      },
      character(1L)
    ),
    stringsAsFactors = FALSE
  )
}

#' Audit the participant-condition-time grid for cluster-permutation analysis
#'
#' Checks whether a time-course data set has a complete participant by condition
#' by time grid. This is intended as a safety diagnostic before calling
#' [run_gazepoint_cluster_permutation()].
#'
#' @param data A data frame.
#' @param subject Participant identifier column, supplied as a bare column name
#'   or a single string.
#' @param condition Condition column, supplied as a bare column name or a single
#'   string.
#' @param time Time-bin column, supplied as a bare column name or a single string.
#' @param value Optional numeric outcome column used to count missing outcome
#'   values.
#' @param max_report_cells Maximum number of missing or duplicate cells stored in
#'   the returned object.
#'
#' @return An object of class `gazepoint_timecourse_grid_audit`.
#' @export
audit_gazepoint_timecourse_grid <- function(data,
                                            subject,
                                            condition,
                                            time,
                                            value = NULL,
                                            max_report_cells = 1000L) {
  .gp_cpd_check_data_frame(data)

  env <- parent.frame()
  subject_name <- .gp_cpd_col_name(substitute(subject), env)
  condition_name <- .gp_cpd_col_name(substitute(condition), env)
  time_name <- .gp_cpd_col_name(substitute(time), env)

  value_expr <- substitute(value)
  value_name <- NULL

  if (!missing(value) && !identical(value_expr, quote(NULL))) {
    value_name <- .gp_cpd_col_name(value_expr, env)
  }

  required <- c(subject_name, condition_name, time_name)
  if (!is.null(value_name)) {
    required <- c(required, value_name)
  }

  .gp_cpd_check_columns(data, required)

  df <- data.frame(
    subject = as.character(data[[subject_name]]),
    condition = as.character(data[[condition_name]]),
    time = data[[time_name]],
    stringsAsFactors = FALSE
  )

  if (anyNA(df$subject)) {
    stop("`subject` contains missing values.", call. = FALSE)
  }

  if (anyNA(df$condition)) {
    stop("`condition` contains missing values.", call. = FALSE)
  }

  if (anyNA(df$time)) {
    stop("`time` contains missing values.", call. = FALSE)
  }

  cells <- stats::aggregate(
    list(n = rep.int(1L, nrow(df))),
    by = df[c("subject", "condition", "time")],
    FUN = length
  )

  subjects <- sort(unique(df$subject))
  conditions <- sort(unique(df$condition))
  times <- sort(unique(df$time))

  expected <- expand.grid(
    subject = subjects,
    condition = conditions,
    time = times,
    KEEP.OUT.ATTRS = FALSE,
    stringsAsFactors = FALSE
  )

  observed_unique <- cells[c("subject", "condition", "time")]

  missing_cells <- expected[
    !.gp_cpd_make_key(expected) %in% .gp_cpd_make_key(observed_unique),
    ,
    drop = FALSE
  ]

  duplicate_cells <- cells[cells$n > 1L, , drop = FALSE]

  n_missing_values <- NA_integer_
  value_column <- value_name

  if (!is.null(value_name)) {
    n_missing_values <- sum(is.na(data[[value_name]]))
  }

  subject_condition_counts <- as.data.frame.matrix(
    table(df$subject, df$condition)
  )
  subject_condition_counts$subject <- rownames(subject_condition_counts)
  rownames(subject_condition_counts) <- NULL
  subject_condition_counts <- subject_condition_counts[
    c("subject", setdiff(names(subject_condition_counts), "subject"))
  ]

  complete_grid <- nrow(missing_cells) == 0L && nrow(duplicate_cells) == 0L

  summary <- data.frame(
    n_rows = nrow(data),
    n_subjects = length(subjects),
    n_conditions = length(conditions),
    n_time_bins = length(times),
    expected_cells = nrow(expected),
    observed_unique_cells = nrow(observed_unique),
    missing_cells = nrow(missing_cells),
    duplicate_cells = nrow(duplicate_cells),
    missing_values = n_missing_values,
    complete_grid = complete_grid,
    stringsAsFactors = FALSE
  )

  out <- list(
    summary = summary,
    missing_cells = utils::head(missing_cells, max_report_cells),
    duplicate_cells = utils::head(duplicate_cells, max_report_cells),
    subject_condition_counts = subject_condition_counts,
    columns = list(
      subject = subject_name,
      condition = condition_name,
      time = time_name,
      value = value_column
    ),
    max_report_cells = max_report_cells
  )

  class(out) <- "gazepoint_timecourse_grid_audit"
  out
}

#' @export
print.gazepoint_timecourse_grid_audit <- function(x, ...) {
  cat("Gazepoint time-course grid audit\n")
  cat("--------------------------------\n")
  print(x$summary, row.names = FALSE)

  if (isFALSE(x$summary$complete_grid[1L])) {
    cat("\nThe grid is not complete.\n")
  } else {
    cat("\nThe grid is complete.\n")
  }

  if (x$summary$missing_cells[1L] > 0L) {
    cat("\nStored missing cells:\n")
    print(utils::head(x$missing_cells), row.names = FALSE)
  }

  if (x$summary$duplicate_cells[1L] > 0L) {
    cat("\nStored duplicate cells:\n")
    print(utils::head(x$duplicate_cells), row.names = FALSE)
  }

  invisible(x)
}

#' Diagnose whether a design is suitable for cluster-permutation analysis
#'
#' Performs high-level checks on the data structure and design assumptions used
#' by the current cluster-permutation prototype.
#'
#' @param data A data frame.
#' @param subject Participant identifier column.
#' @param condition Condition column.
#' @param time Time-bin column.
#' @param value Optional numeric outcome column.
#' @param design Design to diagnose. The current runner is designed for
#'   within-subject two-condition time-course data.
#' @param min_subjects Minimum recommended number of participants.
#'
#' @return An object of class `gazepoint_cluster_design_diagnostic`.
#' @export
diagnose_gazepoint_cluster_design <- function(data,
                                              subject,
                                              condition,
                                              time,
                                              value = NULL,
                                              design = c("within", "between"),
                                              min_subjects = 10L) {
  design <- match.arg(design)

  env <- parent.frame()
  subject_name <- .gp_cpd_col_name(substitute(subject), env)
  condition_name <- .gp_cpd_col_name(substitute(condition), env)
  time_name <- .gp_cpd_col_name(substitute(time), env)

  value_expr <- substitute(value)
  value_name <- NULL

  if (!missing(value) && !identical(value_expr, quote(NULL))) {
    value_name <- .gp_cpd_col_name(value_expr, env)
  }

  audit <- audit_gazepoint_timecourse_grid(
    data = data,
    subject = subject_name,
    condition = condition_name,
    time = time_name,
    value = value_name
  )

  s <- audit$summary
  counts <- audit$subject_condition_counts
  condition_columns <- setdiff(names(counts), "subject")

  row_condition_presence <- rowSums(counts[condition_columns] > 0L)

  check_rows <- list(
    data.frame(
      check = "two_conditions",
      passed = s$n_conditions == 2L,
      severity = if (s$n_conditions == 2L) "ok" else "error",
      message = if (s$n_conditions == 2L) {
        "Exactly two conditions are present."
      } else {
        paste0("Expected two conditions; found ", s$n_conditions, ".")
      },
      stringsAsFactors = FALSE
    ),
    data.frame(
      check = "complete_grid",
      passed = isTRUE(s$complete_grid),
      severity = if (isTRUE(s$complete_grid)) "ok" else "error",
      message = if (isTRUE(s$complete_grid)) {
        "Every participant-condition-time cell is present exactly once."
      } else {
        "The participant-condition-time grid has missing or duplicate cells."
      },
      stringsAsFactors = FALSE
    ),
    data.frame(
      check = "minimum_subjects",
      passed = s$n_subjects >= min_subjects,
      severity = if (s$n_subjects >= min_subjects) "ok" else "warning",
      message = if (s$n_subjects >= min_subjects) {
        paste0("At least ", min_subjects, " participants are present.")
      } else {
        paste0(
          "Only ", s$n_subjects, " participant(s) are present; permutation ",
          "p-values may be coarse or unstable."
        )
      },
      stringsAsFactors = FALSE
    )
  )

  if (design == "within") {
    within_ok <- all(row_condition_presence == length(condition_columns))

    check_rows[[length(check_rows) + 1L]] <- data.frame(
      check = "within_subject_condition_presence",
      passed = within_ok,
      severity = if (within_ok) "ok" else "error",
      message = if (within_ok) {
        "Every participant appears in every condition."
      } else {
        "At least one participant is missing one or more conditions."
      },
      stringsAsFactors = FALSE
    )

    check_rows[[length(check_rows) + 1L]] <- data.frame(
      check = "supported_by_current_runner",
      passed = TRUE,
      severity = "ok",
      message = paste(
        "The current runner supports the diagnosed within-subject,",
        "two-condition time-course design."
      ),
      stringsAsFactors = FALSE
    )
  } else {
    between_ok <- all(row_condition_presence == 1L)

    check_rows[[length(check_rows) + 1L]] <- data.frame(
      check = "between_subject_condition_presence",
      passed = between_ok,
      severity = if (between_ok) "ok" else "error",
      message = if (between_ok) {
        "Each participant appears in one condition."
      } else {
        "At least one participant appears in more than one condition."
      },
      stringsAsFactors = FALSE
    )

    check_rows[[length(check_rows) + 1L]] <- data.frame(
      check = "supported_by_current_runner",
      passed = FALSE,
      severity = "warning",
      message = paste(
        "The current cluster-permutation runner is conservative and focused on",
        "within-subject two-condition time courses."
      ),
      stringsAsFactors = FALSE
    )
  }

  checks <- do.call(rbind, check_rows)

  out <- list(
    design = design,
    checks = checks,
    audit = audit,
    passed = all(checks$passed[checks$severity == "error"]),
    columns = list(
      subject = subject_name,
      condition = condition_name,
      time = time_name,
      value = value_name
    )
  )

  class(out) <- "gazepoint_cluster_design_diagnostic"
  out
}

#' @export
print.gazepoint_cluster_design_diagnostic <- function(x, ...) {
  cat("Gazepoint cluster-permutation design diagnostic\n")
  cat("------------------------------------------------\n")
  cat("Design:", x$design, "\n\n")
  print(x$checks, row.names = FALSE)

  if (isTRUE(x$passed)) {
    cat("\nNo blocking design errors were detected.\n")
  } else {
    cat("\nOne or more blocking design errors were detected.\n")
  }

  invisible(x)
}

#' Plot the cluster-permutation null distribution
#'
#' Plots the permutation null distribution of maximum cluster masses and,
#' when available, overlays the observed cluster mass for one observed cluster.
#'
#' @param result Object returned by [run_gazepoint_cluster_permutation()].
#' @param cluster_id Observed cluster to overlay.
#' @param observed_mass Optional observed cluster mass. If `NULL`, the function
#'   attempts to extract the mass from `result`.
#' @param bins Number of histogram bins.
#'
#' @return A `ggplot` object.
#' @export
plot_gazepoint_cluster_null_distribution <- function(result,
                                                     cluster_id = 1L,
                                                     observed_mass = NULL,
                                                     bins = 30L) {
  null <- .gp_cpd_extract_null_distribution(result)
  clusters <- .gp_cpd_extract_clusters(result)

  if (is.null(observed_mass)) {
    observed_mass <- .gp_cpd_cluster_mass(clusters, cluster_id = cluster_id)
  }

  plot_data <- data.frame(mass = abs(null))

  p <- ggplot2::ggplot(plot_data, ggplot2::aes(x = mass)) +
    ggplot2::geom_histogram(bins = bins) +
    ggplot2::labs(
      title = "Cluster-permutation null distribution",
      subtitle = "Distribution of maximum absolute cluster mass under permutation",
      x = "Maximum absolute cluster mass",
      y = "Permutation count"
    ) +
    ggplot2::theme_minimal()

  if (is.finite(observed_mass)) {
    p <- p +
      ggplot2::geom_vline(
        xintercept = abs(observed_mass),
        linewidth = 0.8,
        linetype = "dashed"
      ) +
      ggplot2::labs(
        caption = paste0(
          "Dashed line: observed absolute cluster mass for cluster ",
          cluster_id,
          "."
        )
      )
  }

  p
}

#' Create conservative reporting text for a cluster-permutation result
#'
#' Generates cautious manuscript-ready wording for a cluster-permutation result.
#' The wording avoids precise onset or offset claims and frames cluster timing as
#' descriptive.
#'
#' @param result Object returned by [run_gazepoint_cluster_permutation()].
#' @param cluster_alpha Cluster-level alpha used to classify clusters.
#' @param digits Number of digits used for p-values.
#' @param include_assumptions Should an assumptions note be included?
#'
#' @return An object of class `gazepoint_cluster_report`.
#' @export
report_gazepoint_cluster_permutation <- function(result,
                                                 cluster_alpha = 0.05,
                                                 digits = 3L,
                                                 include_assumptions = TRUE) {
  clusters <- .gp_cpd_extract_clusters(result)
  p_values <- .gp_cpd_p_values(clusters)

  if (nrow(clusters) == 0L || length(p_values) == 0L || all(is.na(p_values))) {
    main <- paste(
      "The cluster-based permutation test did not return interpretable",
      "cluster-level p-values."
    )
  } else {
    sig <- which(!is.na(p_values) & p_values <= cluster_alpha)

    if (length(sig) == 0L) {
      main <- paste0(
        "The cluster-based permutation test did not indicate cluster-level ",
        "evidence of a condition difference at alpha = ",
        cluster_alpha,
        "."
      )
    } else {
      cluster_descriptions <- vapply(sig, function(i) {
        range <- .gp_cpd_time_range(clusters, i)
        p_text <- .gp_cpd_format_p(p_values[i], digits = digits)

        if (!is.na(range$start) && !is.na(range$end)) {
          paste0(
            "cluster ", clusters$cluster_id[i],
            " (descriptive time range: ",
            range$start, " to ", range$end,
            ", p = ", p_text, ")"
          )
        } else {
          paste0(
            "cluster ", clusters$cluster_id[i],
            " (p = ", p_text, ")"
          )
        }
      }, character(1L))

      main <- paste0(
        "The cluster-based permutation test indicated cluster-level evidence ",
        "of a condition difference in the tested time course: ",
        paste(cluster_descriptions, collapse = "; "),
        "."
      )
    }
  }

  caution <- paste(
    "The temporal extent of any detected cluster should be interpreted",
    "descriptively. The test evaluates evidence against the global null of no",
    "condition difference anywhere in the tested time range; it does not provide",
    "a precise estimate of effect onset, offset, latency, physiological event",
    "boundary, emotion, stress, cognition, diagnosis, or mechanism."
  )

  assumptions <- c(
    "two-condition comparison",
    "participant-level time courses",
    "common participant-condition-time grid",
    "permutation scheme matched to the supported design",
    "cluster timing interpreted descriptively"
  )

  text <- if (isTRUE(include_assumptions)) {
    paste0(
      main,
      " ",
      caution,
      " Assumptions checked/reported: ",
      paste(assumptions, collapse = "; "),
      "."
    )
  } else {
    paste(main, caution)
  }

  out <- list(
    text = text,
    clusters = clusters,
    cluster_alpha = cluster_alpha,
    assumptions = assumptions
  )

  class(out) <- "gazepoint_cluster_report"
  out
}

#' @export
print.gazepoint_cluster_report <- function(x, ...) {
  cat(x$text, "\n")
  invisible(x)
}

.gp_cpd_match_formal <- function(formal_names, candidates, label) {
  matched <- intersect(candidates, formal_names)

  if (length(matched) == 0L) {
    stop(
      "Could not identify the `", label, "` argument for ",
      "`run_gazepoint_cluster_permutation()`. Candidate names checked: ",
      paste(candidates, collapse = ", "),
      ".",
      call. = FALSE
    )
  }

  matched[1L]
}

.gp_cpd_run_standard_cluster <- function(data, threshold, seed, ...) {
  fn <- run_gazepoint_cluster_permutation
  formal_names <- names(formals(fn))

  value_arg <- .gp_cpd_match_formal(
    formal_names,
    c(
      "value_col",
      "dv_col",
      "dv",
      "value",
      "signal_col",
      "outcome_col",
      "measure_col"
    ),
    "value column"
  )

  time_arg <- .gp_cpd_match_formal(
    formal_names,
    c(
      "time_col",
      "time",
      "time_column",
      "bin_col",
      "time_bin_col"
    ),
    "time column"
  )

  condition_arg <- .gp_cpd_match_formal(
    formal_names,
    c(
      "condition_col",
      "condition",
      "condition_column",
      "group_col",
      "group"
    ),
    "condition column"
  )

  subject_arg <- .gp_cpd_match_formal(
    formal_names,
    c(
      "subject_col",
      "subject",
      "subject_id_col",
      "participant_col",
      "participant",
      "id_col",
      "id"
    ),
    "subject column"
  )

  threshold_arg <- .gp_cpd_match_formal(
    formal_names,
    c(
      "threshold",
      "cluster_threshold",
      "cluster_forming_threshold",
      "cluster_forming_alpha",
      "threshold_p",
      "p_threshold",
      "alpha"
    ),
    "cluster-forming threshold"
  )

  args <- list(data = data)
  args[[value_arg]] <- ".gp_value"
  args[[time_arg]] <- ".gp_time"
  args[[condition_arg]] <- ".gp_condition"
  args[[subject_arg]] <- ".gp_subject"
  args[[threshold_arg]] <- threshold

  if ("seed" %in% formal_names) {
    args[["seed"]] <- seed
  }

  extra_args <- list(...)

  duplicated_args <- intersect(names(extra_args), names(args))
  if (length(duplicated_args) > 0L) {
    args[duplicated_args] <- NULL
  }

  args <- c(args, extra_args)

  do.call(fn, args)
}


#' Run threshold-sensitivity checks for cluster-permutation analysis
#'
#' Re-runs [run_gazepoint_cluster_permutation()] across several cluster-forming
#' thresholds and summarizes whether the broad result is stable.
#'
#' @param data A data frame.
#' @param dv Numeric outcome column.
#' @param time Time-bin column.
#' @param condition Condition column.
#' @param subject Participant identifier column.
#' @param thresholds Numeric vector of cluster-forming thresholds.
#' @param cluster_alpha Cluster-level alpha used for counting significant
#'   clusters in the summary.
#' @param seed Optional seed. If provided, each threshold receives a deterministic
#'   seed offset.
#' @param ... Additional arguments passed to
#'   [run_gazepoint_cluster_permutation()].
#'
#' @return An object of class `gazepoint_cluster_threshold_sensitivity`.
#' @export
run_gazepoint_cluster_threshold_sensitivity <- function(data,
                                                        dv,
                                                        time,
                                                        condition,
                                                        subject,
                                                        thresholds = c(0.01, 0.025, 0.05, 0.10),
                                                        cluster_alpha = 0.05,
                                                        seed = NULL,
                                                        ...) {
  .gp_cpd_check_data_frame(data)

  env <- parent.frame()
  dv_name <- .gp_cpd_col_name(substitute(dv), env)
  time_name <- .gp_cpd_col_name(substitute(time), env)
  condition_name <- .gp_cpd_col_name(substitute(condition), env)
  subject_name <- .gp_cpd_col_name(substitute(subject), env)

  .gp_cpd_check_columns(
    data,
    c(dv_name, time_name, condition_name, subject_name)
  )

  if (!is.numeric(thresholds) || length(thresholds) == 0L) {
    stop("`thresholds` must be a non-empty numeric vector.", call. = FALSE)
  }

  if (any(!is.finite(thresholds)) || any(thresholds <= 0 | thresholds >= 1)) {
    stop("All `thresholds` must be finite values between 0 and 1.", call. = FALSE)
  }

  standard <- data.frame(
    .gp_subject = data[[subject_name]],
    .gp_condition = data[[condition_name]],
    .gp_time = data[[time_name]],
    .gp_value = data[[dv_name]],
    stringsAsFactors = FALSE
  )

  audit <- audit_gazepoint_timecourse_grid(
    standard,
    subject = ".gp_subject",
    condition = ".gp_condition",
    time = ".gp_time",
    value = ".gp_value"
  )

  if (!isTRUE(audit$summary$complete_grid[1L])) {
    stop(
      "The participant-condition-time grid is incomplete. Run ",
      "`audit_gazepoint_timecourse_grid()` before sensitivity analysis.",
      call. = FALSE
    )
  }

  results <- vector("list", length(thresholds))
  summary_rows <- vector("list", length(thresholds))

  for (i in seq_along(thresholds)) {
    seed_i <- if (is.null(seed)) NULL else seed + i - 1L

    result_i <- .gp_cpd_run_standard_cluster(
      data = standard,
      threshold = thresholds[i],
      seed = seed_i,
      ...
    )

    clusters_i <- .gp_cpd_extract_clusters(result_i)
    p_i <- .gp_cpd_p_values(clusters_i)

    min_p <- if (length(p_i) == 0L || all(is.na(p_i))) {
      NA_real_
    } else {
      min(p_i, na.rm = TRUE)
    }

    summary_rows[[i]] <- data.frame(
      threshold = thresholds[i],
      n_clusters = nrow(clusters_i),
      min_p_value = min_p,
      n_significant = sum(!is.na(p_i) & p_i <= cluster_alpha),
      stringsAsFactors = FALSE
    )

    results[[i]] <- result_i
  }

  names(results) <- paste0("threshold_", thresholds)

  out <- list(
    summary = do.call(rbind, summary_rows),
    results = results,
    thresholds = thresholds,
    cluster_alpha = cluster_alpha,
    seed = seed,
    audit = audit
  )

  class(out) <- "gazepoint_cluster_threshold_sensitivity"
  out
}

#' @export
print.gazepoint_cluster_threshold_sensitivity <- function(x, ...) {
  cat("Gazepoint cluster-permutation threshold sensitivity\n")
  cat("----------------------------------------------------\n")
  print(x$summary, row.names = FALSE)
  invisible(x)
}

#' Simulate two-condition time-course data for cluster-permutation examples
#'
#' Creates participant-level synthetic time-course data with an optional effect
#' window. The function is intended for examples, tests, teaching, and
#' documentation.
#'
#' @param n_subjects Number of participants.
#' @param n_time Number of time bins.
#' @param conditions Character vector of two condition labels.
#' @param effect_start First time value included in the effect window.
#' @param effect_end Last time value included in the effect window.
#' @param effect_size Additive effect size inside the effect window.
#' @param noise_sd Standard deviation of observation-level noise.
#' @param subject_sd Standard deviation of participant-level random intercepts.
#' @param time_start First time value.
#' @param time_step Step between time bins.
#' @param effect_condition Condition receiving the additive effect.
#' @param seed Optional random seed.
#'
#' @return A data frame with columns `subject`, `condition`, `time`, `value`,
#'   and `true_effect`.
#' @export
simulate_gazepoint_cluster_timecourse_data <- function(n_subjects = 12L,
                                                       n_time = 60L,
                                                       conditions = c("A", "B"),
                                                       effect_start = 25,
                                                       effect_end = 38,
                                                       effect_size = 0.6,
                                                       noise_sd = 0.4,
                                                       subject_sd = 0.25,
                                                       time_start = 1,
                                                       time_step = 1,
                                                       effect_condition = "B",
                                                       seed = NULL) {
  if (!is.null(seed)) {
    set.seed(seed)
  }

  if (length(conditions) != 2L) {
    stop("`conditions` must contain exactly two condition labels.", call. = FALSE)
  }

  if (!effect_condition %in% conditions) {
    stop("`effect_condition` must be one of `conditions`.", call. = FALSE)
  }

  if (n_subjects < 2L) {
    stop("`n_subjects` must be at least 2.", call. = FALSE)
  }

  if (n_time < 2L) {
    stop("`n_time` must be at least 2.", call. = FALSE)
  }

  subjects <- sprintf("S%02d", seq_len(n_subjects))
  times <- time_start + (seq_len(n_time) - 1L) * time_step

  grid <- expand.grid(
    subject = subjects,
    condition = conditions,
    time = times,
    KEEP.OUT.ATTRS = FALSE,
    stringsAsFactors = FALSE
  )

  subject_intercepts <- stats::rnorm(n_subjects, mean = 0, sd = subject_sd)
  names(subject_intercepts) <- subjects

  smooth_time <- sin(seq(0, 2 * pi, length.out = n_time))
  names(smooth_time) <- as.character(times)

  in_effect_window <- grid$time >= effect_start & grid$time <= effect_end
  receives_effect <- grid$condition == effect_condition

  grid$true_effect <- ifelse(
    in_effect_window & receives_effect,
    effect_size,
    0
  )

  grid$value <- subject_intercepts[grid$subject] +
    0.15 * smooth_time[as.character(grid$time)] +
    grid$true_effect +
    stats::rnorm(nrow(grid), mean = 0, sd = noise_sd)

  rownames(grid) <- NULL
  grid
}

#' Export cluster-permutation result components
#'
#' Writes the cluster summary, timewise statistics, null distribution, parameter
#' table, and conservative reporting text to disk.
#'
#' @param result Object returned by [run_gazepoint_cluster_permutation()].
#' @param path Output directory.
#' @param prefix File-name prefix.
#' @param overwrite Should existing files be overwritten?
#'
#' @return A data frame listing written files, invisibly.
#' @export
export_gazepoint_cluster_results <- function(result,
                                             path = ".",
                                             prefix = "gazepoint_cluster",
                                             overwrite = FALSE) {
  if (!dir.exists(path)) {
    dir.create(path, recursive = TRUE, showWarnings = FALSE)
  }

  if (!dir.exists(path)) {
    stop("Could not create output directory: ", path, call. = FALSE)
  }

  make_file <- function(suffix) {
    file.path(path, paste0(prefix, "_", suffix))
  }

  files <- c(
    clusters = make_file("clusters.csv"),
    timewise = make_file("timewise_statistics.csv"),
    null = make_file("null_distribution.csv"),
    params = make_file("parameters.csv"),
    report = make_file("report.txt")
  )

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

  clusters <- .gp_cpd_extract_clusters(result)
  timewise <- .gp_cpd_extract_timewise(result)
  null <- .gp_cpd_extract_null_distribution(result)

  params <- .gp_cpd_params_to_data_frame(result$params)
  report <- report_gazepoint_cluster_permutation(result)

  utils::write.csv(clusters, files[["clusters"]], row.names = FALSE)
  utils::write.csv(timewise, files[["timewise"]], row.names = FALSE)
  utils::write.csv(
    data.frame(null_distribution = null),
    files[["null"]],
    row.names = FALSE
  )
  utils::write.csv(params, files[["params"]], row.names = FALSE)
  writeLines(report$text, files[["report"]], useBytes = TRUE)

  out <- data.frame(
    component = names(files),
    file = unname(files),
    stringsAsFactors = FALSE
  )

  invisible(out)
}
