#' Flag MAD-based EDA wearable artifacts
#'
#' Flags dependency-light, subject-specific EDA artifact categories using robust
#' median absolute deviation (MAD) logic. The categories are heuristic QC
#' labels: step artifacts, needle artifacts, flatline artifacts, and wall
#' artifacts.
#'
#' @param dat A data frame.
#' @param eda_col Numeric EDA/conductance column.
#' @param time_col Optional time column for ordering within group.
#' @param group_cols Optional grouping columns.
#' @param mad_multiplier MAD multiplier used for robust thresholding.
#' @param flatline_tolerance Maximum absolute sample-to-sample change treated
#'   as flatline.
#' @param flatline_min_run Minimum consecutive flatline samples.
#' @param wall_abs_change Optional absolute change threshold for wall artifacts.
#' @param output_prefix Prefix for output columns.
#'
#' @return A data frame with artifact flags and artifact-summary attributes.
#' @export
flag_gazepoint_mad_artifacts <- function(dat,
                                         eda_col = "GSR_US",
                                         time_col = NULL,
                                         group_cols = NULL,
                                         mad_multiplier = 8,
                                         flatline_tolerance = 1e-6,
                                         flatline_min_run = 5,
                                         wall_abs_change = NULL,
                                         output_prefix = "mad") {
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

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  missing_groups <- setdiff(group_cols, names(dat))
  if (length(missing_groups) > 0) {
    stop("Missing `group_cols`: ", paste(missing_groups, collapse = ", "), call. = FALSE)
  }

  out <- dat

  step_col <- paste0(output_prefix, "_step_artifact")
  needle_col <- paste0(output_prefix, "_needle_artifact")
  flatline_col <- paste0(output_prefix, "_flatline_artifact")
  wall_col <- paste0(output_prefix, "_wall_artifact")
  any_col <- paste0(output_prefix, "_artifact")
  type_col <- paste0(output_prefix, "_artifact_type")
  status_col <- paste0(output_prefix, "_artifact_status")

  out[[step_col]] <- FALSE
  out[[needle_col]] <- FALSE
  out[[flatline_col]] <- FALSE
  out[[wall_col]] <- FALSE
  out[[any_col]] <- FALSE
  out[[type_col]] <- "none"
  out[[status_col]] <- "not_processed"

  groups <- gpbiometrics_mad_split_indices(out, group_cols)

  summary_rows <- lapply(names(groups), function(group_id) {
    idx <- groups[[group_id]]

    if (!is.null(time_col)) {
      idx <- idx[order(out[[time_col]][idx])]
    }

    x <- out[[eda_col]][idx]
    finite_x <- x[is.finite(x)]

    if (length(finite_x) < 5) {
      out[[status_col]][idx] <<- "insufficient_finite_samples"

      return(data.frame(
        group_id = group_id,
        n_rows = length(idx),
        n_finite = length(finite_x),
        robust_mad = NA_real_,
        artifact_rows = NA_integer_,
        status = "insufficient_finite_samples",
        stringsAsFactors = FALSE
      ))
    }

    robust_center <- stats::median(finite_x)
    robust_mad <- stats::median(abs(finite_x - robust_center))

    if (!is.finite(robust_mad) || robust_mad == 0) {
      robust_mad <- stats::mad(finite_x, constant = 1, na.rm = TRUE)
    }

    if (!is.finite(robust_mad) || robust_mad == 0) {
      robust_mad <- .Machine$double.eps
    }

    dx <- c(NA_real_, diff(x))
    abs_dx <- abs(dx)

    wall_threshold <- if (!is.null(wall_abs_change)) {
      wall_abs_change
    } else {
      mad_multiplier * robust_mad
    }

    wall <- is.finite(abs_dx) & abs_dx > wall_threshold

    local_deviation <- abs(x - robust_center)
    needle <- is.finite(local_deviation) &
      local_deviation > mad_multiplier * robust_mad &
      c(FALSE, abs_dx[-1] > mad_multiplier * robust_mad)

    step <- gpbiometrics_mad_step_flags(
      x = x,
      mad = robust_mad,
      mad_multiplier = mad_multiplier
    )

    flatline <- gpbiometrics_mad_flatline_flags(
      x = x,
      tolerance = flatline_tolerance,
      min_run = flatline_min_run
    )

    any_art <- step | needle | flatline | wall
    artifact_type <- rep("none", length(idx))
    artifact_type[wall] <- "wall"
    artifact_type[flatline] <- "flatline"
    artifact_type[needle] <- "needle"
    artifact_type[step] <- "step"
    artifact_type[rowSums(cbind(step, needle, flatline, wall), na.rm = TRUE) > 1] <- "multiple"

    out[[step_col]][idx] <<- step
    out[[needle_col]][idx] <<- needle
    out[[flatline_col]][idx] <<- flatline
    out[[wall_col]][idx] <<- wall
    out[[any_col]][idx] <<- any_art
    out[[type_col]][idx] <<- artifact_type
    out[[status_col]][idx] <<- "mad_artifact_typology_applied"

    data.frame(
      group_id = group_id,
      n_rows = length(idx),
      n_finite = length(finite_x),
      robust_mad = robust_mad,
      step_rows = sum(step, na.rm = TRUE),
      needle_rows = sum(needle, na.rm = TRUE),
      flatline_rows = sum(flatline, na.rm = TRUE),
      wall_rows = sum(wall, na.rm = TRUE),
      artifact_rows = sum(any_art, na.rm = TRUE),
      status = "mad_artifact_typology_applied",
      stringsAsFactors = FALSE
    )
  })

  summary_table <- do.call(rbind, summary_rows)
  rownames(summary_table) <- NULL

  overview <- data.frame(
    input_rows = nrow(dat),
    group_count = length(groups),
    artifact_rows = sum(out[[any_col]], na.rm = TRUE),
    step_rows = sum(out[[step_col]], na.rm = TRUE),
    needle_rows = sum(out[[needle_col]], na.rm = TRUE),
    flatline_rows = sum(out[[flatline_col]], na.rm = TRUE),
    wall_rows = sum(out[[wall_col]], na.rm = TRUE),
    status = "mad_artifact_typology_complete",
    interpretation = paste(
      "MAD artifact categories are robust heuristic QC labels for wearable EDA signals.",
      "They do not infer psychological state and should be inspected alongside raw signals."
    ),
    stringsAsFactors = FALSE
  )

  attr(out, "mad_artifact_overview") <- overview
  attr(out, "mad_artifact_summary") <- summary_table
  attr(out, "mad_artifact_settings") <- list(
    eda_col = eda_col,
    time_col = time_col,
    group_cols = group_cols,
    mad_multiplier = mad_multiplier,
    flatline_tolerance = flatline_tolerance,
    flatline_min_run = flatline_min_run,
    wall_abs_change = wall_abs_change,
    output_prefix = output_prefix
  )

  class(out) <- unique(c("gazepoint_mad_artifact_flags", class(out)))
  out
}

gpbiometrics_mad_split_indices <- function(dat, group_cols) {
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

gpbiometrics_mad_flatline_flags <- function(x,
                                            tolerance = 1e-6,
                                            min_run = 5) {
  flat <- rep(FALSE, length(x))

  if (length(x) < min_run) {
    return(flat)
  }

  small_change <- c(FALSE, abs(diff(x)) <= tolerance)
  small_change[!is.finite(small_change)] <- FALSE

  run <- rle(small_change)
  ends <- cumsum(run$lengths)
  starts <- ends - run$lengths + 1

  for (i in seq_along(run$values)) {
    if (isTRUE(run$values[i]) && run$lengths[i] >= min_run) {
      flat[starts[i]:ends[i]] <- TRUE
    }
  }

  flat
}

gpbiometrics_mad_step_flags <- function(x,
                                        mad,
                                        mad_multiplier = 8) {
  step <- rep(FALSE, length(x))

  if (length(x) < 8 || !is.finite(mad) || mad <= 0) {
    return(step)
  }

  threshold <- mad_multiplier * mad

  for (i in 4:(length(x) - 4)) {
    before <- x[(i - 3):(i - 1)]
    after <- x[i:(i + 3)]

    if (sum(is.finite(before)) >= 2 && sum(is.finite(after)) >= 2) {
      shift <- abs(stats::median(after, na.rm = TRUE) - stats::median(before, na.rm = TRUE))

      if (is.finite(shift) && shift > threshold) {
        step[i:(i + 3)] <- TRUE
      }
    }
  }

  step
}
