#' Export a Gazepoint biometrics report bundle
#'
#' Exports selected report tables, text outputs, optional plot objects, and a
#' manifest to a local output directory. This helper is intended for reproducible
#' reporting. It does not commit files and should not be used to export private
#' real-data outputs into a package repository.
#'
#' @param bundle Optional list-like object containing data frames, text, or plots.
#' @param output_dir Output directory.
#' @param prefix File prefix.
#' @param tables Optional named list of data frames to export as CSV files.
#' @param text Optional named list or character vector of text outputs to export
#'   as TXT files.
#' @param plots Optional named list of ggplot objects to export as PNG files.
#' @param include_readme Logical. Should a README text file be written?
#' @param include_session_info Logical. Should session information be written?
#' @param overwrite Logical. Should existing files be overwritten?
#'
#' @return A list with `overview`, `manifest`, `output_dir`, and `settings`.
#' @export
export_gazepoint_biometrics_report_bundle <- function(bundle = NULL,
                                                      output_dir,
                                                      prefix = "gpbiometrics_report",
                                                      tables = NULL,
                                                      text = NULL,
                                                      plots = NULL,
                                                      include_readme = TRUE,
                                                      include_session_info = TRUE,
                                                      overwrite = FALSE) {
  if (missing(output_dir) || length(output_dir) != 1 || !is.character(output_dir)) {
    stop("`output_dir` must be a single directory path.", call. = FALSE)
  }

  if (!is.character(prefix) || length(prefix) != 1 || !nzchar(prefix)) {
    stop("`prefix` must be a non-empty character string.", call. = FALSE)
  }

  if (!is.logical(include_readme) || length(include_readme) != 1) {
    stop("`include_readme` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.logical(include_session_info) || length(include_session_info) != 1) {
    stop("`include_session_info` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.logical(overwrite) || length(overwrite) != 1) {
    stop("`overwrite` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  }

  if (!dir.exists(output_dir)) {
    stop("Could not create `output_dir`.", call. = FALSE)
  }

  prefix_safe <- gpbiometrics_bundle_safe_name(prefix)

  collected_tables <- list()

  if (!is.null(bundle)) {
    collected_tables <- c(
      collected_tables,
      gpbiometrics_bundle_collect_tables(bundle, parent_name = "bundle")
    )
  }

  if (!is.null(tables)) {
    if (is.data.frame(tables)) {
      tables <- list(table = tables)
    }

    if (!is.list(tables)) {
      stop("`tables` must be a data frame or a named list of data frames.", call. = FALSE)
    }

    collected_tables <- c(
      collected_tables,
      gpbiometrics_bundle_collect_tables(tables, parent_name = "tables")
    )
  }

  collected_text <- list()

  if (!is.null(bundle)) {
    collected_text <- c(
      collected_text,
      gpbiometrics_bundle_collect_text(bundle, parent_name = "bundle")
    )
  }

  if (!is.null(text)) {
    if (is.character(text) && is.null(names(text))) {
      text <- list(text = text)
    }

    if (!is.list(text)) {
      stop("`text` must be a character vector or a named list.", call. = FALSE)
    }

    collected_text <- c(
      collected_text,
      gpbiometrics_bundle_collect_text(text, parent_name = "text")
    )
  }

  collected_plots <- list()

  if (!is.null(bundle)) {
    collected_plots <- c(
      collected_plots,
      gpbiometrics_bundle_collect_plots(bundle, parent_name = "bundle")
    )
  }

  if (!is.null(plots)) {
    if (!is.list(plots)) {
      stop("`plots` must be a named list of plot objects.", call. = FALSE)
    }

    collected_plots <- c(
      collected_plots,
      gpbiometrics_bundle_collect_plots(plots, parent_name = "plots")
    )
  }

  manifest <- data.frame(
    item = character(),
    type = character(),
    path = character(),
    status = character(),
    note = character(),
    stringsAsFactors = FALSE
  )

  for (name in names(collected_tables)) {
    table_i <- collected_tables[[name]]
    file_path <- file.path(
      output_dir,
      paste0(prefix_safe, "_", gpbiometrics_bundle_safe_name(name), ".csv")
    )

    gpbiometrics_bundle_check_overwrite(file_path, overwrite)

    utils::write.csv(table_i, file_path, row.names = FALSE, na = "")

    manifest <- rbind(
      manifest,
      data.frame(
        item = name,
        type = "table_csv",
        path = normalizePath(file_path, winslash = "/", mustWork = FALSE),
        status = "written",
        note = "",
        stringsAsFactors = FALSE
      )
    )
  }

  for (name in names(collected_text)) {
    text_i <- collected_text[[name]]
    file_path <- file.path(
      output_dir,
      paste0(prefix_safe, "_", gpbiometrics_bundle_safe_name(name), ".txt")
    )

    gpbiometrics_bundle_check_overwrite(file_path, overwrite)

    writeLines(as.character(text_i), file_path, useBytes = TRUE)

    manifest <- rbind(
      manifest,
      data.frame(
        item = name,
        type = "text",
        path = normalizePath(file_path, winslash = "/", mustWork = FALSE),
        status = "written",
        note = "",
        stringsAsFactors = FALSE
      )
    )
  }

  if (length(collected_plots) > 0) {
    if (!requireNamespace("ggplot2", quietly = TRUE)) {
      for (name in names(collected_plots)) {
        manifest <- rbind(
          manifest,
          data.frame(
            item = name,
            type = "plot_png",
            path = "",
            status = "skipped",
            note = "Package ggplot2 is not installed.",
            stringsAsFactors = FALSE
          )
        )
      }
    } else {
      for (name in names(collected_plots)) {
        plot_i <- collected_plots[[name]]
        file_path <- file.path(
          output_dir,
          paste0(prefix_safe, "_", gpbiometrics_bundle_safe_name(name), ".png")
        )

        gpbiometrics_bundle_check_overwrite(file_path, overwrite)

        ggplot2::ggsave(
          filename = file_path,
          plot = plot_i,
          width = 8,
          height = 5,
          dpi = 300
        )

        manifest <- rbind(
          manifest,
          data.frame(
            item = name,
            type = "plot_png",
            path = normalizePath(file_path, winslash = "/", mustWork = FALSE),
            status = "written",
            note = "",
            stringsAsFactors = FALSE
          )
        )
      }
    }
  }

  if (isTRUE(include_readme)) {
    file_path <- file.path(output_dir, paste0(prefix_safe, "_README.txt"))
    gpbiometrics_bundle_check_overwrite(file_path, overwrite)

    readme_text <- c(
      "Gazepoint biometrics report bundle",
      "",
      paste0("Created: ", as.character(Sys.time())),
      "",
      "This bundle contains exported package outputs for inspection and reporting.",
      "Private real-data outputs should be stored outside the package repository.",
      "",
      "Included workflow scope may include:",
      "- Import/schema checks and active biometric-channel detection.",
      "- Missingness, dropout, sampling, time-reset, activity, and readiness checks.",
      "- GSR/EDA quality checks, decomposition, SCR peak/event-window summaries, and SCR sensitivity analyses.",
      "- HR/IBI quality checks, implausible-IBI filtering, HR-IBI consistency checks, and IBI-derived HRV summaries.",
      "- TTL/event alignment and multimodal timeline inspection.",
      "- AOI-linked biometric summaries and model-preparation tables.",
      "- Optional interoperability exports for tools such as RHRV or NeuroKit2.",
      "- Contract-standardised ggplot outputs with stored plot data, settings, and interpretation notes.",
      "",
      "Interpretation cautions:",
      "- GSR/EDA should be interpreted as electrodermal/arousal-related signal, not emotional valence.",
      "- SCR detections are signal-processing events and depend on preprocessing, threshold, and event-window settings.",
      "- Raw Gazepoint HRV should be treated as a vendor/validity field unless independently documented.",
      "- HRV features should be derived from genuine IBI/RR intervals after plausibility filtering and window-duration checks.",
      "- AOI-linked biometric summaries describe signals during AOI exposure and do not by themselves establish preference, trust, scrutiny, or cognitive evaluation.",
      "- Eye-tracking measures indicate visual attention, not direct cognition or evaluation.",
      "- Plots are intended for quality control, synchronization checks, and reporting support, not standalone inferential evidence."
    )

    writeLines(readme_text, file_path, useBytes = TRUE)

    manifest <- rbind(
      manifest,
      data.frame(
        item = "README",
        type = "text",
        path = normalizePath(file_path, winslash = "/", mustWork = FALSE),
        status = "written",
        note = "",
        stringsAsFactors = FALSE
      )
    )
  }

  if (isTRUE(include_session_info)) {
    file_path <- file.path(output_dir, paste0(prefix_safe, "_session_info.txt"))
    gpbiometrics_bundle_check_overwrite(file_path, overwrite)

    writeLines(utils::capture.output(utils::sessionInfo()), file_path, useBytes = TRUE)

    manifest <- rbind(
      manifest,
      data.frame(
        item = "session_info",
        type = "text",
        path = normalizePath(file_path, winslash = "/", mustWork = FALSE),
        status = "written",
        note = "",
        stringsAsFactors = FALSE
      )
    )
  }

  manifest_path <- file.path(output_dir, paste0(prefix_safe, "_manifest.csv"))
  gpbiometrics_bundle_check_overwrite(manifest_path, overwrite)

  utils::write.csv(manifest, manifest_path, row.names = FALSE, na = "")

  manifest <- rbind(
    manifest,
    data.frame(
      item = "manifest",
      type = "manifest_csv",
      path = normalizePath(manifest_path, winslash = "/", mustWork = FALSE),
      status = "written",
      note = "",
      stringsAsFactors = FALSE
    )
  )

  written_count <- sum(manifest$status == "written")
  skipped_count <- sum(manifest$status == "skipped")

  status <- if (written_count == 0) {
    "nothing_written"
  } else if (skipped_count > 0) {
    "bundle_exported_with_skips"
  } else {
    "bundle_exported"
  }

  structure(
    list(
      overview = data.frame(
        output_dir = normalizePath(output_dir, winslash = "/", mustWork = FALSE),
        written_files = written_count,
        skipped_items = skipped_count,
        status = status,
        stringsAsFactors = FALSE
      ),
      manifest = manifest,
      output_dir = normalizePath(output_dir, winslash = "/", mustWork = FALSE),
      settings = list(
        prefix = prefix,
        include_readme = include_readme,
        include_session_info = include_session_info,
        overwrite = overwrite
      )
    ),
    class = c("gazepoint_biometrics_report_bundle", "list")
  )
}

#' Run a final real-data readiness gate for Gazepoint biometrics data
#'
#' Provides conservative pass/warn/fail checks before using real Gazepoint
#' Biometrics exports for analysis or reporting. The function checks basic row
#' count, signal availability, missingness, time ordering, TTL availability, and
#' HRV/IBI caution status. It does not certify data quality or infer emotional
#' states.
#'
#' @param data A biometric data frame. If `NULL`, the function tries to extract a
#'   data frame from `workflow_result`.
#' @param workflow_result Optional workflow/list object containing biometric data.
#' @param min_rows Minimum number of rows expected for a usable real-data check.
#' @param min_active_signal_count Minimum number of biometric signal columns with
#'   at least one non-missing/non-zero value.
#' @param max_missing_prop Maximum acceptable missing proportion for detected
#'   signal columns before a warning is raised.
#' @param required_signal_cols Optional signal columns that must be present.
#' @param require_gsr_us_preferred Logical. If `TRUE`, warns when `GSR_US` is
#'   absent but `GSR` is present.
#' @param require_ibi_for_hrv Logical. If `TRUE`, fails when HRV is present but
#'   IBI is absent. If `FALSE`, this condition is reported as a warning.
#' @param time_col Optional time column. If `NULL`, common time columns are
#'   detected automatically.
#' @param ttl_cols Optional TTL marker columns. If `NULL`, `ttl_marker` or
#'   `TTL0`-`TTL6` are detected automatically.
#'
#' @return A list with `overview`, `checks`, `signal_summary`, and `settings`.
#' @export
run_gazepoint_biometrics_real_data_readiness <- function(data = NULL,
                                                         workflow_result = NULL,
                                                         min_rows = 100,
                                                         min_active_signal_count = 1,
                                                         max_missing_prop = 0.50,
                                                         required_signal_cols = NULL,
                                                         require_gsr_us_preferred = TRUE,
                                                         require_ibi_for_hrv = FALSE,
                                                         time_col = NULL,
                                                         ttl_cols = NULL) {
  if (is.null(data)) {
    data <- gpbiometrics_readiness_extract_data(workflow_result)
  }

  if (!is.data.frame(data)) {
    stop(
      "`data` must be a data frame, or `workflow_result` must contain a data frame.",
      call. = FALSE
    )
  }

  if (!is.numeric(min_rows) || length(min_rows) != 1 || min_rows < 1) {
    stop("`min_rows` must be a positive number.", call. = FALSE)
  }

  if (!is.numeric(min_active_signal_count) ||
      length(min_active_signal_count) != 1 ||
      min_active_signal_count < 0) {
    stop("`min_active_signal_count` must be a non-negative number.", call. = FALSE)
  }

  if (!is.numeric(max_missing_prop) ||
      length(max_missing_prop) != 1 ||
      max_missing_prop < 0 ||
      max_missing_prop > 1) {
    stop("`max_missing_prop` must be between 0 and 1.", call. = FALSE)
  }

  if (!is.logical(require_gsr_us_preferred) || length(require_gsr_us_preferred) != 1) {
    stop("`require_gsr_us_preferred` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.logical(require_ibi_for_hrv) || length(require_ibi_for_hrv) != 1) {
    stop("`require_ibi_for_hrv` must be TRUE or FALSE.", call. = FALSE)
  }

  dat <- as.data.frame(data, stringsAsFactors = FALSE)
  names_dat <- names(dat)

  signal_cols <- gpbiometrics_readiness_signal_cols(names_dat)
  signal_summary <- gpbiometrics_readiness_signal_summary(dat, signal_cols)

  active_signal_count <- sum(signal_summary$active_signal, na.rm = TRUE)

  if (is.null(time_col)) {
    time_col <- gpbiometrics_readiness_first_existing(
      names_dat,
      c(
        "time_ms", "timestamp_ms", "timestamp",
        "TIME", "Time", "time",
        "CNT", "cnt"
      )
    )
  }

  if (is.null(ttl_cols)) {
    ttl_marker <- gpbiometrics_readiness_first_existing(names_dat, c("ttl_marker"))

    if (!is.null(ttl_marker)) {
      ttl_cols <- ttl_marker
    } else {
      ttl_cols <- grep("^TTL[0-6]$", names_dat, value = TRUE, ignore.case = TRUE)
    }
  }

  checks <- data.frame(
    check = character(),
    status = character(),
    detail = character(),
    stringsAsFactors = FALSE
  )

  checks <- gpbiometrics_readiness_add_check(
    checks,
    check = "row_count",
    status = if (nrow(dat) >= min_rows) "pass" else "fail",
    detail = paste0("Input contains ", nrow(dat), " rows; minimum requested is ", min_rows, ".")
  )

  checks <- gpbiometrics_readiness_add_check(
    checks,
    check = "active_signal_count",
    status = if (active_signal_count >= min_active_signal_count) "pass" else "fail",
    detail = paste0(
      "Detected ",
      active_signal_count,
      " active biometric signal column(s); minimum requested is ",
      min_active_signal_count,
      "."
    )
  )

  if (!is.null(required_signal_cols)) {
    missing_required <- setdiff(required_signal_cols, names_dat)

    checks <- gpbiometrics_readiness_add_check(
      checks,
      check = "required_signal_columns",
      status = if (length(missing_required) == 0) "pass" else "fail",
      detail = if (length(missing_required) == 0) {
        "All requested signal columns are present."
      } else {
        paste("Missing requested signal columns:", paste(missing_required, collapse = ", "))
      }
    )
  }

  high_missing <- signal_summary$signal[
    signal_summary$active_signal &
      is.finite(signal_summary$missing_prop) &
      signal_summary$missing_prop > max_missing_prop
  ]

  checks <- gpbiometrics_readiness_add_check(
    checks,
    check = "signal_missingness",
    status = if (length(high_missing) == 0) "pass" else "warn",
    detail = if (length(high_missing) == 0) {
      paste0("No active signal exceeded missingness threshold ", max_missing_prop, ".")
    } else {
      paste(
        "Active signals exceeding missingness threshold:",
        paste(high_missing, collapse = ", ")
      )
    }
  )

  has_gsr_us <- "GSR_US" %in% names_dat || "gsr_us" %in% names_dat
  has_gsr <- "GSR" %in% names_dat || "gsr" %in% names_dat

  checks <- gpbiometrics_readiness_add_check(
    checks,
    check = "gsr_conductance_channel",
    status = if (has_gsr_us || !has_gsr || !isTRUE(require_gsr_us_preferred)) "pass" else "warn",
    detail = if (has_gsr_us) {
      "GSR_US conductance channel is available."
    } else if (has_gsr) {
      "GSR is present but GSR_US is absent; conversion should be conservative and documented."
    } else {
      "No GSR/GSR_US channel detected."
    }
  )

  has_hrv <- "HRV" %in% names_dat || "hrv" %in% names_dat
  has_ibi <- "IBI" %in% names_dat || "ibi" %in% names_dat

  hrv_status <- "pass"
  hrv_detail <- "No HRV/IBI conflict detected."

  if (has_hrv && !has_ibi) {
    hrv_status <- if (isTRUE(require_ibi_for_hrv)) "fail" else "warn"
    hrv_detail <- paste(
      "HRV column is present but IBI is absent.",
      "Treat raw Gazepoint HRV as a vendor/validity field unless independently documented."
    )
  } else if (has_hrv && has_ibi) {
    hrv_detail <- paste(
      "HRV and IBI are present.",
      "Derived HRV features should use IBI/RR intervals, not the raw HRV field."
    )
  } else if (!has_hrv && has_ibi) {
    hrv_detail <- "IBI is present; HRV features can be derived from genuine IBI/RR intervals after quality checks."
  }

  checks <- gpbiometrics_readiness_add_check(
    checks,
    check = "hrv_ibi_caution",
    status = hrv_status,
    detail = hrv_detail
  )

  time_status <- "warn"
  time_detail <- "No usable time column detected."

  if (!is.null(time_col) && time_col %in% names_dat) {
    time_numeric <- suppressWarnings(as.numeric(dat[[time_col]]))

    if (all(is.na(time_numeric))) {
      time_status <- "fail"
      time_detail <- paste0("Detected time column `", time_col, "` is not numeric/coercible.")
    } else {
      time_group_cols <- intersect(
        c(
          "source_file",
          "source_participant",
          "USER",
          "USER_FILE",
          "participant",
          "subject",
          "MEDIA_ID",
          "MEDIA_NAME",
          "trial",
          "trial_id"
        ),
        names_dat
      )

      if (length(time_group_cols) > 0) {
        time_group_id <- apply(
          dat[time_group_cols],
          1,
          function(z) paste(ifelse(is.na(z), "<NA>", as.character(z)), collapse = "||")
        )
      } else {
        time_group_id <- rep("all", nrow(dat))
      }

      split_rows <- split(seq_len(nrow(dat)), time_group_id, drop = TRUE)

      negative_steps_by_group <- vapply(
        split_rows,
        function(idx) {
          x <- time_numeric[idx]
          x <- x[is.finite(x)]
          if (length(x) < 2) {
            return(0L)
          }
          sum(diff(x) < 0, na.rm = TRUE)
        },
        integer(1)
      )

      negative_steps <- sum(negative_steps_by_group)
      affected_groups <- sum(negative_steps_by_group > 0)

      if (negative_steps == 0) {
        time_status <- "pass"
        time_detail <- paste0(
          "Time column `",
          time_col,
          "` is usable and non-decreasing within ",
          length(split_rows),
          " detected group(s)."
        )
      } else {
        time_status <- "warn"
        time_detail <- paste0(
          "Time column `",
          time_col,
          "` has ",
          negative_steps,
          " negative step(s) within ",
          affected_groups,
          " detected group(s)."
        )
      }
    }
  }

  checks <- gpbiometrics_readiness_add_check(
    checks,
    check = "time_column",
    status = time_status,
    detail = time_detail
  )

  ttl_status <- "info"
  ttl_detail <- "No TTL marker columns detected."

  if (length(ttl_cols) > 0) {
    ttl_cols <- ttl_cols[ttl_cols %in% names_dat]

    if (length(ttl_cols) > 0) {
      ttl_active <- vapply(
        ttl_cols,
        function(col) {
          x <- dat[[col]]
          if (is.logical(x)) {
            return(any(!is.na(x) & x))
          }
          if (is.numeric(x)) {
            return(any(!is.na(x) & x != 0))
          }
          x_chr <- trimws(as.character(x))
          any(!is.na(x_chr) & nzchar(x_chr) & !toupper(x_chr) %in% c("0", "FALSE", "F", "NA", "NAN", "NULL"))
        },
        logical(1)
      )

      ttl_status <- if (any(ttl_active)) "pass" else "warn"
      ttl_detail <- if (any(ttl_active)) {
        paste("Active TTL marker detected in:", paste(ttl_cols[ttl_active], collapse = ", "))
      } else {
        paste("TTL marker columns detected but no active TTL marker found:", paste(ttl_cols, collapse = ", "))
      }
    }
  }

  checks <- gpbiometrics_readiness_add_check(
    checks,
    check = "ttl_markers",
    status = ttl_status,
    detail = ttl_detail
  )

  fail_count <- sum(checks$status == "fail")
  warn_count <- sum(checks$status == "warn")
  pass_count <- sum(checks$status == "pass")
  info_count <- sum(checks$status == "info")

  final_status <- if (fail_count > 0) {
    "fail"
  } else if (warn_count > 0) {
    "warn"
  } else {
    "pass"
  }

  decision <- switch(
    final_status,
    pass = "ready_for_analysis_with_standard_cautions",
    warn = "review_before_analysis",
    fail = "not_ready_for_analysis"
  )

  structure(
    list(
      overview = data.frame(
        input_rows = nrow(dat),
        detected_signal_count = length(signal_cols),
        active_signal_count = active_signal_count,
        pass_checks = pass_count,
        warn_checks = warn_count,
        fail_checks = fail_count,
        info_checks = info_count,
        final_status = final_status,
        decision = decision,
        stringsAsFactors = FALSE
      ),
      checks = checks,
      signal_summary = signal_summary,
      settings = list(
        min_rows = min_rows,
        min_active_signal_count = min_active_signal_count,
        max_missing_prop = max_missing_prop,
        required_signal_cols = required_signal_cols,
        require_gsr_us_preferred = require_gsr_us_preferred,
        require_ibi_for_hrv = require_ibi_for_hrv,
        time_col = time_col,
        ttl_cols = ttl_cols
      )
    ),
    class = c("gazepoint_biometrics_real_data_readiness", "list")
  )
}

gpbiometrics_bundle_safe_name <- function(x) {
  x <- as.character(x)
  x <- gsub("[^A-Za-z0-9_-]+", "_", x)
  x <- gsub("_+", "_", x)
  x <- gsub("^_|_$", "", x)

  if (!nzchar(x)) {
    x <- "item"
  }

  x
}

gpbiometrics_bundle_check_overwrite <- function(path, overwrite) {
  if (file.exists(path) && !isTRUE(overwrite)) {
    stop(
      "File already exists and `overwrite = FALSE`: ",
      path,
      call. = FALSE
    )
  }

  invisible(TRUE)
}

gpbiometrics_bundle_collect_tables <- function(x, parent_name = "item") {
  out <- list()

  if (is.data.frame(x)) {
    out[[parent_name]] <- x
    return(out)
  }

  if (!is.list(x)) {
    return(out)
  }

  nms <- names(x)

  if (is.null(nms)) {
    nms <- paste0("item_", seq_along(x))
  }

  for (i in seq_along(x)) {
    child_name <- paste(parent_name, nms[i], sep = "_")
    child <- x[[i]]

    if (is.data.frame(child)) {
      out[[child_name]] <- child
    } else if (is.list(child) && !inherits(child, "ggplot")) {
      out <- c(out, gpbiometrics_bundle_collect_tables(child, child_name))
    }
  }

  out
}

gpbiometrics_bundle_collect_text <- function(x, parent_name = "item") {
  out <- list()

  if (is.character(x) && length(x) > 0) {
    out[[parent_name]] <- x
    return(out)
  }

  if (!is.list(x)) {
    return(out)
  }

  nms <- names(x)

  if (is.null(nms)) {
    nms <- paste0("item_", seq_along(x))
  }

  for (i in seq_along(x)) {
    child_name <- paste(parent_name, nms[i], sep = "_")
    child <- x[[i]]

    if (is.character(child) && length(child) > 0) {
      out[[child_name]] <- child
    } else if (is.list(child) && !inherits(child, "ggplot")) {
      out <- c(out, gpbiometrics_bundle_collect_text(child, child_name))
    }
  }

  out
}

gpbiometrics_bundle_collect_plots <- function(x, parent_name = "item") {
  out <- list()

  if (inherits(x, "ggplot")) {
    out[[parent_name]] <- x
    return(out)
  }

  if (!is.list(x)) {
    return(out)
  }

  nms <- names(x)

  if (is.null(nms)) {
    nms <- paste0("item_", seq_along(x))
  }

  for (i in seq_along(x)) {
    child_name <- paste(parent_name, nms[i], sep = "_")
    child <- x[[i]]

    if (inherits(child, "ggplot")) {
      out[[child_name]] <- child
    } else if (is.list(child)) {
      out <- c(out, gpbiometrics_bundle_collect_plots(child, child_name))
    }
  }

  out
}

gpbiometrics_readiness_extract_data <- function(workflow_result) {
  if (is.null(workflow_result)) {
    return(NULL)
  }

  if (is.data.frame(workflow_result)) {
    return(workflow_result)
  }

  if (!is.list(workflow_result)) {
    return(NULL)
  }

  candidate_names <- c(
    "biometrics",
    "biometric_data",
    "data",
    "raw_data",
    "imported_data",
    "all_gaze",
    "samples"
  )

  for (candidate in candidate_names) {
    if (!is.null(workflow_result[[candidate]]) &&
        is.data.frame(workflow_result[[candidate]])) {
      return(workflow_result[[candidate]])
    }
  }

  for (item in workflow_result) {
    if (is.data.frame(item)) {
      return(item)
    }
  }

  NULL
}

gpbiometrics_readiness_first_existing <- function(names_dat, candidates) {
  exact <- candidates[candidates %in% names_dat]

  if (length(exact) > 0) {
    return(exact[1])
  }

  lower_names <- tolower(names_dat)
  lower_candidates <- tolower(candidates)
  idx <- match(lower_candidates, lower_names)
  idx <- idx[!is.na(idx)]

  if (length(idx) > 0) {
    return(names_dat[idx[1]])
  }

  NULL
}

gpbiometrics_readiness_signal_cols <- function(names_dat) {
  candidates <- c(
    "DIAL", "DIALV",
    "GSR", "GSR_US", "GSR_US_TONIC", "GSR_US_PHASIC", "GSRV",
    "HR", "HRV", "HRP", "IBI",
    "dial", "dialv",
    "gsr", "gsr_us", "gsr_us_tonic", "gsr_us_phasic", "gsrv",
    "hr", "hrv", "hrp", "ibi"
  )

  unique(candidates[candidates %in% names_dat])
}

gpbiometrics_readiness_signal_summary <- function(dat, signal_cols) {
  out <- data.frame(
    signal = signal_cols,
    present = TRUE,
    numeric_or_coercible = NA,
    missing_count = NA_integer_,
    missing_prop = NA_real_,
    nonzero_count = NA_integer_,
    active_signal = NA,
    stringsAsFactors = FALSE
  )

  if (length(signal_cols) == 0) {
    return(out)
  }

  for (i in seq_along(signal_cols)) {
    signal <- signal_cols[i]
    x <- suppressWarnings(as.numeric(dat[[signal]]))

    numeric_or_coercible <- !all(is.na(x))
    missing_count <- sum(is.na(x))
    missing_prop <- if (length(x) == 0) NA_real_ else mean(is.na(x))
    nonzero_count <- sum(!is.na(x) & x != 0)
    active_signal <- numeric_or_coercible && any(!is.na(x) & x != 0)

    out$numeric_or_coercible[i] <- numeric_or_coercible
    out$missing_count[i] <- missing_count
    out$missing_prop[i] <- missing_prop
    out$nonzero_count[i] <- nonzero_count
    out$active_signal[i] <- active_signal
  }

  out
}

gpbiometrics_readiness_add_check <- function(checks, check, status, detail) {
  rbind(
    checks,
    data.frame(
      check = check,
      status = status,
      detail = detail,
      stringsAsFactors = FALSE
    )
  )
}
