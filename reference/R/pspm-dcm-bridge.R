#' Prepare Gazepoint EDA data for PsPM DCM workflows
#'
#' Prepares Gazepoint EDA data and event metadata for downstream PsPM dynamic
#' causal modelling workflows. This function does not run PsPM or invert a DCM
#' model in R. It creates structured input tables and notes for MATLAB/PsPM.
#'
#' @param dat A data frame containing EDA data.
#' @param eda_col Numeric EDA/conductance column.
#' @param time_col Numeric time column.
#' @param event_onset_col Optional event onset column.
#' @param event_duration_col Optional event duration column.
#' @param event_name_col Optional event name/condition column.
#' @param participant_col Optional participant column.
#' @param session_col Optional session column.
#' @param sampling_rate Optional sampling rate in Hz.
#' @param output_dir Optional directory for CSV export.
#' @param prefix File prefix when `output_dir` is supplied.
#'
#' @return A list with `overview`, `signal_table`, `event_table`,
#'   `pspm_notes`, `written_files`, and `settings`.
#' @export
prepare_gazepoint_pspm_dcm_input <- function(dat,
                                             eda_col = "GSR_US",
                                             time_col = "CNT",
                                             event_onset_col = NULL,
                                             event_duration_col = NULL,
                                             event_name_col = NULL,
                                             participant_col = NULL,
                                             session_col = NULL,
                                             sampling_rate = NULL,
                                             output_dir = NULL,
                                             prefix = "gazepoint_pspm_dcm") {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  required <- c(
    eda_col,
    time_col,
    event_onset_col,
    event_duration_col,
    event_name_col,
    participant_col,
    session_col
  )

  required <- required[!is.null(required)]

  missing_required <- setdiff(required, names(dat))

  if (length(missing_required) > 0) {
    stop("Missing required columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  if (!is.numeric(dat[[eda_col]])) {
    stop("`eda_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.numeric(dat[[time_col]])) {
    stop("`time_col` must identify a numeric column.", call. = FALSE)
  }

  signal_table <- data.frame(
    time = dat[[time_col]],
    conductance = dat[[eda_col]],
    stringsAsFactors = FALSE
  )

  if (!is.null(participant_col)) {
    signal_table$participant <- dat[[participant_col]]
  }

  if (!is.null(session_col)) {
    signal_table$session <- dat[[session_col]]
  }

  signal_table <- signal_table[is.finite(signal_table$time), , drop = FALSE]
  signal_table <- signal_table[order(signal_table$time), , drop = FALSE]

  if (is.null(sampling_rate)) {
    sampling_rate <- gpbiometrics_pspm_dcm_sampling_rate(signal_table$time)
  }

  event_table <- data.frame()

  if (!is.null(event_onset_col)) {
    event_table <- data.frame(
      onset = dat[[event_onset_col]],
      duration = if (!is.null(event_duration_col)) {
        dat[[event_duration_col]]
      } else {
        0
      },
      name = if (!is.null(event_name_col)) {
        as.character(dat[[event_name_col]])
      } else {
        "event"
      },
      stringsAsFactors = FALSE
    )

    if (!is.null(participant_col)) {
      event_table$participant <- dat[[participant_col]]
    }

    if (!is.null(session_col)) {
      event_table$session <- dat[[session_col]]
    }

    event_table <- unique(event_table[is.finite(event_table$onset), , drop = FALSE])
    event_table <- event_table[order(event_table$onset), , drop = FALSE]
  }

  pspm_notes <- c(
    "This object prepares Gazepoint EDA signal and event tables for downstream PsPM DCM workflows.",
    "It does not run MATLAB, PsPM, Bayesian model inversion, or DCM estimation inside R.",
    "Use the signal table as the observed skin-conductance time series and the event table as model input/onset metadata.",
    "Verify PsPM version, units, sampling rate, filtering, event timing, and participant/session splitting before model inversion.",
    "DCM outputs should be interpreted as model-based estimates of latent sudomotor drivers under the chosen model, not direct psychological labels."
  )

  written_files <- character()

  if (!is.null(output_dir)) {
    if (!dir.exists(output_dir)) {
      dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
    }

    signal_file <- file.path(output_dir, paste0(prefix, "_signal.csv"))
    utils::write.csv(signal_table, signal_file, row.names = FALSE)
    written_files <- c(written_files, signal_file)

    if (nrow(event_table) > 0) {
      event_file <- file.path(output_dir, paste0(prefix, "_events.csv"))
      utils::write.csv(event_table, event_file, row.names = FALSE)
      written_files <- c(written_files, event_file)
    }

    notes_file <- file.path(output_dir, paste0(prefix, "_notes.txt"))
    writeLines(pspm_notes, notes_file, useBytes = TRUE)
    written_files <- c(written_files, notes_file)
  }

  overview <- data.frame(
    signal_rows = nrow(signal_table),
    event_rows = nrow(event_table),
    sampling_rate_hz = sampling_rate,
    output_written = length(written_files) > 0,
    status = if (nrow(signal_table) > 0) {
      "pspm_dcm_input_prepared"
    } else {
      "pspm_dcm_input_empty_signal"
    },
    interpretation = paste(
      "Prepared tables are an interoperability bridge for PsPM DCM workflows.",
      "They do not constitute DCM estimation or psychological-state inference."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      signal_table = signal_table,
      event_table = event_table,
      pspm_notes = pspm_notes,
      written_files = written_files,
      settings = list(
        eda_col = eda_col,
        time_col = time_col,
        event_onset_col = event_onset_col,
        event_duration_col = event_duration_col,
        event_name_col = event_name_col,
        participant_col = participant_col,
        session_col = session_col,
        sampling_rate = sampling_rate,
        output_dir = output_dir,
        prefix = prefix
      )
    ),
    class = c("gazepoint_pspm_dcm_input", "list")
  )
}

gpbiometrics_pspm_dcm_sampling_rate <- function(time) {
  time <- time[is.finite(time)]

  if (length(time) < 3) {
    return(NA_real_)
  }

  dt <- diff(time)
  dt <- dt[is.finite(dt) & dt > 0]

  if (length(dt) == 0) {
    return(NA_real_)
  }

  median_dt <- stats::median(dt)

  if (median_dt > 10) {
    1000 / median_dt
  } else {
    1 / median_dt
  }
}
