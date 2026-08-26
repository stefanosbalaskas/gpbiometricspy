#' Extract time-varying spectral EDA features
#'
#' Computes a dependency-light approximation of TVSymp-style time-varying
#' spectral EDA power using sliding-window spectral analysis. The default band
#' is 0.08--0.24 Hz, following the TVSymp literature. This function does not
#' claim exact VFCDM reproduction.
#'
#' @param dat A data frame containing EDA data.
#' @param eda_col Numeric EDA/conductance column.
#' @param time_col Numeric time column.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate Optional sampling rate in Hz. If `NULL`, estimated from
#'   `time_col`.
#' @param band Frequency band in Hz used for TVSymp-style power.
#' @param window_seconds Sliding-window length in seconds.
#' @param step_seconds Sliding-window step in seconds.
#' @param min_valid_fraction Minimum valid fraction per window.
#' @param normalise Logical. If `TRUE`, compute EDASympn-style relative band
#'   power normalised by total positive-frequency power.
#'
#' @return A list with `overview`, `tvsymp_timeseries`, `summary`, and `settings`.
#' @export
extract_gazepoint_eda_tvsymp <- function(dat,
                                         eda_col = "GSR_US",
                                         time_col = "CNT",
                                         group_cols = NULL,
                                         sampling_rate = NULL,
                                         band = c(0.08, 0.24),
                                         window_seconds = 60,
                                         step_seconds = 5,
                                         min_valid_fraction = 0.70,
                                         normalise = TRUE) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  if (!eda_col %in% names(dat)) {
    stop("Column `", eda_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!time_col %in% names(dat)) {
    stop("Column `", time_col, "` was not found in `dat`.", call. = FALSE)
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

  if (!is.numeric(band) ||
      length(band) != 2 ||
      any(!is.finite(band)) ||
      band[1] <= 0 ||
      band[1] >= band[2]) {
    stop("`band` must be a positive numeric vector of length two.", call. = FALSE)
  }

  groups <- gpbiometrics_tvsymp_split_indices(dat, group_cols)

  rows <- list()
  row_id <- 1L

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]
    idx <- idx[order(dat[[time_col]][idx])]

    time <- dat[[time_col]][idx]
    eda <- dat[[eda_col]][idx]

    fs <- gpbiometrics_tvsymp_sampling_rate(time, sampling_rate)

    if (!is.finite(fs) || fs <= 0) {
      rows[[row_id]] <- data.frame(
        group_id = group_id,
        window_index = NA_integer_,
        window_start = NA_real_,
        window_end = NA_real_,
        window_midpoint = NA_real_,
        n_samples = length(idx),
        valid_fraction = mean(is.finite(eda)),
        sampling_rate_hz = fs,
        tvsymp_power = NA_real_,
        edasympn = NA_real_,
        total_power = NA_real_,
        status = "sampling_rate_not_available",
        stringsAsFactors = FALSE
      )
      row_id <- row_id + 1L
      next
    }

    min_time <- min(time, na.rm = TRUE)
    max_time <- max(time, na.rm = TRUE)

    starts <- seq(min_time, max_time - window_seconds, by = step_seconds)

    if (length(starts) == 0) {
      starts <- min_time
    }

    for (i in seq_along(starts)) {
      w_start <- starts[i]
      w_end <- w_start + window_seconds
      in_window <- is.finite(time) & time >= w_start & time <= w_end

      x <- eda[in_window]
      valid_fraction <- mean(is.finite(x))

      if (length(x) < 8 || valid_fraction < min_valid_fraction) {
        rows[[row_id]] <- data.frame(
          group_id = group_id,
          window_index = i,
          window_start = w_start,
          window_end = w_end,
          window_midpoint = mean(c(w_start, w_end)),
          n_samples = length(x),
          valid_fraction = valid_fraction,
          sampling_rate_hz = fs,
          tvsymp_power = NA_real_,
          edasympn = NA_real_,
          total_power = NA_real_,
          status = "insufficient_window_data",
          stringsAsFactors = FALSE
        )
        row_id <- row_id + 1L
        next
      }

      x <- gpbiometrics_tvsymp_fill_linear(x)
      x <- x - mean(x, na.rm = TRUE)

      spec <- stats::spec.pgram(
        x,
        taper = 0.1,
        plot = FALSE,
        demean = TRUE,
        detrend = TRUE,
        fast = TRUE
      )

      freq <- spec$freq * fs
      power <- spec$spec

      keep <- is.finite(freq) & is.finite(power) & freq > 0
      freq <- freq[keep]
      power <- power[keep]

      in_band <- freq >= band[1] & freq <= band[2]
      tvsymp_power <- sum(power[in_band], na.rm = TRUE)
      total_power <- sum(power, na.rm = TRUE)

      edasympn <- if (isTRUE(normalise) && is.finite(total_power) && total_power > 0) {
        tvsymp_power / total_power
      } else {
        NA_real_
      }

      rows[[row_id]] <- data.frame(
        group_id = group_id,
        window_index = i,
        window_start = w_start,
        window_end = w_end,
        window_midpoint = mean(c(w_start, w_end)),
        n_samples = length(x),
        valid_fraction = valid_fraction,
        sampling_rate_hz = fs,
        tvsymp_power = tvsymp_power,
        edasympn = edasympn,
        total_power = total_power,
        status = "tvsymp_extracted",
        stringsAsFactors = FALSE
      )

      row_id <- row_id + 1L
    }
  }

  tvsymp_timeseries <- do.call(rbind, rows)
  rownames(tvsymp_timeseries) <- NULL

  summary <- stats::aggregate(
    cbind(tvsymp_power, edasympn) ~ group_id,
    data = tvsymp_timeseries,
    FUN = function(x) mean(x, na.rm = TRUE)
  )

  names(summary)[names(summary) == "tvsymp_power"] <- "mean_tvsymp_power"
  names(summary)[names(summary) == "edasympn"] <- "mean_edasympn"

  overview <- data.frame(
    group_count = length(groups),
    window_rows = nrow(tvsymp_timeseries),
    successful_windows = sum(tvsymp_timeseries$status == "tvsymp_extracted"),
    problem_windows = sum(tvsymp_timeseries$status != "tvsymp_extracted"),
    band_lower_hz = band[1],
    band_upper_hz = band[2],
    status = if (all(tvsymp_timeseries$status == "tvsymp_extracted")) {
      "tvsymp_extraction_complete"
    } else if (any(tvsymp_timeseries$status == "tvsymp_extracted")) {
      "tvsymp_extraction_partial"
    } else {
      "tvsymp_extraction_failed"
    },
    interpretation = paste(
      "TVSymp-style features describe time-varying EDA spectral power.",
      "This is a sliding-window spectral approximation, not exact VFCDM reproduction.",
      "Outputs should not be interpreted as direct stress, emotion, cognition, health status, or diagnosis."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      tvsymp_timeseries = tvsymp_timeseries,
      summary = summary,
      settings = list(
        eda_col = eda_col,
        time_col = time_col,
        group_cols = group_cols,
        sampling_rate = sampling_rate,
        band = band,
        window_seconds = window_seconds,
        step_seconds = step_seconds,
        min_valid_fraction = min_valid_fraction,
        normalise = normalise
      )
    ),
    class = c("gazepoint_eda_tvsymp", "list")
  )
}

gpbiometrics_tvsymp_split_indices <- function(dat, group_cols) {
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

gpbiometrics_tvsymp_sampling_rate <- function(time, sampling_rate = NULL) {
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

gpbiometrics_tvsymp_fill_linear <- function(x) {
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
