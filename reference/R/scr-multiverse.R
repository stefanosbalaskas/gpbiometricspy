#' Run a multiverse of SCR scoring specifications
#'
#' Scores SCR amplitudes across multiple latency windows, thresholds, baseline
#' methods, and response metrics. Optionally applies a user-supplied model
#' function to each specification. This supports transparent sensitivity
#' analysis and specification-curve style reporting.
#'
#' @param dat Sample-level EDA data.
#' @param signal_col Conductance/EDA signal column.
#' @param time_col Time column, preferably relative to stimulus onset. If
#'   `event_time_col` is supplied, relative time is computed as
#'   `time_col - event_time_col`.
#' @param trial_cols Columns identifying trials.
#' @param condition_col Optional experimental condition column.
#' @param participant_col Optional participant column.
#' @param event_time_col Optional event/stimulus onset time column.
#' @param latency_windows List of response windows in seconds.
#' @param thresholds SCR response thresholds.
#' @param baseline_methods Baseline methods: `"median"`, `"mean"`, or `"none"`.
#' @param baseline_window Baseline window in relative seconds.
#' @param response_metrics Response metrics: `"max_minus_baseline"` or
#'   `"peak_to_peak"`.
#' @param model_function Optional function applied to each specification-level
#'   trial summary.
#'
#' @return A list with specification grid, scored trials, optional model results,
#'   and robustness overview.
#' @export
run_gazepoint_scr_multiverse <- function(dat,
                                         signal_col = "GSR_US",
                                         time_col = "time",
                                         trial_cols = NULL,
                                         condition_col = NULL,
                                         participant_col = NULL,
                                         event_time_col = NULL,
                                         latency_windows = list(c(1, 3), c(1, 4), c(1, 5)),
                                         thresholds = c(0.01, 0.05),
                                         baseline_methods = c("median", "mean"),
                                         baseline_window = c(-1, 0),
                                         response_metrics = c("max_minus_baseline"),
                                         model_function = NULL) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  required <- c(signal_col, time_col, trial_cols, condition_col, participant_col, event_time_col)
  required <- required[!is.null(required)]

  missing_required <- setdiff(required, names(dat))
  if (length(missing_required) > 0) {
    stop("Missing required columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  if (!is.numeric(dat[[signal_col]])) {
    stop("`signal_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.numeric(dat[[time_col]])) {
    stop("`time_col` must identify a numeric column.", call. = FALSE)
  }

  baseline_methods <- match.arg(baseline_methods, choices = c("median", "mean", "none"), several.ok = TRUE)
  response_metrics <- match.arg(response_metrics, choices = c("max_minus_baseline", "peak_to_peak"), several.ok = TRUE)

  if (is.null(trial_cols)) {
    dat$.gpbiometrics_trial_id <- "trial_1"
    trial_cols <- ".gpbiometrics_trial_id"
  }

  specification_grid <- expand.grid(
    window_id = seq_along(latency_windows),
    threshold = thresholds,
    baseline_method = baseline_methods,
    response_metric = response_metrics,
    stringsAsFactors = FALSE
  )

  specification_grid$latency_lower <- vapply(latency_windows[specification_grid$window_id], `[`, numeric(1), 1)
  specification_grid$latency_upper <- vapply(latency_windows[specification_grid$window_id], `[`, numeric(1), 2)
  specification_grid$specification_id <- paste0("spec_", seq_len(nrow(specification_grid)))

  trial_groups <- gpbiometrics_scr_multiverse_split(dat, trial_cols)

  scored_rows <- list()
  row_id <- 1L

  for (spec_i in seq_len(nrow(specification_grid))) {
    spec <- specification_grid[spec_i, , drop = FALSE]

    for (trial_id in names(trial_groups)) {
      idx <- trial_groups[[trial_id]]

      rel_time <- dat[[time_col]][idx]

      if (!is.null(event_time_col)) {
        event_time <- dat[[event_time_col]][idx][1]
        rel_time <- rel_time - event_time
      }

      signal <- dat[[signal_col]][idx]

      baseline_idx <- is.finite(rel_time) &
        rel_time >= baseline_window[1] &
        rel_time <= baseline_window[2] &
        is.finite(signal)

      response_idx <- is.finite(rel_time) &
        rel_time >= spec$latency_lower &
        rel_time <= spec$latency_upper &
        is.finite(signal)

      baseline_value <- gpbiometrics_scr_multiverse_baseline(
        signal[baseline_idx],
        method = spec$baseline_method
      )

      if (sum(response_idx) == 0) {
        response_amplitude <- NA_real_
        peak_time <- NA_real_
        status <- "no_response_window_samples"
      } else {
        response_signal <- signal[response_idx]
        response_time <- rel_time[response_idx]

        if (spec$response_metric == "max_minus_baseline") {
          peak_i <- which.max(response_signal)
          response_amplitude <- max(response_signal, na.rm = TRUE) - baseline_value
          peak_time <- response_time[peak_i]
        } else {
          peak_i <- which.max(response_signal)
          response_amplitude <- max(response_signal, na.rm = TRUE) - min(response_signal, na.rm = TRUE)
          peak_time <- response_time[peak_i]
        }

        status <- "scr_scored"
      }

      base_values <- gpbiometrics_scr_multiverse_values(dat, idx, c(trial_cols, participant_col, condition_col))

      scored_rows[[row_id]] <- data.frame(
        specification_id = spec$specification_id,
        window_id = spec$window_id,
        latency_lower = spec$latency_lower,
        latency_upper = spec$latency_upper,
        threshold = spec$threshold,
        baseline_method = spec$baseline_method,
        response_metric = spec$response_metric,
        trial_id = trial_id,
        base_values,
        baseline_value = baseline_value,
        response_amplitude = response_amplitude,
        response_present = is.finite(response_amplitude) && response_amplitude >= spec$threshold,
        peak_time = peak_time,
        status = status,
        stringsAsFactors = FALSE,
        check.names = FALSE
      )

      row_id <- row_id + 1L
    }
  }

  scored_trials <- do.call(rbind, scored_rows)
  rownames(scored_trials) <- NULL

  specification_summary <- stats::aggregate(
    cbind(response_amplitude, response_present) ~ specification_id + latency_lower +
      latency_upper + threshold + baseline_method + response_metric,
    data = scored_trials,
    FUN = function(x) mean(x, na.rm = TRUE)
  )

  names(specification_summary)[names(specification_summary) == "response_amplitude"] <- "mean_response_amplitude"
  names(specification_summary)[names(specification_summary) == "response_present"] <- "response_rate"

  model_results <- NULL

  if (!is.null(model_function)) {
    model_results <- lapply(split(scored_trials, scored_trials$specification_id), function(x) {
      tryCatch(
        model_function(x),
        error = function(e) list(error = conditionMessage(e))
      )
    })
  } else if (!is.null(condition_col) && condition_col %in% names(scored_trials)) {
    model_results <- gpbiometrics_scr_multiverse_default_models(scored_trials, condition_col)
  }

  overview <- data.frame(
    specification_count = nrow(specification_grid),
    trial_count = length(trial_groups),
    scored_rows = nrow(scored_trials),
    successful_rows = sum(scored_trials$status == "scr_scored"),
    problem_rows = sum(scored_trials$status != "scr_scored"),
    status = if (all(scored_trials$status == "scr_scored")) {
      "scr_multiverse_complete"
    } else if (any(scored_trials$status == "scr_scored")) {
      "scr_multiverse_partial"
    } else {
      "scr_multiverse_failed"
    },
    interpretation = paste(
      "The SCR multiverse scores responses across defensible parameter specifications.",
      "It supports transparent sensitivity reporting and does not identify a universally best scoring rule."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      specification_grid = specification_grid,
      scored_trials = scored_trials,
      specification_summary = specification_summary,
      model_results = model_results,
      settings = list(
        signal_col = signal_col,
        time_col = time_col,
        trial_cols = trial_cols,
        condition_col = condition_col,
        participant_col = participant_col,
        event_time_col = event_time_col,
        latency_windows = latency_windows,
        thresholds = thresholds,
        baseline_methods = baseline_methods,
        baseline_window = baseline_window,
        response_metrics = response_metrics
      )
    ),
    class = c("gazepoint_scr_multiverse", "list")
  )
}

gpbiometrics_scr_multiverse_split <- function(dat, trial_cols) {
  gf <- dat[trial_cols]
  gf[] <- lapply(gf, function(x) {
    x <- as.character(x)
    x[is.na(x)] <- "<NA>"
    x
  })

  split(seq_len(nrow(dat)), do.call(paste, c(gf, sep = " | ")))
}

gpbiometrics_scr_multiverse_values <- function(dat, idx, cols) {
  cols <- cols[!is.null(cols)]
  cols <- unique(cols)
  cols <- cols[cols %in% names(dat)]

  if (length(cols) == 0) {
    return(data.frame(dummy = NA_character_)[0])
  }

  vals <- lapply(cols, function(nm) as.character(dat[[nm]][idx[1]]))
  names(vals) <- cols
  as.data.frame(vals, stringsAsFactors = FALSE, optional = TRUE)
}

gpbiometrics_scr_multiverse_baseline <- function(x, method) {
  if (method == "none") {
    return(0)
  }

  x <- x[is.finite(x)]

  if (length(x) == 0) {
    return(0)
  }

  if (method == "median") {
    stats::median(x)
  } else {
    mean(x)
  }
}

gpbiometrics_scr_multiverse_default_models <- function(scored_trials, condition_col) {
  lapply(split(scored_trials, scored_trials$specification_id), function(x) {
    out <- list()

    if (length(unique(x[[condition_col]])) < 2) {
      return(list(status = "condition_has_less_than_two_levels"))
    }

    x[[condition_col]] <- as.factor(x[[condition_col]])

    out$hurdle_part <- tryCatch({
      fit <- stats::glm(response_present ~ x[[condition_col]], data = x, family = stats::binomial())
      coef_table <- stats::coef(summary(fit))
      data.frame(
        term = rownames(coef_table),
        estimate = coef_table[, "Estimate"],
        p_value = coef_table[, "Pr(>|z|)"],
        row.names = NULL,
        stringsAsFactors = FALSE
      )
    }, error = function(e) {
      data.frame(error = conditionMessage(e), stringsAsFactors = FALSE)
    })

    positive <- x[is.finite(x$response_amplitude) & x$response_amplitude > 0, , drop = FALSE]

    out$amplitude_part <- tryCatch({
      if (nrow(positive) < 3 || length(unique(positive[[condition_col]])) < 2) {
        data.frame(status = "insufficient_positive_responses", stringsAsFactors = FALSE)
      } else {
        fit <- stats::lm(log1p(response_amplitude) ~ positive[[condition_col]], data = positive)
        coef_table <- stats::coef(summary(fit))
        data.frame(
          term = rownames(coef_table),
          estimate = coef_table[, "Estimate"],
          p_value = coef_table[, "Pr(>|t|)"],
          row.names = NULL,
          stringsAsFactors = FALSE
        )
      }
    }, error = function(e) {
      data.frame(error = conditionMessage(e), stringsAsFactors = FALSE)
    })

    out$status <- "default_two_part_models_completed"
    out
  })
}
