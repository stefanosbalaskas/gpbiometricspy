#' Compute a heuristic QC quality index
#'
#' Combines user-selected numeric QC metrics into a transparent row-level
#' heuristic quality index. Metrics are range-scaled by default and combined
#' using user-supplied directions and weights. The result is intended for
#' quality-control summaries only. It does not remove data and does not make
#' physiological, psychological, diagnostic, or clinical claims.
#'
#' @param data A data frame.
#' @param metric_cols Character vector of numeric QC metric columns.
#' @param directions Direction for each metric. Use \code{"higher"} when higher
#'   values indicate better quality and \code{"lower"} when lower values indicate
#'   better quality. May be unnamed, named by metric, or length one.
#' @param weights Optional non-negative numeric weights. May be unnamed, named
#'   by metric, or length one.
#' @param index_col Name of the output quality-index column.
#' @param component_prefix Prefix used for metric component-score columns.
#' @param overwrite Logical. If \code{FALSE}, existing output columns are not
#'   overwritten.
#'
#' @return A data frame with class \code{gazepoint_quality_index}.
#' @export
compute_gazepoint_quality_index <- function(data,
                                            metric_cols,
                                            directions = NULL,
                                            weights = NULL,
                                            index_col = "quality_index",
                                            component_prefix = "quality_component_",
                                            overwrite = FALSE) {
  gpqc_check_data_frame(data)
  metric_cols <- gpqc_check_metric_cols(data, metric_cols)

  directions <- gpqc_prepare_directions(directions, metric_cols)
  weights <- gpqc_prepare_weights(weights, metric_cols)

  if (!is.character(index_col) || length(index_col) != 1 || is.na(index_col) || !nzchar(index_col)) {
    stop("`index_col` must be a single non-empty character string.", call. = FALSE)
  }

  if (!is.character(component_prefix) ||
      length(component_prefix) != 1 ||
      is.na(component_prefix) ||
      !nzchar(component_prefix)) {
    stop("`component_prefix` must be a single non-empty character string.", call. = FALSE)
  }

  gpqc_check_logical_one(overwrite, "overwrite")

  component_cols <- paste0(component_prefix, metric_cols)
  proposed_cols <- c(index_col, component_cols)
  existing <- intersect(proposed_cols, names(data))

  if (!overwrite && length(existing) > 0) {
    stop(
      "Output column(s) already exist: ",
      paste(existing, collapse = ", "),
      ". Choose different output names or set `overwrite = TRUE`.",
      call. = FALSE
    )
  }

  out <- data
  component_matrix <- matrix(
    NA_real_,
    nrow = nrow(data),
    ncol = length(metric_cols),
    dimnames = list(NULL, metric_cols)
  )

  for (metric in metric_cols) {
    x <- data[[metric]]
    scaled <- gpqc_range_score(x)

    if (directions[[metric]] == "lower") {
      scaled <- 1 - scaled
    }

    component_matrix[, metric] <- scaled
    out[[paste0(component_prefix, metric)]] <- scaled
  }

  weighted_sum <- rep(NA_real_, nrow(data))
  finite_weight <- rep(NA_real_, nrow(data))

  for (i in seq_len(nrow(data))) {
    finite <- is.finite(component_matrix[i, ])

    if (any(finite)) {
      weighted_sum[i] <- sum(component_matrix[i, finite] * weights[finite], na.rm = TRUE)
      finite_weight[i] <- sum(weights[finite], na.rm = TRUE)
    }
  }

  out[[index_col]] <- ifelse(
    is.finite(finite_weight) & finite_weight > 0,
    weighted_sum / finite_weight,
    NA_real_
  )

  attr(out, "quality_index_parameters") <- list(
    metric_cols = metric_cols,
    directions = directions,
    weights = weights,
    index_col = index_col,
    component_cols = component_cols
  )

  class(out) <- c("gazepoint_quality_index", class(out))
  out
}

#' Audit session comparability across QC metrics
#'
#' Aggregates selected QC metrics by session, participant, trial, or another
#' grouping unit, then flags unusual values using transparent z-score and/or IQR
#' rules. The function is intended for audit reporting only and does not imply
#' automatic exclusion.
#'
#' @param data A data frame.
#' @param metric_cols Character vector of numeric QC metric columns.
#' @param group_cols Optional character vector defining the session or analysis
#'   unit to compare.
#' @param method Outlier rule: \code{"z"}, \code{"iqr"}, or \code{"both"}.
#' @param z_threshold Absolute z-score threshold.
#' @param iqr_multiplier IQR multiplier used for Tukey-style fences.
#'
#' @return A list with class \code{gazepoint_session_comparability_audit}.
#' @export
audit_gazepoint_session_comparability <- function(data,
                                                  metric_cols,
                                                  group_cols = NULL,
                                                  method = c("both", "z", "iqr"),
                                                  z_threshold = 2,
                                                  iqr_multiplier = 1.5) {
  gpqc_check_data_frame(data)
  metric_cols <- gpqc_check_metric_cols(data, metric_cols)

  method <- match.arg(method)
  gpqc_check_positive_number(z_threshold, "z_threshold")
  gpqc_check_nonnegative_number(iqr_multiplier, "iqr_multiplier")

  group_cols <- gpqc_check_group_cols(data, group_cols)

  aggregated <- gpqc_aggregate_metrics(data, group_cols, metric_cols)

  flag_rows <- list()
  flag_i <- 0L

  for (metric in metric_cols) {
    x <- aggregated[[metric]]
    finite <- is.finite(x)

    metric_mean <- if (any(finite)) mean(x[finite]) else NA_real_
    metric_sd <- if (sum(finite) >= 2) stats::sd(x[finite]) else NA_real_
    metric_median <- if (any(finite)) stats::median(x[finite]) else NA_real_
    q1 <- if (sum(finite) >= 2) stats::quantile(x[finite], 0.25, names = FALSE, type = 7) else NA_real_
    q3 <- if (sum(finite) >= 2) stats::quantile(x[finite], 0.75, names = FALSE, type = 7) else NA_real_
    metric_iqr <- q3 - q1

    z <- rep(NA_real_, length(x))

    if (is.finite(metric_sd) && metric_sd > 0) {
      z[finite] <- (x[finite] - metric_mean) / metric_sd
    } else if (any(finite)) {
      z[finite] <- 0
    }

    iqr_low <- if (is.finite(metric_iqr)) q1 - iqr_multiplier * metric_iqr else NA_real_
    iqr_high <- if (is.finite(metric_iqr)) q3 + iqr_multiplier * metric_iqr else NA_real_

    z_low_flag <- method %in% c("z", "both") & is.finite(z) & z <= -abs(z_threshold)
    z_high_flag <- method %in% c("z", "both") & is.finite(z) & z >= abs(z_threshold)

    iqr_low_flag <- method %in% c("iqr", "both") &
      finite &
      is.finite(iqr_low) &
      x < iqr_low

    iqr_high_flag <- method %in% c("iqr", "both") &
      finite &
      is.finite(iqr_high) &
      x > iqr_high

    metric_missing <- !finite
    any_flag <- metric_missing | z_low_flag | z_high_flag | iqr_low_flag | iqr_high_flag

    for (i in seq_len(nrow(aggregated))) {
      flag_i <- flag_i + 1L
      flag_rows[[flag_i]] <- cbind(
        aggregated[i, gpqc_group_output_cols(aggregated, group_cols), drop = FALSE],
        data.frame(
          metric = metric,
          value = x[i],
          metric_mean = metric_mean,
          metric_sd = metric_sd,
          metric_median = metric_median,
          iqr_low = iqr_low,
          iqr_high = iqr_high,
          z_score = z[i],
          metric_missing = metric_missing[i],
          z_low_flag = z_low_flag[i],
          z_high_flag = z_high_flag[i],
          iqr_low_flag = iqr_low_flag[i],
          iqr_high_flag = iqr_high_flag[i],
          any_flag = any_flag[i],
          flag_reason = gpqc_comparability_reason(
            metric_missing[i],
            z_low_flag[i],
            z_high_flag[i],
            iqr_low_flag[i],
            iqr_high_flag[i]
          ),
          stringsAsFactors = FALSE
        )
      )
    }
  }

  flags <- do.call(rbind, flag_rows)
  rownames(flags) <- NULL

  summary <- gpqc_session_summary(flags, group_cols)

  result <- list(
    data = aggregated,
    flags = flags,
    summary = summary,
    parameters = list(
      metric_cols = metric_cols,
      group_cols = group_cols,
      method = method,
      z_threshold = z_threshold,
      iqr_multiplier = iqr_multiplier
    )
  )

  class(result) <- c("gazepoint_session_comparability_audit", "list")
  result
}

#' Summarize QC overview tables
#'
#' Creates a compact QC overview table from row-level or session-level QC data.
#' The summary can include counts of flags, mean/minimum quality index values,
#' and simple descriptive summaries for selected metrics.
#'
#' @param data A data frame.
#' @param group_cols Optional grouping columns.
#' @param quality_index_col Optional numeric quality-index column.
#' @param flag_cols Optional logical flag columns. If \code{NULL}, logical
#'   columns containing \code{"flag"} in their names are used when available.
#' @param metric_cols Optional numeric metric columns to summarize.
#'
#' @return A data frame with class \code{gazepoint_qc_overview}.
#' @export
summarize_gazepoint_qc_overview <- function(data,
                                            group_cols = NULL,
                                            quality_index_col = NULL,
                                            flag_cols = NULL,
                                            metric_cols = NULL) {
  gpqc_check_data_frame(data)
  group_cols <- gpqc_check_group_cols(data, group_cols)

  if (!is.null(quality_index_col)) {
    quality_index_col <- as.character(quality_index_col)[1]

    if (!quality_index_col %in% names(data)) {
      stop("`quality_index_col` was not found in `data`.", call. = FALSE)
    }

    if (!is.numeric(data[[quality_index_col]])) {
      stop("`quality_index_col` must refer to a numeric column.", call. = FALSE)
    }
  }

  if (is.null(flag_cols)) {
    flag_cols <- names(data)[
      vapply(data, is.logical, logical(1)) &
        grepl("flag", names(data), ignore.case = TRUE)
    ]
  } else {
    flag_cols <- as.character(flag_cols)
  }

  missing_flag_cols <- setdiff(flag_cols, names(data))

  if (length(missing_flag_cols) > 0) {
    stop(
      "`flag_cols` contains columns not found in `data`: ",
      paste(missing_flag_cols, collapse = ", "),
      call. = FALSE
    )
  }

  nonlogical_flags <- flag_cols[!vapply(data[flag_cols], is.logical, logical(1))]

  if (length(nonlogical_flags) > 0) {
    stop(
      "All `flag_cols` must be logical. Non-logical columns: ",
      paste(nonlogical_flags, collapse = ", "),
      call. = FALSE
    )
  }

  if (is.null(metric_cols)) {
    metric_cols <- character(0)
  } else {
    metric_cols <- gpqc_check_metric_cols(data, metric_cols)
  }

  split_index <- if (is.null(group_cols) || length(group_cols) == 0) {
    factor(rep("all", nrow(data)))
  } else {
    interaction(data[group_cols], drop = TRUE, lex.order = TRUE)
  }

  pieces <- split(data, split_index, drop = TRUE)

  rows <- lapply(names(pieces), function(piece_name) {
    piece <- pieces[[piece_name]]

    group_values <- if (is.null(group_cols) || length(group_cols) == 0) {
      data.frame(segment_id = piece_name, stringsAsFactors = FALSE)
    } else {
      piece[1, group_cols, drop = FALSE]
    }

    out <- cbind(
      group_values,
      data.frame(
        n_rows = nrow(piece),
        stringsAsFactors = FALSE
      )
    )

    if (length(flag_cols) > 0) {
      any_row_flag <- rep(FALSE, nrow(piece))

      for (flag in flag_cols) {
        flag_values <- piece[[flag]]
        flag_values[is.na(flag_values)] <- FALSE
        any_row_flag <- any_row_flag | flag_values
        out[[paste0("n_", flag)]] <- sum(flag_values, na.rm = TRUE)
      }

      out$n_flagged_rows <- sum(any_row_flag, na.rm = TRUE)
      out$prop_flagged_rows <- if (nrow(piece) > 0) {
        out$n_flagged_rows / nrow(piece)
      } else {
        NA_real_
      }
    } else {
      out$n_flagged_rows <- NA_integer_
      out$prop_flagged_rows <- NA_real_
    }

    if (!is.null(quality_index_col)) {
      q <- piece[[quality_index_col]]
      out$quality_index_mean <- if (any(is.finite(q))) mean(q[is.finite(q)]) else NA_real_
      out$quality_index_min <- if (any(is.finite(q))) min(q[is.finite(q)]) else NA_real_
      out$quality_index_max <- if (any(is.finite(q))) max(q[is.finite(q)]) else NA_real_
    }

    for (metric in metric_cols) {
      x <- piece[[metric]]
      finite <- is.finite(x)
      safe_metric <- make.names(metric)

      out[[paste0(safe_metric, "_mean")]] <- if (any(finite)) mean(x[finite]) else NA_real_
      out[[paste0(safe_metric, "_min")]] <- if (any(finite)) min(x[finite]) else NA_real_
      out[[paste0(safe_metric, "_max")]] <- if (any(finite)) max(x[finite]) else NA_real_
    }

    out
  })

  out <- do.call(rbind, rows)
  rownames(out) <- NULL
  class(out) <- c("gazepoint_qc_overview", class(out))
  out
}

gpqc_check_data_frame <- function(data) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (nrow(data) == 0) {
    stop("`data` must contain at least one row.", call. = FALSE)
  }

  invisible(TRUE)
}

gpqc_check_metric_cols <- function(data, metric_cols) {
  if (missing(metric_cols) || length(metric_cols) == 0) {
    stop("`metric_cols` must contain at least one column name.", call. = FALSE)
  }

  metric_cols <- as.character(metric_cols)
  missing_metric_cols <- setdiff(metric_cols, names(data))

  if (length(missing_metric_cols) > 0) {
    stop(
      "`metric_cols` contains columns not found in `data`: ",
      paste(missing_metric_cols, collapse = ", "),
      call. = FALSE
    )
  }

  non_numeric <- metric_cols[!vapply(data[metric_cols], is.numeric, logical(1))]

  if (length(non_numeric) > 0) {
    stop(
      "All `metric_cols` must be numeric. Non-numeric columns: ",
      paste(non_numeric, collapse = ", "),
      call. = FALSE
    )
  }

  metric_cols
}

gpqc_check_group_cols <- function(data, group_cols) {
  if (is.null(group_cols)) {
    return(NULL)
  }

  group_cols <- as.character(group_cols)
  missing_group_cols <- setdiff(group_cols, names(data))

  if (length(missing_group_cols) > 0) {
    stop(
      "`group_cols` contains columns not found in `data`: ",
      paste(missing_group_cols, collapse = ", "),
      call. = FALSE
    )
  }

  group_cols
}

gpqc_prepare_directions <- function(directions, metric_cols) {
  if (is.null(directions)) {
    directions <- rep("higher", length(metric_cols))
    names(directions) <- metric_cols
    return(directions)
  }

  direction_names <- names(directions)
  directions <- as.character(directions)
  names(directions) <- direction_names

  if (length(directions) == 1) {
    directions <- rep(directions, length(metric_cols))
  } else if (!is.null(names(directions)) && all(metric_cols %in% names(directions))) {
    directions <- directions[metric_cols]
  } else if (length(directions) != length(metric_cols)) {
    stop(
      "`directions` must have length one, length equal to `metric_cols`, or names matching `metric_cols`.",
      call. = FALSE
    )
  }

  if (is.null(names(directions))) {
    names(directions) <- metric_cols
  }

  invalid <- setdiff(directions, c("higher", "lower"))

  if (length(invalid) > 0) {
    stop("`directions` must contain only 'higher' or 'lower'.", call. = FALSE)
  }

  directions
}

gpqc_prepare_weights <- function(weights, metric_cols) {
  if (is.null(weights)) {
    weights <- rep(1, length(metric_cols))
    names(weights) <- metric_cols
    return(weights)
  }

  weight_names <- names(weights)
  weights <- as.numeric(weights)
  names(weights) <- weight_names

  if (length(weights) == 1) {
    weights <- rep(weights, length(metric_cols))
  } else if (!is.null(names(weights)) && all(metric_cols %in% names(weights))) {
    weights <- weights[metric_cols]
  } else if (length(weights) != length(metric_cols)) {
    stop(
      "`weights` must have length one, length equal to `metric_cols`, or names matching `metric_cols`.",
      call. = FALSE
    )
  }

  if (is.null(names(weights))) {
    names(weights) <- metric_cols
  }

  if (any(!is.finite(weights)) || any(weights < 0)) {
    stop("`weights` must be finite non-negative numbers.", call. = FALSE)
  }

  if (sum(weights) <= 0) {
    stop("At least one `weights` value must be positive.", call. = FALSE)
  }

  weights
}

gpqc_range_score <- function(x) {
  out <- rep(NA_real_, length(x))
  finite <- is.finite(x)

  if (!any(finite)) {
    return(out)
  }

  range_x <- range(x[finite], na.rm = TRUE)

  if (!is.finite(range_x[1]) || !is.finite(range_x[2]) || range_x[1] == range_x[2]) {
    out[finite] <- 0.5
    return(out)
  }

  out[finite] <- (x[finite] - range_x[1]) / (range_x[2] - range_x[1])
  out
}

gpqc_aggregate_metrics <- function(data, group_cols, metric_cols) {
  if (is.null(group_cols) || length(group_cols) == 0) {
    out <- data.frame(.gp_unit = seq_len(nrow(data)), stringsAsFactors = FALSE)
    out[metric_cols] <- data[metric_cols]
    return(out)
  }

  split_index <- interaction(data[group_cols], drop = TRUE, lex.order = TRUE)
  pieces <- split(data, split_index, drop = TRUE)

  rows <- lapply(pieces, function(piece) {
    group_values <- piece[1, group_cols, drop = FALSE]

    metric_values <- as.data.frame(
      stats::setNames(rep(list(NA_real_), length(metric_cols)), metric_cols),
      stringsAsFactors = FALSE
    )

    for (metric in metric_cols) {
      x <- piece[[metric]]
      finite <- is.finite(x)
      metric_values[[metric]] <- if (any(finite)) mean(x[finite]) else NA_real_
    }

    cbind(group_values, metric_values)
  })

  out <- do.call(rbind, rows)
  rownames(out) <- NULL
  out
}

gpqc_group_output_cols <- function(data, group_cols) {
  if (is.null(group_cols) || length(group_cols) == 0) {
    ".gp_unit"
  } else {
    group_cols
  }
}

gpqc_comparability_reason <- function(metric_missing,
                                      z_low_flag,
                                      z_high_flag,
                                      iqr_low_flag,
                                      iqr_high_flag) {
  reasons <- character(0)

  if (isTRUE(metric_missing)) {
    reasons <- c(reasons, "metric_missing")
  }

  if (isTRUE(z_low_flag)) {
    reasons <- c(reasons, "z_low")
  }

  if (isTRUE(z_high_flag)) {
    reasons <- c(reasons, "z_high")
  }

  if (isTRUE(iqr_low_flag)) {
    reasons <- c(reasons, "iqr_low")
  }

  if (isTRUE(iqr_high_flag)) {
    reasons <- c(reasons, "iqr_high")
  }

  paste(reasons, collapse = ";")
}

gpqc_session_summary <- function(flags, group_cols) {
  by_cols <- gpqc_group_output_cols(flags, group_cols)
  split_index <- interaction(flags[by_cols], drop = TRUE, lex.order = TRUE)
  pieces <- split(flags, split_index, drop = TRUE)

  rows <- lapply(pieces, function(piece) {
    group_values <- piece[1, by_cols, drop = FALSE]
    flagged <- piece$any_flag
    flagged[is.na(flagged)] <- FALSE
    missing <- piece$metric_missing
    missing[is.na(missing)] <- FALSE

    cbind(
      group_values,
      data.frame(
        n_metrics = nrow(piece),
        n_flagged_metrics = sum(flagged, na.rm = TRUE),
        prop_flagged_metrics = if (nrow(piece) > 0) sum(flagged, na.rm = TRUE) / nrow(piece) else NA_real_,
        n_missing_metrics = sum(missing, na.rm = TRUE),
        flagged_metrics = paste(piece$metric[flagged], collapse = ","),
        flag_reasons = paste(piece$flag_reason[flagged], collapse = ";"),
        stringsAsFactors = FALSE
      )
    )
  })

  out <- do.call(rbind, rows)
  rownames(out) <- NULL
  out
}

gpqc_check_positive_number <- function(x, name) {
  if (!is.numeric(x) || length(x) != 1 || !is.finite(x) || x <= 0) {
    stop("`", name, "` must be a single positive number.", call. = FALSE)
  }

  invisible(TRUE)
}

gpqc_check_nonnegative_number <- function(x, name) {
  if (!is.numeric(x) || length(x) != 1 || !is.finite(x) || x < 0) {
    stop("`", name, "` must be a single non-negative number.", call. = FALSE)
  }

  invisible(TRUE)
}

gpqc_check_logical_one <- function(x, name) {
  if (!is.logical(x) || length(x) != 1 || is.na(x)) {
    stop("`", name, "` must be TRUE or FALSE.", call. = FALSE)
  }

  invisible(TRUE)
}
