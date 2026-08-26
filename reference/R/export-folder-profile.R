utils::globalVariables(c(
  "extension", "n", "role", "missing_prop", "column",
  "file_label", "metric", "value"
))

#' Profile a Gazepoint export folder before analysis
#'
#' Create a compact, auditable profile of a Gazepoint-style export folder
#' before running a full workflow. The profiler inspects files, row and column
#' counts, likely Gazepoint column roles, missingness, numeric signal activity,
#' constant columns, all-zero columns, and read errors.
#'
#' @param path Path to a folder containing Gazepoint-style export files.
#' @param pattern File-name regular expression. Defaults to CSV files.
#' @param recursive Logical. If `TRUE`, search subfolders recursively.
#' @param max_files Maximum number of matching files to inspect.
#' @param max_rows Maximum number of rows to read per file for profiling.
#'   Use `Inf` to read complete files.
#' @param na.strings Character vector of strings to treat as missing values.
#'
#' @return A list with class `"gazepoint_export_folder_profile"` containing
#'   `overview`, `files`, `columns`, `warnings`, and `settings` tables.
#'
#' @examples
#' demo_dir <- system.file(
#'   "extdata",
#'   "gazepoint_biometrics_kiosk_demo_exports",
#'   package = "gpbiometrics"
#' )
#'
#' if (nzchar(demo_dir)) {
#'   profile <- profile_gazepoint_export_folder(demo_dir, max_files = 2)
#'   profile
#' }
#'
#' @export
profile_gazepoint_export_folder <- function(path,
                                            pattern = "\\.csv$",
                                            recursive = FALSE,
                                            max_files = Inf,
                                            max_rows = Inf,
                                            na.strings = c("", "NA", "NaN")) {
  if (!is.character(path) || length(path) != 1L || is.na(path)) {
    stop("`path` must be a single folder path.", call. = FALSE)
  }

  if (!dir.exists(path)) {
    stop("`path` does not exist or is not a folder: ", path, call. = FALSE)
  }

  if (!is.character(pattern) || length(pattern) != 1L || is.na(pattern)) {
    stop("`pattern` must be a single regular expression.", call. = FALSE)
  }

  if (!is.logical(recursive) || length(recursive) != 1L || is.na(recursive)) {
    stop("`recursive` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.numeric(max_files) || length(max_files) != 1L ||
      is.na(max_files) || max_files <= 0) {
    stop("`max_files` must be a positive number.", call. = FALSE)
  }

  if (!is.numeric(max_rows) || length(max_rows) != 1L ||
      is.na(max_rows) || max_rows <= 0) {
    stop("`max_rows` must be a positive number or Inf.", call. = FALSE)
  }

  files <- list.files(
    path = path,
    pattern = pattern,
    recursive = recursive,
    full.names = TRUE,
    ignore.case = TRUE
  )

  files <- sort(files)

  if (is.finite(max_files) && length(files) > max_files) {
    files <- files[seq_len(max_files)]
  }

  settings <- data.frame(
    path = normalizePath(path, winslash = "/", mustWork = FALSE),
    pattern = pattern,
    recursive = recursive,
    max_files = max_files,
    max_rows = max_rows,
    stringsAsFactors = FALSE
  )

  if (length(files) == 0L) {
    overview <- data.frame(
      path = settings$path,
      n_files = 0L,
      n_readable_files = 0L,
      n_read_errors = 0L,
      total_rows_profiled = 0L,
      total_size_bytes = 0,
      n_unique_extensions = 0L,
      n_unique_column_sets = 0L,
      any_time_columns = FALSE,
      any_ttl_columns = FALSE,
      any_aoi_columns = FALSE,
      any_signal_columns = FALSE,
      stringsAsFactors = FALSE
    )

    warnings <- data.frame(
      severity = "warning",
      issue = "no_matching_files",
      message = paste0(
        "No files matching pattern `", pattern, "` were found in `",
        settings$path, "`."
      ),
      stringsAsFactors = FALSE
    )

    out <- list(
      overview = overview,
      files = .gp_efp_empty_files(),
      columns = .gp_efp_empty_columns(),
      warnings = warnings,
      settings = settings
    )

    class(out) <- "gazepoint_export_folder_profile"
    return(out)
  }

  file_profiles <- vector("list", length(files))
  column_profiles <- vector("list", length(files))

  for (i in seq_along(files)) {
    one <- .gp_efp_profile_file(
      file = files[[i]],
      root = path,
      max_rows = max_rows,
      na.strings = na.strings
    )

    file_profiles[[i]] <- one$file
    column_profiles[[i]] <- one$columns
  }

  file_table <- do.call(rbind, file_profiles)
  column_table <- do.call(rbind, column_profiles)

  if (NROW(column_table) == 0L) {
    column_table <- .gp_efp_empty_columns()
  }

  readable <- file_table$status == "readable"

  overview <- data.frame(
    path = settings$path,
    n_files = NROW(file_table),
    n_readable_files = sum(readable, na.rm = TRUE),
    n_read_errors = sum(file_table$status == "read_error", na.rm = TRUE),
    total_rows_profiled = sum(file_table$n_rows, na.rm = TRUE),
    total_size_bytes = sum(file_table$size_bytes, na.rm = TRUE),
    n_unique_extensions = length(unique(file_table$extension)),
    n_unique_column_sets = length(unique(file_table$column_signature[readable])),
    any_time_columns = any(column_table$role == "time", na.rm = TRUE),
    any_ttl_columns = any(column_table$role == "ttl_event", na.rm = TRUE),
    any_aoi_columns = any(column_table$role == "aoi", na.rm = TRUE),
    any_signal_columns = any(
      column_table$role %in% c(
        "gaze", "pupil", "eda_gsr", "heart_rate",
        "ibi_rr", "ppg_pulse", "engagement_dial"
      ),
      na.rm = TRUE
    ),
    stringsAsFactors = FALSE
  )

  warnings <- .gp_efp_make_warnings(overview, file_table, column_table)

  out <- list(
    overview = overview,
    files = file_table,
    columns = column_table,
    warnings = warnings,
    settings = settings
  )

  class(out) <- "gazepoint_export_folder_profile"
  out
}

#' Compare Gazepoint export-folder profiles
#'
#' Compare two or more objects created by
#' `profile_gazepoint_export_folder()`. The comparison reports folder-level
#' dimensions and column-role coverage across profiles.
#'
#' @param ... Profile objects returned by `profile_gazepoint_export_folder()`,
#'   or a single list of profile objects.
#' @param labels Optional labels for the profiles.
#'
#' @return A list with class `"gazepoint_export_profile_comparison"`.
#'
#' @export
compare_gazepoint_export_profiles <- function(..., labels = NULL) {
  profiles <- list(...)

  if (length(profiles) == 1L && is.list(profiles[[1L]]) &&
      !inherits(profiles[[1L]], "gazepoint_export_folder_profile")) {
    profiles <- profiles[[1L]]
  }

  if (length(profiles) < 2L) {
    stop("Provide at least two export-folder profiles.", call. = FALSE)
  }

  ok <- vapply(
    profiles,
    inherits,
    logical(1),
    what = "gazepoint_export_folder_profile"
  )

  if (!all(ok)) {
    stop(
      "All inputs must be objects returned by ",
      "`profile_gazepoint_export_folder()`.",
      call. = FALSE
    )
  }

  if (is.null(labels)) {
    labels <- names(profiles)
    if (is.null(labels) || any(!nzchar(labels))) {
      labels <- paste0("profile_", seq_along(profiles))
    }
  }

  if (!is.character(labels) || length(labels) != length(profiles)) {
    stop("`labels` must have one label per profile.", call. = FALSE)
  }

  overview <- do.call(
    rbind,
    Map(function(profile, label) {
      x <- profile$overview
      x$profile <- label
      x[, c("profile", setdiff(names(x), "profile")), drop = FALSE]
    }, profiles, labels)
  )

  role_coverage <- do.call(
    rbind,
    Map(function(profile, label) {
      cols <- profile$columns
      if (NROW(cols) == 0L) {
        return(data.frame(
          profile = label,
          role = character(0),
          n_columns = integer(0),
          stringsAsFactors = FALSE
        ))
      }

      tab <- as.data.frame(table(cols$role), stringsAsFactors = FALSE)
      names(tab) <- c("role", "n_columns")
      tab$profile <- label
      tab[, c("profile", "role", "n_columns"), drop = FALSE]
    }, profiles, labels)
  )

  all_columns <- unique(unlist(lapply(profiles, function(x) x$columns$column)))
  all_columns <- sort(all_columns)

  column_presence <- do.call(
    rbind,
    lapply(all_columns, function(col) {
      present <- vapply(
        profiles,
        function(profile) col %in% profile$columns$column,
        logical(1)
      )

      data.frame(
        column = col,
        n_profiles_present = sum(present),
        profiles_present = paste(labels[present], collapse = "; "),
        stringsAsFactors = FALSE
      )
    })
  )

  out <- list(
    overview = overview,
    role_coverage = role_coverage,
    column_presence = column_presence,
    labels = labels
  )

  class(out) <- "gazepoint_export_profile_comparison"
  out
}

#' Write a Gazepoint export-folder profile to disk
#'
#' Export profile tables and a compact text summary.
#'
#' @param profile Object returned by `profile_gazepoint_export_folder()`.
#' @param path Output folder.
#' @param prefix File prefix.
#' @param overwrite Logical. If `FALSE`, existing files are not overwritten.
#'
#' @return A data frame listing written files.
#'
#' @export
write_gazepoint_export_profile <- function(profile,
                                           path,
                                           prefix = "gazepoint_export_profile",
                                           overwrite = FALSE) {
  if (!inherits(profile, "gazepoint_export_folder_profile")) {
    stop(
      "`profile` must be returned by `profile_gazepoint_export_folder()`.",
      call. = FALSE
    )
  }

  if (!is.character(path) || length(path) != 1L || is.na(path)) {
    stop("`path` must be a single output folder path.", call. = FALSE)
  }

  if (!dir.exists(path)) {
    dir.create(path, recursive = TRUE, showWarnings = FALSE)
  }

  if (!dir.exists(path)) {
    stop("Could not create output folder: ", path, call. = FALSE)
  }

  if (!is.character(prefix) || length(prefix) != 1L ||
      is.na(prefix) || !nzchar(prefix)) {
    stop("`prefix` must be a non-empty string.", call. = FALSE)
  }

  files <- data.frame(
    component = c("overview", "files", "columns", "warnings", "summary"),
    file = file.path(
      path,
      paste0(
        prefix,
        c("_overview.csv", "_files.csv", "_columns.csv", "_warnings.csv", "_summary.txt")
      )
    ),
    stringsAsFactors = FALSE
  )

  existing <- file.exists(files$file)

  if (any(existing) && !isTRUE(overwrite)) {
    stop(
      "Output file(s) already exist. Use `overwrite = TRUE` to replace them: ",
      paste(files$file[existing], collapse = "; "),
      call. = FALSE
    )
  }

  utils::write.csv(profile$overview, files$file[files$component == "overview"], row.names = FALSE)
  utils::write.csv(profile$files, files$file[files$component == "files"], row.names = FALSE)
  utils::write.csv(profile$columns, files$file[files$component == "columns"], row.names = FALSE)
  utils::write.csv(profile$warnings, files$file[files$component == "warnings"], row.names = FALSE)

  txt <- c(
    "Gazepoint export folder profile",
    "================================",
    "",
    paste0("Path: ", profile$settings$path),
    paste0("Pattern: ", profile$settings$pattern),
    paste0("Recursive: ", profile$settings$recursive),
    "",
    utils::capture.output(print(profile))
  )

  writeLines(txt, files$file[files$component == "summary"], useBytes = TRUE)

  files
}

#' Plot a Gazepoint export-folder profile
#'
#' Create compact plots for file extensions, detected column roles, mean
#' missingness, or numeric signal activity.
#'
#' @param profile Object returned by `profile_gazepoint_export_folder()`.
#' @param type Plot type. One of `"files"`, `"roles"`, `"missingness"`,
#'   or `"activity"`.
#' @param top_n Number of columns or files to show for selected plots.
#'
#' @return A `ggplot` object.
#'
#' @export
plot_gazepoint_export_profile <- function(profile,
                                          type = c(
                                            "files",
                                            "roles",
                                            "missingness",
                                            "activity"
                                          ),
                                          top_n = 20) {
  if (!inherits(profile, "gazepoint_export_folder_profile")) {
    stop(
      "`profile` must be returned by `profile_gazepoint_export_folder()`.",
      call. = FALSE
    )
  }

  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    stop("Package `ggplot2` is required for plotting.", call. = FALSE)
  }

  type <- match.arg(type)

  if (!is.numeric(top_n) || length(top_n) != 1L || is.na(top_n) || top_n <= 0) {
    stop("`top_n` must be a positive number.", call. = FALSE)
  }

  if (type == "files") {
    df <- as.data.frame(table(profile$files$extension), stringsAsFactors = FALSE)
    names(df) <- c("extension", "n")

    return(
      ggplot2::ggplot(df, ggplot2::aes(x = extension, y = n)) +
        ggplot2::geom_col() +
        ggplot2::labs(
          x = "File extension",
          y = "Number of files",
          title = "Gazepoint export-folder file types"
        ) +
        ggplot2::theme_minimal()
    )
  }

  if (type == "roles") {
    cols <- profile$columns

    if (NROW(cols) == 0L) {
      stop("No column profile is available to plot.", call. = FALSE)
    }

    df <- as.data.frame(table(cols$role), stringsAsFactors = FALSE)
    names(df) <- c("role", "n")
    df <- df[order(df$n, decreasing = TRUE), , drop = FALSE]
    df$role <- factor(df$role, levels = rev(df$role))

    return(
      ggplot2::ggplot(df, ggplot2::aes(x = role, y = n)) +
        ggplot2::geom_col() +
        ggplot2::coord_flip() +
        ggplot2::labs(
          x = "Detected column role",
          y = "Number of columns",
          title = "Detected Gazepoint-style column roles"
        ) +
        ggplot2::theme_minimal()
    )
  }

  if (type == "missingness") {
    cols <- profile$columns

    if (NROW(cols) == 0L) {
      stop("No column profile is available to plot.", call. = FALSE)
    }

    df <- stats::aggregate(
      missing_prop ~ column + role,
      data = cols,
      FUN = mean,
      na.rm = TRUE
    )

    df <- df[order(df$missing_prop, decreasing = TRUE), , drop = FALSE]
    df <- utils::head(df, top_n)
    df$column <- factor(df$column, levels = rev(df$column))

    return(
      ggplot2::ggplot(df, ggplot2::aes(x = column, y = missing_prop)) +
        ggplot2::geom_col() +
        ggplot2::coord_flip() +
        ggplot2::labs(
          x = "Column",
          y = "Mean missing proportion",
          title = "Highest-missingness columns"
        ) +
        ggplot2::theme_minimal()
    )
  }

  activity <- profile$files[, c(
    "file_label",
    "constant_numeric_cols",
    "zero_numeric_cols"
  ), drop = FALSE]

  activity <- activity[order(
    activity$constant_numeric_cols + activity$zero_numeric_cols,
    decreasing = TRUE
  ), , drop = FALSE]

  activity <- utils::head(activity, top_n)

  df <- rbind(
    data.frame(
      file_label = activity$file_label,
      metric = "constant numeric columns",
      value = activity$constant_numeric_cols,
      stringsAsFactors = FALSE
    ),
    data.frame(
      file_label = activity$file_label,
      metric = "all-zero numeric columns",
      value = activity$zero_numeric_cols,
      stringsAsFactors = FALSE
    )
  )

  df$file_label <- factor(df$file_label, levels = rev(unique(activity$file_label)))

  ggplot2::ggplot(df, ggplot2::aes(x = file_label, y = value, fill = metric)) +
    ggplot2::geom_col(position = "dodge") +
    ggplot2::coord_flip() +
    ggplot2::labs(
      x = "File",
      y = "Number of columns",
      fill = "Metric",
      title = "Numeric signal-activity indicators"
    ) +
    ggplot2::theme_minimal()
}

#' @export
print.gazepoint_export_folder_profile <- function(x, ...) {
  cat("Gazepoint export folder profile\n")
  cat("--------------------------------\n")
  print(x$overview, row.names = FALSE)

  if (NROW(x$warnings) > 0L) {
    cat("\nWarnings\n")
    print(x$warnings, row.names = FALSE)
  } else {
    cat("\nNo folder-level warnings detected.\n")
  }

  invisible(x)
}

#' @export
print.gazepoint_export_profile_comparison <- function(x, ...) {
  cat("Gazepoint export-folder profile comparison\n")
  cat("------------------------------------------\n")
  print(x$overview, row.names = FALSE)

  cat("\nColumn-role coverage\n")
  print(x$role_coverage, row.names = FALSE)

  invisible(x)
}

.gp_efp_profile_file <- function(file, root, max_rows, na.strings) {
  info <- file.info(file)

  relative_path <- .gp_efp_relative_path(file, root)
  extension <- tools::file_ext(file)
  if (!nzchar(extension)) {
    extension <- "(none)"
  }

  nrows <- if (is.finite(max_rows)) as.integer(max_rows) else -1L

  dat <- tryCatch(
    withCallingHandlers(
      utils::read.csv(
        file,
        stringsAsFactors = FALSE,
        check.names = FALSE,
        na.strings = na.strings,
        nrows = nrows
      ),
      warning = function(w) {
        stop(conditionMessage(w), call. = FALSE)
      }
    ),
    error = function(e) e
  )

  if (inherits(dat, "error")) {
    file_row <- data.frame(
      file = normalizePath(file, winslash = "/", mustWork = FALSE),
      relative_path = relative_path,
      file_label = basename(file),
      extension = tolower(extension),
      size_bytes = info$size,
      modified_time = as.character(info$mtime),
      status = "read_error",
      n_rows = NA_integer_,
      n_cols = NA_integer_,
      column_signature = NA_character_,
      column_names = NA_character_,
      time_columns = NA_character_,
      ttl_columns = NA_character_,
      aoi_columns = NA_character_,
      gaze_columns = NA_character_,
      pupil_columns = NA_character_,
      eda_gsr_columns = NA_character_,
      heart_rate_columns = NA_character_,
      ibi_rr_columns = NA_character_,
      ppg_pulse_columns = NA_character_,
      engagement_dial_columns = NA_character_,
      numeric_cols = NA_integer_,
      constant_numeric_cols = NA_integer_,
      zero_numeric_cols = NA_integer_,
      read_error = conditionMessage(dat),
      stringsAsFactors = FALSE
    )

    return(list(file = file_row, columns = .gp_efp_empty_columns()))
  }

  cols <- names(dat)
  roles <- .gp_efp_detect_roles(cols)

  col_table <- .gp_efp_profile_columns(dat, file, relative_path, roles)

  file_row <- data.frame(
    file = normalizePath(file, winslash = "/", mustWork = FALSE),
    relative_path = relative_path,
    file_label = basename(file),
    extension = tolower(extension),
    size_bytes = info$size,
    modified_time = as.character(info$mtime),
    status = "readable",
    n_rows = NROW(dat),
    n_cols = NCOL(dat),
    column_signature = paste(sort(cols), collapse = " | "),
    column_names = .gp_efp_collapse(cols),
    time_columns = .gp_efp_collapse(cols[roles == "time"]),
    ttl_columns = .gp_efp_collapse(cols[roles == "ttl_event"]),
    aoi_columns = .gp_efp_collapse(cols[roles == "aoi"]),
    gaze_columns = .gp_efp_collapse(cols[roles == "gaze"]),
    pupil_columns = .gp_efp_collapse(cols[roles == "pupil"]),
    eda_gsr_columns = .gp_efp_collapse(cols[roles == "eda_gsr"]),
    heart_rate_columns = .gp_efp_collapse(cols[roles == "heart_rate"]),
    ibi_rr_columns = .gp_efp_collapse(cols[roles == "ibi_rr"]),
    ppg_pulse_columns = .gp_efp_collapse(cols[roles == "ppg_pulse"]),
    engagement_dial_columns = .gp_efp_collapse(cols[roles == "engagement_dial"]),
    numeric_cols = sum(vapply(dat, is.numeric, logical(1))),
    constant_numeric_cols = sum(col_table$constant & col_table$type == "numeric", na.rm = TRUE),
    zero_numeric_cols = sum(col_table$all_zero & col_table$type == "numeric", na.rm = TRUE),
    read_error = NA_character_,
    stringsAsFactors = FALSE
  )

  list(file = file_row, columns = col_table)
}

.gp_efp_profile_columns <- function(dat, file, relative_path, roles) {
  cols <- names(dat)

  rows <- lapply(seq_along(cols), function(i) {
    x <- dat[[i]]
    non_missing <- x[!is.na(x)]

    type <- if (is.numeric(x)) {
      "numeric"
    } else if (is.logical(x)) {
      "logical"
    } else if (inherits(x, "Date")) {
      "date"
    } else if (inherits(x, "POSIXt")) {
      "datetime"
    } else {
      "character"
    }

    n_unique <- length(unique(non_missing))

    numeric_sd <- if (is.numeric(x) && length(non_missing) > 1L) {
      stats::sd(non_missing)
    } else {
      NA_real_
    }

    all_zero <- if (is.numeric(x) && length(non_missing) > 0L) {
      all(non_missing == 0)
    } else {
      FALSE
    }

    constant <- if (length(non_missing) > 0L) {
      n_unique <= 1L
    } else {
      NA
    }

    data.frame(
      file = normalizePath(file, winslash = "/", mustWork = FALSE),
      relative_path = relative_path,
      file_label = basename(file),
      column = cols[[i]],
      role = roles[[i]],
      type = type,
      n_missing = sum(is.na(x)),
      missing_prop = mean(is.na(x)),
      n_unique = n_unique,
      numeric_sd = numeric_sd,
      all_zero = all_zero,
      constant = constant,
      stringsAsFactors = FALSE
    )
  })

  do.call(rbind, rows)
}

.gp_efp_detect_roles <- function(cols) {
  vapply(cols, .gp_efp_detect_role, character(1))
}

.gp_efp_detect_role <- function(col) {
  x <- tryCatch(
    toupper(enc2utf8(col)),
    error = function(e) NA_character_
  )

  if (is.na(x) || !nzchar(x)) {
    return("other")
  }

  if (grepl("^(CNT|TIME|TIME_TICK|TIME_TICK_MS|TIMESTAMP|MSTIMER|TRIAL_TIME|TIME_MS)$", x) ||
      grepl("TIME|TICK|CNT", x)) {
    return("time")
  }

  if (grepl("^TTL|TTL[0-9]+|MARKER|USER_DATA|USER$|EVENT", x)) {
    return("ttl_event")
  }

  if (grepl("AOI|AREA_OF_INTEREST|INTEREST_AREA|IA_", x)) {
    return("aoi")
  }

  if (grepl("PUPIL|LPMM|RPMM|LPD|RPD", x)) {
    return("pupil")
  }

  if (grepl("GSR|EDA|SCR|SCL|PHASIC|TONIC", x)) {
    return("eda_gsr")
  }

  if (grepl("^(HR|BPM)$|HEART|HEART_RATE|HEARTRATE", x)) {
    return("heart_rate")
  }

  if (grepl("IBI|RRI|RR_INTERVAL|RR$|NNI|NN_INTERVAL", x)) {
    return("ibi_rr")
  }

  if (grepl("PPG|PULSE|HRP|BVP", x)) {
    return("ppg_pulse")
  }

  if (grepl("DIAL|ENGAGEMENT", x)) {
    return("engagement_dial")
  }

  if (grepl("FPOG|BPOG|LPOG|RPOG|GAZE|X$|Y$", x)) {
    return("gaze")
  }

  "other"
}

.gp_efp_make_warnings <- function(overview, files, columns) {
  out <- list()

  if (overview$n_read_errors > 0L) {
    out[[length(out) + 1L]] <- data.frame(
      severity = "warning",
      issue = "read_errors",
      message = paste0(
        overview$n_read_errors,
        " file(s) could not be read. Inspect `profile$files$read_error`."
      ),
      stringsAsFactors = FALSE
    )
  }

  if (overview$n_readable_files == 0L) {
    out[[length(out) + 1L]] <- data.frame(
      severity = "error",
      issue = "no_readable_files",
      message = "No matching files could be read.",
      stringsAsFactors = FALSE
    )
  }

  if (overview$n_unique_column_sets > 1L) {
    out[[length(out) + 1L]] <- data.frame(
      severity = "info",
      issue = "multiple_column_sets",
      message = paste0(
        "Readable files contain ",
        overview$n_unique_column_sets,
        " unique column sets."
      ),
      stringsAsFactors = FALSE
    )
  }

  if (!isTRUE(overview$any_time_columns)) {
    out[[length(out) + 1L]] <- data.frame(
      severity = "warning",
      issue = "no_time_columns_detected",
      message = "No likely time columns were detected.",
      stringsAsFactors = FALSE
    )
  }

  if (!isTRUE(overview$any_signal_columns)) {
    out[[length(out) + 1L]] <- data.frame(
      severity = "warning",
      issue = "no_signal_columns_detected",
      message = paste0(
        "No likely gaze, pupil, EDA/GSR, HR, IBI/RR, PPG/pulse, ",
        "or engagement-dial columns were detected."
      ),
      stringsAsFactors = FALSE
    )
  }

  zero_row_files <- files$status == "readable" & !is.na(files$n_rows) & files$n_rows == 0L

  if (any(zero_row_files)) {
    out[[length(out) + 1L]] <- data.frame(
      severity = "warning",
      issue = "zero_row_files",
      message = paste0(
        sum(zero_row_files),
        " readable file(s) contained zero rows."
      ),
      stringsAsFactors = FALSE
    )
  }

  if (NROW(columns) > 0L) {
    all_zero_cols <- columns$type == "numeric" & columns$all_zero
    if (any(all_zero_cols, na.rm = TRUE)) {
      out[[length(out) + 1L]] <- data.frame(
        severity = "info",
        issue = "all_zero_numeric_columns",
        message = paste0(
          sum(all_zero_cols, na.rm = TRUE),
          " numeric column occurrence(s) were all zero."
        ),
        stringsAsFactors = FALSE
      )
    }
  }

  if (length(out) == 0L) {
    return(data.frame(
      severity = character(0),
      issue = character(0),
      message = character(0),
      stringsAsFactors = FALSE
    ))
  }

  do.call(rbind, out)
}

.gp_efp_relative_path <- function(file, root) {
  file_n <- normalizePath(file, winslash = "/", mustWork = FALSE)
  root_n <- normalizePath(root, winslash = "/", mustWork = FALSE)
  sub(paste0("^", gsub("([\\W])", "\\\\\\1", root_n), "/?"), "", file_n)
}

.gp_efp_collapse <- function(x) {
  x <- x[!is.na(x) & nzchar(x)]

  if (length(x) == 0L) {
    return(NA_character_)
  }

  paste(unique(x), collapse = "; ")
}

.gp_efp_empty_files <- function() {
  data.frame(
    file = character(0),
    relative_path = character(0),
    file_label = character(0),
    extension = character(0),
    size_bytes = numeric(0),
    modified_time = character(0),
    status = character(0),
    n_rows = integer(0),
    n_cols = integer(0),
    column_signature = character(0),
    column_names = character(0),
    time_columns = character(0),
    ttl_columns = character(0),
    aoi_columns = character(0),
    gaze_columns = character(0),
    pupil_columns = character(0),
    eda_gsr_columns = character(0),
    heart_rate_columns = character(0),
    ibi_rr_columns = character(0),
    ppg_pulse_columns = character(0),
    engagement_dial_columns = character(0),
    numeric_cols = integer(0),
    constant_numeric_cols = integer(0),
    zero_numeric_cols = integer(0),
    read_error = character(0),
    stringsAsFactors = FALSE
  )
}

.gp_efp_empty_columns <- function() {
  data.frame(
    file = character(0),
    relative_path = character(0),
    file_label = character(0),
    column = character(0),
    role = character(0),
    type = character(0),
    n_missing = integer(0),
    missing_prop = numeric(0),
    n_unique = integer(0),
    numeric_sd = numeric(0),
    all_zero = logical(0),
    constant = logical(0),
    stringsAsFactors = FALSE
  )
}
