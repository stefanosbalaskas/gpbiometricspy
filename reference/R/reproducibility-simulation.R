#' Inject simple synthetic artifacts into signal columns
#'
#' Adds transparent, rule-based synthetic artifacts to selected numeric signal
#' columns. The function is intended for testing QC pipelines and does not
#' interpret the physiological meaning of any signal.
#'
#' @param data A data frame.
#' @param signal_cols Character vector of numeric signal columns.
#' @param artifact Character vector of artifact types. Supported values are
#'   \code{"missing_run"}, \code{"flatline"}, \code{"spike"}, \code{"noise"},
#'   and \code{"drift"}.
#' @param n_artifacts Number of artifacts of each requested type to add per
#'   signal column.
#' @param artifact_length Number of rows affected by each inserted artifact.
#' @param magnitude Optional numeric artifact magnitude. If \code{NULL}, a
#'   conservative value is derived from the signal standard deviation.
#' @param seed Optional random seed for reproducible artifact placement.
#' @param suffix Suffix used for new artifact-injected columns when
#'   \code{overwrite = FALSE}.
#' @param overwrite Logical. If \code{TRUE}, modify the original signal columns.
#'   If \code{FALSE}, create new columns.
#'
#' @return A list with class \code{gazepoint_artifact_simulation}, containing
#'   the modified data, an artifact log, and the parameters used.
#' @export
simulate_gazepoint_artifact <- function(data,
                                        signal_cols,
                                        artifact = c("missing_run", "flatline", "spike"),
                                        n_artifacts = 1,
                                        artifact_length = 5,
                                        magnitude = NULL,
                                        seed = NULL,
                                        suffix = "_artifact",
                                        overwrite = FALSE) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (nrow(data) == 0) {
    stop("`data` must contain at least one row.", call. = FALSE)
  }

  if (missing(signal_cols) || length(signal_cols) == 0) {
    stop("`signal_cols` must contain at least one column name.", call. = FALSE)
  }

  signal_cols <- as.character(signal_cols)
  missing_signal_cols <- setdiff(signal_cols, names(data))
  if (length(missing_signal_cols) > 0) {
    stop(
      "`signal_cols` contains columns not found in `data`: ",
      paste(missing_signal_cols, collapse = ", "),
      call. = FALSE
    )
  }

  non_numeric <- signal_cols[!vapply(data[signal_cols], is.numeric, logical(1))]
  if (length(non_numeric) > 0) {
    stop(
      "All `signal_cols` must be numeric. Non-numeric columns: ",
      paste(non_numeric, collapse = ", "),
      call. = FALSE
    )
  }

  artifact <- match.arg(
    artifact,
    choices = c("missing_run", "flatline", "spike", "noise", "drift"),
    several.ok = TRUE
  )

  if (!is.numeric(n_artifacts) || length(n_artifacts) != 1 ||
      is.na(n_artifacts) || n_artifacts < 0) {
    stop("`n_artifacts` must be a single non-negative number.", call. = FALSE)
  }

  if (!is.numeric(artifact_length) || length(artifact_length) != 1 ||
      is.na(artifact_length) || artifact_length < 1) {
    stop("`artifact_length` must be a single positive number.", call. = FALSE)
  }

  n_artifacts <- as.integer(n_artifacts)
  artifact_length <- as.integer(artifact_length)

  if (!is.null(magnitude) &&
      (!is.numeric(magnitude) || length(magnitude) != 1 || !is.finite(magnitude))) {
    stop("`magnitude` must be `NULL` or a single finite number.", call. = FALSE)
  }

  if (!is.character(suffix) || length(suffix) != 1 || is.na(suffix)) {
    stop("`suffix` must be a single character string.", call. = FALSE)
  }

  if (!is.logical(overwrite) || length(overwrite) != 1 || is.na(overwrite)) {
    stop("`overwrite` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.null(seed)) {
    old_seed_exists <- exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)
    old_seed <- if (old_seed_exists) get(".Random.seed", envir = .GlobalEnv) else NULL

    on.exit({
      if (old_seed_exists) {
        assign(".Random.seed", old_seed, envir = .GlobalEnv)
      }
    }, add = TRUE)

    set.seed(seed)
  }

  out <- data
  log_rows <- list()
  log_i <- 0L

  for (signal in signal_cols) {
    output_col <- if (overwrite) signal else paste0(signal, suffix)

    if (!overwrite && output_col %in% names(out)) {
      stop(
        "Output column already exists: ",
        output_col,
        ". Choose another `suffix` or set `overwrite = TRUE`.",
        call. = FALSE
      )
    }

    out[[output_col]] <- out[[signal]]

    for (artifact_type in artifact) {
      for (j in seq_len(n_artifacts)) {
        max_start <- max(1L, nrow(out) - artifact_length + 1L)
        start_row <- sample(seq_len(max_start), size = 1)
        end_row <- min(nrow(out), start_row + artifact_length - 1L)
        rows <- seq.int(start_row, end_row)

        original_values <- out[[output_col]][rows]
        finite_signal <- out[[output_col]][is.finite(out[[output_col]])]
        signal_scale <- stats::sd(finite_signal)

        if (!is.finite(signal_scale) || signal_scale == 0) {
          signal_scale <- 1
        }

        artifact_magnitude <- if (is.null(magnitude)) {
          5 * signal_scale
        } else {
          magnitude
        }

        if (artifact_type == "missing_run") {
          out[[output_col]][rows] <- NA_real_
        }

        if (artifact_type == "flatline") {
          flat_value <- original_values[is.finite(original_values)][1]

          if (!is.finite(flat_value)) {
            flat_value <- stats::median(finite_signal, na.rm = TRUE)
          }

          if (!is.finite(flat_value)) {
            flat_value <- 0
          }

          out[[output_col]][rows] <- flat_value
        }

        if (artifact_type == "spike") {
          signs <- sample(c(-1, 1), size = length(rows), replace = TRUE)
          out[[output_col]][rows] <- out[[output_col]][rows] + signs * artifact_magnitude
        }

        if (artifact_type == "noise") {
          out[[output_col]][rows] <- out[[output_col]][rows] +
            stats::rnorm(length(rows), mean = 0, sd = abs(artifact_magnitude))
        }

        if (artifact_type == "drift") {
          out[[output_col]][rows] <- out[[output_col]][rows] +
            seq(0, artifact_magnitude, length.out = length(rows))
        }

        log_i <- log_i + 1L
        log_rows[[log_i]] <- data.frame(
          signal = signal,
          output_col = output_col,
          artifact = artifact_type,
          artifact_index = j,
          start_row = start_row,
          end_row = end_row,
          n_samples_modified = length(rows),
          magnitude = artifact_magnitude,
          stringsAsFactors = FALSE
        )
      }
    }
  }

  artifact_log <- if (length(log_rows) == 0) {
    data.frame(
      signal = character(0),
      output_col = character(0),
      artifact = character(0),
      artifact_index = integer(0),
      start_row = integer(0),
      end_row = integer(0),
      n_samples_modified = integer(0),
      magnitude = numeric(0),
      stringsAsFactors = FALSE
    )
  } else {
    do.call(rbind, log_rows)
  }

  rownames(artifact_log) <- NULL

  result <- list(
    data = out,
    artifact_log = artifact_log,
    parameters = list(
      signal_cols = signal_cols,
      artifact = artifact,
      n_artifacts = n_artifacts,
      artifact_length = artifact_length,
      magnitude = magnitude,
      seed = seed,
      suffix = suffix,
      overwrite = overwrite
    )
  )

  class(result) <- c("gazepoint_artifact_simulation", "list")
  result
}

#' Generate a reproducibility manifest
#'
#' Creates a conservative analysis manifest containing package/session
#' information, input file metadata, output paths, user-supplied parameters, and
#' notes. The function is designed for auditability and does not inspect private
#' data contents.
#'
#' @param input_paths Optional character vector of input file or folder paths.
#' @param parameters Optional named list of analysis parameters.
#' @param outputs Optional character vector of output paths or object names.
#' @param notes Optional character vector of free-text notes.
#' @param write_path Optional path. Use \code{.rds} to save the manifest object;
#'   otherwise a plain-text manifest is written.
#' @param include_session_info Logical. If \code{TRUE}, include
#'   \code{utils::sessionInfo()}.
#'
#' @return A list with class \code{gazepoint_manifest}.
#' @export
generate_gazepoint_manifest <- function(input_paths = NULL,
                                        parameters = list(),
                                        outputs = NULL,
                                        notes = NULL,
                                        write_path = NULL,
                                        include_session_info = TRUE) {
  if (!is.null(input_paths) && !is.character(input_paths)) {
    stop("`input_paths` must be `NULL` or a character vector.", call. = FALSE)
  }

  if (!is.list(parameters)) {
    stop("`parameters` must be a list.", call. = FALSE)
  }

  if (!is.null(outputs) && !is.character(outputs)) {
    stop("`outputs` must be `NULL` or a character vector.", call. = FALSE)
  }

  if (!is.null(notes) && !is.character(notes)) {
    stop("`notes` must be `NULL` or a character vector.", call. = FALSE)
  }

  if (!is.null(write_path) &&
      (!is.character(write_path) || length(write_path) != 1 || is.na(write_path))) {
    stop("`write_path` must be `NULL` or a single file path.", call. = FALSE)
  }

  if (!is.logical(include_session_info) ||
      length(include_session_info) != 1 ||
      is.na(include_session_info)) {
    stop("`include_session_info` must be TRUE or FALSE.", call. = FALSE)
  }

  manifest <- list(
    created_at = format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"),
    package = "gpbiometrics",
    package_version = as.character(utils::packageVersion("gpbiometrics")),
    r_version = paste(R.version$major, R.version$minor, sep = "."),
    platform = R.version$platform,
    input_files = gazepoint_manifest_file_table(input_paths),
    outputs = outputs,
    parameters = parameters,
    notes = notes,
    session_info = if (include_session_info) utils::sessionInfo() else NULL
  )

  class(manifest) <- c("gazepoint_manifest", "list")

  if (!is.null(write_path)) {
    gazepoint_write_manifest(manifest, write_path)
  }

  manifest
}

gazepoint_manifest_file_table <- function(input_paths) {
  if (is.null(input_paths) || length(input_paths) == 0) {
    return(data.frame(
      path = character(0),
      exists = logical(0),
      is_directory = logical(0),
      size_bytes = numeric(0),
      modified_time = character(0),
      stringsAsFactors = FALSE
    ))
  }

  input_paths <- as.character(input_paths)

  info <- lapply(input_paths, function(path) {
    exists_path <- file.exists(path)
    file_info <- if (exists_path) file.info(path) else NULL

    data.frame(
      path = normalizePath(path, winslash = "/", mustWork = FALSE),
      exists = exists_path,
      is_directory = if (exists_path) isTRUE(file_info$isdir) else NA,
      size_bytes = if (exists_path) as.numeric(file_info$size) else NA_real_,
      modified_time = if (exists_path) as.character(file_info$mtime) else NA_character_,
      stringsAsFactors = FALSE
    )
  })

  out <- do.call(rbind, info)
  rownames(out) <- NULL
  out
}

gazepoint_write_manifest <- function(manifest, write_path) {
  ext <- tolower(tools::file_ext(write_path))

  if (identical(ext, "rds")) {
    saveRDS(manifest, write_path)
  } else {
    writeLines(gazepoint_manifest_text(manifest), write_path, useBytes = TRUE)
  }

  invisible(write_path)
}

gazepoint_manifest_text <- function(manifest) {
  parameter_names <- names(manifest$parameters)

  parameter_lines <- if (length(parameter_names) == 0) {
    "parameters: none supplied"
  } else {
    paste0(
      "parameter: ",
      parameter_names,
      " = ",
      vapply(manifest$parameters, function(x) {
        paste(utils::capture.output(utils::str(x, give.attr = FALSE)), collapse = " ")
      }, character(1))
    )
  }

  input_lines <- if (nrow(manifest$input_files) == 0) {
    "input: none supplied"
  } else {
    apply(manifest$input_files, 1, function(z) {
      paste0(
        "input: ",
        z[["path"]],
        " | exists=",
        z[["exists"]],
        " | directory=",
        z[["is_directory"]],
        " | size_bytes=",
        z[["size_bytes"]]
      )
    })
  }

  c(
    "Gazepoint analysis manifest",
    paste0("created_at: ", manifest$created_at),
    paste0("package: ", manifest$package),
    paste0("package_version: ", manifest$package_version),
    paste0("r_version: ", manifest$r_version),
    paste0("platform: ", manifest$platform),
    input_lines,
    parameter_lines,
    if (length(manifest$outputs) > 0) paste0("output: ", manifest$outputs) else "output: none supplied",
    if (length(manifest$notes) > 0) paste0("note: ", manifest$notes) else "note: none supplied"
  )
}

#' Create a simple Gazepoint data dictionary
#'
#' Creates a column-level dictionary from a data frame or from CSV file headers.
#' The output is intended for reporting and reproducibility documentation.
#'
#' @param data Optional data frame.
#' @param file_paths Optional character vector of CSV files to inspect when
#'   \code{data} is \code{NULL}.
#' @param units Optional named character vector or named list mapping columns to
#'   units.
#' @param descriptions Optional named character vector or named list mapping
#'   columns to descriptions.
#' @param required_cols Optional character vector of columns expected in the
#'   data.
#' @param write_path Optional output path. Use \code{.csv} for CSV; otherwise a
#'   simple Markdown table is written.
#'
#' @return A data frame with class \code{gazepoint_dictionary}.
#' @export
create_gazepoint_dictionary <- function(data = NULL,
                                        file_paths = NULL,
                                        units = NULL,
                                        descriptions = NULL,
                                        required_cols = NULL,
                                        write_path = NULL) {
  if (!is.null(data) && !is.data.frame(data)) {
    stop("`data` must be `NULL` or a data frame.", call. = FALSE)
  }

  if (!is.null(file_paths) && !is.character(file_paths)) {
    stop("`file_paths` must be `NULL` or a character vector.", call. = FALSE)
  }

  if (is.null(data) && is.null(file_paths)) {
    stop("Supply either `data` or `file_paths`.", call. = FALSE)
  }

  if (!is.null(required_cols) && !is.character(required_cols)) {
    stop("`required_cols` must be `NULL` or a character vector.", call. = FALSE)
  }

  if (!is.null(write_path) &&
      (!is.character(write_path) || length(write_path) != 1 || is.na(write_path))) {
    stop("`write_path` must be `NULL` or a single file path.", call. = FALSE)
  }

  dictionary <- if (!is.null(data)) {
    gazepoint_dictionary_from_data(
      data = data,
      units = units,
      descriptions = descriptions,
      required_cols = required_cols
    )
  } else {
    gazepoint_dictionary_from_files(
      file_paths = file_paths,
      units = units,
      descriptions = descriptions,
      required_cols = required_cols
    )
  }

  class(dictionary) <- c("gazepoint_dictionary", "data.frame")

  if (!is.null(write_path)) {
    gazepoint_write_dictionary(dictionary, write_path)
  }

  dictionary
}

gazepoint_dictionary_from_data <- function(data, units, descriptions, required_cols) {
  cols <- names(data)

  out <- data.frame(
    source = "data",
    column = cols,
    present = TRUE,
    required = cols %in% required_cols,
    type = vapply(data, function(x) paste(class(x), collapse = "/"), character(1)),
    n_rows = nrow(data),
    n_missing = vapply(data, function(x) sum(is.na(x)), integer(1)),
    prop_missing = vapply(data, function(x) {
      if (length(x) == 0) NA_real_ else mean(is.na(x))
    }, numeric(1)),
    n_unique = vapply(data, function(x) length(unique(x)), integer(1)),
    unit = gazepoint_named_lookup(cols, units),
    description = gazepoint_named_lookup(cols, descriptions),
    stringsAsFactors = FALSE
  )

  gazepoint_append_missing_required(out, required_cols, units, descriptions)
}

gazepoint_dictionary_from_files <- function(file_paths, units, descriptions, required_cols) {
  rows <- lapply(file_paths, function(path) {
    if (!file.exists(path)) {
      return(data.frame(
        source = normalizePath(path, winslash = "/", mustWork = FALSE),
        column = NA_character_,
        present = FALSE,
        required = NA,
        type = NA_character_,
        n_rows = NA_integer_,
        n_missing = NA_integer_,
        prop_missing = NA_real_,
        n_unique = NA_integer_,
        unit = NA_character_,
        description = "File not found",
        stringsAsFactors = FALSE
      ))
    }

    header <- utils::read.csv(path, nrows = 0, check.names = FALSE)
    cols <- names(header)

    data.frame(
      source = normalizePath(path, winslash = "/", mustWork = FALSE),
      column = cols,
      present = TRUE,
      required = cols %in% required_cols,
      type = NA_character_,
      n_rows = NA_integer_,
      n_missing = NA_integer_,
      prop_missing = NA_real_,
      n_unique = NA_integer_,
      unit = gazepoint_named_lookup(cols, units),
      description = gazepoint_named_lookup(cols, descriptions),
      stringsAsFactors = FALSE
    )
  })

  out <- do.call(rbind, rows)
  rownames(out) <- NULL
  gazepoint_append_missing_required(out, required_cols, units, descriptions)
}

gazepoint_named_lookup <- function(cols, values) {
  if (is.null(values)) {
    return(rep(NA_character_, length(cols)))
  }

  if (is.list(values)) {
    values <- unlist(values, use.names = TRUE)
  }

  if (is.null(names(values))) {
    stop("Named lookup values must have names.", call. = FALSE)
  }

  out <- rep(NA_character_, length(cols))
  matched <- cols %in% names(values)
  out[matched] <- as.character(values[cols[matched]])
  out
}

gazepoint_append_missing_required <- function(dictionary, required_cols, units, descriptions) {
  if (is.null(required_cols) || length(required_cols) == 0) {
    return(dictionary)
  }

  missing_required <- setdiff(required_cols, dictionary$column)

  if (length(missing_required) == 0) {
    return(dictionary)
  }

  missing_rows <- data.frame(
    source = "required_cols",
    column = missing_required,
    present = FALSE,
    required = TRUE,
    type = NA_character_,
    n_rows = NA_integer_,
    n_missing = NA_integer_,
    prop_missing = NA_real_,
    n_unique = NA_integer_,
    unit = gazepoint_named_lookup(missing_required, units),
    description = gazepoint_named_lookup(missing_required, descriptions),
    stringsAsFactors = FALSE
  )

  out <- rbind(dictionary, missing_rows)
  rownames(out) <- NULL
  out
}

gazepoint_write_dictionary <- function(dictionary, write_path) {
  ext <- tolower(tools::file_ext(write_path))

  if (identical(ext, "csv")) {
    utils::write.csv(dictionary, write_path, row.names = FALSE)
  } else {
    writeLines(gazepoint_dictionary_markdown(dictionary), write_path, useBytes = TRUE)
  }

  invisible(write_path)
}

gazepoint_dictionary_markdown <- function(dictionary) {
  cols <- c("column", "present", "required", "type", "unit", "description")
  cols <- cols[cols %in% names(dictionary)]
  table_data <- dictionary[cols]

  header <- paste0("| ", paste(cols, collapse = " | "), " |")
  divider <- paste0("| ", paste(rep("---", length(cols)), collapse = " | "), " |")

  rows <- apply(table_data, 1, function(z) {
    z <- ifelse(is.na(z), "", z)
    paste0("| ", paste(z, collapse = " | "), " |")
  })

  c(header, divider, rows)
}

#' Pseudonymize participant or record identifiers
#'
#' Replaces selected identifier columns with deterministic sequential codes.
#' This function supports de-identification workflows, but it does not by itself
#' guarantee anonymity or regulatory compliance.
#'
#' @param data A data frame.
#' @param id_cols Character vector of identifier columns to replace.
#' @param prefix Prefix used in generated codes.
#' @param width Numeric width used for zero-padded codes.
#' @param keep_mapping Logical. If \code{TRUE}, store the mapping table as an
#'   attribute named \code{"id_mapping"}.
#'
#' @return A data frame with class \code{gazepoint_anonymized_data}.
#' @export
anonymize_gazepoint_data <- function(data,
                                     id_cols,
                                     prefix = "P",
                                     width = 3,
                                     keep_mapping = TRUE) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (missing(id_cols) || length(id_cols) == 0) {
    stop("`id_cols` must contain at least one column name.", call. = FALSE)
  }

  id_cols <- as.character(id_cols)
  missing_id_cols <- setdiff(id_cols, names(data))
  if (length(missing_id_cols) > 0) {
    stop(
      "`id_cols` contains columns not found in `data`: ",
      paste(missing_id_cols, collapse = ", "),
      call. = FALSE
    )
  }

  if (!is.character(prefix) || length(prefix) != 1 || is.na(prefix)) {
    stop("`prefix` must be a single character string.", call. = FALSE)
  }

  if (!is.numeric(width) || length(width) != 1 || is.na(width) || width < 1) {
    stop("`width` must be a single positive number.", call. = FALSE)
  }

  if (!is.logical(keep_mapping) || length(keep_mapping) != 1 || is.na(keep_mapping)) {
    stop("`keep_mapping` must be TRUE or FALSE.", call. = FALSE)
  }

  width <- as.integer(width)
  out <- data
  mapping_rows <- list()
  k <- 0L

  for (id_col in id_cols) {
    original_values <- as.character(out[[id_col]])
    unique_values <- sort(unique(original_values[!is.na(original_values)]))
    codes <- sprintf(paste0("%s%0", width, "d"), prefix, seq_along(unique_values))
    map <- stats::setNames(codes, unique_values)

    replaced <- original_values
    matched <- !is.na(original_values) & original_values %in% names(map)
    replaced[matched] <- unname(map[original_values[matched]])
    replaced[is.na(original_values)] <- NA_character_

    out[[id_col]] <- replaced

    for (i in seq_along(unique_values)) {
      k <- k + 1L
      mapping_rows[[k]] <- data.frame(
        column = id_col,
        original_value = unique_values[i],
        anonymized_value = codes[i],
        stringsAsFactors = FALSE
      )
    }
  }

  mapping <- if (length(mapping_rows) == 0) {
    data.frame(
      column = character(0),
      original_value = character(0),
      anonymized_value = character(0),
      stringsAsFactors = FALSE
    )
  } else {
    do.call(rbind, mapping_rows)
  }

  rownames(mapping) <- NULL

  if (keep_mapping) {
    attr(out, "id_mapping") <- mapping
  }

  class(out) <- c("gazepoint_anonymized_data", class(out))
  out
}
