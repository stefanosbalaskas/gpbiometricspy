#' Create a compact Gazepoint methods section
#'
#' Generate conservative, manuscript-ready methods text from available
#' Gazepoint workflow objects. The function reports workflow structure and
#' audit coverage only; it does not infer emotion, stress, cognition,
#' preference, diagnosis, mechanism, or exact temporal onset from biometric
#' or gaze-linked signals.
#'
#' @param export_profile Optional object from `profile_gazepoint_export_folder()`.
#' @param design_audit Optional object from `audit_gazepoint_experiment_design()`.
#' @param event_audit Optional object from `audit_gazepoint_event_coverage()`.
#' @param condition_audit Optional object from `audit_gazepoint_condition_balance()`.
#' @param decision_log Optional object from `create_gazepoint_analysis_decision_log()`.
#' @param package_version Package version to report. Defaults to the installed
#'   gpbiometrics version.
#' @param validation Optional named list with validation entries, for example
#'   `list(test = "PASS 2322", check = "0 errors, 0 warnings, 0 notes")`.
#' @param include_guardrails Logical. If `TRUE`, append conservative
#'   interpretation guardrails.
#'
#' @return A character vector with class `"gazepoint_report_text"`.
#'
#' @examples
#' log <- create_gazepoint_analysis_decision_log(study_id = "demo")
#' create_gazepoint_methods_section(decision_log = log)
#'
#' @export
create_gazepoint_methods_section <- function(export_profile = NULL,
                                             design_audit = NULL,
                                             event_audit = NULL,
                                             condition_audit = NULL,
                                             decision_log = NULL,
                                             package_version = as.character(utils::packageVersion("gpbiometrics")),
                                             validation = NULL,
                                             include_guardrails = TRUE) {
  .gp_rrt_validate_optional_inputs(
    export_profile = export_profile,
    design_audit = design_audit,
    event_audit = event_audit,
    condition_audit = condition_audit,
    decision_log = decision_log
  )

  package_version <- .gp_rrt_scalar(package_version, "package_version")
  include_guardrails <- .gp_rrt_logical(include_guardrails, "include_guardrails")

  txt <- c(
    paste0(
      "Gazepoint biometric workflow processing was conducted using gpbiometrics ",
      package_version,
      ", an R package designed for importing, checking, preprocessing, summarising, ",
      "and reporting Gazepoint Biometrics and GP3-derived biometric exports."
    )
  )

  if (!is.null(export_profile)) {
    ov <- export_profile$overview[1, , drop = FALSE]
    txt <- c(
      txt,
      paste0(
        "Before analysis, the export folder was profiled for file readability, ",
        "row and column structure, likely Gazepoint column roles, signal activity, ",
        "missingness, and folder-level warnings. The profiled folder contained ",
        .gp_rrt_value(ov$n_files), " matching file(s), of which ",
        .gp_rrt_value(ov$n_readable_files), " were readable; ",
        .gp_rrt_value(ov$n_read_errors), " file-level read error(s) were recorded."
      )
    )
  }

  if (!is.null(design_audit)) {
    ov <- design_audit$overview[1, , drop = FALSE]
    txt <- c(
      txt,
      paste0(
        "The experiment-design audit identified ",
        .gp_rrt_value(ov$n_participants), " participant(s), ",
        .gp_rrt_value(ov$n_trials), " trial identifier(s), and ",
        .gp_rrt_value(ov$n_conditions), " condition(s), with ",
        .gp_rrt_value(NROW(design_audit$warnings)),
        " design-warning record(s)."
      )
    )
  }

  if (!is.null(event_audit)) {
    ov <- event_audit$overview[1, , drop = FALSE]
    txt <- c(
      txt,
      paste0(
        "Event coverage was audited across ",
        .gp_rrt_value(ov$n_units), " analysis unit(s) and ",
        .gp_rrt_value(ov$n_expected_events), " expected event label(s). ",
        .gp_rrt_value(ov$n_complete_units), " unit(s) contained all expected events ",
        "(coverage proportion = ", .gp_rrt_prop(ov$complete_unit_prop), ")."
      )
    )
  }

  if (!is.null(condition_audit)) {
    ov <- condition_audit$overview[1, , drop = FALSE]
    txt <- c(
      txt,
      paste0(
        "Condition balance was audited before model-ready data preparation. ",
        "The condition-balance audit identified ",
        .gp_rrt_value(ov$n_participants), " participant(s), ",
        .gp_rrt_value(ov$n_conditions), " condition(s), and ",
        .gp_rrt_value(ov$n_trials), " participant-condition trial unit(s); ",
        "the participant-condition grid was ",
        if (isTRUE(ov$complete_participant_condition_grid)) "complete" else "incomplete",
        "."
      )
    )
  }

  if (!is.null(decision_log)) {
    summary <- summarise_gazepoint_decision_log(decision_log)
    txt <- c(
      txt,
      paste0(
        "Workflow decisions were recorded in a structured analysis decision log. ",
        "The log contained ", .gp_rrt_value(summary$overview$n_decisions),
        " decision record(s), covering exclusions, preprocessing choices, ",
        "quality-control decisions, analysis settings, or reviewer-facing notes where applicable."
      )
    )
  }

  if (!is.null(validation)) {
    txt <- c(txt, .gp_rrt_validation_sentence(validation))
  }

  if (include_guardrails) {
    txt <- c(
      txt,
      "All biometric, gaze-linked, and time-course outputs were treated as workflow descriptors. They were not interpreted as direct measures of emotion, stress, cognition, preference, health status, diagnosis, mechanism, or precise temporal onset."
    )
  }

  .gp_rrt_text(txt, template = "methods_section")
}

#' Create a Gazepoint quality-control supplement section
#'
#' Generate a compact reviewer-facing quality-control supplement from available
#' export-profile, design-audit, event-audit, condition-balance, and decision-log
#' objects.
#'
#' @param export_profile Optional object from `profile_gazepoint_export_folder()`.
#' @param design_audit Optional object from `audit_gazepoint_experiment_design()`.
#' @param event_audit Optional object from `audit_gazepoint_event_coverage()`.
#' @param condition_audit Optional object from `audit_gazepoint_condition_balance()`.
#' @param decision_log Optional object from `create_gazepoint_analysis_decision_log()`.
#' @param title Section title.
#'
#' @return A character vector with class `"gazepoint_report_text"`.
#'
#' @export
create_gazepoint_qc_supplement <- function(export_profile = NULL,
                                           design_audit = NULL,
                                           event_audit = NULL,
                                           condition_audit = NULL,
                                           decision_log = NULL,
                                           title = "Gazepoint workflow quality-control supplement") {
  .gp_rrt_validate_optional_inputs(
    export_profile = export_profile,
    design_audit = design_audit,
    event_audit = event_audit,
    condition_audit = condition_audit,
    decision_log = decision_log
  )

  title <- .gp_rrt_scalar(title, "title")

  txt <- c(title, paste(rep("=", nchar(title)), collapse = ""))

  if (!is.null(export_profile)) {
    txt <- c(
      txt,
      "",
      "Export-folder profile",
      "---------------------",
      .gp_rrt_table_lines(export_profile$overview),
      .gp_rrt_warning_lines(export_profile$warnings)
    )
  }

  if (!is.null(design_audit)) {
    txt <- c(
      txt,
      "",
      "Experiment-design audit",
      "-----------------------",
      .gp_rrt_table_lines(design_audit$overview),
      .gp_rrt_warning_lines(design_audit$warnings)
    )
  }

  if (!is.null(event_audit)) {
    txt <- c(
      txt,
      "",
      "Event-coverage audit",
      "--------------------",
      .gp_rrt_table_lines(event_audit$overview),
      .gp_rrt_warning_lines(event_audit$warnings)
    )
  }

  if (!is.null(condition_audit)) {
    txt <- c(
      txt,
      "",
      "Condition-balance audit",
      "-----------------------",
      .gp_rrt_table_lines(condition_audit$overview),
      .gp_rrt_warning_lines(condition_audit$warnings)
    )
  }

  if (!is.null(decision_log)) {
    summary <- summarise_gazepoint_decision_log(decision_log)
    txt <- c(
      txt,
      "",
      "Analysis decision log",
      "---------------------",
      .gp_rrt_table_lines(summary$overview),
      "",
      "Decision counts by stage:",
      .gp_rrt_table_lines(summary$by_stage)
    )
  }

  if (length(txt) <= 2L) {
    txt <- c(
      txt,
      "",
      "No audit objects were supplied. The supplement template was created without workflow-specific summaries."
    )
  }

  .gp_rrt_text(txt, template = "qc_supplement")
}

#' Create a Gazepoint reproducibility statement
#'
#' Generate a compact reproducibility statement for manuscripts, supplements, or
#' reviewer responses.
#'
#' @param decision_log Optional object from `create_gazepoint_analysis_decision_log()`.
#' @param package_version Package version to report.
#' @param repository_url Optional repository URL.
#' @param validation Optional named list with validation entries.
#' @param data_statement Optional text describing data availability or synthetic
#'   demonstration status.
#' @param include_guardrails Logical. If `TRUE`, include conservative
#'   interpretation guardrails.
#'
#' @return A character vector with class `"gazepoint_report_text"`.
#'
#' @export
create_gazepoint_reproducibility_statement <- function(decision_log = NULL,
                                                       package_version = as.character(utils::packageVersion("gpbiometrics")),
                                                       repository_url = NA_character_,
                                                       validation = NULL,
                                                       data_statement = NA_character_,
                                                       include_guardrails = TRUE) {
  if (!is.null(decision_log) &&
      !inherits(decision_log, "gazepoint_analysis_decision_log")) {
    stop(
      "`decision_log` must be created by `create_gazepoint_analysis_decision_log()`.",
      call. = FALSE
    )
  }

  package_version <- .gp_rrt_scalar(package_version, "package_version")
  repository_url <- .gp_rrt_optional_scalar(repository_url, "repository_url")
  data_statement <- .gp_rrt_optional_scalar(data_statement, "data_statement")
  include_guardrails <- .gp_rrt_logical(include_guardrails, "include_guardrails")

  txt <- c(
    paste0(
      "Analyses were supported by gpbiometrics ",
      package_version,
      ". The workflow was structured to preserve auditability of import, ",
      "quality-control, preprocessing, analysis-readiness, and reporting decisions."
    )
  )

  if (!is.na(repository_url)) {
    txt <- c(txt, paste0("Repository, package source, and documentation are available at: ", repository_url, "."))
  }

  if (!is.null(decision_log)) {
    summary <- summarise_gazepoint_decision_log(decision_log)
    txt <- c(
      txt,
      paste0(
        "A structured analysis decision log recorded ",
        .gp_rrt_value(summary$overview$n_decisions),
        " workflow decision(s)."
      )
    )
  }

  if (!is.null(validation)) {
    txt <- c(txt, .gp_rrt_validation_sentence(validation))
  }

  if (!is.na(data_statement)) {
    txt <- c(txt, data_statement)
  }

  if (include_guardrails) {
    txt <- c(
      txt,
      "The workflow is conservative: biometric and gaze-linked outputs are documented as signal-processing and reporting products, not as automatic labels of emotion, stress, cognition, preference, health status, diagnosis, mechanism, or exact temporal onset."
    )
  }

  .gp_rrt_text(txt, template = "reproducibility_statement")
}

#' Create a Gazepoint audit-report section
#'
#' Create a concise integrated report section from available Gazepoint audit
#' objects.
#'
#' @param export_profile Optional object from `profile_gazepoint_export_folder()`.
#' @param design_audit Optional object from `audit_gazepoint_experiment_design()`.
#' @param event_audit Optional object from `audit_gazepoint_event_coverage()`.
#' @param condition_audit Optional object from `audit_gazepoint_condition_balance()`.
#' @param decision_log Optional object from `create_gazepoint_analysis_decision_log()`.
#' @param include_warnings Logical. If `TRUE`, include warning summaries.
#'
#' @return A character vector with class `"gazepoint_report_text"`.
#'
#' @export
create_gazepoint_audit_report_section <- function(export_profile = NULL,
                                                  design_audit = NULL,
                                                  event_audit = NULL,
                                                  condition_audit = NULL,
                                                  decision_log = NULL,
                                                  include_warnings = TRUE) {
  .gp_rrt_validate_optional_inputs(
    export_profile = export_profile,
    design_audit = design_audit,
    event_audit = event_audit,
    condition_audit = condition_audit,
    decision_log = decision_log
  )

  include_warnings <- .gp_rrt_logical(include_warnings, "include_warnings")

  txt <- c("Gazepoint workflow audit summary")

  if (!is.null(export_profile)) {
    ov <- export_profile$overview[1, , drop = FALSE]
    txt <- c(
      txt,
      paste0(
        "The export-folder profile included ", .gp_rrt_value(ov$n_files),
        " matching file(s), ", .gp_rrt_value(ov$n_readable_files),
        " readable file(s), and ", .gp_rrt_value(ov$n_read_errors),
        " read error(s)."
      )
    )
  }

  if (!is.null(design_audit)) {
    ov <- design_audit$overview[1, , drop = FALSE]
    txt <- c(
      txt,
      paste0(
        "The design audit identified ", .gp_rrt_value(ov$n_participants),
        " participant(s), ", .gp_rrt_value(ov$n_trials),
        " trial identifier(s), and ", .gp_rrt_value(ov$n_conditions),
        " condition(s)."
      )
    )
  }

  if (!is.null(event_audit)) {
    ov <- event_audit$overview[1, , drop = FALSE]
    txt <- c(
      txt,
      paste0(
        "The event-coverage audit evaluated ", .gp_rrt_value(ov$n_units),
        " unit(s), with complete expected-event coverage in ",
        .gp_rrt_value(ov$n_complete_units), " unit(s)."
      )
    )
  }

  if (!is.null(condition_audit)) {
    ov <- condition_audit$overview[1, , drop = FALSE]
    txt <- c(
      txt,
      paste0(
        "The condition-balance audit indicated a trial-imbalance ratio of ",
        .gp_rrt_prop(ov$trial_imbalance_ratio), " and a ",
        if (isTRUE(ov$complete_participant_condition_grid)) "complete" else "incomplete",
        " participant-condition grid."
      )
    )
  }

  if (!is.null(decision_log)) {
    summary <- summarise_gazepoint_decision_log(decision_log)
    txt <- c(
      txt,
      paste0(
        "The decision log contained ",
        .gp_rrt_value(summary$overview$n_decisions),
        " recorded workflow decision(s)."
      )
    )
  }

  if (length(txt) == 1L) {
    txt <- c(
      txt,
      "No audit objects were supplied. The report section was created without workflow-specific summaries."
    )
  }

  if (include_warnings) {
    warnings <- .gp_rrt_collect_warnings(
      export_profile = export_profile,
      design_audit = design_audit,
      event_audit = event_audit,
      condition_audit = condition_audit
    )

    txt <- c(txt, .gp_rrt_warning_summary_sentence(warnings))
  }

  .gp_rrt_text(txt, template = "audit_report_section")
}

#' @export
print.gazepoint_report_text <- function(x, ...) {
  cat(paste(as.character(x), collapse = "\n\n"))
  cat("\n")
  invisible(x)
}

.gp_rrt_text <- function(x, template) {
  x <- as.character(x)
  attr(x, "template") <- template
  class(x) <- c("gazepoint_report_text", "character")
  x
}

.gp_rrt_validate_optional_inputs <- function(export_profile,
                                             design_audit,
                                             event_audit,
                                             condition_audit,
                                             decision_log) {
  if (!is.null(export_profile) &&
      !inherits(export_profile, "gazepoint_export_folder_profile")) {
    stop(
      "`export_profile` must be created by `profile_gazepoint_export_folder()`.",
      call. = FALSE
    )
  }

  if (!is.null(design_audit) &&
      !inherits(design_audit, "gazepoint_experiment_design_audit")) {
    stop(
      "`design_audit` must be created by `audit_gazepoint_experiment_design()`.",
      call. = FALSE
    )
  }

  if (!is.null(event_audit) &&
      !inherits(event_audit, "gazepoint_event_coverage_audit")) {
    stop(
      "`event_audit` must be created by `audit_gazepoint_event_coverage()`.",
      call. = FALSE
    )
  }

  if (!is.null(condition_audit) &&
      !inherits(condition_audit, "gazepoint_condition_balance_audit")) {
    stop(
      "`condition_audit` must be created by `audit_gazepoint_condition_balance()`.",
      call. = FALSE
    )
  }

  if (!is.null(decision_log) &&
      !inherits(decision_log, "gazepoint_analysis_decision_log")) {
    stop(
      "`decision_log` must be created by `create_gazepoint_analysis_decision_log()`.",
      call. = FALSE
    )
  }

  invisible(TRUE)
}

.gp_rrt_scalar <- function(x, name) {
  if (is.null(x) || length(x) != 1L || is.na(x) || !nzchar(as.character(x))) {
    stop("`", name, "` must be a non-empty scalar value.", call. = FALSE)
  }

  as.character(x)
}

.gp_rrt_optional_scalar <- function(x, name) {
  if (is.null(x) || length(x) == 0L || is.na(x)) {
    return(NA_character_)
  }

  if (length(x) != 1L) {
    stop("`", name, "` must be a scalar value.", call. = FALSE)
  }

  as.character(x)
}

.gp_rrt_logical <- function(x, name) {
  if (!is.logical(x) || length(x) != 1L || is.na(x)) {
    stop("`", name, "` must be TRUE or FALSE.", call. = FALSE)
  }

  x
}

.gp_rrt_value <- function(x) {
  if (length(x) == 0L || is.na(x)) {
    return("not recorded")
  }

  as.character(x)
}

.gp_rrt_prop <- function(x) {
  if (length(x) == 0L || is.na(x)) {
    return("not recorded")
  }

  if (is.infinite(x)) {
    return("Inf")
  }

  format(round(as.numeric(x), 3), nsmall = 3, trim = TRUE)
}

.gp_rrt_validation_sentence <- function(validation) {
  if (!is.list(validation) || length(validation) == 0L) {
    stop("`validation` must be NULL or a non-empty named list.", call. = FALSE)
  }

  nms <- names(validation)
  if (is.null(nms) || any(!nzchar(nms))) {
    stop("`validation` must be a named list.", call. = FALSE)
  }

  vals <- vapply(validation, function(x) {
    if (length(x) == 0L || is.na(x[1])) {
      "not recorded"
    } else {
      as.character(x[1])
    }
  }, character(1))

  paste0(
    "Package validation was recorded as: ",
    paste(paste0(nms, " = ", vals), collapse = "; "),
    "."
  )
}

.gp_rrt_table_lines <- function(x) {
  if (is.null(x) || NROW(x) == 0L) {
    return("No rows recorded.")
  }

  utils::capture.output(print(x, row.names = FALSE))
}

.gp_rrt_warning_lines <- function(warnings) {
  if (is.null(warnings) || NROW(warnings) == 0L) {
    return("Warnings: none recorded.")
  }

  c("Warnings:", utils::capture.output(print(warnings, row.names = FALSE)))
}

.gp_rrt_collect_warnings <- function(export_profile,
                                     design_audit,
                                     event_audit,
                                     condition_audit) {
  out <- list()

  if (!is.null(export_profile) && NROW(export_profile$warnings) > 0L) {
    tmp <- export_profile$warnings
    tmp$source <- "export_profile"
    out[[length(out) + 1L]] <- tmp
  }

  if (!is.null(design_audit) && NROW(design_audit$warnings) > 0L) {
    tmp <- design_audit$warnings
    tmp$source <- "design_audit"
    out[[length(out) + 1L]] <- tmp
  }

  if (!is.null(event_audit) && NROW(event_audit$warnings) > 0L) {
    tmp <- event_audit$warnings
    tmp$source <- "event_audit"
    out[[length(out) + 1L]] <- tmp
  }

  if (!is.null(condition_audit) && NROW(condition_audit$warnings) > 0L) {
    tmp <- condition_audit$warnings
    tmp$source <- "condition_audit"
    out[[length(out) + 1L]] <- tmp
  }

  if (length(out) == 0L) {
    return(data.frame(
      severity = character(0),
      issue = character(0),
      message = character(0),
      source = character(0),
      stringsAsFactors = FALSE
    ))
  }

  do.call(rbind, out)
}

.gp_rrt_warning_summary_sentence <- function(warnings) {
  if (is.null(warnings) || NROW(warnings) == 0L) {
    return("No audit warnings were recorded in the supplied objects.")
  }

  sev <- as.data.frame(table(warnings$severity), stringsAsFactors = FALSE)
  names(sev) <- c("severity", "n")

  paste0(
    "Across supplied audit objects, warning records were: ",
    paste(paste0(sev$severity, " = ", sev$n), collapse = "; "),
    "."
  )
}
