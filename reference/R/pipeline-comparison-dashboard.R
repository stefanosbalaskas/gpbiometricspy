#' Create a static Gazepoint pipeline comparison dashboard
#'
#' @description
#' Aggregates participant-, session-, or row-level Gazepoint QC outputs into a
#' compact static dashboard object. The function is intentionally conservative:
#' it summarizes existing QC indicators, missingness rates, signal-quality scores,
#' rule failures, exclusion flags, and audit notes without fitting models, making
#' clinical claims, or launching an interactive dashboard.
#'
#' @param data A data frame containing QC, quality, missingness, exclusion, or
#'   audit-summary columns.
#' @param participant_col Optional participant identifier column. If `NULL`, a
#'   common participant column is detected when available.
#' @param session_col Optional session identifier column. If `NULL`, a common
#'   session column is detected when available.
#' @param grouping_cols Optional character vector of grouping columns. If supplied,
#'   this overrides `participant_col` and `session_col`.
#' @param missingness_col Optional numeric missingness-rate column.
#' @param quality_col Optional numeric quality-score or SQI column.
#' @param qc_status_col Optional QC status column.
#' @param failed_rules_col Optional column containing failed rule labels.
#' @param excluded_col Optional logical, numeric, or character exclusion flag column.
#' @param notes_col Optional audit-note column.
#'
#' @return A list with class `gazepoint_pipeline_comparison_dashboard` containing
#'   an overall summary, grouped dashboard table, issue table, and detected column
#'   mapping.
#'
#' @export
pipeline_comparison_dashboard <- function(data,
                                          participant_col = NULL,
                                          session_col = NULL,
                                          grouping_cols = NULL,
                                          missingness_col = NULL,
                                          quality_col = NULL,
                                          qc_status_col = NULL,
                                          failed_rules_col = NULL,
                                          excluded_col = NULL,
                                          notes_col = NULL) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }
  if (nrow(data) == 0L) {
    stop("`data` must contain at least one row.", call. = FALSE)
  }

  pick_column <- function(requested, candidates) {
    if (!is.null(requested)) {
      if (!is.character(requested) || length(requested) != 1L || is.na(requested) || !nzchar(requested)) {
        stop("Column arguments must be non-empty character scalars when supplied.", call. = FALSE)
      }
      if (!requested %in% names(data)) {
        stop(paste0("Column not found in `data`: ", requested), call. = FALSE)
      }
      return(requested)
    }
    hit <- candidates[candidates %in% names(data)]
    if (length(hit)) hit[[1L]] else NULL
  }

  collapse_unique <- function(x) {
    x <- as.character(x)
    x <- x[!is.na(x) & nzchar(x)]
    x <- unique(x)
    if (length(x)) paste(x, collapse = "; ") else NA_character_
  }

  mean_or_na <- function(x) {
    x <- suppressWarnings(as.numeric(x))
    if (all(is.na(x))) NA_real_ else mean(x, na.rm = TRUE)
  }

  flag_to_logical <- function(x) {
    if (is.logical(x)) {
      return(ifelse(is.na(x), FALSE, x))
    }
    if (is.numeric(x)) {
      return(ifelse(is.na(x), FALSE, x != 0))
    }
    x <- tolower(trimws(as.character(x)))
    x %in% c("true", "t", "yes", "y", "1", "exclude", "excluded", "reject", "rejected")
  }

  participant_col <- pick_column(
    participant_col,
    c("participant_id", "participant", "subject_id", "subject", "sub", "id")
  )
  session_col <- pick_column(
    session_col,
    c("session_id", "session", "visit", "recording", "run")
  )
  missingness_col <- pick_column(
    missingness_col,
    c("missingness_rate", "missing_rate", "prop_missing", "pct_missing", "percent_missing")
  )
  quality_col <- pick_column(
    quality_col,
    c("quality_index", "quality_score", "signal_quality", "sqi", "mean_sqi")
  )
  qc_status_col <- pick_column(
    qc_status_col,
    c("qc_status", "quality_status", "status", "decision", "recommendation")
  )
  failed_rules_col <- pick_column(
    failed_rules_col,
    c("failed_rules", "failing_rules", "rule_failures", "failed_checks", "flags")
  )
  excluded_col <- pick_column(
    excluded_col,
    c("excluded", "exclude", "exclusion_recommended", "recommended_exclusion", "remove")
  )
  notes_col <- pick_column(
    notes_col,
    c("audit_notes", "notes", "note", "comment", "comments")
  )

  if (!is.null(grouping_cols)) {
    if (!is.character(grouping_cols) || anyNA(grouping_cols) || any(!nzchar(grouping_cols))) {
      stop("`grouping_cols` must be a character vector of column names.", call. = FALSE)
    }
    missing_grouping <- setdiff(grouping_cols, names(data))
    if (length(missing_grouping)) {
      stop(paste0("Grouping columns not found in `data`: ", paste(missing_grouping, collapse = ", ")), call. = FALSE)
    }
  } else {
    grouping_cols <- c(participant_col, session_col)
    grouping_cols <- grouping_cols[!is.null(grouping_cols) & !is.na(grouping_cols)]
  }

  if (!length(grouping_cols)) {
    groups <- list(all_data = seq_len(nrow(data)))
  } else {
    group_df <- data[grouping_cols]
    group_df[] <- lapply(group_df, function(z) {
      z <- as.character(z)
      z[is.na(z) | !nzchar(z)] <- "NA"
      z
    })
    group_keys <- apply(group_df, 1L, paste, collapse = " | ")
    groups <- split(seq_len(nrow(data)), group_keys)
  }

  rows <- lapply(names(groups), function(key) {
    idx <- groups[[key]]
    out <- data.frame(
      group = key,
      n_rows = length(idx),
      missingness_rate = if (!is.null(missingness_col)) mean_or_na(data[[missingness_col]][idx]) else NA_real_,
      quality_score = if (!is.null(quality_col)) mean_or_na(data[[quality_col]][idx]) else NA_real_,
      qc_status = if (!is.null(qc_status_col)) collapse_unique(data[[qc_status_col]][idx]) else NA_character_,
      failed_rules = if (!is.null(failed_rules_col)) collapse_unique(data[[failed_rules_col]][idx]) else NA_character_,
      n_flagged_rows = if (!is.null(failed_rules_col)) {
        sum(!is.na(data[[failed_rules_col]][idx]) & nzchar(as.character(data[[failed_rules_col]][idx])))
      } else {
        NA_integer_
      },
      n_excluded_rows = if (!is.null(excluded_col)) {
        sum(flag_to_logical(data[[excluded_col]][idx]))
      } else {
        NA_integer_
      },
      audit_notes = if (!is.null(notes_col)) collapse_unique(data[[notes_col]][idx]) else NA_character_,
      stringsAsFactors = FALSE
    )
    if (length(grouping_cols)) {
      for (g in grouping_cols) {
        out[[g]] <- collapse_unique(data[[g]][idx])
      }
      out <- out[c("group", grouping_cols, setdiff(names(out), c("group", grouping_cols)))]
    }
    out
  })

  dashboard <- do.call(rbind, rows)
  status_text <- tolower(ifelse(is.na(dashboard$qc_status), "", dashboard$qc_status))
  bad_status <- grepl("reject|fail|bad|warn|exclude|review", status_text)
  has_failed_rules <- !is.na(dashboard$failed_rules) & nzchar(dashboard$failed_rules)
  has_exclusions <- !is.na(dashboard$n_excluded_rows) & dashboard$n_excluded_rows > 0L
  dashboard$has_issue <- bad_status | has_failed_rules | has_exclusions

  issues <- dashboard[dashboard$has_issue, , drop = FALSE]

  overall <- data.frame(
    n_groups = nrow(dashboard),
    n_rows = nrow(data),
    n_issue_groups = sum(dashboard$has_issue, na.rm = TRUE),
    mean_missingness_rate = mean_or_na(dashboard$missingness_rate),
    mean_quality_score = mean_or_na(dashboard$quality_score),
    n_excluded_rows = if (all(is.na(dashboard$n_excluded_rows))) NA_integer_ else sum(dashboard$n_excluded_rows, na.rm = TRUE),
    stringsAsFactors = FALSE
  )

  columns <- data.frame(
    role = c("participant", "session", "missingness", "quality", "qc_status", "failed_rules", "excluded", "notes"),
    column = c(participant_col, session_col, missingness_col, quality_col, qc_status_col, failed_rules_col, excluded_col, notes_col),
    stringsAsFactors = FALSE
  )

  out <- list(
    overall = overall,
    dashboard = dashboard,
    issues = issues,
    columns = columns
  )
  class(out) <- "gazepoint_pipeline_comparison_dashboard"
  out
}

#' @export
print.gazepoint_pipeline_comparison_dashboard <- function(x, ...) {
  cat("Gazepoint pipeline comparison dashboard\n\n")
  print(x$overall, row.names = FALSE)
  cat("\nDashboard preview:\n")
  print(utils::head(x$dashboard, 10L), row.names = FALSE)
  invisible(x)
}
