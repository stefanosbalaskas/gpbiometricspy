#' Audit distributional drift across sessions or ordered blocks
#'
#' Compares signal distributions across sessions/blocks using baseline-vs-current
#' differences, Kolmogorov-Smirnov tests, and Population Stability Index (PSI).
#'
#' @param dat A data frame containing longitudinal biometric data.
#' @param signal_cols Numeric signal columns to audit.
#' @param session_col Session/block/timepoint column.
#' @param participant_col Optional participant column.
#' @param reference_session Optional reference session. If `NULL`, the first
#'   ordered session is used within each participant/global group.
#' @param bins Number of bins for PSI.
#' @param psi_warn PSI threshold for warning.
#' @param psi_fail PSI threshold for failure.
#'
#' @return A list with `overview`, `drift_summary`, and `settings`.
#' @export
audit_gazepoint_distributional_drift <- function(dat,
                                                 signal_cols,
                                                 session_col = "session",
                                                 participant_col = NULL,
                                                 reference_session = NULL,
                                                 bins = 10,
                                                 psi_warn = 0.10,
                                                 psi_fail = 0.25) {
  if (!is.data.frame(dat)) stop("`dat` must be a data frame.", call. = FALSE)
  if (!session_col %in% names(dat)) stop("Column `", session_col, "` was not found.", call. = FALSE)

  missing_signals <- setdiff(signal_cols, names(dat))
  if (length(missing_signals) > 0) {
    stop("Missing `signal_cols`: ", paste(missing_signals, collapse = ", "), call. = FALSE)
  }

  non_numeric <- signal_cols[!vapply(dat[signal_cols], is.numeric, logical(1))]
  if (length(non_numeric) > 0) {
    stop("Non-numeric `signal_cols`: ", paste(non_numeric, collapse = ", "), call. = FALSE)
  }

  if (!is.null(participant_col) && !participant_col %in% names(dat)) {
    stop("Column `", participant_col, "` was not found.", call. = FALSE)
  }

  groups <- if (is.null(participant_col)) {
    list(all_participants = seq_len(nrow(dat)))
  } else {
    split(seq_len(nrow(dat)), dat[[participant_col]], drop = TRUE)
  }

  rows <- list()
  row_id <- 1L

  for (group_id in names(groups)) {
    idx_group <- groups[[group_id]]
    sessions <- unique(dat[[session_col]][idx_group])
    sessions <- sessions[order(sessions)]

    ref <- if (!is.null(reference_session)) reference_session else sessions[1]

    idx_ref <- idx_group[dat[[session_col]][idx_group] == ref]

    for (sess in sessions) {
      idx_sess <- idx_group[dat[[session_col]][idx_group] == sess]

      for (signal_col in signal_cols) {
        x_ref <- dat[[signal_col]][idx_ref]
        x_cur <- dat[[signal_col]][idx_sess]

        x_ref <- x_ref[is.finite(x_ref)]
        x_cur <- x_cur[is.finite(x_cur)]

        status <- "drift_audited"
        ks_p <- NA_real_
        psi <- NA_real_
        mean_difference <- NA_real_
        sd_ratio <- NA_real_

        if (length(x_ref) < 2 || length(x_cur) < 2) {
          status <- "insufficient_data"
        } else {
          mean_difference <- mean(x_cur) - mean(x_ref)
          sd_ratio <- if (stats::sd(x_ref) > 0) stats::sd(x_cur) / stats::sd(x_ref) else NA_real_
          ks_p <- tryCatch(stats::ks.test(x_ref, x_cur)$p.value, error = function(e) NA_real_)
          psi <- gpbiometrics_psi(x_ref, x_cur, bins = bins)

          if (is.finite(psi) && psi >= psi_fail) {
            status <- "drift_fail"
          } else if (is.finite(psi) && psi >= psi_warn) {
            status <- "drift_warn"
          }
        }

        rows[[row_id]] <- data.frame(
          group_id = as.character(group_id),
          reference_session = as.character(ref),
          comparison_session = as.character(sess),
          signal_col = signal_col,
          n_reference = length(x_ref),
          n_comparison = length(x_cur),
          reference_mean = if (length(x_ref) > 0) mean(x_ref) else NA_real_,
          comparison_mean = if (length(x_cur) > 0) mean(x_cur) else NA_real_,
          mean_difference = mean_difference,
          sd_ratio = sd_ratio,
          ks_p_value = ks_p,
          psi = psi,
          status = status,
          stringsAsFactors = FALSE
        )

        row_id <- row_id + 1L
      }
    }
  }

  drift_summary <- do.call(rbind, rows)
  rownames(drift_summary) <- NULL

  overview <- data.frame(
    drift_rows = nrow(drift_summary),
    signal_count = length(signal_cols),
    participant_groups = length(groups),
    warn_rows = sum(drift_summary$status == "drift_warn"),
    fail_rows = sum(drift_summary$status == "drift_fail"),
    insufficient_rows = sum(drift_summary$status == "insufficient_data"),
    status = if (any(drift_summary$status == "drift_fail")) {
      "distributional_drift_failures_detected"
    } else if (any(drift_summary$status == "drift_warn")) {
      "distributional_drift_warnings_detected"
    } else {
      "distributional_drift_audited"
    },
    interpretation = paste(
      "Distributional drift metrics flag changes in signal distributions across sessions or blocks.",
      "They support longitudinal QC and do not prove that data cannot be pooled without design-specific judgement."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      drift_summary = drift_summary,
      settings = list(
        signal_cols = signal_cols,
        session_col = session_col,
        participant_col = participant_col,
        reference_session = reference_session,
        bins = bins,
        psi_warn = psi_warn,
        psi_fail = psi_fail
      )
    ),
    class = c("gazepoint_distributional_drift", "list")
  )
}

gpbiometrics_psi <- function(reference, current, bins = 10, eps = 1e-6) {
  reference <- reference[is.finite(reference)]
  current <- current[is.finite(current)]

  if (length(reference) < 2 || length(current) < 2) return(NA_real_)

  probs <- seq(0, 1, length.out = bins + 1)
  breaks <- unique(as.numeric(stats::quantile(reference, probs = probs, na.rm = TRUE, type = 7)))

  if (length(breaks) < 3) return(NA_real_)

  breaks[1] <- -Inf
  breaks[length(breaks)] <- Inf

  ref_tab <- table(cut(reference, breaks = breaks, include.lowest = TRUE))
  cur_tab <- table(cut(current, breaks = breaks, include.lowest = TRUE))

  ref_prop <- as.numeric(ref_tab) / sum(ref_tab)
  cur_prop <- as.numeric(cur_tab) / sum(cur_tab)

  ref_prop <- pmax(ref_prop, eps)
  cur_prop <- pmax(cur_prop, eps)

  sum((cur_prop - ref_prop) * log(cur_prop / ref_prop))
}
