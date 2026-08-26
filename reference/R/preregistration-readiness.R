#' Create a Gazepoint preregistration checklist
#'
#' Creates a structured checklist for preregistration and reviewer-readiness
#' documentation. The checklist is descriptive only: it helps users document
#' design, preprocessing, QC, exclusions, outcomes, and reporting decisions. It
#' does not judge scientific validity, remove data, or make biometric,
#' psychological, diagnostic, or clinical claims.
#'
#' @param study_id Optional study identifier added to the checklist.
#' @param include_optional Logical. If \code{TRUE}, optional auditability items
#'   such as sensitivity analyses, data dictionaries, and manifests are included.
#' @param custom_items Optional data frame of additional checklist items. It may
#'   contain columns \code{domain}, \code{item_id}, \code{item},
#'   \code{required}, \code{evidence_key}, and \code{required_fields}.
#'
#' @return A data frame with class \code{gazepoint_preregistration_checklist}.
#' @export
create_gazepoint_preregistration_checklist <- function(study_id = NULL,
                                                       include_optional = TRUE,
                                                       custom_items = NULL) {
  gppr_check_logical_one(include_optional, "include_optional")

  if (!is.null(study_id)) {
    if (!is.character(study_id) || length(study_id) != 1 || is.na(study_id)) {
      stop("`study_id` must be NULL or a single character string.", call. = FALSE)
    }
  }

  required_items <- data.frame(
    domain = c(
      "design",
      "sampling",
      "outcomes",
      "preprocessing",
      "quality_control",
      "exclusions",
      "missingness",
      "time_windows",
      "analysis",
      "reporting"
    ),
    item_id = c(
      "design_conditions",
      "sampling_plan",
      "primary_outcomes",
      "preprocessing_plan",
      "qc_thresholds",
      "exclusion_rules",
      "missing_data_plan",
      "analysis_windows",
      "analysis_models",
      "reporting_decisions"
    ),
    item = c(
      "Conditions, participant/trial identifiers, and design structure are specified.",
      "Sampling plan, inclusion criteria, and intended sample size are documented.",
      "Primary outcomes or main dependent variables are identified.",
      "Preprocessing steps and their ordering are documented.",
      "Quality-control metrics, thresholds, or flagging rules are documented.",
      "Exclusion rules and their intended actions are documented.",
      "Missing-data handling decisions are documented.",
      "Analysis windows or event-aligned time intervals are documented where applicable.",
      "Planned analysis models or summary comparisons are documented.",
      "Reporting decisions, tables, figures, or reviewer-facing outputs are documented."
    ),
    required = TRUE,
    evidence_key = c(
      "design",
      "sampling",
      "outcomes",
      "preprocessing",
      "quality_control",
      "exclusions",
      "missingness",
      "time_windows",
      "analysis",
      "reporting"
    ),
    required_fields = c(
      "condition,participant,trial",
      "sample_size,inclusion_criteria",
      "outcome,role",
      "step,decision",
      "metric,rule",
      "rule,action",
      "variable,handling",
      "window_start,window_end",
      "outcome,model",
      "item,decision"
    ),
    stringsAsFactors = FALSE
  )

  optional_items <- data.frame(
    domain = c(
      "randomization",
      "robustness",
      "reproducibility",
      "reproducibility"
    ),
    item_id = c(
      "randomization_checks",
      "sensitivity_analyses",
      "data_dictionary",
      "analysis_manifest"
    ),
    item = c(
      "Randomization or balance checks are documented where applicable.",
      "Planned sensitivity analyses or robustness checks are documented.",
      "A data dictionary or variable map is available.",
      "An analysis manifest or reproducibility ledger is available."
    ),
    required = FALSE,
    evidence_key = c(
      "randomization",
      "sensitivity",
      "dictionary",
      "manifest"
    ),
    required_fields = c(
      "check,result",
      "analysis,reason",
      "variable,description",
      "field,value"
    ),
    stringsAsFactors = FALSE
  )

  checklist <- if (include_optional) {
    rbind(required_items, optional_items)
  } else {
    required_items
  }

  if (!is.null(custom_items)) {
    custom_items <- gppr_normalize_custom_items(custom_items)
    checklist <- rbind(checklist, custom_items)
  }

  checklist$study_id <- if (is.null(study_id)) NA_character_ else study_id
  checklist$status <- "not_checked"
  checklist$notes <- NA_character_

  checklist <- checklist[
    ,
    c(
      "study_id",
      "domain",
      "item_id",
      "item",
      "required",
      "evidence_key",
      "required_fields",
      "status",
      "notes"
    ),
    drop = FALSE
  ]

  class(checklist) <- c("gazepoint_preregistration_checklist", class(checklist))
  checklist
}

#' Audit preregistration checklist consistency
#'
#' Checks whether a preregistration checklist has corresponding evidence objects
#' and whether those evidence objects contain expected fields. The audit is a
#' documentation-readiness check only; it does not judge study quality or perform
#' automatic exclusion.
#'
#' @param checklist A checklist produced by
#'   \code{create_gazepoint_preregistration_checklist()}, or \code{NULL} to use
#'   the default checklist.
#' @param evidence A named list of evidence objects. Each checklist row uses
#'   \code{evidence_key} to look up an object in this list. Evidence objects can
#'   be data frames, named lists, character vectors, logical values, or other
#'   non-empty objects.
#' @param require_required_fields Logical. If \code{TRUE}, listed
#'   \code{required_fields} must be present in data-frame or named-list evidence.
#'
#' @return A list with class \code{gazepoint_preregistration_audit}.
#' @export
audit_gazepoint_preregistration_consistency <- function(checklist = NULL,
                                                        evidence = list(),
                                                        require_required_fields = TRUE) {
  if (is.null(checklist)) {
    checklist <- create_gazepoint_preregistration_checklist()
  }

  gppr_check_checklist(checklist)
  gppr_check_logical_one(require_required_fields, "require_required_fields")

  if (!is.list(evidence) || is.null(names(evidence))) {
    stop("`evidence` must be a named list.", call. = FALSE)
  }

  if (any(!nzchar(names(evidence)))) {
    stop("All `evidence` entries must be named.", call. = FALSE)
  }

  rows <- lapply(seq_len(nrow(checklist)), function(i) {
    row <- checklist[i, , drop = FALSE]
    key <- row$evidence_key
    required_fields <- gppr_parse_required_fields(row$required_fields)
    has_evidence <- key %in% names(evidence)

    evidence_type <- NA_character_
    evidence_rows <- NA_integer_
    evidence_complete <- FALSE
    missing_fields <- character(0)
    present_fields <- character(0)

    if (has_evidence) {
      object <- evidence[[key]]
      info <- gppr_evidence_info(object)
      evidence_type <- info$type
      evidence_rows <- info$n_rows
      evidence_complete <- info$complete
      present_fields <- info$fields

      if (
        require_required_fields &&
        length(required_fields) > 0 &&
        info$field_checkable
      ) {
        missing_fields <- setdiff(required_fields, present_fields)

        if (length(missing_fields) > 0) {
          evidence_complete <- FALSE
        }
      }
    }

    status <- gppr_item_status(
      required = row$required,
      has_evidence = has_evidence,
      evidence_complete = evidence_complete,
      missing_fields = missing_fields
    )

    cbind(
      row,
      data.frame(
        has_evidence = has_evidence,
        evidence_type = evidence_type,
        evidence_rows = evidence_rows,
        evidence_complete = evidence_complete,
        missing_fields = paste(missing_fields, collapse = ","),
        present_fields = paste(present_fields, collapse = ","),
        audit_status = status,
        audit_pass = status %in% c("complete_required", "complete_optional", "not_applicable_optional"),
        stringsAsFactors = FALSE
      )
    )
  })

  item_results <- do.call(rbind, rows)
  rownames(item_results) <- NULL

  summary <- summarize_gazepoint_preregistration_readiness(item_results, by = NULL)

  result <- list(
    checklist = checklist,
    item_results = item_results,
    summary = summary,
    parameters = list(
      evidence_names = names(evidence),
      require_required_fields = require_required_fields
    )
  )

  class(result) <- c("gazepoint_preregistration_audit", "list")
  result
}

#' Summarize preregistration readiness
#'
#' Summarizes checklist or audit results into compact readiness counts and
#' proportions. The summary is intended for reporting and reviewer-readiness
#' documentation.
#'
#' @param audit A \code{gazepoint_preregistration_audit} object or an item-level
#'   audit data frame.
#' @param by Optional grouping column, such as \code{"domain"}.
#'
#' @return A data frame with class \code{gazepoint_preregistration_readiness}.
#' @export
summarize_gazepoint_preregistration_readiness <- function(audit,
                                                          by = NULL) {
  item_results <- if (inherits(audit, "gazepoint_preregistration_audit")) {
    audit$item_results
  } else {
    audit
  }

  if (!is.data.frame(item_results)) {
    stop("`audit` must be a preregistration audit object or an item-level data frame.", call. = FALSE)
  }

  required_cols <- c("required", "audit_status", "audit_pass")

  missing_cols <- setdiff(required_cols, names(item_results))

  if (length(missing_cols) > 0) {
    stop(
      "`audit` is missing required column(s): ",
      paste(missing_cols, collapse = ", "),
      call. = FALSE
    )
  }

  if (!is.null(by)) {
    by <- as.character(by)
    missing_by <- setdiff(by, names(item_results))

    if (length(missing_by) > 0) {
      stop(
        "`by` contains columns not found in `audit`: ",
        paste(missing_by, collapse = ", "),
        call. = FALSE
      )
    }
  }

  split_index <- if (is.null(by) || length(by) == 0) {
    factor(rep("all", nrow(item_results)))
  } else {
    interaction(item_results[by], drop = TRUE, lex.order = TRUE)
  }

  pieces <- split(item_results, split_index, drop = TRUE)

  rows <- lapply(names(pieces), function(piece_name) {
    piece <- pieces[[piece_name]]

    group_values <- if (is.null(by) || length(by) == 0) {
      data.frame(summary_id = piece_name, stringsAsFactors = FALSE)
    } else {
      piece[1, by, drop = FALSE]
    }

    required <- piece$required
    required[is.na(required)] <- FALSE

    pass <- piece$audit_pass
    pass[is.na(pass)] <- FALSE

    required_pass <- pass & required
    optional <- !required
    optional_pass <- pass & optional

    status <- as.character(piece$audit_status)

    n_required <- sum(required, na.rm = TRUE)
    n_optional <- sum(optional, na.rm = TRUE)
    n_required_complete <- sum(required_pass, na.rm = TRUE)
    n_optional_complete <- sum(optional_pass, na.rm = TRUE)

    readiness_score <- if (n_required > 0) {
      n_required_complete / n_required
    } else {
      NA_real_
    }

    cbind(
      group_values,
      data.frame(
        n_items = nrow(piece),
        n_required = n_required,
        n_optional = n_optional,
        n_required_complete = n_required_complete,
        n_optional_complete = n_optional_complete,
        n_missing_required = sum(status == "missing_required", na.rm = TRUE),
        n_incomplete_required = sum(status == "incomplete_required", na.rm = TRUE),
        n_missing_optional = sum(status == "missing_optional", na.rm = TRUE),
        n_incomplete_optional = sum(status == "incomplete_optional", na.rm = TRUE),
        readiness_score = readiness_score,
        readiness_label = gppr_readiness_label(readiness_score),
        incomplete_required_items = paste(
          piece$item_id[required & !pass],
          collapse = ","
        ),
        stringsAsFactors = FALSE
      )
    )
  })

  out <- do.call(rbind, rows)
  rownames(out) <- NULL
  class(out) <- c("gazepoint_preregistration_readiness", class(out))
  out
}

gppr_normalize_custom_items <- function(custom_items) {
  if (!is.data.frame(custom_items)) {
    stop("`custom_items` must be a data frame.", call. = FALSE)
  }

  required_cols <- c("domain", "item_id", "item")
  missing_cols <- setdiff(required_cols, names(custom_items))

  if (length(missing_cols) > 0) {
    stop(
      "`custom_items` is missing required column(s): ",
      paste(missing_cols, collapse = ", "),
      call. = FALSE
    )
  }

  out <- custom_items

  if (!"required" %in% names(out)) {
    out$required <- TRUE
  }

  if (!"evidence_key" %in% names(out)) {
    out$evidence_key <- out$item_id
  }

  if (!"required_fields" %in% names(out)) {
    out$required_fields <- ""
  }

  out <- out[
    ,
    c("domain", "item_id", "item", "required", "evidence_key", "required_fields"),
    drop = FALSE
  ]

  out$domain <- as.character(out$domain)
  out$item_id <- as.character(out$item_id)
  out$item <- as.character(out$item)
  out$required <- as.logical(out$required)
  out$evidence_key <- as.character(out$evidence_key)
  out$required_fields <- as.character(out$required_fields)

  if (any(!nzchar(out$domain)) || any(!nzchar(out$item_id)) || any(!nzchar(out$item))) {
    stop("`custom_items` text columns must contain non-empty values.", call. = FALSE)
  }

  if (any(is.na(out$required))) {
    stop("`custom_items$required` must contain TRUE or FALSE values.", call. = FALSE)
  }

  out
}

gppr_check_checklist <- function(checklist) {
  if (!is.data.frame(checklist)) {
    stop("`checklist` must be a data frame.", call. = FALSE)
  }

  required_cols <- c(
    "domain",
    "item_id",
    "item",
    "required",
    "evidence_key",
    "required_fields"
  )

  missing_cols <- setdiff(required_cols, names(checklist))

  if (length(missing_cols) > 0) {
    stop(
      "`checklist` is missing required column(s): ",
      paste(missing_cols, collapse = ", "),
      call. = FALSE
    )
  }

  if (!is.logical(checklist$required)) {
    stop("`checklist$required` must be logical.", call. = FALSE)
  }

  invisible(TRUE)
}

gppr_parse_required_fields <- function(required_fields) {
  if (length(required_fields) == 0 || is.na(required_fields) || !nzchar(required_fields)) {
    return(character(0))
  }

  fields <- unlist(strsplit(required_fields, "[,;]", perl = TRUE), use.names = FALSE)
  fields <- trimws(fields)
  fields[nzchar(fields)]
}

gppr_evidence_info <- function(object) {
  if (is.data.frame(object)) {
    return(list(
      type = "data.frame",
      n_rows = nrow(object),
      complete = nrow(object) > 0,
      field_checkable = TRUE,
      fields = names(object)
    ))
  }

  if (is.list(object)) {
    return(list(
      type = "list",
      n_rows = length(object),
      complete = length(object) > 0,
      field_checkable = !is.null(names(object)),
      fields = if (is.null(names(object))) character(0) else names(object)
    ))
  }

  if (is.character(object)) {
    complete <- length(object) > 0 && any(nzchar(object[!is.na(object)]))

    return(list(
      type = "character",
      n_rows = length(object),
      complete = complete,
      field_checkable = FALSE,
      fields = character(0)
    ))
  }

  if (is.logical(object)) {
    complete <- length(object) == 1 && isTRUE(object)

    return(list(
      type = "logical",
      n_rows = length(object),
      complete = complete,
      field_checkable = FALSE,
      fields = character(0)
    ))
  }

  list(
    type = class(object)[1],
    n_rows = length(object),
    complete = length(object) > 0,
    field_checkable = FALSE,
    fields = character(0)
  )
}

gppr_item_status <- function(required,
                             has_evidence,
                             evidence_complete,
                             missing_fields) {
  required <- isTRUE(required)

  if (!has_evidence && required) {
    return("missing_required")
  }

  if (!has_evidence && !required) {
    return("missing_optional")
  }

  if (evidence_complete && required) {
    return("complete_required")
  }

  if (evidence_complete && !required) {
    return("complete_optional")
  }

  if (!evidence_complete && required && length(missing_fields) > 0) {
    return("incomplete_required")
  }

  if (!evidence_complete && !required && length(missing_fields) > 0) {
    return("incomplete_optional")
  }

  if (!evidence_complete && required) {
    return("incomplete_required")
  }

  if (!evidence_complete && !required) {
    return("incomplete_optional")
  }

  "not_applicable_optional"
}

gppr_readiness_label <- function(readiness_score) {
  if (!is.finite(readiness_score)) {
    return("not_applicable")
  }

  if (readiness_score >= 1) {
    return("complete")
  }

  if (readiness_score >= 0.75) {
    return("mostly_complete")
  }

  if (readiness_score >= 0.50) {
    return("partly_complete")
  }

  "early_stage"
}

gppr_check_logical_one <- function(x, name) {
  if (!is.logical(x) || length(x) != 1 || is.na(x)) {
    stop("`", name, "` must be TRUE or FALSE.", call. = FALSE)
  }

  invisible(TRUE)
}
