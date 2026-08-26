#' Prepare Gazepoint EDA data for CTSI sparse deconvolution workflows
#'
#' Prepares signal, event, and configuration tables for downstream
#' continuous-time system identification (CTSI) sparse EDA deconvolution
#' workflows. This function does not implement the full Amin-Faghih CTSI solver
#' in R. It creates reproducible input objects and optional CSV files for
#' external CTSI implementations.
#'
#' @param dat A data frame containing EDA data.
#' @param eda_col Numeric EDA/conductance column.
#' @param time_col Numeric time column.
#' @param group_cols Optional grouping columns, such as participant/session.
#' @param event_onset_col Optional event onset column.
#' @param event_name_col Optional event/condition column.
#' @param sampling_rate Optional sampling rate in Hz.
#' @param tau0_range Candidate slow time-constant range.
#' @param tau1_range Candidate fast time-constant range.
#' @param sparsity_grid Candidate sparsity penalties.
#' @param output_dir Optional directory for CSV export.
#' @param prefix Output file prefix.
#'
#' @return A list with `overview`, `signal_table`, `event_table`,
#'   `ctsi_config`, `ctsi_notes`, `written_files`, and `settings`.
#' @export
prepare_gazepoint_ctsi_input <- function(dat,
                                         eda_col = "GSR_US",
                                         time_col = "CNT",
                                         group_cols = NULL,
                                         event_onset_col = NULL,
                                         event_name_col = NULL,
                                         sampling_rate = NULL,
                                         tau0_range = c(2, 4),
                                         tau1_range = c(0.5, 1),
                                         sparsity_grid = c(0.001, 0.01, 0.1, 1),
                                         output_dir = NULL,
                                         prefix = "gazepoint_ctsi") {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  required <- c(eda_col, time_col, group_cols, event_onset_col, event_name_col)
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

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  signal_table <- data.frame(
    time = dat[[time_col]],
    conductance = dat[[eda_col]],
    stringsAsFactors = FALSE
  )

  for (group_col in group_cols) {
    signal_table[[group_col]] <- dat[[group_col]]
  }

  signal_table <- signal_table[is.finite(signal_table$time), , drop = FALSE]
  signal_table <- signal_table[order(signal_table$time), , drop = FALSE]

  if (is.null(sampling_rate)) {
    sampling_rate <- gpbiometrics_ctsi_sampling_rate(signal_table$time)
  }

  event_table <- data.frame()

  if (!is.null(event_onset_col)) {
    event_table <- data.frame(
      onset = dat[[event_onset_col]],
      event_name = if (!is.null(event_name_col)) {
        as.character(dat[[event_name_col]])
      } else {
        "event"
      },
      stringsAsFactors = FALSE
    )

    for (group_col in group_cols) {
      event_table[[group_col]] <- dat[[group_col]]
    }

    event_table <- unique(event_table[is.finite(event_table$onset), , drop = FALSE])
    event_table <- event_table[order(event_table$onset), , drop = FALSE]
  }

  ctsi_config <- expand.grid(
    tau0 = seq(tau0_range[1], tau0_range[2], length.out = 5),
    tau1 = seq(tau1_range[1], tau1_range[2], length.out = 3),
    sparsity_lambda = sparsity_grid,
    KEEP.OUT.ATTRS = FALSE,
    stringsAsFactors = FALSE
  )

  ctsi_config <- ctsi_config[ctsi_config$tau0 > ctsi_config$tau1, , drop = FALSE]
  ctsi_config$sampling_rate_hz <- sampling_rate

  ctsi_notes <- c(
    "This object prepares Gazepoint EDA data for downstream CTSI sparse deconvolution workflows.",
    "It does not implement the full continuous-time system-identification solver inside R.",
    "The signal table should be checked for units, sampling rate, missingness, and filtering before external CTSI fitting.",
    "The configuration grid records candidate physiological time constants and sparsity penalties.",
    "CTSI-derived latent-driver estimates should not be interpreted as direct emotion, stress, cognition, health status, or diagnosis."
  )

  written_files <- character()

  if (!is.null(output_dir)) {
    if (!dir.exists(output_dir)) {
      dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
    }

    signal_file <- file.path(output_dir, paste0(prefix, "_signal.csv"))
    utils::write.csv(signal_table, signal_file, row.names = FALSE)
    written_files <- c(written_files, signal_file)

    config_file <- file.path(output_dir, paste0(prefix, "_config.csv"))
    utils::write.csv(ctsi_config, config_file, row.names = FALSE)
    written_files <- c(written_files, config_file)

    if (nrow(event_table) > 0) {
      event_file <- file.path(output_dir, paste0(prefix, "_events.csv"))
      utils::write.csv(event_table, event_file, row.names = FALSE)
      written_files <- c(written_files, event_file)
    }

    notes_file <- file.path(output_dir, paste0(prefix, "_notes.txt"))
    writeLines(ctsi_notes, notes_file, useBytes = TRUE)
    written_files <- c(written_files, notes_file)
  }

  overview <- data.frame(
    signal_rows = nrow(signal_table),
    event_rows = nrow(event_table),
    config_rows = nrow(ctsi_config),
    sampling_rate_hz = sampling_rate,
    output_written = length(written_files) > 0,
    status = if (nrow(signal_table) > 0 && nrow(ctsi_config) > 0) {
      "ctsi_input_prepared"
    } else {
      "ctsi_input_incomplete"
    },
    interpretation = paste(
      "Prepared tables are an interoperability bridge for CTSI sparse EDA deconvolution.",
      "They do not constitute CTSI model fitting or psychological-state inference."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      signal_table = signal_table,
      event_table = event_table,
      ctsi_config = ctsi_config,
      ctsi_notes = ctsi_notes,
      written_files = written_files,
      settings = list(
        eda_col = eda_col,
        time_col = time_col,
        group_cols = group_cols,
        event_onset_col = event_onset_col,
        event_name_col = event_name_col,
        sampling_rate = sampling_rate,
        tau0_range = tau0_range,
        tau1_range = tau1_range,
        sparsity_grid = sparsity_grid,
        output_dir = output_dir,
        prefix = prefix
      )
    ),
    class = c("gazepoint_ctsi_input", "list")
  )
}

gpbiometrics_ctsi_sampling_rate <- function(time) {
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
