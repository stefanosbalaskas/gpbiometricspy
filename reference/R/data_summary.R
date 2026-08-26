#' Import a Gazepoint Data Summary export
#'
#' Reads a multi-section `Data_Summary_export_*.csv` file produced by Gazepoint
#' Analysis. These files are not ordinary rectangular CSV files. They contain
#' metadata followed by sections such as `AOI Summary` and `AOI Statistics (for
#' each user)`. The latter may include AOI-level biometric summaries such as
#' average dial value, average GSR, average heart rate, average interbeat
#' interval, and pupil diameter.
#'
#' @param file Path to a Gazepoint `Data_Summary_export_*.csv` file.
#'
#' @return A list with `metadata`, `aoi_summary`, and `aoi_statistics` data
#'   frames. The returned object has class `"gazepoint_data_summary"`.
#'
#' @export
import_gazepoint_data_summary <- function(file) {
  if (missing(file) || length(file) != 1L || !nzchar(file)) {
    stop("`file` must be a single non-empty file path.", call. = FALSE)
  }

  if (!file.exists(file)) {
    stop("File does not exist: ", file, call. = FALSE)
  }

  lines <- readLines(file, warn = FALSE, encoding = "UTF-8")

  metadata <- parse_gazepoint_data_summary_metadata(lines, file)

  aoi_summary <- parse_gazepoint_data_summary_section(
    lines = lines,
    section_pattern = "^AOI Summary$",
    source_file = basename(file)
  )

  aoi_statistics <- parse_gazepoint_data_summary_section(
    lines = lines,
    section_pattern = "^AOI Statistics",
    source_file = basename(file)
  )

  out <- list(
    metadata = metadata,
    aoi_summary = aoi_summary,
    aoi_statistics = aoi_statistics
  )

  class(out) <- c("gazepoint_data_summary", "list")
  out
}


parse_gazepoint_data_summary_metadata <- function(lines, file) {
  first_line <- split_first_csv_line(lines[1])
  second_line <- if (length(lines) >= 2L) split_first_csv_line(lines[2]) else c(NA, NA)

  notes <- lines[grepl("^Note:", trimws(lines), ignore.case = TRUE)]
  notes <- trimws(notes)

  data.frame(
    source_file = basename(file),
    software = first_line[1],
    version = first_line[2],
    processed_label = second_line[1],
    processed_on = second_line[2],
    notes = paste(notes, collapse = " | "),
    stringsAsFactors = FALSE
  )
}


parse_gazepoint_data_summary_section <- function(lines,
                                                 section_pattern,
                                                 source_file) {
  trimmed <- trimws(lines)

  section_idx <- grep(section_pattern, trimmed, ignore.case = TRUE)

  if (length(section_idx) == 0L) {
    return(data.frame(source_file = character(0), stringsAsFactors = FALSE))
  }

  section_idx <- section_idx[1]

  header_idx <- next_nonempty_line(trimmed, section_idx + 1L)

  if (is.na(header_idx)) {
    return(data.frame(source_file = character(0), stringsAsFactors = FALSE))
  }

  data_start <- header_idx + 1L
  data_end <- data_start - 1L

  if (data_start <= length(lines)) {
    for (i in data_start:length(lines)) {
      if (!nzchar(trimmed[i])) {
        break
      }

      data_end <- i
    }
  }

  section_lines <- lines[header_idx:data_end]

  if (length(section_lines) == 1L) {
    header <- parse_csv_text(section_lines)
    out <- header[0, , drop = FALSE]
  } else {
    out <- parse_csv_text(section_lines)
  }

  out <- drop_empty_trailing_columns(out)
  out <- convert_numeric_like_columns(out)

  out$source_file <- source_file

  out
}


next_nonempty_line <- function(trimmed_lines, start) {
  if (start > length(trimmed_lines)) {
    return(NA_integer_)
  }

  for (i in start:length(trimmed_lines)) {
    if (nzchar(trimmed_lines[i])) {
      return(i)
    }
  }

  NA_integer_
}


parse_csv_text <- function(lines) {
  text <- paste(lines, collapse = "\n")

  utils::read.csv(
    text = text,
    stringsAsFactors = FALSE,
    check.names = FALSE,
    na.strings = c("", "NA", "NaN")
  )
}


split_first_csv_line <- function(line) {
  if (length(line) == 0L || is.na(line)) {
    return(c(NA_character_, NA_character_))
  }

  parts <- strsplit(line, ",", fixed = TRUE)[[1]]

  if (length(parts) == 1L) {
    return(c(trimws(parts[1]), NA_character_))
  }

  c(trimws(parts[1]), trimws(paste(parts[-1], collapse = ",")))
}


convert_numeric_like_columns <- function(data) {
  if (!is.data.frame(data) || ncol(data) == 0L) {
    return(data)
  }

  for (nm in names(data)) {
    x <- data[[nm]]

    if (!is.character(x)) {
      next
    }

    x_trim <- trimws(x)

    non_missing <- x_trim[!is.na(x_trim) & nzchar(x_trim)]

    if (length(non_missing) == 0L) {
      next
    }

    numeric_x <- suppressWarnings(as.numeric(x_trim))
    numeric_non_missing <- numeric_x[!is.na(x_trim) & nzchar(x_trim)]

    if (all(!is.na(numeric_non_missing))) {
      data[[nm]] <- numeric_x
    }
  }

  data
}
