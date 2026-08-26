#' Model EDA events as a dependency-light point process
#'
#' Creates event-time, inter-event interval, and inverse-Gaussian-style summary
#' tables for EDA/SCR events. Events can be supplied directly through an event
#' column or derived from positive EDA-derivative bursts.
#'
#' This function is a compact point-process summary/model-preparation helper. It
#' does not fit a full latent sympathetic state-space model.
#'
#' @param dat A data frame.
#' @param eda_col Numeric EDA column.
#' @param time_col Numeric time column.
#' @param group_cols Optional grouping columns.
#' @param event_time_col Optional column of event onset times.
#' @param event_indicator_col Optional binary event indicator column.
#' @param derivative_mad_multiplier MAD multiplier for derivative-derived events.
#' @param min_event_distance_s Minimum distance between derived events.
#'
#' @return A list with `overview`, `event_table`, `interval_table`,
#'   `process_summary`, and `settings`.
#' @export
model_gazepoint_eda_point_process <- function(dat,
                                              eda_col = "GSR_US",
                                              time_col = "CNT",
                                              group_cols = NULL,
                                              event_time_col = NULL,
                                              event_indicator_col = NULL,
                                              derivative_mad_multiplier = 6,
                                              min_event_distance_s = 1) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  required <- c(eda_col, time_col, event_time_col, event_indicator_col)
  required <- required[!is.null(required)]

  missing_required <- setdiff(required, names(dat))
  if (length(missing_required) > 0) {
    stop("Missing required columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  if (!is.numeric(dat[[eda_col]])) {
    stop("`eda_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.numeric(dat[[time_col]])) {
    stop("`time_col` must identify a numeric column.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  missing_groups <- setdiff(group_cols, names(dat))
  if (length(missing_groups) > 0) {
    stop("Missing `group_cols`: ", paste(missing_groups, collapse = ", "), call. = FALSE)
  }

  groups <- gpbiometrics_pp_split(dat, group_cols)

  event_rows <- list()
  interval_rows <- list()
  summary_rows <- list()
  event_id <- 1L
  interval_id <- 1L

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]
    idx <- idx[order(dat[[time_col]][idx])]

    time <- dat[[time_col]][idx]
    eda <- dat[[eda_col]][idx]

    event_times <- gpbiometrics_eda_pp_events(
      dat = dat,
      idx = idx,
      time_col = time_col,
      eda_col = eda_col,
      event_time_col = event_time_col,
      event_indicator_col = event_indicator_col,
      derivative_mad_multiplier = derivative_mad_multiplier,
      min_event_distance_s = min_event_distance_s
    )

    event_times <- sort(unique(event_times[is.finite(event_times)]))

    for (i in seq_along(event_times)) {
      event_rows[[event_id]] <- data.frame(
        group_id = group_id,
        event_index = i,
        event_time = event_times[i],
        event_source = if (!is.null(event_time_col)) {
          "event_time_col"
        } else if (!is.null(event_indicator_col)) {
          "event_indicator_col"
        } else {
          "eda_derivative"
        },
        stringsAsFactors = FALSE
      )
      event_id <- event_id + 1L
    }

    intervals <- diff(event_times)

    if (length(intervals) > 0) {
      for (i in seq_along(intervals)) {
        interval_rows[[interval_id]] <- data.frame(
          group_id = group_id,
          interval_index = i,
          start_time = event_times[i],
          end_time = event_times[i + 1],
          inter_event_interval_s = intervals[i],
          stringsAsFactors = FALSE
        )
        interval_id <- interval_id + 1L
      }
    }

    duration <- max(time, na.rm = TRUE) - min(time, na.rm = TRUE)
    ig <- gpbiometrics_pp_inverse_gaussian_summary(intervals)

    summary_rows[[group_id]] <- data.frame(
      group_id = group_id,
      n_samples = length(idx),
      n_events = length(event_times),
      duration_s = duration,
      event_rate_per_min = if (is.finite(duration) && duration > 0) {
        length(event_times) / duration * 60
      } else {
        NA_real_
      },
      mean_inter_event_interval_s = if (length(intervals) > 0) mean(intervals) else NA_real_,
      inverse_gaussian_mu = ig$mu,
      inverse_gaussian_lambda = ig$lambda,
      interval_cv = ig$cv,
      status = if (length(event_times) >= 3) {
        "eda_point_process_summarised"
      } else {
        "insufficient_eda_events"
      },
      stringsAsFactors = FALSE
    )
  }

  event_table <- if (length(event_rows) > 0) do.call(rbind, event_rows) else data.frame()
  interval_table <- if (length(interval_rows) > 0) do.call(rbind, interval_rows) else data.frame()
  process_summary <- do.call(rbind, summary_rows)
  rownames(process_summary) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    event_rows = nrow(event_table),
    interval_rows = nrow(interval_table),
    successful_groups = sum(process_summary$status == "eda_point_process_summarised"),
    problem_groups = sum(process_summary$status != "eda_point_process_summarised"),
    status = if (all(process_summary$status == "eda_point_process_summarised")) {
      "eda_point_process_complete"
    } else if (any(process_summary$status == "eda_point_process_summarised")) {
      "eda_point_process_partial"
    } else {
      "eda_point_process_insufficient_events"
    },
    interpretation = paste(
      "EDA point-process summaries describe event timing and inter-event intervals.",
      "They do not estimate latent sympathetic nerve firing or arousal states by themselves."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      event_table = event_table,
      interval_table = interval_table,
      process_summary = process_summary,
      settings = list(
        eda_col = eda_col,
        time_col = time_col,
        group_cols = group_cols,
        event_time_col = event_time_col,
        event_indicator_col = event_indicator_col,
        derivative_mad_multiplier = derivative_mad_multiplier,
        min_event_distance_s = min_event_distance_s
      )
    ),
    class = c("gazepoint_eda_point_process", "list")
  )
}

#' Model heartbeats as a dependency-light point process
#'
#' Creates beat-time, interbeat interval, and inverse-Gaussian-style summary
#' tables from IBI/RR intervals. This is a compact point-process
#' model-preparation helper, not a full adaptive Bayesian heartbeat filter.
#'
#' @param dat A data frame.
#' @param ibi_col Numeric IBI/RR interval column.
#' @param time_col Optional time column.
#' @param beat_time_col Optional explicit beat-time column.
#' @param group_cols Optional grouping columns.
#' @param ibi_units `"auto"`, `"seconds"`, or `"milliseconds"`.
#'
#' @return A list with `overview`, `beat_table`, `interval_table`,
#'   `process_summary`, and `settings`.
#' @export
model_gazepoint_hr_point_process <- function(dat,
                                             ibi_col = "IBI",
                                             time_col = NULL,
                                             beat_time_col = NULL,
                                             group_cols = NULL,
                                             ibi_units = c("auto", "seconds", "milliseconds")) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  ibi_units <- match.arg(ibi_units)

  required <- c(ibi_col, time_col, beat_time_col)
  required <- required[!is.null(required)]

  missing_required <- setdiff(required, names(dat))
  if (length(missing_required) > 0) {
    stop("Missing required columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  if (!is.numeric(dat[[ibi_col]])) {
    stop("`ibi_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.null(time_col) && !is.numeric(dat[[time_col]])) {
    stop("`time_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.null(beat_time_col) && !is.numeric(dat[[beat_time_col]])) {
    stop("`beat_time_col` must identify a numeric column.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  missing_groups <- setdiff(group_cols, names(dat))
  if (length(missing_groups) > 0) {
    stop("Missing `group_cols`: ", paste(missing_groups, collapse = ", "), call. = FALSE)
  }

  groups <- gpbiometrics_pp_split(dat, group_cols)

  beat_rows <- list()
  interval_rows <- list()
  summary_rows <- list()
  beat_id <- 1L
  interval_id <- 1L

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]

    if (!is.null(time_col)) {
      idx <- idx[order(dat[[time_col]][idx])]
    }

    ibi <- dat[[ibi_col]][idx]
    ibi <- ibi[is.finite(ibi) & ibi > 0]
    ibi_s <- gpbiometrics_pp_ibi_to_seconds(ibi, ibi_units)

    if (!is.null(beat_time_col)) {
      beat_time <- dat[[beat_time_col]][idx]
      beat_time <- beat_time[is.finite(beat_time)]
      beat_time <- sort(unique(beat_time))
      intervals <- diff(beat_time)
    } else {
      beat_time <- cumsum(ibi_s)
      intervals <- ibi_s
    }

    for (i in seq_along(beat_time)) {
      beat_rows[[beat_id]] <- data.frame(
        group_id = group_id,
        beat_index = i,
        beat_time = beat_time[i],
        instantaneous_hr_bpm = if (i <= length(ibi_s) && ibi_s[i] > 0) 60 / ibi_s[i] else NA_real_,
        stringsAsFactors = FALSE
      )
      beat_id <- beat_id + 1L
    }

    intervals <- intervals[is.finite(intervals) & intervals > 0]

    for (i in seq_along(intervals)) {
      interval_rows[[interval_id]] <- data.frame(
        group_id = group_id,
        interval_index = i,
        interbeat_interval_s = intervals[i],
        stringsAsFactors = FALSE
      )
      interval_id <- interval_id + 1L
    }

    ig <- gpbiometrics_pp_inverse_gaussian_summary(intervals)

    summary_rows[[group_id]] <- data.frame(
      group_id = group_id,
      n_beats = length(beat_time),
      n_intervals = length(intervals),
      mean_interbeat_interval_s = if (length(intervals) > 0) mean(intervals) else NA_real_,
      mean_hr_bpm = if (length(intervals) > 0) 60 / mean(intervals) else NA_real_,
      inverse_gaussian_mu = ig$mu,
      inverse_gaussian_lambda = ig$lambda,
      interval_cv = ig$cv,
      status = if (length(intervals) >= 5) {
        "hr_point_process_summarised"
      } else {
        "insufficient_heartbeats"
      },
      stringsAsFactors = FALSE
    )
  }

  beat_table <- if (length(beat_rows) > 0) do.call(rbind, beat_rows) else data.frame()
  interval_table <- if (length(interval_rows) > 0) do.call(rbind, interval_rows) else data.frame()
  process_summary <- do.call(rbind, summary_rows)
  rownames(process_summary) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    beat_rows = nrow(beat_table),
    interval_rows = nrow(interval_table),
    successful_groups = sum(process_summary$status == "hr_point_process_summarised"),
    problem_groups = sum(process_summary$status != "hr_point_process_summarised"),
    status = if (all(process_summary$status == "hr_point_process_summarised")) {
      "hr_point_process_complete"
    } else if (any(process_summary$status == "hr_point_process_summarised")) {
      "hr_point_process_partial"
    } else {
      "hr_point_process_insufficient_beats"
    },
    interpretation = paste(
      "HR point-process summaries describe heartbeat timing and interval distributions.",
      "They are not adaptive Bayesian heartbeat filters or clinical diagnoses by themselves."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      beat_table = beat_table,
      interval_table = interval_table,
      process_summary = process_summary,
      settings = list(
        ibi_col = ibi_col,
        time_col = time_col,
        beat_time_col = beat_time_col,
        group_cols = group_cols,
        ibi_units = ibi_units
      )
    ),
    class = c("gazepoint_hr_point_process", "list")
  )
}

gpbiometrics_pp_split <- function(dat, group_cols) {
  if (length(group_cols) == 0) {
    return(list(all_rows = seq_len(nrow(dat))))
  }

  gf <- dat[group_cols]
  gf[] <- lapply(gf, function(x) {
    x <- as.character(x)
    x[is.na(x)] <- "<NA>"
    x
  })

  split(seq_len(nrow(dat)), do.call(paste, c(gf, sep = " | ")))
}

gpbiometrics_eda_pp_events <- function(dat,
                                       idx,
                                       time_col,
                                       eda_col,
                                       event_time_col = NULL,
                                       event_indicator_col = NULL,
                                       derivative_mad_multiplier = 6,
                                       min_event_distance_s = 1) {
  if (!is.null(event_time_col)) {
    return(dat[[event_time_col]][idx])
  }

  time <- dat[[time_col]][idx]

  if (!is.null(event_indicator_col)) {
    indicator <- dat[[event_indicator_col]][idx]
    event_idx <- which(is.finite(indicator) & indicator > 0)
    return(time[event_idx])
  }

  eda <- dat[[eda_col]][idx]
  finite <- is.finite(time) & is.finite(eda)

  time <- time[finite]
  eda <- eda[finite]

  if (length(time) < 5) {
    return(numeric())
  }

  dt <- diff(time)
  dx <- diff(eda)

  derivative <- dx / dt
  derivative[!is.finite(derivative)] <- NA_real_

  center <- stats::median(derivative, na.rm = TRUE)
  mad_value <- stats::mad(derivative, constant = 1, na.rm = TRUE)

  if (!is.finite(mad_value) || mad_value == 0) {
    mad_value <- .Machine$double.eps
  }

  threshold <- center + derivative_mad_multiplier * mad_value
  candidate <- which(is.finite(derivative) & derivative > threshold) + 1L

  if (length(candidate) == 0) {
    return(numeric())
  }

  selected <- candidate[1]

  if (length(candidate) > 1) {
    for (i in candidate[-1]) {
      if ((time[i] - time[selected[length(selected)]]) >= min_event_distance_s) {
        selected <- c(selected, i)
      } else if (eda[i] > eda[selected[length(selected)]]) {
        selected[length(selected)] <- i
      }
    }
  }

  time[selected]
}

gpbiometrics_pp_inverse_gaussian_summary <- function(intervals) {
  intervals <- intervals[is.finite(intervals) & intervals > 0]

  if (length(intervals) < 2) {
    return(list(mu = NA_real_, lambda = NA_real_, cv = NA_real_))
  }

  mu <- mean(intervals)
  variance <- stats::var(intervals)

  lambda <- if (is.finite(variance) && variance > 0) {
    mu^3 / variance
  } else {
    NA_real_
  }

  cv <- if (is.finite(mu) && mu > 0) {
    stats::sd(intervals) / mu
  } else {
    NA_real_
  }

  list(mu = mu, lambda = lambda, cv = cv)
}

gpbiometrics_pp_ibi_to_seconds <- function(ibi, ibi_units = "auto") {
  if (ibi_units == "milliseconds") {
    return(ibi / 1000)
  }

  if (ibi_units == "seconds") {
    return(ibi)
  }

  if (stats::median(ibi, na.rm = TRUE) > 10) {
    ibi / 1000
  } else {
    ibi
  }
}
