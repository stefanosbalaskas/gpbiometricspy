#' Extract bilateral EDA asymmetry features
#'
#' Computes left-right electrodermal activity asymmetry descriptors from two
#' simultaneously recorded EDA channels. The function returns row-level
#' asymmetry time series and group-level summaries.
#'
#' These descriptors quantify bilateral EDA differences only. They do not infer
#' hemisphere activation, amygdala activity, psychopathology, emotion, stress,
#' cognition, health status, or diagnosis.
#'
#' @param dat A data frame.
#' @param left_col Numeric left-side EDA column.
#' @param right_col Numeric right-side EDA column.
#' @param time_col Optional numeric time column for ordering and gradient
#'   calculation.
#' @param group_cols Optional grouping columns.
#' @param output_prefix Prefix used for row-level output columns.
#'
#' @return A list with `overview`, `asymmetry_timeseries`, `summary`, and
#'   `settings`.
#' @export
extract_gazepoint_bilateral_eda_asymmetry <- function(dat,
                                                      left_col,
                                                      right_col,
                                                      time_col = NULL,
                                                      group_cols = NULL,
                                                      output_prefix = "beda") {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  required <- c(left_col, right_col, time_col)
  required <- required[!is.null(required)]

  missing_required <- setdiff(required, names(dat))
  if (length(missing_required) > 0) {
    stop("Missing required columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  if (!is.numeric(dat[[left_col]])) {
    stop("`left_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.numeric(dat[[right_col]])) {
    stop("`right_col` must identify a numeric column.", call. = FALSE)
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

  groups <- gpbiometrics_modality_split(dat, group_cols)

  rows <- list()
  summary_rows <- list()

  diff_col <- paste0(output_prefix, "_left_minus_right")
  abs_col <- paste0(output_prefix, "_absolute_difference")
  norm_col <- paste0(output_prefix, "_normalised_difference")
  log_ratio_col <- paste0(output_prefix, "_log_left_right_ratio")
  gradient_col <- paste0(output_prefix, "_difference_gradient")

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]

    if (!is.null(time_col)) {
      idx <- idx[order(dat[[time_col]][idx])]
    }

    left <- dat[[left_col]][idx]
    right <- dat[[right_col]][idx]
    mean_pair <- rowMeans(cbind(left, right), na.rm = TRUE)

    asym_diff <- left - right
    abs_diff <- abs(asym_diff)

    norm_diff <- ifelse(
      is.finite(mean_pair) & mean_pair != 0,
      asym_diff / mean_pair,
      NA_real_
    )

    log_ratio <- ifelse(
      is.finite(left) & is.finite(right) & left > 0 & right > 0,
      log(left / right),
      NA_real_
    )

    gradient <- rep(NA_real_, length(idx))

    if (!is.null(time_col) && length(idx) >= 2) {
      time <- dat[[time_col]][idx]
      dt <- diff(time)
      dd <- diff(asym_diff)

      gradient[-1] <- ifelse(
        is.finite(dt) & dt != 0,
        dd / dt,
        NA_real_
      )
    }

    group_dat <- data.frame(
      row_index = idx,
      group_id = group_id,
      stringsAsFactors = FALSE
    )

    if (!is.null(time_col)) {
      group_dat[[time_col]] <- dat[[time_col]][idx]
    }

    group_dat[[left_col]] <- left
    group_dat[[right_col]] <- right
    group_dat[[diff_col]] <- asym_diff
    group_dat[[abs_col]] <- abs_diff
    group_dat[[norm_col]] <- norm_diff
    group_dat[[log_ratio_col]] <- log_ratio
    group_dat[[gradient_col]] <- gradient

    rows[[group_id]] <- group_dat

    finite_pair <- is.finite(left) & is.finite(right)

    summary_rows[[group_id]] <- data.frame(
      group_id = group_id,
      n_rows = length(idx),
      n_valid_pairs = sum(finite_pair),
      mean_left = mean(left[finite_pair], na.rm = TRUE),
      mean_right = mean(right[finite_pair], na.rm = TRUE),
      mean_left_minus_right = mean(asym_diff[finite_pair], na.rm = TRUE),
      median_left_minus_right = stats::median(asym_diff[finite_pair], na.rm = TRUE),
      mean_absolute_difference = mean(abs_diff[finite_pair], na.rm = TRUE),
      mean_normalised_difference = mean(norm_diff[finite_pair], na.rm = TRUE),
      mean_log_left_right_ratio = mean(log_ratio[finite_pair], na.rm = TRUE),
      sd_left_minus_right = stats::sd(asym_diff[finite_pair], na.rm = TRUE),
      status = if (sum(finite_pair) > 0) {
        "bilateral_eda_asymmetry_extracted"
      } else {
        "no_valid_bilateral_pairs"
      },
      stringsAsFactors = FALSE
    )
  }

  asymmetry_timeseries <- do.call(rbind, rows)
  rownames(asymmetry_timeseries) <- NULL

  summary <- do.call(rbind, summary_rows)
  rownames(summary) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    timeseries_rows = nrow(asymmetry_timeseries),
    summary_rows = nrow(summary),
    successful_groups = sum(summary$status == "bilateral_eda_asymmetry_extracted"),
    problem_groups = sum(summary$status != "bilateral_eda_asymmetry_extracted"),
    status = if (all(summary$status == "bilateral_eda_asymmetry_extracted")) {
      "bilateral_eda_asymmetry_complete"
    } else if (any(summary$status == "bilateral_eda_asymmetry_extracted")) {
      "bilateral_eda_asymmetry_partial"
    } else {
      "bilateral_eda_asymmetry_failed"
    },
    interpretation = paste(
      "Bilateral EDA asymmetry features quantify left-right signal differences.",
      "They do not infer hemisphere activation, brain-region activity, emotion, stress, cognition, health status, or diagnosis."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      asymmetry_timeseries = asymmetry_timeseries,
      summary = summary,
      settings = list(
        left_col = left_col,
        right_col = right_col,
        time_col = time_col,
        group_cols = group_cols,
        output_prefix = output_prefix
      )
    ),
    class = c("gazepoint_bilateral_eda_asymmetry", "list")
  )
}

#' Add small uniform noise to reduce quantization overlap
#'
#' Adds uniform white noise with magnitude tied to hardware resolution. This is
#' intended only for nonlinear phase-space methods that are sensitive to exact
#' repeated values caused by coarse interval quantization.
#'
#' @param dat A data frame.
#' @param signal_cols Numeric signal columns to jitter.
#' @param resolution Numeric scalar or named numeric vector giving measurement
#'   resolution for each column.
#' @param group_cols Optional grouping columns, retained in settings.
#' @param output_suffix Suffix for jittered columns.
#' @param seed Optional random seed.
#' @param overwrite Logical. If `FALSE`, existing output columns are protected.
#'
#' @return A data frame with jittered columns and quantization-noise attributes.
#' @export
denoise_gazepoint_quantization_noise <- function(dat,
                                                 signal_cols,
                                                 resolution,
                                                 group_cols = NULL,
                                                 output_suffix = "_quantization_jittered",
                                                 seed = NULL,
                                                 overwrite = FALSE) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  missing_signals <- setdiff(signal_cols, names(dat))
  if (length(missing_signals) > 0) {
    stop("Missing `signal_cols`: ", paste(missing_signals, collapse = ", "), call. = FALSE)
  }

  non_numeric <- signal_cols[!vapply(dat[signal_cols], is.numeric, logical(1))]
  if (length(non_numeric) > 0) {
    stop("These `signal_cols` are not numeric: ", paste(non_numeric, collapse = ", "), call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  missing_groups <- setdiff(group_cols, names(dat))
  if (length(missing_groups) > 0) {
    stop("Missing `group_cols`: ", paste(missing_groups, collapse = ", "), call. = FALSE)
  }

  if (!is.numeric(resolution) || length(resolution) < 1 || any(!is.finite(resolution)) || any(resolution <= 0)) {
    stop("`resolution` must contain positive finite numeric values.", call. = FALSE)
  }

  if (!is.null(seed)) {
    set.seed(seed)
  }

  out <- dat
  summary_rows <- list()

  for (signal_col in signal_cols) {
    output_col <- paste0(signal_col, output_suffix)

    if (!isTRUE(overwrite) && output_col %in% names(out)) {
      stop("Output column `", output_col, "` already exists. Use `overwrite = TRUE`.", call. = FALSE)
    }

    col_resolution <- gpbiometrics_quantization_resolution(signal_col, resolution)

    noise <- stats::runif(
      n = nrow(out),
      min = -col_resolution / 2,
      max = col_resolution / 2
    )

    x <- out[[signal_col]]
    y <- x
    y[is.finite(x)] <- x[is.finite(x)] + noise[is.finite(x)]

    out[[output_col]] <- y

    summary_rows[[signal_col]] <- data.frame(
      signal_col = signal_col,
      output_col = output_col,
      resolution = col_resolution,
      noise_min = -col_resolution / 2,
      noise_max = col_resolution / 2,
      finite_rows = sum(is.finite(x)),
      changed_rows = sum(is.finite(x)),
      status = "quantization_jitter_added",
      stringsAsFactors = FALSE
    )
  }

  summary <- do.call(rbind, summary_rows)
  rownames(summary) <- NULL

  overview <- data.frame(
    input_rows = nrow(dat),
    output_rows = nrow(out),
    signal_count = length(signal_cols),
    status = "quantization_noise_reduction_complete",
    interpretation = paste(
      "Uniform jitter is intended only to reduce exact overlap from coarse quantization before nonlinear phase-space analyses.",
      "It does not recover lost physiological information and should not replace raw data for ordinary summaries."
    ),
    stringsAsFactors = FALSE
  )

  attr(out, "quantization_noise_overview") <- overview
  attr(out, "quantization_noise_summary") <- summary
  attr(out, "quantization_noise_settings") <- list(
    signal_cols = signal_cols,
    resolution = resolution,
    group_cols = group_cols,
    output_suffix = output_suffix,
    seed = seed,
    overwrite = overwrite
  )

  class(out) <- unique(c("gazepoint_quantization_noise_adjusted", class(out)))
  out
}

#' Extract ECG-derived respiration using PCA
#'
#' Extracts an ECG-derived respiration proxy from beat-level ECG morphology
#' features using principal component analysis. This function requires
#' ECG-derived morphology columns, such as QRS amplitudes, widths, or sampled
#' beat-shape features. It is not intended for HR, IBI, or PPG-only data.
#'
#' @param dat A data frame.
#' @param ecg_cols Numeric ECG morphology columns.
#' @param time_col Optional time column.
#' @param group_cols Optional grouping columns.
#' @param n_components Number of PCA components to retain.
#' @param scale Logical. If `TRUE`, scale ECG morphology columns before PCA.
#' @param output_prefix Prefix for PCA output columns.
#'
#' @return A list with `overview`, `edr_timeseries`, `component_summary`, and
#'   `settings`.
#' @export
extract_gazepoint_edr_pca <- function(dat,
                                      ecg_cols,
                                      time_col = NULL,
                                      group_cols = NULL,
                                      n_components = 1,
                                      scale = TRUE,
                                      output_prefix = "edr_pca") {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  if (length(ecg_cols) < 2) {
    stop("`ecg_cols` must contain at least two ECG morphology columns.", call. = FALSE)
  }

  missing_ecg <- setdiff(ecg_cols, names(dat))
  if (length(missing_ecg) > 0) {
    stop("Missing `ecg_cols`: ", paste(missing_ecg, collapse = ", "), call. = FALSE)
  }

  non_numeric <- ecg_cols[!vapply(dat[ecg_cols], is.numeric, logical(1))]
  if (length(non_numeric) > 0) {
    stop("These `ecg_cols` are not numeric: ", paste(non_numeric, collapse = ", "), call. = FALSE)
  }

  if (!is.null(time_col) && !time_col %in% names(dat)) {
    stop("Column `", time_col, "` was not found in `dat`.", call. = FALSE)
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

  groups <- gpbiometrics_modality_split(dat, group_cols)

  rows <- list()
  component_rows <- list()

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]

    if (!is.null(time_col)) {
      idx <- idx[order(dat[[time_col]][idx])]
    }

    x <- dat[idx, ecg_cols, drop = FALSE]
    complete <- stats::complete.cases(x)

    group_out <- data.frame(
      row_index = idx,
      group_id = group_id,
      stringsAsFactors = FALSE
    )

    if (!is.null(time_col)) {
      group_out[[time_col]] <- dat[[time_col]][idx]
    }

    for (component in seq_len(n_components)) {
      group_out[[paste0(output_prefix, "_pc", component)]] <- NA_real_
    }

    if (sum(complete) < max(3, n_components + 1)) {
      group_out[[paste0(output_prefix, "_status")]] <- "insufficient_complete_ecg_morphology"
      rows[[group_id]] <- group_out

      component_rows[[group_id]] <- data.frame(
        group_id = group_id,
        component = seq_len(n_components),
        variance_explained = NA_real_,
        cumulative_variance_explained = NA_real_,
        status = "insufficient_complete_ecg_morphology",
        stringsAsFactors = FALSE
      )

      next
    }

    pca <- stats::prcomp(
      x[complete, , drop = FALSE],
      center = TRUE,
      scale. = scale
    )

    available_components <- min(n_components, ncol(pca$x))

    for (component in seq_len(available_components)) {
      group_out[[paste0(output_prefix, "_pc", component)]][complete] <- pca$x[, component]
    }

    group_out[[paste0(output_prefix, "_status")]] <- ifelse(
      complete,
      "edr_pca_extracted",
      "incomplete_ecg_morphology"
    )

    variance <- pca$sdev^2
    variance_explained <- variance / sum(variance)

    component_rows[[group_id]] <- data.frame(
      group_id = group_id,
      component = seq_len(available_components),
      variance_explained = variance_explained[seq_len(available_components)],
      cumulative_variance_explained = cumsum(variance_explained)[seq_len(available_components)],
      status = "edr_pca_extracted",
      stringsAsFactors = FALSE
    )

    rows[[group_id]] <- group_out
  }

  edr_timeseries <- do.call(rbind, rows)
  rownames(edr_timeseries) <- NULL

  component_summary <- do.call(rbind, component_rows)
  rownames(component_summary) <- NULL

  status_col <- paste0(output_prefix, "_status")

  overview <- data.frame(
    group_count = length(groups),
    timeseries_rows = nrow(edr_timeseries),
    component_rows = nrow(component_summary),
    successful_rows = sum(edr_timeseries[[status_col]] == "edr_pca_extracted"),
    problem_rows = sum(edr_timeseries[[status_col]] != "edr_pca_extracted"),
    status = if (any(edr_timeseries[[status_col]] == "edr_pca_extracted")) {
      "edr_pca_extracted"
    } else {
      "edr_pca_failed"
    },
    interpretation = paste(
      "EDR-PCA outputs are respiration proxy components from ECG morphology columns.",
      "They require ECG-like morphology input and should not be interpreted as direct respiratory-belt measurement."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      edr_timeseries = edr_timeseries,
      component_summary = component_summary,
      settings = list(
        ecg_cols = ecg_cols,
        time_col = time_col,
        group_cols = group_cols,
        n_components = n_components,
        scale = scale,
        output_prefix = output_prefix
      )
    ),
    class = c("gazepoint_edr_pca", "list")
  )
}

#' Analyse endosomatic skin-potential recordings
#'
#' Computes skin-potential level and skin-potential response descriptors from a
#' voltage-like skin-potential column. This is for endosomatic skin-potential
#' recordings, not standard exosomatic skin conductance.
#'
#' @param dat A data frame.
#' @param sp_col Numeric skin-potential column, usually in millivolts.
#' @param time_col Numeric time column.
#' @param group_cols Optional grouping columns.
#' @param response_direction `"both"`, `"positive"`, or `"negative"`.
#' @param response_threshold Optional absolute threshold for response detection.
#'   If `NULL`, a MAD-based derivative threshold is used.
#' @param min_response_distance_s Minimum distance between detected responses.
#'
#' @return A list with `overview`, `level_summary`, `response_table`,
#'   `timeseries`, and `settings`.
#' @export
analyze_gazepoint_skin_potential <- function(dat,
                                             sp_col,
                                             time_col,
                                             group_cols = NULL,
                                             response_direction = c("both", "positive", "negative"),
                                             response_threshold = NULL,
                                             min_response_distance_s = 1) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  response_direction <- match.arg(response_direction)

  required <- c(sp_col, time_col)
  missing_required <- setdiff(required, names(dat))
  if (length(missing_required) > 0) {
    stop("Missing required columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  if (!is.numeric(dat[[sp_col]])) {
    stop("`sp_col` must identify a numeric skin-potential column.", call. = FALSE)
  }

  if (!is.numeric(dat[[time_col]])) {
    stop("`time_col` must identify a numeric time column.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  missing_groups <- setdiff(group_cols, names(dat))
  if (length(missing_groups) > 0) {
    stop("Missing `group_cols`: ", paste(missing_groups, collapse = ", "), call. = FALSE)
  }

  groups <- gpbiometrics_modality_split(dat, group_cols)

  level_rows <- list()
  response_rows <- list()
  timeseries_rows <- list()
  response_id <- 1L

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]
    idx <- idx[order(dat[[time_col]][idx])]

    time <- dat[[time_col]][idx]
    sp <- dat[[sp_col]][idx]

    finite <- is.finite(time) & is.finite(sp)

    spl_center <- if (any(finite)) {
      stats::median(sp[finite], na.rm = TRUE)
    } else {
      NA_real_
    }

    sp_centered <- sp - spl_center
    derivative <- rep(NA_real_, length(sp))

    if (length(sp) >= 2) {
      dt <- diff(time)
      dsp <- diff(sp)
      derivative[-1] <- ifelse(is.finite(dt) & dt != 0, dsp / dt, NA_real_)
    }

    threshold <- response_threshold

    if (is.null(threshold)) {
      mad_derivative <- stats::mad(derivative, constant = 1, na.rm = TRUE)
      if (!is.finite(mad_derivative) || mad_derivative == 0) {
        mad_derivative <- stats::sd(derivative, na.rm = TRUE)
      }
      if (!is.finite(mad_derivative) || mad_derivative == 0) {
        mad_derivative <- NA_real_
      }
      threshold <- 6 * mad_derivative
    }

    candidate <- gpbiometrics_skin_potential_candidates(
      derivative = derivative,
      threshold = threshold,
      direction = response_direction
    )

    event_idx <- gpbiometrics_skin_potential_select_events(
      candidate = candidate,
      time = time,
      amplitude = derivative,
      min_distance_s = min_response_distance_s
    )

    response_flag <- rep(FALSE, length(idx))
    response_flag[event_idx] <- TRUE

    if (length(event_idx) > 0) {
      for (j in seq_along(event_idx)) {
        local_idx <- event_idx[j]
        response_rows[[response_id]] <- data.frame(
          group_id = group_id,
          response_index = j,
          row_index = idx[local_idx],
          response_time = time[local_idx],
          skin_potential = sp[local_idx],
          centered_skin_potential = sp_centered[local_idx],
          derivative = derivative[local_idx],
          response_polarity = if (derivative[local_idx] > 0) {
            "positive"
          } else if (derivative[local_idx] < 0) {
            "negative"
          } else {
            "zero"
          },
          stringsAsFactors = FALSE
        )
        response_id <- response_id + 1L
      }
    }

    timeseries_rows[[group_id]] <- data.frame(
      row_index = idx,
      group_id = group_id,
      time = time,
      skin_potential = sp,
      centered_skin_potential = sp_centered,
      skin_potential_derivative = derivative,
      skin_potential_response = response_flag,
      stringsAsFactors = FALSE
    )

    level_rows[[group_id]] <- data.frame(
      group_id = group_id,
      n_rows = length(idx),
      n_finite = sum(finite),
      mean_spl = mean(sp[finite], na.rm = TRUE),
      median_spl = stats::median(sp[finite], na.rm = TRUE),
      sd_spl = stats::sd(sp[finite], na.rm = TRUE),
      min_spl = min(sp[finite], na.rm = TRUE),
      max_spl = max(sp[finite], na.rm = TRUE),
      response_count = length(event_idx),
      response_rate_per_min = gpbiometrics_skin_potential_rate(time, length(event_idx)),
      threshold_used = threshold,
      status = if (sum(finite) > 0) {
        "skin_potential_analysed"
      } else {
        "no_valid_skin_potential"
      },
      stringsAsFactors = FALSE
    )
  }

  level_summary <- do.call(rbind, level_rows)
  rownames(level_summary) <- NULL

  response_table <- if (length(response_rows) > 0) {
    do.call(rbind, response_rows)
  } else {
    data.frame()
  }

  timeseries <- do.call(rbind, timeseries_rows)
  rownames(timeseries) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    timeseries_rows = nrow(timeseries),
    response_rows = nrow(response_table),
    successful_groups = sum(level_summary$status == "skin_potential_analysed"),
    problem_groups = sum(level_summary$status != "skin_potential_analysed"),
    status = if (all(level_summary$status == "skin_potential_analysed")) {
      "skin_potential_analysis_complete"
    } else if (any(level_summary$status == "skin_potential_analysed")) {
      "skin_potential_analysis_partial"
    } else {
      "skin_potential_analysis_failed"
    },
    interpretation = paste(
      "Skin potential analysis is for endosomatic voltage-like recordings, not exosomatic skin conductance.",
      "Outputs are SPL/SPR descriptors and do not infer emotion, stress, cognition, health status, or diagnosis."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      level_summary = level_summary,
      response_table = response_table,
      timeseries = timeseries,
      settings = list(
        sp_col = sp_col,
        time_col = time_col,
        group_cols = group_cols,
        response_direction = response_direction,
        response_threshold = response_threshold,
        min_response_distance_s = min_response_distance_s
      )
    ),
    class = c("gazepoint_skin_potential_analysis", "list")
  )
}

gpbiometrics_modality_split <- function(dat, group_cols) {
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

gpbiometrics_quantization_resolution <- function(signal_col, resolution) {
  if (length(resolution) == 1 && is.null(names(resolution))) {
    return(as.numeric(resolution[1]))
  }

  if (!is.null(names(resolution)) && signal_col %in% names(resolution)) {
    return(as.numeric(resolution[[signal_col]]))
  }

  if (length(resolution) == 1) {
    return(as.numeric(resolution[1]))
  }

  stop(
    "When `resolution` has multiple values, it must be named and include `",
    signal_col,
    "`.",
    call. = FALSE
  )
}

gpbiometrics_skin_potential_candidates <- function(derivative,
                                                   threshold,
                                                   direction = "both") {
  if (!is.finite(threshold) || threshold <= 0) {
    return(integer())
  }

  if (direction == "positive") {
    return(which(is.finite(derivative) & derivative >= threshold))
  }

  if (direction == "negative") {
    return(which(is.finite(derivative) & derivative <= -threshold))
  }

  which(is.finite(derivative) & abs(derivative) >= threshold)
}

gpbiometrics_skin_potential_select_events <- function(candidate,
                                                      time,
                                                      amplitude,
                                                      min_distance_s = 1) {
  if (length(candidate) == 0) {
    return(integer())
  }

  candidate <- candidate[is.finite(time[candidate])]

  if (length(candidate) == 0) {
    return(integer())
  }

  selected <- candidate[1]

  if (length(candidate) > 1) {
    for (idx in candidate[-1]) {
      last <- selected[length(selected)]

      if ((time[idx] - time[last]) >= min_distance_s) {
        selected <- c(selected, idx)
      } else if (abs(amplitude[idx]) > abs(amplitude[last])) {
        selected[length(selected)] <- idx
      }
    }
  }

  selected
}

gpbiometrics_skin_potential_rate <- function(time, event_count) {
  time <- time[is.finite(time)]

  if (length(time) < 2) {
    return(NA_real_)
  }

  duration <- max(time) - min(time)

  if (!is.finite(duration) || duration <= 0) {
    return(NA_real_)
  }

  event_count / duration * 60
}
