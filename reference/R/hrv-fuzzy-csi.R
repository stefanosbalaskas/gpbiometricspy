#' Extract FuzzyEn and Lorenz-plot CSI HRV features
#'
#' Computes fuzzy entropy and Lorenz/Poincare-derived cardiac sympathetic index
#' style descriptors from IBI/RR intervals.
#'
#' These outputs are nonlinear/geometric HRV descriptors. They do not infer
#' seizure status, diagnosis, health status, emotion, stress, or cognition.
#'
#' @param dat A data frame.
#' @param ibi_col Numeric IBI/RR interval column.
#' @param group_cols Optional grouping columns.
#' @param m Embedding dimension.
#' @param r_multiplier Tolerance multiplier applied to within-group SD.
#' @param fuzzy_power Fuzzy exponential power.
#' @param min_intervals Minimum intervals per group.
#'
#' @return A list with `overview`, `features`, and `settings`.
#' @export
extract_gazepoint_hrv_fuzzy_csi <- function(dat,
                                            ibi_col = "IBI",
                                            group_cols = NULL,
                                            m = 2,
                                            r_multiplier = 0.2,
                                            fuzzy_power = 2,
                                            min_intervals = 10) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  if (!ibi_col %in% names(dat)) {
    stop("Column `", ibi_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!is.numeric(dat[[ibi_col]])) {
    stop("`ibi_col` must identify a numeric column.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  missing_groups <- setdiff(group_cols, names(dat))
  if (length(missing_groups) > 0) {
    stop("Missing `group_cols`: ", paste(missing_groups, collapse = ", "), call. = FALSE)
  }

  groups <- gpbiometrics_fuzzy_split(dat, group_cols)

  rows <- lapply(names(groups), function(group_id) {
    idx <- groups[[group_id]]
    base <- gpbiometrics_fuzzy_group_values(dat, idx, group_cols, group_id)

    x <- dat[[ibi_col]][idx]
    x <- x[is.finite(x) & x > 0]

    if (length(x) < min_intervals || stats::sd(x) == 0) {
      return(data.frame(
        base,
        group_id = group_id,
        n_intervals = length(x),
        fuzzy_entropy = NA_real_,
        sd1 = NA_real_,
        sd2 = NA_real_,
        csi = NA_real_,
        cvi = NA_real_,
        modified_csi = NA_real_,
        status = "insufficient_intervals",
        stringsAsFactors = FALSE,
        check.names = FALSE
      ))
    }

    r <- r_multiplier * stats::sd(x)
    fuzzy_entropy <- gpbiometrics_fuzzy_entropy(
      x = x,
      m = m,
      r = r,
      fuzzy_power = fuzzy_power
    )

    dx <- diff(x)
    sdnn <- stats::sd(x)
    diff_var <- stats::var(dx, na.rm = TRUE)

    sd1 <- sqrt(diff_var / 2)
    sd2 <- sqrt(max((2 * sdnn^2) - (0.5 * diff_var), 0))

    csi <- if (is.finite(sd1) && sd1 > 0) {
      sd2 / sd1
    } else {
      NA_real_
    }

    cvi <- if (is.finite(sd1) && is.finite(sd2) && sd1 > 0 && sd2 > 0) {
      log10(sd1 * sd2)
    } else {
      NA_real_
    }

    modified_csi <- if (is.finite(sd1) && sd1 > 0 && is.finite(sd2)) {
      sd2^2 / sd1
    } else {
      NA_real_
    }

    data.frame(
      base,
      group_id = group_id,
      n_intervals = length(x),
      fuzzy_entropy = fuzzy_entropy,
      sd1 = sd1,
      sd2 = sd2,
      csi = csi,
      cvi = cvi,
      modified_csi = modified_csi,
      status = "fuzzy_csi_extracted",
      stringsAsFactors = FALSE,
      check.names = FALSE
    )
  })

  features <- do.call(rbind, rows)
  rownames(features) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    feature_rows = nrow(features),
    successful_groups = sum(features$status == "fuzzy_csi_extracted"),
    problem_groups = sum(features$status != "fuzzy_csi_extracted"),
    status = if (all(features$status == "fuzzy_csi_extracted")) {
      "fuzzy_csi_extracted"
    } else if (any(features$status == "fuzzy_csi_extracted")) {
      "fuzzy_csi_partial"
    } else {
      "fuzzy_csi_failed"
    },
    interpretation = paste(
      "FuzzyEn and CSI are nonlinear/geometric HRV descriptors.",
      "They are not diagnostic labels and do not infer clinical or psychological state by themselves."
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
        m = m,
        r_multiplier = r_multiplier,
        fuzzy_power = fuzzy_power,
        min_intervals = min_intervals
      )
    ),
    class = c("gazepoint_hrv_fuzzy_csi", "list")
  )
}

gpbiometrics_fuzzy_split <- function(dat, group_cols) {
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

gpbiometrics_fuzzy_group_values <- function(dat, idx, group_cols, group_id) {
  if (length(group_cols) == 0) {
    return(data.frame(unit_label = group_id, stringsAsFactors = FALSE))
  }

  values <- lapply(group_cols, function(nm) as.character(dat[[nm]][idx[1]]))
  names(values) <- group_cols
  as.data.frame(values, stringsAsFactors = FALSE, optional = TRUE)
}

gpbiometrics_fuzzy_entropy <- function(x,
                                       m = 2,
                                       r,
                                       fuzzy_power = 2) {
  x <- x[is.finite(x)]

  if (length(x) <= m + 2 || !is.finite(r) || r <= 0) {
    return(NA_real_)
  }

  phi_m <- gpbiometrics_fuzzy_phi(x, m = m, r = r, fuzzy_power = fuzzy_power)
  phi_m1 <- gpbiometrics_fuzzy_phi(x, m = m + 1, r = r, fuzzy_power = fuzzy_power)

  if (!is.finite(phi_m) || !is.finite(phi_m1) || phi_m <= 0 || phi_m1 <= 0) {
    return(NA_real_)
  }

  log(phi_m) - log(phi_m1)
}

gpbiometrics_fuzzy_phi <- function(x,
                                   m,
                                   r,
                                   fuzzy_power = 2) {
  n <- length(x) - m + 1

  if (n <= 1) {
    return(NA_real_)
  }

  emb <- matrix(NA_real_, nrow = n, ncol = m)

  for (j in seq_len(m)) {
    emb[, j] <- x[j:(j + n - 1)]
  }

  emb <- emb - rowMeans(emb)

  values <- numeric()

  for (i in seq_len(n - 1)) {
    for (j in (i + 1):n) {
      d <- max(abs(emb[i, ] - emb[j, ]))
      values <- c(values, exp(-((d^fuzzy_power) / r)))
    }
  }

  if (length(values) == 0) {
    return(NA_real_)
  }

  mean(values, na.rm = TRUE)
}
