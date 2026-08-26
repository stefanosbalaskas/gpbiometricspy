#' Audit likely GSR/EDA units
#'
#' Checks whether a Gazepoint GSR/EDA column looks more like conductance
#' in microSiemens or resistance/impedance-like values in Ohms. This is a
#' preprocessing safety audit, not a definitive device calibration test.
#'
#' @param dat A data frame.
#' @param gsr_col Name of the GSR/EDA column to audit.
#' @param convert Logical. If `TRUE`, add a conductance-converted column when
#'   the signal is likely resistance/impedance-like.
#' @param output_col Output column used when `convert = TRUE`.
#' @param resistance_to_us_factor Conversion factor. For Ohms to microSiemens,
#'   use `1000000 / resistance`.
#'
#' @return A list with `overview`, `diagnostics`, `recommendation`, and,
#'   when requested, `data`.
#' @export
audit_gazepoint_gsr_units <- function(dat,
                                      gsr_col = "GSR",
                                      convert = FALSE,
                                      output_col = NULL,
                                      resistance_to_us_factor = 1000000) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  if (!gsr_col %in% names(dat)) {
    stop("Column `", gsr_col, "` was not found in `dat`.", call. = FALSE)
  }

  x <- dat[[gsr_col]]

  if (!is.numeric(x)) {
    stop("`gsr_col` must identify a numeric column.", call. = FALSE)
  }

  finite_x <- x[is.finite(x)]

  if (length(finite_x) == 0) {
    stop("`gsr_col` contains no finite numeric values.", call. = FALSE)
  }

  q <- stats::quantile(
    finite_x,
    probs = c(0, 0.01, 0.25, 0.5, 0.75, 0.99, 1),
    na.rm = TRUE,
    names = FALSE
  )

  names(q) <- c("min", "q01", "q25", "median", "q75", "q99", "max")

  col_lower <- tolower(gsr_col)

  likely_unit <- "ambiguous"
  confidence <- "low"

  if (grepl("_us$|us$|microsiemens|micro_siemens|conductance", col_lower)) {
    likely_unit <- "conductance_microSiemens"
    confidence <- "high_column_name"
  } else if (q["median"] > 1000 || q["q75"] > 1000) {
    likely_unit <- "resistance_or_impedance_ohms"
    confidence <- "high_numeric_range"
  } else if (q["median"] > 0 && q["median"] <= 100 && q["q99"] <= 500) {
    likely_unit <- "conductance_microSiemens"
    confidence <- "moderate_numeric_range"
  } else if (q["median"] > 100 && q["median"] <= 1000) {
    likely_unit <- "ambiguous_large_conductance_or_scaled_signal"
    confidence <- "low_numeric_range"
  }

  threshold_warning <- if (likely_unit == "resistance_or_impedance_ohms") {
    paste(
      "Do not apply SCR thresholds expressed in microSiemens directly to this column.",
      "Convert resistance-like values to conductance first or use a verified conductance column such as GSR_US."
    )
  } else if (likely_unit == "conductance_microSiemens") {
    "SCR thresholds expressed in microSiemens may be appropriate if the column is verified as conductance."
  } else {
    "Verify device/export documentation before applying SCR thresholds."
  }

  diagnostics <- data.frame(
    gsr_col = gsr_col,
    n_rows = length(x),
    n_finite = length(finite_x),
    missing_rate = mean(!is.finite(x)),
    min = q["min"],
    q01 = q["q01"],
    q25 = q["q25"],
    median = q["median"],
    q75 = q["q75"],
    q99 = q["q99"],
    max = q["max"],
    likely_unit = likely_unit,
    confidence = confidence,
    stringsAsFactors = FALSE
  )

  overview <- data.frame(
    gsr_col = gsr_col,
    likely_unit = likely_unit,
    confidence = confidence,
    convert_requested = isTRUE(convert),
    status = if (likely_unit == "resistance_or_impedance_ohms") {
      "unit_warning_resistance_like"
    } else if (likely_unit == "conductance_microSiemens") {
      "unit_audit_conductance_like"
    } else {
      "unit_audit_ambiguous"
    },
    interpretation = paste(
      "This audit uses column names and numerical ranges to flag likely GSR/EDA units.",
      "It is a preprocessing sanity check and does not replace device/export documentation."
    ),
    stringsAsFactors = FALSE
  )

  recommendation <- data.frame(
    gsr_col = gsr_col,
    likely_unit = likely_unit,
    recommendation = threshold_warning,
    stringsAsFactors = FALSE
  )

  result <- list(
    overview = overview,
    diagnostics = diagnostics,
    recommendation = recommendation,
    settings = list(
      gsr_col = gsr_col,
      convert = convert,
      output_col = output_col,
      resistance_to_us_factor = resistance_to_us_factor
    )
  )

  if (isTRUE(convert)) {
    if (is.null(output_col)) {
      output_col <- paste0(gsr_col, "_converted_us")
    }

    out <- dat

    if (likely_unit == "resistance_or_impedance_ohms") {
      out[[output_col]] <- ifelse(
        is.finite(out[[gsr_col]]) & out[[gsr_col]] > 0,
        resistance_to_us_factor / out[[gsr_col]],
        NA_real_
      )
      attr(out, "gsr_unit_conversion") <- "resistance_or_impedance_to_microSiemens"
    } else {
      out[[output_col]] <- out[[gsr_col]]
      attr(out, "gsr_unit_conversion") <- "copied_without_conversion_unit_not_resistance_like"
    }

    result$data <- out
  }

  class(result) <- c("gazepoint_gsr_unit_audit", "list")
  result
}
