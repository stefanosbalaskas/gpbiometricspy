#' Plot multimodal Gazepoint biometric timelines
#'
#' Creates a conservative timeline plot for one or more biometric channels. The
#' plot is intended for inspection, synchronization checks, and reporting
#' support. It does not interpret electrodermal activity as emotional valence.
#'
#' @param data A data frame containing biometric samples or aligned biometric
#'   rows.
#' @param time_col Optional time column. If `NULL`, common time columns are
#'   detected automatically.
#' @param signal_cols Optional biometric signal columns. If `NULL`, common
#'   Gazepoint biometric columns are detected automatically.
#' @param group_cols Optional grouping columns used to separate trajectories.
#' @param participant_col,stimulus_col,trial_col Optional common grouping columns
#'   to add to `group_cols`.
#' @param event_time_col Optional column containing event times for vertical
#'   markers.
#' @param event_col Optional event/TTL indicator column used for vertical markers.
#' @param standardise Logical. If `TRUE`, signals are z-scored within channel for
#'   visual comparison.
#' @param show_event_markers Logical. Should event markers be drawn when
#'   available?
#' @param title Optional plot title.
#'
#' @return A ggplot object with the long plotting data stored in the `plot_data`
#'   attribute and settings stored in the `settings` attribute.
#' @export
plot_gazepoint_multimodal_timeline <- function(data,
                                               time_col = NULL,
                                               signal_cols = NULL,
                                               group_cols = NULL,
                                               participant_col = NULL,
                                               stimulus_col = NULL,
                                               trial_col = NULL,
                                               event_time_col = NULL,
                                               event_col = NULL,
                                               standardise = TRUE,
                                               show_event_markers = TRUE,
                                               title = NULL) {
  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    stop("Package `ggplot2` is required for timeline plotting.", call. = FALSE)
  }

  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (!is.logical(standardise) || length(standardise) != 1 || is.na(standardise)) {
    stop("`standardise` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.logical(show_event_markers) ||
      length(show_event_markers) != 1 ||
      is.na(show_event_markers)) {
    stop("`show_event_markers` must be TRUE or FALSE.", call. = FALSE)
  }

  dat <- as.data.frame(data, stringsAsFactors = FALSE)

  if (nrow(dat) == 0) {
    stop("`data` has no rows to plot.", call. = FALSE)
  }

  names_dat <- names(dat)

  if (is.null(time_col)) {
    time_col <- gpbiometrics_timeline_first_existing(
      names_dat,
      c(
        "event_relative_time_ms",
        "time_ms",
        "timestamp_ms",
        "timestamp",
        "TIME",
        "Time",
        "time",
        "CNT",
        "cnt"
      )
    )
  }

  if (is.null(time_col) || !time_col %in% names_dat) {
    stop("No usable time column was found. Supply `time_col`.", call. = FALSE)
  }

  time_value <- suppressWarnings(as.numeric(dat[[time_col]]))

  if (all(is.na(time_value))) {
    stop("`time_col` must contain numeric values.", call. = FALSE)
  }

  if (is.null(signal_cols)) {
    signal_cols <- gpbiometrics_timeline_infer_signal_cols(names_dat)
  }

  signal_cols <- unique(signal_cols)

  if (length(signal_cols) == 0) {
    stop("No biometric signal columns were found. Supply `signal_cols`.", call. = FALSE)
  }

  missing_signal_cols <- setdiff(signal_cols, names_dat)

  if (length(missing_signal_cols) > 0) {
    stop(
      "`signal_cols` not found in `data`: ",
      paste(missing_signal_cols, collapse = ", "),
      call. = FALSE
    )
  }

  numeric_signal <- vapply(
    signal_cols,
    function(col) {
      x <- suppressWarnings(as.numeric(dat[[col]]))
      !all(is.na(x))
    },
    logical(1)
  )

  signal_cols <- signal_cols[numeric_signal]

  if (length(signal_cols) == 0) {
    stop("None of the selected signal columns contain numeric values.", call. = FALSE)
  }

  group_cols <- gpbiometrics_timeline_resolve_group_cols(
    names_dat = names_dat,
    group_cols = group_cols,
    participant_col = participant_col,
    stimulus_col = stimulus_col,
    trial_col = trial_col
  )

  missing_group_cols <- setdiff(group_cols, names_dat)

  if (length(missing_group_cols) > 0) {
    stop(
      "`group_cols` not found in `data`: ",
      paste(missing_group_cols, collapse = ", "),
      call. = FALSE
    )
  }

  panel_group <- gpbiometrics_timeline_group_id(dat, group_cols)

  long_data <- gpbiometrics_timeline_long_data(
    dat = dat,
    time_value = time_value,
    time_col = time_col,
    signal_cols = signal_cols,
    panel_group = panel_group,
    standardise = standardise
  )

  y_label <- if (isTRUE(standardise)) {
    "Standardised signal value"
  } else {
    "Signal value"
  }

  p <- ggplot2::ggplot(
    long_data,
    ggplot2::aes(
      x = .data_time,
      y = .data_value,
      group = interaction(.data_group, .data_signal, drop = TRUE)
    )
  ) +
    ggplot2::geom_line(na.rm = TRUE, alpha = 0.7) +
    ggplot2::facet_wrap(stats::as.formula("~ .data_signal"), scales = "free_y") +
    ggplot2::labs(
      x = time_col,
      y = y_label,
      title = title
    ) +
    ggplot2::theme_minimal()

  event_times <- numeric()
  event_data <- data.frame()

  if (isTRUE(show_event_markers)) {
    event_times <- gpbiometrics_timeline_event_times(
      dat = dat,
      time_value = time_value,
      time_col = time_col,
      event_time_col = event_time_col,
      event_col = event_col
    )

    if (length(event_times) > 0) {
      event_data <- data.frame(.event_time = unique(event_times))
      p <- p +
        ggplot2::geom_vline(
          data = event_data,
          ggplot2::aes(xintercept = .event_time),
          inherit.aes = FALSE,
          linetype = "dashed",
          alpha = 0.35
        )
    }
  }

  settings <- list(
    time_col = time_col,
    signal_cols = signal_cols,
    group_cols = group_cols,
    event_time_col = event_time_col,
    event_col = event_col,
    standardise = standardise,
    show_event_markers = show_event_markers,
    event_times = event_times,
    title = title,
    plot_type = "multimodal_timeline",
    interpretation_notes = c(
      "The plot is intended for multimodal signal inspection, synchronization checks, and reporting support.",
      "EDA/GSR and related biometric traces should not be interpreted as emotional valence.",
      "Standardised traces support visual comparison only and do not replace signal-specific modelling."
    )
  )

  p <- standardise_gazepoint_plot_contract(
    plot = p,
    plot_data = long_data,
    settings = settings,
    interpretation_notes = settings$interpretation_notes,
    plot_type = "multimodal_timeline"
  )

  attr(p, "event_data") <- event_data

  p
}

gpbiometrics_timeline_first_existing <- function(names_dat, candidates) {
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

gpbiometrics_timeline_infer_signal_cols <- function(names_dat) {
  candidates <- c(
    "GSR_US",
    "gsr_us",
    "GSR_US_TONIC",
    "gsr_us_tonic",
    "GSR_US_PHASIC",
    "gsr_us_phasic",
    "GSR",
    "gsr",
    "HR",
    "hr",
    "IBI",
    "ibi",
    "DIAL",
    "dial"
  )

  candidates[candidates %in% names_dat]
}

gpbiometrics_timeline_resolve_group_cols <- function(names_dat,
                                                     group_cols,
                                                     participant_col,
                                                     stimulus_col,
                                                     trial_col) {
  explicit <- unique(stats::na.omit(c(
    group_cols,
    participant_col,
    stimulus_col,
    trial_col
  )))

  if (length(explicit) > 0) {
    return(explicit)
  }

  participant <- gpbiometrics_timeline_first_existing(
    names_dat,
    c("participant", "subject", "subject_id", "USER", "USER_FILE", "user_file")
  )

  stimulus <- gpbiometrics_timeline_first_existing(
    names_dat,
    c("stimulus", "stimulus_id", "MEDIA_ID", "MEDIA_NAME", "media_id", "media_name")
  )

  trial <- gpbiometrics_timeline_first_existing(
    names_dat,
    c("trial", "trial_id", "TRIAL", "trial_global")
  )

  unique(stats::na.omit(c(participant, stimulus, trial)))
}

gpbiometrics_timeline_group_id <- function(dat, group_cols) {
  if (length(group_cols) == 0) {
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

gpbiometrics_timeline_long_data <- function(dat,
                                            time_value,
                                            time_col,
                                            signal_cols,
                                            panel_group,
                                            standardise) {
  parts <- vector("list", length(signal_cols))

  for (i in seq_along(signal_cols)) {
    signal <- signal_cols[i]
    value_raw <- suppressWarnings(as.numeric(dat[[signal]]))

    value_plot <- value_raw

    if (isTRUE(standardise)) {
      value_mean <- mean(value_raw, na.rm = TRUE)
      value_sd <- stats::sd(value_raw, na.rm = TRUE)

      if (is.finite(value_sd) && value_sd > 0) {
        value_plot <- (value_raw - value_mean) / value_sd
      } else {
        value_plot <- ifelse(is.na(value_raw), NA_real_, 0)
      }
    }

    parts[[i]] <- data.frame(
      .data_time = time_value,
      .data_value = value_plot,
      .data_value_raw = value_raw,
      .data_signal = signal,
      .data_group = panel_group,
      .data_row_id = seq_len(nrow(dat)),
      stringsAsFactors = FALSE
    )
  }

  out <- do.call(rbind, parts)
  rownames(out) <- NULL

  out
}

gpbiometrics_timeline_event_times <- function(dat,
                                              time_value,
                                              time_col,
                                              event_time_col,
                                              event_col) {
  event_times <- numeric()

  if (!is.null(event_time_col)) {
    if (!event_time_col %in% names(dat)) {
      stop("`event_time_col` was not found in `data`.", call. = FALSE)
    }

    event_times <- suppressWarnings(as.numeric(dat[[event_time_col]]))
    event_times <- event_times[is.finite(event_times)]
    return(unique(event_times))
  }

  if (!is.null(event_col)) {
    if (!event_col %in% names(dat)) {
      stop("`event_col` was not found in `data`.", call. = FALSE)
    }

    active <- gpbiometrics_timeline_active_event(dat[[event_col]])
    event_times <- time_value[active & is.finite(time_value)]
    return(unique(event_times))
  }

  if (identical(time_col, "event_relative_time_ms") ||
      identical(time_col, "event_relative_time")) {
    return(0)
  }

  numeric()
}

gpbiometrics_timeline_active_event <- function(x) {
  if (is.logical(x)) {
    return(!is.na(x) & x)
  }

  if (is.numeric(x)) {
    return(!is.na(x) & x != 0)
  }

  x_chr <- trimws(as.character(x))
  x_chr[is.na(x_chr)] <- ""

  x_num <- suppressWarnings(as.numeric(x_chr))

  if (sum(!is.na(x_num) & x_chr != "") >= max(1, sum(x_chr != "") / 2)) {
    return(!is.na(x_num) & x_num != 0)
  }

  x_chr != "" & !toupper(x_chr) %in% c("0", "FALSE", "F", "NA", "NAN", "NULL")
}
