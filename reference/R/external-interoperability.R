#' Export Gazepoint IBI data for RHRV-style workflows
#'
#' Prepares cleaned inter-beat interval data for external HRV workflows. The
#' helper writes simple beat tables with cumulative beat time and IBI/RR interval
#' columns. It does not use the Gazepoint `HRV` column.
#'
#' @param data A Gazepoint biometric data frame or `gazepoint_ibi_filter` object.
#' @param ibi_col IBI/RR interval column.
#' @param group_cols Optional grouping columns.
#' @param unit Unit of the IBI column: `"auto"`, `"ms"`, or `"seconds"`.
#' @param collapse_repeated_intervals Logical. If `TRUE`, consecutive repeated
#'   IBI values are collapsed before export.
#' @param repeated_tolerance_ms Numeric tolerance used when identifying repeated
#'   consecutive IBI values.
#' @param min_ibi_ms Minimum plausible IBI in milliseconds retained for export.
#' @param max_ibi_ms Maximum plausible IBI in milliseconds retained for export.
#' @param output_dir Optional directory where per-group CSV files are written.
#' @param prefix File prefix used when `output_dir` is supplied.
#'
#' @return A list with `overview`, `beat_table`, `group_summary`, `manifest`,
#'   and `settings`.
#' @export
export_gazepoint_rhrv_input <- function(data,
                                        ibi_col = "IBI_clean_ms",
                                        group_cols = NULL,
                                        unit = c("auto", "ms", "seconds"),
                                        collapse_repeated_intervals = TRUE,
                                        repeated_tolerance_ms = 1e-8,
                                        min_ibi_ms = 300,
                                        max_ibi_ms = 2000,
                                        output_dir = NULL,
                                        prefix = "gazepoint_rhrv") {
  unit <- match.arg(unit)

  dat <- gpbiometrics_external_extract_data(data)

  if (!ibi_col %in% names(dat)) {
    stop("`ibi_col` was not found in `data`.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- gpbiometrics_external_default_group_cols(names(dat))
  }

  missing_groups <- setdiff(group_cols, names(dat))

  if (length(missing_groups) > 0) {
    stop(
      "`group_cols` were not found in `data`: ",
      paste(missing_groups, collapse = ", "),
      call. = FALSE
    )
  }

  if (!is.logical(collapse_repeated_intervals) ||
      length(collapse_repeated_intervals) != 1 ||
      is.na(collapse_repeated_intervals)) {
    stop("`collapse_repeated_intervals` must be TRUE or FALSE.", call. = FALSE)
  }

  gpbiometrics_external_validate_nonnegative_scalar(
    repeated_tolerance_ms,
    "repeated_tolerance_ms"
  )
  gpbiometrics_external_validate_positive_scalar(min_ibi_ms, "min_ibi_ms")
  gpbiometrics_external_validate_positive_scalar(max_ibi_ms, "max_ibi_ms")

  if (max_ibi_ms <= min_ibi_ms) {
    stop("`max_ibi_ms` must be greater than `min_ibi_ms`.", call. = FALSE)
  }

  ibi_raw <- suppressWarnings(as.numeric(dat[[ibi_col]]))
  detected_unit <- gpbiometrics_external_detect_ibi_unit(ibi_raw, unit)
  ibi_ms <- if (identical(detected_unit, "seconds")) ibi_raw * 1000 else ibi_raw

  dat$.ibi_export_ms <- ibi_ms
  dat$.group_id <- gpbiometrics_external_group_id(dat, group_cols)

  group_ids <- unique(dat$.group_id)

  beat_tables <- lapply(group_ids, function(group_id) {
    d <- dat[dat$.group_id == group_id, , drop = FALSE]
    x <- d$.ibi_export_ms
    x <- x[is.finite(x) & x >= min_ibi_ms & x <= max_ibi_ms]

    input_interval_rows <- length(x)

    if (isTRUE(collapse_repeated_intervals)) {
      x <- gpbiometrics_external_collapse_repeated_intervals(
        x,
        tolerance_ms = repeated_tolerance_ms
      )
    }

    beat_table <- data.frame(
      group_id = rep(group_id, length(x)),
      beat_index = seq_along(x),
      time_s = cumsum(x) / 1000,
      ibi_ms = x,
      ibi_s = x / 1000,
      stringsAsFactors = FALSE
    )

    beat_table$input_interval_rows <- rep(as.integer(input_interval_rows), nrow(beat_table))
    beat_table$output_interval_rows <- rep(as.integer(length(x)), nrow(beat_table))
    beat_table$used_intervals_after_collapse <- rep(as.integer(length(x)), nrow(beat_table))

    if (length(group_cols) > 0 && nrow(d) > 0 &&
        all(group_cols %in% names(d))) {
      beat_table <- cbind(d[rep(1, nrow(beat_table)), group_cols, drop = FALSE], beat_table)
    }

    beat_table
  })

  beat_table <- do.call(rbind, beat_tables)
  rownames(beat_table) <- NULL

  group_summary <- gpbiometrics_external_rhrv_group_summary(
    beat_table = beat_table,
    group_cols = group_cols
  )

  manifest <- gpbiometrics_external_write_group_files(
    data = beat_table,
    group_cols = group_cols,
    output_dir = output_dir,
    prefix = prefix,
    suffix = "rhrv_input"
  )

  overview <- data.frame(
    input_rows = nrow(dat),
    beat_rows = nrow(beat_table),
    group_count = length(group_ids),
    detected_ibi_unit = detected_unit,
    collapse_repeated_intervals = collapse_repeated_intervals,
    files_written = sum(!is.na(manifest$file_path)),
    status = if (nrow(beat_table) == 0) {
      "fail_no_ibi_rows_for_export"
    } else if (!is.null(output_dir)) {
      "rhrv_input_exported"
    } else {
      "rhrv_input_prepared"
    },
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      beat_table = beat_table,
      group_summary = group_summary,
      manifest = manifest,
      settings = list(
        ibi_col = ibi_col,
        group_cols = group_cols,
        unit = unit,
        detected_ibi_unit = detected_unit,
        collapse_repeated_intervals = collapse_repeated_intervals,
        repeated_tolerance_ms = repeated_tolerance_ms,
        min_ibi_ms = min_ibi_ms,
        max_ibi_ms = max_ibi_ms,
        output_dir = output_dir,
        prefix = prefix,
        interpretation_notes = c(
          "The export uses genuine IBI/RR intervals only.",
          "The Gazepoint HRV column is not used.",
          "External HRV software may require additional formatting depending on the selected workflow."
        )
      )
    ),
    class = c("gazepoint_rhrv_input_export", "list")
  )
}

#' Prepare Gazepoint EDA input for NeuroKit2-style workflows
#'
#' Prepares EDA/GSR signal tables for optional external NeuroKit2 processing.
#' This helper does not require Python or NeuroKit2.
#'
#' @param data A Gazepoint biometric data frame.
#' @param eda_col EDA/GSR signal column.
#' @param time_col Optional time/counter column.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate Optional sampling rate in Hz.
#' @param output_dir Optional directory where per-group CSV files are written.
#' @param prefix File prefix used when `output_dir` is supplied.
#'
#' @return A list with `overview`, `eda_table`, `group_summary`, `manifest`,
#'   and `settings`.
#' @export
prepare_gazepoint_neurokit_eda_input <- function(data,
                                                 eda_col = "GSR_US",
                                                 time_col = NULL,
                                                 group_cols = NULL,
                                                 sampling_rate = NULL,
                                                 output_dir = NULL,
                                                 prefix = "gazepoint_neurokit_eda") {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  dat <- as.data.frame(data, stringsAsFactors = FALSE)

  if (!eda_col %in% names(dat)) {
    stop("`eda_col` was not found in `data`.", call. = FALSE)
  }

  if (!is.null(time_col) && !time_col %in% names(dat)) {
    stop("`time_col` was not found in `data`.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- gpbiometrics_external_default_group_cols(names(dat))
  }

  missing_groups <- setdiff(group_cols, names(dat))

  if (length(missing_groups) > 0) {
    stop(
      "`group_cols` were not found in `data`: ",
      paste(missing_groups, collapse = ", "),
      call. = FALSE
    )
  }

  if (!is.null(sampling_rate)) {
    gpbiometrics_external_validate_positive_scalar(sampling_rate, "sampling_rate")
  }

  dat$.group_id <- gpbiometrics_external_group_id(dat, group_cols)
  group_ids <- unique(dat$.group_id)

  eda_tables <- lapply(group_ids, function(group_id) {
    d <- dat[dat$.group_id == group_id, , drop = FALSE]

    eda <- suppressWarnings(as.numeric(d[[eda_col]]))
    sample_index <- seq_along(eda)

    time_raw <- if (!is.null(time_col)) {
      suppressWarnings(as.numeric(d[[time_col]]))
    } else {
      sample_index - 1
    }

    time_s <- gpbiometrics_external_time_seconds(
      time_raw = time_raw,
      sampling_rate = sampling_rate
    )

    out <- data.frame(
      group_id = group_id,
      sample_index = sample_index,
      time_raw = time_raw,
      time_s = time_s,
      eda = eda,
      stringsAsFactors = FALSE
    )

    if (length(group_cols) > 0 && all(group_cols %in% names(d))) {
      out <- cbind(d[, group_cols, drop = FALSE], out)
    }

    out
  })

  eda_table <- do.call(rbind, eda_tables)
  rownames(eda_table) <- NULL

  group_summary <- gpbiometrics_external_eda_group_summary(
    eda_table = eda_table,
    group_cols = group_cols
  )

  manifest <- gpbiometrics_external_write_group_files(
    data = eda_table,
    group_cols = group_cols,
    output_dir = output_dir,
    prefix = prefix,
    suffix = "neurokit_eda_input"
  )

  overview <- data.frame(
    input_rows = nrow(dat),
    eda_rows = nrow(eda_table),
    group_count = length(group_ids),
    eda_col = eda_col,
    sampling_rate = if (is.null(sampling_rate)) NA_real_ else sampling_rate,
    files_written = sum(!is.na(manifest$file_path)),
    status = if (nrow(eda_table) == 0) {
      "fail_no_eda_rows_for_export"
    } else if (!is.null(output_dir)) {
      "neurokit_eda_input_exported"
    } else {
      "neurokit_eda_input_prepared"
    },
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      eda_table = eda_table,
      group_summary = group_summary,
      manifest = manifest,
      settings = list(
        eda_col = eda_col,
        time_col = time_col,
        group_cols = group_cols,
        sampling_rate = sampling_rate,
        output_dir = output_dir,
        prefix = prefix,
        interpretation_notes = c(
          "This helper prepares EDA/GSR input for optional external NeuroKit2 processing.",
          "EDA/GSR reflects sympathetic arousal-related activity and should not be treated as emotional valence.",
          "External NeuroKit2 execution is optional and not required by gpbiometrics."
        )
      )
    ),
    class = c("gazepoint_neurokit_eda_input", "list")
  )
}

#' Optionally run a NeuroKit2 EDA cross-check
#'
#' Optionally calls Python/NeuroKit2 on prepared EDA input. By default,
#' `execute = FALSE`, so no external dependency is required.
#'
#' @param data A Gazepoint biometric data frame or
#'   `gazepoint_neurokit_eda_input` object.
#' @param eda_col EDA/GSR signal column, used when `data` is a data frame.
#' @param time_col Optional time/counter column.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate Sampling rate in Hz required for NeuroKit2 execution.
#' @param execute Logical. If `FALSE`, only prepare input and return skipped
#'   status.
#' @param python Python executable.
#' @param output_dir Directory for temporary/input/output files.
#' @param prefix File prefix.
#' @param keep_files Logical. If `FALSE`, temporary files produced during
#'   execution may be removed.
#'
#' @return A list with `overview`, `prepared_input`, `crosscheck_summary`,
#'   `manifest`, and `settings`.
#' @export
run_gazepoint_neurokit_eda_crosscheck <- function(data,
                                                  eda_col = "GSR_US",
                                                  time_col = NULL,
                                                  group_cols = NULL,
                                                  sampling_rate = NULL,
                                                  execute = FALSE,
                                                  python = "python",
                                                  output_dir = tempdir(),
                                                  prefix = "gazepoint_neurokit_crosscheck",
                                                  keep_files = FALSE) {
  if (!is.logical(execute) || length(execute) != 1 || is.na(execute)) {
    stop("`execute` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.logical(keep_files) || length(keep_files) != 1 || is.na(keep_files)) {
    stop("`keep_files` must be TRUE or FALSE.", call. = FALSE)
  }

  prepared <- if (inherits(data, "gazepoint_neurokit_eda_input")) {
    data
  } else {
    prepare_gazepoint_neurokit_eda_input(
      data = data,
      eda_col = eda_col,
      time_col = time_col,
      group_cols = group_cols,
      sampling_rate = sampling_rate,
      output_dir = NULL,
      prefix = prefix
    )
  }

  if (!isTRUE(execute)) {
    overview <- data.frame(
      input_rows = nrow(prepared$eda_table),
      groups = prepared$overview$group_count,
      executed = FALSE,
      status = "skipped_execute_false",
      message = "Set `execute = TRUE` to run optional Python/NeuroKit2 cross-check.",
      stringsAsFactors = FALSE
    )

    return(structure(
      list(
        overview = overview,
        prepared_input = prepared,
        crosscheck_summary = data.frame(),
        manifest = prepared$manifest,
        settings = list(
          eda_col = eda_col,
          time_col = time_col,
          group_cols = group_cols,
          sampling_rate = sampling_rate,
          execute = execute,
          python = python,
          output_dir = output_dir,
          prefix = prefix,
          keep_files = keep_files
        )
      ),
      class = c("gazepoint_neurokit_eda_crosscheck", "list")
    ))
  }

  if (is.null(sampling_rate) || !is.finite(sampling_rate) || sampling_rate <= 0) {
    stop("`sampling_rate` must be supplied as a positive finite number when `execute = TRUE`.", call. = FALSE)
  }

  python_path <- Sys.which(python)

  if (identical(unname(python_path), "")) {
    overview <- data.frame(
      input_rows = nrow(prepared$eda_table),
      groups = prepared$overview$group_count,
      executed = FALSE,
      status = "skipped_python_not_found",
      message = paste("Python executable not found:", python),
      stringsAsFactors = FALSE
    )

    return(structure(
      list(
        overview = overview,
        prepared_input = prepared,
        crosscheck_summary = data.frame(),
        manifest = prepared$manifest,
        settings = list(
          eda_col = eda_col,
          time_col = time_col,
          group_cols = group_cols,
          sampling_rate = sampling_rate,
          execute = execute,
          python = python,
          output_dir = output_dir,
          prefix = prefix,
          keep_files = keep_files
        )
      ),
      class = c("gazepoint_neurokit_eda_crosscheck", "list")
    ))
  }

  neurokit_available <- gpbiometrics_external_python_has_neurokit2(
    python_path = python_path
  )

  if (!isTRUE(neurokit_available)) {
    overview <- data.frame(
      input_rows = nrow(prepared$eda_table),
      groups = prepared$overview$group_count,
      executed = FALSE,
      status = "skipped_neurokit2_not_available",
      message = "Python was found, but neurokit2 could not be imported.",
      stringsAsFactors = FALSE
    )

    return(structure(
      list(
        overview = overview,
        prepared_input = prepared,
        crosscheck_summary = data.frame(),
        manifest = prepared$manifest,
        settings = list(
          eda_col = eda_col,
          time_col = time_col,
          group_cols = group_cols,
          sampling_rate = sampling_rate,
          execute = execute,
          python = python,
          output_dir = output_dir,
          prefix = prefix,
          keep_files = keep_files
        )
      ),
      class = c("gazepoint_neurokit_eda_crosscheck", "list")
    ))
  }

  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

  input_file <- file.path(output_dir, paste0(prefix, "_input.csv"))
  output_file <- file.path(output_dir, paste0(prefix, "_summary.csv"))
  script_file <- file.path(output_dir, paste0(prefix, "_runner.py"))

  utils::write.csv(prepared$eda_table, input_file, row.names = FALSE)

  gpbiometrics_external_write_neurokit_script(
    script_file = script_file,
    input_file = input_file,
    output_file = output_file,
    sampling_rate = sampling_rate
  )

  run_status <- try(
    system2(
      python_path,
      args = script_file,
      stdout = TRUE,
      stderr = TRUE
    ),
    silent = TRUE
  )

  if (inherits(run_status, "try-error") || !file.exists(output_file)) {
    overview <- data.frame(
      input_rows = nrow(prepared$eda_table),
      groups = prepared$overview$group_count,
      executed = FALSE,
      status = "neurokit2_execution_failed",
      message = paste(as.character(run_status), collapse = " "),
      stringsAsFactors = FALSE
    )

    return(structure(
      list(
        overview = overview,
        prepared_input = prepared,
        crosscheck_summary = data.frame(),
        manifest = data.frame(
          input_file = input_file,
          output_file = output_file,
          script_file = script_file,
          stringsAsFactors = FALSE
        ),
        settings = list(
          eda_col = eda_col,
          time_col = time_col,
          group_cols = group_cols,
          sampling_rate = sampling_rate,
          execute = execute,
          python = python,
          output_dir = output_dir,
          prefix = prefix,
          keep_files = keep_files
        )
      ),
      class = c("gazepoint_neurokit_eda_crosscheck", "list")
    ))
  }

  crosscheck_summary <- utils::read.csv(output_file, stringsAsFactors = FALSE)

  if (!isTRUE(keep_files)) {
    unlink(c(input_file, script_file), force = TRUE)
  }

  overview <- data.frame(
    input_rows = nrow(prepared$eda_table),
    groups = prepared$overview$group_count,
    executed = TRUE,
    status = "neurokit2_crosscheck_completed",
    message = "Optional NeuroKit2 EDA cross-check completed.",
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      prepared_input = prepared,
      crosscheck_summary = crosscheck_summary,
      manifest = data.frame(
        input_file = if (isTRUE(keep_files)) input_file else NA_character_,
        output_file = output_file,
        script_file = if (isTRUE(keep_files)) script_file else NA_character_,
        stringsAsFactors = FALSE
      ),
      settings = list(
        eda_col = eda_col,
        time_col = time_col,
        group_cols = group_cols,
        sampling_rate = sampling_rate,
        execute = execute,
        python = python,
        output_dir = output_dir,
        prefix = prefix,
        keep_files = keep_files
      )
    ),
    class = c("gazepoint_neurokit_eda_crosscheck", "list")
  )
}

gpbiometrics_external_extract_data <- function(data) {
  if (inherits(data, "gazepoint_ibi_filter") && !is.null(data$data)) {
    return(as.data.frame(data$data, stringsAsFactors = FALSE))
  }

  if (is.data.frame(data)) {
    return(as.data.frame(data, stringsAsFactors = FALSE))
  }

  stop("`data` must be a data frame or a supported gpbiometrics object.", call. = FALSE)
}

gpbiometrics_external_default_group_cols <- function(names_dat) {
  candidates <- c(
    "source_file",
    "source_participant",
    "participant",
    "subject",
    "subject_id",
    "MEDIA_ID",
    "MEDIA_NAME",
    "trial",
    "trial_id",
    "trial_global"
  )

  unique(candidates[candidates %in% names_dat])
}

gpbiometrics_external_group_id <- function(dat, group_cols) {
  if (length(group_cols) == 0) {
    return(rep("all", nrow(dat)))
  }

  group_dat <- dat[group_cols]

  group_dat[] <- lapply(group_dat, function(x) {
    x_chr <- as.character(x)
    x_chr[is.na(x_chr)] <- "<NA>"
    x_chr
  })

  apply(group_dat, 1, paste, collapse = "||")
}

gpbiometrics_external_validate_positive_scalar <- function(x, name) {
  if (!is.numeric(x) || length(x) != 1 || !is.finite(x) || x <= 0) {
    stop("`", name, "` must be a single positive finite number.", call. = FALSE)
  }

  invisible(TRUE)
}

gpbiometrics_external_validate_nonnegative_scalar <- function(x, name) {
  if (!is.numeric(x) || length(x) != 1 || !is.finite(x) || x < 0) {
    stop("`", name, "` must be a single non-negative finite number.", call. = FALSE)
  }

  invisible(TRUE)
}

gpbiometrics_external_detect_ibi_unit <- function(x, unit) {
  if (!identical(unit, "auto")) {
    return(unit)
  }

  finite_x <- x[is.finite(x) & x > 0]

  if (length(finite_x) == 0) {
    return("ms")
  }

  med <- stats::median(finite_x, na.rm = TRUE)

  if (is.finite(med) && med > 0.2 && med < 5) {
    "seconds"
  } else {
    "ms"
  }
}

gpbiometrics_external_collapse_repeated_intervals <- function(x,
                                                              tolerance_ms) {
  if (length(x) <= 1) {
    return(x)
  }

  keep <- c(TRUE, abs(diff(x)) > tolerance_ms)
  x[keep]
}

gpbiometrics_external_time_seconds <- function(time_raw,
                                               sampling_rate = NULL) {
  if (!is.null(sampling_rate)) {
    return((seq_along(time_raw) - 1) / sampling_rate)
  }

  finite_time <- time_raw[is.finite(time_raw)]

  if (length(finite_time) < 2) {
    return(seq_along(time_raw) - 1)
  }

  shifted <- time_raw - min(finite_time, na.rm = TRUE)

  if (max(shifted, na.rm = TRUE) > 10000) {
    shifted / 1000
  } else {
    shifted
  }
}

gpbiometrics_external_rhrv_group_summary <- function(beat_table,
                                                     group_cols) {
  if (nrow(beat_table) == 0) {
    return(data.frame())
  }

  group_ids <- unique(beat_table$group_id)

  out <- lapply(group_ids, function(group_id) {
    d <- beat_table[beat_table$group_id == group_id, , drop = FALSE]

    row <- data.frame(
      group_id = group_id,
      beat_rows = nrow(d),
      duration_s = if (nrow(d) > 0) max(d$time_s, na.rm = TRUE) else NA_real_,
      mean_ibi_ms = mean(d$ibi_ms, na.rm = TRUE),
      median_ibi_ms = stats::median(d$ibi_ms, na.rm = TRUE),
      min_ibi_ms = min(d$ibi_ms, na.rm = TRUE),
      max_ibi_ms = max(d$ibi_ms, na.rm = TRUE),
      input_interval_rows = if ("input_interval_rows" %in% names(d)) d$input_interval_rows[1] else NA_integer_,
      used_intervals_after_collapse = if ("used_intervals_after_collapse" %in% names(d)) d$used_intervals_after_collapse[1] else NA_integer_,
      stringsAsFactors = FALSE
    )

    if (length(group_cols) > 0 && all(group_cols %in% names(d))) {
      row <- cbind(d[1, group_cols, drop = FALSE], row)
    }

    row
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}

gpbiometrics_external_eda_group_summary <- function(eda_table,
                                                    group_cols) {
  if (nrow(eda_table) == 0) {
    return(data.frame())
  }

  group_ids <- unique(eda_table$group_id)

  out <- lapply(group_ids, function(group_id) {
    d <- eda_table[eda_table$group_id == group_id, , drop = FALSE]
    finite_eda <- d$eda[is.finite(d$eda)]

    row <- data.frame(
      group_id = group_id,
      rows = nrow(d),
      finite_rows = length(finite_eda),
      missing_rows = sum(!is.finite(d$eda)),
      mean_eda = if (length(finite_eda) > 0) mean(finite_eda, na.rm = TRUE) else NA_real_,
      median_eda = if (length(finite_eda) > 0) stats::median(finite_eda, na.rm = TRUE) else NA_real_,
      min_time_s = min(d$time_s, na.rm = TRUE),
      max_time_s = max(d$time_s, na.rm = TRUE),
      stringsAsFactors = FALSE
    )

    if (length(group_cols) > 0 && all(group_cols %in% names(d))) {
      row <- cbind(d[1, group_cols, drop = FALSE], row)
    }

    row
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}

gpbiometrics_external_write_group_files <- function(data,
                                                    group_cols,
                                                    output_dir,
                                                    prefix,
                                                    suffix) {
  if (is.null(output_dir)) {
    return(data.frame(
      group_id = unique(data$group_id),
      file_path = NA_character_,
      stringsAsFactors = FALSE
    ))
  }

  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

  group_ids <- unique(data$group_id)

  manifest <- lapply(seq_along(group_ids), function(i) {
    group_id <- group_ids[i]
    d <- data[data$group_id == group_id, , drop = FALSE]

    file_name <- paste0(
      prefix,
      "_",
      sprintf("%03d", i),
      "_",
      gpbiometrics_external_safe_file_name(group_id),
      "_",
      suffix,
      ".csv"
    )

    file_path <- file.path(output_dir, file_name)
    utils::write.csv(d, file_path, row.names = FALSE)

    row <- data.frame(
      group_id = group_id,
      file_path = file_path,
      stringsAsFactors = FALSE
    )

    if (length(group_cols) > 0 && all(group_cols %in% names(d))) {
      row <- cbind(d[1, group_cols, drop = FALSE], row)
    }

    row
  })

  manifest <- do.call(rbind, manifest)
  rownames(manifest) <- NULL

  manifest
}

gpbiometrics_external_safe_file_name <- function(x) {
  x <- gsub("[^A-Za-z0-9_-]+", "_", x)
  x <- gsub("_+", "_", x)
  x <- gsub("^_|_$", "", x)

  if (nchar(x) == 0) {
    "group"
  } else {
    substr(x, 1, 80)
  }
}

gpbiometrics_external_python_has_neurokit2 <- function(python_path) {
  status <- try(
    system2(
      python_path,
      args = c("-c", "import neurokit2"),
      stdout = TRUE,
      stderr = TRUE
    ),
    silent = TRUE
  )

  !inherits(status, "try-error")
}

gpbiometrics_external_write_neurokit_script <- function(script_file,
                                                        input_file,
                                                        output_file,
                                                        sampling_rate) {
  lines <- c(
    "import pandas as pd",
    "import neurokit2 as nk",
    paste0("input_file = r'''", input_file, "'''"),
    paste0("output_file = r'''", output_file, "'''"),
    paste0("sampling_rate = ", sampling_rate),
    "df = pd.read_csv(input_file)",
    "rows = []",
    "for group_id, g in df.groupby('group_id'):",
    "    eda = pd.to_numeric(g['eda'], errors='coerce').dropna().values",
    "    row = {'group_id': group_id, 'rows': len(g), 'finite_rows': len(eda)}",
    "    try:",
    "        if len(eda) > 3:",
    "            signals, info = nk.eda_process(eda, sampling_rate=sampling_rate)",
    "            row['scr_peaks'] = int(signals['SCR_Peaks'].sum()) if 'SCR_Peaks' in signals else None",
    "            row['eda_clean_mean'] = float(signals['EDA_Clean'].mean()) if 'EDA_Clean' in signals else None",
    "            row['status'] = 'processed'",
    "        else:",
    "            row['scr_peaks'] = None",
    "            row['eda_clean_mean'] = None",
    "            row['status'] = 'too_few_samples'",
    "    except Exception as e:",
    "        row['scr_peaks'] = None",
    "        row['eda_clean_mean'] = None",
    "        row['status'] = 'error: ' + str(e)",
    "    rows.append(row)",
    "pd.DataFrame(rows).to_csv(output_file, index=False)"
  )

  writeLines(lines, script_file)
  invisible(script_file)
}
