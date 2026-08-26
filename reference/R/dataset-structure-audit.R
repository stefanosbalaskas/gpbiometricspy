#' Summarize Gazepoint export inventory
#'
#' Creates a descriptive file inventory for a Gazepoint export folder or a vector
#' of files. The function summarizes paths, extensions, file sizes, likely export
#' types, and empty-file flags. It is intended for reproducibility and audit
#' reporting only.
#'
#' @param path Directory path, file path, or character vector of file paths.
#' @param recursive Logical. If \code{TRUE}, directories are searched
#'   recursively.
#' @param include_hidden Logical. If \code{TRUE}, hidden files are included.
#' @param classify Logical. If \code{TRUE}, likely Gazepoint export types are
#'   inferred from file names using conservative keyword rules.
#'
#' @return A data frame with class \code{gazepoint_export_inventory}.
#' @export
summarize_gazepoint_export_inventory <- function(path,
                                                 recursive = TRUE,
                                                 include_hidden = FALSE,
                                                 classify = TRUE) {
  gpds_check_character_path(path)
  gpds_check_logical_one(recursive, "recursive")
  gpds_check_logical_one(include_hidden, "include_hidden")
  gpds_check_logical_one(classify, "classify")

  paths <- gpds_collect_files(path, recursive = recursive, include_hidden = include_hidden)

  if (length(paths) == 0) {
    out <- gpds_empty_inventory()
    class(out) <- c("gazepoint_export_inventory", class(out))
    return(out)
  }

  info <- file.info(paths)
  normalized <- gpds_normalize_path(paths, must_work = FALSE)
  root <- gpds_common_root(path, normalized)

  out <- data.frame(
    path = normalized,
    relative_path = gpds_relative_path(normalized, root),
    directory = dirname(normalized),
    file_name = basename(normalized),
    extension = tolower(tools::file_ext(normalized)),
    size_bytes = as.numeric(info$size),
    modified_time = as.POSIXct(info$mtime),
    is_empty = is.finite(as.numeric(info$size)) & as.numeric(info$size) == 0,
    stringsAsFactors = FALSE
  )

  out$likely_export_type <- if (classify) {
    vapply(out$file_name, gpds_classify_export_type, character(1))
  } else {
    NA_character_
  }

  out$participant_id <- vapply(out$relative_path, gpds_extract_participant_id, character(1))
  out$has_sidecar <- gpds_has_sidecar(out$path)

  out <- out[
    order(out$relative_path, out$file_name),
    ,
    drop = FALSE
  ]

  rownames(out) <- NULL
  class(out) <- c("gazepoint_export_inventory", class(out))
  out
}

#' Audit Gazepoint dataset structure
#'
#' Checks a dataset or export folder for expected directories, files, filename
#' patterns, duplicate names, empty files, and optional sidecar coverage. This is
#' a lightweight structure audit, not a full BIDS validator or converter.
#'
#' @param root Dataset or export root directory.
#' @param expected_dirs Optional character vector of directory paths expected
#'   under \code{root}.
#' @param expected_files Optional character vector of file paths expected under
#'   \code{root}.
#' @param expected_patterns Optional named or unnamed character vector of regular
#'   expressions that should match at least one relative file path.
#' @param allowed_extensions Optional character vector of allowed file
#'   extensions, without leading dots.
#' @param require_sidecars Logical. If \code{TRUE}, non-sidecar files are flagged
#'   when no same-stem \code{.json} sidecar exists.
#' @param recursive Logical. If \code{TRUE}, files are inventoried recursively.
#' @param include_hidden Logical. If \code{TRUE}, hidden files are included.
#'
#' @return A list with class \code{gazepoint_dataset_structure_audit}.
#' @export
audit_gazepoint_dataset_structure <- function(root,
                                              expected_dirs = NULL,
                                              expected_files = NULL,
                                              expected_patterns = NULL,
                                              allowed_extensions = c("csv", "tsv", "txt", "json", "xlsx", "rds"),
                                              require_sidecars = FALSE,
                                              recursive = TRUE,
                                              include_hidden = FALSE) {
  gpds_check_root_dir(root)
  gpds_check_logical_one(require_sidecars, "require_sidecars")
  gpds_check_logical_one(recursive, "recursive")
  gpds_check_logical_one(include_hidden, "include_hidden")

  root <- gpds_normalize_path(root, must_work = TRUE)

  expected_dirs <- gpds_optional_character(expected_dirs, "expected_dirs")
  expected_files <- gpds_optional_character(expected_files, "expected_files")
  expected_patterns <- gpds_optional_character(expected_patterns, "expected_patterns")

  if (!is.null(allowed_extensions)) {
    allowed_extensions <- tolower(gsub("^\\.", "", as.character(allowed_extensions)))
    allowed_extensions <- allowed_extensions[nzchar(allowed_extensions)]
  }

  inventory <- summarize_gazepoint_export_inventory(
    root,
    recursive = recursive,
    include_hidden = include_hidden,
    classify = TRUE
  )

  checks <- list()

  checks$expected_dirs <- gpds_check_expected_dirs(root, expected_dirs)
  checks$expected_files <- gpds_check_expected_files(root, expected_files)
  checks$expected_patterns <- gpds_check_expected_patterns(inventory, expected_patterns)
  checks$duplicate_file_names <- gpds_check_duplicate_file_names(inventory)
  checks$empty_files <- gpds_check_empty_files(inventory)
  checks$unexpected_extensions <- gpds_check_unexpected_extensions(inventory, allowed_extensions)
  checks$sidecars <- gpds_check_sidecars(inventory, require_sidecars)

  results <- do.call(rbind, checks)
  rownames(results) <- NULL

  summary <- gpds_dataset_audit_summary(results, inventory)

  audit <- list(
    root = root,
    inventory = inventory,
    checks = results,
    summary = summary,
    parameters = list(
      expected_dirs = expected_dirs,
      expected_files = expected_files,
      expected_patterns = expected_patterns,
      allowed_extensions = allowed_extensions,
      require_sidecars = require_sidecars,
      recursive = recursive,
      include_hidden = include_hidden
    )
  )

  class(audit) <- c("gazepoint_dataset_structure_audit", "list")
  audit
}

#' Create a Gazepoint sidecar metadata template
#'
#' Creates a simple tabular template for dataset, export, device, timing, and
#' processing metadata. The output can be written by the user as CSV/TSV/JSON
#' outside this function. This function does not perform full BIDS conversion.
#'
#' @param dataset_id Optional dataset identifier.
#' @param export_type Optional export type label, such as \code{"all_gaze"},
#'   \code{"fixations"}, \code{"biometrics"}, or \code{"summary"}.
#' @param include_optional Logical. If \code{TRUE}, optional auditability fields
#'   are included.
#' @param custom_fields Optional data frame with columns \code{field},
#'   \code{description}, \code{required}, \code{value}, and \code{notes}.
#'
#' @return A data frame with class \code{gazepoint_sidecar_template}.
#' @export
create_gazepoint_sidecar_template <- function(dataset_id = NULL,
                                              export_type = NULL,
                                              include_optional = TRUE,
                                              custom_fields = NULL) {
  gpds_check_logical_one(include_optional, "include_optional")

  dataset_id <- gpds_optional_scalar_character(dataset_id, "dataset_id")
  export_type <- gpds_optional_scalar_character(export_type, "export_type")

  required <- data.frame(
    field = c(
      "dataset_id",
      "export_type",
      "source_software",
      "device",
      "sampling_rate_hz",
      "time_column",
      "participant_column",
      "trial_column",
      "created_by_package"
    ),
    description = c(
      "Dataset or project identifier.",
      "Gazepoint export type represented by the file.",
      "Software used to create the export.",
      "Recording device or system.",
      "Nominal sampling rate in Hz.",
      "Name of the timestamp column.",
      "Name of the participant identifier column.",
      "Name of the trial or event identifier column.",
      "R package used to create the sidecar template."
    ),
    required = TRUE,
    value = c(
      gpds_value_or_blank(dataset_id),
      gpds_value_or_blank(export_type),
      "Gazepoint",
      "",
      "",
      "",
      "",
      "",
      "gpbiometrics"
    ),
    notes = "",
    stringsAsFactors = FALSE
  )

  optional <- data.frame(
    field = c(
      "export_file",
      "export_date",
      "coordinate_system",
      "screen_resolution",
      "units",
      "preprocessing_steps",
      "quality_control_rules",
      "exclusion_rules",
      "analysis_manifest",
      "data_dictionary"
    ),
    description = c(
      "Name of the export file described by this sidecar.",
      "Date or timestamp when the export was created.",
      "Coordinate system used for gaze or screen-position variables.",
      "Screen resolution used during recording.",
      "Units for key numeric columns.",
      "Documented preprocessing steps.",
      "Documented quality-control rules or thresholds.",
      "Documented exclusion rules.",
      "Associated analysis manifest path or identifier.",
      "Associated data dictionary path or identifier."
    ),
    required = FALSE,
    value = "",
    notes = "",
    stringsAsFactors = FALSE
  )

  out <- if (include_optional) {
    rbind(required, optional)
  } else {
    required
  }

  if (!is.null(custom_fields)) {
    out <- rbind(out, gpds_normalize_custom_sidecar_fields(custom_fields))
  }

  rownames(out) <- NULL
  class(out) <- c("gazepoint_sidecar_template", class(out))
  out
}

gpds_check_character_path <- function(path) {
  if (!is.character(path) || length(path) == 0 || any(is.na(path)) || any(!nzchar(path))) {
    stop("`path` must be a non-empty character vector.", call. = FALSE)
  }

  invisible(TRUE)
}

gpds_check_root_dir <- function(root) {
  if (!is.character(root) || length(root) != 1 || is.na(root) || !nzchar(root)) {
    stop("`root` must be a single non-empty directory path.", call. = FALSE)
  }

  if (!dir.exists(root)) {
    stop("`root` does not exist or is not a directory.", call. = FALSE)
  }

  invisible(TRUE)
}

gpds_check_logical_one <- function(x, name) {
  if (!is.logical(x) || length(x) != 1 || is.na(x)) {
    stop("`", name, "` must be TRUE or FALSE.", call. = FALSE)
  }

  invisible(TRUE)
}

gpds_optional_character <- function(x, name) {
  if (is.null(x)) {
    return(NULL)
  }

  if (!is.character(x) || any(is.na(x))) {
    stop("`", name, "` must be NULL or a character vector.", call. = FALSE)
  }

  x[nzchar(x)]
}

gpds_optional_scalar_character <- function(x, name) {
  if (is.null(x)) {
    return(NULL)
  }

  if (!is.character(x) || length(x) != 1 || is.na(x)) {
    stop("`", name, "` must be NULL or a single character string.", call. = FALSE)
  }

  x
}

gpds_value_or_blank <- function(x) {
  if (is.null(x)) {
    ""
  } else {
    x
  }
}

gpds_collect_files <- function(path, recursive, include_hidden) {
  existing <- path[file.exists(path)]

  if (length(existing) != length(path)) {
    missing <- setdiff(path, existing)
    stop("Path(s) not found: ", paste(missing, collapse = ", "), call. = FALSE)
  }

  files <- character(0)

  for (p in path) {
    if (dir.exists(p)) {
      files <- c(
        files,
        list.files(
          p,
          recursive = recursive,
          all.files = include_hidden,
          full.names = TRUE,
          no.. = TRUE
        )
      )
    } else {
      files <- c(files, p)
    }
  }

  files <- files[file.exists(files)]
  files <- files[!dir.exists(files)]
  unique(files)
}

gpds_empty_inventory <- function() {
  data.frame(
    path = character(0),
    relative_path = character(0),
    directory = character(0),
    file_name = character(0),
    extension = character(0),
    size_bytes = numeric(0),
    modified_time = as.POSIXct(character(0)),
    is_empty = logical(0),
    likely_export_type = character(0),
    participant_id = character(0),
    has_sidecar = logical(0),
    stringsAsFactors = FALSE
  )
}

gpds_normalize_path <- function(path, must_work = FALSE) {
  out <- normalizePath(path, winslash = "/", mustWork = must_work)
  gsub("\\\\", "/", out)
}

gpds_common_root <- function(original_path, normalized_files) {
  dirs <- original_path[dir.exists(original_path)]

  if (length(dirs) == 1) {
    return(gpds_normalize_path(dirs, must_work = TRUE))
  }

  if (length(dirs) > 1) {
    normalized_dirs <- gpds_normalize_path(dirs, must_work = TRUE)
    split_dirs <- strsplit(normalized_dirs, "/", fixed = TRUE)
    min_len <- min(vapply(split_dirs, length, integer(1)))
    common <- character(0)

    for (i in seq_len(min_len)) {
      values <- vapply(split_dirs, `[`, character(1), i)

      if (length(unique(values)) == 1) {
        common <- c(common, values[1])
      } else {
        break
      }
    }

    if (length(common) > 0) {
      return(paste(common, collapse = "/"))
    }
  }

  if (length(normalized_files) == 0) {
    return(getwd())
  }

  dirname(normalized_files[1])
}

gpds_relative_path <- function(paths, root) {
  root <- sub("/$", "", gpds_normalize_path(root, must_work = FALSE))
  paths <- gpds_normalize_path(paths, must_work = FALSE)
  out <- sub(paste0("^", gpds_escape_regex(root), "/?"), "", paths)
  out
}

gpds_escape_regex <- function(x) {
  gsub("([][{}()+*^$|\\\\?.])", "\\\\\\1", x)
}

gpds_classify_export_type <- function(file_name) {
  name <- tolower(file_name)

  if (grepl("\\.json$", name)) {
    return("sidecar")
  }

  if (grepl("all[-_ ]?gaze|gazedata|gaze", name)) {
    return("all_gaze")
  }

  if (grepl("fixation|fixations", name)) {
    return("fixations")
  }

  if (grepl("summary|summaries", name)) {
    return("summary")
  }

  if (grepl("eda|gsr|ecg|ppg|hrv|ibi|heart|biometric|physio", name)) {
    return("biometrics")
  }

  if (grepl("event|marker|ttl|trigger", name)) {
    return("events")
  }

  if (grepl("aoi", name)) {
    return("aoi")
  }

  "unknown"
}

gpds_extract_participant_id <- function(relative_path) {
  parts <- unlist(strsplit(relative_path, "[/\\\\]", perl = TRUE), use.names = FALSE)
  hit <- grep("^sub[-_A-Za-z0-9]+", parts, value = TRUE)

  if (length(hit) > 0) {
    return(hit[1])
  }

  hit <- regmatches(relative_path, regexpr("P[0-9]{2,}", relative_path, perl = TRUE))

  if (length(hit) > 0 && nzchar(hit)) {
    return(hit)
  }

  NA_character_
}

gpds_has_sidecar <- function(paths) {
  stems <- tools::file_path_sans_ext(paths)
  ext <- tolower(tools::file_ext(paths))
  out <- file.exists(paste0(stems, ".json"))
  out[ext == "json"] <- TRUE
  out
}

gpds_issue_frame <- function(check, item, status, message, path = NA_character_) {
  data.frame(
    check = check,
    item = item,
    status = status,
    message = message,
    path = path,
    stringsAsFactors = FALSE
  )
}

gpds_check_expected_dirs <- function(root, expected_dirs) {
  if (is.null(expected_dirs) || length(expected_dirs) == 0) {
    return(gpds_issue_frame("expected_dirs", NA_character_, "not_checked", "No expected directories supplied."))
  }

  rows <- lapply(expected_dirs, function(d) {
    full <- file.path(root, d)
    exists <- dir.exists(full)

    gpds_issue_frame(
      "expected_dirs",
      d,
      if (exists) "pass" else "fail",
      if (exists) "Expected directory exists." else "Expected directory is missing.",
      gpds_normalize_path(full, must_work = FALSE)
    )
  })

  do.call(rbind, rows)
}

gpds_check_expected_files <- function(root, expected_files) {
  if (is.null(expected_files) || length(expected_files) == 0) {
    return(gpds_issue_frame("expected_files", NA_character_, "not_checked", "No expected files supplied."))
  }

  rows <- lapply(expected_files, function(f) {
    full <- file.path(root, f)
    exists <- file.exists(full) && !dir.exists(full)

    gpds_issue_frame(
      "expected_files",
      f,
      if (exists) "pass" else "fail",
      if (exists) "Expected file exists." else "Expected file is missing.",
      gpds_normalize_path(full, must_work = FALSE)
    )
  })

  do.call(rbind, rows)
}

gpds_check_expected_patterns <- function(inventory, expected_patterns) {
  if (is.null(expected_patterns) || length(expected_patterns) == 0) {
    return(gpds_issue_frame("expected_patterns", NA_character_, "not_checked", "No expected filename patterns supplied."))
  }

  pattern_names <- names(expected_patterns)

  if (is.null(pattern_names)) {
    pattern_names <- expected_patterns
  } else {
    pattern_names[!nzchar(pattern_names)] <- expected_patterns[!nzchar(pattern_names)]
  }

  rows <- lapply(seq_along(expected_patterns), function(i) {
    pattern <- expected_patterns[[i]]
    matched <- any(grepl(pattern, inventory$relative_path, ignore.case = TRUE, perl = TRUE))

    gpds_issue_frame(
      "expected_patterns",
      pattern_names[[i]],
      if (matched) "pass" else "fail",
      if (matched) "At least one file matched the expected pattern." else "No files matched the expected pattern.",
      NA_character_
    )
  })

  do.call(rbind, rows)
}

gpds_check_duplicate_file_names <- function(inventory) {
  if (nrow(inventory) == 0) {
    return(gpds_issue_frame("duplicate_file_names", NA_character_, "not_checked", "No files were found."))
  }

  duplicated_names <- unique(inventory$file_name[duplicated(inventory$file_name)])

  if (length(duplicated_names) == 0) {
    return(gpds_issue_frame("duplicate_file_names", NA_character_, "pass", "No duplicate file names were found."))
  }

  rows <- lapply(duplicated_names, function(name) {
    gpds_issue_frame(
      "duplicate_file_names",
      name,
      "warn",
      "Duplicate file name found in multiple folders.",
      paste(inventory$relative_path[inventory$file_name == name], collapse = ";")
    )
  })

  do.call(rbind, rows)
}

gpds_check_empty_files <- function(inventory) {
  if (nrow(inventory) == 0) {
    return(gpds_issue_frame("empty_files", NA_character_, "not_checked", "No files were found."))
  }

  empty <- inventory[inventory$is_empty, , drop = FALSE]

  if (nrow(empty) == 0) {
    return(gpds_issue_frame("empty_files", NA_character_, "pass", "No empty files were found."))
  }

  rows <- lapply(seq_len(nrow(empty)), function(i) {
    gpds_issue_frame(
      "empty_files",
      empty$file_name[i],
      "fail",
      "File is empty.",
      empty$relative_path[i]
    )
  })

  do.call(rbind, rows)
}

gpds_check_unexpected_extensions <- function(inventory, allowed_extensions) {
  if (is.null(allowed_extensions) || length(allowed_extensions) == 0) {
    return(gpds_issue_frame("unexpected_extensions", NA_character_, "not_checked", "No allowed extensions supplied."))
  }

  if (nrow(inventory) == 0) {
    return(gpds_issue_frame("unexpected_extensions", NA_character_, "not_checked", "No files were found."))
  }

  bad <- inventory[
    !inventory$extension %in% allowed_extensions |
      is.na(inventory$extension) |
      !nzchar(inventory$extension),
    ,
    drop = FALSE
  ]

  if (nrow(bad) == 0) {
    return(gpds_issue_frame("unexpected_extensions", NA_character_, "pass", "All file extensions were allowed."))
  }

  rows <- lapply(seq_len(nrow(bad)), function(i) {
    gpds_issue_frame(
      "unexpected_extensions",
      bad$extension[i],
      "warn",
      "File extension is not in `allowed_extensions`.",
      bad$relative_path[i]
    )
  })

  do.call(rbind, rows)
}

gpds_check_sidecars <- function(inventory, require_sidecars) {
  if (!require_sidecars) {
    return(gpds_issue_frame("sidecars", NA_character_, "not_checked", "Sidecars were not required."))
  }

  if (nrow(inventory) == 0) {
    return(gpds_issue_frame("sidecars", NA_character_, "not_checked", "No files were found."))
  }

  ext <- tolower(inventory$extension)
  needs_sidecar <- ext != "json"
  missing <- inventory[needs_sidecar & !inventory$has_sidecar, , drop = FALSE]

  if (nrow(missing) == 0) {
    return(gpds_issue_frame("sidecars", NA_character_, "pass", "All non-sidecar files had same-stem JSON sidecars."))
  }

  rows <- lapply(seq_len(nrow(missing)), function(i) {
    gpds_issue_frame(
      "sidecars",
      missing$file_name[i],
      "warn",
      "No same-stem JSON sidecar was found.",
      missing$relative_path[i]
    )
  })

  do.call(rbind, rows)
}

gpds_dataset_audit_summary <- function(results, inventory) {
  status <- results$status

  data.frame(
    n_files = nrow(inventory),
    n_directories = length(unique(inventory$directory)),
    total_size_bytes = sum(inventory$size_bytes, na.rm = TRUE),
    n_pass = sum(status == "pass", na.rm = TRUE),
    n_warn = sum(status == "warn", na.rm = TRUE),
    n_fail = sum(status == "fail", na.rm = TRUE),
    n_not_checked = sum(status == "not_checked", na.rm = TRUE),
    audit_pass = !any(status == "fail", na.rm = TRUE),
    stringsAsFactors = FALSE
  )
}

gpds_normalize_custom_sidecar_fields <- function(custom_fields) {
  if (!is.data.frame(custom_fields)) {
    stop("`custom_fields` must be a data frame.", call. = FALSE)
  }

  required_cols <- c("field", "description")
  missing_cols <- setdiff(required_cols, names(custom_fields))

  if (length(missing_cols) > 0) {
    stop(
      "`custom_fields` is missing required column(s): ",
      paste(missing_cols, collapse = ", "),
      call. = FALSE
    )
  }

  out <- custom_fields

  if (!"required" %in% names(out)) {
    out$required <- FALSE
  }

  if (!"value" %in% names(out)) {
    out$value <- ""
  }

  if (!"notes" %in% names(out)) {
    out$notes <- ""
  }

  out <- out[, c("field", "description", "required", "value", "notes"), drop = FALSE]
  out$field <- as.character(out$field)
  out$description <- as.character(out$description)
  out$required <- as.logical(out$required)
  out$value <- as.character(out$value)
  out$notes <- as.character(out$notes)

  if (any(!nzchar(out$field)) || any(!nzchar(out$description))) {
    stop("`custom_fields$field` and `custom_fields$description` must be non-empty.", call. = FALSE)
  }

  if (any(is.na(out$required))) {
    stop("`custom_fields$required` must contain TRUE or FALSE values.", call. = FALSE)
  }

  out
}
