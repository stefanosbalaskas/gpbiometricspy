#' Extract nonlinear HRV features from IBI/RR intervals
#'
#' Computes dependency-light nonlinear HRV descriptors from IBI/RR intervals,
#' including Poincare SD1/SD2, sample entropy, approximate entropy,
#' multiscale entropy, and detrended fluctuation analysis.
#'
#' These are variability and complexity descriptors. They should not be
#' interpreted as direct emotion, cognitive-load, health-status, or diagnostic
#' labels by themselves.
#'
#' @param dat A data frame containing IBI/RR intervals.
#' @param ibi_col IBI/RR interval column.
#' @param group_cols Optional grouping columns.
#' @param min_intervals Minimum finite intervals per group.
#' @param sampen_m Embedding dimension for sample entropy.
#' @param sampen_r_multiplier Tolerance multiplier applied to the within-group SD.
#' @param mse_scales Integer scales used for multiscale entropy.
#'
#' @return A list with `overview`, `features`, and `settings`.
#' @export
extract_gazepoint_hrv_nonlinear <- function(dat,
                                            ibi_col = "IBI",
                                            group_cols = NULL,
                                            min_intervals = 10,
                                            sampen_m = 2,
                                            sampen_r_multiplier = 0.2,
                                            mse_scales = 1:5) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  if (!ibi_col %in% names(dat)) {
    stop("Column `", ibi_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!is.numeric(dat[[ibi_col]])) {
    stop("`ibi_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.numeric(mse_scales) ||
      length(mse_scales) < 1 ||
      any(!is.finite(mse_scales)) ||
      any(mse_scales < 1)) {
    stop("`mse_scales` must be positive integer-like values.", call. = FALSE)
  }

  mse_scales <- sort(unique(as.integer(mse_scales)))

  group_cols <- gpbiometrics_complexity_group_cols(dat, group_cols)
  groups <- gpbiometrics_complexity_split_indices(dat, group_cols)

  rows <- lapply(names(groups), function(unit_id) {
    idx <- groups[[unit_id]]
    base <- gpbiometrics_complexity_unit_values(dat, idx, group_cols, unit_id)

    x <- dat[[ibi_col]][idx]
    x <- x[is.finite(x) & x > 0]

    mse_names <- paste0("mse_scale_", mse_scales)

    if (length(x) < min_intervals) {
      mse_empty <- as.data.frame(as.list(rep(NA_real_, length(mse_names))))
      names(mse_empty) <- mse_names

      return(data.frame(
        base,
        unit_id = unit_id,
        n_intervals = length(x),
        mean_ibi = NA_real_,
        sdnn = NA_real_,
        rmssd = NA_real_,
        sd1 = NA_real_,
        sd2 = NA_real_,
        sd1_sd2_ratio = NA_real_,
        sample_entropy = NA_real_,
        approximate_entropy = NA_real_,
        dfa_alpha = NA_real_,
        mse_mean = NA_real_,
        mse_empty,
        status = "insufficient_intervals",
        stringsAsFactors = FALSE,
        check.names = FALSE
      ))
    }

    diff_x <- diff(x)
    sdnn <- stats::sd(x)
    diff_var <- stats::var(diff_x, na.rm = TRUE)

    rmssd <- sqrt(mean(diff_x^2, na.rm = TRUE))
    sd1 <- sqrt(diff_var / 2)
    sd2 <- sqrt(max((2 * sdnn^2) - (0.5 * diff_var), 0))
    ratio <- if (is.finite(sd2) && sd2 > 0) sd1 / sd2 else NA_real_

    sampen_r <- sampen_r_multiplier * stats::sd(x)

    sampen <- gpbiometrics_sample_entropy(
      x,
      m = sampen_m,
      r = sampen_r
    )

    apen <- gpbiometrics_approximate_entropy(
      x,
      m = sampen_m,
      r = sampen_r
    )

    dfa <- gpbiometrics_dfa_alpha(x)

    mse <- gpbiometrics_multiscale_entropy(
      x,
      scales = mse_scales,
      m = sampen_m,
      r_multiplier = sampen_r_multiplier
    )

    mse_df <- as.data.frame(as.list(mse))
    names(mse_df) <- mse_names

    data.frame(
      base,
      unit_id = unit_id,
      n_intervals = length(x),
      mean_ibi = mean(x),
      sdnn = sdnn,
      rmssd = rmssd,
      sd1 = sd1,
      sd2 = sd2,
      sd1_sd2_ratio = ratio,
      sample_entropy = sampen,
      approximate_entropy = apen,
      dfa_alpha = dfa,
      mse_mean = if (any(is.finite(mse))) mean(mse, na.rm = TRUE) else NA_real_,
      mse_df,
      status = "nonlinear_hrv_extracted",
      stringsAsFactors = FALSE,
      check.names = FALSE
    )
  })

  features <- do.call(rbind, rows)
  rownames(features) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    feature_rows = nrow(features),
    successful_groups = sum(features$status == "nonlinear_hrv_extracted"),
    problem_groups = sum(features$status != "nonlinear_hrv_extracted"),
    ibi_col = ibi_col,
    status = if (all(features$status == "nonlinear_hrv_extracted")) {
      "nonlinear_hrv_extracted"
    } else if (any(features$status == "nonlinear_hrv_extracted")) {
      "nonlinear_hrv_partial"
    } else {
      "nonlinear_hrv_failed"
    },
    interpretation = paste(
      "Nonlinear HRV features describe interval variability, irregularity, and scale-dependent structure.",
      "They do not infer emotion, cognitive load, psychiatric status, health status, or diagnosis by themselves."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      features = features,
      settings = list(
        ibi_col = ibi_col,
        group_cols = group_cols,
        min_intervals = min_intervals,
        sampen_m = sampen_m,
        sampen_r_multiplier = sampen_r_multiplier,
        mse_scales = mse_scales
      )
    ),
    class = c("gazepoint_hrv_nonlinear", "list")
  )
}

#' Extract EDA complexity features
#'
#' Computes dependency-light EDA complexity descriptors, including sample entropy
#' and detrended fluctuation analysis alpha.
#'
#' @param dat A data frame containing EDA data.
#' @param eda_col EDA/conductance column.
#' @param group_cols Optional grouping columns.
#' @param min_samples Minimum finite samples per group.
#' @param sampen_m Embedding dimension for sample entropy.
#' @param sampen_r_multiplier Tolerance multiplier applied to within-group SD.
#'
#' @return A list with `overview`, `features`, and `settings`.
#' @export
extract_gazepoint_eda_complexity <- function(dat,
                                             eda_col = "GSR_US",
                                             group_cols = NULL,
                                             min_samples = 32,
                                             sampen_m = 2,
                                             sampen_r_multiplier = 0.2) {
  if (!is.data.frame(dat)) stop("`dat` must be a data frame.", call. = FALSE)
  if (!eda_col %in% names(dat)) stop("Column `", eda_col, "` was not found in `dat`.", call. = FALSE)
  if (!is.numeric(dat[[eda_col]])) stop("`eda_col` must identify a numeric column.", call. = FALSE)

  group_cols <- gpbiometrics_complexity_group_cols(dat, group_cols)
  groups <- gpbiometrics_complexity_split_indices(dat, group_cols)

  rows <- lapply(names(groups), function(unit_id) {
    idx <- groups[[unit_id]]
    base <- gpbiometrics_complexity_unit_values(dat, idx, group_cols, unit_id)
    x <- dat[[eda_col]][idx]
    x <- x[is.finite(x)]

    if (length(x) < min_samples || stats::sd(x) == 0) {
      return(data.frame(
        base,
        unit_id = unit_id,
        n_samples = length(x),
        signal_sd = if (length(x) > 1) stats::sd(x) else NA_real_,
        sample_entropy = NA_real_,
        dfa_alpha = NA_real_,
        status = "insufficient_or_constant_signal",
        stringsAsFactors = FALSE,
        check.names = FALSE
      ))
    }

    se <- gpbiometrics_sample_entropy(x, m = sampen_m, r = sampen_r_multiplier * stats::sd(x))
    dfa <- gpbiometrics_dfa_alpha(x)

    data.frame(
      base,
      unit_id = unit_id,
      n_samples = length(x),
      signal_sd = stats::sd(x),
      sample_entropy = se,
      dfa_alpha = dfa,
      status = "eda_complexity_extracted",
      stringsAsFactors = FALSE,
      check.names = FALSE
    )
  })

  features <- do.call(rbind, rows)
  rownames(features) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    feature_rows = nrow(features),
    successful_groups = sum(features$status == "eda_complexity_extracted"),
    problem_groups = sum(features$status != "eda_complexity_extracted"),
    eda_col = eda_col,
    status = if (all(features$status == "eda_complexity_extracted")) {
      "eda_complexity_extracted"
    } else if (any(features$status == "eda_complexity_extracted")) {
      "eda_complexity_partial"
    } else {
      "eda_complexity_failed"
    },
    interpretation = paste(
      "EDA complexity features describe nonlinear or scale-dependent signal structure.",
      "They are not direct emotion, stress, cognition, trust, preference, or diagnosis labels."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(overview = overview, features = features, settings = list(
      eda_col = eda_col,
      group_cols = group_cols,
      min_samples = min_samples,
      sampen_m = sampen_m,
      sampen_r_multiplier = sampen_r_multiplier
    )),
    class = c("gazepoint_eda_complexity", "list")
  )
}

gpbiometrics_sample_entropy <- function(x, m = 2, r) {
  x <- x[is.finite(x)]

  if (length(x) <= m + 2 || !is.finite(r) || r <= 0) return(NA_real_)

  count_matches <- function(mm) {
    n <- length(x) - mm + 1
    if (n <= 1) return(NA_real_)

    emb <- matrix(NA_real_, nrow = n, ncol = mm)
    for (j in seq_len(mm)) emb[, j] <- x[j:(j + n - 1)]

    count <- 0
    total <- 0

    for (i in seq_len(n - 1)) {
      for (k in (i + 1):n) {
        total <- total + 1
        if (max(abs(emb[i, ] - emb[k, ])) <= r) count <- count + 1
      }
    }

    if (total == 0) return(NA_real_)
    count / total
  }

  a <- count_matches(m + 1)
  b <- count_matches(m)

  if (!is.finite(a) || !is.finite(b) || a <= 0 || b <= 0) return(NA_real_)
  -log(a / b)
}

gpbiometrics_dfa_alpha <- function(x) {
  x <- x[is.finite(x)]

  n <- length(x)
  if (n < 32) return(NA_real_)

  y <- cumsum(x - mean(x))
  scales <- unique(floor(exp(seq(log(4), log(max(8, floor(n / 4))), length.out = 8))))
  scales <- scales[scales >= 4 & scales < n / 2]

  if (length(scales) < 3) return(NA_real_)

  fluct <- vapply(scales, function(s) {
    starts <- seq(1, n - s + 1, by = s)
    rms <- vapply(starts, function(st) {
      seg <- y[st:(st + s - 1)]
      fit <- stats::lm(seg ~ seq_along(seg))
      sqrt(mean(stats::resid(fit)^2))
    }, numeric(1))

    mean(rms, na.rm = TRUE)
  }, numeric(1))

  keep <- is.finite(fluct) & fluct > 0 & is.finite(scales)
  if (sum(keep) < 3) return(NA_real_)

  unname(stats::coef(stats::lm(log(fluct[keep]) ~ log(scales[keep])))[2])
}

gpbiometrics_complexity_group_cols <- function(dat, group_cols = NULL) {
  if (is.null(group_cols)) return(character())
  missing_cols <- setdiff(group_cols, names(dat))
  if (length(missing_cols) > 0) {
    stop("Missing `group_cols`: ", paste(missing_cols, collapse = ", "), call. = FALSE)
  }
  group_cols
}

gpbiometrics_complexity_split_indices <- function(dat, group_cols) {
  if (length(group_cols) == 0) return(list(all_rows = seq_len(nrow(dat))))
  gf <- dat[group_cols]
  gf[] <- lapply(gf, function(x) {
    x <- as.character(x)
    x[is.na(x)] <- "<NA>"
    x
  })
  split(seq_len(nrow(dat)), do.call(paste, c(gf, sep = " | ")))
}

gpbiometrics_complexity_unit_values <- function(dat, idx, group_cols, unit_id) {
  if (length(group_cols) == 0) return(data.frame(unit_label = unit_id, stringsAsFactors = FALSE))
  values <- lapply(group_cols, function(nm) as.character(dat[[nm]][idx[1]]))
  names(values) <- group_cols
  as.data.frame(values, stringsAsFactors = FALSE, optional = TRUE)
}

gpbiometrics_approximate_entropy <- function(x, m = 2, r) {
  x <- x[is.finite(x)]

  if (length(x) <= m + 2 || !is.finite(r) || r <= 0) {
    return(NA_real_)
  }

  phi <- function(mm) {
    n <- length(x) - mm + 1

    if (n <= 1) {
      return(NA_real_)
    }

    emb <- matrix(NA_real_, nrow = n, ncol = mm)

    for (j in seq_len(mm)) {
      emb[, j] <- x[j:(j + n - 1)]
    }

    c_i <- numeric(n)

    for (i in seq_len(n)) {
      dist <- apply(emb, 1, function(row) max(abs(row - emb[i, ])))
      c_i[i] <- mean(dist <= r)
    }

    mean(log(pmax(c_i, .Machine$double.eps)))
  }

  phi_m <- phi(m)
  phi_m1 <- phi(m + 1)

  if (!is.finite(phi_m) || !is.finite(phi_m1)) {
    return(NA_real_)
  }

  phi_m - phi_m1
}

gpbiometrics_multiscale_entropy <- function(x,
                                            scales = 1:5,
                                            m = 2,
                                            r_multiplier = 0.2) {
  x <- x[is.finite(x)]

  vapply(scales, function(scale) {
    coarse <- gpbiometrics_coarse_grain(x, scale)

    if (length(coarse) <= m + 2 || stats::sd(coarse) == 0) {
      return(NA_real_)
    }

    gpbiometrics_sample_entropy(
      coarse,
      m = m,
      r = r_multiplier * stats::sd(coarse)
    )
  }, numeric(1))
}

gpbiometrics_coarse_grain <- function(x, scale) {
  scale <- as.integer(scale)

  if (scale <= 1) {
    return(x)
  }

  n_blocks <- floor(length(x) / scale)

  if (n_blocks < 1) {
    return(numeric())
  }

  vapply(seq_len(n_blocks), function(i) {
    start <- (i - 1) * scale + 1
    end <- i * scale
    mean(x[start:end], na.rm = TRUE)
  }, numeric(1))
}
