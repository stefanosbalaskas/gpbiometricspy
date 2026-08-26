#' Extract respiration proxy using a CEEMDAN-style bridge
#'
#' Extracts respiration-like components from PPG or ECG-derived respiratory
#' proxy signals. If `external_fun` is supplied, it is used as the CEEMDAN
#' backend. Otherwise, the function uses a dependency-light multiscale
#' decomposition fallback and labels the result accordingly.
#'
#' This function does not claim to reproduce full CEEMDAN unless a validated
#' external CEEMDAN function is supplied.
#'
#' @param dat A data frame.
#' @param signal_col Numeric PPG/ECG-derived signal column.
#' @param time_col Numeric time column.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate Optional sampling rate in Hz.
#' @param respiration_band Frequency band in Hz used to select respiration-like
#'   components.
#' @param scales Moving-average scales used by the fallback decomposition.
#' @param external_fun Optional function with arguments `x`, `time`, and
#'   `sampling_rate`, returning either a numeric vector or a list/data frame of
#'   components.
#'
#' @return A list with `overview`, `component_table`, `respiration_timeseries`,
#'   `summary`, and `settings`.
#' @export
extract_gazepoint_respiration_ceemdan <- function(dat,
                                                  signal_col,
                                                  time_col = "CNT",
                                                  group_cols = NULL,
                                                  sampling_rate = NULL,
                                                  respiration_band = c(0.10, 0.60),
                                                  scales = c(5, 15, 30, 60, 120),
                                                  external_fun = NULL) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  if (!signal_col %in% names(dat)) {
    stop("Column `", signal_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!time_col %in% names(dat)) {
    stop("Column `", time_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!is.numeric(dat[[signal_col]])) {
    stop("`signal_col` must identify a numeric column.", call. = FALSE)
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

  groups <- gpbiometrics_ceemdan_split(dat, group_cols)

  component_rows <- list()
  timeseries_rows <- list()
  summary_rows <- list()
  component_id <- 1L

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]
    idx <- idx[order(dat[[time_col]][idx])]

    time <- dat[[time_col]][idx]
    x <- dat[[signal_col]][idx]
    fs <- gpbiometrics_ceemdan_sampling_rate(time, sampling_rate)

    if (!is.finite(fs) || fs <= 0 || sum(is.finite(x)) < 10) {
      summary_rows[[group_id]] <- data.frame(
        group_id = group_id,
        n_rows = length(idx),
        sampling_rate_hz = fs,
        selected_component_count = 0L,
        proxy_respiration_rate_hz = NA_real_,
        proxy_respiration_rate_bpm = NA_real_,
        status = "insufficient_signal_or_sampling_rate",
        stringsAsFactors = FALSE
      )
      next
    }

    x_filled <- gpbiometrics_ceemdan_fill(x)

    decomposition <- gpbiometrics_ceemdan_decompose(
      x = x_filled,
      time = time,
      sampling_rate = fs,
      scales = scales,
      external_fun = external_fun
    )

    components <- decomposition$components
    method <- decomposition$method

    if (ncol(components) == 0) {
      summary_rows[[group_id]] <- data.frame(
        group_id = group_id,
        n_rows = length(idx),
        sampling_rate_hz = fs,
        selected_component_count = 0L,
        proxy_respiration_rate_hz = NA_real_,
        proxy_respiration_rate_bpm = NA_real_,
        status = "no_components_extracted",
        stringsAsFactors = FALSE
      )
      next
    }

    component_rates <- vapply(seq_len(ncol(components)), function(j) {
      gpbiometrics_ceemdan_dominant_frequency(
        signal = components[, j],
        sampling_rate = fs,
        frequency_band = respiration_band
      )
    }, numeric(1))

    selected <- is.finite(component_rates) &
      component_rates >= respiration_band[1] &
      component_rates <= respiration_band[2]

    if (!any(selected)) {
      selected[which.max(stats::var(components, na.rm = TRUE))] <- TRUE
    }

    proxy <- rowMeans(components[, selected, drop = FALSE], na.rm = TRUE)

    proxy_rate <- gpbiometrics_ceemdan_dominant_frequency(
      signal = proxy,
      sampling_rate = fs,
      frequency_band = respiration_band
    )

    for (j in seq_len(ncol(components))) {
      component_rows[[component_id]] <- data.frame(
        group_id = group_id,
        component = colnames(components)[j],
        dominant_frequency_hz = component_rates[j],
        selected_for_respiration = selected[j],
        variance = stats::var(components[, j], na.rm = TRUE),
        method = method,
        stringsAsFactors = FALSE
      )
      component_id <- component_id + 1L
    }

    timeseries_rows[[group_id]] <- data.frame(
      row_index = idx,
      group_id = group_id,
      time = time,
      respiration_proxy = proxy,
      status = "respiration_proxy_extracted",
      stringsAsFactors = FALSE
    )

    summary_rows[[group_id]] <- data.frame(
      group_id = group_id,
      n_rows = length(idx),
      sampling_rate_hz = fs,
      selected_component_count = sum(selected),
      proxy_respiration_rate_hz = proxy_rate,
      proxy_respiration_rate_bpm = proxy_rate * 60,
      status = "respiration_proxy_extracted",
      stringsAsFactors = FALSE
    )
  }

  component_table <- if (length(component_rows) > 0) {
    do.call(rbind, component_rows)
  } else {
    data.frame()
  }

  respiration_timeseries <- if (length(timeseries_rows) > 0) {
    do.call(rbind, timeseries_rows)
  } else {
    data.frame()
  }

  summary <- do.call(rbind, summary_rows)
  rownames(summary) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    component_rows = nrow(component_table),
    timeseries_rows = nrow(respiration_timeseries),
    successful_groups = sum(summary$status == "respiration_proxy_extracted"),
    problem_groups = sum(summary$status != "respiration_proxy_extracted"),
    status = if (all(summary$status == "respiration_proxy_extracted")) {
      "ceemdan_respiration_proxy_complete"
    } else if (any(summary$status == "respiration_proxy_extracted")) {
      "ceemdan_respiration_proxy_partial"
    } else {
      "ceemdan_respiration_proxy_failed"
    },
    interpretation = paste(
      "Respiration output is a signal-derived proxy.",
      "Full CEEMDAN is used only when a validated external function is supplied; otherwise a dependency-light multiscale fallback is used."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      component_table = component_table,
      respiration_timeseries = respiration_timeseries,
      summary = summary,
      settings = list(
        signal_col = signal_col,
        time_col = time_col,
        group_cols = group_cols,
        sampling_rate = sampling_rate,
        respiration_band = respiration_band,
        scales = scales,
        external_fun_supplied = !is.null(external_fun)
      )
    ),
    class = c("gazepoint_respiration_ceemdan", "list")
  )
}

#' Fuse respiration proxies using a Kalman filter
#'
#' Fuses two respiration proxy streams, such as PPG-derived respiration and
#' ECG-derived respiration, using a transparent one-dimensional Kalman filter.
#' This is a linear Kalman fusion helper. It is not an extended Kalman filter
#' unless the user supplies nonlinear state/measurement logic externally.
#'
#' @param dat A data frame.
#' @param primary_col First respiration proxy column.
#' @param secondary_col Second respiration proxy column.
#' @param time_col Optional time column.
#' @param group_cols Optional grouping columns.
#' @param process_var Process variance.
#' @param primary_var Measurement variance for `primary_col`.
#' @param secondary_var Measurement variance for `secondary_col`.
#' @param output_col Output fused respiration column.
#'
#' @return A data frame with fused respiration output and Kalman attributes.
#' @export
fuse_gazepoint_respiration_kalman <- function(dat,
                                              primary_col,
                                              secondary_col,
                                              time_col = NULL,
                                              group_cols = NULL,
                                              process_var = 0.01,
                                              primary_var = 0.05,
                                              secondary_var = 0.05,
                                              output_col = "respiration_kalman_fused") {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  required <- c(primary_col, secondary_col, time_col)
  required <- required[!is.null(required)]

  missing_required <- setdiff(required, names(dat))
  if (length(missing_required) > 0) {
    stop("Missing required columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  if (!is.numeric(dat[[primary_col]])) {
    stop("`primary_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.numeric(dat[[secondary_col]])) {
    stop("`secondary_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.null(time_col) && !is.numeric(dat[[time_col]])) {
    stop("`time_col` must identify a numeric column.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  missing_groups <- setdiff(group_cols, names(dat))
  if (length(missing_groups) > 0) {
    stop("Missing `group_cols`: ", paste(missing_groups, collapse = ", "), call. = FALSE)
  }

  out <- dat
  out[[output_col]] <- NA_real_
  out[[paste0(output_col, "_variance")]] <- NA_real_
  out[[paste0(output_col, "_status")]] <- "not_processed"

  groups <- gpbiometrics_ceemdan_split(out, group_cols)
  summary_rows <- list()

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]

    if (!is.null(time_col)) {
      idx <- idx[order(out[[time_col]][idx])]
    }

    primary <- out[[primary_col]][idx]
    secondary <- out[[secondary_col]][idx]

    filtered <- gpbiometrics_kalman_fuse_two_streams(
      primary = primary,
      secondary = secondary,
      process_var = process_var,
      primary_var = primary_var,
      secondary_var = secondary_var
    )

    out[[output_col]][idx] <- filtered$state
    out[[paste0(output_col, "_variance")]][idx] <- filtered$variance
    out[[paste0(output_col, "_status")]][idx] <- filtered$status

    summary_rows[[group_id]] <- data.frame(
      group_id = group_id,
      n_rows = length(idx),
      finite_primary = sum(is.finite(primary)),
      finite_secondary = sum(is.finite(secondary)),
      fused_rows = sum(filtered$status == "fused"),
      primary_only_rows = sum(filtered$status == "primary_only"),
      secondary_only_rows = sum(filtered$status == "secondary_only"),
      missing_rows = sum(filtered$status == "missing"),
      status = if (any(filtered$status != "missing")) {
        "kalman_respiration_fusion_complete"
      } else {
        "kalman_respiration_fusion_failed"
      },
      stringsAsFactors = FALSE
    )
  }

  summary <- do.call(rbind, summary_rows)
  rownames(summary) <- NULL

  overview <- data.frame(
    input_rows = nrow(dat),
    output_rows = nrow(out),
    group_count = length(groups),
    successful_groups = sum(summary$status == "kalman_respiration_fusion_complete"),
    problem_groups = sum(summary$status != "kalman_respiration_fusion_complete"),
    status = if (all(summary$status == "kalman_respiration_fusion_complete")) {
      "kalman_respiration_fusion_complete"
    } else if (any(summary$status == "kalman_respiration_fusion_complete")) {
      "kalman_respiration_fusion_partial"
    } else {
      "kalman_respiration_fusion_failed"
    },
    interpretation = paste(
      "The fused series is a Kalman-filtered respiration proxy from two measurement streams.",
      "It is not direct respiratory-belt measurement and does not infer psychological or clinical state."
    ),
    stringsAsFactors = FALSE
  )

  attr(out, "kalman_respiration_overview") <- overview
  attr(out, "kalman_respiration_summary") <- summary
  attr(out, "kalman_respiration_settings") <- list(
    primary_col = primary_col,
    secondary_col = secondary_col,
    time_col = time_col,
    group_cols = group_cols,
    process_var = process_var,
    primary_var = primary_var,
    secondary_var = secondary_var,
    output_col = output_col
  )

  class(out) <- unique(c("gazepoint_respiration_kalman_fused", class(out)))
  out
}

gpbiometrics_ceemdan_split <- function(dat, group_cols) {
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

gpbiometrics_ceemdan_sampling_rate <- function(time, sampling_rate = NULL) {
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

gpbiometrics_ceemdan_fill <- function(x) {
  idx <- seq_along(x)
  finite <- is.finite(x)

  if (all(finite)) {
    return(x)
  }

  if (sum(finite) == 0) {
    return(rep(0, length(x)))
  }

  if (sum(finite) == 1) {
    return(rep(x[finite][1], length(x)))
  }

  stats::approx(idx[finite], x[finite], xout = idx, rule = 2)$y
}

gpbiometrics_ceemdan_decompose <- function(x,
                                           time,
                                           sampling_rate,
                                           scales,
                                           external_fun = NULL) {
  if (!is.null(external_fun)) {
    raw <- external_fun(x = x, time = time, sampling_rate = sampling_rate)

    if (is.numeric(raw)) {
      components <- matrix(raw, ncol = 1)
    } else if (is.data.frame(raw)) {
      components <- as.matrix(raw[vapply(raw, is.numeric, logical(1))])
    } else if (is.list(raw)) {
      numeric_items <- raw[vapply(raw, is.numeric, logical(1))]
      components <- do.call(cbind, numeric_items)
    } else {
      stop("`external_fun` must return numeric components.", call. = FALSE)
    }

    if (is.null(colnames(components))) {
      colnames(components) <- paste0("external_component_", seq_len(ncol(components)))
    }

    return(list(components = components, method = "external_ceemdan"))
  }

  components <- list()
  previous_smooth <- x

  for (scale in scales) {
    smooth <- gpbiometrics_ceemdan_moving_average(x, scale)
    component <- previous_smooth - smooth
    components[[paste0("fallback_scale_", scale)]] <- component
    previous_smooth <- smooth
  }

  components[["fallback_residual"]] <- previous_smooth

  list(
    components = as.matrix(as.data.frame(components)),
    method = "multiscale_fallback_not_full_ceemdan"
  )
}

gpbiometrics_ceemdan_moving_average <- function(x, window) {
  window <- max(3L, as.integer(window))

  if (length(x) < window) {
    return(rep(mean(x, na.rm = TRUE), length(x)))
  }

  y <- as.numeric(stats::filter(x, rep(1 / window, window), sides = 2))
  y[!is.finite(y)] <- x[!is.finite(y)]
  y[is.na(y)] <- x[is.na(y)]
  y
}

gpbiometrics_ceemdan_dominant_frequency <- function(signal,
                                                    sampling_rate,
                                                    frequency_band) {
  signal <- signal[is.finite(signal)]

  if (length(signal) < 8 || stats::sd(signal) == 0) {
    return(NA_real_)
  }

  spec <- stats::spec.pgram(
    signal,
    taper = 0.1,
    plot = FALSE,
    demean = TRUE,
    detrend = TRUE,
    fast = TRUE
  )

  freq <- spec$freq * sampling_rate
  power <- spec$spec

  keep <- is.finite(freq) &
    is.finite(power) &
    freq >= frequency_band[1] &
    freq <= frequency_band[2]

  if (!any(keep)) {
    return(NA_real_)
  }

  freq[keep][which.max(power[keep])]
}

gpbiometrics_kalman_fuse_two_streams <- function(primary,
                                                 secondary,
                                                 process_var,
                                                 primary_var,
                                                 secondary_var) {
  n <- length(primary)
  state <- rep(NA_real_, n)
  variance <- rep(NA_real_, n)
  status <- rep("missing", n)

  initial_values <- c(primary, secondary)
  initial_values <- initial_values[is.finite(initial_values)]

  if (length(initial_values) == 0) {
    return(list(state = state, variance = variance, status = status))
  }

  current_state <- mean(initial_values)
  current_var <- stats::var(initial_values)

  if (!is.finite(current_var) || current_var <= 0) {
    current_var <- 1
  }

  for (i in seq_len(n)) {
    current_var <- current_var + process_var

    measurements <- c(primary[i], secondary[i])
    measurement_vars <- c(primary_var, secondary_var)
    valid <- is.finite(measurements)

    if (any(valid)) {
      for (j in which(valid)) {
        kalman_gain <- current_var / (current_var + measurement_vars[j])
        current_state <- current_state + kalman_gain * (measurements[j] - current_state)
        current_var <- (1 - kalman_gain) * current_var
      }

      if (all(valid)) {
        status[i] <- "fused"
      } else if (valid[1]) {
        status[i] <- "primary_only"
      } else {
        status[i] <- "secondary_only"
      }
    }

    state[i] <- current_state
    variance[i] <- current_var
  }

  list(state = state, variance = variance, status = status)
}
