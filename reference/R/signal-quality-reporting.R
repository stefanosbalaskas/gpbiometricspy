#' Compute transparent signal-quality indicators
#'
#' Computes conservative, rule-based descriptive quality indicators for one or
#' more Gazepoint biometric signal columns. The function does not interpret the
#' physiological meaning of the signal and does not exclude data.
#'
#' @param data A data frame.
#' @param signal_cols Character vector of numeric signal columns to evaluate.
#' @param group_cols Optional character vector of grouping columns, such as
#'   participant, trial, condition, session, window, or segment identifiers.
#' @param flatline_tolerance Numeric tolerance used when detecting adjacent
#'   constant values. Defaults to 0.
#' @param long_missing_run_threshold Integer threshold used to count whether a
#'   segment contains a long missing run. The maximum run length is always
#'   returned regardless of this threshold.
#' @param long_constant_run_threshold Integer threshold used to count whether a
#'   segment contains a long constant run. The maximum run length is always
#'   returned regardless of this threshold.
#' @param spike_z Numeric z-score threshold for adjacent-change spikes.
#' @param extreme_z Numeric z-score threshold for extreme standardized values.
#'
#' @return A data frame with class \code{gazepoint_signal_quality}.
#' @export
compute_gazepoint_signal_quality <- function(data,
                                             signal_cols,
                                             group_cols = NULL,
                                             flatline_tolerance = 0,
                                             long_missing_run_threshold = 10,
                                             long_constant_run_threshold = 10,
                                             spike_z = 4,
                                             extreme_z = 4) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (missing(signal_cols) || length(signal_cols) == 0) {
    stop("`signal_cols` must contain at least one column name.", call. = FALSE)
  }

  signal_cols <- as.character(signal_cols)
  missing_signal_cols <- setdiff(signal_cols, names(data))
  if (length(missing_signal_cols) > 0) {
    stop(
      "`signal_cols` contains columns not found in `data`: ",
      paste(missing_signal_cols, collapse = ", "),
      call. = FALSE
    )
  }

  non_numeric <- signal_cols[!vapply(data[signal_cols], is.numeric, logical(1))]
  if (length(non_numeric) > 0) {
    stop(
      "All `signal_cols` must be numeric. Non-numeric columns: ",
      paste(non_numeric, collapse = ", "),
      call. = FALSE
    )
  }

  if (!is.null(group_cols)) {
    group_cols <- as.character(group_cols)
    missing_group_cols <- setdiff(group_cols, names(data))
    if (length(missing_group_cols) > 0) {
      stop(
        "`group_cols` contains columns not found in `data`: ",
        paste(missing_group_cols, collapse = ", "),
        call. = FALSE
      )
    }
  }

  if (!is.numeric(flatline_tolerance) || length(flatline_tolerance) != 1 ||
      is.na(flatline_tolerance) || flatline_tolerance < 0) {
    stop("`flatline_tolerance` must be a single non-negative number.", call. = FALSE)
  }

  if (!is.numeric(spike_z) || length(spike_z) != 1 || is.na(spike_z) || spike_z <= 0) {
    stop("`spike_z` must be a single positive number.", call. = FALSE)
  }

  if (!is.numeric(extreme_z) || length(extreme_z) != 1 || is.na(extreme_z) || extreme_z <= 0) {
    stop("`extreme_z` must be a single positive number.", call. = FALSE)
  }

  split_index <- if (is.null(group_cols) || length(group_cols) == 0) {
    factor(rep("all", nrow(data)))
  } else {
    interaction(data[group_cols], drop = TRUE, lex.order = TRUE)
  }

  pieces <- split(data, split_index, drop = TRUE)

  out <- vector("list", length(pieces) * length(signal_cols))
  k <- 0L

  for (piece_name in names(pieces)) {
    piece <- pieces[[piece_name]]

    group_values <- if (is.null(group_cols) || length(group_cols) == 0) {
      data.frame(segment_id = piece_name, stringsAsFactors = FALSE)
    } else {
      piece[1, group_cols, drop = FALSE]
    }

    for (signal in signal_cols) {
      k <- k + 1L
      metrics <- gazepoint_signal_quality_one(
        x = piece[[signal]],
        flatline_tolerance = flatline_tolerance,
        long_missing_run_threshold = long_missing_run_threshold,
        long_constant_run_threshold = long_constant_run_threshold,
        spike_z = spike_z,
        extreme_z = extreme_z
      )

      out[[k]] <- cbind(
        group_values,
        data.frame(signal = signal, stringsAsFactors = FALSE),
        metrics,
        stringsAsFactors = FALSE
      )
    }
  }

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  class(out) <- c("gazepoint_signal_quality", "data.frame")
  out
}

gazepoint_signal_quality_one <- function(x,
                                         flatline_tolerance,
                                         long_missing_run_threshold,
                                         long_constant_run_threshold,
                                         spike_z,
                                         extreme_z) {
  n_samples <- length(x)
  missing_flag <- is.na(x)
  finite_flag <- is.finite(x)

  n_missing <- sum(missing_flag)
  n_finite <- sum(finite_flag)

  finite_x <- x[finite_flag]

  if (n_samples == 0) {
    prop_missing <- NA_real_
    finite_prop <- NA_real_
  } else {
    prop_missing <- n_missing / n_samples
    finite_prop <- n_finite / n_samples
  }

  mean_value <- if (n_finite > 0) mean(finite_x) else NA_real_
  sd_value <- if (n_finite > 1) stats::sd(finite_x) else NA_real_
  median_value <- if (n_finite > 0) stats::median(finite_x) else NA_real_
  mad_value <- if (n_finite > 0) stats::mad(finite_x, constant = 1) else NA_real_
  min_value <- if (n_finite > 0) min(finite_x) else NA_real_
  max_value <- if (n_finite > 0) max(finite_x) else NA_real_
  range_value <- if (n_finite > 0) max_value - min_value else NA_real_
  iqr_value <- if (n_finite > 0) stats::IQR(finite_x) else NA_real_

  finite_adjacent <- is.finite(x[-1]) & is.finite(x[-length(x)])
  adjacent_diff <- abs(diff(x))
  constant_adjacent <- finite_adjacent & adjacent_diff <= flatline_tolerance

  flatline_prop <- if (length(adjacent_diff) == 0) {
    NA_real_
  } else {
    sum(constant_adjacent, na.rm = TRUE) / length(adjacent_diff)
  }

  long_missing_run <- gazepoint_max_run_length(missing_flag)

  constant_point_flag <- rep(FALSE, n_samples)
  if (n_samples > 1) {
    constant_point_flag[-1] <- constant_point_flag[-1] | constant_adjacent
    constant_point_flag[-n_samples] <- constant_point_flag[-n_samples] | constant_adjacent
  }
  long_constant_run <- gazepoint_max_run_length(constant_point_flag)

  contains_long_missing_run <- long_missing_run >= long_missing_run_threshold
  contains_long_constant_run <- long_constant_run >= long_constant_run_threshold

  spike_count <- gazepoint_spike_count(x, spike_z = spike_z)
  extreme_z_count <- gazepoint_extreme_z_count(x, extreme_z = extreme_z)

  data.frame(
    n_samples = n_samples,
    n_missing = n_missing,
    prop_missing = prop_missing,
    n_finite = n_finite,
    finite_prop = finite_prop,
    mean = mean_value,
    sd = sd_value,
    median = median_value,
    mad = mad_value,
    min = min_value,
    max = max_value,
    range = range_value,
    iqr = iqr_value,
    flatline_prop = flatline_prop,
    long_missing_run = long_missing_run,
    long_constant_run = long_constant_run,
    contains_long_missing_run = contains_long_missing_run,
    contains_long_constant_run = contains_long_constant_run,
    spike_count = spike_count,
    extreme_z_count = extreme_z_count,
    stringsAsFactors = FALSE
  )
}

gazepoint_max_run_length <- function(flag) {
  if (length(flag) == 0) {
    return(0L)
  }

  flag <- isTRUE(flag) | flag
  flag[is.na(flag)] <- FALSE

  runs <- rle(flag)
  if (!any(runs$values)) {
    return(0L)
  }

  max(runs$lengths[runs$values])
}

gazepoint_spike_count <- function(x, spike_z) {
  finite_x <- x[is.finite(x)]

  if (length(finite_x) < 3) {
    return(0L)
  }

  dx <- diff(finite_x)
  scale_value <- stats::mad(dx, constant = 1)

  if (!is.finite(scale_value) || scale_value == 0) {
    scale_value <- stats::sd(dx)
  }

  if (!is.finite(scale_value) || scale_value == 0) {
    return(0L)
  }

  sum(abs(dx - stats::median(dx)) / scale_value > spike_z, na.rm = TRUE)
}

gazepoint_extreme_z_count <- function(x, extreme_z) {
  finite_x <- x[is.finite(x)]

  if (length(finite_x) < 3) {
    return(0L)
  }

  scale_value <- stats::mad(finite_x, constant = 1)

  if (!is.finite(scale_value) || scale_value == 0) {
    scale_value <- stats::sd(finite_x)
  }

  if (!is.finite(scale_value) || scale_value == 0) {
    return(0L)
  }

  center_value <- stats::median(finite_x)
  sum(abs(finite_x - center_value) / scale_value > extreme_z, na.rm = TRUE)
}

#' Classify signal-quality rows using transparent threshold rules
#'
#' Applies user-visible threshold rules to a signal-quality table. The function
#' adds review labels and failing-rule descriptions. It does not remove data.
#'
#' @param quality A data frame returned by
#'   \code{compute_gazepoint_signal_quality()}.
#' @param rules Optional named list of threshold rules. Missing rules use the
#'   conservative defaults. Set a rule to \code{NULL} to remove it.
#'
#' @return A data frame with class
#'   \code{gazepoint_signal_quality_classification}.
#' @export
classify_gazepoint_signal_quality <- function(quality, rules = NULL) {
  if (!is.data.frame(quality)) {
    stop("`quality` must be a data frame.", call. = FALSE)
  }

  default_rules <- list(
    n_samples_review_below = 10,
    prop_missing_review_at_or_above = 0.20,
    prop_missing_exclude_at_or_above = 0.50,
    finite_prop_review_below = 0.80,
    finite_prop_exclude_below = 0.50,
    flatline_prop_review_at_or_above = 0.20,
    flatline_prop_exclude_at_or_above = 0.50,
    long_missing_run_review_at_or_above = 10,
    long_missing_run_exclude_at_or_above = 50,
    long_constant_run_review_at_or_above = 10,
    long_constant_run_exclude_at_or_above = 50,
    spike_count_review_at_or_above = 5,
    extreme_z_count_review_at_or_above = 5
  )

  rules <- gazepoint_modify_rules(default_rules, rules)
  gazepoint_validate_quality_rules(rules)

  labels <- character(nrow(quality))
  failing_rules <- character(nrow(quality))
  warnings <- character(nrow(quality))

  for (i in seq_len(nrow(quality))) {
    row <- quality[i, , drop = FALSE]
    row_result <- gazepoint_classify_quality_row(row, rules)

    labels[i] <- row_result$label
    failing_rules[i] <- paste(row_result$failing_rules, collapse = "; ")
    warnings[i] <- paste(row_result$warnings, collapse = "; ")
  }

  quality$quality_label <- labels
  quality$failing_rules <- failing_rules
  quality$quality_warnings <- warnings

  attr(quality, "rules") <- rules
  class(quality) <- c("gazepoint_signal_quality_classification", "data.frame")
  quality
}

gazepoint_modify_rules <- function(default_rules, user_rules) {
  if (is.null(user_rules)) {
    return(default_rules)
  }

  if (!is.list(user_rules) || is.null(names(user_rules)) || any(names(user_rules) == "")) {
    stop("`rules` must be a named list.", call. = FALSE)
  }

  out <- default_rules

  for (nm in names(user_rules)) {
    if (is.null(user_rules[[nm]])) {
      out[[nm]] <- NULL
    } else {
      out[[nm]] <- user_rules[[nm]]
    }
  }

  out
}

gazepoint_validate_quality_rules <- function(rules) {
  if (length(rules) == 0) {
    return(invisible(TRUE))
  }

  bad <- names(rules)[!vapply(rules, function(x) {
    is.numeric(x) && length(x) == 1 && is.finite(x)
  }, logical(1))]

  if (length(bad) > 0) {
    stop(
      "All quality rules must be single finite numeric values. Invalid rules: ",
      paste(bad, collapse = ", "),
      call. = FALSE
    )
  }

  invisible(TRUE)
}

gazepoint_classify_quality_row <- function(row, rules) {
  failing_review <- character(0)
  failing_exclude <- character(0)
  warnings <- character(0)

  check_rule <- function(column, rule_name, operator, label) {
    if (is.null(rules[[rule_name]])) {
      return(NULL)
    }

    if (!column %in% names(row)) {
      warnings <<- c(warnings, paste0("Metric unavailable: ", column))
      return(NULL)
    }

    value <- row[[column]][1]
    threshold <- rules[[rule_name]]

    if (is.na(value)) {
      warnings <<- c(warnings, paste0("Metric missing: ", column))
      return(NULL)
    }

    failed <- switch(
      operator,
      below = value < threshold,
      at_or_above = value >= threshold,
      stop("Unsupported operator.", call. = FALSE)
    )

    if (isTRUE(failed)) {
      label_text <- paste0(label, " [", column, " ", operator, " ", threshold, "]")

      if (grepl("exclude", rule_name, fixed = TRUE)) {
        failing_exclude <<- c(failing_exclude, label_text)
      } else {
        failing_review <<- c(failing_review, label_text)
      }
    }

    NULL
  }

  check_rule("n_samples", "n_samples_review_below", "below", "Low sample count")

  check_rule(
    "prop_missing",
    "prop_missing_review_at_or_above",
    "at_or_above",
    "Missingness review threshold"
  )
  check_rule(
    "prop_missing",
    "prop_missing_exclude_at_or_above",
    "at_or_above",
    "Missingness exclude-candidate threshold"
  )

  check_rule(
    "finite_prop",
    "finite_prop_review_below",
    "below",
    "Finite-value review threshold"
  )
  check_rule(
    "finite_prop",
    "finite_prop_exclude_below",
    "below",
    "Finite-value exclude-candidate threshold"
  )

  check_rule(
    "flatline_prop",
    "flatline_prop_review_at_or_above",
    "at_or_above",
    "Flatline review threshold"
  )
  check_rule(
    "flatline_prop",
    "flatline_prop_exclude_at_or_above",
    "at_or_above",
    "Flatline exclude-candidate threshold"
  )

  check_rule(
    "long_missing_run",
    "long_missing_run_review_at_or_above",
    "at_or_above",
    "Long missing-run review threshold"
  )
  check_rule(
    "long_missing_run",
    "long_missing_run_exclude_at_or_above",
    "at_or_above",
    "Long missing-run exclude-candidate threshold"
  )

  check_rule(
    "long_constant_run",
    "long_constant_run_review_at_or_above",
    "at_or_above",
    "Long constant-run review threshold"
  )
  check_rule(
    "long_constant_run",
    "long_constant_run_exclude_at_or_above",
    "at_or_above",
    "Long constant-run exclude-candidate threshold"
  )

  check_rule(
    "spike_count",
    "spike_count_review_at_or_above",
    "at_or_above",
    "Spike-count review threshold"
  )
  check_rule(
    "extreme_z_count",
    "extreme_z_count_review_at_or_above",
    "at_or_above",
    "Extreme-value review threshold"
  )

  label <- if (length(failing_exclude) > 0) {
    "exclude_candidate"
  } else if (length(failing_review) > 0) {
    "review"
  } else {
    "pass"
  }

  list(
    label = label,
    failing_rules = c(failing_exclude, failing_review),
    warnings = unique(warnings)
  )
}

#' Summarize signal-quality indicators
#'
#' Summarizes signal-quality rows by user-selected columns. The result is a
#' reporting table and does not imply automatic exclusion or interpretation.
#'
#' @param quality A data frame returned by
#'   \code{compute_gazepoint_signal_quality()} or
#'   \code{classify_gazepoint_signal_quality()}.
#' @param by Character vector of grouping columns. Defaults to \code{"signal"}.
#'
#' @return A data frame.
#' @export
summarize_gazepoint_signal_quality <- function(quality, by = "signal") {
  if (!is.data.frame(quality)) {
    stop("`quality` must be a data frame.", call. = FALSE)
  }

  by <- as.character(by)
  missing_by <- setdiff(by, names(quality))
  if (length(missing_by) > 0) {
    stop(
      "`by` contains columns not found in `quality`: ",
      paste(missing_by, collapse = ", "),
      call. = FALSE
    )
  }

  split_index <- interaction(quality[by], drop = TRUE, lex.order = TRUE)
  pieces <- split(quality, split_index, drop = TRUE)

  out <- lapply(pieces, function(piece) {
    group_values <- piece[1, by, drop = FALSE]

    result <- data.frame(
      n_segments = nrow(piece),
      n_samples_total = sum(piece$n_samples, na.rm = TRUE),
      n_samples_median = stats::median(piece$n_samples, na.rm = TRUE),
      prop_missing_mean = mean(piece$prop_missing, na.rm = TRUE),
      prop_missing_max = max(piece$prop_missing, na.rm = TRUE),
      finite_prop_mean = mean(piece$finite_prop, na.rm = TRUE),
      finite_prop_min = min(piece$finite_prop, na.rm = TRUE),
      flatline_prop_mean = mean(piece$flatline_prop, na.rm = TRUE),
      flatline_prop_max = max(piece$flatline_prop, na.rm = TRUE),
      long_missing_run_max = max(piece$long_missing_run, na.rm = TRUE),
      long_constant_run_max = max(piece$long_constant_run, na.rm = TRUE),
      spike_count_total = sum(piece$spike_count, na.rm = TRUE),
      extreme_z_count_total = sum(piece$extreme_z_count, na.rm = TRUE),
      stringsAsFactors = FALSE
    )

    if ("quality_label" %in% names(piece)) {
      result$pass_n <- sum(piece$quality_label == "pass", na.rm = TRUE)
      result$review_n <- sum(piece$quality_label == "review", na.rm = TRUE)
      result$exclude_candidate_n <- sum(piece$quality_label == "exclude_candidate", na.rm = TRUE)
    }

    cbind(group_values, result, stringsAsFactors = FALSE)
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL
  out
}

#' Plot signal-quality diagnostics
#'
#' Creates a lightweight ggplot diagnostic for signal-quality metrics or labels.
#' The plot is intended for quality control and audit reporting only.
#'
#' @param quality A data frame returned by
#'   \code{compute_gazepoint_signal_quality()} or
#'   \code{classify_gazepoint_signal_quality()}.
#' @param metric Metric to plot. Use \code{"quality_label"} for label counts.
#' @param x Optional x-axis column. If omitted, the function uses the first
#'   available column among participant, participant_id, trial, trial_id,
#'   segment, segment_id, session, or signal.
#' @param colour Optional colour/grouping column.
#' @param facet Optional faceting column. Defaults to \code{"signal"} when
#'   available.
#'
#' @return A ggplot object.
#' @export
plot_gazepoint_signal_quality <- function(quality,
                                          metric = "prop_missing",
                                          x = NULL,
                                          colour = NULL,
                                          facet = NULL) {
  if (!is.data.frame(quality)) {
    stop("`quality` must be a data frame.", call. = FALSE)
  }

  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    stop("Package `ggplot2` is required for plotting.", call. = FALSE)
  }

  metric <- as.character(metric)[1]

  if (!metric %in% names(quality)) {
    stop("`metric` was not found in `quality`.", call. = FALSE)
  }

  if (is.null(x)) {
    candidates <- c(
      "participant",
      "participant_id",
      "trial",
      "trial_id",
      "segment",
      "segment_id",
      "session",
      "signal"
    )
    x <- candidates[candidates %in% names(quality)][1]
  }

  if (is.na(x) || length(x) == 0) {
    stop("Could not infer `x`; please provide an x-axis column.", call. = FALSE)
  }

  if (!x %in% names(quality)) {
    stop("`x` was not found in `quality`.", call. = FALSE)
  }

  if (!is.null(colour) && !colour %in% names(quality)) {
    stop("`colour` was not found in `quality`.", call. = FALSE)
  }

  if (is.null(facet) && "signal" %in% names(quality) && x != "signal") {
    facet <- "signal"
  }

  if (!is.null(facet) && !facet %in% names(quality)) {
    stop("`facet` was not found in `quality`.", call. = FALSE)
  }

  if (metric == "quality_label") {
    plot_data <- as.data.frame(
      table(quality[[x]], quality[[metric]]),
      stringsAsFactors = FALSE
    )
    names(plot_data) <- c("x_value", "quality_label", "n")

    mapping <- do.call(
      ggplot2::aes,
      list(
        x = as.name("x_value"),
        y = as.name("n"),
        fill = as.name("quality_label")
      )
    )

    p <- ggplot2::ggplot(plot_data, mapping) +
      ggplot2::geom_col(position = "dodge") +
      ggplot2::labs(
        x = x,
        y = "Number of segments",
        fill = "Quality label"
      )
  } else {
    plot_data <- quality
    plot_data$x_value <- quality[[x]]
    plot_data$metric_value <- quality[[metric]]

    mapping_args <- list(
      x = as.name("x_value"),
      y = as.name("metric_value")
    )

    if (!is.null(colour)) {
      plot_data$colour_value <- quality[[colour]]
      mapping_args$colour <- as.name("colour_value")
    }

    if (!is.null(facet) && facet != x) {
      plot_data$facet_value <- quality[[facet]]
    }

    p <- ggplot2::ggplot(
      plot_data,
      do.call(ggplot2::aes, mapping_args)
    ) +
      ggplot2::geom_point(na.rm = TRUE) +
      ggplot2::labs(
        x = x,
        y = metric,
        colour = colour
      )

    if (!is.null(facet) && facet != x) {
      p <- p + ggplot2::facet_wrap(~facet_value)
    }
  }

  p +
    ggplot2::theme_minimal()
}
