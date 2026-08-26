#' Correct EDA for ambient or body temperature
#'
#' Regresses an EDA/conductance signal on one or more continuous temperature
#' covariates and returns a temperature-adjusted residual series. The adjusted
#' signal is temperature-adjusted EDA, not "pure" cognitive or emotional EDA.
#'
#' @param dat A data frame.
#' @param eda_col Numeric EDA/conductance column.
#' @param temperature_cols One or more numeric temperature columns.
#' @param group_cols Optional grouping columns.
#' @param time_col Optional time column retained in summaries.
#' @param output_col Output residual-adjusted EDA column.
#' @param fitted_col Output fitted temperature component column.
#' @param model_by_group Logical. If `TRUE`, fit one model per group.
#' @param add_intercept_mean Logical. If `TRUE`, add the group mean EDA back to
#'   residuals so the adjusted signal remains on the original scale.
#'
#' @return A data frame with adjusted EDA columns and model-summary attributes.
#' @export
correct_gazepoint_eda_temperature <- function(dat,
                                              eda_col = "GSR_US",
                                              temperature_cols,
                                              group_cols = NULL,
                                              time_col = NULL,
                                              output_col = "eda_temperature_adjusted",
                                              fitted_col = "eda_temperature_fitted",
                                              model_by_group = TRUE,
                                              add_intercept_mean = TRUE) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  required <- c(eda_col, temperature_cols, group_cols, time_col)
  required <- required[!is.null(required)]

  missing_required <- setdiff(required, names(dat))
  if (length(missing_required) > 0) {
    stop("Missing required columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  numeric_required <- c(eda_col, temperature_cols, time_col)
  numeric_required <- numeric_required[!is.null(numeric_required)]

  non_numeric <- numeric_required[!vapply(dat[numeric_required], is.numeric, logical(1))]
  if (length(non_numeric) > 0) {
    stop("These columns must be numeric: ", paste(non_numeric, collapse = ", "), call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  out <- dat
  out[[output_col]] <- NA_real_
  out[[fitted_col]] <- NA_real_
  out$eda_temperature_correction_status <- "not_processed"

  groups <- if (isTRUE(model_by_group)) {
    gpbiometrics_11y_split(dat, group_cols)
  } else {
    list(all_rows = seq_len(nrow(dat)))
  }

  summary_rows <- list()

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]
    d <- out[idx, c(eda_col, temperature_cols), drop = FALSE]
    names(d) <- c(".eda", paste0(".temp", seq_along(temperature_cols)))

    complete <- stats::complete.cases(d)

    if (sum(complete) < max(5, length(temperature_cols) + 2)) {
      out$eda_temperature_correction_status[idx] <- "insufficient_complete_cases"

      summary_rows[[group_id]] <- data.frame(
        group_id = group_id,
        n_rows = length(idx),
        n_complete = sum(complete),
        r_squared = NA_real_,
        status = "insufficient_complete_cases",
        stringsAsFactors = FALSE
      )
      next
    }

    fit <- stats::lm(.eda ~ ., data = d[complete, , drop = FALSE])

    fitted_values <- rep(NA_real_, length(idx))
    fitted_values[complete] <- stats::predict(fit, newdata = d[complete, , drop = FALSE])

    residual_values <- out[[eda_col]][idx] - fitted_values

    if (isTRUE(add_intercept_mean)) {
      residual_values <- residual_values + mean(out[[eda_col]][idx][complete], na.rm = TRUE)
    }

    out[[output_col]][idx] <- residual_values
    out[[fitted_col]][idx] <- fitted_values
    out$eda_temperature_correction_status[idx] <- ifelse(
      complete,
      "temperature_adjusted",
      "incomplete_temperature_or_eda"
    )

    fit_summary <- summary(fit)

    summary_rows[[group_id]] <- data.frame(
      group_id = group_id,
      n_rows = length(idx),
      n_complete = sum(complete),
      r_squared = fit_summary$r.squared,
      adjusted_r_squared = fit_summary$adj.r.squared,
      residual_sd = stats::sd(stats::residuals(fit), na.rm = TRUE),
      status = "temperature_model_fitted",
      stringsAsFactors = FALSE
    )
  }

  model_summary <- do.call(rbind, summary_rows)
  rownames(model_summary) <- NULL

  overview <- data.frame(
    input_rows = nrow(dat),
    output_rows = nrow(out),
    group_count = length(groups),
    successful_groups = sum(model_summary$status == "temperature_model_fitted"),
    problem_groups = sum(model_summary$status != "temperature_model_fitted"),
    status = if (all(model_summary$status == "temperature_model_fitted")) {
      "eda_temperature_correction_complete"
    } else if (any(model_summary$status == "temperature_model_fitted")) {
      "eda_temperature_correction_partial"
    } else {
      "eda_temperature_correction_failed"
    },
    interpretation = paste(
      "The output is temperature-adjusted EDA.",
      "Residualisation does not make the signal purely cognitive, emotional, or sympathetic."
    ),
    stringsAsFactors = FALSE
  )

  attr(out, "eda_temperature_overview") <- overview
  attr(out, "eda_temperature_model_summary") <- model_summary
  attr(out, "eda_temperature_settings") <- list(
    eda_col = eda_col,
    temperature_cols = temperature_cols,
    group_cols = group_cols,
    time_col = time_col,
    output_col = output_col,
    fitted_col = fitted_col,
    model_by_group = model_by_group,
    add_intercept_mean = add_intercept_mean
  )

  class(out) <- unique(c("gazepoint_eda_temperature_corrected", class(out)))
  out
}

#' Extract heartbeat candidates from Gazepoint pulse using k-means
#'
#' Uses k-means clustering on the raw pulse waveform to classify likely
#' heartbeat regions and then selects local extrema as beat candidates. This is
#' a Gazepoint Biometrics-oriented fallback for difficult pulse waveforms, not
#' an ECG-equivalent R-peak detector.
#'
#' @param dat A data frame.
#' @param pulse_col Numeric pulse/PPG column.
#' @param time_col Numeric time column.
#' @param group_cols Optional grouping columns.
#' @param k Number of k-means clusters.
#' @param peak_polarity `"positive"` or `"negative"`.
#' @param min_distance_s Minimum time between selected beats.
#' @param sampling_rate Optional sampling rate in Hz.
#' @param seed Optional random seed.
#'
#' @return A list with `overview`, `beat_table`, `interval_table`,
#'   `timeseries`, and `settings`.
#' @export
extract_gazepoint_beats_kmeans <- function(dat,
                                           pulse_col = "HRP",
                                           time_col = "CNT",
                                           group_cols = NULL,
                                           k = 2,
                                           peak_polarity = c("positive", "negative"),
                                           min_distance_s = 0.30,
                                           sampling_rate = NULL,
                                           seed = NULL) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  peak_polarity <- match.arg(peak_polarity)

  required <- c(pulse_col, time_col, group_cols)
  required <- required[!is.null(required)]

  missing_required <- setdiff(required, names(dat))
  if (length(missing_required) > 0) {
    stop("Missing required columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  if (!is.numeric(dat[[pulse_col]])) {
    stop("`pulse_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.numeric(dat[[time_col]])) {
    stop("`time_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.null(seed)) {
    set.seed(seed)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  groups <- gpbiometrics_11y_split(dat, group_cols)

  beat_rows <- list()
  interval_rows <- list()
  timeseries_rows <- list()
  summary_rows <- list()
  beat_id <- 1L
  interval_id <- 1L

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]
    idx <- idx[order(dat[[time_col]][idx])]

    time <- dat[[time_col]][idx]
    pulse <- dat[[pulse_col]][idx]
    finite <- is.finite(time) & is.finite(pulse)

    fs <- gpbiometrics_11y_sampling_rate(time, sampling_rate)

    status <- rep("not_beat_candidate", length(idx))
    cluster <- rep(NA_integer_, length(idx))

    if (sum(finite) < max(10, k * 3) || length(unique(pulse[finite])) < k) {
      timeseries_rows[[group_id]] <- data.frame(
        row_index = idx,
        group_id = group_id,
        time = time,
        pulse = pulse,
        beat_cluster = cluster,
        beat_candidate = FALSE,
        status = "insufficient_pulse_variability",
        stringsAsFactors = FALSE
      )

      summary_rows[[group_id]] <- data.frame(
        group_id = group_id,
        n_rows = length(idx),
        beat_count = 0L,
        mean_ibi_s = NA_real_,
        mean_hr_bpm = NA_real_,
        sampling_rate_hz = fs,
        status = "insufficient_pulse_variability",
        stringsAsFactors = FALSE
      )
      next
    }

    km <- stats::kmeans(pulse[finite], centers = k, nstart = 10)
    centers <- as.numeric(km$centers)

    beat_cluster_id <- if (peak_polarity == "positive") {
      which.max(centers)
    } else {
      which.min(centers)
    }

    cluster[finite] <- km$cluster
    candidate_local <- which(cluster == beat_cluster_id)

    selected_local <- gpbiometrics_11y_select_kmeans_beats(
      candidate = candidate_local,
      time = time,
      pulse = pulse,
      polarity = peak_polarity,
      min_distance_s = min_distance_s
    )

    beat_flag <- rep(FALSE, length(idx))
    beat_flag[selected_local] <- TRUE

    status[cluster == beat_cluster_id] <- "cluster_candidate"
    status[selected_local] <- "selected_beat"

    beat_times <- time[selected_local]
    beat_amplitudes <- pulse[selected_local]
    ibi <- diff(beat_times)

    for (i in seq_along(beat_times)) {
      beat_rows[[beat_id]] <- data.frame(
        group_id = group_id,
        beat_index = i,
        row_index = idx[selected_local[i]],
        beat_time = beat_times[i],
        pulse_amplitude = beat_amplitudes[i],
        method = "kmeans_pulse_classification",
        stringsAsFactors = FALSE
      )
      beat_id <- beat_id + 1L
    }

    if (length(ibi) > 0) {
      for (i in seq_along(ibi)) {
        interval_rows[[interval_id]] <- data.frame(
          group_id = group_id,
          interval_index = i,
          start_time = beat_times[i],
          end_time = beat_times[i + 1],
          ibi_s = ibi[i],
          hr_bpm = if (ibi[i] > 0) 60 / ibi[i] else NA_real_,
          stringsAsFactors = FALSE
        )
        interval_id <- interval_id + 1L
      }
    }

    timeseries_rows[[group_id]] <- data.frame(
      row_index = idx,
      group_id = group_id,
      time = time,
      pulse = pulse,
      beat_cluster = cluster,
      beat_candidate = beat_flag,
      status = status,
      stringsAsFactors = FALSE
    )

    summary_rows[[group_id]] <- data.frame(
      group_id = group_id,
      n_rows = length(idx),
      beat_count = length(beat_times),
      mean_ibi_s = if (length(ibi) > 0) mean(ibi, na.rm = TRUE) else NA_real_,
      mean_hr_bpm = if (length(ibi) > 0) 60 / mean(ibi, na.rm = TRUE) else NA_real_,
      sampling_rate_hz = fs,
      status = if (length(beat_times) >= 2) {
        "kmeans_beats_extracted"
      } else {
        "too_few_beats_detected"
      },
      stringsAsFactors = FALSE
    )
  }

  beat_table <- if (length(beat_rows) > 0) do.call(rbind, beat_rows) else data.frame()
  interval_table <- if (length(interval_rows) > 0) do.call(rbind, interval_rows) else data.frame()
  timeseries <- do.call(rbind, timeseries_rows)
  summary <- do.call(rbind, summary_rows)
  rownames(summary) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    beat_rows = nrow(beat_table),
    interval_rows = nrow(interval_table),
    successful_groups = sum(summary$status == "kmeans_beats_extracted"),
    problem_groups = sum(summary$status != "kmeans_beats_extracted"),
    status = if (all(summary$status == "kmeans_beats_extracted")) {
      "kmeans_beats_extracted"
    } else if (any(summary$status == "kmeans_beats_extracted")) {
      "kmeans_beats_partial"
    } else {
      "kmeans_beats_failed"
    },
    interpretation = paste(
      "K-means pulse beat candidates are hardware-oriented pulse features.",
      "They are not ECG-equivalent R peaks and should be visually/QC checked before HRV inference."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      beat_table = beat_table,
      interval_table = interval_table,
      timeseries = timeseries,
      summary = summary,
      settings = list(
        pulse_col = pulse_col,
        time_col = time_col,
        group_cols = group_cols,
        k = k,
        peak_polarity = peak_polarity,
        min_distance_s = min_distance_s,
        sampling_rate = sampling_rate,
        seed = seed
      )
    ),
    class = c("gazepoint_kmeans_beats", "list")
  )
}

#' Audit or trim the EDA electrode stabilization period
#'
#' Flags or removes the initial stabilization period in each recording/group.
#' This is intended to prevent early skin-electrode drift from being treated as
#' a stable physiological baseline.
#'
#' @param dat A data frame.
#' @param time_col Numeric time column.
#' @param group_cols Optional grouping columns.
#' @param stabilization_minutes Stabilization duration to flag or trim.
#' @param action `"flag"` or `"trim"`.
#' @param output_col Output logical flag column.
#' @param time_units `"auto"`, `"seconds"`, or `"milliseconds"`.
#'
#' @return A data frame with stabilization-period attributes.
#' @export
audit_gazepoint_stabilization_period <- function(dat,
                                                 time_col = "CNT",
                                                 group_cols = NULL,
                                                 stabilization_minutes = 10,
                                                 action = c("flag", "trim"),
                                                 output_col = "in_stabilization_period",
                                                 time_units = c("auto", "seconds", "milliseconds")) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  action <- match.arg(action)
  time_units <- match.arg(time_units)

  required <- c(time_col, group_cols)
  required <- required[!is.null(required)]

  missing_required <- setdiff(required, names(dat))
  if (length(missing_required) > 0) {
    stop("Missing required columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  if (!is.numeric(dat[[time_col]])) {
    stop("`time_col` must identify a numeric column.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  out <- dat
  out[[output_col]] <- FALSE
  out$stabilization_elapsed_s <- NA_real_
  out$stabilization_audit_status <- "not_processed"

  groups <- gpbiometrics_11y_split(out, group_cols)
  summary_rows <- list()

  cutoff_s <- stabilization_minutes * 60

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]
    time_raw <- out[[time_col]][idx]
    time_s <- gpbiometrics_11y_time_to_seconds(time_raw, time_units)

    start_s <- min(time_s[is.finite(time_s)], na.rm = TRUE)
    elapsed_s <- time_s - start_s

    in_stabilization <- is.finite(elapsed_s) & elapsed_s < cutoff_s

    out[[output_col]][idx] <- in_stabilization
    out$stabilization_elapsed_s[idx] <- elapsed_s
    out$stabilization_audit_status[idx] <- ifelse(
      in_stabilization,
      "within_stabilization_period",
      "after_stabilization_period"
    )

    summary_rows[[group_id]] <- data.frame(
      group_id = group_id,
      n_rows = length(idx),
      stabilization_rows = sum(in_stabilization, na.rm = TRUE),
      retained_rows_after_stabilization = sum(!in_stabilization, na.rm = TRUE),
      stabilization_minutes = stabilization_minutes,
      start_time_s = start_s,
      cutoff_time_s = start_s + cutoff_s,
      status = "stabilization_period_audited",
      stringsAsFactors = FALSE
    )
  }

  audit_summary <- do.call(rbind, summary_rows)
  rownames(audit_summary) <- NULL

  if (action == "trim") {
    out <- out[!out[[output_col]], , drop = FALSE]
  }

  overview <- data.frame(
    input_rows = nrow(dat),
    output_rows = nrow(out),
    group_count = length(groups),
    stabilization_minutes = stabilization_minutes,
    action = action,
    status = "stabilization_period_audited",
    interpretation = paste(
      "The stabilization flag identifies the initial skin-electrode adaptation period.",
      "Flagging does not prove that all early data are invalid; trimming should match the study protocol."
    ),
    stringsAsFactors = FALSE
  )

  attr(out, "stabilization_overview") <- overview
  attr(out, "stabilization_summary") <- audit_summary
  attr(out, "stabilization_settings") <- list(
    time_col = time_col,
    group_cols = group_cols,
    stabilization_minutes = stabilization_minutes,
    action = action,
    output_col = output_col,
    time_units = time_units
  )

  class(out) <- unique(c("gazepoint_stabilization_audit", class(out)))
  out
}

#' Regress stimulus luminance from pupil diameter
#'
#' Regresses continuous pupil diameter on frame-wise or sample-wise stimulus
#' luminance and returns a luminance-adjusted pupil series. This controls a
#' major visual confound but does not prove that residual pupil changes are
#' cognitive-load-only effects.
#'
#' @param dat A data frame.
#' @param pupil_col Numeric pupil column.
#' @param luminance_col Numeric luminance/brightness column.
#' @param group_cols Optional grouping columns.
#' @param time_col Optional time column.
#' @param output_col Output luminance-adjusted pupil column.
#' @param fitted_col Output fitted luminance component column.
#' @param include_quadratic Logical. If `TRUE`, include luminance squared.
#' @param model_by_group Logical. If `TRUE`, fit models per group.
#' @param add_intercept_mean Logical. If `TRUE`, add mean pupil size back to
#'   residuals.
#'
#' @return A data frame with luminance-adjusted pupil columns and attributes.
#' @export
regress_gazepoint_pupil_luminance <- function(dat,
                                              pupil_col,
                                              luminance_col,
                                              group_cols = NULL,
                                              time_col = NULL,
                                              output_col = "pupil_luminance_adjusted",
                                              fitted_col = "pupil_luminance_fitted",
                                              include_quadratic = TRUE,
                                              model_by_group = TRUE,
                                              add_intercept_mean = TRUE) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  required <- c(pupil_col, luminance_col, group_cols, time_col)
  required <- required[!is.null(required)]

  missing_required <- setdiff(required, names(dat))
  if (length(missing_required) > 0) {
    stop("Missing required columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  numeric_required <- c(pupil_col, luminance_col, time_col)
  numeric_required <- numeric_required[!is.null(numeric_required)]

  non_numeric <- numeric_required[!vapply(dat[numeric_required], is.numeric, logical(1))]
  if (length(non_numeric) > 0) {
    stop("These columns must be numeric: ", paste(non_numeric, collapse = ", "), call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  out <- dat
  out[[output_col]] <- NA_real_
  out[[fitted_col]] <- NA_real_
  out$pupil_luminance_regression_status <- "not_processed"

  groups <- if (isTRUE(model_by_group)) {
    gpbiometrics_11y_split(dat, group_cols)
  } else {
    list(all_rows = seq_len(nrow(dat)))
  }

  summary_rows <- list()

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]

    d <- data.frame(
      pupil = out[[pupil_col]][idx],
      luminance = out[[luminance_col]][idx],
      stringsAsFactors = FALSE
    )

    if (isTRUE(include_quadratic)) {
      d$luminance2 <- d$luminance^2
    }

    complete <- stats::complete.cases(d)

    if (sum(complete) < if (include_quadratic) 5 else 4) {
      out$pupil_luminance_regression_status[idx] <- "insufficient_complete_cases"

      summary_rows[[group_id]] <- data.frame(
        group_id = group_id,
        n_rows = length(idx),
        n_complete = sum(complete),
        r_squared = NA_real_,
        status = "insufficient_complete_cases",
        stringsAsFactors = FALSE
      )
      next
    }

    fit <- stats::lm(pupil ~ ., data = d[complete, , drop = FALSE])

    fitted_values <- rep(NA_real_, length(idx))
    fitted_values[complete] <- stats::predict(fit, newdata = d[complete, , drop = FALSE])

    residual_values <- out[[pupil_col]][idx] - fitted_values

    if (isTRUE(add_intercept_mean)) {
      residual_values <- residual_values + mean(out[[pupil_col]][idx][complete], na.rm = TRUE)
    }

    out[[output_col]][idx] <- residual_values
    out[[fitted_col]][idx] <- fitted_values
    out$pupil_luminance_regression_status[idx] <- ifelse(
      complete,
      "luminance_adjusted",
      "incomplete_pupil_or_luminance"
    )

    fit_summary <- summary(fit)

    summary_rows[[group_id]] <- data.frame(
      group_id = group_id,
      n_rows = length(idx),
      n_complete = sum(complete),
      r_squared = fit_summary$r.squared,
      adjusted_r_squared = fit_summary$adj.r.squared,
      residual_sd = stats::sd(stats::residuals(fit), na.rm = TRUE),
      status = "luminance_model_fitted",
      stringsAsFactors = FALSE
    )
  }

  model_summary <- do.call(rbind, summary_rows)
  rownames(model_summary) <- NULL

  overview <- data.frame(
    input_rows = nrow(dat),
    output_rows = nrow(out),
    group_count = length(groups),
    successful_groups = sum(model_summary$status == "luminance_model_fitted"),
    problem_groups = sum(model_summary$status != "luminance_model_fitted"),
    status = if (all(model_summary$status == "luminance_model_fitted")) {
      "pupil_luminance_regression_complete"
    } else if (any(model_summary$status == "luminance_model_fitted")) {
      "pupil_luminance_regression_partial"
    } else {
      "pupil_luminance_regression_failed"
    },
    interpretation = paste(
      "The output is luminance-adjusted pupil diameter.",
      "Residual pupil variation should not be interpreted as cognitive load alone without design and modelling support."
    ),
    stringsAsFactors = FALSE
  )

  attr(out, "pupil_luminance_overview") <- overview
  attr(out, "pupil_luminance_model_summary") <- model_summary
  attr(out, "pupil_luminance_settings") <- list(
    pupil_col = pupil_col,
    luminance_col = luminance_col,
    group_cols = group_cols,
    time_col = time_col,
    output_col = output_col,
    fitted_col = fitted_col,
    include_quadratic = include_quadratic,
    model_by_group = model_by_group,
    add_intercept_mean = add_intercept_mean
  )

  class(out) <- unique(c("gazepoint_pupil_luminance_adjusted", class(out)))
  out
}

#' Model heartbeat timing using an IPFM-style impulse train
#'
#' Builds an impulse-train representation of heartbeat timing from IBI/RR
#' intervals or beat times and computes a simple spectrum of the resulting
#' impulse train. This is an IPFM-style model-preparation helper, not a perfect
#' reconstruction of sinoatrial-node physiology.
#'
#' @param dat A data frame.
#' @param ibi_col Optional numeric IBI/RR interval column.
#' @param beat_time_col Optional explicit beat-time column.
#' @param group_cols Optional grouping columns.
#' @param ibi_units `"auto"`, `"seconds"`, or `"milliseconds"`.
#' @param output_sampling_rate Sampling rate for regular impulse train in Hz.
#' @param max_frequency Maximum frequency returned in spectrum.
#'
#' @return A list with `overview`, `beat_table`, `impulse_table`,
#'   `spectrum_table`, `summary`, and `settings`.
#' @export
model_gazepoint_hrv_ipfm <- function(dat,
                                     ibi_col = "IBI",
                                     beat_time_col = NULL,
                                     group_cols = NULL,
                                     ibi_units = c("auto", "seconds", "milliseconds"),
                                     output_sampling_rate = 4,
                                     max_frequency = 0.50) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  ibi_units <- match.arg(ibi_units)

  if (is.null(ibi_col) && is.null(beat_time_col)) {
    stop("Supply either `ibi_col` or `beat_time_col`.", call. = FALSE)
  }

  required <- c(ibi_col, beat_time_col, group_cols)
  required <- required[!is.null(required)]

  missing_required <- setdiff(required, names(dat))
  if (length(missing_required) > 0) {
    stop("Missing required columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  if (!is.null(ibi_col) && !is.numeric(dat[[ibi_col]])) {
    stop("`ibi_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.null(beat_time_col) && !is.numeric(dat[[beat_time_col]])) {
    stop("`beat_time_col` must identify a numeric column.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  groups <- gpbiometrics_11y_split(dat, group_cols)

  beat_rows <- list()
  impulse_rows <- list()
  spectrum_rows <- list()
  summary_rows <- list()
  beat_id <- 1L
  impulse_id <- 1L
  spectrum_id <- 1L

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]

    if (!is.null(beat_time_col)) {
      beat_times <- sort(unique(dat[[beat_time_col]][idx]))
      beat_times <- beat_times[is.finite(beat_times)]
    } else {
      ibi <- dat[[ibi_col]][idx]
      ibi <- ibi[is.finite(ibi) & ibi > 0]
      ibi_s <- gpbiometrics_11y_ibi_to_seconds(ibi, ibi_units)
      beat_times <- cumsum(ibi_s)
    }

    if (length(beat_times) < 3) {
      summary_rows[[group_id]] <- data.frame(
        group_id = group_id,
        beat_count = length(beat_times),
        impulse_rows = 0L,
        dominant_frequency_hz = NA_real_,
        status = "insufficient_beats",
        stringsAsFactors = FALSE
      )
      next
    }

    beat_times <- beat_times - min(beat_times, na.rm = TRUE)
    duration <- max(beat_times, na.rm = TRUE)
    grid <- seq(0, duration, by = 1 / output_sampling_rate)
    impulse <- rep(0, length(grid))

    nearest <- vapply(beat_times, function(bt) {
      which.min(abs(grid - bt))
    }, integer(1))

    impulse[nearest] <- 1

    for (i in seq_along(beat_times)) {
      beat_rows[[beat_id]] <- data.frame(
        group_id = group_id,
        beat_index = i,
        beat_time = beat_times[i],
        stringsAsFactors = FALSE
      )
      beat_id <- beat_id + 1L
    }

    for (i in seq_along(grid)) {
      impulse_rows[[impulse_id]] <- data.frame(
        group_id = group_id,
        time = grid[i],
        impulse = impulse[i],
        stringsAsFactors = FALSE
      )
      impulse_id <- impulse_id + 1L
    }

    spec <- gpbiometrics_11y_ipfm_spectrum(impulse, output_sampling_rate, max_frequency)

    if (nrow(spec) > 0) {
      for (i in seq_len(nrow(spec))) {
        spectrum_rows[[spectrum_id]] <- data.frame(
          group_id = group_id,
          frequency_hz = spec$frequency_hz[i],
          power = spec$power[i],
          stringsAsFactors = FALSE
        )
        spectrum_id <- spectrum_id + 1L
      }
    }

    dominant_frequency <- if (nrow(spec) > 0) {
      spec$frequency_hz[which.max(spec$power)]
    } else {
      NA_real_
    }

    summary_rows[[group_id]] <- data.frame(
      group_id = group_id,
      beat_count = length(beat_times),
      impulse_rows = length(grid),
      dominant_frequency_hz = dominant_frequency,
      status = "ipfm_impulse_train_created",
      stringsAsFactors = FALSE
    )
  }

  beat_table <- if (length(beat_rows) > 0) do.call(rbind, beat_rows) else data.frame()
  impulse_table <- if (length(impulse_rows) > 0) do.call(rbind, impulse_rows) else data.frame()
  spectrum_table <- if (length(spectrum_rows) > 0) do.call(rbind, spectrum_rows) else data.frame()
  summary <- do.call(rbind, summary_rows)
  rownames(summary) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    beat_rows = nrow(beat_table),
    impulse_rows = nrow(impulse_table),
    spectrum_rows = nrow(spectrum_table),
    successful_groups = sum(summary$status == "ipfm_impulse_train_created"),
    problem_groups = sum(summary$status != "ipfm_impulse_train_created"),
    status = if (all(summary$status == "ipfm_impulse_train_created")) {
      "ipfm_model_created"
    } else if (any(summary$status == "ipfm_impulse_train_created")) {
      "ipfm_model_partial"
    } else {
      "ipfm_model_failed"
    },
    interpretation = paste(
      "The impulse train is an IPFM-style heartbeat timing representation.",
      "It is not a perfect reconstruction of sinoatrial-node physiology."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      beat_table = beat_table,
      impulse_table = impulse_table,
      spectrum_table = spectrum_table,
      summary = summary,
      settings = list(
        ibi_col = ibi_col,
        beat_time_col = beat_time_col,
        group_cols = group_cols,
        ibi_units = ibi_units,
        output_sampling_rate = output_sampling_rate,
        max_frequency = max_frequency
      )
    ),
    class = c("gazepoint_hrv_ipfm", "list")
  )
}

gpbiometrics_11y_split <- function(dat, group_cols) {
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

gpbiometrics_11y_sampling_rate <- function(time, sampling_rate = NULL) {
  if (!is.null(sampling_rate)) {
    return(sampling_rate)
  }

  time <- time[is.finite(time)]

  if (length(time) < 3) {
    return(NA_real_)
  }

  dt <- diff(time)
  dt <- dt[is.finite(dt) & dt > 0]

  if (length(dt) == 0) {
    return(NA_real_)
  }

  median_dt <- stats::median(dt)

  if (median_dt > 10) {
    1000 / median_dt
  } else {
    1 / median_dt
  }
}

gpbiometrics_11y_time_to_seconds <- function(time, time_units = "auto") {
  if (time_units == "milliseconds") {
    return(time / 1000)
  }

  if (time_units == "seconds") {
    return(time)
  }

  finite_time <- time[is.finite(time)]

  if (length(finite_time) < 2) {
    return(time)
  }

  dt <- diff(finite_time)
  dt <- dt[is.finite(dt) & dt > 0]

  if (length(dt) > 0 && stats::median(dt) > 10) {
    time / 1000
  } else {
    time
  }
}

gpbiometrics_11y_ibi_to_seconds <- function(ibi, ibi_units = "auto") {
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

gpbiometrics_11y_select_kmeans_beats <- function(candidate,
                                                 time,
                                                 pulse,
                                                 polarity,
                                                 min_distance_s) {
  if (length(candidate) == 0) {
    return(integer())
  }

  candidate <- sort(candidate)
  gaps <- c(TRUE, diff(candidate) > 1)
  run_id <- cumsum(gaps)

  selected <- integer()

  for (run in unique(run_id)) {
    run_idx <- candidate[run_id == run]

    if (polarity == "positive") {
      local <- run_idx[which.max(pulse[run_idx])]
    } else {
      local <- run_idx[which.min(pulse[run_idx])]
    }

    selected <- c(selected, local)
  }

  selected <- selected[order(time[selected])]

  if (length(selected) <= 1) {
    return(selected)
  }

  keep <- selected[1]

  for (idx in selected[-1]) {
    last <- keep[length(keep)]

    if ((time[idx] - time[last]) >= min_distance_s) {
      keep <- c(keep, idx)
    } else {
      replace <- if (polarity == "positive") {
        pulse[idx] > pulse[last]
      } else {
        pulse[idx] < pulse[last]
      }

      if (isTRUE(replace)) {
        keep[length(keep)] <- idx
      }
    }
  }

  keep
}

gpbiometrics_11y_ipfm_spectrum <- function(impulse,
                                           sampling_rate,
                                           max_frequency = 0.50) {
  impulse <- impulse - mean(impulse, na.rm = TRUE)

  if (length(impulse) < 8 || stats::sd(impulse) == 0) {
    return(data.frame())
  }

  spec <- stats::spec.pgram(
    impulse,
    taper = 0.1,
    plot = FALSE,
    demean = TRUE,
    detrend = TRUE,
    fast = TRUE
  )

  freq <- spec$freq * sampling_rate
  power <- spec$spec

  keep <- is.finite(freq) & is.finite(power) & freq > 0 & freq <= max_frequency

  data.frame(
    frequency_hz = freq[keep],
    power = power[keep],
    stringsAsFactors = FALSE
  )
}
