#' Extract heart-rate fragmentation features
#'
#' Computes dependency-light heart-rate fragmentation descriptors from IBI/RR
#' intervals. Metrics include percentage of inflection points (PIP), inverse
#' average segment length (IALS), percentage of short segments (PSS), percentage
#' of alternation segments (PAS), and long/short segment summaries.
#'
#' These are fragmentation descriptors of interbeat interval dynamics. They
#' should not be interpreted as clinical diagnoses or direct autonomic-state
#' labels by themselves.
#'
#' @param dat A data frame containing IBI/RR intervals.
#' @param ibi_col Numeric IBI/RR interval column.
#' @param group_cols Optional grouping columns.
#' @param zero_tolerance Absolute change below which interval differences are
#'   treated as zero.
#' @param short_segment_length Maximum segment length counted as short.
#'
#' @return A list with `overview`, `features`, and `settings`.
#' @export
extract_gazepoint_hrv_fragmentation <- function(dat,
                                                ibi_col = "IBI",
                                                group_cols = NULL,
                                                zero_tolerance = 0,
                                                short_segment_length = 3) {
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

  groups <- gpbiometrics_hrf_split(dat, group_cols)

  rows <- lapply(names(groups), function(group_id) {
    idx <- groups[[group_id]]
    base <- gpbiometrics_hrf_group_values(dat, idx, group_cols, group_id)

    x <- dat[[ibi_col]][idx]
    x <- x[is.finite(x) & x > 0]

    if (length(x) < 5) {
      return(data.frame(
        base,
        group_id = group_id,
        n_intervals = length(x),
        n_differences = max(length(x) - 1, 0),
        percentage_inflection_points = NA_real_,
        pip = NA_real_,
        inverse_average_segment_length = NA_real_,
        ials = NA_real_,
        percentage_short_segments = NA_real_,
        pss = NA_real_,
        percentage_alternation_segments = NA_real_,
        pas = NA_real_,
        mean_segment_length = NA_real_,
        median_segment_length = NA_real_,
        longest_segment = NA_real_,
        status = "insufficient_intervals",
        stringsAsFactors = FALSE,
        check.names = FALSE
      ))
    }

    dx <- diff(x)
    sx <- sign(dx)
    sx[abs(dx) <= zero_tolerance] <- 0
    sx <- sx[sx != 0]

    if (length(sx) < 2) {
      return(data.frame(
        base,
        group_id = group_id,
        n_intervals = length(x),
        n_differences = length(dx),
        percentage_inflection_points = NA_real_,
        pip = NA_real_,
        inverse_average_segment_length = NA_real_,
        ials = NA_real_,
        percentage_short_segments = NA_real_,
        pss = NA_real_,
        percentage_alternation_segments = NA_real_,
        pas = NA_real_,
        mean_segment_length = NA_real_,
        median_segment_length = NA_real_,
        longest_segment = NA_real_,
        status = "insufficient_nonzero_differences",
        stringsAsFactors = FALSE,
        check.names = FALSE
      ))
    }

    inflections <- sum(sx[-1] * sx[-length(sx)] < 0)
    pip <- 100 * inflections / (length(sx) - 1)

    runs <- rle(sx)
    segment_lengths <- runs$lengths

    mean_segment_length <- mean(segment_lengths)
    median_segment_length <- stats::median(segment_lengths)
    longest_segment <- max(segment_lengths)

    ials <- if (is.finite(mean_segment_length) && mean_segment_length > 0) {
      1 / mean_segment_length
    } else {
      NA_real_
    }

    pss <- 100 * sum(segment_lengths <= short_segment_length) / sum(segment_lengths)
    pas <- 100 * sum(segment_lengths == 1) / sum(segment_lengths)

    data.frame(
      base,
      group_id = group_id,
      n_intervals = length(x),
      n_differences = length(dx),
      percentage_inflection_points = pip,
      pip = pip,
      inverse_average_segment_length = ials,
      ials = ials,
      percentage_short_segments = pss,
      pss = pss,
      percentage_alternation_segments = pas,
      pas = pas,
      mean_segment_length = mean_segment_length,
      median_segment_length = median_segment_length,
      longest_segment = longest_segment,
      status = "hrv_fragmentation_extracted",
      stringsAsFactors = FALSE,
      check.names = FALSE
    )
  })

  features <- do.call(rbind, rows)
  rownames(features) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    feature_rows = nrow(features),
    successful_groups = sum(features$status == "hrv_fragmentation_extracted"),
    problem_groups = sum(features$status != "hrv_fragmentation_extracted"),
    status = if (all(features$status == "hrv_fragmentation_extracted")) {
      "hrv_fragmentation_extracted"
    } else if (any(features$status == "hrv_fragmentation_extracted")) {
      "hrv_fragmentation_partial"
    } else {
      "hrv_fragmentation_failed"
    },
    interpretation = paste(
      "Heart-rate fragmentation features describe rapid sign changes and segment structure in IBI/RR dynamics.",
      "They are not diagnostic labels and do not directly infer vagal tone, cardiovascular disease, emotion, or cognition."
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
        zero_tolerance = zero_tolerance,
        short_segment_length = short_segment_length
      )
    ),
    class = c("gazepoint_hrv_fragmentation", "list")
  )
}

#' Extract heart-rate asymmetry features
#'
#' Computes dependency-light heart-rate asymmetry descriptors from IBI/RR
#' intervals, including acceleration/deceleration proportions, signed run
#' summaries, and Guzik-style squared-difference asymmetry.
#'
#' Positive IBI/RR differences are treated as decelerations because the heart
#' period lengthens. Negative IBI/RR differences are treated as accelerations.
#'
#' @param dat A data frame containing IBI/RR intervals.
#' @param ibi_col Numeric IBI/RR interval column.
#' @param group_cols Optional grouping columns.
#' @param zero_tolerance Absolute change below which interval differences are
#'   treated as zero.
#'
#' @return A list with `overview`, `features`, `run_table`, and `settings`.
#' @export
extract_gazepoint_hrv_asymmetry <- function(dat,
                                            ibi_col = "IBI",
                                            group_cols = NULL,
                                            zero_tolerance = 0) {
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

  groups <- gpbiometrics_hrf_split(dat, group_cols)

  feature_rows <- list()
  run_rows <- list()
  run_id <- 1L

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]
    base <- gpbiometrics_hrf_group_values(dat, idx, group_cols, group_id)

    x <- dat[[ibi_col]][idx]
    x <- x[is.finite(x) & x > 0]

    if (length(x) < 5) {
      feature_rows[[group_id]] <- data.frame(
        base,
        group_id = group_id,
        n_intervals = length(x),
        n_differences = max(length(x) - 1, 0),
        acceleration_count = NA_integer_,
        deceleration_count = NA_integer_,
        acceleration_proportion = NA_real_,
        deceleration_proportion = NA_real_,
        acceleration_run_count = NA_integer_,
        deceleration_run_count = NA_integer_,
        mean_acceleration_run_length = NA_real_,
        mean_deceleration_run_length = NA_real_,
        longest_acceleration_run = NA_real_,
        longest_deceleration_run = NA_real_,
        guzik_index = NA_real_,
        porta_index = NA_real_,
        asymmetry_balance = NA_real_,
        status = "insufficient_intervals",
        stringsAsFactors = FALSE,
        check.names = FALSE
      )
      next
    }

    dx <- diff(x)
    dx[abs(dx) <= zero_tolerance] <- 0

    direction <- ifelse(dx > 0, "deceleration",
                        ifelse(dx < 0, "acceleration", "no_change")
    )

    nonzero <- direction != "no_change"

    if (sum(nonzero) < 2) {
      feature_rows[[group_id]] <- data.frame(
        base,
        group_id = group_id,
        n_intervals = length(x),
        n_differences = length(dx),
        acceleration_count = sum(direction == "acceleration"),
        deceleration_count = sum(direction == "deceleration"),
        acceleration_proportion = NA_real_,
        deceleration_proportion = NA_real_,
        acceleration_run_count = NA_integer_,
        deceleration_run_count = NA_integer_,
        mean_acceleration_run_length = NA_real_,
        mean_deceleration_run_length = NA_real_,
        longest_acceleration_run = NA_real_,
        longest_deceleration_run = NA_real_,
        guzik_index = NA_real_,
        porta_index = NA_real_,
        asymmetry_balance = NA_real_,
        status = "insufficient_nonzero_differences",
        stringsAsFactors = FALSE,
        check.names = FALSE
      )
      next
    }

    d_nonzero <- direction[nonzero]
    dx_nonzero <- dx[nonzero]

    runs <- rle(d_nonzero)

    for (i in seq_along(runs$values)) {
      run_rows[[run_id]] <- data.frame(
        group_id = group_id,
        run_index = i,
        run_type = runs$values[i],
        run_length = runs$lengths[i],
        stringsAsFactors = FALSE
      )
      run_id <- run_id + 1L
    }

    acc_runs <- runs$lengths[runs$values == "acceleration"]
    dec_runs <- runs$lengths[runs$values == "deceleration"]

    acc_count <- sum(d_nonzero == "acceleration")
    dec_count <- sum(d_nonzero == "deceleration")
    total_nonzero <- length(d_nonzero)

    positive_energy <- sum(dx_nonzero[dx_nonzero > 0]^2)
    negative_energy <- sum(dx_nonzero[dx_nonzero < 0]^2)
    total_energy <- positive_energy + negative_energy

    guzik_index <- if (total_energy > 0) {
      100 * positive_energy / total_energy
    } else {
      NA_real_
    }

    porta_index <- 100 * dec_count / total_nonzero

    feature_rows[[group_id]] <- data.frame(
      base,
      group_id = group_id,
      n_intervals = length(x),
      n_differences = length(dx),
      acceleration_count = acc_count,
      deceleration_count = dec_count,
      acceleration_proportion = acc_count / total_nonzero,
      deceleration_proportion = dec_count / total_nonzero,
      acceleration_run_count = length(acc_runs),
      deceleration_run_count = length(dec_runs),
      mean_acceleration_run_length = if (length(acc_runs) > 0) mean(acc_runs) else NA_real_,
      mean_deceleration_run_length = if (length(dec_runs) > 0) mean(dec_runs) else NA_real_,
      longest_acceleration_run = if (length(acc_runs) > 0) max(acc_runs) else NA_real_,
      longest_deceleration_run = if (length(dec_runs) > 0) max(dec_runs) else NA_real_,
      guzik_index = guzik_index,
      porta_index = porta_index,
      asymmetry_balance = (dec_count - acc_count) / total_nonzero,
      status = "hrv_asymmetry_extracted",
      stringsAsFactors = FALSE,
      check.names = FALSE
    )
  }

  features <- do.call(rbind, feature_rows)
  rownames(features) <- NULL

  run_table <- if (length(run_rows) > 0) {
    do.call(rbind, run_rows)
  } else {
    data.frame()
  }

  overview <- data.frame(
    group_count = length(groups),
    feature_rows = nrow(features),
    run_rows = nrow(run_table),
    successful_groups = sum(features$status == "hrv_asymmetry_extracted"),
    problem_groups = sum(features$status != "hrv_asymmetry_extracted"),
    status = if (all(features$status == "hrv_asymmetry_extracted")) {
      "hrv_asymmetry_extracted"
    } else if (any(features$status == "hrv_asymmetry_extracted")) {
      "hrv_asymmetry_partial"
    } else {
      "hrv_asymmetry_failed"
    },
    interpretation = paste(
      "Heart-rate asymmetry features summarise unequal acceleration and deceleration dynamics.",
      "They do not directly infer health status, emotion, cognition, or diagnosis."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      features = features,
      run_table = run_table,
      settings = list(
        ibi_col = ibi_col,
        group_cols = group_cols,
        zero_tolerance = zero_tolerance
      )
    ),
    class = c("gazepoint_hrv_asymmetry", "list")
  )
}

gpbiometrics_hrf_split <- function(dat, group_cols) {
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

gpbiometrics_hrf_group_values <- function(dat, idx, group_cols, group_id) {
  if (length(group_cols) == 0) {
    return(data.frame(unit_label = group_id, stringsAsFactors = FALSE))
  }

  values <- lapply(group_cols, function(nm) as.character(dat[[nm]][idx[1]]))
  names(values) <- group_cols
  as.data.frame(values, stringsAsFactors = FALSE, optional = TRUE)
}
