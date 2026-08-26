#' Create a Gazepoint audit index
#'
#' Normalizes one or more Gazepoint audit/check objects into a single tabular
#' index. The function is designed for reproducibility and reporting: it records
#' object identifiers, source tables, checks, items, statuses, messages, and
#' optional paths. It does not modify data and does not make scientific or
#' clinical interpretations.
#'
#' @param audits A single audit object, a data frame, or a named/unnamed list of
#'   audit objects. Recognized list elements include \code{checks},
#'   \code{item_results}, \code{results}, \code{issues}, \code{flags},
#'   \code{problems}, and \code{summary}.
#' @param audit_ids Optional character vector of audit identifiers. If omitted,
#'   names from \code{audits} are used where available.
#' @param include_summary_rows Logical. If \code{TRUE}, summary rows are added
#'   when a supplied audit object contains a \code{summary} data frame. If
#'   \code{FALSE}, summary rows are added only when no detailed audit table is
#'   available.
#'
#' @return A data frame with class \code{gazepoint_audit_index}.
#' @export
create_gazepoint_audit_index <- function(audits,
                                         audit_ids = NULL,
                                         include_summary_rows = FALSE) {
  gpati_check_logical_one(include_summary_rows, "include_summary_rows")

  if (missing(audits) || is.null(audits)) {
    out <- gpati_empty_index()
    class(out) <- c("gazepoint_audit_index", class(out))
    return(out)
  }

  audit_list <- gpati_normalize_audit_list(audits)
  audit_ids <- gpati_normalize_audit_ids(audit_list, audit_ids)

  rows <- list()

  for (i in seq_along(audit_list)) {
    object <- audit_list[[i]]
    audit_id <- audit_ids[[i]]
    object_class <- paste(class(object), collapse = "/")

    detail <- gpati_extract_detail_table(object)

    if (!is.null(detail$data)) {
      rows[[length(rows) + 1]] <- gpati_normalize_detail_table(
        detail$data,
        audit_id = audit_id,
        object_class = object_class,
        source_table = detail$source_table
      )
    }

    summary_table <- gpati_extract_summary_table(object)

    if (!is.null(summary_table) && (include_summary_rows || is.null(detail$data))) {
      rows[[length(rows) + 1]] <- gpati_normalize_summary_table(
        summary_table,
        audit_id = audit_id,
        object_class = object_class
      )
    }

    if (is.null(detail$data) && is.null(summary_table)) {
      rows[[length(rows) + 1]] <- gpati_issue_row(
        audit_id = audit_id,
        object_class = object_class,
        source_table = "object",
        check = "object_record",
        item = NA_character_,
        status = "recorded",
        message = "Object was supplied but no recognized audit table was found.",
        path = NA_character_,
        domain = NA_character_,
        row_number = 1L
      )
    }
  }

  if (length(rows) == 0) {
    out <- gpati_empty_index()
  } else {
    out <- do.call(rbind, rows)
    rownames(out) <- NULL
  }

  class(out) <- c("gazepoint_audit_index", class(out))
  out
}

#' Summarize a Gazepoint audit trail
#'
#' Summarizes pass, warning, failure, not-checked, recorded, and other status
#' counts from a Gazepoint audit index. The summary is descriptive only and is
#' intended to support transparent reporting of audit outputs.
#'
#' @param audit_index A \code{gazepoint_audit_index} object, a data frame, or an
#'   object accepted by \code{create_gazepoint_audit_index()}.
#' @param by Optional character vector of grouping columns in \code{audit_index},
#'   such as \code{"audit_id"}, \code{"source_table"}, or \code{"domain"}.
#'
#' @return A data frame with class \code{gazepoint_audit_trail_summary}.
#' @export
summarize_gazepoint_audit_trail <- function(audit_index,
                                            by = NULL) {
  index <- gpati_as_index(audit_index)
  by <- gpati_optional_character(by, "by")

  if (nrow(index) == 0) {
    out <- gpati_empty_summary(by)
    class(out) <- c("gazepoint_audit_trail_summary", class(out))
    return(out)
  }

  if (!is.null(by)) {
    missing_by <- setdiff(by, names(index))

    if (length(missing_by) > 0) {
      stop(
        "`by` contains unknown column(s): ",
        paste(missing_by, collapse = ", "),
        call. = FALSE
      )
    }

    group_key <- interaction(index[, by, drop = FALSE], drop = TRUE, sep = "\r")
    split_index <- split(index, group_key)
    group_values <- lapply(split_index, function(x) x[1, by, drop = FALSE])
    summaries <- lapply(split_index, gpati_summarize_one_index)

    out <- do.call(rbind, Map(cbind, group_values, summaries))
  } else {
    out <- gpati_summarize_one_index(index)
  }

  rownames(out) <- NULL
  class(out) <- c("gazepoint_audit_trail_summary", class(out))
  out
}

#' Export a Gazepoint audit trail as Markdown
#'
#' Creates a plain Markdown audit-trail summary from a Gazepoint audit index.
#' The output can be copied into supplementary materials, review responses, or
#' project documentation. No rendering dependency is required.
#'
#' @param audit_index A \code{gazepoint_audit_index} object, a data frame, or an
#'   object accepted by \code{create_gazepoint_audit_index()}.
#' @param summary Optional summary table. If \code{NULL}, the summary is created
#'   with \code{summarize_gazepoint_audit_trail()}.
#' @param title Markdown title.
#' @param include_details Logical. If \code{TRUE}, detail rows are included.
#' @param max_details Maximum number of detail rows to include.
#' @param file Optional file path. If supplied, the Markdown text is written to
#'   disk.
#'
#' @return A single character string containing Markdown text.
#' @export
export_gazepoint_audit_trail_markdown <- function(audit_index,
                                                  summary = NULL,
                                                  title = "Gazepoint audit trail",
                                                  include_details = TRUE,
                                                  max_details = 50,
                                                  file = NULL) {
  index <- gpati_as_index(audit_index)

  if (is.null(summary)) {
    summary <- summarize_gazepoint_audit_trail(index)
  } else if (!is.data.frame(summary)) {
    stop("`summary` must be NULL or a data frame.", call. = FALSE)
  }

  title <- gpati_required_scalar_character(title, "title")
  gpati_check_logical_one(include_details, "include_details")
  max_details <- gpati_check_nonnegative_integer(max_details, "max_details")
  file <- gpati_optional_scalar_character(file, "file")

  lines <- c(
    paste0("# ", title),
    "",
    "## Summary",
    "",
    gpati_markdown_table(summary)
  )

  if (include_details) {
    detail <- index

    if (nrow(detail) > max_details) {
      detail <- detail[seq_len(max_details), , drop = FALSE]
      truncated <- TRUE
    } else {
      truncated <- FALSE
    }

    detail <- detail[
      ,
      c("audit_id", "source_table", "check", "item", "status", "message"),
      drop = FALSE
    ]

    lines <- c(
      lines,
      "",
      "## Details",
      "",
      gpati_markdown_table(detail)
    )

    if (truncated) {
      lines <- c(
        lines,
        "",
        paste0("_Detail table truncated to ", max_details, " rows._")
      )
    }
  }

  md <- paste(lines, collapse = "\n")

  if (!is.null(file)) {
    writeLines(md, file, useBytes = TRUE)
  }

  md
}

gpati_normalize_audit_list <- function(audits) {
  if (is.data.frame(audits)) {
    return(list(audits))
  }

  if (!is.list(audits)) {
    stop("`audits` must be an audit object, data frame, or list.", call. = FALSE)
  }

  if (gpati_is_audit_like(audits)) {
    return(list(audits))
  }

  audits
}

gpati_is_audit_like <- function(x) {
  if (!is.list(x) || is.data.frame(x)) {
    return(FALSE)
  }

  recognized <- c(
    "checks",
    "item_results",
    "results",
    "issues",
    "flags",
    "problems",
    "summary"
  )

  any(recognized %in% names(x))
}

gpati_normalize_audit_ids <- function(audit_list, audit_ids) {
  n <- length(audit_list)

  if (!is.null(audit_ids)) {
    if (!is.character(audit_ids) || length(audit_ids) != n || any(is.na(audit_ids)) || any(!nzchar(audit_ids))) {
      stop("`audit_ids` must be NULL or a non-empty character vector with one value per audit object.", call. = FALSE)
    }

    return(audit_ids)
  }

  ids <- names(audit_list)

  if (is.null(ids)) {
    ids <- rep("", n)
  }

  missing <- is.na(ids) | !nzchar(ids)
  ids[missing] <- sprintf("audit_%03d", which(missing))
  ids
}

gpati_extract_detail_table <- function(object) {
  if (is.data.frame(object)) {
    return(list(data = object, source_table = "data_frame"))
  }

  if (!is.list(object)) {
    return(list(data = NULL, source_table = NA_character_))
  }

  candidates <- c("checks", "item_results", "results", "issues", "flags", "problems")

  for (candidate in candidates) {
    if (candidate %in% names(object) && is.data.frame(object[[candidate]])) {
      return(list(data = object[[candidate]], source_table = candidate))
    }
  }

  list(data = NULL, source_table = NA_character_)
}

gpati_extract_summary_table <- function(object) {
  if (!is.list(object) || is.data.frame(object)) {
    return(NULL)
  }

  if ("summary" %in% names(object) && is.data.frame(object$summary)) {
    return(object$summary)
  }

  NULL
}

gpati_normalize_detail_table <- function(data,
                                         audit_id,
                                         object_class,
                                         source_table) {
  if (nrow(data) == 0) {
    return(gpati_issue_row(
      audit_id = audit_id,
      object_class = object_class,
      source_table = source_table,
      check = "empty_table",
      item = NA_character_,
      status = "not_checked",
      message = "Audit table contained no rows.",
      path = NA_character_,
      domain = NA_character_,
      row_number = 1L
    ))
  }

  check_col <- gpati_find_col(data, c("check", "section", "category", "type", "source"))
  item_col <- gpati_find_col(data, c("item", "field", "step_id", "metric", "variable", "column", "file_name", "rule", "path"))
  status_col <- gpati_find_col(data, c("status", "result", "outcome", "check_status", "flag"))
  message_col <- gpati_find_col(data, c("message", "description", "notes", "interpretation", "reason", "warning"))
  path_col <- gpati_find_col(data, c("path", "file", "relative_path"))
  domain_col <- gpati_find_col(data, c("domain", "group"))

  n <- nrow(data)

  check <- gpati_column_or_default(data, check_col, source_table)
  item <- gpati_column_or_default(data, item_col, NA_character_)
  status <- gpati_column_or_default(data, status_col, "recorded")
  message <- gpati_column_or_default(data, message_col, "")
  path <- gpati_column_or_default(data, path_col, NA_character_)
  domain <- gpati_column_or_default(data, domain_col, NA_character_)

  out <- data.frame(
    audit_id = rep(audit_id, n),
    object_class = rep(object_class, n),
    source_table = rep(source_table, n),
    row_number = seq_len(n),
    check = as.character(check),
    item = as.character(item),
    status = gpati_normalize_status(status),
    message = as.character(message),
    path = as.character(path),
    domain = as.character(domain),
    stringsAsFactors = FALSE
  )

  out$message[is.na(out$message)] <- ""
  out$check[is.na(out$check) | !nzchar(out$check)] <- source_table
  out
}

gpati_normalize_summary_table <- function(summary_table,
                                          audit_id,
                                          object_class) {
  if (nrow(summary_table) == 0) {
    return(gpati_issue_row(
      audit_id = audit_id,
      object_class = object_class,
      source_table = "summary",
      check = "summary",
      item = NA_character_,
      status = "not_checked",
      message = "Summary table contained no rows.",
      path = NA_character_,
      domain = NA_character_,
      row_number = 1L
    ))
  }

  rows <- lapply(seq_len(nrow(summary_table)), function(i) {
    row <- summary_table[i, , drop = FALSE]
    status <- gpati_status_from_summary(row)
    message <- gpati_summary_message(row)

    gpati_issue_row(
      audit_id = audit_id,
      object_class = object_class,
      source_table = "summary",
      check = "summary",
      item = paste0("summary_row_", i),
      status = status,
      message = message,
      path = NA_character_,
      domain = NA_character_,
      row_number = i
    )
  })

  do.call(rbind, rows)
}

gpati_status_from_summary <- function(row) {
  n_fail <- gpati_summary_count(row, c("n_fail", "n_failed", "fail", "failed"))
  n_warn <- gpati_summary_count(row, c("n_warn", "n_warning", "n_warnings", "warn", "warnings"))
  n_missing <- gpati_summary_count(row, c("n_missing", "missing", "n_missing_required"))

  audit_pass_col <- gpati_find_col(row, c("audit_pass", "pass", "passed"))

  if (n_fail > 0 || n_missing > 0) {
    return("fail")
  }

  if (n_warn > 0) {
    return("warn")
  }

  if (!is.na(audit_pass_col)) {
    val <- row[[audit_pass_col]][1]

    if (is.logical(val) && isTRUE(val)) {
      return("pass")
    }

    if (is.logical(val) && identical(val, FALSE)) {
      return("fail")
    }
  }

  "recorded"
}

gpati_summary_count <- function(row, candidates) {
  col <- gpati_find_col(row, candidates)

  if (is.na(col)) {
    return(0)
  }

  val <- suppressWarnings(as.numeric(row[[col]][1]))

  if (is.na(val)) {
    0
  } else {
    val
  }
}

gpati_summary_message <- function(row) {
  pieces <- paste(names(row), as.character(row[1, , drop = TRUE]), sep = "=")
  paste(pieces, collapse = "; ")
}

gpati_issue_row <- function(audit_id,
                            object_class,
                            source_table,
                            check,
                            item,
                            status,
                            message,
                            path,
                            domain,
                            row_number) {
  data.frame(
    audit_id = audit_id,
    object_class = object_class,
    source_table = source_table,
    row_number = row_number,
    check = check,
    item = item,
    status = status,
    message = message,
    path = path,
    domain = domain,
    stringsAsFactors = FALSE
  )
}

gpati_find_col <- function(data, candidates) {
  lower_names <- tolower(names(data))
  idx <- match(tolower(candidates), lower_names)
  idx <- idx[!is.na(idx)]

  if (length(idx) == 0) {
    return(NA_character_)
  }

  names(data)[idx[1]]
}

gpati_column_or_default <- function(data, column, default) {
  if (is.na(column)) {
    return(rep(default, nrow(data)))
  }

  x <- data[[column]]

  if (length(x) == 0) {
    return(rep(default, nrow(data)))
  }

  as.character(x)
}

gpati_normalize_status <- function(status) {
  x <- tolower(trimws(as.character(status)))
  x[is.na(x) | !nzchar(x)] <- "recorded"
  x <- gsub("[ -]+", "_", x)

  out <- rep("other", length(x))
  out[x %in% c("pass", "passed", "ok", "okay", "complete", "completed", "accepted", "good", "true")] <- "pass"
  out[x %in% c("warn", "warning", "warnings", "review", "flag", "flagged", "caution")] <- "warn"
  out[x %in% c("fail", "failed", "error", "missing", "incomplete", "rejected", "reject", "bad", "false")] <- "fail"
  out[x %in% c("not_checked", "not_applicable", "skipped", "skip", "na", "n/a")] <- "not_checked"
  out[x %in% c("recorded", "present", "available")] <- "recorded"
  out
}

gpati_as_index <- function(audit_index) {
  if (inherits(audit_index, "gazepoint_audit_index")) {
    return(audit_index)
  }

  if (is.data.frame(audit_index) && all(c("audit_id", "status") %in% names(audit_index))) {
    out <- audit_index
    class(out) <- c("gazepoint_audit_index", class(out))
    return(out)
  }

  create_gazepoint_audit_index(audit_index)
}

gpati_summarize_one_index <- function(index) {
  status <- gpati_normalize_status(index$status)

  data.frame(
    n_records = length(status),
    n_pass = sum(status == "pass", na.rm = TRUE),
    n_warn = sum(status == "warn", na.rm = TRUE),
    n_fail = sum(status == "fail", na.rm = TRUE),
    n_not_checked = sum(status == "not_checked", na.rm = TRUE),
    n_recorded = sum(status == "recorded", na.rm = TRUE),
    n_other = sum(status == "other", na.rm = TRUE),
    audit_pass = !any(status == "fail", na.rm = TRUE),
    needs_review = any(status %in% c("warn", "fail"), na.rm = TRUE),
    stringsAsFactors = FALSE
  )
}

gpati_empty_index <- function() {
  data.frame(
    audit_id = character(0),
    object_class = character(0),
    source_table = character(0),
    row_number = integer(0),
    check = character(0),
    item = character(0),
    status = character(0),
    message = character(0),
    path = character(0),
    domain = character(0),
    stringsAsFactors = FALSE
  )
}

gpati_empty_summary <- function(by) {
  base <- data.frame(
    n_records = integer(0),
    n_pass = integer(0),
    n_warn = integer(0),
    n_fail = integer(0),
    n_not_checked = integer(0),
    n_recorded = integer(0),
    n_other = integer(0),
    audit_pass = logical(0),
    needs_review = logical(0),
    stringsAsFactors = FALSE
  )

  if (is.null(by)) {
    return(base)
  }

  group_cols <- as.data.frame(
    stats::setNames(rep(list(character(0)), length(by)), by),
    stringsAsFactors = FALSE
  )

  cbind(group_cols, base)
}

gpati_markdown_table <- function(data) {
  if (!is.data.frame(data) || nrow(data) == 0) {
    return("_No rows._")
  }

  out <- data
  out[] <- lapply(out, function(x) {
    x <- as.character(x)
    x[is.na(x)] <- ""
    x <- gsub("\\|", "\\\\|", x)
    x <- gsub("\r", " ", x, fixed = TRUE)
    x <- gsub("\n", " ", x, fixed = TRUE)
    x
  })

  header <- paste0("| ", paste(names(out), collapse = " | "), " |")
  divider <- paste0("| ", paste(rep("---", ncol(out)), collapse = " | "), " |")
  body <- apply(out, 1, function(row) {
    paste0("| ", paste(row, collapse = " | "), " |")
  })

  paste(c(header, divider, body), collapse = "\n")
}

gpati_optional_character <- function(x, name) {
  if (is.null(x)) {
    return(NULL)
  }

  if (!is.character(x) || any(is.na(x))) {
    stop("`", name, "` must be NULL or a character vector.", call. = FALSE)
  }

  x[nzchar(x)]
}

gpati_optional_scalar_character <- function(x, name) {
  if (is.null(x)) {
    return(NULL)
  }

  gpati_required_scalar_character(x, name)
}

gpati_required_scalar_character <- function(x, name) {
  if (!is.character(x) || length(x) != 1 || is.na(x) || !nzchar(x)) {
    stop("`", name, "` must be a single non-empty character string.", call. = FALSE)
  }

  x
}

gpati_check_logical_one <- function(x, name) {
  if (!is.logical(x) || length(x) != 1 || is.na(x)) {
    stop("`", name, "` must be TRUE or FALSE.", call. = FALSE)
  }

  invisible(TRUE)
}

gpati_check_nonnegative_integer <- function(x, name) {
  if (!is.numeric(x) || length(x) != 1 || is.na(x) || x < 0 || x != floor(x)) {
    stop("`", name, "` must be a single non-negative integer.", call. = FALSE)
  }

  as.integer(x)
}
