#' Extract HRV recurrence quantification analysis features
#'
#' Computes dependency-light recurrence quantification analysis (RQA) features
#' from IBI/RR intervals. This is intended as a compact nonlinear HRV summary
#' and not as a clinical diagnostic tool.
#'
#' @param dat A data frame.
#' @param ibi_col Numeric IBI/RR interval column.
#' @param group_cols Optional grouping columns.
#' @param embedding_dimension Embedding dimension for phase-space reconstruction.
#' @param delay Delay used in embedding.
#' @param radius Radius for recurrence threshold. If `NULL`, uses
#'   `radius_multiplier * SD`.
#' @param radius_multiplier Multiplier used when `radius = NULL`.
#' @param min_line_length Minimum diagonal/vertical line length.
#'
#' @return A list with `overview`, `features`, and `settings`.
#' @export
extract_gazepoint_hrv_rqa <- function(dat,
                                      ibi_col = "IBI",
                                      group_cols = NULL,
                                      embedding_dimension = 2,
                                      delay = 1,
                                      radius = NULL,
                                      radius_multiplier = 0.2,
                                      min_line_length = 2) {
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

  groups <- gpbiometrics_hrv_rqa_split(dat, group_cols)

  rows <- lapply(names(groups), function(group_id) {
    idx <- groups[[group_id]]
    base <- gpbiometrics_hrv_rqa_values(dat, idx, group_cols, group_id)

    x <- dat[[ibi_col]][idx]
    x <- x[is.finite(x) & x > 0]

    if (length(x) < (embedding_dimension + 2) * delay + 5) {
      return(data.frame(
        base,
        group_id = group_id,
        n_intervals = length(x),
        recurrence_rate = NA_real_,
        determinism = NA_real_,
        laminarity = NA_real_,
        trapping_time = NA_real_,
        diagonal_entropy = NA_real_,
        mean_diagonal_length = NA_real_,
        longest_diagonal = NA_real_,
        status = "insufficient_intervals",
        stringsAsFactors = FALSE,
        check.names = FALSE
      ))
    }

    embedded <- gpbiometrics_hrv_rqa_embed(
      x,
      dimension = embedding_dimension,
      delay = delay
    )

    rad <- if (!is.null(radius)) {
      radius
    } else {
      radius_multiplier * stats::sd(as.numeric(embedded), na.rm = TRUE)
    }

    if (!is.finite(rad) || rad <= 0) {
      rad <- .Machine$double.eps
    }

    rec <- gpbiometrics_hrv_rqa_matrix(embedded, radius = rad)

    diag_lengths <- gpbiometrics_hrv_rqa_diagonal_lengths(rec)
    vert_lengths <- gpbiometrics_hrv_rqa_vertical_lengths(rec)

    recurrence_points <- sum(rec)
    total_points <- length(rec)

    diag_recurrent <- sum(diag_lengths[diag_lengths >= min_line_length], na.rm = TRUE)
    vert_recurrent <- sum(vert_lengths[vert_lengths >= min_line_length], na.rm = TRUE)

    recurrence_rate <- recurrence_points / total_points
    determinism <- if (recurrence_points > 0) diag_recurrent / recurrence_points else NA_real_
    laminarity <- if (recurrence_points > 0) vert_recurrent / recurrence_points else NA_real_
    trapping_time <- if (any(vert_lengths >= min_line_length)) {
      mean(vert_lengths[vert_lengths >= min_line_length])
    } else {
      NA_real_
    }

    diagonal_entropy <- gpbiometrics_hrv_rqa_entropy(
      diag_lengths[diag_lengths >= min_line_length]
    )

    mean_diagonal_length <- if (any(diag_lengths >= min_line_length)) {
      mean(diag_lengths[diag_lengths >= min_line_length])
    } else {
      NA_real_
    }

    longest_diagonal <- if (length(diag_lengths) > 0) {
      max(diag_lengths)
    } else {
      NA_real_
    }

    data.frame(
      base,
      group_id = group_id,
      n_intervals = length(x),
      recurrence_rate = recurrence_rate,
      determinism = determinism,
      laminarity = laminarity,
      trapping_time = trapping_time,
      diagonal_entropy = diagonal_entropy,
      mean_diagonal_length = mean_diagonal_length,
      longest_diagonal = longest_diagonal,
      status = "hrv_rqa_extracted",
      stringsAsFactors = FALSE,
      check.names = FALSE
    )
  })

  features <- do.call(rbind, rows)
  rownames(features) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    feature_rows = nrow(features),
    successful_groups = sum(features$status == "hrv_rqa_extracted"),
    problem_groups = sum(features$status != "hrv_rqa_extracted"),
    status = if (all(features$status == "hrv_rqa_extracted")) {
      "hrv_rqa_extracted"
    } else if (any(features$status == "hrv_rqa_extracted")) {
      "hrv_rqa_partial"
    } else {
      "hrv_rqa_failed"
    },
    interpretation = paste(
      "RQA features describe recurrence structure in IBI/RR dynamics.",
      "They are nonlinear descriptors and do not infer health status or diagnosis by themselves."
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
        embedding_dimension = embedding_dimension,
        delay = delay,
        radius = radius,
        radius_multiplier = radius_multiplier,
        min_line_length = min_line_length
      )
    ),
    class = c("gazepoint_hrv_rqa", "list")
  )
}

#' Extract geometric HRV features
#'
#' Computes dependency-light geometric HRV descriptors, including the HRV
#' triangular index and an approximate TINN-style triangular interpolation width.
#'
#' @param dat A data frame.
#' @param ibi_col Numeric IBI/RR interval column.
#' @param group_cols Optional grouping columns.
#' @param bin_width Histogram bin width in the same units as `ibi_col`.
#'
#' @return A list with `overview`, `features`, and `settings`.
#' @export
extract_gazepoint_hrv_geometric <- function(dat,
                                            ibi_col = "IBI",
                                            group_cols = NULL,
                                            bin_width = NULL) {
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

  groups <- gpbiometrics_hrv_rqa_split(dat, group_cols)

  rows <- lapply(names(groups), function(group_id) {
    idx <- groups[[group_id]]
    base <- gpbiometrics_hrv_rqa_values(dat, idx, group_cols, group_id)

    x <- dat[[ibi_col]][idx]
    x <- x[is.finite(x) & x > 0]

    if (length(x) < 5) {
      return(data.frame(
        base,
        group_id = group_id,
        n_intervals = length(x),
        bin_width = NA_real_,
        hrv_triangular_index = NA_real_,
        tinn = NA_real_,
        histogram_peak_count = NA_real_,
        status = "insufficient_intervals",
        stringsAsFactors = FALSE,
        check.names = FALSE
      ))
    }

    bw <- bin_width

    if (is.null(bw)) {
      bw <- if (stats::median(x, na.rm = TRUE) > 10) 7.8125 else 0.0078125
    }

    breaks <- seq(
      floor(min(x) / bw) * bw,
      ceiling(max(x) / bw) * bw + bw,
      by = bw
    )

    h <- graphics::hist(x, breaks = breaks, plot = FALSE)
    max_count <- max(h$counts)

    hti <- if (max_count > 0) length(x) / max_count else NA_real_

    nonzero <- which(h$counts > 0)

    tinn <- if (length(nonzero) >= 2) {
      h$breaks[max(nonzero) + 1] - h$breaks[min(nonzero)]
    } else {
      NA_real_
    }

    data.frame(
      base,
      group_id = group_id,
      n_intervals = length(x),
      bin_width = bw,
      hrv_triangular_index = hti,
      tinn = tinn,
      histogram_peak_count = max_count,
      status = "hrv_geometric_extracted",
      stringsAsFactors = FALSE,
      check.names = FALSE
    )
  })

  features <- do.call(rbind, rows)
  rownames(features) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    feature_rows = nrow(features),
    successful_groups = sum(features$status == "hrv_geometric_extracted"),
    problem_groups = sum(features$status != "hrv_geometric_extracted"),
    status = if (all(features$status == "hrv_geometric_extracted")) {
      "hrv_geometric_extracted"
    } else if (any(features$status == "hrv_geometric_extracted")) {
      "hrv_geometric_partial"
    } else {
      "hrv_geometric_failed"
    },
    interpretation = paste(
      "Geometric HRV features summarise the distributional shape of IBI/RR intervals.",
      "They are not diagnostic labels by themselves."
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
        bin_width = bin_width
      )
    ),
    class = c("gazepoint_hrv_geometric", "list")
  )
}

gpbiometrics_hrv_rqa_split <- function(dat, group_cols) {
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

gpbiometrics_hrv_rqa_values <- function(dat, idx, group_cols, group_id) {
  if (length(group_cols) == 0) {
    return(data.frame(unit_label = group_id, stringsAsFactors = FALSE))
  }

  values <- lapply(group_cols, function(nm) as.character(dat[[nm]][idx[1]]))
  names(values) <- group_cols
  as.data.frame(values, stringsAsFactors = FALSE, optional = TRUE)
}

gpbiometrics_hrv_rqa_embed <- function(x, dimension = 2, delay = 1) {
  n <- length(x) - (dimension - 1) * delay

  if (n <= 0) {
    return(matrix(numeric(), nrow = 0, ncol = dimension))
  }

  out <- matrix(NA_real_, nrow = n, ncol = dimension)

  for (j in seq_len(dimension)) {
    out[, j] <- x[(1:n) + (j - 1) * delay]
  }

  out
}

gpbiometrics_hrv_rqa_matrix <- function(embedded, radius) {
  n <- nrow(embedded)
  rec <- matrix(FALSE, nrow = n, ncol = n)

  for (i in seq_len(n)) {
    d <- sqrt(rowSums((t(t(embedded) - embedded[i, ]))^2))
    rec[i, ] <- d <= radius
  }

  rec
}

gpbiometrics_hrv_rqa_diagonal_lengths <- function(rec) {
  n <- nrow(rec)
  lengths <- integer()

  for (offset in seq(-(n - 1), n - 1)) {
    diag_values <- gpbiometrics_hrv_rqa_get_offset_diagonal(rec, offset)

    if (length(diag_values) == 0) {
      next
    }

    lengths <- c(lengths, gpbiometrics_hrv_rqa_run_lengths(diag_values))
  }

  lengths
}

gpbiometrics_hrv_rqa_get_offset_diagonal <- function(rec, offset = 0) {
  n <- nrow(rec)

  if (offset >= 0) {
    i <- seq_len(n - offset)
    j <- i + offset
  } else {
    j <- seq_len(n + offset)
    i <- j - offset
  }

  if (length(i) == 0 || length(j) == 0) {
    return(logical())
  }

  rec[cbind(i, j)]
}

gpbiometrics_hrv_rqa_vertical_lengths <- function(rec) {
  lengths <- integer()

  for (j in seq_len(ncol(rec))) {
    lengths <- c(lengths, gpbiometrics_hrv_rqa_run_lengths(rec[, j]))
  }

  lengths
}

gpbiometrics_hrv_rqa_run_lengths <- function(x) {
  r <- rle(as.logical(x))
  r$lengths[r$values]
}

gpbiometrics_hrv_rqa_entropy <- function(lengths) {
  if (length(lengths) == 0) {
    return(NA_real_)
  }

  tab <- table(lengths)
  p <- as.numeric(tab) / sum(tab)

  -sum(p * log(p))
}
