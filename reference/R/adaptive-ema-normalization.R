#' Adaptive EMA normalization for non-stationary EDA
#'
#' Applies dependency-light adaptive normalization using an exponential moving
#' average center and robust local scale after IQR-based outlier screening.
#' This preserves local dynamics more than whole-session z-scoring, but it is
#' still a preprocessing transformation and not an emotion/stress classifier.
#'
#' @param dat A data frame.
#' @param signal_col Numeric signal column.
#' @param group_cols Optional grouping columns.
#' @param time_col Optional time column used to order rows within group.
#' @param alpha EMA smoothing parameter in `(0, 1]`.
#' @param iqr_multiplier IQR multiplier for outlier screening.
#' @param suffix Suffix for the normalized output column.
#' @param center_suffix Suffix for the EMA center column.
#' @param scale_suffix Suffix for the EMA scale column.
#' @param min_scale Minimum scale used to avoid division by zero.
#' @param overwrite Logical. If `FALSE`, existing output columns are protected.
#'
#' @return A data frame with adaptive normalized signal columns and attributes.
#' @export
standardise_gazepoint_adaptive_ema <- function(dat,
                                               signal_col = "GSR_US",
                                               group_cols = NULL,
                                               time_col = NULL,
                                               alpha = 0.05,
                                               iqr_multiplier = 1.5,
                                               suffix = "_adaptive_ema",
                                               center_suffix = "_ema_center",
                                               scale_suffix = "_ema_scale",
                                               min_scale = 1e-8,
                                               overwrite = FALSE) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  if (!signal_col %in% names(dat)) {
    stop("Column `", signal_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!is.numeric(dat[[signal_col]])) {
    stop("`signal_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.null(time_col) && !time_col %in% names(dat)) {
    stop("Column `", time_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  missing_groups <- setdiff(group_cols, names(dat))
  if (length(missing_groups) > 0) {
    stop("Missing `group_cols`: ", paste(missing_groups, collapse = ", "), call. = FALSE)
  }

  if (!is.numeric(alpha) || length(alpha) != 1 || !is.finite(alpha) || alpha <= 0 || alpha > 1) {
    stop("`alpha` must be a finite number in `(0, 1]`.", call. = FALSE)
  }

  out_col <- paste0(signal_col, suffix)
  center_col <- paste0(signal_col, center_suffix)
  scale_col <- paste0(signal_col, scale_suffix)
  status_col <- paste0(signal_col, "_adaptive_ema_status")

  new_cols <- c(out_col, center_col, scale_col, status_col)

  if (!isTRUE(overwrite) && any(new_cols %in% names(dat))) {
    stop(
      "One or more output columns already exist: ",
      paste(intersect(new_cols, names(dat)), collapse = ", "),
      ". Use `overwrite = TRUE`.",
      call. = FALSE
    )
  }

  out <- dat
  out[[out_col]] <- NA_real_
  out[[center_col]] <- NA_real_
  out[[scale_col]] <- NA_real_
  out[[status_col]] <- "not_processed"

  groups <- gpbiometrics_adaptive_ema_split(out, group_cols)

  summary_rows <- lapply(names(groups), function(unit_id) {
    idx <- groups[[unit_id]]

    if (!is.null(time_col)) {
      idx <- idx[order(out[[time_col]][idx])]
    }

    x <- out[[signal_col]][idx]
    finite <- is.finite(x)

    if (sum(finite) < 5) {
      out[[status_col]][idx] <<- "insufficient_finite_samples"
      return(data.frame(
        unit_id = unit_id,
        n_rows = length(idx),
        n_finite = sum(finite),
        n_outliers = NA_integer_,
        status = "insufficient_finite_samples",
        stringsAsFactors = FALSE
      ))
    }

    q <- stats::quantile(x[finite], probs = c(0.25, 0.75), na.rm = TRUE, names = FALSE)
    iqr <- q[2] - q[1]

    lower <- q[1] - iqr_multiplier * iqr
    upper <- q[2] + iqr_multiplier * iqr

    clean <- x
    outlier <- is.finite(clean) & (clean < lower | clean > upper)
    clean[outlier] <- NA_real_

    clean_filled <- gpbiometrics_adaptive_fill(clean)
    center <- gpbiometrics_adaptive_ema(clean_filled, alpha = alpha)

    abs_dev <- abs(clean_filled - center)
    scale <- gpbiometrics_adaptive_ema(abs_dev, alpha = alpha) * 1.4826
    scale[!is.finite(scale) | scale < min_scale] <- min_scale

    normalized <- (x - center) / scale

    out[[out_col]][idx] <<- normalized
    out[[center_col]][idx] <<- center
    out[[scale_col]][idx] <<- scale
    out[[status_col]][idx] <<- ifelse(outlier, "iqr_outlier_used_for_output_not_center", "adaptive_ema_normalized")

    data.frame(
      unit_id = unit_id,
      n_rows = length(idx),
      n_finite = sum(finite),
      n_outliers = sum(outlier, na.rm = TRUE),
      status = "adaptive_ema_normalized",
      stringsAsFactors = FALSE
    )
  })

  summary_table <- do.call(rbind, summary_rows)
  rownames(summary_table) <- NULL

  overview <- data.frame(
    input_rows = nrow(dat),
    group_count = length(groups),
    successful_groups = sum(summary_table$status == "adaptive_ema_normalized"),
    problem_groups = sum(summary_table$status != "adaptive_ema_normalized"),
    signal_col = signal_col,
    output_col = out_col,
    status = if (all(summary_table$status == "adaptive_ema_normalized")) {
      "adaptive_ema_normalization_complete"
    } else if (any(summary_table$status == "adaptive_ema_normalized")) {
      "adaptive_ema_normalization_partial"
    } else {
      "adaptive_ema_normalization_failed"
    },
    interpretation = paste(
      "Adaptive EMA normalization estimates local signal center and scale after IQR-based outlier screening.",
      "It is a preprocessing transformation and does not infer emotion, stress, cognition, trust, preference, or diagnosis."
    ),
    stringsAsFactors = FALSE
  )

  attr(out, "adaptive_ema_overview") <- overview
  attr(out, "adaptive_ema_summary") <- summary_table
  attr(out, "adaptive_ema_settings") <- list(
    signal_col = signal_col,
    group_cols = group_cols,
    time_col = time_col,
    alpha = alpha,
    iqr_multiplier = iqr_multiplier,
    suffix = suffix,
    center_suffix = center_suffix,
    scale_suffix = scale_suffix,
    min_scale = min_scale,
    overwrite = overwrite
  )

  class(out) <- unique(c("gazepoint_adaptive_ema_normalised", class(out)))
  out
}

#' @rdname standardise_gazepoint_adaptive_ema
#' @export
standardize_gazepoint_adaptive_ema <- standardise_gazepoint_adaptive_ema

gpbiometrics_adaptive_ema_split <- function(dat, group_cols) {
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

gpbiometrics_adaptive_fill <- function(x) {
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

gpbiometrics_adaptive_ema <- function(x, alpha) {
  out <- numeric(length(x))
  out[1] <- x[1]

  if (length(x) > 1) {
    for (i in 2:length(x)) {
      out[i] <- alpha * x[i] + (1 - alpha) * out[i - 1]
    }
  }

  out
}
