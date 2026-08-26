
# Exact roadmap backlog helpers:
# schema/QC, multimodal simulation, AOI/scanpath summaries, manifests,
# PPG template similarity, and HRV wavelet-style PSD.

.gp_exact_check_df <- function(data, arg = "data") {
  if (!is.data.frame(data)) {
    stop("`", arg, "` must be a data frame.", call. = FALSE)
  }
  if (!nrow(data)) {
    stop("`", arg, "` has no rows.", call. = FALSE)
  }
  invisible(data)
}

.gp_exact_default_dictionary <- function() {
  list(
    time_s = c("time_s", "time", "timestamp", "TIME", "TIME_TICK", "MSTIMER", "CNT"),
    participant = c("participant", "participant_id", "subject", "subject_id", "SUBJECT", "P"),
    trial = c("trial", "trial_id", "TRIAL", "stimulus", "stimulus_id", "screen"),
    pupil_left = c("pupil_left", "left_pupil", "LPD", "LPMM", "left_pupil_diameter"),
    pupil_right = c("pupil_right", "right_pupil", "RPD", "RPMM", "right_pupil_diameter"),
    gaze_x = c("gaze_x", "x", "BPOGX", "FPOGX", "GPOGX", "CX"),
    gaze_y = c("gaze_y", "y", "BPOGY", "FPOGY", "GPOGY", "CY"),
    validity_left = c("validity_left", "left_validity", "LPV", "LVALID", "left_valid"),
    validity_right = c("validity_right", "right_validity", "RPV", "RVALID", "right_valid"),
    fixation_id = c("fixation_id", "fix_id", "FPOGID", "fixation"),
    AOI = c("AOI", "aoi", "aoi_name", "AOI_NAME", "area_of_interest"),
    GSR = c("GSR", "GSR_US", "EDA", "eda", "skin_conductance", "conductance"),
    PPG = c("PPG", "BVP", "HRP", "ppg", "bvp", "pulse"),
    HR = c("HR", "heart_rate", "heartrate", "bpm"),
    IBI = c("IBI", "RRI", "RR", "NN", "ibi_ms", "rr_ms"),
    DIAL = c("DIAL", "dial", "engagement", "engagement_dial"),
    TTL = c("TTL", "TTL0", "TTL1", "marker", "event_marker", "USER", "USER_DATA")
  )
}

.gp_exact_read_table <- function(path) {
  if (!is.character(path) || length(path) != 1L || !file.exists(path)) {
    stop("`path` must be an existing file path.", call. = FALSE)
  }

  first <- readLines(path, n = 1L, warn = FALSE)
  sep <- ","
  if (length(first)) {
    counts <- c(
      comma = lengths(regmatches(first, gregexpr(",", first, fixed = TRUE))),
      semicolon = lengths(regmatches(first, gregexpr(";", first, fixed = TRUE))),
      tab = lengths(regmatches(first, gregexpr("\t", first, fixed = TRUE)))
    )
    sep <- switch(names(which.max(counts)), comma = ",", semicolon = ";", tab = "\t", ",")
  }

  utils::read.table(
    path,
    sep = sep,
    header = TRUE,
    stringsAsFactors = FALSE,
    check.names = FALSE,
    comment.char = ""
  )
}

.gp_exact_guess_col <- function(data, candidates, label, required = TRUE) {
  nms <- names(data)
  idx <- match(tolower(candidates), tolower(nms))
  idx <- idx[!is.na(idx)]

  if (length(idx)) {
    return(nms[idx[1L]])
  }

  if (isTRUE(required)) {
    stop("Could not identify ", label, " column. Supply it explicitly.", call. = FALSE)
  }

  NULL
}

.gp_exact_time_seconds <- function(time) {
  time <- suppressWarnings(as.numeric(time))

  if (!length(time) || all(!is.finite(time))) {
    return(time)
  }

  d <- diff(time[is.finite(time)])
  d <- d[is.finite(d) & d > 0]

  if (!length(d)) {
    return(time)
  }

  med_d <- stats::median(d, na.rm = TRUE)

  if (is.finite(med_d) && med_d > 5) {
    time / 1000
  } else {
    time
  }
}

.gp_exact_group_indices <- function(data, group_cols = NULL) {
  if (is.null(group_cols) || !length(group_cols)) {
    return(list(all = seq_len(nrow(data))))
  }

  missing <- setdiff(group_cols, names(data))
  if (length(missing)) {
    stop("Missing grouping columns: ", paste(missing, collapse = ", "), call. = FALSE)
  }

  split(seq_len(nrow(data)), interaction(data[group_cols], drop = TRUE, sep = " | "))
}

.gp_exact_unique_name <- function(existing, target) {
  if (!target %in% existing) {
    return(target)
  }

  i <- 2L
  repeat {
    candidate <- paste0(target, "_", i)
    if (!candidate %in% existing) {
      return(candidate)
    }
    i <- i + 1L
  }
}

.gp_exact_local_peaks <- function(x, min_distance = 1L) {
  x <- suppressWarnings(as.numeric(x))

  if (length(x) < 3L) {
    return(integer())
  }

  peaks <- which(
    x[-c(1L, length(x))] > x[-c(length(x) - 1L, length(x))] &
      x[-c(1L, 2L)] <= x[-c(1L, length(x))]
  ) + 1L

  peaks <- peaks[is.finite(x[peaks])]

  if (!length(peaks) || min_distance <= 1L) {
    return(peaks)
  }

  kept <- integer()
  last <- -Inf

  for (p in peaks) {
    if (p - last >= min_distance) {
      kept <- c(kept, p)
      last <- p
    } else if (length(kept) && x[p] > x[kept[length(kept)]]) {
      kept[length(kept)] <- p
      last <- p
    }
  }

  kept
}

.gp_exact_entropy <- function(x) {
  x <- x[!is.na(x) & nzchar(as.character(x))]
  if (!length(x)) {
    return(NA_real_)
  }

  tab <- table(x)
  p <- as.numeric(tab) / sum(tab)
  -sum(p * log2(p), na.rm = TRUE)
}

.gp_exact_file_info <- function(files) {
  if (is.null(files)) {
    return(data.frame())
  }

  files <- as.character(files)
  info <- file.info(files)

  data.frame(
    path = files,
    exists = file.exists(files),
    size_bytes = ifelse(is.na(info$size), NA_real_, info$size),
    modified_time = as.character(info$mtime),
    stringsAsFactors = FALSE
  )
}

#' Standardize common Gazepoint column names
#'
#' Maps common Gazepoint-style export aliases to canonical names such as
#' `time_s`, `participant`, `trial`, `pupil_left`, `pupil_right`, `gaze_x`,
#' `gaze_y`, `GSR`, and `PPG`.
#'
#' @param data Data frame, or a named list of data frames.
#' @param dictionary Optional named list mapping canonical names to aliases.
#' @param conflict How to handle rename conflicts: `"suffix"`, `"error"`, or
#'   `"keep"`.
#' @param ignore_case If TRUE, match aliases case-insensitively.
#'
#' @return Data frame, or list of data frames, with a
#'   `gazepoint_column_standardization` attribute containing the rename audit.
#' @export
standardize_gazepoint_column_names <- function(data,
                                               dictionary = NULL,
                                               conflict = c("suffix", "error", "keep"),
                                               ignore_case = TRUE) {
  conflict <- match.arg(conflict)

  if (is.null(dictionary)) {
    dictionary <- .gp_exact_default_dictionary()
  }

  if (is.list(data) && !is.data.frame(data)) {
    return(lapply(data, standardize_gazepoint_column_names,
      dictionary = dictionary,
      conflict = conflict,
      ignore_case = ignore_case
    ))
  }

  .gp_exact_check_df(data)

  original <- names(data)
  new_names <- original
  audit <- data.frame(
    original_name = original,
    standardized_name = original,
    role = NA_character_,
    changed = FALSE,
    stringsAsFactors = FALSE
  )

  lookup_names <- if (isTRUE(ignore_case)) tolower(original) else original

  for (role in names(dictionary)) {
    aliases <- unique(c(role, dictionary[[role]]))
    aliases_lookup <- if (isTRUE(ignore_case)) tolower(aliases) else aliases
    hits <- which(lookup_names %in% aliases_lookup)

    if (!length(hits)) {
      next
    }

    for (j in seq_along(hits)) {
      idx <- hits[j]
      target <- role

      if (new_names[idx] == role) {
        audit$role[idx] <- role
        next
      }

      if (target %in% new_names[-idx]) {
        if (conflict == "error") {
          stop("Column rename conflict for canonical name `", target, "`.", call. = FALSE)
        }
        if (conflict == "keep") {
          audit$role[idx] <- role
          next
        }
        target <- .gp_exact_unique_name(new_names[-idx], target)
      }

      new_names[idx] <- target
      audit$standardized_name[idx] <- target
      audit$role[idx] <- role
      audit$changed[idx] <- target != original[idx]
    }
  }

  names(data) <- new_names
  attr(data, "gazepoint_column_standardization") <- audit
  data
}

#' Audit a Gazepoint export schema
#'
#' Reports whether expected Gazepoint-style roles are present, missing, or
#' ambiguous, using the same alias dictionary as
#' `standardize_gazepoint_column_names()`.
#'
#' @param data Data frame or CSV/TSV path.
#' @param expected_roles Optional character vector of expected canonical roles.
#' @param dictionary Optional alias dictionary.
#' @param strict If TRUE, error when required roles are missing.
#'
#' @return Data frame with one row per expected role.
#' @export
audit_gazepoint_export_schema <- function(data,
                                          expected_roles = NULL,
                                          dictionary = NULL,
                                          strict = FALSE) {
  if (is.character(data) && length(data) == 1L && file.exists(data)) {
    data <- .gp_exact_read_table(data)
  }

  .gp_exact_check_df(data)

  if (is.null(dictionary)) {
    dictionary <- .gp_exact_default_dictionary()
  }

  if (is.null(expected_roles)) {
    expected_roles <- names(dictionary)
  }

  nms <- names(data)
  nms_lookup <- tolower(nms)

  rows <- vector("list", length(expected_roles))

  for (i in seq_along(expected_roles)) {
    role <- expected_roles[i]
    aliases <- unique(c(role, dictionary[[role]]))
    hits <- which(nms_lookup %in% tolower(aliases))
    matched <- nms[hits]

    status <- if (!length(hits)) {
      "missing"
    } else if (length(hits) == 1L) {
      "present"
    } else {
      "ambiguous"
    }

    rows[[i]] <- data.frame(
      role = role,
      present = length(hits) > 0L,
      n_matches = length(hits),
      matched_columns = paste(matched, collapse = ", "),
      status = status,
      recommendation = switch(status,
        missing = paste0("Add or map a column for role `", role, "`."),
        ambiguous = paste0("Multiple columns match role `", role, "`; standardize explicitly."),
        present = "OK"
      ),
      stringsAsFactors = FALSE
    )
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL

  duplicate_columns <- unique(nms[duplicated(nms)])
  attr(out, "duplicate_columns") <- duplicate_columns

  if (isTRUE(strict) && any(out$status == "missing")) {
    stop(
      "Missing required Gazepoint roles: ",
      paste(out$role[out$status == "missing"], collapse = ", "),
      call. = FALSE
    )
  }

  out
}

#' Simulate a small multimodal Gazepoint-style dataset
#'
#' Generates deterministic synthetic biometric, pupil/gaze, event, AOI, and
#' fixation tables for tests, examples, and smoke-test workflows. The output is
#' for software demonstration only and should not be treated as physiological
#' validation data.
#'
#' @param n Number of samples.
#' @param duration_s Recording duration in seconds.
#' @param sampling_rate_hz Sampling rate in Hz. If supplied, overrides `n`.
#' @param seed Optional random seed.
#' @param participant Participant identifier.
#' @param n_trials Number of trial/event periods.
#'
#' @return Named list with `biometrics`, `eye`, `events`, `fixations`, and
#'   `metadata`.
#' @export
simulate_gazepoint_multimodal_data <- function(n = NULL,
                                               duration_s = 20,
                                               sampling_rate_hz = 50,
                                               seed = 1,
                                               participant = "P01",
                                               n_trials = 4) {
  if (!is.null(seed)) {
    old_seed <- if (exists(".Random.seed", envir = .GlobalEnv)) get(".Random.seed", envir = .GlobalEnv) else NULL
    on.exit({
      if (is.null(old_seed)) {
        if (exists(".Random.seed", envir = .GlobalEnv)) rm(".Random.seed", envir = .GlobalEnv)
      } else {
        assign(".Random.seed", old_seed, envir = .GlobalEnv)
      }
    }, add = TRUE)
    set.seed(seed)
  }

  if (is.null(n)) {
    n <- max(2L, as.integer(duration_s * sampling_rate_hz) + 1L)
  }

  time_s <- seq(0, duration_s, length.out = n)
  mstimer <- round(time_s * 1000)
  trial_breaks <- cut(time_s, breaks = n_trials, labels = FALSE, include.lowest = TRUE)
  trial <- paste0("T", trial_breaks)

  event_time <- seq(2, max(2, duration_s - 2), length.out = n_trials)
  events <- data.frame(
    event_id = paste0("E", seq_len(n_trials)),
    event_time = event_time,
    event_label = rep(c("baseline", "stimulus"), length.out = n_trials),
    trial = paste0("T", seq_len(n_trials)),
    participant = participant,
    stringsAsFactors = FALSE
  )

  event_pulse <- rep(0, n)
  for (et in event_time) {
    event_pulse <- event_pulse + exp(-((time_s - (et + 1.2))^2) / 0.20)
  }

  gsr <- 2 + 0.03 * time_s + 0.20 * event_pulse + stats::rnorm(n, 0, 0.01)
  ppg <- sin(2 * pi * 1.2 * time_s) + 0.15 * sin(2 * pi * 2.4 * time_s)
  hr <- 72 + 4 * sin(2 * pi * 0.08 * time_s) + stats::rnorm(n, 0, 0.3)
  ibi <- 60000 / pmax(hr, 1)
  dial <- 50 + 10 * sin(2 * pi * 0.03 * time_s)
  ttl <- as.integer(time_s %in% time_s[vapply(event_time, function(et) which.min(abs(time_s - et)), integer(1))])

  biometrics <- data.frame(
    time_s = time_s,
    MSTIMER = mstimer,
    participant = participant,
    trial = trial,
    GSR = gsr,
    PPG = ppg,
    HR = hr,
    IBI = ibi,
    DIAL = dial,
    TTL = ttl,
    stringsAsFactors = FALSE
  )

  gaze_x <- pmin(pmax(0.5 + 0.25 * sin(2 * pi * 0.15 * time_s) + stats::rnorm(n, 0, 0.02), 0), 1)
  gaze_y <- pmin(pmax(0.5 + 0.20 * cos(2 * pi * 0.11 * time_s) + stats::rnorm(n, 0, 0.02), 0), 1)
  pupil_left <- 3 + 0.15 * event_pulse + stats::rnorm(n, 0, 0.02)
  pupil_right <- pupil_left + stats::rnorm(n, 0, 0.015)

  blink_idx <- seq(round(n * 0.20), round(n * 0.80), length.out = 2L)
  for (b in blink_idx) {
    span <- seq(max(1L, b - 2L), min(n, b + 2L))
    pupil_left[span] <- NA_real_
    pupil_right[span] <- NA_real_
  }

  aoi <- ifelse(gaze_x < 0.33, "left", ifelse(gaze_x > 0.67, "right", "center"))

  eye <- data.frame(
    time_s = time_s,
    participant = participant,
    trial = trial,
    pupil_left = pupil_left,
    pupil_right = pupil_right,
    gaze_x = gaze_x,
    gaze_y = gaze_y,
    validity_left = as.integer(is.finite(pupil_left)),
    validity_right = as.integer(is.finite(pupil_right)),
    AOI = aoi,
    stringsAsFactors = FALSE
  )

  fix_starts <- seq(0, duration_s - 1, by = max(1, duration_s / 10))
  fixations <- data.frame(
    participant = participant,
    trial = paste0("T", pmax(1, pmin(n_trials, ceiling(seq_along(fix_starts) / max(1, length(fix_starts) / n_trials))))),
    fixation_id = seq_along(fix_starts),
    start_time = fix_starts,
    end_time = pmin(fix_starts + 0.6, duration_s),
    duration_s = pmin(fix_starts + 0.6, duration_s) - fix_starts,
    AOI = rep(c("left", "center", "right"), length.out = length(fix_starts)),
    x = rep(c(0.25, 0.50, 0.75), length.out = length(fix_starts)),
    y = rep(c(0.45, 0.50, 0.55), length.out = length(fix_starts)),
    stringsAsFactors = FALSE
  )

  list(
    biometrics = biometrics,
    eye = eye,
    events = events,
    fixations = fixations,
    metadata = list(
      participant = participant,
      duration_s = duration_s,
      sampling_rate_hz = sampling_rate_hz,
      n_samples = n,
      synthetic = TRUE
    )
  )
}

#' Assess sampling irregularity in Gazepoint time series
#'
#' Summarizes median sample interval, effective sampling rate, jitter, repeated
#' timestamps, negative steps, and large gaps overall or by group.
#'
#' @param data Data frame or numeric time vector.
#' @param time_col Time column for data-frame input.
#' @param group_cols Optional grouping columns.
#' @param nominal_rate_hz Optional expected sampling rate.
#' @param large_gap_factor Gap threshold relative to median interval.
#'
#' @return Data frame with one row per group.
#' @export
assess_gazepoint_sampling_irregularity <- function(data,
                                                   time_col = NULL,
                                                   group_cols = NULL,
                                                   nominal_rate_hz = NULL,
                                                   large_gap_factor = 3) {
  if (is.numeric(data) && is.null(dim(data))) {
    data <- data.frame(time_s = data)
    time_col <- "time_s"
  }

  .gp_exact_check_df(data)

  if (is.null(time_col)) {
    time_col <- .gp_exact_guess_col(data, .gp_exact_default_dictionary()$time_s, "time", TRUE)
  }

  groups <- .gp_exact_group_indices(data, group_cols)
  rows <- vector("list", length(groups))
  k <- 0L

  for (g in names(groups)) {
    idx <- groups[[g]]
    tt <- .gp_exact_time_seconds(data[[time_col]][idx])
    tt <- tt[is.finite(tt)]

    d <- diff(tt)
    pos_d <- d[is.finite(d) & d > 0]
    med <- if (length(pos_d)) stats::median(pos_d, na.rm = TRUE) else NA_real_
    mean_rate <- if (is.finite(med) && med > 0) 1 / med else NA_real_
    jitter <- if (length(pos_d)) stats::sd(pos_d, na.rm = TRUE) else NA_real_
    large_gap_threshold <- if (is.finite(med)) med * large_gap_factor else NA_real_

    dropped <- if (is.finite(med) && med > 0 && length(pos_d)) {
      sum(pmax(0, round(pos_d / med) - 1), na.rm = TRUE)
    } else {
      NA_real_
    }

    k <- k + 1L
    row <- data.frame(
      group = g,
      n_samples = length(tt),
      median_interval_s = med,
      effective_rate_hz = mean_rate,
      nominal_rate_hz = ifelse(is.null(nominal_rate_hz), NA_real_, nominal_rate_hz),
      jitter_sd_s = jitter,
      min_interval_s = if (length(pos_d)) min(pos_d, na.rm = TRUE) else NA_real_,
      max_interval_s = if (length(pos_d)) max(pos_d, na.rm = TRUE) else NA_real_,
      n_negative_steps = sum(d < 0, na.rm = TRUE),
      n_zero_steps = sum(d == 0, na.rm = TRUE),
      n_large_gaps = if (is.finite(large_gap_threshold)) sum(pos_d > large_gap_threshold, na.rm = TRUE) else NA_integer_,
      estimated_dropped_samples = dropped,
      stringsAsFactors = FALSE
    )

    if (!is.null(group_cols) && length(group_cols)) {
      row <- cbind(data[idx[1L], group_cols, drop = FALSE], row[setdiff(names(row), "group")])
    }

    rows[[k]] <- row
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  out
}

#' Diagnose synchronization drift between two time bases
#'
#' Estimates lag and linear drift between matched timestamps or event markers.
#' A fixed lag has a near-zero drift slope; a changing lag has a non-zero slope.
#'
#' @param reference Reference timestamps or data frame.
#' @param target Target timestamps or data frame.
#' @param reference_time_col Optional reference time column.
#' @param target_time_col Optional target time column.
#' @param max_pairs Optional maximum number of matched pairs.
#'
#' @return List with `summary` and `lag_table`.
#' @export
diagnose_gazepoint_sync_drift <- function(reference,
                                          target = NULL,
                                          reference_time_col = NULL,
                                          target_time_col = NULL,
                                          max_pairs = NULL) {
  if (is.data.frame(reference)) {
    reference_time_col <- if (is.null(reference_time_col)) {
      .gp_exact_guess_col(reference, .gp_exact_default_dictionary()$time_s, "reference time", TRUE)
    } else {
      reference_time_col
    }
    ref_time <- .gp_exact_time_seconds(reference[[reference_time_col]])
  } else {
    ref_time <- .gp_exact_time_seconds(reference)
  }

  if (is.null(target)) {
    stop("Supply `target` timestamps or a target data frame.", call. = FALSE)
  }

  if (is.data.frame(target)) {
    target_time_col <- if (is.null(target_time_col)) {
      .gp_exact_guess_col(target, .gp_exact_default_dictionary()$time_s, "target time", TRUE)
    } else {
      target_time_col
    }
    target_time <- .gp_exact_time_seconds(target[[target_time_col]])
  } else {
    target_time <- .gp_exact_time_seconds(target)
  }

  n <- min(length(ref_time), length(target_time))
  if (!is.null(max_pairs)) {
    n <- min(n, as.integer(max_pairs))
  }

  if (n < 2L) {
    stop("At least two matched timestamp pairs are required.", call. = FALSE)
  }

  ref_time <- ref_time[seq_len(n)]
  target_time <- target_time[seq_len(n)]
  ok <- is.finite(ref_time) & is.finite(target_time)
  ref_time <- ref_time[ok]
  target_time <- target_time[ok]

  if (length(ref_time) < 2L) {
    stop("At least two finite matched timestamp pairs are required.", call. = FALSE)
  }

  lag <- target_time - ref_time
  fit <- stats::lm(lag ~ ref_time)
  co <- stats::coef(fit)

  lag_table <- data.frame(
    pair_id = seq_along(ref_time),
    reference_time = ref_time,
    target_time = target_time,
    lag_s = lag,
    fitted_lag_s = stats::fitted(fit),
    residual_lag_s = stats::resid(fit),
    stringsAsFactors = FALSE
  )

  summary <- data.frame(
    n_pairs = length(ref_time),
    median_lag_s = stats::median(lag, na.rm = TRUE),
    mean_lag_s = mean(lag, na.rm = TRUE),
    min_lag_s = min(lag, na.rm = TRUE),
    max_lag_s = max(lag, na.rm = TRUE),
    lag_range_s = diff(range(lag, na.rm = TRUE)),
    drift_slope_s_per_s = unname(co[2L]),
    drift_intercept_s = unname(co[1L]),
    residual_sd_s = stats::sd(stats::resid(fit), na.rm = TRUE),
    stringsAsFactors = FALSE
  )

  out <- list(summary = summary, lag_table = lag_table)
  class(out) <- c("gazepoint_sync_drift", "list")
  out
}

#' Summarize AOI dwell time and entries
#'
#' Computes AOI dwell time, entry counts, first-entry latency, and valid-sample
#' ratios from gaze samples or fixation/AOI tables.
#'
#' @param data Data frame containing AOI labels.
#' @param time_col Optional time column for sample-level data.
#' @param aoi_col AOI column.
#' @param duration_col Optional duration column for fixation-level data.
#' @param group_cols Optional grouping columns such as participant/trial.
#' @param valid_col Optional validity column.
#'
#' @return Data frame with one row per group and AOI.
#' @export
summarize_gazepoint_aoi_dwell <- function(data,
                                          time_col = NULL,
                                          aoi_col = NULL,
                                          duration_col = NULL,
                                          group_cols = NULL,
                                          valid_col = NULL) {
  .gp_exact_check_df(data)

  if (is.null(aoi_col)) {
    aoi_col <- .gp_exact_guess_col(data, .gp_exact_default_dictionary()$AOI, "AOI", TRUE)
  }

  if (is.null(duration_col)) {
    duration_col <- .gp_exact_guess_col(data, c("duration_s", "duration", "fixation_duration", "FPOGD"), "duration", FALSE)
  }

  if (is.null(time_col) && is.null(duration_col)) {
    time_col <- .gp_exact_guess_col(data, .gp_exact_default_dictionary()$time_s, "time", TRUE)
  } else if (is.null(time_col)) {
    time_col <- .gp_exact_guess_col(data, .gp_exact_default_dictionary()$time_s, "time", FALSE)
  }

  groups <- .gp_exact_group_indices(data, group_cols)
  rows <- list()
  k <- 0L

  for (g in names(groups)) {
    idx <- groups[[g]]
    z <- data[idx, , drop = FALSE]
    aoi <- as.character(z[[aoi_col]])
    valid <- rep(TRUE, nrow(z))

    if (!is.null(valid_col) && valid_col %in% names(z)) {
      valid <- suppressWarnings(as.numeric(z[[valid_col]])) > 0
      valid[is.na(valid)] <- FALSE
    }

    if (!is.null(duration_col) && duration_col %in% names(z)) {
      duration <- suppressWarnings(as.numeric(z[[duration_col]]))
      time <- if (!is.null(time_col) && time_col %in% names(z)) .gp_exact_time_seconds(z[[time_col]]) else seq_along(duration)
    } else {
      time <- .gp_exact_time_seconds(z[[time_col]])
      ord <- order(time)
      z <- z[ord, , drop = FALSE]
      aoi <- aoi[ord]
      valid <- valid[ord]
      time <- time[ord]
      d <- diff(time)
      med_d <- stats::median(d[d > 0 & is.finite(d)], na.rm = TRUE)
      if (!is.finite(med_d)) med_d <- 0
      duration <- c(d, med_d)
      duration[!is.finite(duration) | duration < 0] <- 0
    }

    unique_aoi <- unique(aoi[!is.na(aoi) & nzchar(aoi)])
    group_start <- min(time, na.rm = TRUE)

    for (aa in unique_aoi) {
      in_aoi <- aoi == aa & valid
      prev <- c(FALSE, utils::head(in_aoi, -1L))
      entries <- sum(in_aoi & !prev, na.rm = TRUE)

      first_idx <- which(in_aoi)
      latency <- if (length(first_idx) && is.finite(group_start)) time[first_idx[1L]] - group_start else NA_real_

      k <- k + 1L
      row <- data.frame(
        group = g,
        AOI = aa,
        n_samples = sum(aoi == aa, na.rm = TRUE),
        valid_samples = sum(in_aoi, na.rm = TRUE),
        dwell_time_s = sum(duration[in_aoi], na.rm = TRUE),
        entry_count = entries,
        latency_to_first_entry_s = latency,
        valid_ratio = mean(valid[aoi == aa], na.rm = TRUE),
        stringsAsFactors = FALSE
      )

      if (!is.null(group_cols) && length(group_cols)) {
        row <- cbind(z[1L, group_cols, drop = FALSE], row[setdiff(names(row), "group")])
      }

      rows[[k]] <- row
    }
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  out
}

#' Summarize simple scanpath metrics
#'
#' Computes simple gaze/fixation-path summaries including path length, saccade
#' count, regression-like leftward movements, fixation count, AOI transitions,
#' and transition entropy.
#'
#' @param data Gaze or fixation data frame.
#' @param x_col Gaze/fixation x column.
#' @param y_col Gaze/fixation y column.
#' @param time_col Optional time column.
#' @param aoi_col Optional AOI column.
#' @param fixation_id_col Optional fixation identifier column.
#' @param group_cols Optional grouping columns.
#' @param min_saccade_distance Minimum Euclidean movement counted as saccade.
#'
#' @return Data frame with one row per group.
#' @export
summarize_gazepoint_scanpath_metrics <- function(data,
                                                 x_col = NULL,
                                                 y_col = NULL,
                                                 time_col = NULL,
                                                 aoi_col = NULL,
                                                 fixation_id_col = NULL,
                                                 group_cols = NULL,
                                                 min_saccade_distance = 0.02) {
  .gp_exact_check_df(data)

  if (is.null(x_col)) {
    x_col <- .gp_exact_guess_col(data, c("gaze_x", "x", "BPOGX", "FPOGX", "GPOGX"), "x", TRUE)
  }

  if (is.null(y_col)) {
    y_col <- .gp_exact_guess_col(data, c("gaze_y", "y", "BPOGY", "FPOGY", "GPOGY"), "y", TRUE)
  }

  if (is.null(time_col)) {
    time_col <- .gp_exact_guess_col(data, .gp_exact_default_dictionary()$time_s, "time", FALSE)
  }

  if (is.null(aoi_col)) {
    aoi_col <- .gp_exact_guess_col(data, .gp_exact_default_dictionary()$AOI, "AOI", FALSE)
  }

  if (is.null(fixation_id_col)) {
    fixation_id_col <- .gp_exact_guess_col(data, .gp_exact_default_dictionary()$fixation_id, "fixation id", FALSE)
  }

  groups <- .gp_exact_group_indices(data, group_cols)
  rows <- vector("list", length(groups))
  k <- 0L

  for (g in names(groups)) {
    idx <- groups[[g]]
    z <- data[idx, , drop = FALSE]

    if (!is.null(time_col) && time_col %in% names(z)) {
      ord <- order(.gp_exact_time_seconds(z[[time_col]]))
      z <- z[ord, , drop = FALSE]
    }

    x <- suppressWarnings(as.numeric(z[[x_col]]))
    y <- suppressWarnings(as.numeric(z[[y_col]]))
    ok <- is.finite(x) & is.finite(y)
    x <- x[ok]
    y <- y[ok]

    dist <- if (length(x) >= 2L) sqrt(diff(x)^2 + diff(y)^2) else numeric()
    path_length <- sum(dist, na.rm = TRUE)
    saccades <- sum(dist > min_saccade_distance, na.rm = TRUE)
    regressions <- if (length(x) >= 2L) sum(diff(x) < -min_saccade_distance, na.rm = TRUE) else 0L

    fixation_count <- if (!is.null(fixation_id_col) && fixation_id_col %in% names(z)) {
      length(unique(z[[fixation_id_col]][!is.na(z[[fixation_id_col]])]))
    } else {
      length(x)
    }

    aoi_transition_count <- NA_integer_
    transition_entropy <- NA_real_

    if (!is.null(aoi_col) && aoi_col %in% names(z)) {
      aoi <- as.character(z[[aoi_col]])
      aoi <- aoi[!is.na(aoi) & nzchar(aoi)]
      if (length(aoi)) {
        aoi_rle <- rle(aoi)$values
        aoi_transition_count <- max(0L, length(aoi_rle) - 1L)
        transitions <- if (length(aoi_rle) >= 2L) paste(utils::head(aoi_rle, -1L), utils::tail(aoi_rle, -1L), sep = "->") else character()
        transition_entropy <- .gp_exact_entropy(transitions)
      }
    }

    k <- k + 1L
    row <- data.frame(
      group = g,
      n_points = length(x),
      fixation_count = fixation_count,
      path_length = path_length,
      mean_step_length = if (length(dist)) mean(dist, na.rm = TRUE) else NA_real_,
      saccade_count = saccades,
      regression_like_count = regressions,
      aoi_transition_count = aoi_transition_count,
      transition_entropy = transition_entropy,
      stringsAsFactors = FALSE
    )

    if (!is.null(group_cols) && length(group_cols)) {
      row <- cbind(data[idx[1L], group_cols, drop = FALSE], row[setdiff(names(row), "group")])
    }

    rows[[k]] <- row
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  out
}

#' Create a Gazepoint analysis manifest
#'
#' Creates a reproducibility manifest containing package version, files, settings,
#' outputs, exclusions, and optional session information. If `path` is supplied,
#' a plain-text manifest is written for audit trails.
#'
#' @param files Optional character vector of input files.
#' @param settings Optional named list of analysis settings.
#' @param outputs Optional named list or character vector of generated outputs.
#' @param exclusions Optional data frame or named list of exclusions.
#' @param path Optional output path for a text manifest.
#' @param include_session If TRUE, include `sessionInfo()` in the return object.
#'
#' @return Manifest list.
#' @export
create_gazepoint_analysis_manifest <- function(files = NULL,
                                               settings = list(),
                                               outputs = NULL,
                                               exclusions = NULL,
                                               path = NULL,
                                               include_session = TRUE) {
  if (!is.list(settings)) {
    stop("`settings` must be a named list.", call. = FALSE)
  }

  manifest <- list(
    package = "gpbiometrics",
    package_version = as.character(utils::packageVersion("gpbiometrics")),
    created = as.character(Sys.time()),
    files = .gp_exact_file_info(files),
    settings = settings,
    outputs = outputs,
    exclusions = exclusions
  )

  if (isTRUE(include_session)) {
    manifest$session_info <- utils::sessionInfo()
  }

  if (!is.null(path)) {
    lines <- c(
      "gpbiometrics analysis manifest",
      paste0("created: ", manifest$created),
      paste0("package_version: ", manifest$package_version),
      "",
      "[files]"
    )

    if (NROW(manifest$files)) {
      file_lines <- apply(manifest$files, 1L, function(z) {
        paste(names(z), z, sep = "=", collapse = "; ")
      })
      lines <- c(lines, file_lines)
    } else {
      lines <- c(lines, "none")
    }

    lines <- c(lines, "", "[settings]")
    if (length(settings)) {
      lines <- c(lines, paste(names(settings), unlist(settings), sep = ": "))
    } else {
      lines <- c(lines, "none")
    }

    lines <- c(lines, "", "[outputs]")
    if (!is.null(outputs)) {
      if (is.list(outputs)) {
        lines <- c(lines, paste(names(outputs), unlist(outputs), sep = ": "))
      } else {
        lines <- c(lines, as.character(outputs))
      }
    } else {
      lines <- c(lines, "none")
    }

    dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
    writeLines(lines, path, useBytes = TRUE)
    manifest$manifest_path <- normalizePath(path, winslash = "/", mustWork = FALSE)
  }

  class(manifest) <- c("gazepoint_analysis_manifest", "list")
  manifest
}

#' Compute PPG beat-template similarity
#'
#' Extracts peak-centered PPG windows, builds a median beat template, and
#' computes per-beat correlation with the template as an interpretable quality
#' metric.
#'
#' @param data PPG data frame or numeric PPG vector.
#' @param time_col Time column for data-frame input.
#' @param ppg_col PPG/BVP signal column for data-frame input.
#' @param peaks Optional peak indices or peak times.
#' @param window_s Two-element window around each peak in seconds.
#' @param sampling_rate_hz Sampling rate for vector input or when time is absent.
#' @param n_grid Number of points in the normalized beat template.
#' @param similarity_threshold Correlation threshold for `quality_ok`.
#'
#' @return List with `beats`, `template`, `summary`, and `settings`.
#' @export
compute_gazepoint_ppg_template_similarity <- function(data,
                                                      time_col = NULL,
                                                      ppg_col = NULL,
                                                      peaks = NULL,
                                                      window_s = c(-0.25, 0.45),
                                                      sampling_rate_hz = NULL,
                                                      n_grid = 101,
                                                      similarity_threshold = 0.80) {
  if (is.numeric(data) && is.null(dim(data))) {
    ppg <- as.numeric(data)
    if (is.null(sampling_rate_hz)) {
      sampling_rate_hz <- 50
    }
    time <- seq_along(ppg) / sampling_rate_hz
  } else {
    .gp_exact_check_df(data)
    if (is.null(time_col)) {
      time_col <- .gp_exact_guess_col(data, .gp_exact_default_dictionary()$time_s, "time", FALSE)
    }
    if (is.null(ppg_col)) {
      ppg_col <- .gp_exact_guess_col(data, .gp_exact_default_dictionary()$PPG, "PPG", TRUE)
    }
    ppg <- suppressWarnings(as.numeric(data[[ppg_col]]))
    if (!is.null(time_col) && time_col %in% names(data)) {
      time <- .gp_exact_time_seconds(data[[time_col]])
    } else {
      if (is.null(sampling_rate_hz)) {
        sampling_rate_hz <- 50
      }
      time <- seq_along(ppg) / sampling_rate_hz
    }
  }

  dt <- stats::median(diff(time), na.rm = TRUE)
  if (!is.finite(dt) || dt <= 0) {
    dt <- if (!is.null(sampling_rate_hz)) 1 / sampling_rate_hz else 0.02
  }

  if (is.null(peaks)) {
    peak_idx <- .gp_exact_local_peaks(ppg, min_distance = max(1L, round(0.30 / dt)))
  } else {
    peaks <- suppressWarnings(as.numeric(peaks))
    if (all(is.finite(peaks) & peaks >= 1 & peaks <= length(ppg) & abs(peaks - round(peaks)) < 1e-8)) {
      peak_idx <- as.integer(round(peaks))
    } else {
      peak_idx <- vapply(peaks, function(z) which.min(abs(time - z)), integer(1))
    }
  }

  grid <- seq(window_s[1L], window_s[2L], length.out = n_grid)
  windows <- matrix(NA_real_, nrow = length(peak_idx), ncol = n_grid)
  keep <- rep(FALSE, length(peak_idx))

  for (i in seq_along(peak_idx)) {
    p <- peak_idx[i]
    rel <- time - time[p]
    idx <- which(rel >= window_s[1L] & rel <= window_s[2L] & is.finite(ppg))

    if (length(idx) < 5L) {
      next
    }

    ord <- order(rel[idx])
    xx <- rel[idx][ord]
    yy <- ppg[idx][ord]

    yy <- yy - mean(yy, na.rm = TRUE)
    sc <- stats::sd(yy, na.rm = TRUE)
    if (is.finite(sc) && sc > 0) {
      yy <- yy / sc
    }

    windows[i, ] <- stats::approx(xx, yy, xout = grid, rule = 2, ties = mean)$y
    keep[i] <- all(is.finite(windows[i, ]))
  }

  windows <- windows[keep, , drop = FALSE]
  peak_idx <- peak_idx[keep]

  if (!NROW(windows)) {
    empty <- data.frame()
    return(list(
      beats = empty,
      template = data.frame(relative_time_s = grid, template = NA_real_),
      summary = data.frame(n_beats = 0L, mean_similarity = NA_real_, quality_ok_ratio = NA_real_),
      settings = list(window_s = window_s, n_grid = n_grid, similarity_threshold = similarity_threshold)
    ))
  }

  template <- apply(windows, 2L, stats::median, na.rm = TRUE)
  similarity <- apply(windows, 1L, function(z) suppressWarnings(stats::cor(z, template, use = "complete.obs")))

  beats <- data.frame(
    beat_id = seq_along(peak_idx),
    peak_index = peak_idx,
    peak_time = time[peak_idx],
    template_similarity = similarity,
    quality_ok = is.finite(similarity) & similarity >= similarity_threshold,
    stringsAsFactors = FALSE
  )

  summary <- data.frame(
    n_beats = nrow(beats),
    mean_similarity = mean(similarity, na.rm = TRUE),
    median_similarity = stats::median(similarity, na.rm = TRUE),
    min_similarity = min(similarity, na.rm = TRUE),
    quality_ok_ratio = mean(beats$quality_ok, na.rm = TRUE),
    stringsAsFactors = FALSE
  )

  list(
    beats = beats,
    template = data.frame(relative_time_s = grid, template = template),
    summary = summary,
    settings = list(window_s = window_s, n_grid = n_grid, similarity_threshold = similarity_threshold)
  )
}

#' Compute a simple Haar-style HRV wavelet PSD summary
#'
#' Computes a conservative Haar-style multiscale power summary for RR/NN
#' intervals. This is intended as a lightweight, CRAN-safe exploratory
#' nonstationary-HRV helper, not as a replacement for specialist HRV packages.
#'
#' @param rr_intervals Numeric RR/NN intervals in milliseconds or seconds.
#' @param time Optional timestamps for intervals.
#' @param bands Named list of frequency bands in Hz.
#' @param max_scale Optional maximum Haar scale in beats.
#'
#' @return List with `psd`, `band_power`, and `settings`.
#' @export
compute_gazepoint_hrv_wavelet_psd <- function(rr_intervals,
                                              time = NULL,
                                              bands = list(
                                                vlf = c(0.0033, 0.04),
                                                lf = c(0.04, 0.15),
                                                hf = c(0.15, 0.40)
                                              ),
                                              max_scale = NULL) {
  rr <- suppressWarnings(as.numeric(rr_intervals))
  rr <- rr[is.finite(rr)]

  if (length(rr) < 8L) {
    stop("At least 8 finite RR/NN intervals are required.", call. = FALSE)
  }

  if (stats::median(rr, na.rm = TRUE) > 10) {
    rr_s <- rr / 1000
  } else {
    rr_s <- rr
  }

  x <- rr_s - mean(rr_s, na.rm = TRUE)
  n <- length(x)

  if (is.null(max_scale)) {
    max_scale <- 2^floor(log2(max(2L, floor(n / 4L))))
  }

  scales <- 2^(0:floor(log2(max_scale)))
  scales <- scales[scales >= 1L & scales * 2L <= n]

  rows <- vector("list", length(scales))

  median_rr_s <- stats::median(rr_s, na.rm = TRUE)

  for (i in seq_along(scales)) {
    s <- scales[i]
    coeff <- numeric()

    for (k in seq_len(n - 2L * s + 1L)) {
      left <- mean(x[k:(k + s - 1L)], na.rm = TRUE)
      right <- mean(x[(k + s):(k + 2L * s - 1L)], na.rm = TRUE)
      coeff <- c(coeff, left - right)
    }

    pseudo_frequency <- if (is.finite(median_rr_s) && median_rr_s > 0) {
      1 / (2 * s * median_rr_s)
    } else {
      NA_real_
    }

    rows[[i]] <- data.frame(
      scale_beats = s,
      pseudo_frequency_hz = pseudo_frequency,
      period_beats = 2 * s,
      n_coefficients = length(coeff),
      wavelet_power = mean(coeff^2, na.rm = TRUE) / 2,
      stringsAsFactors = FALSE
    )
  }

  psd <- do.call(rbind, rows)
  row.names(psd) <- NULL

  band_rows <- vector("list", length(bands))
  for (i in seq_along(bands)) {
    band <- bands[[i]]
    in_band <- psd$pseudo_frequency_hz >= band[1L] & psd$pseudo_frequency_hz < band[2L]
    band_rows[[i]] <- data.frame(
      band = names(bands)[i],
      low_hz = band[1L],
      high_hz = band[2L],
      n_scales = sum(in_band, na.rm = TRUE),
      band_power = sum(psd$wavelet_power[in_band], na.rm = TRUE),
      stringsAsFactors = FALSE
    )
  }

  band_power <- do.call(rbind, band_rows)
  row.names(band_power) <- NULL

  list(
    psd = psd,
    band_power = band_power,
    settings = list(
      interval_unit = ifelse(stats::median(rr_intervals, na.rm = TRUE) > 10, "ms", "s"),
      method = "haar_style_multiscale_power",
      max_scale = max(scales, na.rm = TRUE)
    )
  )
}

