#' Check a Gazepoint dataset for a BIDS-like layout
#'
#' @description
#' Performs a conservative, Gazepoint-oriented audit of a dataset folder that
#' follows, or approximately follows, a BIDS-like organization. This function is
#' not a full BIDS validator and does not convert data. It checks only simple,
#' reviewable layout features such as dataset-level metadata files, subject
#' folders, Gazepoint-like export files, and optional JSON sidecars.
#'
#' @param root Character scalar. Path to the dataset root folder.
#' @param subject_pattern Regular expression used to identify subject folders.
#'   Defaults to folders such as `sub-001`.
#' @param recursive Logical. Whether to search for Gazepoint export files
#'   recursively under `root`.
#' @param expected_files Character vector of optional dataset-level files to check.
#' @param gazepoint_patterns Character vector of case-insensitive filename
#'   patterns used to identify Gazepoint-derived exports.
#'
#' @return A list with class `gazepoint_bids_layout_audit` containing the root
#'   path, check table, discovered files, and summary counts.
#'
#' @export
check_gazepoint_bids <- function(root,
                                  subject_pattern = "^sub-[A-Za-z0-9]+$",
                                  recursive = TRUE,
                                  expected_files = c("dataset_description.json", "participants.tsv"),
                                  gazepoint_patterns = c(
                                    "all[_-]?gaze", "fixation", "summary",
                                    "biometric", "eda", "gsr", "ecg",
                                    "ppg", "hr", "ibi"
                                  )) {
  if (!is.character(root) || length(root) != 1 || is.na(root) || !nzchar(root)) {
    stop("`root` must be a non-empty character scalar.", call. = FALSE)
  }
  if (!is.character(subject_pattern) || length(subject_pattern) != 1 || is.na(subject_pattern)) {
    stop("`subject_pattern` must be a character scalar regular expression.", call. = FALSE)
  }
  if (!is.logical(recursive) || length(recursive) != 1 || is.na(recursive)) {
    stop("`recursive` must be TRUE or FALSE.", call. = FALSE)
  }

  add_check <- function(check, status, severity, message) {
    data.frame(
      check = check,
      status = status,
      severity = severity,
      message = message,
      stringsAsFactors = FALSE
    )
  }

  root_norm <- normalizePath(root, winslash = "/", mustWork = FALSE)
  checks <- list()
  files <- character(0)

  root_exists <- dir.exists(root)
  checks[[length(checks) + 1L]] <- add_check(
    "root_directory",
    if (root_exists) "pass" else "fail",
    if (root_exists) "none" else "error",
    if (root_exists) {
      paste0("Dataset root exists: ", root_norm)
    } else {
      paste0("Dataset root does not exist: ", root_norm)
    }
  )

  if (!root_exists) {
    check_table <- do.call(rbind, checks)
    summary <- data.frame(
      n_checks = nrow(check_table),
      n_pass = sum(check_table$status == "pass"),
      n_warn = sum(check_table$status == "warn"),
      n_fail = sum(check_table$status == "fail"),
      layout_ready = FALSE,
      needs_review = TRUE,
      stringsAsFactors = FALSE
    )
    out <- list(root = root_norm, checks = check_table, files = files, summary = summary)
    class(out) <- "gazepoint_bids_layout_audit"
    return(out)
  }

  top_level <- list.files(root, full.names = FALSE, recursive = FALSE, all.files = FALSE)

  for (expected in expected_files) {
    present <- expected %in% top_level
    checks[[length(checks) + 1L]] <- add_check(
      paste0("dataset_file_", expected),
      if (present) "pass" else "warn",
      if (present) "none" else "review",
      if (present) {
        paste0("Dataset-level file found: ", expected)
      } else {
        paste0("Dataset-level file not found: ", expected)
      }
    )
  }

  dirs <- list.dirs(root, recursive = FALSE, full.names = FALSE)
  subject_dirs <- grep("^sub-", dirs, value = TRUE)
  checks[[length(checks) + 1L]] <- add_check(
    "subject_directories",
    if (length(subject_dirs) > 0L) "pass" else "warn",
    if (length(subject_dirs) > 0L) "none" else "review",
    if (length(subject_dirs) > 0L) {
      paste0("Subject directories found: ", paste(subject_dirs, collapse = ", "))
    } else {
      "No top-level `sub-*` subject directories were found."
    }
  )

  if (length(subject_dirs) > 0L) {
    invalid_subject_dirs <- subject_dirs[!grepl(subject_pattern, subject_dirs)]
    checks[[length(checks) + 1L]] <- add_check(
      "subject_directory_names",
      if (length(invalid_subject_dirs) == 0L) "pass" else "warn",
      if (length(invalid_subject_dirs) == 0L) "none" else "review",
      if (length(invalid_subject_dirs) == 0L) {
        "All detected subject directories match the requested subject pattern."
      } else {
        paste0("Subject directories not matching pattern: ", paste(invalid_subject_dirs, collapse = ", "))
      }
    )
  }

  files <- list.files(root, full.names = TRUE, recursive = recursive, all.files = FALSE)
  file_names <- basename(files)
  export_regex <- paste(gazepoint_patterns, collapse = "|")
  gazepoint_files <- files[grepl(export_regex, file_names, ignore.case = TRUE)]
  gazepoint_files <- gazepoint_files[grepl("\\.(csv|tsv|txt)$", gazepoint_files, ignore.case = TRUE)]

  checks[[length(checks) + 1L]] <- add_check(
    "gazepoint_export_files",
    if (length(gazepoint_files) > 0L) "pass" else "warn",
    if (length(gazepoint_files) > 0L) "none" else "review",
    if (length(gazepoint_files) > 0L) {
      paste0("Gazepoint-like export files found: ", length(gazepoint_files))
    } else {
      "No Gazepoint-like CSV, TSV, or TXT export files were found."
    }
  )

  json_files <- files[grepl("\\.json$", files, ignore.case = TRUE)]
  checks[[length(checks) + 1L]] <- add_check(
    "json_sidecars",
    if (length(json_files) > 0L) "pass" else "warn",
    if (length(json_files) > 0L) "none" else "review",
    if (length(json_files) > 0L) {
      paste0("JSON metadata/sidecar files found: ", length(json_files))
    } else {
      "No JSON metadata or sidecar files were found."
    }
  )

  check_table <- do.call(rbind, checks)
  summary <- data.frame(
    n_checks = nrow(check_table),
    n_pass = sum(check_table$status == "pass"),
    n_warn = sum(check_table$status == "warn"),
    n_fail = sum(check_table$status == "fail"),
    layout_ready = sum(check_table$status == "fail") == 0L,
    needs_review = any(check_table$status %in% c("warn", "fail")),
    stringsAsFactors = FALSE
  )

  out <- list(
    root = root_norm,
    checks = check_table,
    files = data.frame(
      path = normalizePath(files, winslash = "/", mustWork = FALSE),
      is_gazepoint_export = normalizePath(files, winslash = "/", mustWork = FALSE) %in%
        normalizePath(gazepoint_files, winslash = "/", mustWork = FALSE),
      is_json = grepl("\\.json$", files, ignore.case = TRUE),
      stringsAsFactors = FALSE
    ),
    summary = summary
  )
  class(out) <- "gazepoint_bids_layout_audit"
  out
}

#' @export
print.gazepoint_bids_layout_audit <- function(x, ...) {
  cat("Gazepoint BIDS-like layout audit\n")
  cat("Root:", x$root, "\n\n")
  print(x$summary, row.names = FALSE)
  cat("\nChecks:\n")
  print(x$checks, row.names = FALSE)
  invisible(x)
}
