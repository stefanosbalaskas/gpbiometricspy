#' Create a Gazepoint pipeline map
#'
#' Creates a lightweight tabular representation of a Gazepoint analysis pipeline.
#' The output contains workflow nodes and directed edges that can be audited or
#' exported as DOT/Graphviz text. This function is intended for documentation,
#' reporting, and reproducibility only.
#'
#' @param steps Optional data frame of pipeline steps. Required column:
#'   \code{step_id}. Optional columns include \code{label}, \code{domain},
#'   \code{description}, \code{expected_order}, \code{required}, \code{status},
#'   and \code{notes}. If \code{NULL}, a conservative default workflow is used.
#' @param edges Optional data frame of directed edges with columns \code{from}
#'   and \code{to}. Optional columns include \code{edge_type},
#'   \code{description}, and \code{required}. If \code{NULL}, sequential edges
#'   are created from the step order.
#' @param pipeline_id Optional pipeline identifier.
#' @param include_default Logical. If \code{TRUE} and \code{steps = NULL}, the
#'   default Gazepoint pipeline steps are used.
#'
#' @return A list with class \code{gazepoint_pipeline_map}.
#' @export
create_gazepoint_pipeline_map <- function(steps = NULL,
                                          edges = NULL,
                                          pipeline_id = NULL,
                                          include_default = TRUE) {
  gppl_check_logical_one(include_default, "include_default")
  pipeline_id <- gppl_optional_scalar_character(pipeline_id, "pipeline_id")

  if (is.null(steps)) {
    if (!include_default) {
      stop("`steps` must be supplied when `include_default = FALSE`.", call. = FALSE)
    }

    nodes <- gppl_default_pipeline_steps()
  } else {
    nodes <- gppl_normalize_steps(steps)
  }

  if (is.null(edges)) {
    edges <- gppl_make_sequential_edges(nodes)
  } else {
    edges <- gppl_normalize_edges(edges, nodes)
  }

  summary <- gppl_pipeline_summary(nodes, edges)

  out <- list(
    pipeline_id = gppl_value_or_blank(pipeline_id),
    nodes = nodes,
    edges = edges,
    summary = summary,
    parameters = list(
      include_default = include_default,
      custom_steps = !is.null(steps),
      custom_edges = !is.null(edges)
    )
  )

  class(out) <- c("gazepoint_pipeline_map", "list")
  out
}

#' Audit Gazepoint pipeline steps
#'
#' Checks a pipeline map for missing expected steps, duplicate step identifiers,
#' edge references to missing nodes, and simple ordering violations. The audit is
#' descriptive and does not evaluate whether a scientific analysis is valid.
#'
#' @param pipeline A \code{gazepoint_pipeline_map} object or a data frame of
#'   pipeline steps.
#' @param expected_steps Optional character vector of step identifiers expected
#'   in the pipeline. If \code{NULL}, required steps in the pipeline map are used.
#' @param required_order Optional character vector describing the expected order
#'   of selected steps. If \code{NULL}, the order implied by
#'   \code{expected_order} is used when available.
#' @param allow_extra Logical. If \code{FALSE}, steps not listed in
#'   \code{expected_steps} are reported as warnings.
#'
#' @return A list with class \code{gazepoint_pipeline_audit}.
#' @export
audit_gazepoint_pipeline_steps <- function(pipeline,
                                           expected_steps = NULL,
                                           required_order = NULL,
                                           allow_extra = TRUE) {
  gppl_check_logical_one(allow_extra, "allow_extra")

  map <- gppl_as_pipeline_map(pipeline)
  nodes <- map$nodes
  edges <- map$edges

  expected_steps <- gppl_optional_character(expected_steps, "expected_steps")
  required_order <- gppl_optional_character(required_order, "required_order")

  if (is.null(expected_steps)) {
    expected_steps <- nodes$step_id[isTRUE(length(nodes$required) > 0) & nodes$required]
  }

  if (is.null(required_order) && "expected_order" %in% names(nodes)) {
    ord_nodes <- nodes[
      !is.na(nodes$expected_order),
      ,
      drop = FALSE
    ]
    ord_nodes <- ord_nodes[order(ord_nodes$expected_order), , drop = FALSE]
    required_order <- ord_nodes$step_id
  }

  checks <- list(
    duplicates = gppl_check_duplicate_steps(nodes),
    expected = gppl_check_expected_steps(nodes, expected_steps),
    extras = gppl_check_extra_steps(nodes, expected_steps, allow_extra),
    edge_references = gppl_check_edge_references(nodes, edges),
    ordering = gppl_check_required_order(nodes, required_order)
  )

  results <- do.call(rbind, checks)
  rownames(results) <- NULL

  summary <- data.frame(
    n_steps = nrow(nodes),
    n_edges = nrow(edges),
    n_pass = sum(results$status == "pass", na.rm = TRUE),
    n_warn = sum(results$status == "warn", na.rm = TRUE),
    n_fail = sum(results$status == "fail", na.rm = TRUE),
    n_not_checked = sum(results$status == "not_checked", na.rm = TRUE),
    audit_pass = !any(results$status == "fail", na.rm = TRUE),
    stringsAsFactors = FALSE
  )

  out <- list(
    pipeline_id = map$pipeline_id,
    checks = results,
    summary = summary,
    parameters = list(
      expected_steps = expected_steps,
      required_order = required_order,
      allow_extra = allow_extra
    )
  )

  class(out) <- c("gazepoint_pipeline_audit", "list")
  out
}

#' Export a Gazepoint pipeline map as DOT text
#'
#' Converts a Gazepoint pipeline map to a lightweight DOT/Graphviz character
#' string. The DOT text can be copied into external graph-rendering tools. This
#' function does not require Graphviz, DiagrammeR, or any rendering dependency.
#'
#' @param pipeline A \code{gazepoint_pipeline_map} object or a data frame of
#'   pipeline steps.
#' @param file Optional file path. If supplied, the DOT text is written to disk.
#' @param graph_name DOT graph name.
#' @param rankdir Graph direction. Common values are \code{"LR"} and \code{"TB"}.
#' @param include_descriptions Logical. If \code{TRUE}, node descriptions are
#'   included in DOT labels.
#'
#' @return A single character string containing DOT text.
#' @export
export_gazepoint_pipeline_dot <- function(pipeline,
                                          file = NULL,
                                          graph_name = "gazepoint_pipeline",
                                          rankdir = "LR",
                                          include_descriptions = FALSE) {
  map <- gppl_as_pipeline_map(pipeline)

  file <- gppl_optional_scalar_character(file, "file")
  graph_name <- gppl_required_scalar_character(graph_name, "graph_name")
  rankdir <- gppl_required_scalar_character(rankdir, "rankdir")
  gppl_check_logical_one(include_descriptions, "include_descriptions")

  nodes <- map$nodes
  edges <- map$edges

  node_lines <- vapply(seq_len(nrow(nodes)), function(i) {
    id <- gppl_dot_id(nodes$step_id[i])
    label <- nodes$label[i]

    if (include_descriptions && "description" %in% names(nodes)) {
      description <- nodes$description[i]
      if (!is.na(description) && nzchar(description)) {
        label <- paste0(label, "\\n", description)
      }
    }

    paste0("  ", id, " [label=\"", gppl_escape_dot(label), "\"];")
  }, character(1))

  edge_lines <- character(0)

  if (nrow(edges) > 0) {
    edge_lines <- vapply(seq_len(nrow(edges)), function(i) {
      paste0(
        "  ",
        gppl_dot_id(edges$from[i]),
        " -> ",
        gppl_dot_id(edges$to[i]),
        ";"
      )
    }, character(1))
  }

  lines <- c(
    paste0("digraph ", gppl_dot_id(graph_name), " {"),
    paste0("  graph [rankdir=\"", gppl_escape_dot(rankdir), "\"];"),
    "  node [shape=box];",
    node_lines,
    edge_lines,
    "}"
  )

  dot <- paste(lines, collapse = "\n")

  if (!is.null(file)) {
    writeLines(dot, file, useBytes = TRUE)
  }

  dot
}

gppl_default_pipeline_steps <- function() {
  data.frame(
    step_id = c(
      "import",
      "metadata_validation",
      "dataset_inventory",
      "quality_control",
      "preprocessing",
      "event_alignment",
      "feature_extraction",
      "analysis_ready_data",
      "model_preparation",
      "reporting"
    ),
    label = c(
      "Import exports",
      "Validate metadata",
      "Inventory files",
      "Quality control",
      "Preprocess signals",
      "Align events",
      "Extract features",
      "Prepare analysis data",
      "Prepare models",
      "Report audit trail"
    ),
    domain = c(
      "data_io",
      "metadata",
      "metadata",
      "qc",
      "preprocessing",
      "synchronization",
      "features",
      "analysis",
      "analysis",
      "reporting"
    ),
    description = c(
      "Read Gazepoint export files into R.",
      "Check required columns and naming assumptions.",
      "Summarize export files and sidecar coverage.",
      "Flag missingness, dropouts, artifacts, and signal-quality issues.",
      "Apply documented cleaning or transformation steps.",
      "Align events, TTL markers, or task windows.",
      "Compute descriptive biometric, gaze, pupil, or event-derived features.",
      "Create analysis-ready tables without changing interpretation.",
      "Prepare model inputs and documented sensitivity checks.",
      "Summarize checks, decisions, and reproducibility metadata."
    ),
    expected_order = seq_len(10),
    required = TRUE,
    status = "planned",
    notes = "",
    stringsAsFactors = FALSE
  )
}

gppl_normalize_steps <- function(steps) {
  if (!is.data.frame(steps)) {
    stop("`steps` must be a data frame.", call. = FALSE)
  }

  if (!"step_id" %in% names(steps)) {
    stop("`steps` must contain a `step_id` column.", call. = FALSE)
  }

  out <- steps
  out$step_id <- as.character(out$step_id)

  if (any(is.na(out$step_id)) || any(!nzchar(out$step_id))) {
    stop("`steps$step_id` must contain non-empty values.", call. = FALSE)
  }

  if (any(duplicated(out$step_id))) {
    stop("`steps$step_id` must be unique.", call. = FALSE)
  }

  if (!"label" %in% names(out)) {
    out$label <- out$step_id
  }

  if (!"domain" %in% names(out)) {
    out$domain <- "unspecified"
  }

  if (!"description" %in% names(out)) {
    out$description <- ""
  }

  if (!"expected_order" %in% names(out)) {
    out$expected_order <- seq_len(nrow(out))
  }

  if (!"required" %in% names(out)) {
    out$required <- TRUE
  }

  if (!"status" %in% names(out)) {
    out$status <- "planned"
  }

  if (!"notes" %in% names(out)) {
    out$notes <- ""
  }

  out <- out[
    ,
    c(
      "step_id",
      "label",
      "domain",
      "description",
      "expected_order",
      "required",
      "status",
      "notes"
    ),
    drop = FALSE
  ]

  out$label <- as.character(out$label)
  out$domain <- as.character(out$domain)
  out$description <- as.character(out$description)
  out$expected_order <- suppressWarnings(as.numeric(out$expected_order))
  out$required <- as.logical(out$required)
  out$status <- as.character(out$status)
  out$notes <- as.character(out$notes)

  if (any(is.na(out$required))) {
    stop("`steps$required` must contain TRUE or FALSE values.", call. = FALSE)
  }

  rownames(out) <- NULL
  out
}

gppl_make_sequential_edges <- function(nodes) {
  if (nrow(nodes) <= 1) {
    return(data.frame(
      from = character(0),
      to = character(0),
      edge_type = character(0),
      description = character(0),
      required = logical(0),
      stringsAsFactors = FALSE
    ))
  }

  ordered <- nodes[order(nodes$expected_order), , drop = FALSE]

  data.frame(
    from = ordered$step_id[-nrow(ordered)],
    to = ordered$step_id[-1],
    edge_type = "sequential",
    description = "Default sequential workflow edge.",
    required = TRUE,
    stringsAsFactors = FALSE
  )
}

gppl_normalize_edges <- function(edges, nodes) {
  if (!is.data.frame(edges)) {
    stop("`edges` must be a data frame.", call. = FALSE)
  }

  missing_cols <- setdiff(c("from", "to"), names(edges))

  if (length(missing_cols) > 0) {
    stop(
      "`edges` is missing required column(s): ",
      paste(missing_cols, collapse = ", "),
      call. = FALSE
    )
  }

  out <- edges
  out$from <- as.character(out$from)
  out$to <- as.character(out$to)

  if (any(is.na(out$from)) || any(!nzchar(out$from)) ||
      any(is.na(out$to)) || any(!nzchar(out$to))) {
    stop("`edges$from` and `edges$to` must contain non-empty values.", call. = FALSE)
  }

  unknown <- setdiff(unique(c(out$from, out$to)), nodes$step_id)

  if (length(unknown) > 0) {
    stop(
      "`edges` refers to unknown step_id value(s): ",
      paste(unknown, collapse = ", "),
      call. = FALSE
    )
  }

  if (!"edge_type" %in% names(out)) {
    out$edge_type <- "sequential"
  }

  if (!"description" %in% names(out)) {
    out$description <- ""
  }

  if (!"required" %in% names(out)) {
    out$required <- TRUE
  }

  out <- out[, c("from", "to", "edge_type", "description", "required"), drop = FALSE]
  out$edge_type <- as.character(out$edge_type)
  out$description <- as.character(out$description)
  out$required <- as.logical(out$required)

  if (any(is.na(out$required))) {
    stop("`edges$required` must contain TRUE or FALSE values.", call. = FALSE)
  }

  rownames(out) <- NULL
  out
}

gppl_pipeline_summary <- function(nodes, edges) {
  data.frame(
    n_steps = nrow(nodes),
    n_edges = nrow(edges),
    n_required_steps = sum(nodes$required, na.rm = TRUE),
    n_optional_steps = sum(!nodes$required, na.rm = TRUE),
    n_domains = length(unique(nodes$domain)),
    stringsAsFactors = FALSE
  )
}

gppl_as_pipeline_map <- function(pipeline) {
  if (inherits(pipeline, "gazepoint_pipeline_map")) {
    return(pipeline)
  }

  if (is.data.frame(pipeline)) {
    return(create_gazepoint_pipeline_map(steps = pipeline, include_default = FALSE))
  }

  stop("`pipeline` must be a gazepoint_pipeline_map object or a steps data frame.", call. = FALSE)
}

gppl_issue_frame <- function(check, item, status, message) {
  data.frame(
    check = check,
    item = item,
    status = status,
    message = message,
    stringsAsFactors = FALSE
  )
}

gppl_check_duplicate_steps <- function(nodes) {
  duplicated_steps <- unique(nodes$step_id[duplicated(nodes$step_id)])

  if (length(duplicated_steps) == 0) {
    return(gppl_issue_frame("duplicate_steps", NA_character_, "pass", "No duplicate step identifiers were found."))
  }

  rows <- lapply(duplicated_steps, function(step) {
    gppl_issue_frame("duplicate_steps", step, "fail", "Duplicate step identifier found.")
  })

  do.call(rbind, rows)
}

gppl_check_expected_steps <- function(nodes, expected_steps) {
  if (is.null(expected_steps) || length(expected_steps) == 0) {
    return(gppl_issue_frame("expected_steps", NA_character_, "not_checked", "No expected steps supplied."))
  }

  missing <- setdiff(expected_steps, nodes$step_id)

  if (length(missing) == 0) {
    return(gppl_issue_frame("expected_steps", NA_character_, "pass", "All expected steps were present."))
  }

  rows <- lapply(missing, function(step) {
    gppl_issue_frame("expected_steps", step, "fail", "Expected pipeline step is missing.")
  })

  do.call(rbind, rows)
}

gppl_check_extra_steps <- function(nodes, expected_steps, allow_extra) {
  if (allow_extra) {
    return(gppl_issue_frame("extra_steps", NA_character_, "not_checked", "Extra steps were allowed."))
  }

  if (is.null(expected_steps) || length(expected_steps) == 0) {
    return(gppl_issue_frame("extra_steps", NA_character_, "not_checked", "No expected steps supplied."))
  }

  extra <- setdiff(nodes$step_id, expected_steps)

  if (length(extra) == 0) {
    return(gppl_issue_frame("extra_steps", NA_character_, "pass", "No extra steps were found."))
  }

  rows <- lapply(extra, function(step) {
    gppl_issue_frame("extra_steps", step, "warn", "Pipeline step was not listed in expected_steps.")
  })

  do.call(rbind, rows)
}

gppl_check_edge_references <- function(nodes, edges) {
  if (nrow(edges) == 0) {
    return(gppl_issue_frame("edge_references", NA_character_, "not_checked", "No edges were supplied."))
  }

  unknown <- setdiff(unique(c(edges$from, edges$to)), nodes$step_id)

  if (length(unknown) == 0) {
    return(gppl_issue_frame("edge_references", NA_character_, "pass", "All edges refer to known steps."))
  }

  rows <- lapply(unknown, function(step) {
    gppl_issue_frame("edge_references", step, "fail", "Edge refers to an unknown step.")
  })

  do.call(rbind, rows)
}

gppl_check_required_order <- function(nodes, required_order) {
  if (is.null(required_order) || length(required_order) <= 1) {
    return(gppl_issue_frame("ordering", NA_character_, "not_checked", "No required order supplied."))
  }

  present <- required_order[required_order %in% nodes$step_id]

  if (length(present) <= 1) {
    return(gppl_issue_frame("ordering", NA_character_, "not_checked", "Fewer than two ordered steps were present."))
  }

  pos <- match(present, nodes$step_id)
  violations <- which(diff(pos) < 0)

  if (length(violations) == 0) {
    return(gppl_issue_frame("ordering", NA_character_, "pass", "Required step order was preserved."))
  }

  rows <- lapply(violations, function(i) {
    gppl_issue_frame(
      "ordering",
      paste(present[i], "before", present[i + 1]),
      "warn",
      "Required order was not preserved in the supplied node order."
    )
  })

  do.call(rbind, rows)
}

gppl_optional_character <- function(x, name) {
  if (is.null(x)) {
    return(NULL)
  }

  if (!is.character(x) || any(is.na(x))) {
    stop("`", name, "` must be NULL or a character vector.", call. = FALSE)
  }

  x[nzchar(x)]
}

gppl_optional_scalar_character <- function(x, name) {
  if (is.null(x)) {
    return(NULL)
  }

  gppl_required_scalar_character(x, name)
}

gppl_required_scalar_character <- function(x, name) {
  if (!is.character(x) || length(x) != 1 || is.na(x) || !nzchar(x)) {
    stop("`", name, "` must be a single non-empty character string.", call. = FALSE)
  }

  x
}

gppl_check_logical_one <- function(x, name) {
  if (!is.logical(x) || length(x) != 1 || is.na(x)) {
    stop("`", name, "` must be TRUE or FALSE.", call. = FALSE)
  }

  invisible(TRUE)
}

gppl_value_or_blank <- function(x) {
  if (is.null(x)) {
    ""
  } else {
    x
  }
}

gppl_dot_id <- function(x) {
  x <- as.character(x)
  x <- gsub("[^A-Za-z0-9_]", "_", x)
  x <- gsub("_+", "_", x)

  if (!grepl("^[A-Za-z_]", x)) {
    x <- paste0("n_", x)
  }

  x
}

gppl_escape_dot <- function(x) {
  x <- as.character(x)
  x <- gsub("\\\\", "\\\\\\\\", x)
  x <- gsub("\"", "\\\\\"", x)
  x <- gsub("\r", "", x, fixed = TRUE)
  x <- gsub("\n", "\\\\n", x, fixed = TRUE)
  x
}
