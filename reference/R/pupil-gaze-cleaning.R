
# Pupil, gaze, and fixation cleaning helpers for Gazepoint exports

.gp_pg_check_data <- function(data, arg = "data") {
  if (!is.data.frame(data)) {
    stop("`", arg, "` must be a data frame.", call. = FALSE)
  }

  if (!nrow(data)) {
    stop("`", arg, "` has no rows.", call. = FALSE)
  }

  invisible(data)
}

.gp_pg_guess_col <- function(data, candidates, label, required = TRUE) {
  nms <- names(data)
  idx <- match(tolower(candidates), tolower(nms))
  idx <- idx[!is.na(idx)]

  if (length(idx)) {
    return(nms[idx[1L]])
  }

  if (isTRUE(required)) {
    stop(
      "Could not identify ", label, " column. Supply it explicitly.",
      call. = FALSE
    )
  }

  NULL
}

.gp_pg_guess_pupil_cols <- function(data, pupil_cols = NULL) {
  if (!is.null(pupil_cols)) {
    missing <- setdiff(pupil_cols, names(data))

    if (length(missing)) {
      stop("Missing pupil columns: ", paste(missing, collapse = ", "), call. = FALSE)
    }

    return(pupil_cols)
  }

  nms <- names(data)

  exact <- c(
    "pupil", "Pupil", "PUPIL",
    "pupil_size", "pupil_diameter",
    "pupil_left", "pupil_right",
    "left_pupil", "right_pupil",
    "left_pupil_diameter", "right_pupil_diameter",
    "LPD", "RPD"
  )

  idx <- match(tolower(exact), tolower(nms))
  idx <- idx[!is.na(idx)]
  cols <- unique(nms[idx])

  rx <- grepl("pupil|diameter|^LPD$|^RPD$", nms, ignore.case = TRUE)
  rx <- rx & !grepl("valid|flag|blink|clean|imputed|outlier|spike|was_", nms, ignore.case = TRUE)

  cols <- unique(c(cols, nms[rx]))
  cols <- cols[vapply(data[cols], is.numeric, logical(1))]

  if (!length(cols)) {
    stop("Could not identify pupil columns. Supply `pupil_cols` explicitly.", call. = FALSE)
  }

  cols
}

.gp_pg_guess_time_col <- function(data, time_col = NULL, required = TRUE) {
  if (!is.null(time_col)) {
    if (!time_col %in% names(data)) {
      stop("`time_col` not found in `data`.", call. = FALSE)
    }

    return(time_col)
  }

  .gp_pg_guess_col(
    data,
    candidates = c(
      "time_s", "TIME", "time", "Time", "timestamp", "Timestamp",
      "MSTIMER", "TIME_TICK", "FPOGS", "BKPMIN"
    ),
    label = "time",
    required = required
  )
}

.gp_pg_time_seconds <- function(time) {
  time <- suppressWarnings(as.numeric(time))

  if (!length(time) || all(!is.finite(time))) {
    return(seq_along(time))
  }

  d <- diff(time[is.finite(time)])
  d <- d[is.finite(d) & d > 0]

  if (!length(d)) {
    return(time)
  }

  med_d <- stats::median(d, na.rm = TRUE)

  if (is.finite(med_d) && med_d > 5) {
    time / 1000
  } else {
    time
  }
}

.gp_pg_group_indices <- function(data, group_cols = NULL) {
  if (is.null(group_cols) || !length(group_cols)) {
    return(list(all = seq_len(nrow(data))))
  }

  missing <- setdiff(group_cols, names(data))

  if (length(missing)) {
    stop("Missing grouping columns: ", paste(missing, collapse = ", "), call. = FALSE)
  }

  split(seq_len(nrow(data)), interaction(data[group_cols], drop = TRUE, sep = " | "))
}

.gp_pg_validity_col_for_pupil <- function(data, pupil_col) {
  nms <- names(data)

  candidates <- switch(
    toupper(pupil_col),
    LPD = c("LPV", "left_pupil_valid", "pupil_left_valid"),
    RPD = c("RPV", "right_pupil_valid", "pupil_right_valid"),
    c(
      paste0(pupil_col, "_valid"),
      paste0(pupil_col, "_validity"),
      sub("diameter", "valid", pupil_col, ignore.case = TRUE)
    )
  )

  idx <- match(tolower(candidates), tolower(nms))
  idx <- idx[!is.na(idx)]

  if (length(idx)) {
    nms[idx[1L]]
  } else {
    NULL
  }
}

.gp_pg_invalid_pupil_matrix <- function(data,
                                        pupil_cols,
                                        validity_cols = NULL,
                                        invalid_values = c(0),
                                        nonpositive_is_missing = TRUE,
                                        treat_infinite_as_missing = TRUE) {
  out <- matrix(FALSE, nrow = nrow(data), ncol = length(pupil_cols))
  colnames(out) <- pupil_cols

  if (!is.null(validity_cols) && length(validity_cols) == 1L && length(pupil_cols) > 1L) {
    validity_cols <- rep(validity_cols, length(pupil_cols))
  }

  for (i in seq_along(pupil_cols)) {
    cc <- pupil_cols[i]
    x <- suppressWarnings(as.numeric(data[[cc]]))

    bad <- is.na(x)

    if (isTRUE(treat_infinite_as_missing)) {
      bad <- bad | !is.finite(x)
    }

    if (length(invalid_values)) {
      bad <- bad | x %in% invalid_values
    }

    if (isTRUE(nonpositive_is_missing)) {
      bad <- bad | x <= 0
    }

    vc <- NULL

    if (!is.null(validity_cols)) {
      vc <- validity_cols[i]

      if (!is.na(vc) && !vc %in% names(data)) {
        stop("Validity column not found: ", vc, call. = FALSE)
      }
    } else {
      vc <- .gp_pg_validity_col_for_pupil(data, cc)
    }

    if (!is.null(vc) && !is.na(vc) && vc %in% names(data)) {
      vv <- data[[vc]]

      if (is.logical(vv)) {
        bad <- bad | !vv
      } else {
        vv_num <- suppressWarnings(as.numeric(vv))
        bad <- bad | is.na(vv_num) | vv_num <= 0
      }
    }

    out[, i] <- bad
  }

  out
}

.gp_pg_runs_to_intervals <- function(flag, idx, time_raw, time_s, min_samples = 1L) {
  if (!any(flag, na.rm = TRUE)) {
    return(data.frame())
  }

  rr <- rle(flag)
  ends <- cumsum(rr$lengths)
  starts <- ends - rr$lengths + 1L

  rows <- vector("list", length(rr$values))
  k <- 0L

  for (i in seq_along(rr$values)) {
    if (isTRUE(rr$values[i]) && rr$lengths[i] >= min_samples) {
      k <- k + 1L

      local_start <- starts[i]
      local_end <- ends[i]
      global_start <- idx[local_start]
      global_end <- idx[local_end]

      rows[[k]] <- data.frame(
        start_index = global_start,
        end_index = global_end,
        onset_time = time_raw[global_start],
        offset_time = time_raw[global_end],
        duration_s = time_s[global_end] - time_s[global_start],
        n_samples = rr$lengths[i],
        stringsAsFactors = FALSE
      )
    }
  }

  if (!k) {
    return(data.frame())
  }

  do.call(rbind, rows[seq_len(k)])
}

.gp_pg_clean_reason <- function(outside, high_velocity) {
  reason <- rep("valid", length(outside))
  reason[outside] <- "outside_screen"
  reason[high_velocity] <- "high_velocity"
  reason[outside & high_velocity] <- "outside_screen;high_velocity"
  reason
}

.gp_pg_duration_to_seconds <- function(x, unit = c("auto", "seconds", "milliseconds")) {
  unit <- match.arg(unit)
  x <- suppressWarnings(as.numeric(x))

  if (unit == "milliseconds") {
    return(x / 1000)
  }

  if (unit == "seconds") {
    return(x)
  }

  med <- stats::median(abs(x), na.rm = TRUE)

  if (is.finite(med) && med > 10) {
    x / 1000
  } else {
    x
  }
}

#' Detect blink intervals from Gazepoint pupil data
#'
#' Identifies blink-like intervals as runs of missing, zero, non-finite, or
#' invalid pupil samples. For binocular data, the default treats a blink as a
#' sample where all selected pupil channels are invalid.
#'
#' @param data Eye-tracking data frame.
#' @param pupil_cols Pupil columns. If NULL, common Gazepoint names such as
#'   `LPD` and `RPD` are detected automatically.
#' @param time_col Time column. If NULL, common Gazepoint time columns are
#'   detected automatically.
#' @param group_cols Optional grouping columns, such as participant or trial.
#' @param validity_cols Optional validity columns corresponding to
#'   `pupil_cols`, such as `LPV` and `RPV`.
#' @param invalid_values Numeric values treated as missing pupil samples.
#' @param nonpositive_is_missing If TRUE, pupil values less than or equal to
#'   zero are treated as invalid.
#' @param combine Whether a blink requires `"all"` or `"any"` selected pupil
#'   channels to be invalid.
#' @param min_blink_samples Minimum run length in samples.
#' @param return Return `"intervals"`, `"onsets"`, or `"flags"`.
#'
#' @return A data frame of blink intervals by default. If `return = "onsets"`,
#'   a numeric vector of blink onset times is returned. If `return = "flags"`,
#'   a logical vector marking blink samples is returned.
#' @export
#'
#' @examples
#' dat <- data.frame(time_s = 0:4, LPD = c(3, NA, NA, 3.1, 3.2))
#' detect_gazepoint_pupil_blinks(dat, pupil_cols = "LPD", time_col = "time_s")
detect_gazepoint_pupil_blinks <- function(data,
                                          pupil_cols = NULL,
                                          time_col = NULL,
                                          group_cols = NULL,
                                          validity_cols = NULL,
                                          invalid_values = c(0),
                                          nonpositive_is_missing = TRUE,
                                          combine = c("all", "any"),
                                          min_blink_samples = 1L,
                                          return = c("intervals", "onsets", "flags")) {
  .gp_pg_check_data(data)
  combine <- match.arg(combine)
  return <- match.arg(return)

  pupil_cols <- .gp_pg_guess_pupil_cols(data, pupil_cols = pupil_cols)
  time_col <- .gp_pg_guess_time_col(data, time_col = time_col, required = FALSE)

  time_raw <- if (!is.null(time_col)) {
    suppressWarnings(as.numeric(data[[time_col]]))
  } else {
    seq_len(nrow(data))
  }

  time_s <- .gp_pg_time_seconds(time_raw)

  invalid_mat <- .gp_pg_invalid_pupil_matrix(
    data = data,
    pupil_cols = pupil_cols,
    validity_cols = validity_cols,
    invalid_values = invalid_values,
    nonpositive_is_missing = nonpositive_is_missing
  )

  blink_flag <- if (combine == "all") {
    rowSums(invalid_mat) == ncol(invalid_mat)
  } else {
    rowSums(invalid_mat) > 0
  }

  blink_flag[is.na(blink_flag)] <- FALSE

  if (return == "flags") {
    return(blink_flag)
  }

  groups <- .gp_pg_group_indices(data, group_cols = group_cols)
  intervals <- list()
  k <- 0L

  for (gname in names(groups)) {
    idx <- groups[[gname]]

    z <- .gp_pg_runs_to_intervals(
      flag = blink_flag[idx],
      idx = idx,
      time_raw = time_raw,
      time_s = time_s,
      min_samples = as.integer(min_blink_samples)
    )

    if (nrow(z)) {
      k <- k + 1L

      if (!is.null(group_cols) && length(group_cols)) {
        group_values <- data[idx[1L], group_cols, drop = FALSE]
        z <- cbind(group_values[rep(1L, nrow(z)), , drop = FALSE], z)
      }

      intervals[[k]] <- z
    }
  }

  if (!k) {
    out <- data.frame(
      blink_id = integer(),
      start_index = integer(),
      end_index = integer(),
      onset_time = numeric(),
      offset_time = numeric(),
      duration_s = numeric(),
      n_samples = integer(),
      stringsAsFactors = FALSE
    )
  } else {
    out <- do.call(rbind, intervals[seq_len(k)])
    row.names(out) <- NULL
    out$blink_id <- seq_len(nrow(out))
    out <- out[c("blink_id", setdiff(names(out), "blink_id"))]
  }

  attr(out, "pupil_cols") <- pupil_cols
  attr(out, "blink_flags") <- blink_flag

  if (return == "onsets") {
    return(out$onset_time)
  }

  out
}

#' Clean Gazepoint pupil signal
#'
#' Flags blink samples, non-positive pupil values, and robust outlier spikes,
#' then interpolates short missing segments. The function returns the original
#' data with cleaned pupil columns and provenance flags.
#'
#' @param data Eye-tracking data frame.
#' @param pupil_cols Pupil columns. If NULL, common Gazepoint pupil columns are
#'   detected automatically.
#' @param time_col Optional time column.
#' @param group_cols Optional grouping columns.
#' @param validity_cols Optional validity columns corresponding to pupil columns.
#' @param method Imputation method passed to `impute_gazepoint_missing()`.
#' @param max_gap Maximum missing run length, in samples, to interpolate.
#' @param spike_mad Robust MAD threshold for pupil outlier spikes.
#' @param combine Blink rule passed to `detect_gazepoint_pupil_blinks()`.
#' @param min_blink_samples Minimum blink run length in samples.
#' @param suffix Suffix for cleaned pupil columns.
#' @param keep_flags If TRUE, add blink/spike/imputation flag columns.
#'
#' @return Data frame with cleaned pupil columns and a `pupil_cleaning_summary`
#'   attribute.
#' @export
#'
#' @examples
#' dat <- data.frame(time_s = 0:4, LPD = c(3, NA, 3.2, 40, 3.1))
#' clean_gazepoint_pupil_signal(dat, pupil_cols = "LPD", time_col = "time_s")
clean_gazepoint_pupil_signal <- function(data,
                                         pupil_cols = NULL,
                                         time_col = NULL,
                                         group_cols = NULL,
                                         validity_cols = NULL,
                                         method = c("linear", "locf", "nocb", "nearest", "constant"),
                                         max_gap = Inf,
                                         spike_mad = 6,
                                         combine = c("all", "any"),
                                         min_blink_samples = 1L,
                                         suffix = "_clean",
                                         keep_flags = TRUE) {
  .gp_pg_check_data(data)
  method <- match.arg(method)
  combine <- match.arg(combine)

  pupil_cols <- .gp_pg_guess_pupil_cols(data, pupil_cols = pupil_cols)

  if (!is.null(time_col) && !time_col %in% names(data)) {
    stop("`time_col` not found in `data`.", call. = FALSE)
  }

  blink_flags <- detect_gazepoint_pupil_blinks(
    data = data,
    pupil_cols = pupil_cols,
    time_col = time_col,
    group_cols = NULL,
    validity_cols = validity_cols,
    combine = combine,
    min_blink_samples = min_blink_samples,
    return = "flags"
  )

  invalid_mat <- .gp_pg_invalid_pupil_matrix(
    data = data,
    pupil_cols = pupil_cols,
    validity_cols = validity_cols
  )

  groups <- .gp_pg_group_indices(data, group_cols = group_cols)
  out <- data
  summaries <- list()

  for (cc in pupil_cols) {
    x <- suppressWarnings(as.numeric(data[[cc]]))
    invalid <- invalid_mat[, cc] | blink_flags

    med <- stats::median(x[!invalid], na.rm = TRUE)
    sc <- stats::mad(x[!invalid], constant = 1.4826, na.rm = TRUE)

    if (!is.finite(sc) || sc == 0) {
      sc <- stats::IQR(x[!invalid], na.rm = TRUE) / 1.349
    }

    if (!is.finite(sc) || sc == 0) {
      spike <- rep(FALSE, length(x))
    } else {
      spike <- abs(x - med) > spike_mad * sc
      spike[is.na(spike)] <- FALSE
    }

    dirty <- invalid | spike
    x_for_impute <- x
    x_for_impute[dirty] <- NA_real_

    cleaned <- x_for_impute

    for (idx in groups) {
      cleaned[idx] <- impute_gazepoint_missing(
        x_for_impute[idx],
        method = method,
        max_gap = max_gap,
        fill_edges = TRUE
      )
    }

    imputed <- is.na(x_for_impute) & !is.na(cleaned)

    clean_col <- paste0(cc, suffix)
    out[[clean_col]] <- cleaned

    if (isTRUE(keep_flags)) {
      out[[paste0(cc, "_was_blink")]] <- blink_flags
      out[[paste0(cc, "_was_spike")]] <- spike
      out[[paste0(cc, "_was_pupil_imputed")]] <- imputed
    }

    summaries[[cc]] <- data.frame(
      column = cc,
      clean_column = clean_col,
      n_blink_samples = sum(blink_flags, na.rm = TRUE),
      n_invalid_samples = sum(invalid, na.rm = TRUE),
      n_spike_samples = sum(spike, na.rm = TRUE),
      n_imputed_samples = sum(imputed, na.rm = TRUE),
      n_missing_after = sum(is.na(cleaned)),
      method = method,
      max_gap = if (is.infinite(max_gap)) Inf else max_gap,
      stringsAsFactors = FALSE
    )
  }

  summary <- do.call(rbind, summaries)
  row.names(summary) <- NULL

  attr(out, "pupil_cols") <- pupil_cols
  attr(out, "pupil_cleaning_summary") <- summary

  out
}

#' Summarize Gazepoint fixation metrics
#'
#' Computes fixation-level summary metrics by participant, trial, AOI, or any
#' user-specified grouping columns.
#'
#' @param fixDF Fixation data frame.
#' @param duration_col Fixation duration column. If NULL, common Gazepoint
#'   names such as `FPOGD` are detected automatically.
#' @param x_col Fixation x-coordinate column.
#' @param y_col Fixation y-coordinate column.
#' @param participant_col Optional participant column.
#' @param trial_col Optional trial column.
#' @param aoi_col Optional AOI column.
#' @param group_cols Optional grouping columns. Overrides detected participant,
#'   trial, and AOI columns.
#' @param duration_unit `"auto"`, `"seconds"`, or `"milliseconds"`.
#'
#' @return Data frame with fixation count, duration, and dispersion metrics.
#' @export
#'
#' @examples
#' fix <- data.frame(trial = "T1", AOI = c("A", "A"), FPOGD = c(.2, .3),
#'                   FPOGX = c(.1, .2), FPOGY = c(.3, .4))
#' summarize_gazepoint_fixations(fix)
summarize_gazepoint_fixations <- function(fixDF,
                                          duration_col = NULL,
                                          x_col = NULL,
                                          y_col = NULL,
                                          participant_col = NULL,
                                          trial_col = NULL,
                                          aoi_col = NULL,
                                          group_cols = NULL,
                                          duration_unit = c("auto", "seconds", "milliseconds")) {
  .gp_pg_check_data(fixDF, arg = "fixDF")
  duration_unit <- match.arg(duration_unit)

  duration_col <- .gp_pg_guess_col(
    fixDF,
    candidates = c("duration_s", "duration", "fixation_duration", "fix_duration", "FPOGD"),
    label = "fixation duration",
    required = is.null(duration_col)
  ) %||% duration_col

  if (!duration_col %in% names(fixDF)) {
    stop("`duration_col` not found in `fixDF`.", call. = FALSE)
  }

  if (is.null(x_col)) {
    x_col <- .gp_pg_guess_col(
      fixDF,
      candidates = c("x", "X", "fix_x", "fixation_x", "FPOGX", "BPOGX"),
      label = "fixation x",
      required = FALSE
    )
  }

  if (is.null(y_col)) {
    y_col <- .gp_pg_guess_col(
      fixDF,
      candidates = c("y", "Y", "fix_y", "fixation_y", "FPOGY", "BPOGY"),
      label = "fixation y",
      required = FALSE
    )
  }

  if (is.null(participant_col)) {
    participant_col <- .gp_pg_guess_col(
      fixDF,
      candidates = c("participant", "participant_id", "subject", "id", "USER"),
      label = "participant",
      required = FALSE
    )
  }

  if (is.null(trial_col)) {
    trial_col <- .gp_pg_guess_col(
      fixDF,
      candidates = c("trial", "trial_id", "TRIAL", "stimulus", "screen"),
      label = "trial",
      required = FALSE
    )
  }

  if (is.null(aoi_col)) {
    aoi_col <- .gp_pg_guess_col(
      fixDF,
      candidates = c("AOI", "aoi", "aoi_name", "area", "region", "interest_area"),
      label = "AOI",
      required = FALSE
    )
  }

  if (is.null(group_cols)) {
    group_cols <- unique(stats::na.omit(c(participant_col, trial_col, aoi_col)))
  }

  if (length(group_cols)) {
    missing <- setdiff(group_cols, names(fixDF))

    if (length(missing)) {
      stop("Missing grouping columns: ", paste(missing, collapse = ", "), call. = FALSE)
    }

    groups <- .gp_pg_group_indices(fixDF, group_cols = group_cols)
  } else {
    groups <- list(all = seq_len(nrow(fixDF)))
  }

  duration_s <- .gp_pg_duration_to_seconds(fixDF[[duration_col]], unit = duration_unit)

  rows <- vector("list", length(groups))
  k <- 0L

  for (gname in names(groups)) {
    idx <- groups[[gname]]
    k <- k + 1L

    d <- duration_s[idx]
    x <- if (!is.null(x_col)) suppressWarnings(as.numeric(fixDF[[x_col]][idx])) else rep(NA_real_, length(idx))
    y <- if (!is.null(y_col)) suppressWarnings(as.numeric(fixDF[[y_col]][idx])) else rep(NA_real_, length(idx))

    row <- data.frame(
      n_fixations = sum(!is.na(d)),
      total_duration_s = sum(d, na.rm = TRUE),
      mean_duration_s = mean(d, na.rm = TRUE),
      median_duration_s = stats::median(d, na.rm = TRUE),
      sd_duration_s = stats::sd(d, na.rm = TRUE),
      min_duration_s = min(d, na.rm = TRUE),
      max_duration_s = max(d, na.rm = TRUE),
      x_dispersion = if (all(is.na(x))) NA_real_ else diff(range(x, na.rm = TRUE)),
      y_dispersion = if (all(is.na(y))) NA_real_ else diff(range(y, na.rm = TRUE)),
      spatial_dispersion = NA_real_,
      bbox_area = NA_real_,
      stringsAsFactors = FALSE
    )

    row$spatial_dispersion <- row$x_dispersion + row$y_dispersion
    row$bbox_area <- row$x_dispersion * row$y_dispersion

    if (length(group_cols)) {
      group_values <- fixDF[idx[1L], group_cols, drop = FALSE]
      row <- cbind(group_values, row)
    } else {
      row <- cbind(data.frame(group = "all", stringsAsFactors = FALSE), row)
    }

    rows[[k]] <- row
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL

  attr(out, "duration_col") <- duration_col
  attr(out, "x_col") <- x_col
  attr(out, "y_col") <- y_col

  out
}

#' Filter implausible Gazepoint gaze samples
#'
#' Flags and optionally removes gaze samples outside screen bounds or with
#' implausibly high point-to-point velocity.
#'
#' @param data Gaze data frame.
#' @param x_col Gaze x column. If NULL, common Gazepoint columns are detected.
#' @param y_col Gaze y column. If NULL, common Gazepoint columns are detected.
#' @param time_col Optional time column.
#' @param group_cols Optional grouping columns.
#' @param screen_bounds Numeric vector `c(x_min, x_max, y_min, y_max)`.
#' @param max_velocity Maximum allowed gaze velocity in coordinate units per
#'   second. Use `Inf` to disable velocity filtering.
#' @param drop_invalid If TRUE, return only valid rows.
#' @param suffix Suffix for filtered coordinate columns.
#'
#' @return Data frame with validity flags, velocity, filter reason, and filtered
#'   x/y columns.
#' @export
#'
#' @examples
#' gaze <- data.frame(time_s = 1:3, BPOGX = c(.1, .2, 2), BPOGY = c(.2, .3, .4))
#' filter_gazepoint_gaze(gaze, screen_bounds = c(0, 1, 0, 1))
filter_gazepoint_gaze <- function(data,
                                  x_col = NULL,
                                  y_col = NULL,
                                  time_col = NULL,
                                  group_cols = NULL,
                                  screen_bounds = c(0, 1, 0, 1),
                                  max_velocity = Inf,
                                  drop_invalid = FALSE,
                                  suffix = "_filtered") {
  .gp_pg_check_data(data)

  if (length(screen_bounds) != 4L || any(!is.finite(screen_bounds))) {
    stop("`screen_bounds` must be c(x_min, x_max, y_min, y_max).", call. = FALSE)
  }

  x_col <- if (is.null(x_col)) {
    .gp_pg_guess_col(
      data,
      candidates = c("BPOGX", "FPOGX", "GPOGX", "LPOGX", "RPOGX", "x", "gaze_x", "X"),
      label = "gaze x",
      required = TRUE
    )
  } else {
    x_col
  }

  y_col <- if (is.null(y_col)) {
    .gp_pg_guess_col(
      data,
      candidates = c("BPOGY", "FPOGY", "GPOGY", "LPOGY", "RPOGY", "y", "gaze_y", "Y"),
      label = "gaze y",
      required = TRUE
    )
  } else {
    y_col
  }

  if (!x_col %in% names(data)) stop("`x_col` not found in `data`.", call. = FALSE)
  if (!y_col %in% names(data)) stop("`y_col` not found in `data`.", call. = FALSE)

  time_col <- .gp_pg_guess_time_col(data, time_col = time_col, required = FALSE)

  x <- suppressWarnings(as.numeric(data[[x_col]]))
  y <- suppressWarnings(as.numeric(data[[y_col]]))
  time_raw <- if (!is.null(time_col)) suppressWarnings(as.numeric(data[[time_col]])) else seq_len(nrow(data))
  time_s <- .gp_pg_time_seconds(time_raw)

  x_min <- screen_bounds[1L]
  x_max <- screen_bounds[2L]
  y_min <- screen_bounds[3L]
  y_max <- screen_bounds[4L]

  in_bounds <- is.finite(x) & is.finite(y) &
    x >= x_min & x <= x_max &
    y >= y_min & y <= y_max

  velocity <- rep(NA_real_, nrow(data))
  velocity_ok <- rep(TRUE, nrow(data))

  groups <- .gp_pg_group_indices(data, group_cols = group_cols)

  for (idx in groups) {
    if (length(idx) < 2L) {
      next
    }

    dx <- diff(x[idx])
    dy <- diff(y[idx])
    dt <- diff(time_s[idx])

    v <- sqrt(dx^2 + dy^2) / dt
    v[!is.finite(v)] <- NA_real_

    velocity[idx[-1L]] <- v

    if (is.finite(max_velocity)) {
      velocity_ok[idx[-1L]] <- is.na(v) | v <= max_velocity
    }
  }

  valid <- in_bounds & velocity_ok
  reason <- .gp_pg_clean_reason(!in_bounds, !velocity_ok)

  out <- data
  out$gaze_in_bounds <- in_bounds
  out$gaze_velocity <- velocity
  out$gaze_velocity_ok <- velocity_ok
  out$gaze_valid <- valid
  out$gaze_filter_reason <- reason

  out[[paste0(x_col, suffix)]] <- x
  out[[paste0(y_col, suffix)]] <- y
  out[[paste0(x_col, suffix)]][!valid] <- NA_real_
  out[[paste0(y_col, suffix)]][!valid] <- NA_real_

  attr(out, "x_col") <- x_col
  attr(out, "y_col") <- y_col
  attr(out, "time_col") <- time_col
  attr(out, "screen_bounds") <- screen_bounds
  attr(out, "max_velocity") <- max_velocity

  if (isTRUE(drop_invalid)) {
    out <- out[valid, , drop = FALSE]
    row.names(out) <- NULL
  }

  out
}

# Fallback for older R code paths if rlang is not available.
`%||%` <- function(x, y) {
  if (is.null(x)) y else x
}

