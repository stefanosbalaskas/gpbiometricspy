#' Write Gazepoint Biometrics report tables
#'
#' Writes report-ready Gazepoint Biometrics tables to CSV files. The input can
#' be a workflow object produced by `run_gazepoint_biometrics_workflow()`, a
#' report-table object produced by `create_gazepoint_biometrics_report_tables()`,
#' or a named list of data frames.
#'
#' @param tables A Gazepoint Biometrics workflow object, report-table object, or
#'   named list of data frames.
#' @param output_dir Output directory for CSV files.
#' @param prefix Filename prefix.
#' @param overwrite Should existing files be overwritten?
#' @param include_empty_message_tables Should placeholder tables containing only
#'   a `message` column be written?
#'
#' @return A data frame indexing written and skipped files.
#'
#' @export
write_gazepoint_biometrics_report_tables <- function(tables,
                                                     output_dir,
                                                     prefix = "gazepoint_biometrics",
                                                     overwrite = TRUE,
                                                     include_empty_message_tables = FALSE) {
  if (missing(output_dir) || is.null(output_dir) || length(output_dir) != 1L) {
    stop("`output_dir` must be supplied as a single folder path.", call. = FALSE)
  }

  if (inherits(tables, "gazepoint_biometrics_workflow")) {
    tables <- create_gazepoint_biometrics_report_tables(workflow = tables)
  }

  if (is.data.frame(tables) || !is.list(tables)) {
    stop(
      "`tables` must be a workflow object, a report-table object, or a named list of data frames.",
      call. = FALSE
    )
  }

  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  }

  if (!dir.exists(output_dir)) {
    stop("Could not create `output_dir`: ", output_dir, call. = FALSE)
  }

  table_names <- names(tables)

  if (is.null(table_names)) {
    table_names <- paste0("table_", seq_along(tables))
  }

  table_names[table_names == ""] <- paste0("table_", which(table_names == ""))

  index_rows <- lapply(seq_along(tables), function(i) {
    table_name <- table_names[i]
    table <- tables[[i]]

    file_name <- paste0(
      safe_filename_component(prefix),
      "_",
      safe_filename_component(table_name),
      ".csv"
    )

    file_path <- file.path(output_dir, file_name)

    if (!is.data.frame(table)) {
      return(data.frame(
        table = table_name,
        file = file_path,
        n_rows = NA_integer_,
        n_columns = NA_integer_,
        written = FALSE,
        skipped_reason = "not_a_data_frame",
        stringsAsFactors = FALSE
      ))
    }

    is_message_only <- identical(names(table), "message")

    if (is_message_only && !isTRUE(include_empty_message_tables)) {
      return(data.frame(
        table = table_name,
        file = file_path,
        n_rows = nrow(table),
        n_columns = ncol(table),
        written = FALSE,
        skipped_reason = "message_only_table",
        stringsAsFactors = FALSE
      ))
    }

    if (file.exists(file_path) && !isTRUE(overwrite)) {
      return(data.frame(
        table = table_name,
        file = file_path,
        n_rows = nrow(table),
        n_columns = ncol(table),
        written = FALSE,
        skipped_reason = "file_exists",
        stringsAsFactors = FALSE
      ))
    }

    utils::write.csv(
      table,
      file = file_path,
      row.names = FALSE,
      na = ""
    )

    data.frame(
      table = table_name,
      file = file_path,
      n_rows = nrow(table),
      n_columns = ncol(table),
      written = TRUE,
      skipped_reason = NA_character_,
      stringsAsFactors = FALSE
    )
  })

  out <- do.call(rbind, index_rows)
  rownames(out) <- NULL
  out
}


safe_filename_component <- function(x) {
  x <- as.character(x)
  x <- gsub("[^A-Za-z0-9_\\-]+", "_", x)
  x <- gsub("_+", "_", x)
  x <- gsub("^_|_$", "", x)

  ifelse(nchar(x) == 0L, "table", x)
}
