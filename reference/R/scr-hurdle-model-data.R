#' Prepare Gazepoint SCR hurdle-model data
#'
#' Converts SCR event-window summaries into model-ready data for two-part
#' electrodermal-response analyses: a binary response/no-response component and
#' a positive-amplitude component among response events.
#'
#' @param scr_event_windows A `gazepoint_scr_event_window_summary` object
#'   returned by `summarise_gazepoint_scr_event_windows()`, or a data frame
#'   containing event-window SCR summaries.
#' @param response_col Column containing the binary SCR response flag.
#' @param amplitude_col Column containing SCR amplitude.
#' @param latency_col Optional column containing SCR latency.
#' @param rise_time_col Optional column containing SCR rise time.
#' @param recovery_time_col Optional column containing SCR recovery time.
#' @param predictor_cols Optional fixed-effect predictor columns to include in
#'   generated formulas and complete-case checks.
#' @param factor_cols Optional columns to coerce to factors.
#' @param numeric_cols Optional columns to coerce to numeric.
#' @param group_cols Optional grouping columns retained for random effects or
#'   clustered summaries.
#' @param event_id_col Optional event identifier column.
#' @param amplitude_transform Transformation for the positive-amplitude outcome:
#'   `"none"`, `"log"`, or `"log1p"`.
#' @param amplitude_offset Small positive offset used when
#'   `amplitude_transform = "log"`.
#' @param drop_missing_predictors Logical. If `TRUE`, model datasets are
#'   restricted to rows complete on outcome and predictor columns.
#'
#' @return A list with `overview`, `response_model_data`,
#'   `amplitude_model_data`, `variable_summary`, `model_formulas`, and
#'   `settings`.
#' @export
prepare_gazepoint_scr_hurdle_model_data <- function(scr_event_windows,
                                                    response_col = "response_flag",
                                                    amplitude_col = "scr_amplitude",
                                                    latency_col = "scr_latency",
                                                    rise_time_col = "scr_rise_time",
                                                    recovery_time_col = "scr_recovery_time",
                                                    predictor_cols = NULL,
                                                    factor_cols = NULL,
                                                    numeric_cols = NULL,
                                                    group_cols = NULL,
                                                    event_id_col = "event_id",
                                                    amplitude_transform = c("none", "log", "log1p"),
                                                    amplitude_offset = 1e-6,
                                                    drop_missing_predictors = TRUE) {
  amplitude_transform <- match.arg(amplitude_transform)

  if (missing(scr_event_windows) || is.null(scr_event_windows)) {
    stop("`scr_event_windows` must be supplied.", call. = FALSE)
  }

  if (!is.logical(drop_missing_predictors) ||
      length(drop_missing_predictors) != 1 ||
      is.na(drop_missing_predictors)) {
    stop("`drop_missing_predictors` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.numeric(amplitude_offset) ||
      length(amplitude_offset) != 1 ||
      !is.finite(amplitude_offset) ||
      amplitude_offset <= 0) {
    stop("`amplitude_offset` must be a single positive finite number.", call. = FALSE)
  }

  event_table <- gpbiometrics_scr_hurdle_extract_event_table(scr_event_windows)

  if (!response_col %in% names(event_table)) {
    stop("`response_col` was not found in the event table.", call. = FALSE)
  }

  if (!amplitude_col %in% names(event_table)) {
    stop("`amplitude_col` was not found in the event table.", call. = FALSE)
  }

  required_requested_cols <- unique(c(
    predictor_cols,
    factor_cols,
    numeric_cols,
    group_cols,
    event_id_col
  ))

  required_requested_cols <- required_requested_cols[
    !is.na(required_requested_cols)
  ]

  missing_requested <- setdiff(required_requested_cols, names(event_table))

  if (length(missing_requested) > 0) {
    stop(
      "Requested columns were not found in the event table: ",
      paste(missing_requested, collapse = ", "),
      call. = FALSE
    )
  }

  dat <- as.data.frame(event_table, stringsAsFactors = FALSE)

  for (col in unique(factor_cols)) {
    dat[[col]] <- as.factor(dat[[col]])
  }

  for (col in unique(c(numeric_cols, response_col, amplitude_col))) {
    if (col %in% names(dat)) {
      dat[[col]] <- suppressWarnings(as.numeric(dat[[col]]))
    }
  }

  response_value <- suppressWarnings(as.numeric(dat[[response_col]]))

  if (all(is.na(response_value))) {
    stop("`response_col` must contain numeric or numeric-coercible values.", call. = FALSE)
  }

  response_binary <- ifelse(is.finite(response_value) & response_value > 0, 1L, 0L)
  response_binary[!is.finite(response_value)] <- NA_integer_

  dat$scr_response_binary <- response_binary

  amplitude_value <- suppressWarnings(as.numeric(dat[[amplitude_col]]))
  dat$scr_amplitude_raw <- amplitude_value

  dat$scr_amplitude_positive <- ifelse(
    dat$scr_response_binary == 1L & is.finite(amplitude_value) & amplitude_value > 0,
    amplitude_value,
    NA_real_
  )

  dat$scr_amplitude_model <- gpbiometrics_scr_hurdle_transform_amplitude(
    x = dat$scr_amplitude_positive,
    transform = amplitude_transform,
    offset = amplitude_offset
  )

  dat$scr_latency_model <- if (latency_col %in% names(dat)) {
    suppressWarnings(as.numeric(dat[[latency_col]]))
  } else {
    NA_real_
  }

  dat$scr_rise_time_model <- if (rise_time_col %in% names(dat)) {
    suppressWarnings(as.numeric(dat[[rise_time_col]]))
  } else {
    NA_real_
  }

  dat$scr_recovery_time_model <- if (recovery_time_col %in% names(dat)) {
    suppressWarnings(as.numeric(dat[[recovery_time_col]]))
  } else {
    NA_real_
  }

  response_complete_cols <- unique(c(
    "scr_response_binary",
    predictor_cols,
    group_cols,
    event_id_col
  ))

  response_complete_cols <- response_complete_cols[response_complete_cols %in% names(dat)]

  amplitude_complete_cols <- unique(c(
    "scr_amplitude_model",
    predictor_cols,
    group_cols,
    event_id_col
  ))

  amplitude_complete_cols <- amplitude_complete_cols[amplitude_complete_cols %in% names(dat)]

  dat$response_model_complete <- stats::complete.cases(dat[response_complete_cols])
  dat$amplitude_model_complete <- stats::complete.cases(dat[amplitude_complete_cols]) &
    dat$scr_response_binary == 1L &
    is.finite(dat$scr_amplitude_model)

  response_model_data <- dat[!is.na(dat$scr_response_binary), , drop = FALSE]

  if (isTRUE(drop_missing_predictors)) {
    response_model_data <- response_model_data[
      response_model_data$response_model_complete,
      ,
      drop = FALSE
    ]
  }

  amplitude_model_data <- dat[
    dat$scr_response_binary == 1L & is.finite(dat$scr_amplitude_model),
    ,
    drop = FALSE
  ]

  if (isTRUE(drop_missing_predictors)) {
    amplitude_model_data <- amplitude_model_data[
      amplitude_model_data$amplitude_model_complete,
      ,
      drop = FALSE
    ]
  }

  variable_summary <- gpbiometrics_scr_hurdle_variable_summary(
    dat = dat,
    predictor_cols = predictor_cols,
    group_cols = group_cols,
    factor_cols = factor_cols,
    numeric_cols = numeric_cols
  )

  model_formulas <- gpbiometrics_scr_hurdle_formulas(
    predictor_cols = predictor_cols,
    group_cols = group_cols
  )

  overview <- data.frame(
    input_events = nrow(dat),
    response_model_rows = nrow(response_model_data),
    amplitude_model_rows = nrow(amplitude_model_data),
    response_events = sum(dat$scr_response_binary == 1L, na.rm = TRUE),
    no_response_events = sum(dat$scr_response_binary == 0L, na.rm = TRUE),
    response_rate = mean(dat$scr_response_binary == 1L, na.rm = TRUE),
    positive_amplitude_events = sum(is.finite(dat$scr_amplitude_positive), na.rm = TRUE),
    predictor_count = length(predictor_cols),
    group_count = length(group_cols),
    amplitude_transform = amplitude_transform,
    status = if (nrow(response_model_data) == 0) {
      "fail_no_response_model_rows"
    } else if (nrow(amplitude_model_data) == 0) {
      "warn_no_positive_amplitude_rows"
    } else {
      "scr_hurdle_model_data_prepared"
    },
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      response_model_data = response_model_data,
      amplitude_model_data = amplitude_model_data,
      variable_summary = variable_summary,
      model_formulas = model_formulas,
      settings = list(
        response_col = response_col,
        amplitude_col = amplitude_col,
        latency_col = latency_col,
        rise_time_col = rise_time_col,
        recovery_time_col = recovery_time_col,
        predictor_cols = predictor_cols,
        factor_cols = factor_cols,
        numeric_cols = numeric_cols,
        group_cols = group_cols,
        event_id_col = event_id_col,
        amplitude_transform = amplitude_transform,
        amplitude_offset = amplitude_offset,
        drop_missing_predictors = drop_missing_predictors,
        interpretation_notes = c(
          "The response model is a binary SCR response/no-response model.",
          "The amplitude model uses only response events with positive finite SCR amplitudes.",
          "EDA/SCR outcomes indicate electrodermal response features, not emotional valence."
        )
      )
    ),
    class = c("gazepoint_scr_hurdle_model_data", "list")
  )
}

gpbiometrics_scr_hurdle_extract_event_table <- function(scr_event_windows) {
  if (inherits(scr_event_windows, "gazepoint_scr_event_window_summary") &&
      !is.null(scr_event_windows$event_table)) {
    return(as.data.frame(scr_event_windows$event_table, stringsAsFactors = FALSE))
  }

  if (is.data.frame(scr_event_windows)) {
    return(as.data.frame(scr_event_windows, stringsAsFactors = FALSE))
  }

  stop(
    "`scr_event_windows` must be an SCR event-window summary object or a data frame.",
    call. = FALSE
  )
}

gpbiometrics_scr_hurdle_transform_amplitude <- function(x,
                                                        transform,
                                                        offset) {
  if (identical(transform, "none")) {
    return(x)
  }

  if (identical(transform, "log")) {
    return(log(x + offset))
  }

  if (identical(transform, "log1p")) {
    return(log1p(x))
  }

  x
}

gpbiometrics_scr_hurdle_variable_summary <- function(dat,
                                                     predictor_cols,
                                                     group_cols,
                                                     factor_cols,
                                                     numeric_cols) {
  cols <- unique(c(
    "scr_response_binary",
    "scr_amplitude_raw",
    "scr_amplitude_positive",
    "scr_amplitude_model",
    "scr_latency_model",
    "scr_rise_time_model",
    "scr_recovery_time_model",
    predictor_cols,
    group_cols,
    factor_cols,
    numeric_cols
  ))

  cols <- cols[cols %in% names(dat)]

  out <- lapply(cols, function(col) {
    x <- dat[[col]]

    if (is.numeric(x) || is.integer(x)) {
      finite_x <- x[is.finite(x)]

      data.frame(
        variable = col,
        class = paste(class(x), collapse = "/"),
        missing = sum(is.na(x)),
        unique_values = length(unique(x[!is.na(x)])),
        mean = if (length(finite_x) > 0) mean(finite_x, na.rm = TRUE) else NA_real_,
        sd = if (length(finite_x) > 1) stats::sd(finite_x, na.rm = TRUE) else NA_real_,
        min = if (length(finite_x) > 0) min(finite_x, na.rm = TRUE) else NA_real_,
        max = if (length(finite_x) > 0) max(finite_x, na.rm = TRUE) else NA_real_,
        stringsAsFactors = FALSE
      )
    } else {
      data.frame(
        variable = col,
        class = paste(class(x), collapse = "/"),
        missing = sum(is.na(x)),
        unique_values = length(unique(x[!is.na(x)])),
        mean = NA_real_,
        sd = NA_real_,
        min = NA_real_,
        max = NA_real_,
        stringsAsFactors = FALSE
      )
    }
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}

gpbiometrics_scr_hurdle_formulas <- function(predictor_cols,
                                             group_cols) {
  fixed_rhs <- if (length(predictor_cols) > 0) {
    paste(predictor_cols, collapse = " + ")
  } else {
    "1"
  }

  random_rhs <- if (length(group_cols) > 0) {
    paste0("(1 | ", group_cols, ")", collapse = " + ")
  } else {
    character()
  }

  rhs <- paste(c(fixed_rhs, random_rhs), collapse = " + ")

  data.frame(
    model_component = c("response", "amplitude"),
    outcome = c("scr_response_binary", "scr_amplitude_model"),
    formula = c(
      paste("scr_response_binary ~", rhs),
      paste("scr_amplitude_model ~", rhs)
    ),
    suggested_family = c("binomial", "gaussian_or_gamma_positive"),
    stringsAsFactors = FALSE
  )
}
