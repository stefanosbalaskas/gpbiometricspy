#' Detect likely blink or pupil-dropout samples
#'
#' Detects likely blink or pupil-dropout samples in Gazepoint pupil columns using
#' transparent, rule-based criteria. The function flags non-finite values,
#' values outside a plausible pupil range, and optionally large sample-to-sample
#' changes. It does not infer attention, cognition, arousal, emotion, or visual
#' processing from the pupil signal.
#'
#' @param data A data frame containing Gazepoint pupil data.
#' @param pupil_cols Character vector naming pupil columns. If `NULL`, numeric
#'   columns whose names contain `"pupil"` are used.
#' @param id_cols Optional character vector naming grouping columns. Blink
#'   detection based on sample-to-sample change is applied within groups.
#' @param min_pupil Minimum plausible pupil value. Values less than or equal to
#'   this threshold are flagged. Use `NULL` to disable the lower-bound rule.
#' @param max_pupil Maximum plausible pupil value. Values greater than or equal
#'   to this threshold are flagged. Use `NULL` to disable the upper-bound rule.
#' @param change_threshold Optional maximum plausible absolute sample-to-sample
#'   change. Use `NULL` to disable the change rule.
#' @param extend_samples Non-negative integer. Number of neighbouring samples on
#'   each side of a detected blink/dropout to also flag.
#' @param mask Logical. If `TRUE`, add cleaned pupil columns with detected
#'   blink/dropout samples set to `NA`.
#' @param flag_suffix Suffix appended to pupil-column names for logical flag
#'   columns.
#' @param clean_suffix Suffix appended to pupil-column names for cleaned columns
#'   when `mask = TRUE`.
#'
#' @return A list with the processed data, a summary table, rule settings, and
#'   warnings. The object has class `"gazepoint_blink_audit"`.
#' @export
#'
#' @examples
#' d <- data.frame(
#'   participant = rep("P01", 8),
#'   time = seq_len(8),
#'   pupil_left = c(3.1, 3.2, 0, 3.2, 8.5, 3.1, NA, 3.0)
#' )
#' detect_gazepoint_blinks(d, pupil_cols = "pupil_left")
detect_gazepoint_blinks <- function(data,
                                    pupil_cols = NULL,
                                    id_cols = NULL,
                                    min_pupil = 0,
                                    max_pupil = Inf,
                                    change_threshold = NULL,
                                    extend_samples = 0L,
                                    mask = TRUE,
                                    flag_suffix = "_blink_flag",
                                    clean_suffix = "_blink_clean") {
  .gp_pqr_assert_data_frame(data)
  pupil_cols <- .gp_pqr_resolve_pupil_cols(data, pupil_cols)

  id_cols <- .gp_pqr_optional_existing_cols(data, id_cols, what = "id_cols")
  extend_samples <- .gp_pqr_nonnegative_integer(extend_samples, "extend_samples")
  mask <- .gp_pqr_scalar_logical(mask, "mask")

  if (!is.null(min_pupil)) {
    min_pupil <- .gp_pqr_scalar_numeric(min_pupil, "min_pupil")
  }
  if (!is.null(max_pupil)) {
    max_pupil <- .gp_pqr_scalar_numeric(max_pupil, "max_pupil")
  }
  if (!is.null(change_threshold)) {
    change_threshold <- .gp_pqr_scalar_numeric(change_threshold, "change_threshold")
    if (!is.finite(change_threshold) || change_threshold < 0) {
      stop("`change_threshold` must be a non-negative finite number.", call. = FALSE)
    }
  }

  out <- data
  groups <- .gp_pqr_group_rows(out, id_cols)

  summary <- lapply(pupil_cols, function(col) {
    x <- out[[col]]
    flag <- rep(FALSE, length(x))

    flag <- flag | !is.finite(x)

    if (!is.null(min_pupil)) {
      flag <- flag | (!is.na(x) & x <= min_pupil)
    }

    if (!is.null(max_pupil) && is.finite(max_pupil)) {
      flag <- flag | (!is.na(x) & x >= max_pupil)
    }

    if (!is.null(change_threshold)) {
      change_flag <- rep(FALSE, length(x))
      for (idx in groups) {
        if (length(idx) <= 1L) {
          next
        }
        dx <- c(NA_real_, abs(diff(x[idx])))
        change_flag[idx] <- !is.na(dx) & dx >= change_threshold
      }
      flag <- flag | change_flag
    }

    if (extend_samples > 0L && any(flag, na.rm = TRUE)) {
      flag <- .gp_pqr_extend_flags(flag, groups, extend_samples)
    }

    flag_col <- paste0(col, flag_suffix)
    out[[flag_col]] <<- flag

    if (mask) {
      clean_col <- paste0(col, clean_suffix)
      cleaned <- x
      cleaned[flag] <- NA_real_
      out[[clean_col]] <<- cleaned
    }

    data.frame(
      pupil_col = col,
      n_samples = length(x),
      n_flagged = sum(flag, na.rm = TRUE),
      prop_flagged = if (length(x) > 0L) sum(flag, na.rm = TRUE) / length(x) else NA_real_,
      stringsAsFactors = FALSE
    )
  })

  summary <- do.call(rbind, summary)

  warnings <- character()
  if (any(summary$prop_flagged > 0.50, na.rm = TRUE)) {
    warnings <- c(
      warnings,
      "More than 50% of samples were flagged in at least one pupil column."
    )
  }

  structure(
    list(
      data = out,
      summary = summary,
      settings = list(
        pupil_cols = pupil_cols,
        id_cols = id_cols,
        min_pupil = min_pupil,
        max_pupil = max_pupil,
        change_threshold = change_threshold,
        extend_samples = extend_samples,
        mask = mask,
        flag_suffix = flag_suffix,
        clean_suffix = clean_suffix
      ),
      warnings = warnings
    ),
    class = c("gazepoint_blink_audit", "gazepoint_qc_object")
  )
}


#' Smooth Gazepoint pupil columns
#'
#' Applies a simple centred moving-average smoother to Gazepoint pupil columns.
#' The function is intended for transparent preprocessing and quality-control
#' workflows. It does not interpolate long missing gaps and does not interpret
#' pupil values as psychological or physiological states.
#'
#' @param data A data frame containing Gazepoint pupil data.
#' @param pupil_cols Character vector naming pupil columns. If `NULL`, numeric
#'   columns whose names contain `"pupil"` are used.
#' @param id_cols Optional character vector naming grouping columns. Smoothing is
#'   applied within groups.
#' @param window Positive odd integer giving the moving-average window size.
#' @param suffix Suffix appended to smoothed pupil-column names.
#' @param min_nonmissing Minimum number of non-missing values required inside a
#'   window to compute a smoothed value.
#'
#' @return A list with the processed data, a summary table, and settings. The
#'   object has class `"gazepoint_pupil_smoothing"`.
#' @export
#'
#' @examples
#' d <- data.frame(
#'   participant = rep("P01", 6),
#'   pupil_left = c(3.0, 3.2, 3.4, NA, 3.3, 3.1)
#' )
#' smooth_gazepoint_pupil(d, pupil_cols = "pupil_left", window = 3)
smooth_gazepoint_pupil <- function(data,
                                   pupil_cols = NULL,
                                   id_cols = NULL,
                                   window = 5L,
                                   suffix = "_smooth",
                                   min_nonmissing = 1L) {
  .gp_pqr_assert_data_frame(data)
  pupil_cols <- .gp_pqr_resolve_pupil_cols(data, pupil_cols)
  id_cols <- .gp_pqr_optional_existing_cols(data, id_cols, what = "id_cols")

  window <- .gp_pqr_positive_integer(window, "window")
  if (window %% 2L == 0L) {
    stop("`window` must be an odd integer.", call. = FALSE)
  }

  min_nonmissing <- .gp_pqr_positive_integer(min_nonmissing, "min_nonmissing")
  if (min_nonmissing > window) {
    stop("`min_nonmissing` cannot be larger than `window`.", call. = FALSE)
  }

  out <- data
  groups <- .gp_pqr_group_rows(out, id_cols)

  summary <- lapply(pupil_cols, function(col) {
    smoothed <- rep(NA_real_, nrow(out))

    for (idx in groups) {
      smoothed[idx] <- .gp_pqr_moving_average(
        out[[col]][idx],
        window = window,
        min_nonmissing = min_nonmissing
      )
    }

    smooth_col <- paste0(col, suffix)
    out[[smooth_col]] <<- smoothed

    data.frame(
      pupil_col = col,
      output_col = smooth_col,
      n_samples = length(smoothed),
      n_smoothed_nonmissing = sum(!is.na(smoothed)),
      stringsAsFactors = FALSE
    )
  })

  summary <- do.call(rbind, summary)

  structure(
    list(
      data = out,
      summary = summary,
      settings = list(
        pupil_cols = pupil_cols,
        id_cols = id_cols,
        window = window,
        suffix = suffix,
        min_nonmissing = min_nonmissing
      )
    ),
    class = c("gazepoint_pupil_smoothing", "gazepoint_qc_object")
  )
}


#' Plot missingness across Gazepoint signal columns
#'
#' Creates a heatmap-style plot showing missing and observed samples across
#' selected Gazepoint signal columns. This is a descriptive quality-control
#' display and should not be interpreted as evidence of psychological or
#' physiological state.
#'
#' @param data A data frame.
#' @param cols Character vector naming columns to inspect. If `NULL`, numeric
#'   columns are used.
#' @param time_col Optional column used for the x-axis. If `NULL`, row number is
#'   used.
#' @param id_col Optional participant/session column used for faceting.
#' @param max_points Maximum number of rows to plot. Larger data sets are evenly
#'   down-sampled for display only.
#'
#' @return A `ggplot` object.
#' @export
#'
#' @examples
#' d <- data.frame(
#'   time = 1:5,
#'   pupil_left = c(3, NA, 3.1, 3.2, NA),
#'   eda = c(1, 1.1, NA, 1.2, 1.3)
#' )
#' plot_gazepoint_missingness(d, cols = c("pupil_left", "eda"), time_col = "time")
plot_gazepoint_missingness <- function(data,
                                       cols = NULL,
                                       time_col = NULL,
                                       id_col = NULL,
                                       max_points = 5000L) {
  .gp_pqr_assert_data_frame(data)

  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    stop("Package `ggplot2` is required for plotting.", call. = FALSE)
  }

  if (is.null(cols)) {
    cols <- names(data)[vapply(data, is.numeric, logical(1))]
  }
  cols <- .gp_pqr_required_existing_cols(data, cols, what = "cols")

  if (!is.null(time_col)) {
    time_col <- .gp_pqr_required_existing_cols(data, time_col, what = "time_col")
  }
  if (!is.null(id_col)) {
    id_col <- .gp_pqr_required_existing_cols(data, id_col, what = "id_col")
  }

  max_points <- .gp_pqr_positive_integer(max_points, "max_points")

  rows <- seq_len(nrow(data))
  if (length(rows) > max_points) {
    rows <- unique(round(seq(1, nrow(data), length.out = max_points)))
  }

  x_values <- if (is.null(time_col)) {
    rows
  } else {
    data[[time_col]][rows]
  }

  plot_data <- do.call(
    rbind,
    lapply(cols, function(col) {
      data.frame(
        .row = rows,
        .x = x_values,
        signal = col,
        missing = is.na(data[[col]][rows]),
        stringsAsFactors = FALSE
      )
    })
  )

  if (!is.null(id_col)) {
    id_values <- data[[id_col]][rows]
    plot_data[[id_col]] <- rep(id_values, times = length(cols))
  }

  p <- ggplot2::ggplot(
    plot_data,
    ggplot2::aes(x = .data$.x, y = .data$signal, fill = .data$missing)
  ) +
    ggplot2::geom_tile() +
    ggplot2::labs(
      x = if (is.null(time_col)) "Row index" else time_col,
      y = "Signal column",
      fill = "Missing",
      title = "Gazepoint signal missingness"
    ) +
    ggplot2::theme_minimal()

  if (!is.null(id_col)) {
    p <- p + ggplot2::facet_wrap(stats::as.formula(paste("~", id_col)))
  }

  p
}


#' Validate Gazepoint metadata and required columns
#'
#' Performs transparent metadata checks for Gazepoint workflow data frames. The
#' function checks required columns, optional expected columns, missing IDs,
#' duplicate key rows, and time ordering within groups. It returns a structured
#' report rather than modifying the data.
#'
#' @param data A data frame.
#' @param required_cols Character vector of required columns.
#' @param expected_cols Optional character vector of expected but non-fatal
#'   columns.
#' @param id_cols Optional character vector naming participant/session/trial
#'   identifiers.
#' @param time_col Optional time column used for ordering checks.
#' @param unique_cols Optional character vector defining a row-level key that
#'   should be unique.
#' @param allow_missing_ids Logical. If `FALSE`, missing values in `id_cols` are
#'   reported as problems.
#'
#' @return A list containing status, problems, warnings, and a summary table. The
#'   object has class `"gazepoint_metadata_validation"`.
#' @export
#'
#' @examples
#' d <- data.frame(
#'   participant = c("P01", "P01"),
#'   time = c(1, 2),
#'   pupil_left = c(3.1, 3.2)
#' )
#' validate_gazepoint_metadata(
#'   d,
#'   required_cols = c("participant", "time"),
#'   id_cols = "participant",
#'   time_col = "time"
#' )
validate_gazepoint_metadata <- function(data,
                                        required_cols = character(),
                                        expected_cols = character(),
                                        id_cols = NULL,
                                        time_col = NULL,
                                        unique_cols = NULL,
                                        allow_missing_ids = FALSE) {
  .gp_pqr_assert_data_frame(data)

  required_cols <- .gp_pqr_character(required_cols, "required_cols", allow_null = FALSE)
  expected_cols <- .gp_pqr_character(expected_cols, "expected_cols", allow_null = FALSE)
  id_cols <- .gp_pqr_character(id_cols, "id_cols", allow_null = TRUE)
  time_col <- .gp_pqr_character(time_col, "time_col", allow_null = TRUE)
  unique_cols <- .gp_pqr_character(unique_cols, "unique_cols", allow_null = TRUE)
  allow_missing_ids <- .gp_pqr_scalar_logical(allow_missing_ids, "allow_missing_ids")

  problems <- character()
  warnings <- character()

  missing_required <- setdiff(required_cols, names(data))
  if (length(missing_required) > 0L) {
    problems <- c(
      problems,
      paste0("Missing required columns: ", paste(missing_required, collapse = ", "))
    )
  }

  missing_expected <- setdiff(expected_cols, names(data))
  if (length(missing_expected) > 0L) {
    warnings <- c(
      warnings,
      paste0("Missing expected columns: ", paste(missing_expected, collapse = ", "))
    )
  }

  existing_id_cols <- intersect(id_cols, names(data))
  missing_id_cols <- setdiff(id_cols, names(data))
  if (length(missing_id_cols) > 0L) {
    problems <- c(
      problems,
      paste0("Missing ID columns: ", paste(missing_id_cols, collapse = ", "))
    )
  }

  if (!allow_missing_ids && length(existing_id_cols) > 0L) {
    for (col in existing_id_cols) {
      if (any(is.na(data[[col]]) | data[[col]] == "")) {
        problems <- c(problems, paste0("Missing values detected in ID column `", col, "`."))
      }
    }
  }

  if (!is.null(time_col)) {
    if (length(time_col) != 1L) {
      problems <- c(problems, "`time_col` must contain exactly one column name.")
    } else if (!time_col %in% names(data)) {
      problems <- c(problems, paste0("Missing time column: ", time_col))
    } else {
      groups <- .gp_pqr_group_rows(data, existing_id_cols)
      bad_groups <- 0L
      for (idx in groups) {
        tx <- data[[time_col]][idx]
        if (length(tx) > 1L && any(diff(tx) < 0, na.rm = TRUE)) {
          bad_groups <- bad_groups + 1L
        }
      }
      if (bad_groups > 0L) {
        problems <- c(
          problems,
          paste0("Time column `", time_col, "` is not monotonically increasing in ",
                 bad_groups, " group(s).")
        )
      }
    }
  }

  if (!is.null(unique_cols)) {
    missing_unique <- setdiff(unique_cols, names(data))
    if (length(missing_unique) > 0L) {
      problems <- c(
        problems,
        paste0("Missing unique-key columns: ", paste(missing_unique, collapse = ", "))
      )
    } else if (length(unique_cols) > 0L) {
      key <- do.call(paste, c(data[unique_cols], sep = "\r"))
      n_duplicate <- sum(duplicated(key))
      if (n_duplicate > 0L) {
        problems <- c(
          problems,
          paste0("Duplicate rows detected for unique key `",
                 paste(unique_cols, collapse = " + "), "`: ", n_duplicate)
        )
      }
    }
  }

  summary <- data.frame(
    n_rows = nrow(data),
    n_columns = ncol(data),
    n_required_columns = length(required_cols),
    n_missing_required = length(missing_required),
    n_expected_columns = length(expected_cols),
    n_missing_expected = length(missing_expected),
    n_problems = length(problems),
    n_warnings = length(warnings),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      status = if (length(problems) == 0L) "pass" else "review",
      summary = summary,
      problems = problems,
      warnings = warnings,
      settings = list(
        required_cols = required_cols,
        expected_cols = expected_cols,
        id_cols = id_cols,
        time_col = time_col,
        unique_cols = unique_cols,
        allow_missing_ids = allow_missing_ids
      )
    ),
    class = c("gazepoint_metadata_validation", "gazepoint_qc_object")
  )
}


#' @export
print.gazepoint_blink_audit <- function(x, ...) {
  cat("Gazepoint blink/dropout audit\n")
  print(x$summary, row.names = FALSE)
  if (length(x$warnings) > 0L) {
    cat("\nWarnings:\n")
    cat(paste0("- ", x$warnings, collapse = "\n"), "\n")
  }
  invisible(x)
}


#' @export
print.gazepoint_pupil_smoothing <- function(x, ...) {
  cat("Gazepoint pupil smoothing\n")
  print(x$summary, row.names = FALSE)
  invisible(x)
}


#' @export
print.gazepoint_metadata_validation <- function(x, ...) {
  cat("Gazepoint metadata validation: ", x$status, "\n", sep = "")
  print(x$summary, row.names = FALSE)

  if (length(x$problems) > 0L) {
    cat("\nProblems:\n")
    cat(paste0("- ", x$problems, collapse = "\n"), "\n")
  }

  if (length(x$warnings) > 0L) {
    cat("\nWarnings:\n")
    cat(paste0("- ", x$warnings, collapse = "\n"), "\n")
  }

  invisible(x)
}


.gp_pqr_assert_data_frame <- function(data) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }
  invisible(TRUE)
}


.gp_pqr_character <- function(x, name, allow_null = TRUE) {
  if (is.null(x)) {
    if (allow_null) {
      return(NULL)
    }
    return(character())
  }

  if (!is.character(x)) {
    stop("`", name, "` must be a character vector.", call. = FALSE)
  }

  x
}


.gp_pqr_required_existing_cols <- function(data, cols, what) {
  cols <- .gp_pqr_character(cols, what, allow_null = FALSE)
  if (length(cols) == 0L) {
    stop("`", what, "` must contain at least one column name.", call. = FALSE)
  }

  missing <- setdiff(cols, names(data))
  if (length(missing) > 0L) {
    stop(
      "`", what, "` contains columns not found in `data`: ",
      paste(missing, collapse = ", "),
      call. = FALSE
    )
  }

  cols
}


.gp_pqr_optional_existing_cols <- function(data, cols, what) {
  cols <- .gp_pqr_character(cols, what, allow_null = TRUE)
  if (is.null(cols) || length(cols) == 0L) {
    return(character())
  }

  missing <- setdiff(cols, names(data))
  if (length(missing) > 0L) {
    stop(
      "`", what, "` contains columns not found in `data`: ",
      paste(missing, collapse = ", "),
      call. = FALSE
    )
  }

  cols
}


.gp_pqr_resolve_pupil_cols <- function(data, pupil_cols) {
  if (is.null(pupil_cols)) {
    pupil_cols <- names(data)[
      grepl("pupil", names(data), ignore.case = TRUE) &
        vapply(data, is.numeric, logical(1))
    ]
  }

  pupil_cols <- .gp_pqr_required_existing_cols(data, pupil_cols, "pupil_cols")

  non_numeric <- pupil_cols[!vapply(data[pupil_cols], is.numeric, logical(1))]
  if (length(non_numeric) > 0L) {
    stop(
      "`pupil_cols` must refer to numeric columns. Non-numeric columns: ",
      paste(non_numeric, collapse = ", "),
      call. = FALSE
    )
  }

  pupil_cols
}


.gp_pqr_group_rows <- function(data, id_cols = character()) {
  if (length(id_cols) == 0L) {
    return(list(seq_len(nrow(data))))
  }

  key <- do.call(paste, c(data[id_cols], sep = "\r"))
  split(seq_len(nrow(data)), key, drop = TRUE)
}


.gp_pqr_extend_flags <- function(flag, groups, extend_samples) {
  extended <- flag

  for (idx in groups) {
    local_flag <- flag[idx]
    flagged <- which(local_flag)

    if (length(flagged) == 0L) {
      next
    }

    for (pos in flagged) {
      span <- seq.int(
        max(1L, pos - extend_samples),
        min(length(local_flag), pos + extend_samples)
      )
      extended[idx[span]] <- TRUE
    }
  }

  extended
}


.gp_pqr_moving_average <- function(x, window, min_nonmissing) {
  n <- length(x)
  out <- rep(NA_real_, n)

  if (n == 0L) {
    return(out)
  }

  half <- floor(window / 2L)

  for (i in seq_len(n)) {
    lo <- max(1L, i - half)
    hi <- min(n, i + half)
    values <- x[lo:hi]
    if (sum(!is.na(values)) >= min_nonmissing) {
      out[i] <- mean(values, na.rm = TRUE)
    }
  }

  out
}


.gp_pqr_scalar_logical <- function(x, name) {
  if (!is.logical(x) || length(x) != 1L || is.na(x)) {
    stop("`", name, "` must be a single TRUE/FALSE value.", call. = FALSE)
  }

  x
}


.gp_pqr_scalar_numeric <- function(x, name) {
  if (!is.numeric(x) || length(x) != 1L || is.na(x)) {
    stop("`", name, "` must be a single numeric value.", call. = FALSE)
  }

  x
}


.gp_pqr_positive_integer <- function(x, name) {
  if (!is.numeric(x) || length(x) != 1L || is.na(x)) {
    stop("`", name, "` must be a single positive integer.", call. = FALSE)
  }

  x <- as.integer(x)

  if (x < 1L) {
    stop("`", name, "` must be a positive integer.", call. = FALSE)
  }

  x
}


.gp_pqr_nonnegative_integer <- function(x, name) {
  if (!is.numeric(x) || length(x) != 1L || is.na(x)) {
    stop("`", name, "` must be a single non-negative integer.", call. = FALSE)
  }

  x <- as.integer(x)

  if (x < 0L) {
    stop("`", name, "` must be a non-negative integer.", call. = FALSE)
  }

  x
}
