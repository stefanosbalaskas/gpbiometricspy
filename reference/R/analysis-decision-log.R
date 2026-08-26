utils::globalVariables(c(
  "stage", "decision", "object_type", "function_name", "n"
))

#' Create a Gazepoint analysis decision log
#'
#' Create an empty structured log for recording preprocessing choices,
#' exclusions, missing channels, quality-control decisions, modelling settings,
#' cluster-permutation settings, and reviewer-facing notes.
#'
#' @param study_id Optional study identifier.
#' @param analyst Optional analyst name or identifier.
#' @param description Optional free-text description of the analysis workflow.
#'
#' @return A data frame with class `"gazepoint_analysis_decision_log"`.
#'
#' @examples
#' log <- create_gazepoint_analysis_decision_log(
#'   study_id = "demo_study",
#'   analyst = "analyst"
#' )
#'
#' log <- add_gazepoint_decision(
#'   log,
#'   stage = "preprocessing",
#'   object_type = "signal",
#'   object_id = "GSR",
#'   decision = "baseline_corrected",
#'   reason = "Pre-event baseline window available",
#'   function_name = "baseline_correct_gazepoint_gsr",
#'   parameter = "baseline_window",
#'   value = "-1000_to_0_ms"
#' )
#'
#' summarise_gazepoint_decision_log(log)
#'
#' @export
create_gazepoint_analysis_decision_log <- function(study_id = NA_character_,
                                                   analyst = NA_character_,
                                                   description = NA_character_) {
  study_id <- .gp_adl_optional_scalar(study_id, "study_id")
  analyst <- .gp_adl_optional_scalar(analyst, "analyst")
  description <- .gp_adl_optional_scalar(description, "description")

  out <- .gp_adl_empty_log()

  attr(out, "study_id") <- study_id
  attr(out, "analyst") <- analyst
  attr(out, "description") <- description
  attr(out, "created_at") <- format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z")
  attr(out, "package_version") <- as.character(utils::packageVersion("gpbiometrics"))

  class(out) <- c("gazepoint_analysis_decision_log", "data.frame")
  out
}

#' Add a decision to a Gazepoint analysis decision log
#'
#' Add one structured record to a decision log created with
#' `create_gazepoint_analysis_decision_log()`.
#'
#' @param log A decision log created with
#'   `create_gazepoint_analysis_decision_log()`.
#' @param stage Workflow stage, for example `"import"`, `"quality_control"`,
#'   `"preprocessing"`, `"feature_extraction"`, `"modelling"`, `"reporting"`,
#'   or `"cluster_permutation"`.
#' @param object_type Type of object affected by the decision, for example
#'   `"file"`, `"participant"`, `"trial"`, `"signal"`, `"channel"`,
#'   `"event_window"`, `"model"`, or `"cluster_test"`.
#' @param object_id Identifier for the affected object.
#' @param decision Compact decision label.
#' @param reason Reason for the decision.
#' @param function_name Optional function associated with the decision.
#' @param parameter Optional parameter name.
#' @param value Optional parameter value. Non-scalar values are collapsed into
#'   a compact character string.
#' @param reviewer_note Optional reviewer-facing note.
#' @param timestamp Optional timestamp. Defaults to the current time.
#'
#' @return Updated decision log.
#'
#' @export
add_gazepoint_decision <- function(log,
                                   stage,
                                   object_type,
                                   object_id = NA_character_,
                                   decision,
                                   reason = NA_character_,
                                   function_name = NA_character_,
                                   parameter = NA_character_,
                                   value = NA_character_,
                                   reviewer_note = NA_character_,
                                   timestamp = Sys.time()) {
  if (!inherits(log, "gazepoint_analysis_decision_log")) {
    stop(
      "`log` must be created by `create_gazepoint_analysis_decision_log()`.",
      call. = FALSE
    )
  }

  stage <- .gp_adl_required_scalar(stage, "stage")
  object_type <- .gp_adl_required_scalar(object_type, "object_type")
  object_id <- .gp_adl_optional_scalar(object_id, "object_id")
  decision <- .gp_adl_required_scalar(decision, "decision")
  reason <- .gp_adl_optional_scalar(reason, "reason")
  function_name <- .gp_adl_optional_scalar(function_name, "function_name")
  parameter <- .gp_adl_optional_scalar(parameter, "parameter")
  value <- .gp_adl_value_to_string(value)
  reviewer_note <- .gp_adl_optional_scalar(reviewer_note, "reviewer_note")

  if (inherits(timestamp, "POSIXt")) {
    timestamp <- format(timestamp, "%Y-%m-%d %H:%M:%S %Z")
  } else {
    timestamp <- .gp_adl_required_scalar(timestamp, "timestamp")
  }

  next_id <- if (NROW(log) == 0L) {
    1L
  } else {
    max(log$decision_id, na.rm = TRUE) + 1L
  }

  row <- data.frame(
    decision_id = next_id,
    timestamp = timestamp,
    stage = stage,
    object_type = object_type,
    object_id = object_id,
    decision = decision,
    reason = reason,
    function_name = function_name,
    parameter = parameter,
    value = value,
    reviewer_note = reviewer_note,
    stringsAsFactors = FALSE
  )

  out <- rbind(as.data.frame(log), row)
  attr(out, "study_id") <- attr(log, "study_id", exact = TRUE)
  attr(out, "analyst") <- attr(log, "analyst", exact = TRUE)
  attr(out, "description") <- attr(log, "description", exact = TRUE)
  attr(out, "created_at") <- attr(log, "created_at", exact = TRUE)
  attr(out, "package_version") <- attr(log, "package_version", exact = TRUE)

  class(out) <- c("gazepoint_analysis_decision_log", "data.frame")
  out
}

#' Summarise a Gazepoint analysis decision log
#'
#' Summarise the number of recorded decisions by workflow stage, object type,
#' decision label, and function name.
#'
#' @param log A decision log created with
#'   `create_gazepoint_analysis_decision_log()`.
#'
#' @return A list with class `"gazepoint_analysis_decision_log_summary"`.
#'
#' @export
summarise_gazepoint_decision_log <- function(log) {
  if (!inherits(log, "gazepoint_analysis_decision_log")) {
    stop(
      "`log` must be created by `create_gazepoint_analysis_decision_log()`.",
      call. = FALSE
    )
  }

  total <- NROW(log)

  out <- list(
    overview = data.frame(
      study_id = .gp_adl_attr_or_na(log, "study_id"),
      analyst = .gp_adl_attr_or_na(log, "analyst"),
      description = .gp_adl_attr_or_na(log, "description"),
      created_at = .gp_adl_attr_or_na(log, "created_at"),
      package_version = .gp_adl_attr_or_na(log, "package_version"),
      n_decisions = total,
      stringsAsFactors = FALSE
    ),
    by_stage = .gp_adl_count(log, "stage"),
    by_object_type = .gp_adl_count(log, "object_type"),
    by_decision = .gp_adl_count(log, "decision"),
    by_function = .gp_adl_count(log, "function_name")
  )

  class(out) <- "gazepoint_analysis_decision_log_summary"
  out
}

#' Write a Gazepoint analysis decision log to disk
#'
#' Write a decision log to CSV, optionally with a compact text summary.
#'
#' @param log A decision log created with
#'   `create_gazepoint_analysis_decision_log()`.
#' @param path Output CSV file path.
#' @param summary_path Optional output path for a text summary. If `NULL`,
#'   only the CSV file is written.
#' @param overwrite Logical. If `FALSE`, existing files are not overwritten.
#'
#' @return A data frame listing written files.
#'
#' @export
write_gazepoint_decision_log <- function(log,
                                         path,
                                         summary_path = NULL,
                                         overwrite = FALSE) {
  if (!inherits(log, "gazepoint_analysis_decision_log")) {
    stop(
      "`log` must be created by `create_gazepoint_analysis_decision_log()`.",
      call. = FALSE
    )
  }

  if (!is.character(path) || length(path) != 1L || is.na(path) || !nzchar(path)) {
    stop("`path` must be a non-empty output file path.", call. = FALSE)
  }

  if (!is.null(summary_path) &&
      (!is.character(summary_path) || length(summary_path) != 1L ||
       is.na(summary_path) || !nzchar(summary_path))) {
    stop("`summary_path` must be NULL or a non-empty file path.", call. = FALSE)
  }

  files <- data.frame(
    component = "decision_log",
    file = path,
    stringsAsFactors = FALSE
  )

  if (!is.null(summary_path)) {
    files <- rbind(
      files,
      data.frame(
        component = "summary",
        file = summary_path,
        stringsAsFactors = FALSE
      )
    )
  }

  existing <- file.exists(files$file)

  if (any(existing) && !isTRUE(overwrite)) {
    stop(
      "Output file(s) already exist. Use `overwrite = TRUE` to replace them: ",
      paste(files$file[existing], collapse = "; "),
      call. = FALSE
    )
  }

  out_dir <- dirname(path)
  if (!dir.exists(out_dir)) {
    dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
  }

  if (!dir.exists(out_dir)) {
    stop("Could not create output folder: ", out_dir, call. = FALSE)
  }

  utils::write.csv(as.data.frame(log), path, row.names = FALSE)

  if (!is.null(summary_path)) {
    summary_dir <- dirname(summary_path)
    if (!dir.exists(summary_dir)) {
      dir.create(summary_dir, recursive = TRUE, showWarnings = FALSE)
    }

    if (!dir.exists(summary_dir)) {
      stop("Could not create output folder: ", summary_dir, call. = FALSE)
    }

    summary <- summarise_gazepoint_decision_log(log)

    txt <- c(
      "Gazepoint analysis decision log",
      "=================================",
      "",
      paste0("Study ID: ", summary$overview$study_id),
      paste0("Analyst: ", summary$overview$analyst),
      paste0("Description: ", summary$overview$description),
      paste0("Created at: ", summary$overview$created_at),
      paste0("Package version: ", summary$overview$package_version),
      paste0("Number of decisions: ", summary$overview$n_decisions),
      "",
      "Decisions by stage",
      "------------------",
      utils::capture.output(print(summary$by_stage, row.names = FALSE)),
      "",
      "Decisions by object type",
      "------------------------",
      utils::capture.output(print(summary$by_object_type, row.names = FALSE)),
      "",
      "Decisions by label",
      "------------------",
      utils::capture.output(print(summary$by_decision, row.names = FALSE))
    )

    writeLines(txt, summary_path, useBytes = TRUE)
  }

  files
}

#' @export
print.gazepoint_analysis_decision_log <- function(x, ...) {
  cat("Gazepoint analysis decision log\n")
  cat("-------------------------------\n")
  cat("Study ID: ", .gp_adl_attr_or_na(x, "study_id"), "\n", sep = "")
  cat("Analyst: ", .gp_adl_attr_or_na(x, "analyst"), "\n", sep = "")
  cat("Decisions: ", NROW(x), "\n", sep = "")

  if (NROW(x) > 0L) {
    print(as.data.frame(x), row.names = FALSE)
  }

  invisible(x)
}

#' @export
print.gazepoint_analysis_decision_log_summary <- function(x, ...) {
  cat("Gazepoint analysis decision log summary\n")
  cat("---------------------------------------\n")
  print(x$overview, row.names = FALSE)

  cat("\nBy stage\n")
  print(x$by_stage, row.names = FALSE)

  cat("\nBy object type\n")
  print(x$by_object_type, row.names = FALSE)

  cat("\nBy decision\n")
  print(x$by_decision, row.names = FALSE)

  invisible(x)
}

.gp_adl_empty_log <- function() {
  data.frame(
    decision_id = integer(0),
    timestamp = character(0),
    stage = character(0),
    object_type = character(0),
    object_id = character(0),
    decision = character(0),
    reason = character(0),
    function_name = character(0),
    parameter = character(0),
    value = character(0),
    reviewer_note = character(0),
    stringsAsFactors = FALSE
  )
}

.gp_adl_required_scalar <- function(x, name) {
  if (missing(x) || is.null(x) || length(x) != 1L || is.na(x) || !nzchar(as.character(x))) {
    stop("`", name, "` must be a non-empty scalar value.", call. = FALSE)
  }

  as.character(x)
}

.gp_adl_optional_scalar <- function(x, name) {
  if (is.null(x) || length(x) == 0L) {
    return(NA_character_)
  }

  if (length(x) != 1L) {
    stop("`", name, "` must be a scalar value.", call. = FALSE)
  }

  if (is.na(x)) {
    return(NA_character_)
  }

  as.character(x)
}

.gp_adl_value_to_string <- function(x) {
  if (is.null(x) || length(x) == 0L) {
    return(NA_character_)
  }

  if (length(x) == 1L) {
    if (is.na(x)) {
      return(NA_character_)
    }

    return(as.character(x))
  }

  if (!is.null(names(x)) && any(nzchar(names(x)))) {
    return(paste(
      paste0(names(x), "=", as.character(x)),
      collapse = "; "
    ))
  }

  paste(as.character(x), collapse = "; ")
}

.gp_adl_count <- function(log, column) {
  if (NROW(log) == 0L) {
    out <- data.frame(
      value = character(0),
      n = integer(0),
      stringsAsFactors = FALSE
    )
    names(out)[1L] <- column
    return(out)
  }

  x <- log[[column]]
  x[is.na(x) | !nzchar(x)] <- "(not recorded)"

  out <- as.data.frame(table(x), stringsAsFactors = FALSE)
  names(out) <- c(column, "n")
  out <- out[order(out$n, decreasing = TRUE), , drop = FALSE]
  row.names(out) <- NULL
  out
}

.gp_adl_attr_or_na <- function(x, attr_name) {
  value <- attr(x, attr_name, exact = TRUE)

  if (is.null(value) || length(value) == 0L || is.na(value)) {
    return(NA_character_)
  }

  as.character(value)
}
