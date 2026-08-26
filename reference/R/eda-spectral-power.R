#' Extract frequency-domain EDA spectral power
#'
#' Computes power spectral density summaries for an EDA signal, including
#' spectral power in the EDASymp-inspired 0.045--0.25 Hz band. This is a
#' descriptive spectral feature and should not be interpreted as direct stress,
#' emotion, valence, cognition, trust, preference, or diagnosis.
#'
#' @param dat A data frame containing EDA data.
#' @param eda_col EDA/conductance column.
#' @param time_col Optional time column.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate Optional sampling rate in Hz. Required if `time_col`
#'   does not allow sampling-rate estimation.
#' @param band Numeric vector of length two defining the frequency band in Hz.
#' @param min_samples Minimum finite samples per group.
#' @param detrend Logical. If `TRUE`, remove a linear trend before spectral analysis.
#'
#' @return A list with `overview`, `spectral_summary`, `settings`, and
#'   interpretation text.
#' @export
extract_gazepoint_eda_spectral_power <- function(dat,
                                                 eda_col = "GSR_US",
                                                 time_col = NULL,
                                                 group_cols = NULL,
                                                 sampling_rate = NULL,
                                                 band = c(0.045, 0.25),
                                                 min_samples = 32,
                                                 detrend = TRUE) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  if (!eda_col %in% names(dat)) {
    stop("Column `", eda_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!is.numeric(dat[[eda_col]])) {
    stop("`eda_col` must identify a numeric column.", call. = FALSE)
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

  if (!is.numeric(band) || length(band) != 2 || any(!is.finite(band)) || band[1] <= 0 || band[1] >= band[2]) {
    stop("`band` must be a positive numeric vector of length two with lower < upper.", call. = FALSE)
  }

  if (!is.numeric(min_samples) || length(min_samples) != 1 || min_samples < 4) {
    stop("`min_samples` must be a number >= 4.", call. = FALSE)
  }

  groups <- gpbiometrics_spectral_split_indices(dat, group_cols)

  rows <- lapply(names(groups), function(unit_id) {
    idx <- groups[[unit_id]]
    x <- dat[[eda_col]][idx]

    time_values <- if (!is.null(time_col)) dat[[time_col]][idx] else NULL
    fs <- gpbiometrics_spectral_sampling_rate(time_values, sampling_rate)

    finite <- is.finite(x)
    n_finite <- sum(finite)

    base <- gpbiometrics_spectral_unit_values(dat, idx, group_cols, unit_id)

    if (n_finite < min_samples || !is.finite(fs) || fs <= 0) {
      return(data.frame(
        base,
        unit_id = unit_id,
        n_rows = length(idx),
        n_finite = n_finite,
        sampling_rate_hz = fs,
        total_power = NA_real_,
        band_power = NA_real_,
        relative_band_power = NA_real_,
        peak_frequency_hz = NA_real_,
        spectral_centroid_hz = NA_real_,
        band_lower_hz = band[1],
        band_upper_hz = band[2],
        status = "insufficient_data",
        stringsAsFactors = FALSE,
        check.names = FALSE
      ))
    }

    y <- x[finite]

    if (isTRUE(detrend) && length(y) >= 3) {
      y <- stats::resid(stats::lm(y ~ seq_along(y)))
    } else {
      y <- y - mean(y, na.rm = TRUE)
    }

    spec <- stats::spec.pgram(
      y,
      spans = NULL,
      taper = 0.1,
      plot = FALSE,
      fast = TRUE,
      demean = TRUE,
      detrend = FALSE
    )

    freq <- spec$freq * fs
    power <- spec$spec

    keep_positive <- is.finite(freq) & is.finite(power) & freq > 0

    freq <- freq[keep_positive]
    power <- power[keep_positive]

    in_band <- freq >= band[1] & freq <= band[2]

    total_power <- sum(power, na.rm = TRUE)
    band_power <- sum(power[in_band], na.rm = TRUE)

    rel_band <- if (is.finite(total_power) && total_power > 0) {
      band_power / total_power
    } else {
      NA_real_
    }

    peak_frequency <- if (length(power) > 0 && any(is.finite(power))) {
      freq[which.max(power)]
    } else {
      NA_real_
    }

    centroid <- if (sum(power, na.rm = TRUE) > 0) {
      sum(freq * power, na.rm = TRUE) / sum(power, na.rm = TRUE)
    } else {
      NA_real_
    }

    data.frame(
      base,
      unit_id = unit_id,
      n_rows = length(idx),
      n_finite = n_finite,
      sampling_rate_hz = fs,
      total_power = total_power,
      band_power = band_power,
      relative_band_power = rel_band,
      peak_frequency_hz = peak_frequency,
      spectral_centroid_hz = centroid,
      band_lower_hz = band[1],
      band_upper_hz = band[2],
      status = "spectral_power_extracted",
      stringsAsFactors = FALSE,
      check.names = FALSE
    )
  })

  spectral_summary <- do.call(rbind, rows)
  rownames(spectral_summary) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    spectral_rows = nrow(spectral_summary),
    successful_groups = sum(spectral_summary$status == "spectral_power_extracted"),
    problem_groups = sum(spectral_summary$status != "spectral_power_extracted"),
    eda_col = eda_col,
    band_lower_hz = band[1],
    band_upper_hz = band[2],
    status = if (all(spectral_summary$status == "spectral_power_extracted")) {
      "eda_spectral_power_extracted"
    } else if (any(spectral_summary$status == "spectral_power_extracted")) {
      "eda_spectral_power_partial"
    } else {
      "eda_spectral_power_failed"
    },
    interpretation = paste(
      "Spectral EDA features quantify frequency-domain signal properties.",
      "Band power in the 0.045--0.25 Hz range is an EDASymp-inspired descriptive feature.",
      "It is not a direct stress, emotion, valence, cognition, trust, preference, or diagnosis measure."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      spectral_summary = spectral_summary,
      settings = list(
        eda_col = eda_col,
        time_col = time_col,
        group_cols = group_cols,
        sampling_rate = sampling_rate,
        band = band,
        min_samples = min_samples,
        detrend = detrend
      )
    ),
    class = c("gazepoint_eda_spectral_power", "list")
  )
}

gpbiometrics_spectral_split_indices <- function(dat, group_cols) {
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

gpbiometrics_spectral_unit_values <- function(dat, idx, group_cols, unit_id) {
  if (length(group_cols) == 0) {
    return(data.frame(unit_label = unit_id, stringsAsFactors = FALSE))
  }

  values <- lapply(group_cols, function(nm) as.character(dat[[nm]][idx[1]]))
  names(values) <- group_cols
  as.data.frame(values, stringsAsFactors = FALSE, optional = TRUE)
}

gpbiometrics_spectral_sampling_rate <- function(time_values = NULL, sampling_rate = NULL) {
  if (!is.null(sampling_rate)) {
    if (!is.numeric(sampling_rate) || length(sampling_rate) != 1 || !is.finite(sampling_rate) || sampling_rate <= 0) {
      stop("`sampling_rate` must be a positive finite number.", call. = FALSE)
    }
    return(as.numeric(sampling_rate))
  }

  if (is.null(time_values)) {
    return(NA_real_)
  }

  time_values <- time_values[is.finite(time_values)]

  if (length(time_values) < 3) {
    return(NA_real_)
  }

  dt <- diff(time_values)
  dt <- dt[is.finite(dt) & dt > 0]

  if (length(dt) == 0) {
    return(NA_real_)
  }

  median_dt <- stats::median(dt)

  if (median_dt > 10) {
    return(1000 / median_dt)
  }

  1 / median_dt
}
