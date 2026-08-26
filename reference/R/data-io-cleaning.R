
# Gazepoint data import and generic missing-value imputation helpers

.gp_io_clean_path <- function(x) {
  normalizePath(x, winslash = "/", mustWork = FALSE)
}

.gp_io_guess_delimiter <- function(path) {
  first <- readLines(path, n = 1L, warn = FALSE)

  if (!length(first)) {
    return(",")
  }

  counts <- c(
    comma = lengths(regmatches(first, gregexpr(",", first, fixed = TRUE))),
    semicolon = lengths(regmatches(first, gregexpr(";", first, fixed = TRUE))),
    tab = lengths(regmatches(first, gregexpr("\t", first, fixed = TRUE)))
  )

  if (all(counts == 0)) {
    return(",")
  }

  c(comma = ",", semicolon = ";", tab = "\t")[[which.max(counts)]]
}

.gp_io_detect_type <- function(path) {
  b <- tolower(basename(path))

  if (grepl("all[_ -]?gaze|allgaze", b)) return("all_gaze")
  if (grepl("fixation|fixations", b)) return("fixations")
  if (grepl("summary", b)) return("summary")
  if (grepl("biometric|gsr|eda|ppg|bvp|heart|hr|ibi|rri", b)) return("biometrics")
  if (grepl("marker|trigger|ttl|event", b)) return("markers")

  "unknown"
}

.gp_io_safe_name <- function(path, session = NULL) {
  nm <- tools::file_path_sans_ext(basename(path))

  if (!is.null(session) && length(session)) {
    for (ss in session) {
      ss_escaped <- gsub("([][{}()+*^$|\\\\?.])", "\\\\\\1", ss)
      nm <- sub(paste0("^", ss_escaped, "([_ -]+)?"), "", nm, ignore.case = TRUE)
    }
  }

  nm <- gsub("[^A-Za-z0-9_]+", "_", nm)
  nm <- gsub("_+", "_", nm)
  nm <- gsub("^_|_$", "", nm)

  if (!nzchar(nm)) {
    nm <- "gazepoint_file"
  }

  nm
}

.gp_io_session_keep <- function(files,
                                session = NULL,
                                session_match = c("prefix", "contains", "regex")) {
  session_match <- match.arg(session_match)

  if (is.null(session) || !length(session) || all(!nzchar(session))) {
    return(rep(TRUE, length(files)))
  }

  b <- basename(files)

  keep_one <- function(ss) {
    if (session_match == "regex") {
      return(grepl(ss, b, ignore.case = TRUE))
    }

    ss_escaped <- gsub("([][{}()+*^$|\\\\?.])", "\\\\\\1", ss)

    if (session_match == "prefix") {
      return(grepl(paste0("^", ss_escaped), b, ignore.case = TRUE))
    }

    grepl(ss_escaped, b, ignore.case = TRUE)
  }

  Reduce(`|`, lapply(session, keep_one))
}

.gp_io_read_csv <- function(path, file_encoding = "UTF-8-BOM") {
  sep <- .gp_io_guess_delimiter(path)

  utils::read.table(
    file = path,
    header = TRUE,
    sep = sep,
    quote = "\"",
    dec = ".",
    fill = TRUE,
    comment.char = "",
    stringsAsFactors = FALSE,
    check.names = FALSE,
    na.strings = c("", "NA", "NaN", "N/A", "NULL", "null"),
    fileEncoding = file_encoding
  )
}

.gp_impute_find_allowed <- function(is_missing, max_gap) {
  if (!any(is_missing)) {
    return(rep(FALSE, length(is_missing)))
  }

  if (is.infinite(max_gap)) {
    return(is_missing)
  }

  r <- rle(is_missing)
  ends <- cumsum(r$lengths)
  starts <- ends - r$lengths + 1L
  allowed <- rep(FALSE, length(is_missing))

  for (i in seq_along(r$values)) {
    if (isTRUE(r$values[i]) && r$lengths[i] <= max_gap) {
      allowed[starts[i]:ends[i]] <- TRUE
    }
  }

  allowed
}

.gp_impute_locf <- function(x) {
  out <- x
  last <- NA_real_

  for (i in seq_along(out)) {
    if (is.na(out[i])) {
      out[i] <- last
    } else {
      last <- out[i]
    }
  }

  out
}

.gp_impute_nocb <- function(x) {
  rev(.gp_impute_locf(rev(x)))
}

.gp_impute_vector <- function(x,
                              time = NULL,
                              method = c("linear", "locf", "nocb", "nearest", "constant"),
                              max_gap = Inf,
                              fill_edges = TRUE,
                              constant_value = 0,
                              treat_infinite_as_missing = TRUE) {
  method <- match.arg(method)

  original <- x

  if (!is.numeric(x)) {
    x <- suppressWarnings(as.numeric(x))
  }

  if (is.null(time)) {
    time <- seq_along(x)
  } else {
    time <- suppressWarnings(as.numeric(time))
    if (length(time) != length(x) || any(!is.finite(time))) {
      time <- seq_along(x)
    }
  }

  miss <- is.na(x)

  if (isTRUE(treat_infinite_as_missing)) {
    miss <- miss | !is.finite(x)
  }

  x[miss] <- NA_real_

  allowed <- .gp_impute_find_allowed(miss, max_gap = max_gap)
  disallowed <- miss & !allowed

  if (!any(allowed)) {
    return(list(values = x, imputed = rep(FALSE, length(x))))
  }

  observed <- !is.na(x)

  if (!any(observed)) {
    if (method == "constant") {
      out <- x
      out[allowed] <- constant_value
      return(list(values = out, imputed = allowed))
    }

    warning("Cannot impute a signal with no observed values.", call. = FALSE)
    return(list(values = x, imputed = rep(FALSE, length(x))))
  }

  if (method == "constant") {
    out <- x
    out[allowed] <- constant_value
  } else if (method == "linear") {
    if (sum(observed) == 1L) {
      out <- x
      out[allowed] <- x[observed][1L]
    } else {
      rule <- if (isTRUE(fill_edges)) 2 else 1
      fitted <- stats::approx(
        x = time[observed],
        y = x[observed],
        xout = time,
        rule = rule,
        ties = "ordered"
      )$y

      out <- x
      out[allowed] <- fitted[allowed]
    }
  } else if (method == "locf") {
    fitted <- .gp_impute_locf(x)

    if (isTRUE(fill_edges)) {
      fitted <- .gp_impute_nocb(fitted)
    }

    out <- x
    out[allowed] <- fitted[allowed]
  } else if (method == "nocb") {
    fitted <- .gp_impute_nocb(x)

    if (isTRUE(fill_edges)) {
      fitted <- .gp_impute_locf(fitted)
    }

    out <- x
    out[allowed] <- fitted[allowed]
  } else {
    f1 <- .gp_impute_locf(x)
    f2 <- .gp_impute_nocb(x)

    out <- x

    for (i in which(allowed)) {
      left <- max(which(!is.na(x) & seq_along(x) < i), na.rm = TRUE)
      right <- min(which(!is.na(x) & seq_along(x) > i), na.rm = TRUE)

      if (!is.finite(left)) left <- NA_integer_
      if (!is.finite(right)) right <- NA_integer_

      if (is.na(left) && is.na(right)) {
        out[i] <- NA_real_
      } else if (is.na(left)) {
        out[i] <- x[right]
      } else if (is.na(right)) {
        out[i] <- x[left]
      } else {
        out[i] <- if (abs(time[i] - time[left]) <= abs(time[right] - time[i])) x[left] else x[right]
      }
    }
  }

  out[disallowed] <- NA_real_

  list(values = out, imputed = allowed & is.na(original))
}

.gp_impute_group_indices <- function(data, group_cols = NULL) {
  if (is.null(group_cols) || !length(group_cols)) {
    return(list(all = seq_len(nrow(data))))
  }

  missing <- setdiff(group_cols, names(data))

  if (length(missing)) {
    stop("Missing grouping columns: ", paste(missing, collapse = ", "), call. = FALSE)
  }

  split(seq_len(nrow(data)), interaction(data[group_cols], drop = TRUE, sep = " | "))
}

#' Import Gazepoint export files from a session folder
#'
#' Loads Gazepoint-style CSV exports from a folder into a named list of data
#' frames. The function is intended as a single entry point for common session
#' folders that contain all-gaze, fixation, summary, biometric, marker, or
#' related exports.
#'
#' @param dir Folder containing Gazepoint export files.
#' @param session Optional session or participant prefix used to select files.
#'   Can be a character vector.
#' @param pattern File pattern. Defaults to CSV files.
#' @param recursive If TRUE, search subfolders.
#' @param session_match How `session` should be matched: `"prefix"`,
#'   `"contains"`, or `"regex"`.
#' @param file_encoding Encoding passed to `read.table()`.
#' @param add_file_info If TRUE, add source-file columns to each imported data
#'   frame.
#'
#' @return A named list of data frames with class `gazepoint_session_data`.
#'   File metadata are stored in the `file_index` attribute.
#' @export
#'
#' @examples
#' \dontrun{
#' session_data <- import_gazepoint_data("path/to/session", session = "P01")
#' names(session_data)
#' attr(session_data, "file_index")
#' }
import_gazepoint_data <- function(dir,
                                  session = NULL,
                                  pattern = "\\.csv$",
                                  recursive = FALSE,
                                  session_match = c("prefix", "contains", "regex"),
                                  file_encoding = "UTF-8-BOM",
                                  add_file_info = TRUE) {
  session_match <- match.arg(session_match)

  if (missing(dir) || !nzchar(dir)) {
    stop("Supply `dir`, the folder containing Gazepoint export files.", call. = FALSE)
  }

  if (!dir.exists(dir)) {
    stop("Folder does not exist: ", dir, call. = FALSE)
  }

  files <- list.files(
    path = dir,
    pattern = pattern,
    full.names = TRUE,
    recursive = recursive,
    ignore.case = TRUE
  )

  files <- files[file.exists(files)]

  if (!length(files)) {
    stop("No files matching `pattern` were found in: ", dir, call. = FALSE)
  }

  keep <- .gp_io_session_keep(
    files = files,
    session = session,
    session_match = session_match
  )

  files <- files[keep]

  if (!length(files)) {
    stop("No files matched `session` in: ", dir, call. = FALSE)
  }

  names_out <- vapply(files, .gp_io_safe_name, character(1), session = session)
  names_out <- make.unique(names_out, sep = "_")

  out <- vector("list", length(files))
  file_index <- data.frame(
    element = names_out,
    file = .gp_io_clean_path(files),
    basename = basename(files),
    detected_type = vapply(files, .gp_io_detect_type, character(1)),
    rows = NA_integer_,
    columns = NA_integer_,
    stringsAsFactors = FALSE
  )

  for (i in seq_along(files)) {
    dat <- .gp_io_read_csv(files[i], file_encoding = file_encoding)

    if (isTRUE(add_file_info)) {
      dat$gp_source_file <- .gp_io_clean_path(files[i])
      dat$gp_source_basename <- basename(files[i])
      dat$gp_source_index <- i
    }

    out[[i]] <- dat
    file_index$rows[i] <- nrow(dat)
    file_index$columns[i] <- ncol(dat)
  }

  names(out) <- names_out

  attr(out, "dir") <- .gp_io_clean_path(dir)
  attr(out, "session") <- session
  attr(out, "file_index") <- file_index

  class(out) <- c("gazepoint_session_data", "list")

  out
}

#' Impute missing values in Gazepoint signals
#'
#' Interpolates missing values in numeric Gazepoint time series, such as pupil,
#' GSR/EDA, PPG/BVP, heart-rate, IBI/RRI, or other continuous channels. The
#' function can work on a numeric vector, a time-series object, or selected
#' numeric columns of a data frame.
#'
#' @param data Numeric vector, time-series object, or data frame.
#' @param method Imputation method: `"linear"`, `"locf"`, `"nocb"`,
#'   `"nearest"`, or `"constant"`.
#' @param cols Columns to impute when `data` is a data frame. If NULL, all
#'   numeric columns except time and grouping columns are used.
#' @param time_col Optional time column for interpolation.
#' @param group_cols Optional grouping columns. Imputation is performed within
#'   groups.
#' @param max_gap Maximum missing-gap length, in samples, to impute. Longer
#'   gaps remain missing. Defaults to `Inf`.
#' @param fill_edges If TRUE, leading and trailing gaps are filled using the
#'   nearest observed value for methods that support it.
#' @param constant_value Value used when `method = "constant"`.
#' @param add_flags If TRUE and `data` is a data frame, add logical
#'   `<column>_was_imputed` columns.
#' @param treat_infinite_as_missing If TRUE, infinite values are treated as
#'   missing before imputation.
#'
#' @return Object of the same basic type as `data`. Data-frame outputs include
#'   an `imputation_summary` attribute.
#' @export
#'
#' @examples
#' x <- c(1, NA, 3, 4)
#' impute_gazepoint_missing(x)
#'
#' dat <- data.frame(time_s = 1:5, GSR = c(1, NA, 3, NA, 5))
#' impute_gazepoint_missing(dat, cols = "GSR", time_col = "time_s")
impute_gazepoint_missing <- function(data,
                                     method = c("linear", "locf", "nocb", "nearest", "constant"),
                                     cols = NULL,
                                     time_col = NULL,
                                     group_cols = NULL,
                                     max_gap = Inf,
                                     fill_edges = TRUE,
                                     constant_value = 0,
                                     add_flags = TRUE,
                                     treat_infinite_as_missing = TRUE) {
  method <- match.arg(method)

  if (!is.finite(max_gap) && !is.infinite(max_gap)) {
    stop("`max_gap` must be a non-negative number or Inf.", call. = FALSE)
  }

  if (max_gap < 0) {
    stop("`max_gap` must be non-negative.", call. = FALSE)
  }

  max_gap <- if (is.infinite(max_gap)) {
    Inf
  } else {
    as.integer(max_gap)
  }

  if (stats::is.ts(data)) {
    tsp_data <- stats::tsp(data)
    res <- .gp_impute_vector(
      x = as.numeric(data),
      method = method,
      max_gap = max_gap,
      fill_edges = fill_edges,
      constant_value = constant_value,
      treat_infinite_as_missing = treat_infinite_as_missing
    )

    return(stats::ts(res$values, start = tsp_data[1L], end = tsp_data[2L], frequency = tsp_data[3L]))
  }

  if (is.numeric(data) && is.null(dim(data))) {
    res <- .gp_impute_vector(
      x = data,
      method = method,
      max_gap = max_gap,
      fill_edges = fill_edges,
      constant_value = constant_value,
      treat_infinite_as_missing = treat_infinite_as_missing
    )

    return(res$values)
  }

  if (!is.data.frame(data)) {
    stop("`data` must be a numeric vector, ts object, or data frame.", call. = FALSE)
  }

  out <- data

  if (!is.null(time_col) && !time_col %in% names(out)) {
    stop("`time_col` not found in `data`.", call. = FALSE)
  }

  if (is.null(cols)) {
    numeric_cols <- names(out)[vapply(out, is.numeric, logical(1))]
    cols <- setdiff(numeric_cols, c(time_col, group_cols))
  }

  if (!length(cols)) {
    stop("No columns selected for imputation.", call. = FALSE)
  }

  missing_cols <- setdiff(cols, names(out))

  if (length(missing_cols)) {
    stop("Missing columns: ", paste(missing_cols, collapse = ", "), call. = FALSE)
  }

  non_numeric <- cols[!vapply(out[cols], is.numeric, logical(1))]

  if (length(non_numeric)) {
    stop("Selected columns must be numeric: ", paste(non_numeric, collapse = ", "), call. = FALSE)
  }

  groups <- .gp_impute_group_indices(out, group_cols = group_cols)

  summaries <- list()

  for (cc in cols) {
    flag <- rep(FALSE, nrow(out))
    before <- sum(is.na(out[[cc]]) | if (isTRUE(treat_infinite_as_missing)) !is.finite(out[[cc]]) else FALSE)

    for (g in groups) {
      tt <- if (!is.null(time_col)) out[[time_col]][g] else NULL

      res <- .gp_impute_vector(
        x = out[[cc]][g],
        time = tt,
        method = method,
        max_gap = max_gap,
        fill_edges = fill_edges,
        constant_value = constant_value,
        treat_infinite_as_missing = treat_infinite_as_missing
      )

      out[[cc]][g] <- res$values
      flag[g] <- res$imputed
    }

    after <- sum(is.na(out[[cc]]) | if (isTRUE(treat_infinite_as_missing)) !is.finite(out[[cc]]) else FALSE)

    if (isTRUE(add_flags)) {
      out[[paste0(cc, "_was_imputed")]] <- flag
    }

    summaries[[cc]] <- data.frame(
      column = cc,
      n_missing_before = before,
      n_imputed = sum(flag, na.rm = TRUE),
      n_missing_after = after,
      method = method,
      max_gap = if (is.infinite(max_gap)) Inf else max_gap,
      stringsAsFactors = FALSE
    )
  }

  summary <- do.call(rbind, summaries)
  row.names(summary) <- NULL

  attr(out, "imputation_summary") <- summary

  out
}

