#' Extract Gazepoint TTL marker events
#'
#' Extracts TTL marker events from Gazepoint Biometrics exports. The function
#' can return either rows where TTL marker values change or all nonzero TTL
#' rows. By default, rows are retained only when the TTL validity column is
#' present and greater than zero. This avoids treating invalid placeholder TTL
#' values as experimental events.
#'
#' @param data A data frame or a path to a Gazepoint CSV export.
#' @param ttl_columns TTL marker columns. If `NULL`, the function uses all
#'   available columns from `TTL0` to `TTL6`.
#' @param group_columns Optional grouping columns within which TTL changes are
#'   detected, such as `source_participant`, `USER`, or `MEDIA_ID`.
#' @param validity_column Optional TTL validity column. Defaults to `"TTLV"`.
#' @param require_validity Logical. Should rows be retained only when
#'   `validity_column` is present and greater than zero? Defaults to `TRUE`.
#' @param mode Event extraction mode. `"changes"` returns rows where TTL values
#'   change. `"nonzero"` returns all rows with nonzero TTL values.
#' @param include_initial Should the first valid, non-missing TTL value within
#'   each group be treated as an event when `mode = "changes"`?
#'
#' @return A data frame of TTL events.
#'
#' @export
extract_gazepoint_ttl_events <- function(data,
                                         ttl_columns = NULL,
                                         group_columns = NULL,
                                         validity_column = "TTLV",
                                         require_validity = TRUE,
                                         mode = c("changes", "nonzero"),
                                         include_initial = TRUE) {
  dat <- coerce_gazepoint_biometrics_data(data)
  mode <- match.arg(mode)

  if (is.null(ttl_columns)) {
    ttl_columns <- intersect(paste0("TTL", 0:6), names(dat))
  }

  if (length(ttl_columns) == 0L) {
    stop("No TTL columns were found in `data`.", call. = FALSE)
  }

  missing_ttl <- setdiff(ttl_columns, names(dat))

  if (length(missing_ttl) > 0L) {
    stop(
      "`ttl_columns` were not found in `data`: ",
      paste(missing_ttl, collapse = ", "),
      call. = FALSE
    )
  }

  if (!is.null(group_columns)) {
    missing_groups <- setdiff(group_columns, names(dat))

    if (length(missing_groups) > 0L) {
      stop(
        "`group_columns` were not found in `data`: ",
        paste(missing_groups, collapse = ", "),
        call. = FALSE
      )
    }

    group_key <- make_group_key(dat, group_columns)
  } else {
    group_key <- rep("all", nrow(dat))
  }

  time_columns <- intersect(c("CNT", "TIME", "TIME_TICK"), names(dat))

  validity_present <- !is.null(validity_column) &&
    length(validity_column) == 1L &&
    validity_column %in% names(dat)

  rows <- list()
  row_counter <- 0L

  for (key in unique(group_key)) {
    group_rows <- which(group_key == key)

    group_validity <- if (validity_present) {
      as_numeric_safe(dat[[validity_column]][group_rows])
    } else {
      rep(NA_real_, length(group_rows))
    }

    valid_mask <- if (isTRUE(require_validity)) {
      validity_present & !is.na(group_validity) & group_validity > 0
    } else {
      rep(TRUE, length(group_rows))
    }

    for (ttl_column in ttl_columns) {
      ttl_values <- as_numeric_safe(dat[[ttl_column]][group_rows])

      event_positions <- detect_ttl_event_positions(
        ttl_values = ttl_values,
        valid_mask = valid_mask,
        mode = mode,
        include_initial = include_initial
      )

      if (length(event_positions) == 0L) {
        next
      }

      for (event_position in event_positions) {
        source_row <- group_rows[event_position]
        row_counter <- row_counter + 1L

        previous_position <- find_previous_valid_ttl_position(
          ttl_values = ttl_values,
          valid_mask = valid_mask,
          current_position = event_position
        )

        previous_value <- if (!is.na(previous_position)) {
          ttl_values[previous_position]
        } else {
          NA_real_
        }

        base <- data.frame(
          row_index = source_row,
          event_order = row_counter,
          ttl_channel = ttl_column,
          ttl_value = ttl_values[event_position],
          previous_ttl_value = previous_value,
          stringsAsFactors = FALSE
        )

        if (!is.null(group_columns)) {
          base <- cbind(
            dat[source_row, group_columns, drop = FALSE],
            base,
            stringsAsFactors = FALSE
          )
        }

        if (length(time_columns) > 0L) {
          base <- cbind(
            base,
            dat[source_row, time_columns, drop = FALSE],
            stringsAsFactors = FALSE
          )
        }

        if (validity_present) {
          base$ttl_validity <- as_numeric_safe(dat[[validity_column]][source_row])
        } else {
          base$ttl_validity <- NA_real_
        }

        rows[[length(rows) + 1L]] <- base
      }
    }
  }

  if (length(rows) == 0L) {
    return(empty_ttl_events(group_columns, time_columns))
  }

  out <- do.call(rbind, rows)
  rownames(out) <- NULL
  out
}


detect_ttl_event_positions <- function(ttl_values,
                                       valid_mask,
                                       mode,
                                       include_initial) {
  present <- !is.na(ttl_values) & valid_mask

  if (mode == "nonzero") {
    return(which(present & ttl_values != 0))
  }

  event <- rep(FALSE, length(ttl_values))

  if (length(ttl_values) == 0L) {
    return(integer(0))
  }

  previous_valid_value <- NA_real_

  for (i in seq_along(ttl_values)) {
    if (!present[i]) {
      next
    }

    if (is.na(previous_valid_value)) {
      event[i] <- isTRUE(include_initial)
    } else {
      event[i] <- ttl_values[i] != previous_valid_value
    }

    previous_valid_value <- ttl_values[i]
  }

  which(event)
}


find_previous_valid_ttl_position <- function(ttl_values,
                                             valid_mask,
                                             current_position) {
  if (current_position <= 1L) {
    return(NA_integer_)
  }

  previous_positions <- seq_len(current_position - 1L)
  previous_positions <- previous_positions[
    valid_mask[previous_positions] & !is.na(ttl_values[previous_positions])
  ]

  if (length(previous_positions) == 0L) {
    return(NA_integer_)
  }

  previous_positions[length(previous_positions)]
}


empty_ttl_events <- function(group_columns,
                             time_columns) {
  out <- data.frame(
    row_index = integer(0),
    event_order = integer(0),
    ttl_channel = character(0),
    ttl_value = numeric(0),
    previous_ttl_value = numeric(0),
    stringsAsFactors = FALSE
  )

  if (!is.null(group_columns) && length(group_columns) > 0L) {
    groups <- as.data.frame(
      stats::setNames(
        replicate(length(group_columns), character(0), simplify = FALSE),
        group_columns
      ),
      stringsAsFactors = FALSE
    )

    out <- cbind(groups, out, stringsAsFactors = FALSE)
  }

  if (length(time_columns) > 0L) {
    times <- as.data.frame(
      stats::setNames(
        replicate(length(time_columns), numeric(0), simplify = FALSE),
        time_columns
      ),
      stringsAsFactors = FALSE
    )

    out <- cbind(out, times, stringsAsFactors = FALSE)
  }

  out$ttl_validity <- numeric(0)
  out
}
