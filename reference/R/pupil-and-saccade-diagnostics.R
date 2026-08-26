#' Baseline-correct Gazepoint pupil size
#'
#' Applies subtractive or divisive baseline correction to pupil-size data within
#' trials or other grouping units.
#'
#' @param dat A data frame containing pupil-size data.
#' @param pupil_col Pupil column. If `NULL`, common Gazepoint pupil columns are
#'   detected.
#' @param time_col Time column.
#' @param stimulus_onset_col Optional stimulus-onset column. If supplied,
#'   baseline windows are interpreted relative to onset.
#' @param trial_cols Trial/grouping columns.
#' @param baseline_window Numeric vector of length two defining the baseline
#'   window relative to stimulus onset.
#' @param baseline_function `"median"` or `"mean"`.
#' @param correction `"subtract"` or `"divide"`.
#' @param suffix Suffix for corrected output column.
#' @param min_baseline_rows Minimum finite baseline rows required.
#' @param overwrite Logical. If `FALSE`, existing output columns are protected.
#'
#' @return A data frame with a corrected pupil column and baseline attributes.
#' @export
baseline_correct_gazepoint_pupil <- function(dat,
                                             pupil_col = NULL,
                                             time_col = "CNT",
                                             stimulus_onset_col = NULL,
                                             trial_cols = NULL,
                                             baseline_window = c(-240, -200),
                                             baseline_function = c("median", "mean"),
                                             correction = c("subtract", "divide"),
                                             suffix = "_baseline_corrected",
                                             min_baseline_rows = 2,
                                             overwrite = FALSE) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  baseline_function <- match.arg(baseline_function)
  correction <- match.arg(correction)

  pupil_col <- gpbiometrics_pupil_resolve_col(dat, pupil_col)

  if (!time_col %in% names(dat)) {
    stop("Column `", time_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!is.null(stimulus_onset_col) && !stimulus_onset_col %in% names(dat)) {
    stop("Column `", stimulus_onset_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (is.null(trial_cols)) {
    trial_cols <- intersect(
      c("source_participant", "participant", "USER_FILE", "source_file", "MEDIA_ID", "trial", "trial_id"),
      names(dat)
    )
  }

  missing_trials <- setdiff(trial_cols, names(dat))

  if (length(missing_trials) > 0) {
    stop(
      "The following `trial_cols` were not found in `dat`: ",
      paste(missing_trials, collapse = ", "),
      call. = FALSE
    )
  }

  if (!is.numeric(baseline_window) || length(baseline_window) != 2 || baseline_window[1] >= baseline_window[2]) {
    stop("`baseline_window` must be a numeric vector of length two with start < end.", call. = FALSE)
  }

  output_col <- paste0(pupil_col, suffix)

  if (!isTRUE(overwrite) && output_col %in% names(dat)) {
    stop(
      "Output column `", output_col, "` already exists. Use `overwrite = TRUE` to replace it.",
      call. = FALSE
    )
  }

  out <- dat
  out[[output_col]] <- NA_real_

  groups <- gpbiometrics_pupil_split_indices(out, trial_cols)

  baseline_rows <- lapply(names(groups), function(unit_id) {
    idx <- groups[[unit_id]]

    if (!is.null(stimulus_onset_col)) {
      relative_time <- out[[time_col]][idx] - out[[stimulus_onset_col]][idx]
    } else {
      relative_time <- out[[time_col]][idx]
    }

    baseline_idx <- idx[
      is.finite(relative_time) &
        relative_time >= baseline_window[1] &
        relative_time <= baseline_window[2]
    ]

    baseline_values <- out[[pupil_col]][baseline_idx]
    baseline_values <- baseline_values[is.finite(baseline_values)]

    status <- "baseline_corrected"
    baseline_value <- NA_real_

    if (length(baseline_values) < min_baseline_rows) {
      status <- "insufficient_baseline_rows"
      out[[output_col]][idx] <<- NA_real_
    } else {
      baseline_value <- if (identical(baseline_function, "median")) {
        stats::median(baseline_values)
      } else {
        mean(baseline_values)
      }

      x <- out[[pupil_col]][idx]

      corrected <- if (identical(correction, "subtract")) {
        x - baseline_value
      } else {
        x / baseline_value
      }

      corrected[!is.finite(corrected)] <- NA_real_
      out[[output_col]][idx] <<- corrected
    }

    data.frame(
      unit_id = unit_id,
      pupil_col = pupil_col,
      output_col = output_col,
      n_rows = length(idx),
      n_baseline_rows = length(baseline_idx),
      n_finite_baseline_rows = length(baseline_values),
      baseline_value = baseline_value,
      status = status,
      stringsAsFactors = FALSE
    )
  })

  baseline_table <- do.call(rbind, baseline_rows)
  rownames(baseline_table) <- NULL

  summary <- data.frame(
    input_rows = nrow(out),
    trial_count = length(groups),
    corrected_trials = sum(baseline_table$status == "baseline_corrected"),
    problem_trials = sum(baseline_table$status != "baseline_corrected"),
    pupil_col = pupil_col,
    output_col = output_col,
    correction = correction,
    baseline_function = baseline_function,
    baseline_window = paste(baseline_window, collapse = " to "),
    status = if (all(baseline_table$status == "baseline_corrected")) {
      "pupil_baseline_correction_complete"
    } else if (any(baseline_table$status == "baseline_corrected")) {
      "pupil_baseline_correction_partial"
    } else {
      "pupil_baseline_correction_failed"
    },
    interpretation = paste(
      "Pupil baseline correction expresses pupil size relative to a trial-level reference period.",
      "It does not infer cognition, workload, emotion, preference, or diagnosis by itself."
    ),
    stringsAsFactors = FALSE
  )

  attr(out, "pupil_baseline_summary") <- summary
  attr(out, "pupil_baseline_table") <- baseline_table
  attr(out, "pupil_baseline_settings") <- list(
    pupil_col = pupil_col,
    time_col = time_col,
    stimulus_onset_col = stimulus_onset_col,
    trial_cols = trial_cols,
    baseline_window = baseline_window,
    baseline_function = baseline_function,
    correction = correction,
    suffix = suffix,
    min_baseline_rows = min_baseline_rows,
    overwrite = overwrite
  )

  class(out) <- unique(c("gazepoint_pupil_baseline_corrected", class(out)))

  out
}

gpbiometrics_pupil_resolve_col <- function(dat, pupil_col = NULL) {
  if (!is.null(pupil_col)) {
    if (!pupil_col %in% names(dat)) {
      stop("Column `", pupil_col, "` was not found in `dat`.", call. = FALSE)
    }

    if (!is.numeric(dat[[pupil_col]])) {
      stop("`pupil_col` must identify a numeric column.", call. = FALSE)
    }

    return(pupil_col)
  }

  candidates <- c("Pupil", "pupil", "pupil_size", "PUPIL", "LPMM", "RPMM", "LPD", "RPD")
  found <- intersect(candidates, names(dat))
  found <- found[vapply(dat[found], is.numeric, logical(1))]

  if (length(found) == 0) {
    stop("No common numeric Gazepoint pupil column was detected. Supply `pupil_col`.", call. = FALSE)
  }

  found[1]
}

gpbiometrics_pupil_split_indices <- function(dat, trial_cols) {
  if (length(trial_cols) == 0) {
    return(list(all_rows = seq_len(nrow(dat))))
  }

  group_frame <- dat[trial_cols]
  group_frame[] <- lapply(group_frame, function(x) {
    x <- as.character(x)
    x[is.na(x)] <- "<NA>"
    x
  })

  group_key <- do.call(paste, c(group_frame, sep = " | "))
  split(seq_len(nrow(dat)), group_key)
}

#' Plot Gazepoint saccade main-sequence diagnostics
#'
#' Plots saccade amplitude against peak velocity. The function expects
#' saccade-level amplitude and peak-velocity columns. If raw sample-level data
#' are supplied, users should first derive saccade-level kinematics with a
#' validated fixation/saccade detector.
#'
#' @param dat A saccade-level data frame.
#' @param amplitude_col Saccade amplitude column.
#' @param peak_velocity_col Peak velocity column.
#' @param group_col Optional grouping column.
#' @param log_axes Logical. If `TRUE`, use log10 axes.
#' @param add_smoother Logical. If `TRUE`, add a lowess curve.
#' @param main Plot title.
#'
#' @return Invisibly returns the plotted data and settings.
#' @export
plot_gazepoint_saccade_main_sequence <- function(dat,
                                                 amplitude_col = NULL,
                                                 peak_velocity_col = NULL,
                                                 group_col = NULL,
                                                 log_axes = TRUE,
                                                 add_smoother = TRUE,
                                                 main = "Gazepoint saccade main-sequence diagnostic") {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  amplitude_col <- gpbiometrics_mainseq_resolve_col(
    dat,
    amplitude_col,
    c("saccade_amplitude", "amplitude", "amplitude_deg", "SACC_AMPLITUDE")
  )

  peak_velocity_col <- gpbiometrics_mainseq_resolve_col(
    dat,
    peak_velocity_col,
    c("peak_velocity", "peak_velocity_deg_s", "saccade_peak_velocity", "SACC_PEAK_VELOCITY")
  )

  if (!is.null(group_col) && !group_col %in% names(dat)) {
    stop("Column `", group_col, "` was not found in `dat`.", call. = FALSE)
  }

  plot_dat <- dat[
    is.finite(dat[[amplitude_col]]) &
      is.finite(dat[[peak_velocity_col]]) &
      dat[[amplitude_col]] > 0 &
      dat[[peak_velocity_col]] > 0,
    ,
    drop = FALSE
  ]

  if (nrow(plot_dat) == 0) {
    stop("No finite positive amplitude/peak-velocity rows are available.", call. = FALSE)
  }

  x <- plot_dat[[amplitude_col]]
  y <- plot_dat[[peak_velocity_col]]

  if (isTRUE(log_axes)) {
    x_plot <- log10(x)
    y_plot <- log10(y)
    xlab <- paste0("log10(", amplitude_col, ")")
    ylab <- paste0("log10(", peak_velocity_col, ")")
  } else {
    x_plot <- x
    y_plot <- y
    xlab <- amplitude_col
    ylab <- peak_velocity_col
  }

  graphics::plot(
    x_plot,
    y_plot,
    xlab = xlab,
    ylab = ylab,
    main = main,
    pch = 19,
    cex = 0.7
  )

  if (isTRUE(add_smoother) && nrow(plot_dat) >= 5) {
    fit <- stats::lowess(x_plot, y_plot)
    graphics::lines(fit, lwd = 2)
  }

  out <- list(
    data = plot_dat,
    settings = list(
      amplitude_col = amplitude_col,
      peak_velocity_col = peak_velocity_col,
      group_col = group_col,
      log_axes = log_axes,
      add_smoother = add_smoother
    ),
    interpretation = paste(
      "This is a saccade-kinematic quality diagnostic.",
      "It should be interpreted only when amplitude and peak velocity were derived from valid saccade-level data."
    )
  )

  invisible(out)
}

gpbiometrics_mainseq_resolve_col <- function(dat, supplied, candidates) {
  if (!is.null(supplied)) {
    if (!supplied %in% names(dat)) {
      stop("Column `", supplied, "` was not found in `dat`.", call. = FALSE)
    }

    if (!is.numeric(dat[[supplied]])) {
      stop("Column `", supplied, "` must be numeric.", call. = FALSE)
    }

    return(supplied)
  }

  found <- intersect(candidates, names(dat))
  found <- found[vapply(dat[found], is.numeric, logical(1))]

  if (length(found) == 0) {
    stop(
      "Could not detect a required saccade kinematic column. Supply it explicitly.",
      call. = FALSE
    )
  }

  found[1]
}
