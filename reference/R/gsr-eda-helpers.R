#' Convert Gazepoint GSR resistance to conductance
#'
#' Converts GSR resistance values to conductance in microSiemens. The helper is
#' intentionally conservative. If a conductance column such as `GSR_US` is
#' already present, the data are returned unchanged unless `overwrite = TRUE`.
#' If `input_unit = "auto"`, conversion is performed only when the source column
#' has a resistance-like name, such as `GSR_OHMS` or `resistance_ohms`.
#'
#' Generic `GSR` columns are not automatically assumed to be resistance because
#' Gazepoint exports and workflows may represent GSR/EDA differently. For a
#' generic `GSR` column, use `input_unit = "ohms"` or `input_unit = "kohms"`
#' only when the study documentation confirms resistance units.
#'
#' @param data A data frame.
#' @param gsr_col Optional source GSR column. If `NULL`, a resistance-like column
#'   is detected when possible.
#' @param output_col Name of the output conductance column.
#' @param input_unit Source unit. `"auto"` converts only resistance-like columns;
#'   `"ohms"` converts ohms to microSiemens; `"kohms"` converts kilo-ohms to
#'   microSiemens; `"microsiemens"` copies values to `output_col`.
#' @param overwrite Logical. If `FALSE`, an existing `output_col` is not
#'   overwritten.
#'
#' @return The input data frame with a conductance column when conversion is
#'   possible. A structured conversion summary is stored in the
#'   `gsr_conversion_summary` attribute.
#'
#' @examples
#' df <- data.frame(GSR_OHMS = c(1000000, 500000, NA))
#' convert_gazepoint_gsr_to_conductance(df)
#'
#' @export
convert_gazepoint_gsr_to_conductance <- function(data,
                                                 gsr_col = NULL,
                                                 output_col = "GSR_US",
                                                 input_unit = c("auto",
                                                                "ohms",
                                                                "kohms",
                                                                "microsiemens"),
                                                 overwrite = FALSE) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  input_unit <- match.arg(input_unit)

  if (!is.character(output_col) ||
      length(output_col) != 1L ||
      is.na(output_col) ||
      !nzchar(output_col)) {
    stop("`output_col` must be a non-empty character string.", call. = FALSE)
  }

  if (!is.logical(overwrite) || length(overwrite) != 1L || is.na(overwrite)) {
    stop("`overwrite` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.null(gsr_col)) {
    .gpbiom_assert_columns(data, gsr_col, "gsr_col")
  }

  existing_conductance <- .gpbiom_existing_conductance_column(data)

  if (output_col %in% names(data) && !isTRUE(overwrite)) {
    summary <- .gpbiom_gsr_conversion_summary(
      status = "conductance_column_already_present",
      source_column = NA_character_,
      output_column = output_col,
      input_unit = input_unit,
      n = nrow(data),
      n_converted = sum(!is.na(data[[output_col]])),
      n_invalid = 0L,
      note = paste0(
        "`", output_col, "` already exists and `overwrite = FALSE`; ",
        "data were returned unchanged."
      )
    )

    attr(data, "gsr_conversion_summary") <- summary
    return(data)
  }

  if (!is.na(existing_conductance) &&
      !identical(existing_conductance, output_col) &&
      !isTRUE(overwrite)) {
    summary <- .gpbiom_gsr_conversion_summary(
      status = "conductance_column_already_present",
      source_column = existing_conductance,
      output_column = existing_conductance,
      input_unit = "microsiemens",
      n = nrow(data),
      n_converted = sum(!is.na(data[[existing_conductance]])),
      n_invalid = 0L,
      note = paste0(
        "A conductance-like column (`", existing_conductance,
        "`) is already present; no conversion was performed."
      )
    )

    attr(data, "gsr_conversion_summary") <- summary
    return(data)
  }

  source_col <- if (is.null(gsr_col)) {
    .gpbiom_detect_resistance_column(data)
  } else {
    gsr_col
  }

  if (is.na(source_col)) {
    summary <- .gpbiom_gsr_conversion_summary(
      status = "no_resistance_source_detected",
      source_column = NA_character_,
      output_column = output_col,
      input_unit = input_unit,
      n = nrow(data),
      n_converted = 0L,
      n_invalid = 0L,
      note = paste0(
        "No resistance-like source column was detected. Generic GSR columns ",
        "are not converted automatically."
      )
    )

    attr(data, "gsr_conversion_summary") <- summary
    return(data)
  }

  if (!is.numeric(data[[source_col]])) {
    stop("The selected GSR source column must be numeric.", call. = FALSE)
  }

  source_standard <- standardise_gazepoint_biometric_names(source_col)

  resolved_unit <- .gpbiom_resolve_gsr_input_unit(
    input_unit = input_unit,
    source_standard = source_standard
  )

  if (identical(resolved_unit, "unknown")) {
    summary <- .gpbiom_gsr_conversion_summary(
      status = "unit_not_confirmed",
      source_column = source_col,
      output_column = output_col,
      input_unit = input_unit,
      n = nrow(data),
      n_converted = 0L,
      n_invalid = 0L,
      note = paste0(
        "The source column was not clearly resistance-like. Use ",
        "`input_unit = \"ohms\"` or `input_unit = \"kohms\"` only when ",
        "documentation confirms resistance units."
      )
    )

    attr(data, "gsr_conversion_summary") <- summary
    return(data)
  }

  source_values <- data[[source_col]]
  converted <- rep(NA_real_, length(source_values))
  invalid <- rep(FALSE, length(source_values))

  if (identical(resolved_unit, "ohms")) {
    valid <- !is.na(source_values) & is.finite(source_values) & source_values > 0
    invalid <- !is.na(source_values) & (!is.finite(source_values) | source_values <= 0)
    converted[valid] <- 1000000 / source_values[valid]
  } else if (identical(resolved_unit, "kohms")) {
    valid <- !is.na(source_values) & is.finite(source_values) & source_values > 0
    invalid <- !is.na(source_values) & (!is.finite(source_values) | source_values <= 0)
    converted[valid] <- 1000 / source_values[valid]
  } else if (identical(resolved_unit, "microsiemens")) {
    valid <- !is.na(source_values) & is.finite(source_values)
    invalid <- !is.na(source_values) & !is.finite(source_values)
    converted[valid] <- source_values[valid]
  }

  data[[output_col]] <- converted

  summary <- .gpbiom_gsr_conversion_summary(
    status = "conductance_created",
    source_column = source_col,
    output_column = output_col,
    input_unit = resolved_unit,
    n = nrow(data),
    n_converted = sum(!is.na(converted)),
    n_invalid = sum(invalid),
    note = "Conductance values are reported in microSiemens."
  )

  attr(data, "gsr_conversion_summary") <- summary
  data
}


#' Summarise tonic and phasic GSR/EDA components
#'
#' Creates a simple descriptive tonic/phasic decomposition of a GSR/EDA signal.
#' The tonic component is estimated with a rolling median, and the phasic
#' component is the observed signal minus the rolling-median tonic estimate.
#'
#' This is a lightweight descriptive helper, not a full skin-conductance-response
#' deconvolution model. It should be used for quality checks, window summaries,
#' and exploratory reporting unless a study requires a specialised EDA model.
#'
#' @param data A data frame.
#' @param gsr_col Optional GSR/EDA column. If `NULL`, the function prefers
#'   `GSR_US`, then `GSR`, then other recognised GSR/EDA columns.
#' @param group_cols Optional grouping columns. Tonic/phasic values are computed
#'   separately within each group.
#' @param time_col Optional time column used to order rows within groups.
#' @param window_n Rolling-median window size in samples.
#' @param peak_threshold Optional phasic peak threshold. If `NULL`, a robust
#'   data-driven threshold is computed within each group as
#'   `median(phasic) + 2 * MAD(phasic)`.
#' @param output_prefix Prefix for generated columns.
#'
#' @return A list with `data`, `summary`, and `settings`.
#'
#' @examples
#' df <- data.frame(
#'   CNT = 1:10,
#'   GSR_US = c(1, 1.1, 1.0, 1.2, 2.0, 1.3, 1.2, 1.1, 1.0, 1.1)
#' )
#' summarise_gazepoint_gsr_tonic_phasic(df, window_n = 3)
#'
#' @export
summarise_gazepoint_gsr_tonic_phasic <- function(data,
                                                 gsr_col = NULL,
                                                 group_cols = NULL,
                                                 time_col = NULL,
                                                 window_n = 15L,
                                                 peak_threshold = NULL,
                                                 output_prefix = "gsr") {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (!is.null(gsr_col)) {
    .gpbiom_assert_columns(data, gsr_col, "gsr_col")
  }

  if (!is.null(group_cols)) {
    .gpbiom_assert_columns(data, group_cols, "group_cols")
  }

  if (!is.null(time_col)) {
    .gpbiom_assert_columns(data, time_col, "time_col")
  }

  .gpbiom_assert_positive_integer(window_n, "window_n")

  if (!is.null(peak_threshold) &&
      (!is.numeric(peak_threshold) ||
       length(peak_threshold) != 1L ||
       is.na(peak_threshold))) {
    stop("`peak_threshold` must be NULL or a single numeric value.",
         call. = FALSE)
  }

  if (!is.character(output_prefix) ||
      length(output_prefix) != 1L ||
      is.na(output_prefix) ||
      !nzchar(output_prefix)) {
    stop("`output_prefix` must be a non-empty character string.",
         call. = FALSE)
  }

  source_col <- if (is.null(gsr_col)) {
    .gpbiom_choose_gsr_column(data)
  } else {
    gsr_col
  }

  if (is.na(source_col)) {
    stop("No GSR/EDA column was detected. Provide `gsr_col` explicitly.",
         call. = FALSE)
  }

  if (!is.numeric(data[[source_col]])) {
    stop("The selected GSR/EDA column must be numeric.", call. = FALSE)
  }

  out <- data

  tonic_col <- paste0(output_prefix, "_tonic")
  phasic_col <- paste0(output_prefix, "_phasic")
  peak_col <- paste0(output_prefix, "_phasic_peak")
  threshold_col <- paste0(output_prefix, "_phasic_peak_threshold")

  out[[tonic_col]] <- NA_real_
  out[[phasic_col]] <- NA_real_
  out[[peak_col]] <- FALSE
  out[[threshold_col]] <- NA_real_

  groups <- .gpbiom_group_indices(out, group_cols)

  for (indices in groups) {
    ordered_indices <- .gpbiom_order_indices(out, indices, time_col)
    values <- out[[source_col]][ordered_indices]

    tonic <- .gpbiom_rolling_median(values, window_n)
    phasic <- values - tonic

    threshold <- if (is.null(peak_threshold)) {
      .gpbiom_default_phasic_threshold(phasic)
    } else {
      peak_threshold
    }

    peaks <- .gpbiom_phasic_peak_flags(phasic, threshold)

    out[[tonic_col]][ordered_indices] <- tonic
    out[[phasic_col]][ordered_indices] <- phasic
    out[[peak_col]][ordered_indices] <- peaks
    out[[threshold_col]][ordered_indices] <- threshold
  }

  summary <- .gpbiom_tonic_phasic_summary(
    data = out,
    source_col = source_col,
    tonic_col = tonic_col,
    phasic_col = phasic_col,
    peak_col = peak_col,
    threshold_col = threshold_col,
    group_cols = group_cols
  )

  settings <- list(
    gsr_col = source_col,
    group_cols = group_cols,
    time_col = time_col,
    window_n = as.integer(window_n),
    peak_threshold = peak_threshold,
    output_prefix = output_prefix,
    tonic_col = tonic_col,
    phasic_col = phasic_col,
    peak_col = peak_col,
    threshold_col = threshold_col,
    note = paste0(
      "This is a descriptive rolling-median tonic/phasic decomposition, ",
      "not a full EDA deconvolution model."
    )
  )

  list(
    data = out,
    summary = summary,
    settings = settings
  )
}


.gpbiom_existing_conductance_column <- function(data) {
  mapping <- standardise_gazepoint_biometric_names(data, rename = FALSE)
  conductance <- mapping$original_name[mapping$standard_name == "GSR_US"]

  if (length(conductance) == 0L) {
    return(NA_character_)
  }

  conductance[1L]
}


.gpbiom_detect_resistance_column <- function(data) {
  mapping <- standardise_gazepoint_biometric_names(data, rename = FALSE)
  resistance <- mapping$original_name[mapping$standard_name == "GSR_OHMS"]

  if (length(resistance) == 0L) {
    return(NA_character_)
  }

  resistance[1L]
}


.gpbiom_resolve_gsr_input_unit <- function(input_unit, source_standard) {
  if (identical(input_unit, "ohms")) {
    return("ohms")
  }

  if (identical(input_unit, "kohms")) {
    return("kohms")
  }

  if (identical(input_unit, "microsiemens")) {
    return("microsiemens")
  }

  if (identical(input_unit, "auto") &&
      identical(source_standard, "GSR_OHMS")) {
    return("ohms")
  }

  if (identical(input_unit, "auto") &&
      identical(source_standard, "GSR_US")) {
    return("microsiemens")
  }

  "unknown"
}


.gpbiom_gsr_conversion_summary <- function(status,
                                           source_column,
                                           output_column,
                                           input_unit,
                                           n,
                                           n_converted,
                                           n_invalid,
                                           note) {
  data.frame(
    status = status,
    source_column = source_column,
    output_column = output_column,
    input_unit = input_unit,
    n = n,
    n_converted = n_converted,
    n_invalid = n_invalid,
    note = note,
    stringsAsFactors = FALSE
  )
}

.gpbiom_choose_gsr_column <- function(data) {
  mapping <- standardise_gazepoint_biometric_names(data, rename = FALSE)

  preferred <- c("GSR_US", "GSR", "GSR_OHMS")

  recognised_candidates <- character()

  for (standard in preferred) {
    candidate <- mapping$original_name[mapping$standard_name == standard]

    if (length(candidate) == 0L) {
      next
    }

    recognised_candidates <- c(recognised_candidates, candidate)

    numeric_candidate <- candidate[vapply(candidate, function(column) {
      is.numeric(data[[column]])
    }, logical(1))]

    if (length(numeric_candidate) > 0L) {
      return(numeric_candidate[1L])
    }
  }

  if (length(recognised_candidates) > 0L) {
    return(recognised_candidates[1L])
  }

  NA_character_
}

.gpbiom_rolling_median <- function(values, window_n) {
  values <- as.numeric(values)
  n <- length(values)

  if (n == 0L) {
    return(numeric())
  }

  half_window <- floor(window_n / 2)
  out <- rep(NA_real_, n)

  for (i in seq_len(n)) {
    start <- max(1L, i - half_window)
    end <- min(n, i + half_window)

    window_values <- values[start:end]
    window_values <- window_values[!is.na(window_values) & is.finite(window_values)]

    if (length(window_values) > 0L) {
      out[i] <- stats::median(window_values)
    }
  }

  out
}


.gpbiom_default_phasic_threshold <- function(phasic) {
  finite <- phasic[!is.na(phasic) & is.finite(phasic)]

  if (length(finite) == 0L) {
    return(NA_real_)
  }

  robust_scale <- stats::mad(finite, constant = 1.4826, na.rm = TRUE)

  if (!is.finite(robust_scale) || robust_scale == 0) {
    robust_scale <- stats::sd(finite, na.rm = TRUE)
  }

  if (!is.finite(robust_scale) || robust_scale == 0) {
    return(Inf)
  }

  stats::median(finite, na.rm = TRUE) + 2 * robust_scale
}


.gpbiom_phasic_peak_flags <- function(phasic, threshold) {
  n <- length(phasic)
  peaks <- rep(FALSE, n)

  if (n == 0L || !is.finite(threshold)) {
    return(peaks)
  }

  finite <- !is.na(phasic) & is.finite(phasic)

  if (n == 1L) {
    peaks[1L] <- finite[1L] && phasic[1L] > threshold
    return(peaks)
  }

  for (i in seq_len(n)) {
    if (!finite[i] || phasic[i] <= threshold) {
      next
    }

    left_ok <- if (i == 1L) TRUE else !finite[i - 1L] || phasic[i] >= phasic[i - 1L]
    right_ok <- if (i == n) TRUE else !finite[i + 1L] || phasic[i] >= phasic[i + 1L]

    peaks[i] <- left_ok && right_ok
  }

  peaks
}


.gpbiom_tonic_phasic_summary <- function(data,
                                         source_col,
                                         tonic_col,
                                         phasic_col,
                                         peak_col,
                                         threshold_col,
                                         group_cols) {
  if (length(group_cols) == 0L) {
    return(.gpbiom_tonic_phasic_one_summary(
      data = data,
      group = "all",
      source_col = source_col,
      tonic_col = tonic_col,
      phasic_col = phasic_col,
      peak_col = peak_col,
      threshold_col = threshold_col
    ))
  }

  split_key <- interaction(data[group_cols], drop = TRUE, lex.order = TRUE)
  indices <- split(seq_len(nrow(data)), split_key)

  rows <- lapply(names(indices), function(group_name) {
    .gpbiom_tonic_phasic_one_summary(
      data = data[indices[[group_name]], , drop = FALSE],
      group = group_name,
      source_col = source_col,
      tonic_col = tonic_col,
      phasic_col = phasic_col,
      peak_col = peak_col,
      threshold_col = threshold_col
    )
  })

  do.call(rbind, rows)
}


.gpbiom_tonic_phasic_one_summary <- function(data,
                                             group,
                                             source_col,
                                             tonic_col,
                                             phasic_col,
                                             peak_col,
                                             threshold_col) {
  signal <- data[[source_col]]
  tonic <- data[[tonic_col]]
  phasic <- data[[phasic_col]]

  finite_signal <- signal[!is.na(signal) & is.finite(signal)]
  finite_tonic <- tonic[!is.na(tonic) & is.finite(tonic)]
  finite_phasic <- phasic[!is.na(phasic) & is.finite(phasic)]

  positive_phasic <- finite_phasic[finite_phasic > 0]

  data.frame(
    group = group,
    n_rows = nrow(data),
    source_column = source_col,
    n_signal_finite = length(finite_signal),
    mean_signal = if (length(finite_signal) > 0L) mean(finite_signal) else NA_real_,
    median_signal = if (length(finite_signal) > 0L) stats::median(finite_signal) else NA_real_,
    mean_tonic = if (length(finite_tonic) > 0L) mean(finite_tonic) else NA_real_,
    median_tonic = if (length(finite_tonic) > 0L) stats::median(finite_tonic) else NA_real_,
    mean_phasic = if (length(finite_phasic) > 0L) mean(finite_phasic) else NA_real_,
    median_phasic = if (length(finite_phasic) > 0L) stats::median(finite_phasic) else NA_real_,
    max_phasic = if (length(finite_phasic) > 0L) max(finite_phasic) else NA_real_,
    min_phasic = if (length(finite_phasic) > 0L) min(finite_phasic) else NA_real_,
    positive_phasic_sum = if (length(positive_phasic) > 0L) sum(positive_phasic) else 0,
    n_phasic_peaks = sum(data[[peak_col]], na.rm = TRUE),
    peak_threshold = unique(data[[threshold_col]][!is.na(data[[threshold_col]])])[1L],
    stringsAsFactors = FALSE
  )
}
