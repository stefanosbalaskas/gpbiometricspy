#' Recommend Gazepoint biometric exclusions
#'
#' Creates window-level and participant-level exclusion recommendations from
#' Gazepoint biometric usable-sample summaries. The function does not remove
#' data. It only creates transparent keep, review, or exclude recommendations.
#'
#' @param data A row-level Gazepoint Biometrics data frame, a path to a
#'   Gazepoint CSV export, or an already summarised multimodal window table.
#' @param group_columns Columns defining analysis windows when `data` is
#'   row-level, such as `c("source_participant", "MEDIA_ID")`.
#' @param data_is_window_summary Logical. If `TRUE`, `data` is treated as an
#'   already summarised window table.
#' @param participant_column Optional participant identifier column. If `NULL`,
#'   the function tries `source_participant`, `USER`, and `USERID`.
#' @param gsr_min_usable_pct Minimum acceptable usable percentage for GSR/EDA.
#' @param hr_min_usable_pct Minimum acceptable usable percentage for heart rate.
#' @param dial_min_usable_pct Minimum acceptable usable percentage for
#'   engagement dial.
#' @param require_gsr Should low GSR/EDA coverage cause exclusion rather than
#'   review?
#' @param require_hr Should low heart-rate coverage cause exclusion rather than
#'   review?
#' @param require_dial Should low engagement-dial coverage cause exclusion
#'   rather than review?
#'
#' @return A list with `overview`, `window_recommendations`,
#'   `participant_recommendations`, and `settings`.
#'
#' @export
recommend_gazepoint_biometric_exclusions <- function(data,
                                                     group_columns = NULL,
                                                     data_is_window_summary = FALSE,
                                                     participant_column = NULL,
                                                     gsr_min_usable_pct = 50,
                                                     hr_min_usable_pct = 50,
                                                     dial_min_usable_pct = 50,
                                                     require_gsr = TRUE,
                                                     require_hr = TRUE,
                                                     require_dial = FALSE) {
  if (isTRUE(data_is_window_summary)) {
    windows <- data

    if (!is.data.frame(windows)) {
      stop(
        "`data` must be a data frame when `data_is_window_summary = TRUE`.",
        call. = FALSE
      )
    }
  } else {
    dat <- coerce_gazepoint_biometrics_data(data)

    if (is.null(group_columns) || length(group_columns) == 0L) {
      stop(
        "`group_columns` must be supplied when `data` is row-level.",
        call. = FALSE
      )
    }

    missing_groups <- setdiff(group_columns, names(dat))

    if (length(missing_groups) > 0L) {
      stop(
        "`group_columns` were not found in `data`: ",
        paste(missing_groups, collapse = ", "),
        call. = FALSE
      )
    }

    windows <- summarise_gazepoint_multimodal_windows(
      data = dat,
      group_columns = group_columns
    )
  }

  required_summary_columns <- c(
    "gsr_usable_pct",
    "hr_usable_pct",
    "dial_usable_pct"
  )

  missing_summary_columns <- setdiff(required_summary_columns, names(windows))

  if (length(missing_summary_columns) > 0L) {
    stop(
      "`data` does not look like a multimodal biometric window summary. ",
      "Missing columns: ",
      paste(missing_summary_columns, collapse = ", "),
      call. = FALSE
    )
  }

  if (is.null(participant_column)) {
    participant_column <- infer_biometric_participant_column(windows)
  }

  window_recommendations <- create_biometric_window_recommendations(
    windows = windows,
    gsr_min_usable_pct = gsr_min_usable_pct,
    hr_min_usable_pct = hr_min_usable_pct,
    dial_min_usable_pct = dial_min_usable_pct,
    require_gsr = require_gsr,
    require_hr = require_hr,
    require_dial = require_dial
  )

  participant_recommendations <- create_biometric_participant_recommendations(
    window_recommendations = window_recommendations,
    participant_column = participant_column
  )

  overview <- data.frame(
    n_windows = nrow(window_recommendations),
    keep_windows = sum(window_recommendations$recommendation == "keep"),
    review_windows = sum(window_recommendations$recommendation == "review"),
    exclude_windows = sum(window_recommendations$recommendation == "exclude"),
    participant_column = ifelse(is.na(participant_column), NA_character_, participant_column),
    n_participants = ifelse(
      nrow(participant_recommendations) > 0L,
      nrow(participant_recommendations),
      NA_integer_
    ),
    stringsAsFactors = FALSE
  )

  settings <- data.frame(
    gsr_min_usable_pct = gsr_min_usable_pct,
    hr_min_usable_pct = hr_min_usable_pct,
    dial_min_usable_pct = dial_min_usable_pct,
    require_gsr = require_gsr,
    require_hr = require_hr,
    require_dial = require_dial,
    stringsAsFactors = FALSE
  )

  out <- list(
    overview = overview,
    window_recommendations = window_recommendations,
    participant_recommendations = participant_recommendations,
    settings = settings
  )

  class(out) <- c("gazepoint_biometric_exclusion_recommendations", "list")
  out
}


infer_biometric_participant_column <- function(data) {
  candidates <- c("source_participant", "USER", "USERID", "participant", "subject")

  present <- intersect(candidates, names(data))

  if (length(present) == 0L) {
    return(NA_character_)
  }

  present[1]
}


create_biometric_window_recommendations <- function(windows,
                                                    gsr_min_usable_pct,
                                                    hr_min_usable_pct,
                                                    dial_min_usable_pct,
                                                    require_gsr,
                                                    require_hr,
                                                    require_dial) {
  out <- windows

  out$low_gsr_usable <- is_low_usable_pct(
    out$gsr_usable_pct,
    gsr_min_usable_pct
  )

  out$low_hr_usable <- is_low_usable_pct(
    out$hr_usable_pct,
    hr_min_usable_pct
  )

  out$low_dial_usable <- is_low_usable_pct(
    out$dial_usable_pct,
    dial_min_usable_pct
  )

  required_fail <- rep(FALSE, nrow(out))

  if (isTRUE(require_gsr)) {
    required_fail <- required_fail | out$low_gsr_usable
  }

  if (isTRUE(require_hr)) {
    required_fail <- required_fail | out$low_hr_usable
  }

  if (isTRUE(require_dial)) {
    required_fail <- required_fail | out$low_dial_usable
  }

  optional_warn <- rep(FALSE, nrow(out))

  if (!isTRUE(require_gsr)) {
    optional_warn <- optional_warn | out$low_gsr_usable
  }

  if (!isTRUE(require_hr)) {
    optional_warn <- optional_warn | out$low_hr_usable
  }

  if (!isTRUE(require_dial)) {
    optional_warn <- optional_warn | out$low_dial_usable
  }

  out$recommendation <- ifelse(
    required_fail,
    "exclude",
    ifelse(optional_warn, "review", "keep")
  )

  out$recommendation_reason <- vapply(
    seq_len(nrow(out)),
    function(i) {
      reasons <- character(0)

      if (out$low_gsr_usable[i]) {
        reasons <- c(
          reasons,
          paste0("GSR/EDA usable coverage below ", gsr_min_usable_pct, "%")
        )
      }

      if (out$low_hr_usable[i]) {
        reasons <- c(
          reasons,
          paste0("Heart-rate usable coverage below ", hr_min_usable_pct, "%")
        )
      }

      if (out$low_dial_usable[i]) {
        reasons <- c(
          reasons,
          paste0("Engagement-dial usable coverage below ", dial_min_usable_pct, "%")
        )
      }

      if (length(reasons) == 0L) {
        return("usable biometric coverage acceptable")
      }

      paste(reasons, collapse = "; ")
    },
    character(1)
  )

  out
}


is_low_usable_pct <- function(x, threshold) {
  is.na(x) | x < threshold
}


create_biometric_participant_recommendations <- function(window_recommendations,
                                                         participant_column) {
  if (is.na(participant_column) || !participant_column %in% names(window_recommendations)) {
    return(data.frame(
      participant = character(0),
      n_windows = integer(0),
      keep_windows = integer(0),
      review_windows = integer(0),
      exclude_windows = integer(0),
      exclude_pct = numeric(0),
      participant_recommendation = character(0),
      stringsAsFactors = FALSE
    ))
  }

  participants <- unique(as.character(window_recommendations[[participant_column]]))

  rows <- lapply(participants, function(participant) {
    in_participant <- as.character(window_recommendations[[participant_column]]) == participant

    recommendations <- window_recommendations$recommendation[in_participant]

    n_windows <- length(recommendations)
    keep_windows <- sum(recommendations == "keep")
    review_windows <- sum(recommendations == "review")
    exclude_windows <- sum(recommendations == "exclude")

    participant_recommendation <- if (exclude_windows == n_windows) {
      "exclude"
    } else if (exclude_windows > 0L || review_windows > 0L) {
      "review"
    } else {
      "keep"
    }

    data.frame(
      participant = participant,
      n_windows = n_windows,
      keep_windows = keep_windows,
      review_windows = review_windows,
      exclude_windows = exclude_windows,
      exclude_pct = safe_pct(exclude_windows, n_windows),
      participant_recommendation = participant_recommendation,
      stringsAsFactors = FALSE
    )
  })

  out <- do.call(rbind, rows)
  rownames(out) <- NULL
  out
}
