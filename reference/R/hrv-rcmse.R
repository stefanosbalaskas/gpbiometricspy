#' Extract refined composite multiscale entropy from HRV intervals
#'
#' Computes refined composite multiscale entropy (RCMSE) from IBI/RR intervals.
#' RCMSE pools template-match counts across all coarse-grained offsets at each
#' scale, making it more stable than ordinary MSE for shorter physiological
#' time series.
#'
#' @param dat A data frame containing IBI/RR intervals.
#' @param ibi_col Numeric IBI/RR interval column.
#' @param group_cols Optional grouping columns.
#' @param scales Positive integer scales.
#' @param m Embedding dimension.
#' @param r_multiplier Tolerance multiplier applied to SD.
#' @param min_intervals Minimum intervals per group.
#'
#' @return A list with `overview`, `rcmse_by_scale`, `summary`, and `settings`.
#' @export
extract_gazepoint_hrv_rcmse <- function(dat,
                                        ibi_col = "IBI",
                                        group_cols = NULL,
                                        scales = 1:10,
                                        m = 2,
                                        r_multiplier = 0.2,
                                        min_intervals = 20) {
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

  scales <- sort(unique(as.integer(scales)))

  if (length(scales) == 0 || any(scales < 1)) {
    stop("`scales` must contain positive integer-like values.", call. = FALSE)
  }

  groups <- gpbiometrics_rcmse_split(dat, group_cols)

  scale_rows <- list()
  summary_rows <- list()
  row_id <- 1L

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]
    x <- dat[[ibi_col]][idx]
    x <- x[is.finite(x) & x > 0]

    if (length(x) < min_intervals || stats::sd(x) == 0) {
      for (scale in scales) {
        scale_rows[[row_id]] <- data.frame(
          group_id = group_id,
          scale = scale,
          rcmse = NA_real_,
          match_count_m = NA_real_,
          match_count_m1 = NA_real_,
          status = "insufficient_intervals",
          stringsAsFactors = FALSE
        )
        row_id <- row_id + 1L
      }

      summary_rows[[group_id]] <- data.frame(
        group_id = group_id,
        n_intervals = length(x),
        mean_rcmse = NA_real_,
        finite_scales = 0L,
        status = "insufficient_intervals",
        stringsAsFactors = FALSE
      )
      next
    }

    r <- r_multiplier * stats::sd(x)

    group_rcmse <- numeric(length(scales))

    for (i in seq_along(scales)) {
      scale <- scales[i]
      value <- gpbiometrics_rcmse_one_scale(
        x = x,
        scale = scale,
        m = m,
        r = r
      )

      group_rcmse[i] <- value$rcmse

      scale_rows[[row_id]] <- data.frame(
        group_id = group_id,
        scale = scale,
        rcmse = value$rcmse,
        match_count_m = value$count_m,
        match_count_m1 = value$count_m1,
        status = if (is.finite(value$rcmse)) {
          "rcmse_extracted"
        } else {
          "rcmse_not_estimated"
        },
        stringsAsFactors = FALSE
      )

      row_id <- row_id + 1L
    }

    summary_rows[[group_id]] <- data.frame(
      group_id = group_id,
      n_intervals = length(x),
      mean_rcmse = if (any(is.finite(group_rcmse))) {
        mean(group_rcmse, na.rm = TRUE)
      } else {
        NA_real_
      },
      finite_scales = sum(is.finite(group_rcmse)),
      status = if (any(is.finite(group_rcmse))) {
        "rcmse_extracted"
      } else {
        "rcmse_not_estimated"
      },
      stringsAsFactors = FALSE
    )
  }

  rcmse_by_scale <- do.call(rbind, scale_rows)
  rownames(rcmse_by_scale) <- NULL

  summary <- do.call(rbind, summary_rows)
  rownames(summary) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    scale_rows = nrow(rcmse_by_scale),
    successful_groups = sum(summary$status == "rcmse_extracted"),
    problem_groups = sum(summary$status != "rcmse_extracted"),
    status = if (all(summary$status == "rcmse_extracted")) {
      "rcmse_extraction_complete"
    } else if (any(summary$status == "rcmse_extracted")) {
      "rcmse_extraction_partial"
    } else {
      "rcmse_extraction_failed"
    },
    interpretation = paste(
      "RCMSE describes multiscale irregularity in IBI/RR intervals.",
      "It is not a direct label for emotion, stress, cognition, health status, or diagnosis."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      rcmse_by_scale = rcmse_by_scale,
      summary = summary,
      settings = list(
        ibi_col = ibi_col,
        group_cols = group_cols,
        scales = scales,
        m = m,
        r_multiplier = r_multiplier,
        min_intervals = min_intervals
      )
    ),
    class = c("gazepoint_hrv_rcmse", "list")
  )
}

gpbiometrics_rcmse_split <- function(dat, group_cols) {
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

gpbiometrics_rcmse_one_scale <- function(x, scale, m, r) {
  count_m <- 0
  count_m1 <- 0

  for (offset in seq_len(scale)) {
    coarse <- gpbiometrics_rcmse_coarse_grain_offset(x, scale, offset)

    if (length(coarse) > m + 2) {
      count_m <- count_m + gpbiometrics_rcmse_match_count(coarse, m, r)
      count_m1 <- count_m1 + gpbiometrics_rcmse_match_count(coarse, m + 1, r)
    }
  }

  rcmse <- if (count_m > 0 && count_m1 > 0) {
    -log(count_m1 / count_m)
  } else {
    NA_real_
  }

  list(
    rcmse = rcmse,
    count_m = count_m,
    count_m1 = count_m1
  )
}

gpbiometrics_rcmse_coarse_grain_offset <- function(x, scale, offset) {
  start <- offset
  values <- numeric()

  while (start <= length(x)) {
    stop_idx <- min(start + scale - 1, length(x))

    if ((stop_idx - start + 1) == scale) {
      values <- c(values, mean(x[start:stop_idx], na.rm = TRUE))
    }

    start <- start + scale
  }

  values
}

gpbiometrics_rcmse_match_count <- function(x, m, r) {
  x <- x[is.finite(x)]

  n <- length(x) - m + 1

  if (n <= 1 || !is.finite(r) || r <= 0) {
    return(0)
  }

  emb <- matrix(NA_real_, nrow = n, ncol = m)

  for (j in seq_len(m)) {
    emb[, j] <- x[j:(j + n - 1)]
  }

  count <- 0

  for (i in seq_len(n - 1)) {
    for (j in (i + 1):n) {
      if (max(abs(emb[i, ] - emb[j, ])) <= r) {
        count <- count + 1
      }
    }
  }

  count
}
