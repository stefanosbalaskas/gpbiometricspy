#' Plot Gazepoint EDA decomposition channels
#'
#' Plots available EDA/GSR decomposition channels, typically `GSR_US`,
#' `GSR_US_TONIC`, and `GSR_US_PHASIC`, as a ggplot object.
#'
#' @param data A Gazepoint biometric data frame or list containing a data frame.
#' @param time_col Optional time/counter column.
#' @param signal_cols Optional signal columns to plot.
#' @param group_cols Optional grouping columns used for facets.
#' @param standardise Logical. If `TRUE`, standardise each signal to z-scores.
#' @param max_points Maximum number of rows retained after simple downsampling.
#' @param title Optional plot title.
#'
#' @return A ggplot object with plot data stored in attributes.
#' @export
plot_gazepoint_eda_decomposition <- function(data,
                                             time_col = NULL,
                                             signal_cols = NULL,
                                             group_cols = NULL,
                                             standardise = FALSE,
                                             max_points = 5000,
                                             title = NULL) {
  gpbiometrics_require_ggplot2()

  dat <- gpbiometrics_eda_plot_extract_data(data)

  if (is.null(time_col)) {
    time_col <- gpbiometrics_eda_plot_first_existing(
      names(dat),
      c(
        "CNT", "cnt", "time", "Time", "TIME",
        "timestamp", "timestamp_ms", "time_ms"
      )
    )
  }

  if (is.null(time_col) || !time_col %in% names(dat)) {
    stop("No usable time column was found. Supply `time_col`.", call. = FALSE)
  }

  if (is.null(signal_cols)) {
    signal_cols <- gpbiometrics_eda_plot_signal_cols(names(dat))
  }

  signal_cols <- signal_cols[signal_cols %in% names(dat)]

  if (length(signal_cols) == 0) {
    stop("No EDA/GSR signal columns were found. Supply `signal_cols`.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- intersect(
      c(
        "source_file",
        "source_participant",
        "participant",
        "subject",
        "MEDIA_ID",
        "MEDIA_NAME",
        "trial",
        "trial_id"
      ),
      names(dat)
    )
  }

  plot_data <- gpbiometrics_eda_plot_long_data(
    dat = dat,
    time_col = time_col,
    signal_cols = signal_cols,
    group_cols = group_cols,
    standardise = standardise,
    max_points = max_points
  )

  y_label <- if (isTRUE(standardise)) {
    "Standardised signal value"
  } else {
    "Signal value"
  }

  p <- ggplot2::ggplot(
    plot_data,
    ggplot2::aes(
      x = .data_time,
      y = .data_value,
      colour = .data_signal
    )
  ) +
    ggplot2::geom_line(na.rm = TRUE) +
    ggplot2::labs(
      title = if (is.null(title)) "Gazepoint EDA decomposition" else title,
      x = time_col,
      y = y_label,
      colour = "Signal"
    ) +
    ggplot2::theme_minimal()

  if (length(unique(plot_data$.data_group)) > 1) {
    p <- p + ggplot2::facet_wrap(
      stats::as.formula("~ .data_group"),
      scales = "free_x"
    )
  }

  settings <- list(
    time_col = time_col,
    signal_cols = signal_cols,
    group_cols = group_cols,
    standardise = standardise,
    max_points = max_points,
    title = title,
    plot_type = "eda_decomposition",
    interpretation_notes = c(
      "The plot is intended for EDA signal inspection and reporting.",
      "EDA/GSR reflects sympathetic arousal-related activity and should not be interpreted as emotional valence."
    )
  )

  standardise_gazepoint_plot_contract(
    plot = p,
    plot_data = plot_data,
    settings = settings,
    interpretation_notes = settings$interpretation_notes,
    plot_type = "eda_decomposition"
  )
}

#' Plot Gazepoint SCR events on an EDA signal
#'
#' Plots an EDA/GSR signal with detected SCR peak markers and optional event
#' onsets from SCR event-window summaries or event tables.
#'
#' @param data Gazepoint biometric data frame.
#' @param scr_peaks A `gazepoint_scr_peak_detection` object or peak data frame.
#' @param event_windows Optional `gazepoint_scr_event_window_summary` object or
#'   event-window data frame.
#' @param events Optional event table used when `event_windows` is not supplied.
#' @param time_col Optional time/counter column.
#' @param signal_col Optional signal column to plot.
#' @param phasic_col Optional preferred phasic signal column.
#' @param group_cols Optional grouping columns used for facets and matching.
#' @param show_events Logical. If `TRUE`, show event onsets when available.
#' @param max_points Maximum number of signal rows retained after downsampling.
#' @param title Optional plot title.
#'
#' @return A ggplot object with plot data stored in attributes.
#' @export
plot_gazepoint_scr_events <- function(data,
                                      scr_peaks,
                                      event_windows = NULL,
                                      events = NULL,
                                      time_col = NULL,
                                      signal_col = NULL,
                                      phasic_col = NULL,
                                      group_cols = NULL,
                                      show_events = TRUE,
                                      max_points = 5000,
                                      title = NULL) {
  gpbiometrics_require_ggplot2()

  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  dat <- as.data.frame(data, stringsAsFactors = FALSE)

  peaks <- gpbiometrics_scr_plot_extract_peaks(scr_peaks)

  if (is.null(time_col)) {
    time_col <- gpbiometrics_eda_plot_first_existing(
      names(dat),
      c(
        "CNT", "cnt", "time", "Time", "TIME",
        "timestamp", "timestamp_ms", "time_ms"
      )
    )
  }

  if (is.null(time_col) || !time_col %in% names(dat)) {
    stop("No usable time column was found. Supply `time_col`.", call. = FALSE)
  }

  if (is.null(signal_col)) {
    if (!is.null(phasic_col) && phasic_col %in% names(dat)) {
      signal_col <- phasic_col
    } else if (inherits(scr_peaks, "gazepoint_scr_peak_detection") &&
               !is.null(scr_peaks$overview$source_signal) &&
               scr_peaks$overview$source_signal[1] %in% names(dat)) {
      signal_col <- scr_peaks$overview$source_signal[1]
    } else {
      signal_col <- gpbiometrics_eda_plot_first_existing(
        names(dat),
        c("GSR_US_PHASIC", "GSR_US", "GSR", "EDA", "eda_phasic")
      )
    }
  }

  if (is.null(signal_col) || !signal_col %in% names(dat)) {
    stop("No usable EDA/GSR signal column was found. Supply `signal_col`.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- intersect(
      c(
        "source_file",
        "source_participant",
        "participant",
        "subject",
        "MEDIA_ID",
        "MEDIA_NAME",
        "trial",
        "trial_id"
      ),
      names(dat)
    )
  }

  plot_data <- gpbiometrics_eda_plot_long_data(
    dat = dat,
    time_col = time_col,
    signal_cols = signal_col,
    group_cols = group_cols,
    standardise = FALSE,
    max_points = max_points
  )

  peak_plot_data <- gpbiometrics_scr_plot_peak_data(
    peaks = peaks,
    dat = dat,
    time_col = time_col,
    signal_col = signal_col,
    group_cols = group_cols
  )

  event_plot_data <- if (isTRUE(show_events)) {
    gpbiometrics_scr_plot_event_data(
      event_windows = event_windows,
      events = events,
      group_cols = group_cols
    )
  } else {
    data.frame()
  }

  p <- ggplot2::ggplot(
    plot_data,
    ggplot2::aes(
      x = .data_time,
      y = .data_value
    )
  ) +
    ggplot2::geom_line(na.rm = TRUE) +
    ggplot2::labs(
      title = if (is.null(title)) "Gazepoint SCR events" else title,
      x = time_col,
      y = signal_col
    ) +
    ggplot2::theme_minimal()

  if (nrow(event_plot_data) > 0) {
    p <- p + ggplot2::geom_vline(
      data = event_plot_data,
      ggplot2::aes(xintercept = .event_time),
      inherit.aes = FALSE,
      linetype = "dashed",
      alpha = 0.5
    )
  }

  if (nrow(peak_plot_data) > 0) {
    p <- p + ggplot2::geom_point(
      data = peak_plot_data,
      ggplot2::aes(
        x = .data_time,
        y = .data_value
      ),
      inherit.aes = FALSE,
      na.rm = TRUE
    )
  }

  if (length(unique(plot_data$.data_group)) > 1) {
    p <- p + ggplot2::facet_wrap(
      stats::as.formula("~ .data_group"),
      scales = "free_x"
    )
  }

  settings <- list(
    time_col = time_col,
    signal_col = signal_col,
    group_cols = group_cols,
    show_events = show_events,
    max_points = max_points,
    title = title,
    event_windows = !is.null(event_windows),
    events = !is.null(events),
    scr_peaks = !is.null(scr_peaks),
    plot_type = "scr_events",
    interpretation_notes = c(
      "SCR peak markers show detected electrodermal response features.",
      "Visual inspection should be used as a QC aid, not as emotional-valence inference."
    )
  )

  p <- standardise_gazepoint_plot_contract(
    plot = p,
    plot_data = plot_data,
    settings = settings,
    interpretation_notes = settings$interpretation_notes,
    plot_type = "scr_events"
  )

  attr(p, "peak_data") <- peak_plot_data
  attr(p, "event_data") <- event_plot_data

  p
}

gpbiometrics_require_ggplot2 <- function() {
  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    stop("Package `ggplot2` is required for this plotting helper.", call. = FALSE)
  }

  invisible(TRUE)
}

gpbiometrics_eda_plot_extract_data <- function(data) {
  if (is.data.frame(data)) {
    return(as.data.frame(data, stringsAsFactors = FALSE))
  }

  if (is.list(data)) {
    candidates <- c(
      "data",
      "decomposition",
      "decomposed_data",
      "signals",
      "aligned_data"
    )

    for (nm in candidates) {
      if (!is.null(data[[nm]]) && is.data.frame(data[[nm]])) {
        return(as.data.frame(data[[nm]], stringsAsFactors = FALSE))
      }
    }

    data_frames <- vapply(data, is.data.frame, logical(1))

    if (any(data_frames)) {
      return(as.data.frame(data[[which(data_frames)[1]]], stringsAsFactors = FALSE))
    }
  }

  stop("`data` must be a data frame or a list containing a data frame.", call. = FALSE)
}

gpbiometrics_eda_plot_first_existing <- function(names_dat, candidates) {
  exact <- candidates[candidates %in% names_dat]

  if (length(exact) > 0) {
    return(exact[1])
  }

  lower_names <- tolower(names_dat)
  lower_candidates <- tolower(candidates)
  idx <- match(lower_candidates, lower_names)
  idx <- idx[!is.na(idx)]

  if (length(idx) > 0) {
    return(names_dat[idx[1]])
  }

  NULL
}

gpbiometrics_eda_plot_signal_cols <- function(names_dat) {
  candidates <- c(
    "GSR_US",
    "GSR_US_TONIC",
    "GSR_US_PHASIC",
    "GSR",
    "EDA",
    "eda",
    "eda_clean",
    "eda_tonic",
    "eda_phasic"
  )

  unique(candidates[candidates %in% names_dat])
}

gpbiometrics_eda_plot_group_id <- function(dat, group_cols) {
  if (length(group_cols) == 0 || !all(group_cols %in% names(dat))) {
    return(rep("all", nrow(dat)))
  }

  group_dat <- dat[group_cols]

  group_dat[] <- lapply(group_dat, function(x) {
    x_chr <- as.character(x)
    x_chr[is.na(x_chr)] <- "<NA>"
    x_chr
  })

  apply(group_dat, 1, paste, collapse = "||")
}

gpbiometrics_eda_plot_downsample <- function(dat, max_points) {
  if (!is.numeric(max_points) ||
      length(max_points) != 1 ||
      !is.finite(max_points) ||
      max_points < 1) {
    stop("`max_points` must be a positive finite number.", call. = FALSE)
  }

  if (nrow(dat) <= max_points) {
    return(dat)
  }

  idx <- unique(round(seq(1, nrow(dat), length.out = max_points)))
  dat[idx, , drop = FALSE]
}

gpbiometrics_eda_plot_long_data <- function(dat,
                                            time_col,
                                            signal_cols,
                                            group_cols,
                                            standardise,
                                            max_points) {
  dat <- gpbiometrics_eda_plot_downsample(dat, max_points)

  time_value <- suppressWarnings(as.numeric(dat[[time_col]]))
  group_id <- gpbiometrics_eda_plot_group_id(dat, group_cols)

  out <- lapply(signal_cols, function(signal_col) {
    value <- suppressWarnings(as.numeric(dat[[signal_col]]))

    if (isTRUE(standardise)) {
      finite_value <- value[is.finite(value)]
      value_mean <- if (length(finite_value) > 0) {
        mean(finite_value, na.rm = TRUE)
      } else {
        NA_real_
      }
      value_sd <- if (length(finite_value) > 1) {
        stats::sd(finite_value, na.rm = TRUE)
      } else {
        NA_real_
      }

      value <- if (is.finite(value_sd) && value_sd > 0) {
        (value - value_mean) / value_sd
      } else {
        ifelse(is.na(value), NA_real_, 0)
      }
    }

    data.frame(
      .data_time = time_value,
      .data_value = value,
      .data_signal = signal_col,
      .data_group = group_id,
      stringsAsFactors = FALSE
    )
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}

gpbiometrics_scr_plot_extract_peaks <- function(scr_peaks) {
  if (inherits(scr_peaks, "gazepoint_scr_peak_detection") &&
      !is.null(scr_peaks$peaks)) {
    return(as.data.frame(scr_peaks$peaks, stringsAsFactors = FALSE))
  }

  if (is.data.frame(scr_peaks)) {
    return(as.data.frame(scr_peaks, stringsAsFactors = FALSE))
  }

  stop("`scr_peaks` must be an SCR peak-detection object or a data frame.", call. = FALSE)
}

gpbiometrics_scr_plot_peak_data <- function(peaks,
                                            dat,
                                            time_col,
                                            signal_col,
                                            group_cols) {
  if (nrow(peaks) == 0 || !"peak_time" %in% names(peaks)) {
    return(data.frame())
  }

  dat_group <- gpbiometrics_eda_plot_group_id(dat, group_cols)
  peak_group <- gpbiometrics_eda_plot_group_id(peaks, group_cols)

  if ("event_group_id" %in% names(peaks) && length(group_cols) > 0) {
    peak_group <- as.character(peaks$event_group_id)
  } else if ("group_id" %in% names(peaks) && length(group_cols) == 0) {
    peak_group <- as.character(peaks$group_id)
  }

  time_value <- suppressWarnings(as.numeric(dat[[time_col]]))
  signal_value <- suppressWarnings(as.numeric(dat[[signal_col]]))
  peak_time <- suppressWarnings(as.numeric(peaks$peak_time))

  out <- lapply(seq_len(nrow(peaks)), function(i) {
    g <- peak_group[i]

    candidate <- which(dat_group == g & is.finite(time_value))

    if (length(candidate) == 0 || !is.finite(peak_time[i])) {
      peak_value <- NA_real_
    } else {
      nearest <- candidate[which.min(abs(time_value[candidate] - peak_time[i]))]
      peak_value <- signal_value[nearest]
    }

    data.frame(
      .data_time = peak_time[i],
      .data_value = peak_value,
      .data_group = g,
      stringsAsFactors = FALSE
    )
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}

gpbiometrics_scr_plot_event_data <- function(event_windows = NULL,
                                             events = NULL,
                                             group_cols = NULL) {
  event_table <- NULL

  if (!is.null(event_windows)) {
    if (inherits(event_windows, "gazepoint_scr_event_window_summary") &&
        !is.null(event_windows$event_table)) {
      event_table <- as.data.frame(event_windows$event_table, stringsAsFactors = FALSE)
    } else if (is.data.frame(event_windows)) {
      event_table <- as.data.frame(event_windows, stringsAsFactors = FALSE)
    }
  } else if (!is.null(events) && is.data.frame(events)) {
    event_table <- as.data.frame(events, stringsAsFactors = FALSE)
  }

  if (is.null(event_table) || nrow(event_table) == 0) {
    return(data.frame())
  }

  event_time_col <- gpbiometrics_eda_plot_first_existing(
    names(event_table),
    c(
      "event_time",
      "onset_time",
      "stimulus_time",
      "time",
      "Time",
      "CNT"
    )
  )

  if (is.null(event_time_col)) {
    return(data.frame())
  }

  event_group <- if (length(group_cols) > 0 &&
                     all(group_cols %in% names(event_table))) {
    gpbiometrics_eda_plot_group_id(event_table, group_cols)
  } else if ("event_group_id" %in% names(event_table)) {
    as.character(event_table$event_group_id)
  } else {
    gpbiometrics_eda_plot_group_id(event_table, group_cols)
  }

  out <- data.frame(
    .event_time = suppressWarnings(as.numeric(event_table[[event_time_col]])),
    .data_group = event_group,
    stringsAsFactors = FALSE
  )

  out[is.finite(out$.event_time), , drop = FALSE]
}
