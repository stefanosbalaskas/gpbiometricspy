#' Align Gazepoint biometric samples to TTL events
#'
#' Aligns biometric rows to TTL/event markers and returns event-relative time and
#' sample indices. The helper is conservative: TTL events are detected from
#' rising edges by default, validity flags are used when available, and no
#' physiological interpretation is added.
#'
#' @param data A data frame containing biometric samples.
#' @param ttl_cols Optional TTL marker columns. If `NULL`, the function first
#'   looks for `ttl_marker`, then raw `TTL0`-`TTL6` columns.
#' @param event_col Optional single user-specified event column. If supplied, it
#'   is used instead of automatic TTL-column detection.
#' @param ttl_valid_col Optional TTL validity column. If `NULL`, the function
#'   looks for `ttl_validity_flag` or `TTLV`.
#' @param time_col Optional time column. If `NULL`, common time-column names are
#'   detected automatically when present.
#' @param sample_col Optional sample/counter column. If `NULL`, `CNT`/`cnt` is
#'   used when present; otherwise row order is used.
#' @param group_cols Optional grouping columns. If `NULL`, the function uses
#'   available participant/stimulus/trial-like columns when present.
#' @param participant_col,stimulus_col,trial_col Optional explicit grouping
#'   columns to add to `group_cols`.
#' @param event_value Optional value(s) that define an active event. If `NULL`,
#'   non-zero numeric/logical values and non-empty character values are treated
#'   as active.
#' @param valid_values Values treated as valid in the TTL validity column.
#' @param event_edge Event-detection rule. `"rising"` keeps inactive-to-active
#'   transitions, `"change"` keeps changes among active event values, and
#'   `"active"` keeps every active sample.
#' @param pre_window_ms,post_window_ms Event window in milliseconds when a usable
#'   time column is available.
#' @param pre_window_samples,post_window_samples Event window in samples when no
#'   usable time column is available. If omitted, only the event sample is kept.
#' @param collapse_nearby_ms Optional minimum distance between retained events
#'   within a group, in milliseconds.
#' @param require_valid_ttl If `TRUE`, a detected TTL validity column must be
#'   active for a row to count as an event.
#'
#' @return A list with `overview`, `events`, `aligned_data`, and `settings`.
#' @export
align_gazepoint_biometrics_to_ttl <- function(data,
                                              ttl_cols = NULL,
                                              event_col = NULL,
                                              ttl_valid_col = NULL,
                                              time_col = NULL,
                                              sample_col = NULL,
                                              group_cols = NULL,
                                              participant_col = NULL,
                                              stimulus_col = NULL,
                                              trial_col = NULL,
                                              event_value = NULL,
                                              valid_values = c(TRUE, 1, "1"),
                                              event_edge = c("rising", "change", "active"),
                                              pre_window_ms = 1000,
                                              post_window_ms = 5000,
                                              pre_window_samples = NULL,
                                              post_window_samples = NULL,
                                              collapse_nearby_ms = 0,
                                              require_valid_ttl = TRUE) {
  event_edge <- match.arg(event_edge)

  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (!is.numeric(pre_window_ms) || length(pre_window_ms) != 1 || pre_window_ms < 0) {
    stop("`pre_window_ms` must be a single non-negative number.", call. = FALSE)
  }

  if (!is.numeric(post_window_ms) || length(post_window_ms) != 1 || post_window_ms < 0) {
    stop("`post_window_ms` must be a single non-negative number.", call. = FALSE)
  }

  if (!is.numeric(collapse_nearby_ms) ||
      length(collapse_nearby_ms) != 1 ||
      collapse_nearby_ms < 0) {
    stop("`collapse_nearby_ms` must be a single non-negative number.", call. = FALSE)
  }

  dat <- as.data.frame(data, stringsAsFactors = FALSE)
  dat$.gpbiometrics_row_id <- seq_len(nrow(dat))

  if (nrow(dat) == 0) {
    events <- ttl_alignment_empty_events(group_cols = character())
    aligned <- ttl_alignment_empty_aligned(dat)

    return(structure(
      list(
        overview = data.frame(
          input_rows = 0L,
          ttl_event_rows = 0L,
          aligned_rows = 0L,
          group_count = 0L,
          status = "empty_input",
          stringsAsFactors = FALSE
        ),
        events = events,
        aligned_data = aligned,
        settings = list(
          ttl_cols = ttl_cols,
          event_col = event_col,
          ttl_valid_col = ttl_valid_col,
          time_col = time_col,
          sample_col = sample_col,
          group_cols = group_cols,
          event_edge = event_edge,
          pre_window_ms = pre_window_ms,
          post_window_ms = post_window_ms,
          pre_window_samples = pre_window_samples,
          post_window_samples = post_window_samples,
          collapse_nearby_ms = collapse_nearby_ms,
          require_valid_ttl = require_valid_ttl
        )
      ),
      class = c("gazepoint_biometrics_ttl_alignment", "list")
    ))
  }

  names_dat <- names(dat)

  if (!is.null(event_col)) {
    if (!event_col %in% names_dat) {
      stop("`event_col` was not found in `data`.", call. = FALSE)
    }
    ttl_cols <- event_col
    event_source <- "user_event_col"
  } else {
    if (is.null(ttl_cols)) {
      ttl_cols <- ttl_alignment_infer_ttl_cols(names_dat)
    }

    if (length(ttl_cols) == 0) {
      stop(
        "No TTL/event columns were found. Supply `ttl_cols` or `event_col`.",
        call. = FALSE
      )
    }

    missing_ttl_cols <- setdiff(ttl_cols, names_dat)
    if (length(missing_ttl_cols) > 0) {
      stop(
        "`ttl_cols` not found in `data`: ",
        paste(missing_ttl_cols, collapse = ", "),
        call. = FALSE
      )
    }

    event_source <- "ttl_cols"
  }

  if (is.null(ttl_valid_col)) {
    ttl_valid_col <- ttl_alignment_first_existing(
      names_dat,
      c("ttl_validity_flag", "TTLV", "ttlv")
    )
  }

  if (!is.null(ttl_valid_col) && !ttl_valid_col %in% names_dat) {
    stop("`ttl_valid_col` was not found in `data`.", call. = FALSE)
  }

  if (is.null(time_col)) {
    time_col <- ttl_alignment_first_existing(
      names_dat,
      c(
        "time_ms", "timestamp_ms", "timestamp",
        "TIME", "Time", "time",
        "recording_time", "sample_time"
      )
    )
  }

  if (!is.null(time_col) && !time_col %in% names_dat) {
    stop("`time_col` was not found in `data`.", call. = FALSE)
  }

  if (is.null(sample_col)) {
    sample_col <- ttl_alignment_first_existing(names_dat, c("CNT", "cnt", "sample", "sample_index"))
  }

  if (!is.null(sample_col) && !sample_col %in% names_dat) {
    stop("`sample_col` was not found in `data`.", call. = FALSE)
  }

  group_cols <- ttl_alignment_resolve_group_cols(
    names_dat = names_dat,
    group_cols = group_cols,
    participant_col = participant_col,
    stimulus_col = stimulus_col,
    trial_col = trial_col
  )

  missing_group_cols <- setdiff(group_cols, names_dat)
  if (length(missing_group_cols) > 0) {
    stop(
      "`group_cols` not found in `data`: ",
      paste(missing_group_cols, collapse = ", "),
      call. = FALSE
    )
  }

  time_ms <- ttl_alignment_time_ms(dat, time_col)

  dat$.gpbiometrics_time_ms <- time_ms
  dat$.gpbiometrics_group_id <- ttl_alignment_group_id(dat, group_cols)

  order_value <- dat$.gpbiometrics_row_id
  if (!all(is.na(dat$.gpbiometrics_time_ms))) {
    order_value <- dat$.gpbiometrics_time_ms
  } else if (!is.null(sample_col)) {
    sample_numeric <- suppressWarnings(as.numeric(dat[[sample_col]]))
    if (!all(is.na(sample_numeric))) {
      order_value <- sample_numeric
    }
  }

  dat$.gpbiometrics_order_value <- order_value
  dat$.gpbiometrics_group_sample_index <- NA_integer_

  group_indices <- split(seq_len(nrow(dat)), dat$.gpbiometrics_group_id, drop = TRUE)

  for (idx in group_indices) {
    idx_ordered <- idx[order(dat$.gpbiometrics_order_value[idx], dat$.gpbiometrics_row_id[idx])]
    dat$.gpbiometrics_group_sample_index[idx_ordered] <- seq_along(idx_ordered)
  }

  active_info <- ttl_alignment_active_info(
    dat = dat,
    ttl_cols = ttl_cols,
    event_value = event_value
  )

  ttl_active <- active_info$active
  event_ttl_column <- active_info$event_ttl_column
  event_ttl_value <- active_info$event_ttl_value

  ttl_valid <- rep(TRUE, nrow(dat))

  if (!is.null(ttl_valid_col) && isTRUE(require_valid_ttl)) {
    ttl_valid <- ttl_alignment_valid(dat[[ttl_valid_col]], valid_values)
  }

  event_active <- ttl_active & ttl_valid

  event_rows <- integer()
  event_group_sequence <- integer()

  for (group_name in names(group_indices)) {
    idx <- group_indices[[group_name]]
    idx <- idx[order(dat$.gpbiometrics_order_value[idx], dat$.gpbiometrics_row_id[idx])]

    active_group <- event_active[idx]
    value_group <- event_ttl_value[idx]

    lag_active <- c(FALSE, utils::head(active_group, -1))
    lag_value <- c(NA_character_, utils::head(value_group, -1))

    is_event <- switch(
      event_edge,
      rising = active_group & !lag_active,
      change = active_group & (!lag_active | value_group != lag_value),
      active = active_group
    )

    candidate_rows <- idx[is_event]

    if (length(candidate_rows) > 1 &&
        collapse_nearby_ms > 0 &&
        !all(is.na(dat$.gpbiometrics_time_ms[candidate_rows]))) {
      keep <- rep(TRUE, length(candidate_rows))
      last_kept_time <- dat$.gpbiometrics_time_ms[candidate_rows[1]]

      for (i in seq_along(candidate_rows)[-1]) {
        current_time <- dat$.gpbiometrics_time_ms[candidate_rows[i]]

        if (!is.na(current_time) &&
            !is.na(last_kept_time) &&
            (current_time - last_kept_time) < collapse_nearby_ms) {
          keep[i] <- FALSE
        } else {
          last_kept_time <- current_time
        }
      }

      candidate_rows <- candidate_rows[keep]
    }

    if (length(candidate_rows) > 0) {
      event_rows <- c(event_rows, candidate_rows)
      event_group_sequence <- c(event_group_sequence, seq_along(candidate_rows))
    }
  }

  if (length(event_rows) == 0) {
    events <- ttl_alignment_empty_events(group_cols)
    aligned <- ttl_alignment_empty_aligned(dat)

    return(structure(
      list(
        overview = data.frame(
          input_rows = nrow(dat),
          ttl_event_rows = 0L,
          aligned_rows = 0L,
          group_count = length(group_indices),
          status = "no_ttl_events_detected",
          stringsAsFactors = FALSE
        ),
        events = events,
        aligned_data = aligned,
        settings = list(
          ttl_cols = ttl_cols,
          event_col = event_col,
          ttl_valid_col = ttl_valid_col,
          time_col = time_col,
          sample_col = sample_col,
          group_cols = group_cols,
          event_source = event_source,
          event_edge = event_edge,
          pre_window_ms = pre_window_ms,
          post_window_ms = post_window_ms,
          pre_window_samples = pre_window_samples,
          post_window_samples = post_window_samples,
          collapse_nearby_ms = collapse_nearby_ms,
          require_valid_ttl = require_valid_ttl
        )
      ),
      class = c("gazepoint_biometrics_ttl_alignment", "list")
    ))
  }

  event_rows <- event_rows[order(
    dat$.gpbiometrics_group_id[event_rows],
    dat$.gpbiometrics_order_value[event_rows],
    dat$.gpbiometrics_row_id[event_rows]
  )]

  event_group_sequence <- stats::ave(
    seq_along(event_rows),
    dat$.gpbiometrics_group_id[event_rows],
    FUN = seq_along
  )

  events <- data.frame(
    ttl_event_id = paste0("ttl_event_", seq_along(event_rows)),
    ttl_event_sequence = as.integer(event_group_sequence),
    event_row_id = dat$.gpbiometrics_row_id[event_rows],
    event_group_id = dat$.gpbiometrics_group_id[event_rows],
    event_group_sample_index = dat$.gpbiometrics_group_sample_index[event_rows],
    event_time_ms = dat$.gpbiometrics_time_ms[event_rows],
    event_ttl_column = event_ttl_column[event_rows],
    event_ttl_value = event_ttl_value[event_rows],
    stringsAsFactors = FALSE
  )

  if (length(group_cols) > 0) {
    events <- cbind(dat[event_rows, group_cols, drop = FALSE], events)
  }

  aligned_parts <- vector("list", nrow(events))

  for (i in seq_len(nrow(events))) {
    event_group_id <- events$event_group_id[i]
    group_rows <- which(dat$.gpbiometrics_group_id == event_group_id)

    event_row <- event_rows[i]
    event_sample_index <- dat$.gpbiometrics_group_sample_index[event_row]
    rel_sample <- dat$.gpbiometrics_group_sample_index[group_rows] - event_sample_index

    event_time <- dat$.gpbiometrics_time_ms[event_row]
    rel_time <- dat$.gpbiometrics_time_ms[group_rows] - event_time

    if (!all(is.na(rel_time)) && !is.na(event_time)) {
      keep_rows <- rel_time >= -pre_window_ms & rel_time <= post_window_ms
      keep_rows[is.na(keep_rows)] <- FALSE
    } else {
      pre_s <- if (is.null(pre_window_samples)) 0 else pre_window_samples
      post_s <- if (is.null(post_window_samples)) 0 else post_window_samples

      if (!is.numeric(pre_s) || length(pre_s) != 1 || pre_s < 0) {
        stop("`pre_window_samples` must be `NULL` or a single non-negative number.", call. = FALSE)
      }

      if (!is.numeric(post_s) || length(post_s) != 1 || post_s < 0) {
        stop("`post_window_samples` must be `NULL` or a single non-negative number.", call. = FALSE)
      }

      keep_rows <- rel_sample >= -pre_s & rel_sample <= post_s
    }

    kept_group_rows <- group_rows[keep_rows]

    if (length(kept_group_rows) == 0) {
      next
    }

    aligned_i <- dat[kept_group_rows, , drop = FALSE]
    aligned_i$ttl_event_id <- events$ttl_event_id[i]
    aligned_i$ttl_event_sequence <- events$ttl_event_sequence[i]
    aligned_i$event_row_id <- events$event_row_id[i]
    aligned_i$event_group_sample_index <- events$event_group_sample_index[i]
    aligned_i$event_time_ms <- events$event_time_ms[i]
    aligned_i$event_ttl_column <- events$event_ttl_column[i]
    aligned_i$event_ttl_value <- events$event_ttl_value[i]
    aligned_i$event_relative_sample_index <- rel_sample[keep_rows]
    aligned_i$event_relative_time_ms <- rel_time[keep_rows]
    aligned_i$event_window_position <- ifelse(
      aligned_i$event_relative_sample_index < 0,
      "pre_event",
      ifelse(aligned_i$event_relative_sample_index == 0, "event", "post_event")
    )
    aligned_i$within_pre_event_window <- aligned_i$event_relative_sample_index < 0
    aligned_i$within_post_event_window <- aligned_i$event_relative_sample_index > 0
    aligned_i$ttl_alignment_status <- "aligned"

    aligned_parts[[i]] <- aligned_i
  }

  aligned <- do.call(rbind, aligned_parts)

  if (is.null(aligned)) {
    aligned <- ttl_alignment_empty_aligned(dat)
    status <- "ttl_events_detected_no_rows_aligned"
  } else {
    rownames(aligned) <- NULL
    status <- "ttl_events_aligned"
  }

  internal_cols <- c(
    ".gpbiometrics_group_id",
    ".gpbiometrics_order_value"
  )

  aligned <- aligned[, setdiff(names(aligned), internal_cols), drop = FALSE]

  events$event_group_id <- NULL

  structure(
    list(
      overview = data.frame(
        input_rows = nrow(dat),
        ttl_event_rows = nrow(events),
        aligned_rows = nrow(aligned),
        group_count = length(group_indices),
        status = status,
        stringsAsFactors = FALSE
      ),
      events = events,
      aligned_data = aligned,
      settings = list(
        ttl_cols = ttl_cols,
        event_col = event_col,
        ttl_valid_col = ttl_valid_col,
        time_col = time_col,
        sample_col = sample_col,
        group_cols = group_cols,
        event_source = event_source,
        event_edge = event_edge,
        pre_window_ms = pre_window_ms,
        post_window_ms = post_window_ms,
        pre_window_samples = pre_window_samples,
        post_window_samples = post_window_samples,
        collapse_nearby_ms = collapse_nearby_ms,
        require_valid_ttl = require_valid_ttl
      )
    ),
    class = c("gazepoint_biometrics_ttl_alignment", "list")
  )
}

ttl_alignment_first_existing <- function(names_dat, candidates) {
  exact <- candidates[candidates %in% names_dat]
  if (length(exact) > 0) {
    return(exact[1])
  }

  lower_names <- tolower(names_dat)
  lower_candidates <- tolower(candidates)
  idx <- match(lower_candidates, lower_names)
  idx <- idx[!is.na(idx)]

  if (length(idx) > 0) {
    return(names_dat[idx[1]])
  }

  NULL
}

ttl_alignment_infer_ttl_cols <- function(names_dat) {
  marker <- ttl_alignment_first_existing(names_dat, c("ttl_marker"))

  if (!is.null(marker)) {
    return(marker)
  }

  raw_ttl <- grep("^TTL[0-6]$", names_dat, value = TRUE, ignore.case = TRUE)
  raw_ttl <- raw_ttl[order(tolower(raw_ttl))]

  raw_ttl
}

ttl_alignment_resolve_group_cols <- function(names_dat,
                                             group_cols,
                                             participant_col,
                                             stimulus_col,
                                             trial_col) {
  explicit_cols <- c(participant_col, stimulus_col, trial_col)
  explicit_cols <- explicit_cols[!is.null(explicit_cols)]

  if (!is.null(group_cols)) {
    return(unique(c(group_cols, explicit_cols)))
  }

  participant <- ttl_alignment_first_existing(
    names_dat,
    c("participant", "subject", "subject_id", "USER", "USER_FILE", "user_file")
  )

  stimulus <- ttl_alignment_first_existing(
    names_dat,
    c("stimulus", "stimulus_id", "MEDIA_ID", "MEDIA_NAME", "media_id", "media_name")
  )

  trial <- ttl_alignment_first_existing(
    names_dat,
    c("trial", "trial_id", "TRIAL", "trial_global")
  )

  unique(stats::na.omit(c(explicit_cols, participant, stimulus, trial)))
}

ttl_alignment_group_id <- function(dat, group_cols) {
  if (length(group_cols) == 0) {
    return(rep("all", nrow(dat)))
  }

  group_dat <- dat[group_cols]
  group_dat[] <- lapply(group_dat, function(x) {
    x_chr <- as.character(x)
    x_chr[is.na(x_chr)] <- "<NA>"
    x_chr
  })

  apply(group_dat, 1, paste, collapse = "||")
}

ttl_alignment_time_ms <- function(dat, time_col) {
  if (is.null(time_col)) {
    return(rep(NA_real_, nrow(dat)))
  }

  time_numeric <- suppressWarnings(as.numeric(dat[[time_col]]))

  if (all(is.na(time_numeric))) {
    return(rep(NA_real_, nrow(dat)))
  }

  diffs <- diff(time_numeric)
  diffs <- diffs[is.finite(diffs) & diffs > 0]

  if (length(diffs) == 0) {
    return(time_numeric)
  }

  median_diff <- stats::median(diffs, na.rm = TRUE)

  # Gazepoint-like seconds often have frame steps around .016 at 60 Hz.
  # Larger numeric steps are kept as milliseconds/input-ms scale.
  if (is.finite(median_diff) && median_diff > 0 && median_diff <= 0.25) {
    return(time_numeric * 1000)
  }

  time_numeric
}

ttl_alignment_active <- function(x, event_value = NULL) {
  if (!is.null(event_value)) {
    return(!is.na(x) & as.character(x) %in% as.character(event_value))
  }

  if (is.logical(x)) {
    return(!is.na(x) & x)
  }

  if (is.numeric(x)) {
    return(!is.na(x) & x != 0)
  }

  x_chr <- trimws(as.character(x))
  x_chr[is.na(x_chr)] <- ""

  x_num <- suppressWarnings(as.numeric(x_chr))
  non_empty <- x_chr != ""

  if (sum(!is.na(x_num) & non_empty) >= max(1, sum(non_empty) / 2)) {
    return(!is.na(x_num) & x_num != 0)
  }

  non_empty & !toupper(x_chr) %in% c("0", "FALSE", "F", "NA", "NAN", "NULL")
}

ttl_alignment_valid <- function(x, valid_values) {
  if (is.null(valid_values)) {
    return(ttl_alignment_active(x))
  }

  !is.na(x) & as.character(x) %in% as.character(valid_values)
}

ttl_alignment_active_info <- function(dat, ttl_cols, event_value) {
  active_mat <- sapply(
    ttl_cols,
    function(col) ttl_alignment_active(dat[[col]], event_value = event_value)
  )

  if (is.null(dim(active_mat))) {
    active_mat <- matrix(active_mat, ncol = 1)
    colnames(active_mat) <- ttl_cols
  }

  active <- rowSums(active_mat, na.rm = TRUE) > 0

  event_ttl_column <- rep(NA_character_, nrow(dat))
  event_ttl_value <- rep(NA_character_, nrow(dat))

  for (i in seq_len(nrow(dat))) {
    active_cols <- ttl_cols[active_mat[i, ]]

    if (length(active_cols) > 0) {
      event_ttl_column[i] <- paste(active_cols, collapse = ";")
      event_ttl_value[i] <- paste(
        paste0(active_cols, "=", as.character(dat[i, active_cols, drop = TRUE])),
        collapse = ";"
      )
    }
  }

  list(
    active = active,
    event_ttl_column = event_ttl_column,
    event_ttl_value = event_ttl_value
  )
}

ttl_alignment_empty_events <- function(group_cols) {
  base <- data.frame(stringsAsFactors = FALSE)

  if (length(group_cols) > 0) {
    for (col in group_cols) {
      base[[col]] <- character()
    }
  }

  base$ttl_event_id <- character()
  base$ttl_event_sequence <- integer()
  base$event_row_id <- integer()
  base$event_group_sample_index <- integer()
  base$event_time_ms <- numeric()
  base$event_ttl_column <- character()
  base$event_ttl_value <- character()

  base
}

ttl_alignment_empty_aligned <- function(dat) {
  aligned <- dat[0, , drop = FALSE]
  aligned$ttl_event_id <- character()
  aligned$ttl_event_sequence <- integer()
  aligned$event_row_id <- integer()
  aligned$event_group_sample_index <- integer()
  aligned$event_time_ms <- numeric()
  aligned$event_ttl_column <- character()
  aligned$event_ttl_value <- character()
  aligned$event_relative_sample_index <- integer()
  aligned$event_relative_time_ms <- numeric()
  aligned$event_window_position <- character()
  aligned$within_pre_event_window <- logical()
  aligned$within_post_event_window <- logical()
  aligned$ttl_alignment_status <- character()

  internal_cols <- c(
    ".gpbiometrics_group_id",
    ".gpbiometrics_order_value"
  )

  aligned[, setdiff(names(aligned), internal_cols), drop = FALSE]
}
