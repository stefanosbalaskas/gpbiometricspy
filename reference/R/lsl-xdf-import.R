#' Import Gazepoint-related streams from an LSL/XDF file
#'
#' Reads an XDF file through the optional Python `pyxdf` package via
#' `reticulate`. This supports high-end LSL workflows without making Python a
#' hard dependency of gpbiometrics.
#'
#' @param path Path to an `.xdf` file.
#' @param stream_name_pattern Regular expression used to identify Gazepoint-like
#'   streams when `include_all_streams = FALSE`.
#' @param include_all_streams Logical. If `TRUE`, return all streams.
#' @param flatten Logical. If `TRUE`, convert streams to data frames where
#'   possible.
#' @param pyxdf_module Python module name, usually `"pyxdf"`.
#'
#' @return A list with `overview`, `streams`, `header`, and `settings`.
#' @export
import_gazepoint_lsl_xdf <- function(path,
                                     stream_name_pattern = "Gazepoint|GP3|GSR|EDA|Biometric|TTL|Pupil|Gaze",
                                     include_all_streams = FALSE,
                                     flatten = TRUE,
                                     pyxdf_module = "pyxdf") {
  if (!is.character(path) || length(path) != 1) {
    stop("`path` must be a single file path.", call. = FALSE)
  }

  if (!file.exists(path)) {
    stop("File does not exist: ", path, call. = FALSE)
  }

  if (!requireNamespace("reticulate", quietly = TRUE)) {
    stop(
      "The optional package `reticulate` is required for XDF import. Install it with install.packages('reticulate').",
      call. = FALSE
    )
  }

  pyxdf <- tryCatch(
    reticulate::import(pyxdf_module, delay_load = FALSE),
    error = function(e) {
      stop(
        "Python module `", pyxdf_module, "` could not be imported. ",
        "Install it in your active Python environment with: pip install pyxdf",
        call. = FALSE
      )
    }
  )

  loaded <- pyxdf$load_xdf(path)
  streams_raw <- reticulate::py_to_r(loaded[[1]])
  header <- reticulate::py_to_r(loaded[[2]])

  stream_meta <- lapply(seq_along(streams_raw), function(i) {
    gpbiometrics_xdf_stream_meta(streams_raw[[i]], i)
  })

  meta_df <- do.call(rbind, stream_meta)

  selected <- rep(TRUE, nrow(meta_df))

  if (!isTRUE(include_all_streams)) {
    selected <- grepl(stream_name_pattern, meta_df$name, ignore.case = TRUE) |
      grepl(stream_name_pattern, meta_df$type, ignore.case = TRUE)
  }

  selected_indices <- which(selected)

  streams <- lapply(selected_indices, function(i) {
    stream <- streams_raw[[i]]
    meta <- gpbiometrics_xdf_stream_meta(stream, i)

    if (isTRUE(flatten)) {
      data <- gpbiometrics_xdf_stream_to_data_frame(stream)
    } else {
      data <- stream
    }

    list(
      meta = meta,
      data = data
    )
  })

  names(streams) <- paste0("stream_", selected_indices)

  overview <- data.frame(
    path = normalizePath(path, winslash = "/", mustWork = FALSE),
    total_streams = length(streams_raw),
    selected_streams = length(streams),
    include_all_streams = include_all_streams,
    stream_name_pattern = stream_name_pattern,
    status = if (length(streams) > 0) "xdf_import_complete" else "xdf_import_no_matching_streams",
    interpretation = paste(
      "XDF import returns synchronized LSL stream contents and metadata.",
      "Downstream alignment and resampling remain design-specific and should be verified before analysis."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      stream_overview = meta_df,
      streams = streams,
      header = header,
      settings = list(
        path = path,
        stream_name_pattern = stream_name_pattern,
        include_all_streams = include_all_streams,
        flatten = flatten,
        pyxdf_module = pyxdf_module
      )
    ),
    class = c("gazepoint_lsl_xdf_import", "list")
  )
}

gpbiometrics_xdf_stream_meta <- function(stream, index) {
  info <- stream$info

  data.frame(
    stream_index = index,
    name = gpbiometrics_xdf_scalar(info$name, paste0("stream_", index)),
    type = gpbiometrics_xdf_scalar(info$type, NA_character_),
    channel_count = suppressWarnings(as.integer(gpbiometrics_xdf_scalar(info$channel_count, NA_character_))),
    nominal_srate = suppressWarnings(as.numeric(gpbiometrics_xdf_scalar(info$nominal_srate, NA_character_))),
    stringsAsFactors = FALSE
  )
}

gpbiometrics_xdf_scalar <- function(x, default = NA_character_) {
  if (is.null(x)) {
    return(default)
  }

  if (is.list(x) && length(x) > 0) {
    return(as.character(x[[1]]))
  }

  if (length(x) > 0) {
    return(as.character(x[1]))
  }

  default
}

gpbiometrics_xdf_stream_to_data_frame <- function(stream) {
  ts <- stream$time_series
  stamps <- as.numeric(stream$time_stamps)

  if (is.null(ts)) {
    return(data.frame(time_stamp = stamps))
  }

  if (is.matrix(ts) || is.data.frame(ts)) {
    out <- as.data.frame(ts, stringsAsFactors = FALSE)
    names(out) <- paste0("channel_", seq_len(ncol(out)))
    out <- cbind(time_stamp = stamps, out)
    return(out)
  }

  if (is.vector(ts) && !is.list(ts)) {
    return(data.frame(time_stamp = stamps, value = ts, stringsAsFactors = FALSE))
  }

  if (is.list(ts)) {
    values <- vapply(ts, function(x) paste(as.character(x), collapse = " | "), character(1))
    return(data.frame(time_stamp = stamps, value = values, stringsAsFactors = FALSE))
  }

  data.frame(time_stamp = stamps, stringsAsFactors = FALSE)
}
