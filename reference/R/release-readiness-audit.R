#' Audit gpbiometrics release readiness
#'
#' Performs conservative package-level checks for release preparation. The audit
#' inspects package files, exported functions, manual pages, tests, pkgdown
#' reference pages, vignettes/articles, and optional roadmap terms. It does not
#' inspect participant-level data and does not make biometric, psychological,
#' clinical, or diagnostic interpretations.
#'
#' @param path Package root.
#' @param required_files Character vector of required package paths.
#' @param expected_exports Optional character vector of exported function names
#'   expected to be present in `NAMESPACE`.
#' @param roadmap_terms Optional character vector of roadmap terms or helper
#'   names to check across R files, tests, documentation, and pkgdown output.
#' @param require_pkgdown Logical. If `TRUE`, missing pkgdown reference pages for
#'   exported functions are warnings. If `FALSE`, they are recorded as
#'   not-checked.
#'
#' @return A list with checks, overview, exports, feature coverage, release
#'   checklist, and settings. The object has class
#'   `gazepoint_release_readiness_audit`.
#' @export
audit_gazepoint_release_readiness <- function(path = ".",
                                              required_files = c(
                                                "DESCRIPTION",
                                                "NAMESPACE",
                                                "R",
                                                "man",
                                                "tests/testthat",
                                                "_pkgdown.yml"
                                              ),
                                              expected_exports = NULL,
                                              roadmap_terms = NULL,
                                              require_pkgdown = TRUE) {
  path <- .gp_rra_path(path)
  required_files <- .gp_rra_character(required_files, "required_files", allow_null = FALSE)
  expected_exports <- .gp_rra_character(expected_exports, "expected_exports", allow_null = TRUE)
  roadmap_terms <- .gp_rra_character(roadmap_terms, "roadmap_terms", allow_null = TRUE)
  .gp_rra_logical_one(require_pkgdown, "require_pkgdown")

  description <- .gp_rra_read_description(path)
  exports <- .gp_rra_read_exports(path)
  r_files <- .gp_rra_files(path, "R", pattern = "\\.R$")
  test_files <- .gp_rra_files(path, file.path("tests", "testthat"), pattern = "\\.R$")
  man_files <- .gp_rra_files(path, "man", pattern = "\\.Rd$")
  vignette_files <- c(
    .gp_rra_files(path, "vignettes", pattern = "\\.(Rmd|qmd)$"),
    .gp_rra_files(path, file.path("docs", "articles"), pattern = "\\.(html|md)$")
  )

  checks <- list(
    .gp_rra_required_file_checks(path, required_files),
    .gp_rra_description_checks(description),
    .gp_rra_export_checks(exports, expected_exports),
    .gp_rra_test_checks(exports, test_files),
    .gp_rra_man_checks(path, exports, man_files),
    .gp_rra_pkgdown_checks(path, exports, require_pkgdown),
    .gp_rra_vignette_checks(vignette_files),
    .gp_rra_roadmap_checks(path, roadmap_terms)
  )

  checks <- do.call(rbind, checks)
  rownames(checks) <- NULL

  overview <- .gp_rra_overview(checks)
  feature_coverage <- summarize_gazepoint_feature_coverage(path = path, exports = exports)
  checklist <- create_gazepoint_release_checklist(audit = checks)

  out <- list(
    overview = overview,
    checks = checks,
    exports = exports,
    feature_coverage = feature_coverage,
    checklist = checklist,
    settings = list(
      path = path,
      required_files = required_files,
      expected_exports = expected_exports,
      roadmap_terms = roadmap_terms,
      require_pkgdown = require_pkgdown
    )
  )

  class(out) <- c("gazepoint_release_readiness_audit", "gazepoint_qc_object", "list")
  out
}

#' Summarize gpbiometrics feature coverage
#'
#' Creates a descriptive feature-coverage table from exported function names.
#' Domains are assigned using transparent name patterns. The summary is intended
#' for release review and documentation planning only.
#'
#' @param path Package root.
#' @param exports Optional character vector of exported functions. If `NULL`,
#'   exports are read from `NAMESPACE`.
#' @param patterns Optional named list of regular-expression patterns used to
#'   assign exported functions to domains.
#'
#' @return A data frame with one row per domain.
#' @export
summarize_gazepoint_feature_coverage <- function(path = ".",
                                                 exports = NULL,
                                                 patterns = NULL) {
  path <- .gp_rra_path(path)

  if (is.null(exports)) {
    exports <- .gp_rra_read_exports(path)
  } else {
    exports <- .gp_rra_character(exports, "exports", allow_null = FALSE)
  }

  if (is.null(patterns)) {
    patterns <- .gp_rra_default_feature_patterns()
  }

  pattern_names <- names(patterns)

  if (!is.list(patterns) || is.null(pattern_names) ||
    length(pattern_names) != length(patterns) ||
    any(is.na(pattern_names)) || any(!nzchar(pattern_names))) {
    stop("`patterns` must be a named list of regular-expression patterns.", call. = FALSE)
  }

  bad_patterns <- vapply(patterns, function(pattern) {
    !is.character(pattern) || length(pattern) != 1 || is.na(pattern) || !nzchar(pattern)
  }, logical(1))

  if (any(bad_patterns)) {
    stop("Each pattern must be a single non-empty character string.", call. = FALSE)
  }

  if (!length(exports)) {
    out <- data.frame(
      domain = names(patterns),
      n_exports = integer(length(patterns)),
      examples = rep(NA_character_, length(patterns)),
      stringsAsFactors = FALSE
    )
    class(out) <- c("gazepoint_feature_coverage", class(out))
    return(out)
  }

  rows <- lapply(names(patterns), function(domain) {
    pattern <- patterns[[domain]]

    hits <- exports[grepl(pattern, exports, ignore.case = TRUE)]

    data.frame(
      domain = domain,
      n_exports = length(hits),
      examples = if (length(hits)) paste(utils::head(hits, 6), collapse = ", ") else NA_character_,
      stringsAsFactors = FALSE
    )
  })

  out <- do.call(rbind, rows)
  rownames(out) <- NULL
  class(out) <- c("gazepoint_feature_coverage", class(out))
  out
}

#' Create a gpbiometrics release checklist
#'
#' Creates a conservative release checklist. If an audit table is supplied, each
#' checklist item is linked to the current audit status. The checklist is meant
#' to support human review before tagging or submission.
#'
#' @param audit Optional audit data frame or `gazepoint_release_readiness_audit`
#'   object.
#' @param include_optional Logical. If `TRUE`, optional release-polish items are
#'   included.
#'
#' @return A data frame with release checklist items.
#' @export
create_gazepoint_release_checklist <- function(audit = NULL,
                                               include_optional = TRUE) {
  .gp_rra_logical_one(include_optional, "include_optional")

  items <- data.frame(
    phase = c(
      "package", "package", "package", "tests", "tests",
      "documentation", "documentation", "documentation",
      "pkgdown", "reproducibility", "scope"
    ),
    item = c(
      "DESCRIPTION is present and parseable",
      "NAMESPACE is present and contains exports",
      "R source files are present",
      "testthat directory is present",
      "exported helpers have at least heuristic test references",
      "manual pages exist for exported helpers",
      "vignettes or pkgdown articles are present",
      "NEWS/README/ROADMAP materials are reviewed manually",
      "pkgdown reference pages are current",
      "urlchecker and R CMD check are run before release",
      "no unsupported biometric, clinical, diagnostic, or psychological claims are introduced"
    ),
    required = c(TRUE, TRUE, TRUE, TRUE, FALSE, TRUE, FALSE, FALSE, FALSE, TRUE, TRUE),
    stringsAsFactors = FALSE
  )

  if (isTRUE(include_optional)) {
    items <- rbind(
      items,
      data.frame(
        phase = c("release", "release", "release"),
        item = c(
          "GitHub Actions are checked after push",
          "pkgdown site is rebuilt after reference changes",
          "release notes are checked against exported functions"
        ),
        required = c(FALSE, FALSE, FALSE),
        stringsAsFactors = FALSE
      )
    )
  }

  audit_checks <- .gp_rra_extract_audit_checks(audit)

  if (is.null(audit_checks) || !nrow(audit_checks)) {
    items$status <- "not_checked"
    items$evidence <- NA_character_
  } else {
    mapped <- lapply(seq_len(nrow(items)), function(i) {
      .gp_rra_map_checklist_item(items$phase[i], items$item[i], audit_checks)
    })

    items$status <- vapply(mapped, `[[`, character(1), "status")
    items$evidence <- vapply(mapped, `[[`, character(1), "evidence")
  }

  class(items) <- c("gazepoint_release_checklist", class(items))
  items
}

.gp_rra_required_file_checks <- function(path, required_files) {
  rows <- lapply(required_files, function(x) {
    exists <- file.exists(file.path(path, x))
    .gp_rra_row(
      area = "package_structure",
      check = "required_path",
      item = x,
      status = if (exists) "pass" else "fail",
      message = if (exists) "Required path is present." else "Required path is missing."
    )
  })

  do.call(rbind, rows)
}

.gp_rra_description_checks <- function(description) {
  if (is.null(description)) {
    return(.gp_rra_row(
      area = "description",
      check = "parse_description",
      item = "DESCRIPTION",
      status = "fail",
      message = "DESCRIPTION could not be parsed."
    ))
  }

  fields <- c("Package", "Title", "Version", "Description", "License")
  rows <- lapply(fields, function(field) {
    ok <- field %in% names(description) && nzchar(description[[field]][1])
    .gp_rra_row(
      area = "description",
      check = "required_field",
      item = field,
      status = if (ok) "pass" else "warn",
      message = if (ok) "DESCRIPTION field is present." else "DESCRIPTION field is missing or empty."
    )
  })

  do.call(rbind, rows)
}

.gp_rra_export_checks <- function(exports, expected_exports) {
  rows <- list(
    .gp_rra_row(
      area = "namespace",
      check = "exports_present",
      item = "NAMESPACE",
      status = if (length(exports)) "pass" else "fail",
      message = paste0(length(exports), " exported function(s) detected.")
    )
  )

  if (!is.null(expected_exports)) {
    missing <- setdiff(expected_exports, exports)

    rows[[length(rows) + 1]] <- .gp_rra_row(
      area = "namespace",
      check = "expected_exports",
      item = "expected_exports",
      status = if (length(missing)) "fail" else "pass",
      message = if (length(missing)) {
        paste("Missing expected export(s):", paste(missing, collapse = ", "))
      } else {
        "All expected exports were found."
      }
    )
  }

  do.call(rbind, rows)
}

.gp_rra_test_checks <- function(exports, test_files) {
  rows <- list(
    .gp_rra_row(
      area = "tests",
      check = "test_files_present",
      item = "tests/testthat",
      status = if (length(test_files)) "pass" else "warn",
      message = paste0(length(test_files), " test file(s) detected.")
    )
  )

  if (!length(exports)) {
    rows[[length(rows) + 1]] <- .gp_rra_row(
      area = "tests",
      check = "export_test_references",
      item = "exports",
      status = "not_checked",
      message = "No exports were available for heuristic test-reference checks."
    )
    return(do.call(rbind, rows))
  }

  test_text <- .gp_rra_read_many(test_files)
  referenced <- vapply(exports, function(fn) {
    any(grepl(fn, test_text, fixed = TRUE))
  }, logical(1))

  missing_refs <- exports[!referenced]
  status <- if (length(test_files) == 0) "not_checked" else if (length(missing_refs)) "warn" else "pass"

  rows[[length(rows) + 1]] <- .gp_rra_row(
    area = "tests",
    check = "export_test_references",
    item = "exports",
    status = status,
    message = if (length(missing_refs)) {
      paste0(
        length(missing_refs),
        " exported function(s) were not detected in test files by simple text search."
      )
    } else {
      "All exported functions were detected in test files by simple text search."
    }
  )

  do.call(rbind, rows)
}

.gp_rra_man_checks <- function(path, exports, man_files) {
  rows <- list(
    .gp_rra_row(
      area = "documentation",
      check = "manual_files_present",
      item = "man",
      status = if (length(man_files)) "pass" else "warn",
      message = paste0(length(man_files), " manual page file(s) detected.")
    )
  )

  if (!length(exports)) {
    return(do.call(rbind, rows))
  }

  expected <- file.path(path, "man", paste0(exports, ".Rd"))
  missing <- exports[!file.exists(expected)]

  rows[[length(rows) + 1]] <- .gp_rra_row(
    area = "documentation",
    check = "export_manual_pages",
    item = "exports",
    status = if (length(missing)) "warn" else "pass",
    message = if (length(missing)) {
      paste0(length(missing), " exported function(s) did not have same-name manual pages.")
    } else {
      "All exported functions had same-name manual pages."
    }
  )

  do.call(rbind, rows)
}

.gp_rra_pkgdown_checks <- function(path, exports, require_pkgdown) {
  has_pkgdown <- file.exists(file.path(path, "_pkgdown.yml"))
  rows <- list(
    .gp_rra_row(
      area = "pkgdown",
      check = "pkgdown_config",
      item = "_pkgdown.yml",
      status = if (has_pkgdown) "pass" else "not_checked",
      message = if (has_pkgdown) "pkgdown configuration is present." else "pkgdown configuration was not found."
    )
  )

  if (!length(exports)) {
    return(do.call(rbind, rows))
  }

  expected <- file.path(path, "docs", "reference", paste0(exports, ".html"))
  missing <- exports[!file.exists(expected)]

  rows[[length(rows) + 1]] <- .gp_rra_row(
    area = "pkgdown",
    check = "export_reference_pages",
    item = "docs/reference",
    status = if (!require_pkgdown) "not_checked" else if (length(missing)) "warn" else "pass",
    message = if (!require_pkgdown) {
      "pkgdown reference-page coverage was not required for this audit."
    } else if (length(missing)) {
      paste0(length(missing), " exported function(s) did not have pkgdown HTML reference pages.")
    } else {
      "All exported functions had pkgdown HTML reference pages."
    }
  )

  do.call(rbind, rows)
}

.gp_rra_vignette_checks <- function(vignette_files) {
  .gp_rra_row(
    area = "documentation",
    check = "vignettes_or_articles",
    item = "vignettes/docs/articles",
    status = if (length(vignette_files)) "pass" else "warn",
    message = paste0(length(vignette_files), " vignette or article file(s) detected.")
  )
}

.gp_rra_roadmap_checks <- function(path, roadmap_terms) {
  if (is.null(roadmap_terms) || !length(roadmap_terms)) {
    return(.gp_rra_row(
      area = "roadmap",
      check = "roadmap_terms",
      item = "roadmap_terms",
      status = "not_checked",
      message = "No roadmap terms were supplied."
    ))
  }

  files <- c(
    .gp_rra_files(path, "R", pattern = "\\.R$"),
    .gp_rra_files(path, "tests", pattern = "\\.R$"),
    .gp_rra_files(path, "man", pattern = "\\.Rd$"),
    .gp_rra_files(path, "docs", pattern = "\\.(md|html|json|txt)$")
  )

  txt <- .gp_rra_read_many(files)

  rows <- lapply(roadmap_terms, function(term) {
    found <- any(grepl(term, txt, fixed = TRUE))
    .gp_rra_row(
      area = "roadmap",
      check = "roadmap_term_present",
      item = term,
      status = if (found) "pass" else "warn",
      message = if (found) "Roadmap term was found in package files." else "Roadmap term was not found in searched package files."
    )
  })

  do.call(rbind, rows)
}

.gp_rra_overview <- function(checks) {
  status <- .gp_rra_normalize_status(checks$status)

  data.frame(
    n_checks = length(status),
    n_pass = sum(status == "pass"),
    n_warn = sum(status == "warn"),
    n_fail = sum(status == "fail"),
    n_not_checked = sum(status == "not_checked"),
    release_ready = !any(status == "fail"),
    needs_review = any(status %in% c("warn", "fail")),
    stringsAsFactors = FALSE
  )
}

.gp_rra_row <- function(area, check, item, status, message) {
  data.frame(
    area = area,
    check = check,
    item = item,
    status = .gp_rra_normalize_status(status),
    message = message,
    stringsAsFactors = FALSE
  )
}

.gp_rra_read_description <- function(path) {
  file <- file.path(path, "DESCRIPTION")

  if (!file.exists(file)) {
    return(NULL)
  }

  out <- tryCatch(
    as.data.frame(read.dcf(file), stringsAsFactors = FALSE),
    error = function(e) NULL
  )

  out
}

.gp_rra_read_exports <- function(path) {
  file <- file.path(path, "NAMESPACE")

  if (!file.exists(file)) {
    return(character())
  }

  lines <- readLines(file, warn = FALSE)
  hits <- grep("^export\\(", lines, value = TRUE)

  exports <- sub("^export\\((.*)\\)$", "\\1", hits)
  exports <- exports[nzchar(exports)]
  sort(unique(exports))
}

.gp_rra_files <- function(path, subdir, pattern) {
  root <- file.path(path, subdir)

  if (!dir.exists(root)) {
    return(character())
  }

  list.files(root, pattern = pattern, full.names = TRUE, recursive = TRUE)
}

.gp_rra_read_many <- function(files) {
  files <- files[file.exists(files)]

  if (!length(files)) {
    return(character())
  }

  unlist(lapply(files, function(file) {
    readLines(file, warn = FALSE)
  }), use.names = FALSE)
}

.gp_rra_default_feature_patterns <- function() {
  list(
    import_export = "import|read|parse|export|write|bundle|manifest|dictionary",
    validation_audit = "audit|validate|check|detect|assess|flag",
    quality_control = "quality|missingness|dropout|nonwear|artifact|outlier|smooth|filter|clean",
    pupil_gaze = "(^|_)pupil($|_)|(^|_)gaze($|_)|fixation|aoi|scanpath|saccade|luminance",
    physiology = "eda|gsr|scr|ppg|hr|ibi|hrv|beat|heart|pulse",
    synchronization = "sync|lag|ttl|align|time|sampling|reset",
    modelling_statistics = "model|fit|cluster|permutation|bootstrap|estimate|compare|prediction",
    reporting_review = "report|summary|summarize|checklist|readiness|preregistration|pipeline|dashboard",
    simulation_reproducibility = "simulate|synthetic|anonymize|reproducibility|roadmap",
    adapters_external = "heartpy|pyppg|pspm|ledalab|cvxeda|gazer|eyetools|lsl|xdf|ctsi"
  )
}

.gp_rra_extract_audit_checks <- function(audit) {
  if (is.null(audit)) {
    return(NULL)
  }

  if (inherits(audit, "gazepoint_release_readiness_audit") && is.data.frame(audit$checks)) {
    return(audit$checks)
  }

  if (is.data.frame(audit)) {
    return(audit)
  }

  NULL
}

.gp_rra_map_checklist_item <- function(phase, item, checks) {
  status <- "not_checked"
  evidence <- NA_character_

  lookup <- list(
    package = c("package_structure", "description", "namespace"),
    tests = "tests",
    documentation = "documentation",
    pkgdown = "pkgdown",
    reproducibility = c("tests", "pkgdown"),
    scope = c("roadmap", "description"),
    release = c("pkgdown", "tests", "documentation")
  )

  areas <- lookup[[phase]]

  if (is.null(areas)) {
    return(list(status = status, evidence = evidence))
  }

  subset <- checks[checks$area %in% areas, , drop = FALSE]

  if (!nrow(subset)) {
    return(list(status = status, evidence = evidence))
  }

  st <- .gp_rra_normalize_status(subset$status)

  if (any(st == "fail")) {
    status <- "fail"
  } else if (any(st == "warn")) {
    status <- "warn"
  } else if (any(st == "pass")) {
    status <- "pass"
  } else {
    status <- "not_checked"
  }

  evidence <- paste(utils::head(unique(subset$check), 4), collapse = ", ")

  list(status = status, evidence = evidence)
}

.gp_rra_normalize_status <- function(status) {
  x <- tolower(trimws(as.character(status)))
  x[is.na(x) | !nzchar(x)] <- "not_checked"
  x <- gsub("[ -]+", "_", x)

  out <- rep("not_checked", length(x))
  out[x %in% c("pass", "passed", "ok", "complete", "completed", "true")] <- "pass"
  out[x %in% c("warn", "warning", "review", "flag", "flagged", "caution")] <- "warn"
  out[x %in% c("fail", "failed", "error", "missing", "false")] <- "fail"
  out[x %in% c("not_checked", "not_applicable", "skipped", "skip", "na", "n/a")] <- "not_checked"
  out
}

.gp_rra_path <- function(path) {
  if (!is.character(path) || length(path) != 1 || is.na(path) || !nzchar(path)) {
    stop("`path` must be a single non-empty character string.", call. = FALSE)
  }

  normalizePath(path, winslash = "/", mustWork = TRUE)
}

.gp_rra_character <- function(x, name, allow_null = TRUE) {
  if (is.null(x) && allow_null) {
    return(NULL)
  }

  if (!is.character(x) || any(is.na(x)) || any(!nzchar(x))) {
    stop("`", name, "` must be a character vector with non-empty values.", call. = FALSE)
  }

  unique(x)
}

.gp_rra_logical_one <- function(x, name) {
  if (!is.logical(x) || length(x) != 1 || is.na(x)) {
    stop("`", name, "` must be TRUE or FALSE.", call. = FALSE)
  }

  invisible(TRUE)
}

#' @export
print.gazepoint_release_readiness_audit <- function(x, ...) {
  cat("Gazepoint release-readiness audit\n")
  print(x$overview, row.names = FALSE)
  invisible(x)
}

#' @export
print.gazepoint_release_checklist <- function(x, ...) {
  cat("Gazepoint release checklist\n")
  print.data.frame(x, row.names = FALSE)
  invisible(x)
}

#' @export
print.gazepoint_feature_coverage <- function(x, ...) {
  cat("Gazepoint feature coverage\n")
  print.data.frame(x, row.names = FALSE)
  invisible(x)
}
