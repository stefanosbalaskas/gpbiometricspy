
# PsPM-style Gazepoint preprocessing and GLM helpers
#
# Gazepoint-native R helpers inspired by PsPM-style marker handling,
# trimming/splitting/merging, SCR preprocessing, segment extraction,
# and event-related convolution GLM workflows. These are not wrappers
# around MATLAB PsPM and make no clinical or diagnostic claims.

.gp_pspm_num <- function(x) {
  suppressWarnings(as.numeric(x))
}

.gp_pspm_pick_col <- function(data, candidates, label) {
  hits <- candidates[candidates %in% names(data)]
  if (!length(hits)) {
    stop("Could not infer ", label, " column. Please supply it explicitly.", call. = FALSE)
  }
  hits[1]
}

.gp_pspm_prepare_time_data <- function(data,
                                       time_col = NULL,
                                       sampling_rate_hz = NULL) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  out <- data

  if (is.null(time_col)) {
    if (!is.null(sampling_rate_hz) && is.finite(sampling_rate_hz) && sampling_rate_hz > 0) {
      time_col <- "time_s"
      out[[time_col]] <- (seq_len(nrow(out)) - 1L) / sampling_rate_hz
    } else {
      time_col <- .gp_pspm_pick_col(
        out,
        c("time_s", "Time", "TIME", "RecordingTime", "MSTIMER", "timestamp", "Timestamp"),
        "time"
      )
    }
  }

  if (!time_col %in% names(out)) {
    stop("`time_col` not found.", call. = FALSE)
  }

  out[[time_col]] <- .gp_pspm_num(out[[time_col]])

  list(data = out, time_col = time_col)
}

.gp_pspm_group_index <- function(data, group_cols = NULL) {
  if (is.null(group_cols) || !length(group_cols)) {
    return(list(all = seq_len(nrow(data))))
  }

  missing <- setdiff(group_cols, names(data))
  if (length(missing)) {
    stop("Missing group columns: ", paste(missing, collapse = ", "), call. = FALSE)
  }

  g <- interaction(data[group_cols], drop = TRUE, sep = " | ")
  split(seq_len(nrow(data)), g)
}

.gp_pspm_interp_na <- function(x) {
  x <- .gp_pspm_num(x)

  if (!length(x)) {
    return(x)
  }

  ok <- is.finite(x)

  if (!any(ok)) {
    return(rep(NA_real_, length(x)))
  }

  if (all(ok)) {
    return(x)
  }

  stats::approx(which(ok), x[ok], xout = seq_along(x), rule = 2)$y
}

.gp_pspm_running_mean <- function(x, k) {
  x <- .gp_pspm_interp_na(x)
  k <- max(1L, as.integer(k))

  if (k <= 1L) {
    return(x)
  }

  y <- as.numeric(stats::filter(x, rep(1 / k, k), sides = 2))
  miss <- !is.finite(y)

  if (any(miss)) {
    y[miss] <- x[miss]
  }

  y
}

.gp_pspm_expand_flags <- function(flag, samples) {
  flag <- as.logical(flag)
  if (!any(flag) || samples <= 0) {
    return(flag)
  }

  out <- flag
  idx <- which(flag)

  for (i in idx) {
    lo <- max(1L, i - samples)
    hi <- min(length(flag), i + samples)
    out[lo:hi] <- TRUE
  }

  out
}

.gp_pspm_short_island_flags <- function(valid, min_samples) {
  valid <- as.logical(valid)
  out <- rep(FALSE, length(valid))

  if (!length(valid)) {
    return(out)
  }

  r <- rle(valid)
  ends <- cumsum(r$lengths)
  starts <- ends - r$lengths + 1L

  for (i in seq_along(r$values)) {
    if (isTRUE(r$values[i]) && r$lengths[i] < min_samples) {
      out[starts[i]:ends[i]] <- TRUE
    }
  }

  out
}

.gp_pspm_artifact_table <- function(time, artifact, reason) {
  artifact <- as.logical(artifact)
  if (!any(artifact)) {
    return(data.frame())
  }

  r <- rle(artifact)
  ends <- cumsum(r$lengths)
  starts <- ends - r$lengths + 1L
  keep <- which(r$values)

  rows <- lapply(seq_along(keep), function(j) {
    k <- keep[j]
    idx <- starts[k]:ends[k]
    data.frame(
      artifact_id = j,
      start_index = min(idx),
      end_index = max(idx),
      start_time_s = time[min(idx)],
      end_time_s = time[max(idx)],
      duration_s = time[max(idx)] - time[min(idx)],
      reason = paste(unique(reason[idx][reason[idx] != "accepted"]), collapse = ";"),
      stringsAsFactors = FALSE
    )
  })

  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  out
}

.gp_pspm_kernel <- function(dt,
                            response = c("scr", "canonical", "boxcar"),
                            response_length_s = 20) {
  response <- match.arg(response)

  if (!is.finite(dt) || dt <= 0) {
    stop("Invalid sampling interval.", call. = FALSE)
  }

  t <- seq(0, response_length_s, by = dt)

  if (response == "boxcar") {
    k <- rep(1, length(t))
  } else if (response == "scr") {
    k <- stats::dgamma(t, shape = 3, scale = 1.5)
  } else {
    k1 <- stats::dgamma(t, shape = 6, scale = 1)
    k2 <- stats::dgamma(t, shape = 16, scale = 1)
    k <- k1 - 0.35 * k2
  }

  if (max(abs(k), na.rm = TRUE) > 0) {
    k <- k / max(abs(k), na.rm = TRUE)
  }

  k
}

.gp_pspm_convolve <- function(x, kernel) {
  y <- stats::convolve(x, rev(kernel), type = "open")
  y[seq_along(x)]
}

.gp_pspm_safe_name <- function(x) {
  make.names(as.character(x), unique = TRUE)
}

#' Extract PsPM-style marker information from Gazepoint biometrics data
#'
#' @param data Gazepoint data frame.
#' @param marker_cols Marker/TTL columns. If NULL, likely marker columns are inferred.
#' @param time_col Time column in seconds. If NULL, inferred or created from sampling_rate_hz.
#' @param sampling_rate_hz Sampling rate used when no time column is available.
#' @param group_cols Optional grouping columns such as participant or trial.
#' @param edge Event rule: rising, change, or nonzero.
#' @param nonzero_only Whether zero-valued markers should be ignored.
#' @return Data frame with marker events.
#' @export
extract_gazepoint_markerinfo_pspm_style <- function(data,
                                                    marker_cols = NULL,
                                                    time_col = NULL,
                                                    sampling_rate_hz = NULL,
                                                    group_cols = NULL,
                                                    edge = c("rising", "change", "nonzero"),
                                                    nonzero_only = TRUE) {
  edge <- match.arg(edge)

  prep <- .gp_pspm_prepare_time_data(
    data,
    time_col = time_col,
    sampling_rate_hz = sampling_rate_hz
  )

  d <- prep$data
  time_col <- prep$time_col

  if (is.null(marker_cols)) {
    marker_cols <- grep(
      "marker|ttl|trigger|event|stim|condition",
      names(d),
      ignore.case = TRUE,
      value = TRUE
    )
    marker_cols <- setdiff(marker_cols, time_col)
  }

  if (!length(marker_cols)) {
    stop("No marker columns found. Supply `marker_cols`.", call. = FALSE)
  }

  missing <- setdiff(marker_cols, names(d))
  if (length(missing)) {
    stop("Missing marker columns: ", paste(missing, collapse = ", "), call. = FALSE)
  }

  groups <- .gp_pspm_group_index(d, group_cols)
  rows <- list()

  for (g in names(groups)) {
    global_idx <- groups[[g]]
    dd <- d[global_idx, , drop = FALSE]
    time <- dd[[time_col]]

    for (mc in marker_cols) {
      raw <- dd[[mc]]
      val <- as.character(raw)
      val[is.na(val)] <- "0"

      numeric_val <- suppressWarnings(as.numeric(val))
      is_zero <- ifelse(
        is.finite(numeric_val),
        numeric_val == 0,
        val %in% c("", "0", "FALSE", "false", "NA", "NaN")
      )

      previous <- c(TRUE, is_zero[-length(is_zero)])

      if (edge == "rising") {
        event_idx <- which(!is_zero & previous)
      } else if (edge == "change") {
        changed <- c(TRUE, val[-1L] != val[-length(val)])
        event_idx <- which(changed)
        if (isTRUE(nonzero_only)) {
          event_idx <- event_idx[!is_zero[event_idx]]
        }
      } else {
        event_idx <- which(!is_zero)
      }

      if (!length(event_idx)) {
        next
      }

      ev <- lapply(seq_along(event_idx), function(j) {
        i <- event_idx[j]
        after <- which(is_zero[i:length(is_zero)])
        end_i <- if (length(after)) i + after[1L] - 1L else i

        data.frame(
          group = g,
          marker_id = length(rows) + j,
          marker_channel = mc,
          marker_code = val[i],
          marker_label = paste(mc, val[i], sep = "_"),
          sample_index = global_idx[i],
          time_s = time[i],
          duration_s = if (end_i > i) time[end_i] - time[i] else 0,
          stringsAsFactors = FALSE
        )
      })

      rows[[length(rows) + 1L]] <- do.call(rbind, ev)
    }
  }

  if (!length(rows)) {
    return(data.frame())
  }

  out <- do.call(rbind, rows)
  out$marker_id <- seq_len(nrow(out))
  row.names(out) <- NULL
  out
}

#' Combine multiple Gazepoint marker channels PsPM-style
#'
#' @param data Gazepoint data frame.
#' @param marker_cols Marker columns to combine.
#' @param time_col Time column.
#' @param sampling_rate_hz Sampling rate if time column is absent.
#' @param group_cols Optional grouping columns.
#' @param combined_col Name of combined marker column.
#' @return List with combined data and marker table.
#' @export
combine_gazepoint_marker_channels_pspm_style <- function(data,
                                                         marker_cols = NULL,
                                                         time_col = NULL,
                                                         sampling_rate_hz = NULL,
                                                         group_cols = NULL,
                                                         combined_col = "pspm_marker") {
  prep <- .gp_pspm_prepare_time_data(
    data,
    time_col = time_col,
    sampling_rate_hz = sampling_rate_hz
  )

  d <- prep$data

  markers <- extract_gazepoint_markerinfo_pspm_style(
    d,
    marker_cols = marker_cols,
    time_col = prep$time_col,
    group_cols = group_cols,
    edge = "rising"
  )

  d[[combined_col]] <- NA_character_
  d[[paste0(combined_col, "_code")]] <- NA_integer_

  if (nrow(markers)) {
    by_sample <- split(markers, markers$sample_index)

    for (nm in names(by_sample)) {
      idx <- as.integer(nm)
      labs <- by_sample[[nm]]$marker_label
      d[[combined_col]][idx] <- paste(labs, collapse = "+")
      d[[paste0(combined_col, "_code")]][idx] <- min(by_sample[[nm]]$marker_id)
    }
  }

  list(
    data = d,
    markers = markers,
    marker_cols = marker_cols,
    combined_col = combined_col
  )
}

#' Trim Gazepoint biometrics data PsPM-style
#'
#' @param data Gazepoint data frame.
#' @param start_s Start time in seconds.
#' @param end_s End time in seconds.
#' @param time_col Time column.
#' @param reset_time If TRUE, reset trimmed time to start at zero.
#' @return Trimmed data frame.
#' @export
trim_gazepoint_biometrics_pspm_style <- function(data,
                                                 start_s = NULL,
                                                 end_s = NULL,
                                                 time_col = NULL,
                                                 reset_time = FALSE) {
  prep <- .gp_pspm_prepare_time_data(data, time_col = time_col)
  d <- prep$data
  time_col <- prep$time_col

  keep <- rep(TRUE, nrow(d))

  if (!is.null(start_s)) {
    keep <- keep & d[[time_col]] >= start_s
  }

  if (!is.null(end_s)) {
    keep <- keep & d[[time_col]] <= end_s
  }

  out <- d[keep, , drop = FALSE]

  if (isTRUE(reset_time) && nrow(out)) {
    out[[time_col]] <- out[[time_col]] - min(out[[time_col]], na.rm = TRUE)
  }

  row.names(out) <- NULL
  out
}

#' Split Gazepoint recordings into PsPM-style sessions
#'
#' @param data Gazepoint data frame.
#' @param time_col Time column.
#' @param gap_seconds Gap threshold. If NULL, inferred from sampling interval.
#' @param session_col Output session column.
#' @param reset_time If TRUE, add session-relative time.
#' @return List with annotated data, sessions, and split data.
#' @export
split_gazepoint_sessions_pspm_style <- function(data,
                                                time_col = NULL,
                                                gap_seconds = NULL,
                                                session_col = "pspm_session",
                                                reset_time = TRUE) {
  prep <- .gp_pspm_prepare_time_data(data, time_col = time_col)
  d <- prep$data
  time_col <- prep$time_col

  time <- d[[time_col]]
  dt <- c(NA_real_, diff(time))

  valid_dt <- dt[is.finite(dt) & dt > 0]

  if (is.null(gap_seconds)) {
    gap_seconds <- if (length(valid_dt)) 5 * stats::median(valid_dt) else Inf
  }

  new_session <- is.na(dt) | !is.finite(dt) | dt < 0 | dt > gap_seconds
  d[[session_col]] <- cumsum(new_session)

  if (isTRUE(reset_time)) {
    d$pspm_session_time_s <- stats::ave(
      d[[time_col]],
      d[[session_col]],
      FUN = function(z) z - min(z, na.rm = TRUE)
    )
  }

  sessions <- do.call(rbind, lapply(split(seq_len(nrow(d)), d[[session_col]]), function(idx) {
    data.frame(
      session = d[[session_col]][idx[1L]],
      start_index = min(idx),
      end_index = max(idx),
      start_time_s = d[[time_col]][min(idx)],
      end_time_s = d[[time_col]][max(idx)],
      n_samples = length(idx)
    )
  }))

  row.names(sessions) <- NULL

  list(
    data = d,
    sessions = sessions,
    split_data = split(d, d[[session_col]])
  )
}

#' Merge multiple Gazepoint recordings PsPM-style
#'
#' @param recordings List of data frames.
#' @param time_col Time column.
#' @param gap_seconds Gap inserted between recordings.
#' @param recording_col Output recording-id column.
#' @param reset_first_time If TRUE, each input time starts from zero before offsetting.
#' @return Merged data frame.
#' @export
merge_gazepoint_recordings_pspm_style <- function(recordings,
                                                  time_col = NULL,
                                                  gap_seconds = 1,
                                                  recording_col = "pspm_recording",
                                                  reset_first_time = TRUE) {
  if (!is.list(recordings) || !length(recordings)) {
    stop("`recordings` must be a non-empty list of data frames.", call. = FALSE)
  }

  out <- list()
  offset <- 0

  for (i in seq_along(recordings)) {
    prep <- .gp_pspm_prepare_time_data(recordings[[i]], time_col = time_col)
    d <- prep$data
    tc <- prep$time_col

    d$pspm_original_time_s <- d[[tc]]

    if (isTRUE(reset_first_time) && nrow(d)) {
      d[[tc]] <- d[[tc]] - min(d[[tc]], na.rm = TRUE)
    }

    d[[tc]] <- d[[tc]] + offset
    d[[recording_col]] <- i

    offset <- max(d[[tc]], na.rm = TRUE) + gap_seconds

    out[[i]] <- d
  }

  merged <- do.call(rbind, out)
  row.names(merged) <- NULL
  merged
}

#' Preprocess Gazepoint SCR/GSR data PsPM-style
#'
#' @param data Gazepoint data frame or numeric SCR/GSR signal.
#' @param signal_col SCR/GSR column.
#' @param time_col Time column.
#' @param sampling_rate_hz Sampling rate for numeric input or missing time.
#' @param range Valid signal range.
#' @param slope_limit_per_s Maximum absolute slope per second.
#' @param clipping_tolerance Difference threshold for flat clipping detection.
#' @param clipping_seconds Minimum flat-run duration.
#' @param min_valid_island_seconds Minimum valid island length.
#' @param artifact_epoch_seconds Seconds to expand around detected artefacts.
#' @param smoothing_seconds Smoothing window after artefact correction.
#' @return List with processed signal, artifact table, summary, and settings.
#' @export
preprocess_gazepoint_scr_pspm_style <- function(data,
                                                signal_col = NULL,
                                                time_col = NULL,
                                                sampling_rate_hz = NULL,
                                                range = c(0, 50),
                                                slope_limit_per_s = 10,
                                                clipping_tolerance = 1e-5,
                                                clipping_seconds = 0.5,
                                                min_valid_island_seconds = 1,
                                                artifact_epoch_seconds = 0.25,
                                                smoothing_seconds = 0.25) {
  if (is.numeric(data) && is.null(dim(data))) {
    if (is.null(sampling_rate_hz) || !is.finite(sampling_rate_hz) || sampling_rate_hz <= 0) {
      stop("`sampling_rate_hz` is required for numeric input.", call. = FALSE)
    }

    d <- data.frame(
      time_s = (seq_along(data) - 1L) / sampling_rate_hz,
      scr = .gp_pspm_num(data)
    )
    signal_col <- "scr"
    time_col <- "time_s"
  } else {
    prep <- .gp_pspm_prepare_time_data(
      data,
      time_col = time_col,
      sampling_rate_hz = sampling_rate_hz
    )
    d <- prep$data
    time_col <- prep$time_col

    if (is.null(signal_col)) {
      signal_col <- .gp_pspm_pick_col(
        d,
        c("SCR", "GSR", "EDA", "scr", "gsr", "eda", "signal"),
        "SCR/GSR"
      )
    }
  }

  if (!signal_col %in% names(d)) {
    stop("`signal_col` not found.", call. = FALSE)
  }

  sig <- .gp_pspm_num(d[[signal_col]])
  time <- .gp_pspm_num(d[[time_col]])

  if (is.null(sampling_rate_hz)) {
    dt0 <- diff(time)
    dt0 <- dt0[is.finite(dt0) & dt0 > 0]
    sampling_rate_hz <- if (length(dt0)) 1 / stats::median(dt0) else NA_real_
  }

  if (!is.finite(sampling_rate_hz) || sampling_rate_hz <= 0) {
    stop("Could not infer a valid sampling rate.", call. = FALSE)
  }

  reason <- rep("accepted", length(sig))

  range_flag <- !is.finite(sig) | sig < range[1] | sig > range[2]
  reason[range_flag] <- "range_or_nonfinite"

  dt <- c(NA_real_, diff(time))
  slope <- c(NA_real_, abs(diff(sig)) / dt[-1L])
  slope_flag <- is.finite(slope) & slope > slope_limit_per_s
  reason[slope_flag] <- ifelse(reason[slope_flag] == "accepted", "slope", paste(reason[slope_flag], "slope", sep = ";"))

  flat <- c(FALSE, abs(diff(sig)) <= clipping_tolerance)
  min_flat <- max(2L, round(clipping_seconds * sampling_rate_hz))
  r <- rle(flat)
  ends <- cumsum(r$lengths)
  starts <- ends - r$lengths + 1L
  clip_flag <- rep(FALSE, length(sig))

  for (i in seq_along(r$values)) {
    if (isTRUE(r$values[i]) && r$lengths[i] >= min_flat) {
      clip_flag[starts[i]:ends[i]] <- TRUE
    }
  }

  reason[clip_flag] <- ifelse(reason[clip_flag] == "accepted", "clipping", paste(reason[clip_flag], "clipping", sep = ";"))

  initial_artifact <- range_flag | slope_flag | clip_flag

  min_island <- max(1L, round(min_valid_island_seconds * sampling_rate_hz))
  island_flag <- .gp_pspm_short_island_flags(!initial_artifact, min_island)
  reason[island_flag] <- ifelse(reason[island_flag] == "accepted", "short_valid_island", paste(reason[island_flag], "short_valid_island", sep = ";"))

  artifact <- initial_artifact | island_flag

  expand_n <- max(0L, round(artifact_epoch_seconds * sampling_rate_hz))
  artifact <- .gp_pspm_expand_flags(artifact, expand_n)
  reason[artifact & reason == "accepted"] <- "artifact_epoch"

  clean <- sig
  clean[artifact] <- NA_real_
  clean <- .gp_pspm_interp_na(clean)

  smooth_n <- max(1L, round(smoothing_seconds * sampling_rate_hz))
  processed <- .gp_pspm_running_mean(clean, smooth_n)

  signal_out <- data.frame(
    d,
    scr_raw = sig,
    scr_clean = clean,
    scr_processed = processed,
    pspm_artifact = artifact,
    pspm_artifact_reason = reason
  )

  artifacts <- .gp_pspm_artifact_table(time, artifact, reason)

  summary <- data.frame(
    n_samples = length(sig),
    sampling_rate_hz = sampling_rate_hz,
    n_artifact_samples = sum(artifact, na.rm = TRUE),
    artifact_fraction = mean(artifact, na.rm = TRUE),
    n_artifact_epochs = nrow(artifacts),
    mean_scr_processed = mean(processed, na.rm = TRUE),
    sd_scr_processed = stats::sd(processed, na.rm = TRUE)
  )

  list(
    signal = signal_out,
    artifacts = artifacts,
    summary = summary,
    settings = list(
      range = range,
      slope_limit_per_s = slope_limit_per_s,
      clipping_tolerance = clipping_tolerance,
      clipping_seconds = clipping_seconds,
      min_valid_island_seconds = min_valid_island_seconds,
      artifact_epoch_seconds = artifact_epoch_seconds,
      smoothing_seconds = smoothing_seconds,
      sampling_rate_hz = sampling_rate_hz
    )
  )
}

#' Extract event-centred Gazepoint segments PsPM-style
#'
#' @param data Gazepoint signal data.
#' @param events Event table.
#' @param signal_col Signal column.
#' @param time_col Signal time column.
#' @param event_time_col Event onset-time column.
#' @param event_id_col Optional event-id column.
#' @param condition_col Optional condition column.
#' @param pre_s Seconds before event.
#' @param post_s Seconds after event.
#' @param baseline_window Baseline window relative to event.
#' @param baseline_correct If TRUE, subtract event baseline.
#' @return Long-format segment table.
#' @export
extract_gazepoint_segments_pspm_style <- function(data,
                                                  events,
                                                  signal_col,
                                                  time_col = NULL,
                                                  event_time_col = "onset_time_s",
                                                  event_id_col = NULL,
                                                  condition_col = NULL,
                                                  pre_s = 1,
                                                  post_s = 5,
                                                  baseline_window = c(-1, 0),
                                                  baseline_correct = TRUE) {
  prep <- .gp_pspm_prepare_time_data(data, time_col = time_col)
  d <- prep$data
  time_col <- prep$time_col

  if (!signal_col %in% names(d)) {
    stop("`signal_col` not found.", call. = FALSE)
  }

  if (!is.data.frame(events) || !event_time_col %in% names(events)) {
    stop("`events` must contain `event_time_col`.", call. = FALSE)
  }

  time <- d[[time_col]]
  signal <- .gp_pspm_num(d[[signal_col]])

  rows <- list()

  for (i in seq_len(nrow(events))) {
    onset <- .gp_pspm_num(events[[event_time_col]][i])
    idx <- which(time >= onset - pre_s & time <= onset + post_s)

    if (!length(idx)) {
      next
    }

    rel <- time[idx] - onset
    base_idx <- idx[rel >= baseline_window[1] & rel <= baseline_window[2]]
    baseline <- if (length(base_idx)) mean(signal[base_idx], na.rm = TRUE) else NA_real_

    ev_id <- if (!is.null(event_id_col) && event_id_col %in% names(events)) {
      events[[event_id_col]][i]
    } else {
      i
    }

    cond <- if (!is.null(condition_col) && condition_col %in% names(events)) {
      as.character(events[[condition_col]][i])
    } else {
      "event"
    }

    rows[[length(rows) + 1L]] <- data.frame(
      event_id = ev_id,
      condition = cond,
      onset_time_s = onset,
      sample_index = idx,
      time_s = time[idx],
      relative_time_s = rel,
      value = signal[idx],
      baseline = baseline,
      value_baseline_corrected = if (isTRUE(baseline_correct)) signal[idx] - baseline else signal[idx],
      stringsAsFactors = FALSE
    )
  }

  if (!length(rows)) {
    return(data.frame())
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  out
}

#' Create PsPM-style convolution GLM design matrix
#'
#' @param events Event table.
#' @param time Numeric time vector or data frame containing time_col.
#' @param time_col Time column if time is a data frame.
#' @param onset_col Event onset column.
#' @param condition_col Event condition column.
#' @param duration_col Optional duration column.
#' @param response Response kernel: scr, canonical, or boxcar.
#' @param response_length_s Kernel length in seconds.
#' @param include_derivative If TRUE, include temporal derivative regressors.
#' @param add_intercept If TRUE, add intercept column.
#' @return Design matrix as data frame.
#' @export
create_gazepoint_pspm_glm_design <- function(events,
                                             time,
                                             time_col = NULL,
                                             onset_col = "onset_time_s",
                                             condition_col = "condition",
                                             duration_col = NULL,
                                             response = c("scr", "canonical", "boxcar"),
                                             response_length_s = 20,
                                             include_derivative = FALSE,
                                             add_intercept = TRUE) {
  response <- match.arg(response)

  if (is.data.frame(time)) {
    prep <- .gp_pspm_prepare_time_data(time, time_col = time_col)
    tt <- prep$data[[prep$time_col]]
  } else {
    tt <- .gp_pspm_num(time)
  }

  tt <- tt[is.finite(tt)]

  if (length(tt) < 3L) {
    stop("At least three time points are required.", call. = FALSE)
  }

  if (!is.data.frame(events) || !onset_col %in% names(events)) {
    stop("`events` must contain `onset_col`.", call. = FALSE)
  }

  if (!condition_col %in% names(events)) {
    events[[condition_col]] <- "event"
  }

  dt <- stats::median(diff(sort(unique(tt))), na.rm = TRUE)

  if (!is.finite(dt) || dt <= 0) {
    stop("Could not infer sampling interval from `time`.", call. = FALSE)
  }

  kernel <- .gp_pspm_kernel(dt, response = response, response_length_s = response_length_s)

  design <- data.frame(time_s = tt)

  if (isTRUE(add_intercept)) {
    design$intercept <- 1
  }

  conditions <- unique(as.character(events[[condition_col]]))

  for (cc in conditions) {
    ev <- events[as.character(events[[condition_col]]) == cc, , drop = FALSE]
    impulse <- rep(0, length(tt))

    for (i in seq_len(nrow(ev))) {
      onset <- .gp_pspm_num(ev[[onset_col]][i])
      duration <- if (!is.null(duration_col) && duration_col %in% names(ev)) {
        .gp_pspm_num(ev[[duration_col]][i])
      } else {
        0
      }

      if (!is.finite(onset)) {
        next
      }

      if (is.finite(duration) && duration > dt) {
        idx <- which(tt >= onset & tt <= onset + duration)
      } else {
        idx <- which.min(abs(tt - onset))
      }

      impulse[idx] <- impulse[idx] + 1
    }

    reg <- .gp_pspm_convolve(impulse, kernel)
    nm <- paste0("pspm_", .gp_pspm_safe_name(cc))
    design[[nm]] <- reg

    if (isTRUE(include_derivative)) {
      design[[paste0(nm, "_derivative")]] <- c(0, diff(reg)) / dt
    }
  }

  attr(design, "kernel") <- kernel
  attr(design, "response") <- response
  attr(design, "response_length_s") <- response_length_s
  design
}

#' Fit PsPM-style event-related convolution GLM
#'
#' @param data Gazepoint signal data.
#' @param design Design matrix from create_gazepoint_pspm_glm_design().
#' @param signal_col Signal column.
#' @param time_col Time column in data.
#' @param design_time_col Time column in design.
#' @param regressor_cols Optional regressor columns. If NULL, inferred.
#' @return List with coefficients, fitted values, residuals, and model summary.
#' @export
fit_gazepoint_convolution_glm <- function(data,
                                          design,
                                          signal_col,
                                          time_col = NULL,
                                          design_time_col = "time_s",
                                          regressor_cols = NULL) {
  prep <- .gp_pspm_prepare_time_data(data, time_col = time_col)
  d <- prep$data
  time_col <- prep$time_col

  if (!signal_col %in% names(d)) {
    stop("`signal_col` not found.", call. = FALSE)
  }

  if (!is.data.frame(design) || !design_time_col %in% names(design)) {
    stop("`design` must be a data frame containing `design_time_col`.", call. = FALSE)
  }

  y <- .gp_pspm_num(d[[signal_col]])
  data_time <- d[[time_col]]

  if (!identical(length(y), nrow(design)) || max(abs(data_time - design[[design_time_col]]), na.rm = TRUE) > 1e-8) {
    y <- stats::approx(data_time, y, xout = design[[design_time_col]], rule = 2)$y
  }

  if (is.null(regressor_cols)) {
    regressor_cols <- setdiff(names(design), design_time_col)
  }

  if (!length(regressor_cols)) {
    stop("No regressors found in `design`.", call. = FALSE)
  }

  X <- as.matrix(design[regressor_cols])
  storage.mode(X) <- "double"

  ok <- is.finite(y) & apply(X, 1, function(z) all(is.finite(z)))
  X_ok <- X[ok, , drop = FALSE]
  y_ok <- y[ok]

  fit <- stats::lm.fit(X_ok, y_ok)
  beta <- fit$coefficients
  fitted <- as.numeric(X %*% beta)
  residuals <- y - fitted

  n <- length(y_ok)
  p <- ncol(X_ok)
  df_resid <- max(0L, n - fit$rank)
  rss <- sum((y_ok - as.numeric(X_ok %*% beta))^2, na.rm = TRUE)
  tss <- sum((y_ok - mean(y_ok, na.rm = TRUE))^2, na.rm = TRUE)
  sigma2 <- if (df_resid > 0) rss / df_resid else NA_real_

  se <- rep(NA_real_, length(beta))
  if (is.finite(sigma2) && fit$rank == p) {
    qr_x <- qr(X_ok)
    r <- qr.R(qr_x)
    inv <- chol2inv(r)
    se <- sqrt(diag(inv) * sigma2)
  }

  t_value <- beta / se
  p_value <- if (df_resid > 0) 2 * stats::pt(abs(t_value), df = df_resid, lower.tail = FALSE) else rep(NA_real_, length(beta))

  coef_tab <- data.frame(
    term = names(beta),
    estimate = as.numeric(beta),
    std_error = as.numeric(se),
    statistic = as.numeric(t_value),
    p_value = as.numeric(p_value),
    stringsAsFactors = FALSE
  )

  predictions <- data.frame(
    time_s = design[[design_time_col]],
    observed = y,
    fitted = fitted,
    residual = residuals
  )

  summary <- data.frame(
    n = n,
    n_regressors = p,
    rank = fit$rank,
    df_residual = df_resid,
    rss = rss,
    r_squared = if (tss > 0) 1 - rss / tss else NA_real_,
    aic = if (n > 0 && rss > 0) n * log(rss / n) + 2 * p else NA_real_
  )

  out <- list(
    coefficients = coef_tab,
    predictions = predictions,
    summary = summary,
    design = design,
    signal_col = signal_col,
    regressor_cols = regressor_cols,
    response = attr(design, "response"),
    call = match.call()
  )

  class(out) <- c("gazepoint_pspm_glm", "list")
  out
}

#' Export PsPM-style Gazepoint model estimates
#'
#' @param model Model object from fit_gazepoint_convolution_glm().
#' @param path Output path. Use .csv, .rds, or .json.
#' @param format Optional format. If NULL, inferred from path extension.
#' @param include_predictions If TRUE, CSV export also writes predictions.
#' @return Data frame of written files.
#' @export
export_gazepoint_pspm_model_estimates <- function(model,
                                                  path,
                                                  format = NULL,
                                                  include_predictions = TRUE) {
  if (missing(path) || !nzchar(path)) {
    stop("Supply `path`.", call. = FALSE)
  }

  if (is.null(format)) {
    ext <- tolower(tools::file_ext(path))
    format <- if (ext %in% c("csv", "rds", "json")) ext else "csv"
  }

  format <- match.arg(format, c("csv", "rds", "json"))
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)

  files <- data.frame(file = character(), role = character(), stringsAsFactors = FALSE)

  if (format == "rds") {
    saveRDS(model, path)
    files <- rbind(files, data.frame(file = path, role = "model_rds"))
  }

  if (format == "json") {
    if (!requireNamespace("jsonlite", quietly = TRUE)) {
      stop("Package `jsonlite` is required for JSON export.", call. = FALSE)
    }

    jsonlite::write_json(
      list(
        coefficients = model$coefficients,
        summary = model$summary,
        response = model$response,
        regressor_cols = model$regressor_cols
      ),
      path = path,
      auto_unbox = TRUE,
      pretty = TRUE,
      null = "null"
    )

    files <- rbind(files, data.frame(file = path, role = "model_json"))
  }

  if (format == "csv") {
    coef_path <- path
    utils::write.csv(model$coefficients, coef_path, row.names = FALSE)
    files <- rbind(files, data.frame(file = coef_path, role = "coefficients"))

    summary_path <- sub("[.]csv$", "_summary.csv", path, ignore.case = TRUE)
    if (identical(summary_path, path)) {
      summary_path <- paste0(path, "_summary.csv")
    }
    utils::write.csv(model$summary, summary_path, row.names = FALSE)
    files <- rbind(files, data.frame(file = summary_path, role = "summary"))

    if (isTRUE(include_predictions)) {
      pred_path <- sub("[.]csv$", "_predictions.csv", path, ignore.case = TRUE)
      if (identical(pred_path, path)) {
        pred_path <- paste0(path, "_predictions.csv")
      }
      utils::write.csv(model$predictions, pred_path, row.names = FALSE)
      files <- rbind(files, data.frame(file = pred_path, role = "predictions"))
    }
  }

  row.names(files) <- NULL
  files
}

