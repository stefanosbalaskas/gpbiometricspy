
# Alignment, AOI time-course, event-locked synthesis, and quality dashboard helpers.

.gp_c2_check_df <- function(data, arg = "data") {
  if (!is.data.frame(data)) {
    stop("`", arg, "` must be a data frame.", call. = FALSE)
  }
  if (!nrow(data)) {
    stop("`", arg, "` has no rows.", call. = FALSE)
  }
  invisible(data)
}

.gp_c2_guess_col <- function(data, candidates, label, required = TRUE) {
  nms <- names(data)
  idx <- match(tolower(candidates), tolower(nms))
  idx <- idx[!is.na(idx)]

  if (length(idx)) {
    return(nms[idx[1L]])
  }

  if (isTRUE(required)) {
    stop("Could not identify ", label, " column. Supply it explicitly.", call. = FALSE)
  }

  NULL
}

.gp_c2_time_seconds <- function(time) {
  time <- suppressWarnings(as.numeric(time))

  if (!length(time) || all(!is.finite(time))) {
    return(time)
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

.gp_c2_time_col <- function(data, required = TRUE) {
  .gp_c2_guess_col(
    data,
    c("time_s", "time", "timestamp", "event_time", "TIME", "MSTIMER", "CNT"),
    "time",
    required = required
  )
}

.gp_c2_group_indices <- function(data, group_cols = NULL) {
  if (is.null(group_cols) || !length(group_cols)) {
    return(list(all = seq_len(nrow(data))))
  }

  missing <- setdiff(group_cols, names(data))
  if (length(missing)) {
    stop("Missing grouping columns: ", paste(missing, collapse = ", "), call. = FALSE)
  }

  split(seq_len(nrow(data)), interaction(data[group_cols], drop = TRUE, sep = " | "))
}

.gp_c2_bind_rows <- function(rows) {
  rows <- rows[!vapply(rows, is.null, logical(1))]

  if (!length(rows)) {
    return(data.frame())
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  out
}

.gp_c2_event_table <- function(events,
                               event_time_col = NULL,
                               event_id_col = NULL) {
  if (is.numeric(events) && is.null(dim(events))) {
    return(data.frame(
      event_id = paste0("E", seq_along(events)),
      event_time_s = .gp_c2_time_seconds(events),
      stringsAsFactors = FALSE
    ))
  }

  .gp_c2_check_df(events, "events")

  if (is.null(event_time_col)) {
    event_time_col <- .gp_c2_guess_col(
      events,
      c("event_time_s", "event_time", "onset", "onset_s", "time_s", "time", "timestamp", "MSTIMER"),
      "event time",
      TRUE
    )
  }

  if (is.null(event_id_col)) {
    event_id_col <- .gp_c2_guess_col(
      events,
      c("event_id", "event", "marker", "trial", "trial_id", "condition"),
      "event id",
      FALSE
    )
  }

  out <- events
  out$event_time_s <- .gp_c2_time_seconds(out[[event_time_col]])

  if (!is.null(event_id_col) && event_id_col %in% names(out)) {
    out$event_id <- as.character(out[[event_id_col]])
  } else {
    out$event_id <- paste0("E", seq_len(nrow(out)))
  }

  out
}

.gp_c2_auc <- function(time, value) {
  time <- suppressWarnings(as.numeric(time))
  value <- suppressWarnings(as.numeric(value))
  ok <- is.finite(time) & is.finite(value)

  if (sum(ok) < 2L) {
    return(NA_real_)
  }

  time <- time[ok]
  value <- value[ok]
  ord <- order(time)
  time <- time[ord]
  value <- value[ord]

  sum(diff(time) * (utils::head(value, -1L) + utils::tail(value, -1L)) / 2)
}

.gp_c2_numeric_signal_cols <- function(data, time_col = NULL, group_cols = NULL) {
  nms <- names(data)
  is_num <- vapply(data, is.numeric, logical(1))
  out <- nms[is_num]
  setdiff(out, unique(c(time_col, group_cols)))
}

.gp_c2_match_event_groups <- function(data, event_row, group_cols) {
  if (is.null(group_cols) || !length(group_cols)) {
    return(seq_len(nrow(data)))
  }

  common <- intersect(group_cols, intersect(names(data), names(event_row)))

  if (!length(common)) {
    return(seq_len(nrow(data)))
  }

  keep <- rep(TRUE, nrow(data))

  for (cc in common) {
    keep <- keep & as.character(data[[cc]]) == as.character(event_row[[cc]][1L])
  }

  which(keep)
}

.gp_c2_signal_summary <- function(relative_time,
                                  value,
                                  baseline_window_s,
                                  summary_window_s) {
  value <- suppressWarnings(as.numeric(value))
  relative_time <- suppressWarnings(as.numeric(relative_time))

  in_full <- is.finite(relative_time)
  in_baseline <- in_full &
    relative_time >= baseline_window_s[1L] &
    relative_time < baseline_window_s[2L]
  in_summary <- in_full &
    relative_time >= summary_window_s[1L] &
    relative_time <= summary_window_s[2L]

  baseline_values <- value[in_baseline]
  summary_values <- value[in_summary]
  summary_time <- relative_time[in_summary]

  finite_summary <- is.finite(summary_values)

  peak_value <- if (any(finite_summary)) max(summary_values, na.rm = TRUE) else NA_real_
  min_value <- if (any(finite_summary)) min(summary_values, na.rm = TRUE) else NA_real_

  peak_latency <- NA_real_
  if (any(finite_summary)) {
    idx <- which.max(summary_values)
    peak_latency <- summary_time[idx]
  }

  data.frame(
    n_samples = length(value),
    n_summary_samples = length(summary_values),
    baseline_mean = if (any(is.finite(baseline_values))) mean(baseline_values, na.rm = TRUE) else NA_real_,
    summary_mean = if (any(finite_summary)) mean(summary_values, na.rm = TRUE) else NA_real_,
    peak_value = peak_value,
    min_value = min_value,
    peak_latency_s = peak_latency,
    auc = .gp_c2_auc(summary_time, summary_values),
    missing_prop = if (length(value)) mean(!is.finite(value)) else NA_real_,
    stringsAsFactors = FALSE
  )
}

.gp_c2_aoi_from_definitions <- function(data,
                                        x_col,
                                        y_col,
                                        aoi_definitions) {
  required <- c("AOI", "xmin", "xmax", "ymin", "ymax")
  missing <- setdiff(required, names(aoi_definitions))

  if (length(missing)) {
    stop(
      "`aoi_definitions` must contain columns: ",
      paste(required, collapse = ", "),
      call. = FALSE
    )
  }

  x <- suppressWarnings(as.numeric(data[[x_col]]))
  y <- suppressWarnings(as.numeric(data[[y_col]]))
  out <- rep(NA_character_, length(x))

  for (i in seq_len(nrow(aoi_definitions))) {
    hit <- is.na(out) &
      is.finite(x) & is.finite(y) &
      x >= aoi_definitions$xmin[i] &
      x <= aoi_definitions$xmax[i] &
      y >= aoi_definitions$ymin[i] &
      y <= aoi_definitions$ymax[i]

    out[hit] <- as.character(aoi_definitions$AOI[i])
  }

  out
}

#' Align two Gazepoint streams using matched event markers
#'
#' Estimates offset or linear drift between a reference stream and a target
#' stream using matched event times, then adds an aligned reference-clock time
#' column to the target stream.
#'
#' @param reference Reference data frame.
#' @param target Target data frame to align to the reference clock.
#' @param reference_events Reference event table or numeric event times.
#' @param target_events Target event table or numeric event times.
#' @param reference_time_col Reference stream time column.
#' @param target_time_col Target stream time column.
#' @param reference_event_time_col Optional reference-event time column.
#' @param target_event_time_col Optional target-event time column.
#' @param event_id_col Optional event identifier column used for matching.
#' @param method `"linear"` estimates offset and drift; `"offset"` estimates a
#'   fixed lag only.
#' @param include_streams If TRUE, include reference and aligned target streams
#'   in the returned object.
#'
#' @return Object of class `gazepoint_stream_alignment`.
#' @export
align_gazepoint_streams_by_events <- function(reference,
                                              target,
                                              reference_events,
                                              target_events,
                                              reference_time_col = NULL,
                                              target_time_col = NULL,
                                              reference_event_time_col = NULL,
                                              target_event_time_col = NULL,
                                              event_id_col = NULL,
                                              method = c("linear", "offset"),
                                              include_streams = TRUE) {
  method <- match.arg(method)

  .gp_c2_check_df(reference, "reference")
  .gp_c2_check_df(target, "target")

  if (is.null(reference_time_col)) {
    reference_time_col <- .gp_c2_time_col(reference, required = TRUE)
  }

  if (is.null(target_time_col)) {
    target_time_col <- .gp_c2_time_col(target, required = TRUE)
  }

  ref_events <- .gp_c2_event_table(
    reference_events,
    event_time_col = reference_event_time_col,
    event_id_col = event_id_col
  )

  tar_events <- .gp_c2_event_table(
    target_events,
    event_time_col = target_event_time_col,
    event_id_col = event_id_col
  )

  if (!is.null(event_id_col) &&
    event_id_col %in% names(ref_events) &&
    event_id_col %in% names(tar_events)) {
    matched <- merge(
      ref_events,
      tar_events,
      by = event_id_col,
      suffixes = c("_reference", "_target")
    )
    ref_time <- matched$event_time_s_reference
    target_time <- matched$event_time_s_target
  } else {
    n <- min(nrow(ref_events), nrow(tar_events))
    if (n < 1L) {
      stop("No event pairs are available for alignment.", call. = FALSE)
    }
    matched <- data.frame(
      event_id = seq_len(n),
      reference_event_time_s = ref_events$event_time_s[seq_len(n)],
      target_event_time_s = tar_events$event_time_s[seq_len(n)],
      stringsAsFactors = FALSE
    )
    ref_time <- matched$reference_event_time_s
    target_time <- matched$target_event_time_s
  }

  ok <- is.finite(ref_time) & is.finite(target_time)
  ref_time <- ref_time[ok]
  target_time <- target_time[ok]
  matched <- matched[ok, , drop = FALSE]

  if (length(ref_time) < 1L) {
    stop("No finite event pairs are available for alignment.", call. = FALSE)
  }

  if (method == "linear" && length(ref_time) >= 2L && length(unique(ref_time)) >= 2L) {
    fit <- stats::lm(target_time ~ ref_time)
    intercept <- unname(stats::coef(fit)[1L])
    slope <- unname(stats::coef(fit)[2L])
    fitted_target <- stats::fitted(fit)
  } else {
    intercept <- stats::median(target_time - ref_time, na.rm = TRUE)
    slope <- 1
    fitted_target <- ref_time + intercept
    method <- "offset"
  }

  target_clock <- .gp_c2_time_seconds(target[[target_time_col]])
  aligned_time <- (target_clock - intercept) / slope

  target_aligned <- target
  target_aligned$target_time_original_s <- target_clock
  target_aligned$target_time_aligned_s <- aligned_time

  alignment_table <- data.frame(
    event_pair = seq_along(ref_time),
    reference_event_time_s = ref_time,
    target_event_time_s = target_time,
    fitted_target_event_time_s = fitted_target,
    residual_s = target_time - fitted_target,
    aligned_target_event_time_s = (target_time - intercept) / slope,
    stringsAsFactors = FALSE
  )

  diagnostics <- data.frame(
    n_event_pairs = length(ref_time),
    method = method,
    intercept_s = intercept,
    slope_target_per_reference = slope,
    median_raw_lag_s = stats::median(target_time - ref_time, na.rm = TRUE),
    residual_sd_s = if (length(ref_time) > 1L) stats::sd(alignment_table$residual_s, na.rm = TRUE) else NA_real_,
    max_abs_residual_s = max(abs(alignment_table$residual_s), na.rm = TRUE),
    stringsAsFactors = FALSE
  )

  out <- list(
    diagnostics = diagnostics,
    alignment_table = alignment_table
  )

  if (isTRUE(include_streams)) {
    out$reference <- reference
    out$target_aligned <- target_aligned
  }

  class(out) <- c("gazepoint_stream_alignment", "list")
  out
}

#' Build a tidy AOI time course
#'
#' Converts gaze or fixation samples into binned AOI proportions by participant,
#' trial, condition, or other grouping columns. AOIs can be supplied as labels or
#' derived from rectangular AOI definitions.
#'
#' @param data Gaze or fixation data frame.
#' @param time_col Time column.
#' @param aoi_col Optional AOI label column.
#' @param x_col Optional x-coordinate column.
#' @param y_col Optional y-coordinate column.
#' @param aoi_definitions Optional data frame with `AOI`, `xmin`, `xmax`,
#'   `ymin`, and `ymax`.
#' @param group_cols Optional grouping columns.
#' @param bin_width_s Bin width in seconds.
#' @param valid_col Optional validity column.
#' @param include_empty If TRUE, include AOI/bin combinations with zero samples.
#'
#' @return Tidy AOI time-course data frame.
#' @export
build_gazepoint_aoi_timecourse <- function(data,
                                           time_col = NULL,
                                           aoi_col = NULL,
                                           x_col = NULL,
                                           y_col = NULL,
                                           aoi_definitions = NULL,
                                           group_cols = NULL,
                                           bin_width_s = 0.10,
                                           valid_col = NULL,
                                           include_empty = TRUE) {
  .gp_c2_check_df(data)

  if (is.null(time_col)) {
    time_col <- .gp_c2_time_col(data, required = TRUE)
  }

  if (is.null(aoi_col) && is.null(aoi_definitions)) {
    aoi_col <- .gp_c2_guess_col(
      data,
      c("AOI", "aoi", "AOI_NAME", "aoi_name", "area_of_interest"),
      "AOI",
      required = TRUE
    )
  }

  work <- data

  if (!is.null(aoi_definitions)) {
    if (is.null(x_col)) {
      x_col <- .gp_c2_guess_col(data, c("gaze_x", "x", "BPOGX", "FPOGX", "GPOGX"), "x", TRUE)
    }
    if (is.null(y_col)) {
      y_col <- .gp_c2_guess_col(data, c("gaze_y", "y", "BPOGY", "FPOGY", "GPOGY"), "y", TRUE)
    }

    work$.gp_aoi_label <- .gp_c2_aoi_from_definitions(data, x_col, y_col, aoi_definitions)
    aoi_col <- ".gp_aoi_label"
  }

  if (!aoi_col %in% names(work)) {
    stop("`aoi_col` was not found in `data`.", call. = FALSE)
  }

  groups <- .gp_c2_group_indices(work, group_cols)
  rows <- list()
  k <- 0L

  for (g in names(groups)) {
    idx <- groups[[g]]
    z <- work[idx, , drop = FALSE]

    time <- .gp_c2_time_seconds(z[[time_col]])
    ok_time <- is.finite(time)

    if (!any(ok_time)) {
      next
    }

    group_start <- min(time[ok_time], na.rm = TRUE)
    rel_time <- time - group_start
    bin_start <- floor(rel_time / bin_width_s) * bin_width_s

    valid <- rep(TRUE, nrow(z))
    if (!is.null(valid_col) && valid_col %in% names(z)) {
      if (is.logical(z[[valid_col]])) {
        valid <- z[[valid_col]]
      } else {
        valid <- suppressWarnings(as.numeric(z[[valid_col]])) > 0
      }
      valid[is.na(valid)] <- FALSE
    }

    aoi <- as.character(z[[aoi_col]])
    aoi[is.na(aoi) | !nzchar(aoi)] <- NA_character_

    aois <- sort(unique(aoi[!is.na(aoi)]))
    bins <- sort(unique(bin_start[is.finite(bin_start)]))

    if (!length(aois) || !length(bins)) {
      next
    }

    for (bb in bins) {
      in_bin <- is.finite(bin_start) & bin_start == bb
      bin_valid <- in_bin & valid
      denom <- sum(bin_valid, na.rm = TRUE)

      for (aa in aois) {
        hit <- bin_valid & aoi == aa

        if (!include_empty && !any(hit, na.rm = TRUE)) {
          next
        }

        k <- k + 1L
        row <- data.frame(
          group = g,
          bin_start_s = bb,
          bin_end_s = bb + bin_width_s,
          bin_center_s = bb + bin_width_s / 2,
          AOI = aa,
          n_bin_samples = sum(in_bin, na.rm = TRUE),
          valid_bin_samples = denom,
          aoi_samples = sum(hit, na.rm = TRUE),
          aoi_prop = if (denom > 0) sum(hit, na.rm = TRUE) / denom else NA_real_,
          stringsAsFactors = FALSE
        )

        if (!is.null(group_cols) && length(group_cols)) {
          row <- cbind(z[1L, group_cols, drop = FALSE], row[setdiff(names(row), "group")])
        }

        rows[[k]] <- row
      }
    }
  }

  .gp_c2_bind_rows(rows)
}

#' Summarize event-locked multimodal Gazepoint data
#'
#' Creates event-locked sample windows and trial-level summary metrics for one
#' or more numeric Gazepoint modalities such as EDA, PPG, HR, IBI, pupil, gaze,
#' or derived signals.
#'
#' @param data Data frame or named list of data frames.
#' @param events Event table or numeric event times.
#' @param time_col Optional time column for data-frame input.
#' @param event_time_col Optional event-time column.
#' @param event_id_col Optional event identifier column.
#' @param group_cols Optional grouping columns used to match events to samples.
#' @param signal_cols Optional character vector, or named list for list input.
#' @param pre_s Seconds before each event.
#' @param post_s Seconds after each event.
#' @param baseline_window_s Two-element baseline window relative to event.
#' @param summary_window_s Two-element summary window relative to event.
#'
#' @return Object of class `gazepoint_eventlocked_multimodal`.
#' @export
summarize_gazepoint_eventlocked_multimodal <- function(data,
                                                       events,
                                                       time_col = NULL,
                                                       event_time_col = NULL,
                                                       event_id_col = NULL,
                                                       group_cols = NULL,
                                                       signal_cols = NULL,
                                                       pre_s = 1,
                                                       post_s = 3,
                                                       baseline_window_s = c(-1, 0),
                                                       summary_window_s = c(0, 3)) {
  event_table <- .gp_c2_event_table(events, event_time_col, event_id_col)

  streams <- if (is.list(data) && !is.data.frame(data)) {
    data
  } else {
    list(data = data)
  }

  sample_rows <- list()
  summary_rows <- list()
  ks <- 0L
  kt <- 0L

  for (stream_name in names(streams)) {
    stream <- streams[[stream_name]]
    .gp_c2_check_df(stream, paste0("data$", stream_name))

    stream_time_col <- time_col
    if (is.null(stream_time_col) || !stream_time_col %in% names(stream)) {
      stream_time_col <- .gp_c2_time_col(stream, required = TRUE)
    }

    stream_time <- .gp_c2_time_seconds(stream[[stream_time_col]])

    stream_signal_cols <- if (is.list(signal_cols) && !is.data.frame(signal_cols)) {
      signal_cols[[stream_name]]
    } else {
      signal_cols
    }

    if (is.null(stream_signal_cols)) {
      stream_signal_cols <- .gp_c2_numeric_signal_cols(stream, stream_time_col, group_cols)
    }

    stream_signal_cols <- intersect(stream_signal_cols, names(stream))

    if (!length(stream_signal_cols)) {
      next
    }

    for (i in seq_len(nrow(event_table))) {
      ev <- event_table[i, , drop = FALSE]
      sample_idx <- .gp_c2_match_event_groups(stream, ev, group_cols)

      if (!length(sample_idx)) {
        next
      }

      rel_time_all <- stream_time[sample_idx] - ev$event_time_s
      in_window <- is.finite(rel_time_all) & rel_time_all >= -pre_s & rel_time_all <= post_s

      if (!any(in_window)) {
        next
      }

      sample_idx <- sample_idx[in_window]
      rel_time <- rel_time_all[in_window]

      for (sig in stream_signal_cols) {
        value <- suppressWarnings(as.numeric(stream[[sig]][sample_idx]))

        ks <- ks + 1L
        sample_row <- data.frame(
          event_id = ev$event_id,
          modality = stream_name,
          signal = sig,
          sample_index = sample_idx,
          time_s = stream_time[sample_idx],
          relative_time_s = rel_time,
          value = value,
          stringsAsFactors = FALSE
        )

        common_event_cols <- setdiff(names(ev), c("event_time_s", "event_id"))
        if (length(common_event_cols)) {
          for (cc in common_event_cols) {
            sample_row[[cc]] <- ev[[cc]][1L]
          }
        }

        sample_rows[[ks]] <- sample_row

        stat <- .gp_c2_signal_summary(
          rel_time,
          value,
          baseline_window_s = baseline_window_s,
          summary_window_s = summary_window_s
        )

        kt <- kt + 1L
        summary_row <- cbind(
          data.frame(
            event_id = ev$event_id,
            event_time_s = ev$event_time_s,
            modality = stream_name,
            signal = sig,
            stringsAsFactors = FALSE
          ),
          stat
        )

        if (length(common_event_cols)) {
          for (cc in common_event_cols) {
            summary_row[[cc]] <- ev[[cc]][1L]
          }
        }

        summary_rows[[kt]] <- summary_row
      }
    }
  }

  out <- list(
    samples = .gp_c2_bind_rows(sample_rows),
    summary = .gp_c2_bind_rows(summary_rows),
    events = event_table,
    settings = list(
      pre_s = pre_s,
      post_s = post_s,
      baseline_window_s = baseline_window_s,
      summary_window_s = summary_window_s
    )
  )

  class(out) <- c("gazepoint_eventlocked_multimodal", "list")
  out
}

#' Create a compact Gazepoint quality dashboard object
#'
#' Combines audit, missingness, synchronization, and event-locked summary objects
#' into a reviewer-friendly quality dashboard. If `output_dir` is supplied, core
#' dashboard tables are exported as CSV/text files.
#'
#' @param data Optional data frame used to compute audit and missingness when
#'   explicit objects are not supplied.
#' @param audit Optional object from `audit_gazepoint_biometrics_file()`.
#' @param missingness Optional object from `summarize_gazepoint_missingness()`.
#' @param alignment Optional object from `align_gazepoint_streams_by_events()`.
#' @param eventlocked Optional object from
#'   `summarize_gazepoint_eventlocked_multimodal()`.
#' @param title Dashboard title.
#' @param output_dir Optional directory where dashboard tables are written.
#'
#' @return Object of class `gazepoint_quality_dashboard`.
#' @export
create_gazepoint_quality_dashboard <- function(data = NULL,
                                               audit = NULL,
                                               missingness = NULL,
                                               alignment = NULL,
                                               eventlocked = NULL,
                                               title = "Gazepoint quality dashboard",
                                               output_dir = NULL) {
  if (is.null(audit) && !is.null(data) &&
    exists("audit_gazepoint_biometrics_file", mode = "function")) {
    audit <- audit_gazepoint_biometrics_file(data = data)
  }

  if (is.null(missingness) && !is.null(data) &&
    exists("summarize_gazepoint_missingness", mode = "function")) {
    missingness <- tryCatch(
      summarize_gazepoint_missingness(data),
      error = function(e) data.frame(error = conditionMessage(e), stringsAsFactors = FALSE)
    )
  }

  overview <- data.frame(
    title = title,
    created = as.character(Sys.time()),
    has_audit = !is.null(audit),
    has_missingness = !is.null(missingness),
    has_alignment = !is.null(alignment),
    has_eventlocked = !is.null(eventlocked),
    stringsAsFactors = FALSE
  )

  if (!is.null(audit) && is.list(audit) && !is.null(audit$dimensions)) {
    overview$n_rows <- audit$dimensions$n_rows
    overview$n_cols <- audit$dimensions$n_cols
    overview$n_warnings <- length(audit$warnings)
    overview$n_duplicate_rows <- audit$duplicate_rows$n_duplicate_rows
  } else {
    overview$n_rows <- NA_integer_
    overview$n_cols <- NA_integer_
    overview$n_warnings <- NA_integer_
    overview$n_duplicate_rows <- NA_integer_
  }

  if (!is.null(missingness) && is.data.frame(missingness) &&
    "missing_prop" %in% names(missingness)) {
    overview$max_missing_prop <- max(missingness$missing_prop, na.rm = TRUE)
    overview$mean_missing_prop <- mean(missingness$missing_prop, na.rm = TRUE)
  } else {
    overview$max_missing_prop <- NA_real_
    overview$mean_missing_prop <- NA_real_
  }

  if (!is.null(alignment) && is.list(alignment) && !is.null(alignment$diagnostics)) {
    overview$n_alignment_pairs <- alignment$diagnostics$n_event_pairs
    overview$alignment_residual_sd_s <- alignment$diagnostics$residual_sd_s
  } else {
    overview$n_alignment_pairs <- NA_integer_
    overview$alignment_residual_sd_s <- NA_real_
  }

  if (!is.null(eventlocked) && is.list(eventlocked) && !is.null(eventlocked$summary)) {
    overview$n_eventlocked_rows <- nrow(eventlocked$summary)
  } else {
    overview$n_eventlocked_rows <- NA_integer_
  }

  out <- list(
    overview = overview,
    audit = audit,
    missingness = missingness,
    alignment = alignment,
    eventlocked = eventlocked
  )

  if (!is.null(output_dir)) {
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

    utils::write.csv(overview, file.path(output_dir, "quality_dashboard_overview.csv"), row.names = FALSE)

    if (!is.null(missingness) && is.data.frame(missingness)) {
      utils::write.csv(missingness, file.path(output_dir, "quality_dashboard_missingness.csv"), row.names = FALSE)
    }

    if (!is.null(audit) && is.list(audit)) {
      if (!is.null(audit$modalities) && is.data.frame(audit$modalities)) {
        utils::write.csv(audit$modalities, file.path(output_dir, "quality_dashboard_modalities.csv"), row.names = FALSE)
      }

      if (length(audit$warnings)) {
        writeLines(audit$warnings, file.path(output_dir, "quality_dashboard_warnings.txt"), useBytes = TRUE)
      } else {
        writeLines("No audit warnings.", file.path(output_dir, "quality_dashboard_warnings.txt"), useBytes = TRUE)
      }
    }

    if (!is.null(alignment) && is.list(alignment) && !is.null(alignment$diagnostics)) {
      utils::write.csv(alignment$diagnostics, file.path(output_dir, "quality_dashboard_alignment.csv"), row.names = FALSE)
    }

    if (!is.null(eventlocked) && is.list(eventlocked) && !is.null(eventlocked$summary)) {
      utils::write.csv(eventlocked$summary, file.path(output_dir, "quality_dashboard_eventlocked_summary.csv"), row.names = FALSE)
    }

    out$output_dir <- normalizePath(output_dir, winslash = "/", mustWork = FALSE)
  }

  class(out) <- c("gazepoint_quality_dashboard", "list")
  out
}

