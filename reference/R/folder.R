#' Import a folder of Gazepoint Biometrics exports
#'
#' Reads rectangular Gazepoint CSV exports from a folder and combines files that
#' contain at least one known Gazepoint Biometrics column. This function is
#' designed for all-gaze and fixation-style exports. Multi-section Gazepoint
#' Data Summary files should be parsed separately.
#'
#' @param path Folder containing Gazepoint CSV exports.
#' @param pattern Regular expression used to identify candidate CSV files.
#' @param recursive Should subfolders be searched?
#' @param include_fixations Should files with `"fixation"` in the file name be
#'   included?
#' @param include_all_gaze Should files with `"all_gaze"` in the file name be
#'   included?
#' @param include_other_csv Should other CSV files be attempted? The default is
#'   `FALSE` to avoid accidentally trying to parse multi-section
#'   `Data_Summary_export` files as rectangular data.
#' @param na Values that should be treated as missing.
#'
#' @return A data frame with all imported rows combined. The output includes a
#'   `source_file` column and has class `"gazepoint_biometrics_folder"`.
#'
#' @export
import_gazepoint_biometric_folder <- function(path,
                                              pattern = "\\.csv$",
                                              recursive = FALSE,
                                              include_fixations = TRUE,
                                              include_all_gaze = TRUE,
                                              include_other_csv = FALSE,
                                              na = c("", "NA", "NaN")) {
  if (missing(path) || length(path) != 1L || !nzchar(path)) {
    stop("`path` must be a single non-empty folder path.", call. = FALSE)
  }

  if (!dir.exists(path)) {
    stop("Folder does not exist: ", path, call. = FALSE)
  }

  files <- list.files(
    path = path,
    pattern = pattern,
    full.names = TRUE,
    recursive = recursive,
    ignore.case = TRUE
  )

  if (length(files) == 0L) {
    stop("No CSV files were found in: ", path, call. = FALSE)
  }

  candidate_files <- keep_candidate_biometric_files(
    files = files,
    include_fixations = include_fixations,
    include_all_gaze = include_all_gaze,
    include_other_csv = include_other_csv
  )

  if (length(candidate_files) == 0L) {
    stop("No candidate Gazepoint biometric CSV files were found.", call. = FALSE)
  }

  imported <- lapply(candidate_files, function(file) {
    dat <- import_gazepoint_biometrics(file, na = na)

    cols <- check_gazepoint_biometric_columns(dat)

    if (!any(cols$present[cols$signal %in% c(
      "gsr_eda",
      "heart_rate",
      "engagement_dial",
      "ttl_marker"
    )])) {
      return(NULL)
    }

    source_file <- basename(file)

    dat$source_file <- source_file
    dat$source_type <- detect_gazepoint_source_type(source_file)
    dat$source_participant <- detect_gazepoint_source_participant(source_file)

    dat
  })

  imported <- imported[!vapply(imported, is.null, logical(1))]

  if (length(imported) == 0L) {
    stop(
      "CSV files were found, but none contained known Gazepoint Biometrics columns.",
      call. = FALSE
    )
  }

  out <- combine_gazepoint_tables(imported)

  attr(out, "source_files") <- basename(candidate_files)
  attr(out, "biometric_columns") <- check_gazepoint_biometric_columns(out)
  attr(out, "active_channels") <- detect_active_biometric_channels(out)

  class(out) <- c("gazepoint_biometrics_folder", "gazepoint_biometrics", class(out))

  out
}


keep_candidate_biometric_files <- function(files,
                                           include_fixations = TRUE,
                                           include_all_gaze = TRUE,
                                           include_other_csv = FALSE) {
  file_names <- basename(files)
  file_names_lower <- tolower(file_names)

  is_data_summary <- grepl("data_summary", file_names_lower)
  is_fixation <- grepl("fixation", file_names_lower)
  is_all_gaze <- grepl("all_gaze", file_names_lower)

  keep <- rep(FALSE, length(files))

  if (include_fixations) {
    keep <- keep | is_fixation
  }

  if (include_all_gaze) {
    keep <- keep | is_all_gaze
  }

  if (include_other_csv) {
    keep <- keep | (!is_data_summary)
  }

  files[keep & !is_data_summary]
}


combine_gazepoint_tables <- function(tables) {
  if (!is.list(tables) || length(tables) == 0L) {
    stop("`tables` must be a non-empty list of data frames.", call. = FALSE)
  }

  all_names <- unique(unlist(lapply(tables, names), use.names = FALSE))

  aligned <- lapply(tables, function(dat) {
    missing_names <- setdiff(all_names, names(dat))

    for (nm in missing_names) {
      dat[[nm]] <- NA
    }

    dat[all_names]
  })

  out <- do.call(rbind, aligned)
  rownames(out) <- NULL
  out
}

detect_gazepoint_source_type <- function(file_name) {
  file_name_lower <- tolower(file_name)

  if (grepl("all_gaze", file_name_lower)) {
    return("all_gaze")
  }

  if (grepl("fixation", file_name_lower)) {
    return("fixations")
  }

  if (grepl("data_summary", file_name_lower)) {
    return("data_summary")
  }

  "other"
}


detect_gazepoint_source_participant <- function(file_name) {
  x <- basename(file_name)

  x <- sub("\\.csv$", "", x, ignore.case = TRUE)
  x <- sub("_all_gaze$", "", x, ignore.case = TRUE)
  x <- sub("_fixations$", "", x, ignore.case = TRUE)
  x <- sub("_fixation$", "", x, ignore.case = TRUE)

  trimws(x)
}
