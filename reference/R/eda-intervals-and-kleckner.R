#' Classify SCRs into FIR, SIR, and TIR latency intervals
#'
#' Classifies extracted SCRs into first-, second-, and third-interval response
#' windows based on response latency after stimulus onset.
#'
#' @param dat A data frame containing SCR events or peaks.
#' @param response_time_col Optional response/peak time column.
#' @param stimulus_onset_col Optional stimulus-onset column. Required when
#'   `latency_col` is not supplied.
#' @param latency_col Optional precomputed latency column.
#' @param output_col Name of the output interval column.
#' @param latency_output_col Name of the latency output column.
#' @param fir Numeric vector of length two defining FIR window in seconds.
#' @param sir Numeric vector of length two defining SIR window in seconds.
#' @param tir Numeric vector of length two defining TIR window in seconds.
#'
#' @return A data frame with interval labels and latency metadata.
#' @export
classify_gazepoint_scr_intervals <- function(dat,
                                             response_time_col = NULL,
                                             stimulus_onset_col = NULL,
                                             latency_col = NULL,
                                             output_col = "scr_interval",
                                             latency_output_col = "scr_latency_s",
                                             fir = c(1, 4),
                                             sir = c(4, 7),
                                             tir = c(7, 10)) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  gpbiometrics_scr_interval_validate_window(fir, "fir")
  gpbiometrics_scr_interval_validate_window(sir, "sir")
  gpbiometrics_scr_interval_validate_window(tir, "tir")

  if (!is.null(latency_col)) {
    if (!latency_col %in% names(dat)) {
      stop("Column `", latency_col, "` was not found in `dat`.", call. = FALSE)
    }

    latency <- dat[[latency_col]]
  } else {
    if (is.null(response_time_col) || is.null(stimulus_onset_col)) {
      stop(
        "Supply either `latency_col` or both `response_time_col` and `stimulus_onset_col`.",
        call. = FALSE
      )
    }

    if (!response_time_col %in% names(dat)) {
      stop("Column `", response_time_col, "` was not found in `dat`.", call. = FALSE)
    }

    if (!stimulus_onset_col %in% names(dat)) {
      stop("Column `", stimulus_onset_col, "` was not found in `dat`.", call. = FALSE)
    }

    latency <- dat[[response_time_col]] - dat[[stimulus_onset_col]]
  }

  if (!is.numeric(latency)) {
    stop("SCR latency values must be numeric and expressed in seconds.", call. = FALSE)
  }

  out <- dat
  interval <- rep("outside_defined_intervals", nrow(out))
  interval[!is.finite(latency)] <- "missing_latency"

  in_fir <- is.finite(latency) & latency >= fir[1] & latency < fir[2]
  in_sir <- is.finite(latency) & latency >= sir[1] & latency < sir[2]
  in_tir <- is.finite(latency) & latency >= tir[1] & latency <= tir[2]

  interval[in_fir] <- "FIR"
  interval[in_sir] <- "SIR"
  interval[in_tir] <- "TIR"

  out[[latency_output_col]] <- latency
  out[[output_col]] <- interval

  summary <- data.frame(
    input_rows = nrow(out),
    fir_rows = sum(interval == "FIR"),
    sir_rows = sum(interval == "SIR"),
    tir_rows = sum(interval == "TIR"),
    outside_rows = sum(interval == "outside_defined_intervals"),
    missing_latency_rows = sum(interval == "missing_latency"),
    fir_window = paste(fir, collapse = "-"),
    sir_window = paste(sir, collapse = "-"),
    tir_window = paste(tir, collapse = "-"),
    status = "scr_intervals_classified",
    interpretation = paste(
      "FIR, SIR, and TIR labels are latency-window descriptors.",
      "They do not infer emotion, valence, stress, fear, trust, preference, cognition, or diagnosis."
    ),
    stringsAsFactors = FALSE
  )

  attr(out, "scr_interval_summary") <- summary
  attr(out, "scr_interval_settings") <- list(
    response_time_col = response_time_col,
    stimulus_onset_col = stimulus_onset_col,
    latency_col = latency_col,
    output_col = output_col,
    latency_output_col = latency_output_col,
    fir = fir,
    sir = sir,
    tir = tir
  )

  class(out) <- unique(c("gazepoint_scr_intervals", class(out)))

  out
}

gpbiometrics_scr_interval_validate_window <- function(x, name) {
  if (!is.numeric(x) || length(x) != 2 || any(!is.finite(x)) || x[1] >= x[2]) {
    stop("`", name, "` must be a numeric vector of length two with start < end.", call. = FALSE)
  }

  invisible(TRUE)
}

#' Flag EDA artifacts using transparent Kleckner-style heuristics
#'
#' Applies simple transparent EDA artifact flags: non-finite values,
#' physiological range violations, rapid percent change per second, and
#' transitional padding around flagged samples.
#'
#' This helper is Kleckner-style rather than a claim of exact reproduction of
#' every rule in a specific external implementation.
#'
#' @param dat A data frame containing EDA data.
#' @param eda_col Conductance column in microsiemens.
#' @param time_col Optional time column.
#' @param group_cols Optional grouping columns.
#' @param min_us Minimum plausible conductance.
#' @param max_us Maximum plausible conductance.
#' @param max_abs_percent_change_per_second Maximum absolute percent change per
#'   second before flagging.
#' @param transition_padding Number of neighbouring rows to flag around bad
#'   samples within each group.
#' @param output_prefix Prefix for output columns.
#'
#' @return A data frame with artifact flag columns and summary attributes.
#' @export
flag_kleckner_eda_artifacts <- function(dat,
                                        eda_col = "GSR_US",
                                        time_col = NULL,
                                        group_cols = NULL,
                                        min_us = 0.01,
                                        max_us = 100,
                                        max_abs_percent_change_per_second = 20,
                                        transition_padding = 1,
                                        output_prefix = "kleckner") {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  if (!eda_col %in% names(dat)) {
    stop("Column `", eda_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!is.numeric(dat[[eda_col]])) {
    stop("`eda_col` must identify a numeric conductance column.", call. = FALSE)
  }

  if (!is.null(time_col) && !time_col %in% names(dat)) {
    stop("Column `", time_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!is.null(group_cols)) {
    missing_groups <- setdiff(group_cols, names(dat))

    if (length(missing_groups) > 0) {
      stop(
        "The following `group_cols` were not found in `dat`: ",
        paste(missing_groups, collapse = ", "),
        call. = FALSE
      )
    }
  } else {
    group_cols <- character()
  }

  if (!is.numeric(transition_padding) || length(transition_padding) != 1 || transition_padding < 0) {
    stop("`transition_padding` must be a non-negative number.", call. = FALSE)
  }

  transition_padding <- as.integer(transition_padding)

  out <- dat

  nonfinite_col <- paste0(output_prefix, "_nonfinite")
  range_col <- paste0(output_prefix, "_range_artifact")
  rapid_col <- paste0(output_prefix, "_rapid_change_artifact")
  transition_col <- paste0(output_prefix, "_transition_artifact")
  final_col <- paste0(output_prefix, "_artifact")
  status_col <- paste0(output_prefix, "_artifact_status")

  for (nm in c(nonfinite_col, range_col, rapid_col, transition_col, final_col)) {
    out[[nm]] <- FALSE
  }

  out[[status_col]] <- "usable"

  groups <- gpbiometrics_kleckner_split_indices(out, group_cols)

  for (idx in groups) {
    x <- out[[eda_col]][idx]

    nonfinite <- !is.finite(x)
    range_bad <- is.finite(x) & (x < min_us | x > max_us)

    rapid_bad <- rep(FALSE, length(idx))

    if (length(idx) >= 2) {
      dx <- diff(x)

      if (!is.null(time_col)) {
        time_values <- out[[time_col]][idx]
        dt <- diff(time_values)
        dt[!is.finite(dt) | dt <= 0] <- NA_real_
      } else {
        dt <- rep(1, length(dx))
      }

      previous <- x[-length(x)]
      percent_change_per_second <- abs((dx / previous) * 100) / dt

      rapid_pair <- is.finite(percent_change_per_second) &
        percent_change_per_second > max_abs_percent_change_per_second

      rapid_bad[-1] <- rapid_pair
    }

    primary_bad <- nonfinite | range_bad | rapid_bad
    transition_bad <- gpbiometrics_kleckner_expand_flags(primary_bad, transition_padding) & !primary_bad

    out[[nonfinite_col]][idx] <- nonfinite
    out[[range_col]][idx] <- range_bad
    out[[rapid_col]][idx] <- rapid_bad
    out[[transition_col]][idx] <- transition_bad
    out[[final_col]][idx] <- primary_bad | transition_bad
  }

  out[[status_col]][out[[transition_col]]] <- "transition_artifact"
  out[[status_col]][out[[rapid_col]]] <- "rapid_change_artifact"
  out[[status_col]][out[[range_col]]] <- "range_artifact"
  out[[status_col]][out[[nonfinite_col]]] <- "nonfinite_artifact"

  summary <- data.frame(
    input_rows = nrow(out),
    artifact_rows = sum(out[[final_col]], na.rm = TRUE),
    artifact_rate = mean(out[[final_col]], na.rm = TRUE),
    nonfinite_rows = sum(out[[nonfinite_col]], na.rm = TRUE),
    range_artifact_rows = sum(out[[range_col]], na.rm = TRUE),
    rapid_change_artifact_rows = sum(out[[rapid_col]], na.rm = TRUE),
    transition_artifact_rows = sum(out[[transition_col]], na.rm = TRUE),
    min_us = min_us,
    max_us = max_us,
    max_abs_percent_change_per_second = max_abs_percent_change_per_second,
    transition_padding = transition_padding,
    status = "kleckner_style_artifacts_flagged",
    interpretation = paste(
      "These are transparent Kleckner-style EDA quality flags.",
      "They indicate potential signal-quality problems and do not infer emotion, valence, stress, cognition, or diagnosis."
    ),
    stringsAsFactors = FALSE
  )

  attr(out, "kleckner_artifact_summary") <- summary
  attr(out, "kleckner_artifact_settings") <- list(
    eda_col = eda_col,
    time_col = time_col,
    group_cols = group_cols,
    min_us = min_us,
    max_us = max_us,
    max_abs_percent_change_per_second = max_abs_percent_change_per_second,
    transition_padding = transition_padding,
    output_prefix = output_prefix
  )

  class(out) <- unique(c("gazepoint_kleckner_eda_artifacts", class(out)))

  out
}

gpbiometrics_kleckner_split_indices <- function(dat, group_cols) {
  if (length(group_cols) == 0) {
    return(list(all_rows = seq_len(nrow(dat))))
  }

  group_frame <- dat[group_cols]
  group_frame[] <- lapply(group_frame, function(x) {
    x <- as.character(x)
    x[is.na(x)] <- "<NA>"
    x
  })

  group_key <- do.call(paste, c(group_frame, sep = " | "))
  split(seq_len(nrow(dat)), group_key)
}

gpbiometrics_kleckner_expand_flags <- function(flags, padding) {
  if (padding <= 0 || !any(flags)) {
    return(flags)
  }

  out <- flags
  bad_idx <- which(flags)

  for (i in bad_idx) {
    lo <- max(1, i - padding)
    hi <- min(length(flags), i + padding)
    out[lo:hi] <- TRUE
  }

  out
}
