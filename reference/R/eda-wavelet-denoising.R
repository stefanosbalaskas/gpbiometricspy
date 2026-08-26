#' Denoise EDA using dependency-light Haar wavelet shrinkage
#'
#' Applies simple Haar wavelet soft-threshold denoising to EDA signals within
#' optional groups. This is a dependency-light wavelet denoising helper and
#' should not be described as an exact reproduction of stationary-wavelet
#' artifact-removal algorithms.
#'
#' @param dat A data frame containing EDA data.
#' @param eda_col EDA/conductance column.
#' @param group_cols Optional grouping columns.
#' @param output_col Optional output column.
#' @param levels Number of Haar decomposition levels.
#' @param threshold_multiplier Multiplier applied to the robust noise estimate.
#' @param overwrite Logical. If `FALSE`, protect existing output columns.
#'
#' @return A data frame with denoised EDA and denoising attributes.
#' @export
denoise_gazepoint_eda_wavelet <- function(dat,
                                          eda_col = "GSR_US",
                                          group_cols = NULL,
                                          output_col = NULL,
                                          levels = 3,
                                          threshold_multiplier = 1,
                                          overwrite = FALSE) {
  if (!is.data.frame(dat)) stop("`dat` must be a data frame.", call. = FALSE)
  if (!eda_col %in% names(dat)) stop("Column `", eda_col, "` was not found in `dat`.", call. = FALSE)
  if (!is.numeric(dat[[eda_col]])) stop("`eda_col` must identify a numeric column.", call. = FALSE)

  if (is.null(output_col)) output_col <- paste0(eda_col, "_wavelet_denoised")

  if (!isTRUE(overwrite) && output_col %in% names(dat)) {
    stop("Output column `", output_col, "` already exists. Use `overwrite = TRUE`.", call. = FALSE)
  }

  if (!is.numeric(levels) || length(levels) != 1 || levels < 1) {
    stop("`levels` must be a positive integer.", call. = FALSE)
  }

  if (!is.numeric(threshold_multiplier) || length(threshold_multiplier) != 1 || threshold_multiplier <= 0) {
    stop("`threshold_multiplier` must be positive.", call. = FALSE)
  }

  levels <- as.integer(levels)

  if (is.null(group_cols)) group_cols <- character()
  missing_groups <- setdiff(group_cols, names(dat))
  if (length(missing_groups) > 0) {
    stop("Missing `group_cols`: ", paste(missing_groups, collapse = ", "), call. = FALSE)
  }

  out <- dat
  out[[output_col]] <- NA_real_

  groups <- gpbiometrics_wavelet_split_indices(out, group_cols)

  rows <- lapply(names(groups), function(unit_id) {
    idx <- groups[[unit_id]]
    x <- out[[eda_col]][idx]
    finite <- is.finite(x)

    status <- "wavelet_denoised"

    if (sum(finite) < 8) {
      status <- "insufficient_finite_samples"
      return(data.frame(
        unit_id = unit_id,
        n_rows = length(idx),
        n_finite = sum(finite),
        threshold = NA_real_,
        levels_used = NA_integer_,
        status = status,
        stringsAsFactors = FALSE
      ))
    }

    x_fill <- gpbiometrics_wavelet_fill_linear(x)
    den <- gpbiometrics_haar_denoise(x_fill, levels = levels, threshold_multiplier = threshold_multiplier)
    den[!finite] <- NA_real_
    out[[output_col]][idx] <<- den$signal

    data.frame(
      unit_id = unit_id,
      n_rows = length(idx),
      n_finite = sum(finite),
      threshold = den$threshold,
      levels_used = den$levels_used,
      status = status,
      stringsAsFactors = FALSE
    )
  })

  summary_table <- do.call(rbind, rows)
  rownames(summary_table) <- NULL

  overview <- data.frame(
    input_rows = nrow(dat),
    group_count = length(groups),
    successful_groups = sum(summary_table$status == "wavelet_denoised"),
    problem_groups = sum(summary_table$status != "wavelet_denoised"),
    eda_col = eda_col,
    output_col = output_col,
    status = if (all(summary_table$status == "wavelet_denoised")) {
      "eda_wavelet_denoising_complete"
    } else if (any(summary_table$status == "wavelet_denoised")) {
      "eda_wavelet_denoising_partial"
    } else {
      "eda_wavelet_denoising_failed"
    },
    interpretation = paste(
      "Wavelet-denoised EDA is a signal-recovery aid.",
      "It should be compared with raw and artifact-flagged data and does not infer emotion, stress, cognition, or diagnosis."
    ),
    stringsAsFactors = FALSE
  )

  attr(out, "wavelet_denoising_overview") <- overview
  attr(out, "wavelet_denoising_summary") <- summary_table
  attr(out, "wavelet_denoising_settings") <- list(
    eda_col = eda_col,
    group_cols = group_cols,
    output_col = output_col,
    levels = levels,
    threshold_multiplier = threshold_multiplier,
    overwrite = overwrite
  )

  class(out) <- unique(c("gazepoint_eda_wavelet_denoised", class(out)))

  out
}

gpbiometrics_wavelet_split_indices <- function(dat, group_cols) {
  if (length(group_cols) == 0) return(list(all_rows = seq_len(nrow(dat))))
  gf <- dat[group_cols]
  gf[] <- lapply(gf, function(x) {
    x <- as.character(x)
    x[is.na(x)] <- "<NA>"
    x
  })
  split(seq_len(nrow(dat)), do.call(paste, c(gf, sep = " | ")))
}

gpbiometrics_wavelet_fill_linear <- function(x) {
  idx <- seq_along(x)
  finite <- is.finite(x)

  if (all(finite)) return(x)
  if (sum(finite) < 2) return(rep(mean(x[finite], na.rm = TRUE), length(x)))

  stats::approx(idx[finite], x[finite], xout = idx, rule = 2)$y
}

gpbiometrics_haar_denoise <- function(x, levels = 3, threshold_multiplier = 1) {
  original_n <- length(x)
  target_n <- 2^ceiling(log2(original_n))
  padded <- c(x, rep(stats::median(x, na.rm = TRUE), target_n - original_n))

  coeffs <- list()
  approx <- padded
  levels_used <- 0L

  for (lev in seq_len(levels)) {
    if (length(approx) < 2 || length(approx) %% 2 != 0) break

    a <- (approx[seq(1, length(approx), by = 2)] + approx[seq(2, length(approx), by = 2)]) / sqrt(2)
    d <- (approx[seq(1, length(approx), by = 2)] - approx[seq(2, length(approx), by = 2)]) / sqrt(2)

    coeffs[[lev]] <- d
    approx <- a
    levels_used <- lev
  }

  if (length(coeffs) == 0) {
    return(list(signal = x, threshold = NA_real_, levels_used = 0L))
  }

  finest <- coeffs[[1]]
  sigma <- stats::median(abs(finest - stats::median(finest, na.rm = TRUE)), na.rm = TRUE) / 0.6745
  threshold <- threshold_multiplier * sigma * sqrt(2 * log(length(padded)))

  coeffs <- lapply(coeffs, function(d) {
    sign(d) * pmax(abs(d) - threshold, 0)
  })

  recon <- approx

  for (lev in rev(seq_len(levels_used))) {
    d <- coeffs[[lev]]
    up <- numeric(length(d) * 2)
    up[seq(1, length(up), by = 2)] <- (recon + d) / sqrt(2)
    up[seq(2, length(up), by = 2)] <- (recon - d) / sqrt(2)
    recon <- up
  }

  list(signal = recon[seq_len(original_n)], threshold = threshold, levels_used = levels_used)
}
