#' Audit beat or IBI sequences
#'
#' Flags short, long, non-finite, duplicate-time, and abrupt-change intervals in
#' beat or inter-beat-interval data. The function is intended for quality
#' control and audit reporting only. It does not remove beats, modify data, or
#' make physiological, psychological, diagnostic, or clinical claims.
#'
#' @param data A data frame.
#' @param ibi_col Optional numeric inter-beat-interval column. If omitted,
#'   intervals are derived from \code{beat_time_col}.
#' @param beat_time_col Optional numeric beat-time column. Required when
#'   \code{ibi_col} is omitted. When supplied, rows are ordered by beat time
#'   within each group and duplicate-time checks are enabled.
#' @param group_cols Optional character vector of grouping columns, such as
#'   participant, session, trial, or condition.
#' @param min_ibi Minimum plausible interval, in the same units as the IBI
#'   column or beat-time column.
#' @param max_ibi Maximum plausible interval, in the same units as the IBI
#'   column or beat-time column.
#' @param duplicate_tolerance Maximum adjacent beat-time difference treated as a
#'   duplicate-time flag. Ignored when \code{beat_time_col} is \code{NULL}.
#' @param max_relative_change Optional relative-change threshold for flagging
#'   abrupt adjacent IBI changes. If \code{NULL}, this check is skipped.
#'
#' @return A list with class \code{gazepoint_beat_audit}, containing beat-level
#'   flags, group summaries, and parameters.
#' @export
audit_gazepoint_beats <- function(data,
                                  ibi_col = NULL,
                                  beat_time_col = NULL,
                                  group_cols = NULL,
                                  min_ibi = 300,
                                  max_ibi = 2000,
                                  duplicate_tolerance = 0,
                                  max_relative_change = NULL) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (nrow(data) == 0) {
    stop("`data` must contain at least one row.", call. = FALSE)
  }

  ibi_col <- gpbeat_optional_col(ibi_col)
  beat_time_col <- gpbeat_optional_col(beat_time_col)

  if (is.null(ibi_col) && is.null(beat_time_col)) {
    stop(
      "Provide `ibi_col`, `beat_time_col`, or both.",
      call. = FALSE
    )
  }

  if (!is.null(ibi_col)) {
    gpbeat_check_existing_numeric_col(data, ibi_col, "ibi_col")
  }

  if (!is.null(beat_time_col)) {
    gpbeat_check_existing_numeric_col(data, beat_time_col, "beat_time_col")
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

  gpbeat_check_positive_number(min_ibi, "min_ibi")
  gpbeat_check_positive_number(max_ibi, "max_ibi")
  gpbeat_check_nonnegative_number(duplicate_tolerance, "duplicate_tolerance")

  if (min_ibi >= max_ibi) {
    stop("`min_ibi` must be smaller than `max_ibi`.", call. = FALSE)
  }

  if (!is.null(max_relative_change)) {
    gpbeat_check_positive_number(max_relative_change, "max_relative_change")
  }

  working <- data
  working$.gp_original_row <- seq_len(nrow(working))

  split_index <- if (is.null(group_cols) || length(group_cols) == 0) {
    factor(rep("all", nrow(working)))
  } else {
    interaction(working[group_cols], drop = TRUE, lex.order = TRUE)
  }

  pieces <- split(working, split_index, drop = TRUE)

  beat_rows <- list()
  summary_rows <- list()
  beat_i <- 0L
  summary_i <- 0L

  for (piece_name in names(pieces)) {
    piece <- pieces[[piece_name]]

    if (!is.null(beat_time_col)) {
      piece <- piece[order(piece[[beat_time_col]], na.last = TRUE), , drop = FALSE]
    }

    group_values <- gpbeat_group_values(piece, group_cols, piece_name)
    n <- nrow(piece)

    ibi <- if (!is.null(ibi_col)) {
      piece[[ibi_col]]
    } else {
      c(NA_real_, diff(piece[[beat_time_col]]))
    }

    has_interval <- rep(TRUE, n)

    if (is.null(ibi_col) && !is.null(beat_time_col) && n > 0) {
      has_interval[1] <- FALSE
    }

    nonfinite_ibi <- has_interval & !is.finite(ibi)
    short_ibi <- has_interval & is.finite(ibi) & ibi < min_ibi
    long_ibi <- has_interval & is.finite(ibi) & ibi > max_ibi

    duplicate_time <- rep(FALSE, n)

    if (!is.null(beat_time_col) && n > 1) {
      beat_time <- piece[[beat_time_col]]
      duplicate_time[-1] <- is.finite(beat_time[-1]) &
        is.finite(beat_time[-n]) &
        abs(beat_time[-1] - beat_time[-n]) <= duplicate_tolerance
    }

    abrupt_change <- rep(FALSE, n)

    if (!is.null(max_relative_change) && n > 1) {
      previous_ibi <- c(NA_real_, ibi[-n])
      abrupt_change <- has_interval &
        is.finite(ibi) &
        is.finite(previous_ibi) &
        previous_ibi > 0 &
        abs(ibi - previous_ibi) / previous_ibi > max_relative_change
    }

    any_flag <- nonfinite_ibi |
      short_ibi |
      long_ibi |
      duplicate_time |
      abrupt_change

    flag_reason <- gpbeat_flag_reasons(
      nonfinite_ibi = nonfinite_ibi,
      short_ibi = short_ibi,
      long_ibi = long_ibi,
      duplicate_time = duplicate_time,
      abrupt_change = abrupt_change
    )

    beat_table <- cbind(
      group_values[rep(1, n), , drop = FALSE],
      data.frame(
        beat_index = seq_len(n),
        original_row = piece$.gp_original_row,
        beat_time = if (!is.null(beat_time_col)) piece[[beat_time_col]] else NA_real_,
        ibi = ibi,
        has_interval = has_interval,
        nonfinite_ibi = nonfinite_ibi,
        short_ibi = short_ibi,
        long_ibi = long_ibi,
        duplicate_time = duplicate_time,
        abrupt_change = abrupt_change,
        any_flag = any_flag,
        flag_reason = flag_reason,
        stringsAsFactors = FALSE
      )
    )

    beat_i <- beat_i + 1L
    beat_rows[[beat_i]] <- beat_table

    analyzable <- has_interval
    n_analyzable <- sum(analyzable, na.rm = TRUE)
    finite_ibi <- is.finite(ibi) & analyzable

    summary_i <- summary_i + 1L
    summary_rows[[summary_i]] <- cbind(
      group_values,
      data.frame(
        n_beats = n,
        n_intervals = n_analyzable,
        n_finite_intervals = sum(finite_ibi, na.rm = TRUE),
        n_flagged_beats = sum(any_flag, na.rm = TRUE),
        prop_flagged_beats = if (n > 0) {
          sum(any_flag, na.rm = TRUE) / n
        } else {
          NA_real_
        },
        n_nonfinite_ibi = sum(nonfinite_ibi, na.rm = TRUE),
        n_short_ibi = sum(short_ibi, na.rm = TRUE),
        n_long_ibi = sum(long_ibi, na.rm = TRUE),
        n_duplicate_time = sum(duplicate_time, na.rm = TRUE),
        n_abrupt_change = sum(abrupt_change, na.rm = TRUE),
        median_ibi = if (any(finite_ibi)) {
          stats::median(ibi[finite_ibi], na.rm = TRUE)
        } else {
          NA_real_
        },
        min_ibi_observed = if (any(finite_ibi)) {
          min(ibi[finite_ibi], na.rm = TRUE)
        } else {
          NA_real_
        },
        max_ibi_observed = if (any(finite_ibi)) {
          max(ibi[finite_ibi], na.rm = TRUE)
        } else {
          NA_real_
        },
        stringsAsFactors = FALSE
      )
    )
  }

  beats <- do.call(rbind, beat_rows)
  summary <- do.call(rbind, summary_rows)

  rownames(beats) <- NULL
  rownames(summary) <- NULL

  result <- list(
    beats = beats,
    summary = summary,
    parameters = list(
      ibi_col = ibi_col,
      beat_time_col = beat_time_col,
      group_cols = group_cols,
      min_ibi = min_ibi,
      max_ibi = max_ibi,
      duplicate_tolerance = duplicate_tolerance,
      max_relative_change = max_relative_change
    )
  )

  class(result) <- c("gazepoint_beat_audit", "list")
  result
}

#' Apply conservative rule-based IBI corrections
#'
#' Applies a conservative correction action to beats flagged by
#' \code{audit_gazepoint_beats()}. The default action masks flagged intervals by
#' setting their corrected IBI to \code{NA}. The local-median action replaces
#' flagged intervals only when an unflagged local or group median is available.
#' Every change is logged. The function does not add or remove beat rows and does
#' not compute or interpret HRV outcomes.
#'
#' @param audit A \code{gazepoint_beat_audit} object, or a data frame that can be
#'   passed to \code{audit_gazepoint_beats()}.
#' @param action Correction action. One of \code{"mask"} or
#'   \code{"local_median"}.
#' @param corrected_col Name of the corrected IBI column to create.
#' @param local_window Number of rows on each side to inspect for local-median
#'   replacement when \code{action = "local_median"}.
#' @param overwrite Logical. If \code{TRUE}, overwrite an existing corrected
#'   column.
#' @param ... Arguments passed to \code{audit_gazepoint_beats()} when
#'   \code{audit} is a data frame.
#'
#' @return A list with class \code{gazepoint_beat_correction}, containing
#'   corrected beat data, a correction log, a summary table, and parameters.
#' @export
correct_gazepoint_beats <- function(audit,
                                    action = c("mask", "local_median"),
                                    corrected_col = "ibi_corrected",
                                    local_window = 5,
                                    overwrite = FALSE,
                                    ...) {
  action <- match.arg(action)

  if (inherits(audit, "gazepoint_beat_audit")) {
    audit_obj <- audit
  } else if (is.data.frame(audit)) {
    audit_obj <- audit_gazepoint_beats(audit, ...)
  } else {
    stop(
      "`audit` must be a gazepoint_beat_audit object or a data frame.",
      call. = FALSE
    )
  }

  if (!is.character(corrected_col) ||
      length(corrected_col) != 1 ||
      is.na(corrected_col) ||
      !nzchar(corrected_col)) {
    stop("`corrected_col` must be a single non-empty character string.", call. = FALSE)
  }

  gpbeat_check_positive_integer(local_window, "local_window")
  gpbeat_check_logical_one(overwrite, "overwrite")

  beats <- audit_obj$beats

  if (!overwrite && corrected_col %in% names(beats)) {
    stop(
      "Column `",
      corrected_col,
      "` already exists. Choose another `corrected_col` or set `overwrite = TRUE`.",
      call. = FALSE
    )
  }

  beats[[corrected_col]] <- beats$ibi

  group_cols <- audit_obj$parameters$group_cols

  if (is.null(group_cols) || length(group_cols) == 0) {
    group_cols <- if ("segment_id" %in% names(beats)) "segment_id" else NULL
  }

  split_index <- if (is.null(group_cols) || length(group_cols) == 0) {
    factor(rep("all", nrow(beats)))
  } else {
    interaction(beats[group_cols], drop = TRUE, lex.order = TRUE)
  }

  index_pieces <- split(seq_len(nrow(beats)), split_index, drop = TRUE)

  log_rows <- list()
  log_i <- 0L

  for (piece_name in names(index_pieces)) {
    idx <- index_pieces[[piece_name]]
    piece <- beats[idx, , drop = FALSE]

    group_values <- gpbeat_group_values(piece, group_cols, piece_name)

    candidate <- piece$any_flag &
      (
        piece$nonfinite_ibi |
          piece$short_ibi |
          piece$long_ibi |
          piece$duplicate_time |
          piece$abrupt_change
      )

    candidate[is.na(candidate)] <- FALSE

    good <- !piece$any_flag & is.finite(piece$ibi)
    group_median <- if (any(good)) {
      stats::median(piece$ibi[good], na.rm = TRUE)
    } else {
      NA_real_
    }

    for (j in which(candidate)) {
      global_row <- idx[j]
      old_value <- beats$ibi[global_row]
      new_value <- NA_real_
      correction_note <- "masked_flagged_interval"

      if (action == "local_median") {
        local_idx <- seq.int(
          max(1L, j - local_window),
          min(nrow(piece), j + local_window)
        )

        local_good <- local_idx[
          !piece$any_flag[local_idx] &
            is.finite(piece$ibi[local_idx])
        ]

        if (length(local_good) > 0) {
          new_value <- stats::median(piece$ibi[local_good], na.rm = TRUE)
          correction_note <- "replaced_with_local_median"
        } else if (is.finite(group_median)) {
          new_value <- group_median
          correction_note <- "replaced_with_group_median"
        } else {
          new_value <- NA_real_
          correction_note <- "masked_no_reference_interval"
        }
      }

      beats[[corrected_col]][global_row] <- new_value

      log_i <- log_i + 1L
      log_rows[[log_i]] <- cbind(
        group_values,
        data.frame(
          beat_index = piece$beat_index[j],
          original_row = piece$original_row[j],
          action = action,
          correction_note = correction_note,
          flag_reason = piece$flag_reason[j],
          original_ibi = old_value,
          corrected_ibi = new_value,
          stringsAsFactors = FALSE
        )
      )
    }
  }

  correction_log <- if (length(log_rows) == 0) {
    gpbeat_empty_correction_log(group_cols)
  } else {
    do.call(rbind, log_rows)
  }

  rownames(beats) <- NULL
  rownames(correction_log) <- NULL

  summary <- summarize_gazepoint_beat_corrections(
    correction_log,
    by = group_cols
  )

  result <- list(
    data = beats,
    correction_log = correction_log,
    summary = summary,
    parameters = list(
      action = action,
      corrected_col = corrected_col,
      local_window = local_window,
      audit_parameters = audit_obj$parameters
    )
  )

  class(result) <- c("gazepoint_beat_correction", "list")
  result
}

#' Summarize beat-correction logs
#'
#' Summarizes the correction log returned by \code{correct_gazepoint_beats()}.
#' The summary is intended for transparent reporting and does not imply automatic
#' exclusion or interpretive conclusions.
#'
#' @param correction A \code{gazepoint_beat_correction} object or a correction
#'   log data frame.
#' @param by Optional character vector of grouping columns.
#'
#' @return A data frame.
#' @export
summarize_gazepoint_beat_corrections <- function(correction, by = NULL) {
  log <- if (inherits(correction, "gazepoint_beat_correction")) {
    correction$correction_log
  } else if (is.data.frame(correction)) {
    correction
  } else {
    stop(
      "`correction` must be a gazepoint_beat_correction object or data frame.",
      call. = FALSE
    )
  }

  required <- c(
    "action",
    "correction_note",
    "flag_reason",
    "original_ibi",
    "corrected_ibi"
  )

  missing_required <- setdiff(required, names(log))

  if (length(missing_required) > 0) {
    stop(
      "`correction` is missing required columns: ",
      paste(missing_required, collapse = ", "),
      call. = FALSE
    )
  }

  if (nrow(log) == 0) {
    groups <- if (is.null(by) || length(by) == 0) {
      data.frame(segment_id = character(0), stringsAsFactors = FALSE)
    } else {
      as.data.frame(
        stats::setNames(rep(list(character(0)), length(by)), by),
        stringsAsFactors = FALSE
      )
    }

    return(cbind(
      groups,
      data.frame(
        n_corrections = integer(0),
        n_masked = integer(0),
        n_local_median = integer(0),
        n_group_median = integer(0),
        n_unresolved = integer(0),
        stringsAsFactors = FALSE
      )
    ))
  }

  if (is.null(by) || length(by) == 0) {
    log$.gp_all <- "all"
    by <- ".gp_all"
  } else {
    by <- as.character(by)
  }

  missing_by <- setdiff(by, names(log))

  if (length(missing_by) > 0) {
    stop(
      "`by` contains columns not found in `correction`: ",
      paste(missing_by, collapse = ", "),
      call. = FALSE
    )
  }

  split_index <- interaction(log[by], drop = TRUE, lex.order = TRUE)
  pieces <- split(log, split_index, drop = TRUE)

  out <- lapply(pieces, function(piece) {
    group_values <- piece[1, by, drop = FALSE]

    cbind(
      group_values,
      data.frame(
        n_corrections = nrow(piece),
        n_masked = sum(piece$correction_note == "masked_flagged_interval", na.rm = TRUE),
        n_local_median = sum(piece$correction_note == "replaced_with_local_median", na.rm = TRUE),
        n_group_median = sum(piece$correction_note == "replaced_with_group_median", na.rm = TRUE),
        n_unresolved = sum(piece$correction_note == "masked_no_reference_interval", na.rm = TRUE),
        stringsAsFactors = FALSE
      )
    )
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  if (".gp_all" %in% names(out)) {
    names(out)[names(out) == ".gp_all"] <- "segment_id"
  }

  out
}

gpbeat_optional_col <- function(x) {
  if (is.null(x)) {
    return(NULL)
  }

  x <- as.character(x)

  if (length(x) != 1 || is.na(x) || !nzchar(x)) {
    stop("Column arguments must be single non-empty character strings.", call. = FALSE)
  }

  x
}

gpbeat_check_existing_numeric_col <- function(data, col, arg_name) {
  if (!col %in% names(data)) {
    stop("`", arg_name, "` was not found in `data`.", call. = FALSE)
  }

  if (!is.numeric(data[[col]])) {
    stop("`", arg_name, "` must refer to a numeric column.", call. = FALSE)
  }

  invisible(TRUE)
}

gpbeat_group_values <- function(piece, group_cols, piece_name) {
  if (is.null(group_cols) || length(group_cols) == 0) {
    data.frame(segment_id = piece_name, stringsAsFactors = FALSE)
  } else {
    piece[1, group_cols, drop = FALSE]
  }
}

gpbeat_flag_reasons <- function(nonfinite_ibi,
                                short_ibi,
                                long_ibi,
                                duplicate_time,
                                abrupt_change) {
  n <- length(nonfinite_ibi)
  out <- character(n)

  for (i in seq_len(n)) {
    reasons <- character(0)

    if (isTRUE(nonfinite_ibi[i])) {
      reasons <- c(reasons, "nonfinite_ibi")
    }

    if (isTRUE(short_ibi[i])) {
      reasons <- c(reasons, "short_ibi")
    }

    if (isTRUE(long_ibi[i])) {
      reasons <- c(reasons, "long_ibi")
    }

    if (isTRUE(duplicate_time[i])) {
      reasons <- c(reasons, "duplicate_time")
    }

    if (isTRUE(abrupt_change[i])) {
      reasons <- c(reasons, "abrupt_change")
    }

    out[i] <- paste(reasons, collapse = ";")
  }

  out
}

gpbeat_empty_correction_log <- function(group_cols) {
  groups <- if (is.null(group_cols) || length(group_cols) == 0) {
    data.frame(segment_id = character(0), stringsAsFactors = FALSE)
  } else {
    as.data.frame(
      stats::setNames(rep(list(character(0)), length(group_cols)), group_cols),
      stringsAsFactors = FALSE
    )
  }

  cbind(
    groups,
    data.frame(
      beat_index = integer(0),
      original_row = integer(0),
      action = character(0),
      correction_note = character(0),
      flag_reason = character(0),
      original_ibi = numeric(0),
      corrected_ibi = numeric(0),
      stringsAsFactors = FALSE
    )
  )
}

gpbeat_check_positive_number <- function(x, name) {
  if (!is.numeric(x) || length(x) != 1 || !is.finite(x) || x <= 0) {
    stop("`", name, "` must be a single positive number.", call. = FALSE)
  }

  invisible(TRUE)
}

gpbeat_check_nonnegative_number <- function(x, name) {
  if (!is.numeric(x) || length(x) != 1 || !is.finite(x) || x < 0) {
    stop("`", name, "` must be a single non-negative number.", call. = FALSE)
  }

  invisible(TRUE)
}

gpbeat_check_positive_integer <- function(x, name) {
  if (!is.numeric(x) || length(x) != 1 || is.na(x) || x < 1 || x != as.integer(x)) {
    stop("`", name, "` must be a single positive integer.", call. = FALSE)
  }

  invisible(TRUE)
}

gpbeat_check_logical_one <- function(x, name) {
  if (!is.logical(x) || length(x) != 1 || is.na(x)) {
    stop("`", name, "` must be TRUE or FALSE.", call. = FALSE)
  }

  invisible(TRUE)
}
