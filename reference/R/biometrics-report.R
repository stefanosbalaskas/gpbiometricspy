#' Create a Gazepoint Biometrics report
#'
#' Creates a structured, manuscript-oriented report object for Gazepoint
#' Biometrics data, workflow outputs, quality checks, report tables, methods
#' text, and reporting checklists. The report is intentionally conservative:
#' GSR/EDA is described as electrodermal activity/arousal-related signal rather
#' than emotional valence; heart-rate interpretation is tied to baseline/task
#' context; eye-tracking is described as visual attention rather than direct
#' cognition; and raw `HRV` columns are not treated as HRV metrics.
#'
#' The function can also write a lightweight Markdown or HTML file without
#' adding heavy reporting dependencies.
#'
#' @param data Optional biometric data frame.
#' @param workflow Optional workflow object or workflow summary list.
#' @param validation Optional validation object or data frame.
#' @param quality Optional quality-audit object or data frame.
#' @param sampling Optional sampling-audit object or data frame.
#' @param missingness Optional missingness-audit object or data frame.
#' @param exclusions Optional exclusion-recommendation object or data frame.
#' @param report_tables Optional report-table object, data frame, or named list
#'   of data frames.
#' @param methods_text Optional methods text, character vector, or object
#'   returned by `create_gazepoint_biometrics_methods_text()`.
#' @param checklist Optional checklist object or data frame.
#' @param title Report title.
#' @param subtitle Optional report subtitle.
#' @param output_file Optional path to write a report file.
#' @param format Output format when `output_file` is supplied. Supported values
#'   are `"markdown"` and `"html"`.
#' @param include_timestamp Logical. Should a creation timestamp be included?
#' @param overwrite Logical. Should an existing `output_file` be overwritten?
#' @param max_table_rows Maximum number of rows shown per table in the written
#'   report.
#'
#' @return A list of class `"gazepoint_biometrics_report"` with `overview`,
#'   `sections`, `tables`, `objects`, `output_file`, and `settings`.
#'
#' @examples
#' df <- data.frame(
#'   CNT = 1:5,
#'   GSR = c(1, 1.1, 1.2, 1.1, 1),
#'   HR = c(70, 71, 72, 71, 70),
#'   DIAL = c(40, 42, 44, 43, 41)
#' )
#' report <- create_gazepoint_biometrics_report(df)
#' names(report)
#'
#' @export
create_gazepoint_biometrics_report <- function(data = NULL,
                                               workflow = NULL,
                                               validation = NULL,
                                               quality = NULL,
                                               sampling = NULL,
                                               missingness = NULL,
                                               exclusions = NULL,
                                               report_tables = NULL,
                                               methods_text = NULL,
                                               checklist = NULL,
                                               title = "Gazepoint Biometrics report",
                                               subtitle = NULL,
                                               output_file = NULL,
                                               format = c("markdown", "html"),
                                               include_timestamp = FALSE,
                                               overwrite = FALSE,
                                               max_table_rows = 20L) {
  format <- match.arg(format)

  if (!is.null(data) && !is.data.frame(data)) {
    stop("`data` must be NULL or a data frame.", call. = FALSE)
  }

  if (!is.character(title) || length(title) != 1L || is.na(title) ||
      !nzchar(title)) {
    stop("`title` must be a non-empty character string.", call. = FALSE)
  }

  if (!is.null(subtitle) &&
      (!is.character(subtitle) || length(subtitle) != 1L || is.na(subtitle))) {
    stop("`subtitle` must be NULL or a single character string.", call. = FALSE)
  }

  if (!is.null(output_file) &&
      (!is.character(output_file) || length(output_file) != 1L ||
       is.na(output_file) || !nzchar(output_file))) {
    stop("`output_file` must be NULL or a non-empty character string.",
         call. = FALSE)
  }

  if (!is.logical(include_timestamp) ||
      length(include_timestamp) != 1L ||
      is.na(include_timestamp)) {
    stop("`include_timestamp` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.logical(overwrite) || length(overwrite) != 1L || is.na(overwrite)) {
    stop("`overwrite` must be TRUE or FALSE.", call. = FALSE)
  }

  .gpbiom_assert_positive_integer(max_table_rows, "max_table_rows")

  if (!is.null(output_file) && file.exists(output_file) && !isTRUE(overwrite)) {
    stop("`output_file` already exists. Use `overwrite = TRUE` to replace it.",
         call. = FALSE)
  }

  derived <- .gpbiom_report_derive_objects(
    data = data,
    workflow = workflow,
    validation = validation,
    quality = quality,
    sampling = sampling,
    missingness = missingness,
    exclusions = exclusions,
    report_tables = report_tables,
    methods_text = methods_text,
    checklist = checklist
  )

  overview <- .gpbiom_report_overview(
    data = data,
    workflow = workflow,
    derived = derived,
    title = title,
    subtitle = subtitle,
    include_timestamp = include_timestamp
  )

  tables <- .gpbiom_report_collect_tables(
    derived = derived,
    report_tables = report_tables
  )

  sections <- .gpbiom_report_sections(
    title = title,
    subtitle = subtitle,
    overview = overview,
    derived = derived,
    tables = tables,
    include_timestamp = include_timestamp,
    max_table_rows = max_table_rows
  )

  output_path <- NA_character_

  if (!is.null(output_file)) {
    text <- .gpbiom_report_render(
      sections = sections,
      format = format
    )

    output_dir <- dirname(output_file)

    if (!identical(output_dir, ".") && !dir.exists(output_dir)) {
      dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
    }

    writeLines(text, output_file, useBytes = TRUE)
    output_path <- normalizePath(output_file, winslash = "/", mustWork = FALSE)
  }

  out <- list(
    overview = overview,
    sections = sections,
    tables = tables,
    objects = derived,
    output_file = output_path,
    settings = list(
      title = title,
      subtitle = subtitle,
      format = format,
      include_timestamp = include_timestamp,
      overwrite = overwrite,
      max_table_rows = as.integer(max_table_rows),
      cautions = .gpbiom_report_cautions()
    )
  )

  class(out) <- c("gazepoint_biometrics_report", class(out))
  out
}


.gpbiom_report_derive_objects <- function(data,
                                          workflow,
                                          validation,
                                          quality,
                                          sampling,
                                          missingness,
                                          exclusions,
                                          report_tables,
                                          methods_text,
                                          checklist) {
  schema <- NULL
  validity <- NULL

  if (!is.null(data)) {
    schema <- tryCatch(
      detect_gazepoint_biometric_schema(data),
      error = function(e) NULL
    )

    validity <- tryCatch(
      summarise_gazepoint_biometric_validity(data),
      error = function(e) NULL
    )

    if (is.null(sampling)) {
      sampling <- tryCatch(
        audit_gazepoint_biometric_sampling(data),
        error = function(e) NULL
      )
    }

    if (is.null(missingness)) {
      missingness <- tryCatch(
        audit_gazepoint_biometric_missingness(data),
        error = function(e) NULL
      )
    }
  }

  list(
    schema = schema,
    validity = validity,
    workflow = workflow,
    validation = validation,
    quality = quality,
    sampling = sampling,
    missingness = missingness,
    exclusions = exclusions,
    report_tables = report_tables,
    methods_text = methods_text,
    checklist = checklist
  )
}


.gpbiom_report_overview <- function(data,
                                    workflow,
                                    derived,
                                    title,
                                    subtitle,
                                    include_timestamp) {
  schema_overview <- .gpbiom_first_data_frame(derived$schema, "overview")
  validity_overview <- .gpbiom_first_data_frame(derived$validity, "overview")
  workflow_overview <- .gpbiom_report_workflow_overview(workflow)

  n_rows <- if (!is.null(data)) nrow(data) else NA_integer_
  n_columns <- if (!is.null(data)) ncol(data) else NA_integer_

  if (!is.null(schema_overview) && "n_rows" %in% names(schema_overview)) {
    n_rows <- schema_overview$n_rows[1L]
  }

  if (!is.null(schema_overview) && "n_columns" %in% names(schema_overview)) {
    n_columns <- schema_overview$n_columns[1L]
  }

  active_signal_count <- NA_integer_

  if (!is.null(schema_overview) &&
      "active_signal_count" %in% names(schema_overview)) {
    active_signal_count <- schema_overview$active_signal_count[1L]
  } else if (!is.null(validity_overview) &&
             "active_signal_count" %in% names(validity_overview)) {
    active_signal_count <- validity_overview$active_signal_count[1L]
  }

  status <- .gpbiom_report_status(
    schema_overview = schema_overview,
    validity_overview = validity_overview,
    workflow_overview = workflow_overview
  )

  data.frame(
    title = title,
    subtitle = ifelse(is.null(subtitle), NA_character_, subtitle),
    created_at = if (isTRUE(include_timestamp)) {
      format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z")
    } else {
      NA_character_
    },
    n_rows = n_rows,
    n_columns = n_columns,
    active_signal_count = active_signal_count,
    has_data = !is.null(data),
    has_workflow = !is.null(workflow),
    has_methods_text = !is.null(derived$methods_text),
    has_checklist = !is.null(derived$checklist),
    table_count = length(.gpbiom_report_extract_tables(derived$report_tables)),
    status = status,
    stringsAsFactors = FALSE
  )
}


.gpbiom_report_status <- function(schema_overview,
                                  validity_overview,
                                  workflow_overview) {
  statuses <- character()

  if (!is.null(schema_overview) && "status" %in% names(schema_overview)) {
    statuses <- c(statuses, schema_overview$status[1L])
  }

  if (!is.null(validity_overview) && "status" %in% names(validity_overview)) {
    statuses <- c(statuses, validity_overview$status[1L])
  }

  if (!is.null(workflow_overview) && "status" %in% names(workflow_overview)) {
    statuses <- c(statuses, workflow_overview$status[1L])
  }

  if (length(statuses) == 0L) {
    return("report_created_without_diagnostic_status")
  }

  if (any(grepl("fail|error|no_", statuses, ignore.case = TRUE))) {
    return("report_created_with_readiness_concerns")
  }

  if (any(grepl("warn|issue|limited|insufficient|inactive",
                statuses, ignore.case = TRUE))) {
    return("report_created_with_cautions")
  }

  "report_created"
}


.gpbiom_report_workflow_overview <- function(workflow) {
  if (is.null(workflow)) {
    return(NULL)
  }

  if (is.data.frame(workflow)) {
    return(workflow)
  }

  if (is.list(workflow)) {
    direct <- .gpbiom_first_data_frame(workflow, "overview")

    if (!is.null(direct)) {
      return(direct)
    }

    summary_obj <- tryCatch(
      summarise_gazepoint_biometrics_workflow(workflow),
      error = function(e) NULL
    )

    if (is.data.frame(summary_obj)) {
      return(summary_obj)
    }

    if (is.list(summary_obj)) {
      summary_overview <- .gpbiom_first_data_frame(summary_obj, "overview")

      if (!is.null(summary_overview)) {
        return(summary_overview)
      }
    }
  }

  data.frame(
    status = "workflow_object_supplied",
    stringsAsFactors = FALSE
  )
}


.gpbiom_report_collect_tables <- function(derived, report_tables) {
  tables <- list()

  schema_overview <- .gpbiom_first_data_frame(derived$schema, "overview")
  schema_columns <- .gpbiom_first_data_frame(derived$schema, "columns")
  validity_signals <- .gpbiom_first_data_frame(derived$validity, "signals")
  validity_flags <- .gpbiom_first_data_frame(derived$validity, "validity_flags")
  workflow_overview <- .gpbiom_report_workflow_overview(derived$workflow)

  if (!is.null(schema_overview)) {
    tables$schema_overview <- schema_overview
  }

  if (!is.null(schema_columns)) {
    tables$schema_columns <- schema_columns
  }

  if (!is.null(validity_signals)) {
    tables$signal_validity <- validity_signals
  }

  if (!is.null(validity_flags)) {
    tables$validity_flags <- validity_flags
  }

  if (!is.null(workflow_overview)) {
    tables$workflow_overview <- workflow_overview
  }

  user_tables <- .gpbiom_report_extract_tables(report_tables)

  for (name in names(user_tables)) {
    tables[[name]] <- user_tables[[name]]
  }

  tables
}


.gpbiom_report_extract_tables <- function(x) {
  if (is.null(x)) {
    return(list())
  }

  if (is.data.frame(x)) {
    return(list(report_table = x))
  }

  if (is.list(x)) {
    tables <- x[vapply(x, is.data.frame, logical(1))]

    if (length(tables) == 0L) {
      return(list())
    }

    if (is.null(names(tables)) || any(!nzchar(names(tables)))) {
      names(tables) <- paste0("table_", seq_along(tables))
    }

    return(tables)
  }

  list()
}


.gpbiom_first_data_frame <- function(x, name = NULL) {
  if (is.null(x)) {
    return(NULL)
  }

  if (is.data.frame(x)) {
    return(x)
  }

  if (is.list(x) && !is.null(name) && name %in% names(x) &&
      is.data.frame(x[[name]])) {
    return(x[[name]])
  }

  if (is.list(x)) {
    data_frames <- x[vapply(x, is.data.frame, logical(1))]

    if (length(data_frames) > 0L) {
      return(data_frames[[1L]])
    }
  }

  NULL
}


.gpbiom_report_sections <- function(title,
                                    subtitle,
                                    overview,
                                    derived,
                                    tables,
                                    include_timestamp,
                                    max_table_rows) {
  methods_text <- .gpbiom_report_text_from_object(derived$methods_text)
  checklist_text <- .gpbiom_report_checklist_text(derived$checklist)

  sections <- list(
    title = c(
      paste0("# ", title),
      if (!is.null(subtitle)) paste0("\n", subtitle) else character(),
      if (isTRUE(include_timestamp)) {
        paste0("\nCreated: ", overview$created_at[1L])
      } else {
        character()
      }
    ),
    overview = c(
      "## Overview",
      .gpbiom_report_table_to_markdown(overview, max_rows = max_table_rows)
    ),
    signal_summary = c(
      "## Signal availability and schema",
      .gpbiom_report_signal_summary_text(derived),
      .gpbiom_report_optional_table(
        tables$signal_validity,
        max_rows = max_table_rows
      )
    ),
    quality_readiness = c(
      "## Quality and readiness",
      .gpbiom_report_quality_text(derived),
      .gpbiom_report_optional_table(
        .gpbiom_report_quality_table(derived),
        max_rows = max_table_rows
      )
    ),
    methods = c(
      "## Methods text",
      if (length(methods_text) > 0L) {
        methods_text
      } else {
        "_No methods text object was supplied._"
      }
    ),
    checklist = c(
      "## Reporting checklist",
      if (length(checklist_text) > 0L) {
        checklist_text
      } else {
        "_No checklist object was supplied._"
      }
    ),
    tables = c(
      "## Report tables",
      .gpbiom_report_all_tables_text(tables, max_rows = max_table_rows)
    ),
    cautions = c(
      "## Interpretation cautions",
      paste0("- ", .gpbiom_report_cautions())
    )
  )

  sections
}


.gpbiom_report_signal_summary_text <- function(derived) {
  schema_overview <- .gpbiom_first_data_frame(derived$schema, "overview")
  validity_overview <- .gpbiom_first_data_frame(derived$validity, "overview")

  if (is.null(schema_overview) && is.null(validity_overview)) {
    return("_No schema or signal-validity summary was available._")
  }

  lines <- character()

  if (!is.null(schema_overview)) {
    if ("active_signal_count" %in% names(schema_overview)) {
      lines <- c(
        lines,
        paste0(
          "- Active signal groups detected: ",
          schema_overview$active_signal_count[1L],
          "."
        )
      )
    }

    flags <- c(
      gsr_eda = "has_gsr_eda",
      heart_rate = "has_heart_rate",
      ibi = "has_ibi",
      engagement_dial = "has_engagement_dial",
      ttl_marker = "has_ttl_marker"
    )

    present <- names(flags)[vapply(flags, function(column) {
      column %in% names(schema_overview) && isTRUE(schema_overview[[column]][1L])
    }, logical(1))]

    if (length(present) > 0L) {
      lines <- c(lines, paste0("- Present channels: ",
                               paste(present, collapse = ", "), "."))
    }
  }

  if (!is.null(validity_overview) && "status" %in% names(validity_overview)) {
    lines <- c(lines, paste0("- Validity status: ",
                             validity_overview$status[1L], "."))
  }

  if (length(lines) == 0L) {
    lines <- "_Schema object was supplied but did not contain standard overview fields._"
  }

  lines
}


.gpbiom_report_quality_text <- function(derived) {
  objects <- list(
    validation = derived$validation,
    quality = derived$quality,
    sampling = derived$sampling,
    missingness = derived$missingness,
    exclusions = derived$exclusions
  )

  present <- names(objects)[!vapply(objects, is.null, logical(1))]

  if (length(present) == 0L) {
    return("_No separate validation, quality, sampling, missingness, or exclusion object was supplied._")
  }

  paste0("- Supplied quality/readiness objects: ", paste(present, collapse = ", "), ".")
}


.gpbiom_report_quality_table <- function(derived) {
  objects <- list(
    validation = derived$validation,
    quality = derived$quality,
    sampling = derived$sampling,
    missingness = derived$missingness,
    exclusions = derived$exclusions
  )

  rows <- lapply(names(objects), function(name) {
    object <- objects[[name]]

    if (is.null(object)) {
      return(NULL)
    }

    table <- .gpbiom_first_data_frame(object, "overview")

    status <- NA_character_
    n_rows <- NA_integer_

    if (!is.null(table)) {
      n_rows <- nrow(table)

      if ("status" %in% names(table)) {
        status <- as.character(table$status[1L])
      } else if ("final_status" %in% names(table)) {
        status <- as.character(table$final_status[1L])
      }
    }

    data.frame(
      object = name,
      table_rows = n_rows,
      status = status,
      stringsAsFactors = FALSE
    )
  })

  rows <- Filter(Negate(is.null), rows)

  if (length(rows) == 0L) {
    return(NULL)
  }

  do.call(rbind, rows)
}


.gpbiom_report_text_from_object <- function(x) {
  if (is.null(x)) {
    return(character())
  }

  if (is.character(x)) {
    return(x)
  }

  if (is.data.frame(x)) {
    return(.gpbiom_report_table_to_markdown(x, max_rows = nrow(x)))
  }

  if (is.list(x)) {
    character_items <- unlist(x[vapply(x, is.character, logical(1))],
                              use.names = FALSE)

    if (length(character_items) > 0L) {
      return(character_items)
    }

    table <- .gpbiom_first_data_frame(x)

    if (!is.null(table)) {
      return(.gpbiom_report_table_to_markdown(table, max_rows = nrow(table)))
    }
  }

  as.character(utils::capture.output(utils::str(x)))
}


.gpbiom_report_checklist_text <- function(checklist) {
  if (is.null(checklist)) {
    return(character())
  }

  if (is.character(checklist)) {
    return(checklist)
  }

  table <- .gpbiom_first_data_frame(checklist, "checklist")

  if (is.null(table)) {
    table <- .gpbiom_first_data_frame(checklist)
  }

  if (!is.null(table)) {
    return(.gpbiom_report_table_to_markdown(table, max_rows = nrow(table)))
  }

  as.character(utils::capture.output(utils::str(checklist)))
}


.gpbiom_report_optional_table <- function(table, max_rows) {
  if (is.null(table) || !is.data.frame(table) || nrow(table) == 0L) {
    return("_No table available._")
  }

  .gpbiom_report_table_to_markdown(table, max_rows = max_rows)
}


.gpbiom_report_all_tables_text <- function(tables, max_rows) {
  if (length(tables) == 0L) {
    return("_No report tables were available._")
  }

  lines <- character()

  for (name in names(tables)) {
    lines <- c(
      lines,
      paste0("### ", name),
      .gpbiom_report_table_to_markdown(tables[[name]], max_rows = max_rows),
      ""
    )
  }

  lines
}


.gpbiom_report_table_to_markdown <- function(table, max_rows = 20L) {
  if (is.null(table) || !is.data.frame(table)) {
    return("_No table available._")
  }

  if (nrow(table) == 0L) {
    return("_Table has no rows._")
  }

  shown <- utils::head(table, max_rows)
  shown[] <- lapply(shown, .gpbiom_report_cell)

  header <- paste0("| ", paste(names(shown), collapse = " | "), " |")
  separator <- paste0("| ", paste(rep("---", ncol(shown)), collapse = " | "), " |")

  rows <- apply(shown, 1L, function(row) {
    paste0("| ", paste(row, collapse = " | "), " |")
  })

  footer <- if (nrow(table) > max_rows) {
    paste0("\n_Showing ", max_rows, " of ", nrow(table), " rows._")
  } else {
    character()
  }

  c(header, separator, rows, footer)
}


.gpbiom_report_cell <- function(x) {
  out <- as.character(x)
  out[is.na(out)] <- ""
  out <- gsub("\\|", "\\\\|", out)
  out <- gsub("\r?\n", " ", out)
  out
}


.gpbiom_report_render <- function(sections, format) {
  markdown <- unlist(sections, use.names = FALSE)
  markdown <- markdown[nzchar(markdown)]

  if (identical(format, "markdown")) {
    return(markdown)
  }

  escaped <- .gpbiom_html_escape(markdown)

  c(
    "<!doctype html>",
    "<html>",
    "<head>",
    "<meta charset=\"utf-8\">",
    "<title>Gazepoint Biometrics report</title>",
    "</head>",
    "<body>",
    "<pre>",
    escaped,
    "</pre>",
    "</body>",
    "</html>"
  )
}


.gpbiom_html_escape <- function(x) {
  x <- gsub("&", "&amp;", x, fixed = TRUE)
  x <- gsub("<", "&lt;", x, fixed = TRUE)
  x <- gsub(">", "&gt;", x, fixed = TRUE)
  x
}


.gpbiom_report_cautions <- function() {
  c(
    "GSR/EDA should be interpreted as electrodermal activity or arousal-related signal, not emotional valence.",
    "Heart-rate summaries require baseline, task, and artefact context before substantive interpretation.",
    "Raw HRV columns in Gazepoint exports should be treated as validity/vendor flags unless documentation proves otherwise.",
    "IBI-derived HRV-style metrics should be computed only from genuine IBI/RR interval columns.",
    "Eye-tracking measures indicate visual attention and do not directly establish deeper cognition, scrutiny, or evaluation."
  )
}
