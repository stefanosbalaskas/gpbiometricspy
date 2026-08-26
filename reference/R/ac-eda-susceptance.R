#' Analyse AC EDA admittance and susceptance recordings
#'
#' Computes summaries for specialised alternating-current EDA recordings. This
#' function is for true AC admittance/susceptance data, not ordinary DC
#' skin-conductance columns such as `GSR_US`.
#'
#' @param dat A data frame.
#' @param conductance_col Optional real conductance component column.
#' @param susceptance_col Optional imaginary susceptance component column.
#' @param admittance_col Optional admittance magnitude column.
#' @param phase_col Optional phase angle column.
#' @param frequency_col Optional AC frequency column.
#' @param time_col Optional time column.
#' @param group_cols Optional grouping columns.
#'
#' @return A list with `overview`, `timeseries`, `summary`, and `settings`.
#' @export
analyze_gazepoint_ac_susceptance <- function(dat,
                                             conductance_col = NULL,
                                             susceptance_col = NULL,
                                             admittance_col = NULL,
                                             phase_col = NULL,
                                             frequency_col = NULL,
                                             time_col = NULL,
                                             group_cols = NULL) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  supplied_signal_cols <- c(conductance_col, susceptance_col, admittance_col, phase_col)
  supplied_signal_cols <- supplied_signal_cols[!is.null(supplied_signal_cols)]

  if (length(supplied_signal_cols) == 0) {
    stop(
      "Supply at least one AC EDA signal column, such as `conductance_col`, `susceptance_col`, `admittance_col`, or `phase_col`.",
      call. = FALSE
    )
  }

  required <- c(supplied_signal_cols, frequency_col, time_col)
  required <- required[!is.null(required)]

  missing_required <- setdiff(required, names(dat))

  if (length(missing_required) > 0) {
    stop("Missing required columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  non_numeric <- required[!vapply(dat[required], is.numeric, logical(1))]
  if (length(non_numeric) > 0) {
    stop("These required columns are not numeric: ", paste(non_numeric, collapse = ", "), call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  missing_groups <- setdiff(group_cols, names(dat))
  if (length(missing_groups) > 0) {
    stop("Missing `group_cols`: ", paste(missing_groups, collapse = ", "), call. = FALSE)
  }

  timeseries <- dat

  g <- if (!is.null(conductance_col)) {
    dat[[conductance_col]]
  } else {
    rep(NA_real_, nrow(dat))
  }

  b <- if (!is.null(susceptance_col)) {
    dat[[susceptance_col]]
  } else {
    rep(NA_real_, nrow(dat))
  }

  admittance <- if (!is.null(admittance_col)) {
    dat[[admittance_col]]
  } else if (!all(is.na(g)) && !all(is.na(b))) {
    sqrt(g^2 + b^2)
  } else {
    rep(NA_real_, nrow(dat))
  }

  phase <- if (!is.null(phase_col)) {
    dat[[phase_col]]
  } else if (!all(is.na(g)) && !all(is.na(b))) {
    atan2(b, g)
  } else {
    rep(NA_real_, nrow(dat))
  }

  timeseries$ac_eda_conductance_component <- g
  timeseries$ac_eda_susceptance_component <- b
  timeseries$ac_eda_admittance_magnitude <- admittance
  timeseries$ac_eda_phase_radians <- phase

  if (!is.null(frequency_col)) {
    timeseries$ac_eda_frequency <- dat[[frequency_col]]
  } else {
    timeseries$ac_eda_frequency <- NA_real_
  }

  summary_group_cols <- c(group_cols, if (!is.null(frequency_col)) "ac_eda_frequency" else NULL)

  groups <- if (length(summary_group_cols) == 0) {
    list(all_rows = seq_len(nrow(timeseries)))
  } else {
    gpbiometrics_aceda_split(timeseries, summary_group_cols)
  }

  summary_rows <- lapply(names(groups), function(group_id) {
    idx <- groups[[group_id]]

    data.frame(
      group_id = group_id,
      n_rows = length(idx),
      mean_conductance_component = mean(timeseries$ac_eda_conductance_component[idx], na.rm = TRUE),
      mean_susceptance_component = mean(timeseries$ac_eda_susceptance_component[idx], na.rm = TRUE),
      mean_admittance_magnitude = mean(timeseries$ac_eda_admittance_magnitude[idx], na.rm = TRUE),
      mean_phase_radians = mean(timeseries$ac_eda_phase_radians[idx], na.rm = TRUE),
      sd_admittance_magnitude = stats::sd(timeseries$ac_eda_admittance_magnitude[idx], na.rm = TRUE),
      status = "ac_eda_summary_created",
      stringsAsFactors = FALSE
    )
  })

  summary <- do.call(rbind, summary_rows)
  rownames(summary) <- NULL

  overview <- data.frame(
    input_rows = nrow(dat),
    output_rows = nrow(timeseries),
    summary_rows = nrow(summary),
    status = "ac_eda_susceptance_analysis_complete",
    interpretation = paste(
      "AC EDA outputs describe admittance, susceptance, and phase properties when true AC recordings are available.",
      "They are not compatible with ordinary DC GSR_US alone and do not infer emotion, stress, cognition, health status, or diagnosis."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      timeseries = timeseries,
      summary = summary,
      settings = list(
        conductance_col = conductance_col,
        susceptance_col = susceptance_col,
        admittance_col = admittance_col,
        phase_col = phase_col,
        frequency_col = frequency_col,
        time_col = time_col,
        group_cols = group_cols
      )
    ),
    class = c("gazepoint_ac_susceptance", "list")
  )
}

gpbiometrics_aceda_split <- function(dat, group_cols) {
  gf <- dat[group_cols]
  gf[] <- lapply(gf, function(x) {
    x <- as.character(x)
    x[is.na(x)] <- "<NA>"
    x
  })

  split(seq_len(nrow(dat)), do.call(paste, c(gf, sep = " | ")))
}
