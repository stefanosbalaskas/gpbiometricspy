#' Define gpbiometrics interoperability targets
#'
#' Creates the machine-readable interoperability manifest used by
#' [audit_gazepoint_interoperability_versions()]. The manifest distinguishes
#' R packages, Python distributions, supporting Python packages, and external
#' standards.
#'
#' A minimum tested version records the oldest version exercised by the
#' maintained interoperability workflow. It is not a claim that every earlier
#' version is incompatible.
#'
#' @param include_support Logical. Include NumPy and pandas support rows in
#'   addition to the direct interoperability targets.
#'
#' @return A data frame of class
#'   `"gazepoint_interoperability_manifest"` with one row per target.
#'
#' @examples
#' manifest <- gazepoint_interoperability_manifest()
#' manifest[, c("target", "dependency", "minimum_tested_version")]
#'
#' @export
gazepoint_interoperability_manifest <- function(include_support = TRUE) {
  .gpbiometrics_interop_assert_flag(
    include_support,
    "include_support"
  )

  manifest <- data.frame(
    target = c(
      "eyetrackingR",
      "PupillometryR",
      "gazeR",
      "MNE-Python",
      "pylsl",
      "BioSPPy",
      "HeartPy",
      "pyHRV",
      "BIDS"
    ),
    ecosystem = c(
      rep("R", 3L),
      rep("Python", 5L),
      "Standard"
    ),
    dependency = c(
      "eyetrackingR",
      "PupillometryR",
      "gazer",
      "mne",
      "pylsl",
      "biosppy",
      "heartpy",
      "pyhrv",
      "BIDS"
    ),
    dependency_type = c(
      rep("r_package", 3L),
      rep("python_module", 5L),
      "standard"
    ),
    minimum_tested_version = c(
      NA_character_,
      NA_character_,
      NA_character_,
      "1.11.0",
      "1.16.2",
      "2.1.0",
      "1.2.7",
      "0.4.1",
      "1.11.1"
    ),
    version_policy = c(
      rep("current-installed", 3L),
      rep("floor-and-current", 5L),
      "specification"
    ),
    test_group = c(
      rep("r-eye-bridges", 3L),
      "mne-lsl",
      "mne-lsl",
      "python-physiology",
      "python-physiology",
      "python-physiology",
      "bids-export"
    ),
    bridge_functions = c(
      "prepare_gazepoint_eyetrackingr_input",
      "prepare_gazepoint_pupillometryr_input",
      "prepare_gazepoint_gazer_input",
      paste(
        c(
          "prepare_gazepoint_mne_events",
          "prepare_gazepoint_mne_input",
          "write_gazepoint_mne_fif"
        ),
        collapse = ";"
      ),
      paste(
        c(
          "sync_gazepoint_signals_via_lsl",
          "estimate_gazepoint_lsl_clock_offsets"
        ),
        collapse = ";"
      ),
      paste(
        c(
          "prepare_gazepoint_biosppy_input",
          "run_gazepoint_biosppy_eda",
          "run_gazepoint_biosppy_ppg"
        ),
        collapse = ";"
      ),
      paste(
        c(
          "prepare_gazepoint_heartpy_input",
          "run_gazepoint_heartpy_crosscheck"
        ),
        collapse = ";"
      ),
      paste(
        c(
          "prepare_gazepoint_pyhrv_input",
          "run_gazepoint_pyhrv_style"
        ),
        collapse = ";"
      ),
      paste(
        c(
          "export_gazepoint_to_bids",
          "prepare_gazepoint_bids_eye",
          "prepare_gazepoint_bids_physio",
          "check_gazepoint_bids"
        ),
        collapse = ";"
      )
    ),
    optional = c(
      rep(TRUE, 8L),
      FALSE
    ),
    stringsAsFactors = FALSE
  )

  if (isTRUE(include_support)) {
    support <- data.frame(
      target = c(
        "NumPy",
        "pandas"
      ),
      ecosystem = c(
        "Python",
        "Python"
      ),
      dependency = c(
        "numpy",
        "pandas"
      ),
      dependency_type = c(
        "python_module",
        "python_module"
      ),
      minimum_tested_version = c(
        "1.26.4",
        "2.2.3"
      ),
      version_policy = c(
        "floor-and-current",
        "floor-and-current"
      ),
      test_group = c(
        "python-support",
        "python-support"
      ),
      bridge_functions = c(
        "",
        ""
      ),
      optional = c(
        TRUE,
        TRUE
      ),
      stringsAsFactors = FALSE
    )

    manifest <- rbind(
      manifest,
      support
    )
  }

  rownames(manifest) <- NULL

  class(manifest) <- c(
    "gazepoint_interoperability_manifest",
    "data.frame"
  )

  manifest
}


#' Audit external interoperability versions
#'
#' Checks whether declared bridge functions are exported and records the
#' installed versions of optional R and Python dependencies. Missing optional
#' dependencies are recorded for review rather than treated as core-package
#' failures.
#'
#' Python package versions are queried through `importlib.metadata`; target
#' modules are not imported merely to determine their versions.
#'
#' @param manifest Interoperability manifest. Defaults to
#'   [gazepoint_interoperability_manifest()].
#' @param include_python Logical. Inspect the active Python environment through
#'   the optional `reticulate` package.
#' @param strict Logical. Stop when a required contract fails, a declared bridge
#'   function is missing, or an installed dependency is below its minimum
#'   tested version.
#'
#' @return An object of class `"gazepoint_interoperability_audit"` containing:
#'
#' - `results`: target-level compatibility findings;
#' - `summary`: aggregate pass and review counts;
#' - `session`: R, Python, operating-system, package, and timestamp metadata;
#' - `manifest`: the manifest used for the audit.
#'
#' @examples
#' audit <- audit_gazepoint_interoperability_versions(
#'   include_python = FALSE
#' )
#' audit$summary
#'
#' @export
audit_gazepoint_interoperability_versions <- function(
    manifest = gazepoint_interoperability_manifest(),
    include_python = TRUE,
    strict = FALSE) {
  .gpbiometrics_interop_assert_flag(
    include_python,
    "include_python"
  )

  .gpbiometrics_interop_assert_flag(
    strict,
    "strict"
  )

  .gpbiometrics_interop_validate_manifest(
    manifest
  )

  exports <- getNamespaceExports(
    "gpbiometrics"
  )

  timestamp_utc <- format(
    Sys.time(),
    tz = "UTC",
    usetz = TRUE
  )

  operating_system <- .gpbiometrics_interop_os_string()

  python_runtime <- .gpbiometrics_interop_python_runtime(
    include_python = include_python
  )

  rows <- lapply(
    seq_len(NROW(manifest)),
    function(index) {
      manifest_row <- manifest[index, , drop = FALSE]

      bridge_functions <- .gpbiometrics_interop_split_functions(
        manifest_row$bridge_functions[[1L]]
      )

      missing_bridge_functions <- setdiff(
        bridge_functions,
        exports
      )

      dependency_result <- switch(
        manifest_row$dependency_type[[1L]],
        r_package = .gpbiometrics_interop_r_dependency(
          manifest_row$dependency[[1L]]
        ),
        python_module = .gpbiometrics_interop_python_dependency(
          manifest_row$dependency[[1L]],
          include_python = include_python,
          python_runtime = python_runtime
        ),
        standard = list(
          status = "declared",
          version = manifest_row$minimum_tested_version[[1L]],
          runtime_version = NA_character_
        ),
        stop(
          "Unsupported dependency type: ",
          manifest_row$dependency_type[[1L]],
          call. = FALSE
        )
      )

      minimum_version <-
        manifest_row$minimum_tested_version[[1L]]

      status <- dependency_result$status

      if (
        identical(status, "available") &&
        (
          is.na(minimum_version) ||
          !nzchar(trimws(minimum_version))
        )
      ) {
        status <- "available_unpinned"
      }

      if (
        identical(status, "available") &&
        !is.na(minimum_version) &&
        nzchar(trimws(minimum_version))
      ) {
        version_ok <- .gpbiometrics_interop_version_at_least(
          installed = dependency_result$version,
          minimum = minimum_version
        )

        if (is.na(version_ok)) {
          status <- "version_unreadable"
        } else if (!isTRUE(version_ok)) {
          status <- "below_minimum"
        }
      }

      if (length(missing_bridge_functions) > 0L) {
        status <- "missing_bridge"
      }

      optional <- isTRUE(
        manifest_row$optional[[1L]]
      )

      pass <- !status %in% c(
        "missing_bridge",
        "below_minimum",
        "version_unreadable"
      )

      if (
        !optional &&
        status %in% c(
          "missing_dependency",
          "runtime_unavailable",
          "not_checked"
        )
      ) {
        pass <- FALSE
      }

      needs_review <- status %in% c(
        "available_unpinned",
        "missing_dependency",
        "runtime_unavailable",
        "not_checked"
      )

      message <- .gpbiometrics_interop_status_message(
        target = manifest_row$target[[1L]],
        dependency = manifest_row$dependency[[1L]],
        status = status,
        installed_version = dependency_result$version,
        minimum_version = minimum_version,
        optional = optional,
        missing_bridge_functions = missing_bridge_functions
      )

      data.frame(
        target = manifest_row$target[[1L]],
        ecosystem = manifest_row$ecosystem[[1L]],
        dependency = manifest_row$dependency[[1L]],
        dependency_type =
          manifest_row$dependency_type[[1L]],
        minimum_tested_version =
          minimum_version,
        installed_version =
          dependency_result$version,
        runtime_version =
          dependency_result$runtime_version,
        operating_system =
          operating_system,
        version_policy =
          manifest_row$version_policy[[1L]],
        test_group =
          manifest_row$test_group[[1L]],
        optional =
          optional,
        bridge_functions =
          manifest_row$bridge_functions[[1L]],
        missing_bridge_functions =
          paste(
            missing_bridge_functions,
            collapse = ";"
          ),
        status =
          status,
        pass =
          pass,
        needs_review =
          needs_review,
        message =
          message,
        timestamp_utc =
          timestamp_utc,
        stringsAsFactors = FALSE
      )
    }
  )

  results <- do.call(
    rbind,
    rows
  )

  rownames(results) <- NULL

  summary <- data.frame(
    n_targets = NROW(results),
    n_pass = sum(results$pass),
    n_fail = sum(!results$pass),
    n_review = sum(results$needs_review),
    n_available = sum(
      results$status %in% c(
        "available",
        "available_unpinned",
        "declared"
      )
    ),
    n_missing_optional = sum(
      results$optional &
        results$status == "missing_dependency"
    ),
    overall_pass = all(results$pass),
    stringsAsFactors = FALSE
  )

  session <- data.frame(
    timestamp_utc = timestamp_utc,
    gpbiometrics_version =
      .gpbiometrics_interop_package_version(),
    r_version = R.version.string,
    python_version = python_runtime$version,
    platform = R.version$platform,
    operating_system = operating_system,
    stringsAsFactors = FALSE
  )

  output <- list(
    results = results,
    summary = summary,
    session = session,
    manifest = as.data.frame(
      manifest,
      stringsAsFactors = FALSE
    )
  )

  class(output) <- c(
    "gazepoint_interoperability_audit",
    "list"
  )

  if (
    isTRUE(strict) &&
    !isTRUE(summary$overall_pass[[1L]])
  ) {
    failed_targets <- results$target[
      !results$pass
    ]

    stop(
      "Interoperability audit failed for: ",
      paste(
        failed_targets,
        collapse = ", "
      ),
      call. = FALSE
    )
  }

  output
}


#' Write an interoperability audit
#'
#' Writes only machine-readable aggregate compatibility information. No source
#' data, participant identifiers, input filenames, or local data paths are
#' included.
#'
#' @param x Object returned by
#'   [audit_gazepoint_interoperability_versions()].
#' @param output_dir Output directory.
#' @param prefix Filename prefix.
#' @param overwrite Logical. Permit replacement of existing files.
#'
#' @return Invisibly returns a named character vector containing the four
#'   written file paths.
#'
#' @examples
#' audit <- audit_gazepoint_interoperability_versions(
#'   include_python = FALSE
#' )
#' output <- tempfile("gpbiometrics-interoperability-")
#' files <- write_gazepoint_interoperability_audit(
#'   audit,
#'   output
#' )
#' basename(files)
#'
#' @export
write_gazepoint_interoperability_audit <- function(
    x,
    output_dir,
    prefix = "gpbiometrics-interoperability",
    overwrite = FALSE) {
  if (!inherits(x, "gazepoint_interoperability_audit")) {
    stop(
      "`x` must be returned by ",
      "`audit_gazepoint_interoperability_versions()`.",
      call. = FALSE
    )
  }

  if (
    !is.character(output_dir) ||
    length(output_dir) != 1L ||
    is.na(output_dir) ||
    !nzchar(trimws(output_dir))
  ) {
    stop(
      "`output_dir` must be one non-empty character value.",
      call. = FALSE
    )
  }

  if (
    !is.character(prefix) ||
    length(prefix) != 1L ||
    is.na(prefix) ||
    !nzchar(trimws(prefix))
  ) {
    stop(
      "`prefix` must be one non-empty character value.",
      call. = FALSE
    )
  }

  if (grepl("[/\\\\]", prefix)) {
    stop(
      "`prefix` must not contain directory separators.",
      call. = FALSE
    )
  }

  .gpbiometrics_interop_assert_flag(
    overwrite,
    "overwrite"
  )

  dir.create(
    output_dir,
    recursive = TRUE,
    showWarnings = FALSE
  )

  if (!dir.exists(output_dir)) {
    stop(
      "Could not create `output_dir`.",
      call. = FALSE
    )
  }

  files <- c(
    results = file.path(
      output_dir,
      paste0(prefix, "-results.csv")
    ),
    summary = file.path(
      output_dir,
      paste0(prefix, "-summary.csv")
    ),
    session = file.path(
      output_dir,
      paste0(prefix, "-session.csv")
    ),
    manifest = file.path(
      output_dir,
      paste0(prefix, "-manifest.csv")
    )
  )

  existing <- files[
    file.exists(files)
  ]

  if (
    length(existing) > 0L &&
    !isTRUE(overwrite)
  ) {
    stop(
      "Refusing to overwrite existing files:\n",
      paste(
        existing,
        collapse = "\n"
      ),
      call. = FALSE
    )
  }

  utils::write.csv(
    x$results,
    files[["results"]],
    row.names = FALSE,
    na = ""
  )

  utils::write.csv(
    x$summary,
    files[["summary"]],
    row.names = FALSE,
    na = ""
  )

  utils::write.csv(
    x$session,
    files[["session"]],
    row.names = FALSE,
    na = ""
  )

  utils::write.csv(
    x$manifest,
    files[["manifest"]],
    row.names = FALSE,
    na = ""
  )

  normalized <- normalizePath(
    files,
    winslash = "/",
    mustWork = TRUE
  )

  names(normalized) <- names(files)

  invisible(normalized)
}


#' @export
print.gazepoint_interoperability_audit <- function(
    x,
    ...) {
  cat(
    "<gazepoint_interoperability_audit>\n",
    sep = ""
  )

  cat(
    "Targets: ",
    x$summary$n_targets[[1L]],
    "\n",
    sep = ""
  )

  cat(
    "Passed: ",
    x$summary$n_pass[[1L]],
    "\n",
    sep = ""
  )

  cat(
    "Failed: ",
    x$summary$n_fail[[1L]],
    "\n",
    sep = ""
  )

  cat(
    "Review: ",
    x$summary$n_review[[1L]],
    "\n",
    sep = ""
  )

  cat(
    "Overall pass: ",
    x$summary$overall_pass[[1L]],
    "\n",
    sep = ""
  )

  invisible(x)
}


.gpbiometrics_interop_assert_flag <- function(
    value,
    name) {
  if (
    !is.logical(value) ||
    length(value) != 1L ||
    is.na(value)
  ) {
    stop(
      "`",
      name,
      "` must be TRUE or FALSE.",
      call. = FALSE
    )
  }

  invisible(TRUE)
}


.gpbiometrics_interop_validate_manifest <- function(
    manifest) {
  if (!is.data.frame(manifest)) {
    stop(
      "`manifest` must be a data frame.",
      call. = FALSE
    )
  }

  required <- c(
    "target",
    "ecosystem",
    "dependency",
    "dependency_type",
    "minimum_tested_version",
    "version_policy",
    "test_group",
    "bridge_functions",
    "optional"
  )

  missing <- setdiff(
    required,
    names(manifest)
  )

  if (length(missing) > 0L) {
    stop(
      "`manifest` is missing columns: ",
      paste(
        missing,
        collapse = ", "
      ),
      call. = FALSE
    )
  }

  if (NROW(manifest) == 0L) {
    stop(
      "`manifest` must contain at least one row.",
      call. = FALSE
    )
  }

  if (
    anyNA(manifest$target) ||
    any(!nzchar(trimws(manifest$target)))
  ) {
    stop(
      "`manifest$target` must contain non-empty values.",
      call. = FALSE
    )
  }

  if (anyDuplicated(manifest$target)) {
    stop(
      "`manifest$target` must be unique.",
      call. = FALSE
    )
  }

  allowed_types <- c(
    "r_package",
    "python_module",
    "standard"
  )

  invalid_types <- setdiff(
    unique(manifest$dependency_type),
    allowed_types
  )

  if (length(invalid_types) > 0L) {
    stop(
      "Unsupported dependency types: ",
      paste(
        invalid_types,
        collapse = ", "
      ),
      call. = FALSE
    )
  }

  if (
    !is.logical(manifest$optional) ||
    anyNA(manifest$optional)
  ) {
    stop(
      "`manifest$optional` must be a non-missing logical column.",
      call. = FALSE
    )
  }

  invisible(TRUE)
}


.gpbiometrics_interop_split_functions <- function(
    value) {
  if (
    length(value) == 0L ||
    is.na(value) ||
    !nzchar(trimws(value))
  ) {
    return(character())
  }

  functions <- trimws(
    strsplit(
      value,
      ";",
      fixed = TRUE
    )[[1L]]
  )

  unique(
    functions[nzchar(functions)]
  )
}


.gpbiometrics_interop_r_dependency <- function(
    dependency) {
  available <- requireNamespace(
    dependency,
    quietly = TRUE
  )

  if (!available) {
    return(
      list(
        status = "missing_dependency",
        version = NA_character_,
        runtime_version = R.version.string
      )
    )
  }

  version <- tryCatch(
    as.character(
      utils::packageVersion(dependency)
    ),
    error = function(error) {
      NA_character_
    }
  )

  list(
    status = if (
      is.na(version)
    ) {
      "version_unreadable"
    } else {
      "available"
    },
    version = version,
    runtime_version = R.version.string
  )
}


.gpbiometrics_interop_python_runtime <- function(
    include_python) {
  if (!isTRUE(include_python)) {
    return(
      list(
        available = FALSE,
        version = NA_character_,
        reason = "not_checked"
      )
    )
  }

  if (!requireNamespace("reticulate", quietly = TRUE)) {
    return(
      list(
        available = FALSE,
        version = NA_character_,
        reason = "runtime_unavailable"
      )
    )
  }

  available <- tryCatch(
    reticulate::py_available(
      initialize = TRUE
    ),
    error = function(error) {
      FALSE
    }
  )

  if (!isTRUE(available)) {
    return(
      list(
        available = FALSE,
        version = NA_character_,
        reason = "runtime_unavailable"
      )
    )
  }

  version <- tryCatch(
    as.character(
      reticulate::py_config()$version_string
    ),
    error = function(error) {
      NA_character_
    }
  )

  list(
    available = TRUE,
    version = version,
    reason = "available"
  )
}


.gpbiometrics_interop_python_dependency <- function(
    dependency,
    include_python,
    python_runtime) {
  if (!isTRUE(include_python)) {
    return(
      list(
        status = "not_checked",
        version = NA_character_,
        runtime_version = NA_character_
      )
    )
  }

  if (!isTRUE(python_runtime$available)) {
    return(
      list(
        status = "runtime_unavailable",
        version = NA_character_,
        runtime_version = python_runtime$version
      )
    )
  }

  metadata <- tryCatch(
    reticulate::import(
      "importlib.metadata",
      convert = TRUE
    ),
    error = function(error) {
      NULL
    }
  )

  if (is.null(metadata)) {
    return(
      list(
        status = "runtime_unavailable",
        version = NA_character_,
        runtime_version = python_runtime$version
      )
    )
  }

  version <- tryCatch(
    as.character(
      metadata$version(dependency)
    ),
    error = function(error) {
      NA_character_
    }
  )

  list(
    status = if (
      is.na(version)
    ) {
      "missing_dependency"
    } else {
      "available"
    },
    version = version,
    runtime_version = python_runtime$version
  )
}


.gpbiometrics_interop_version_at_least <- function(
    installed,
    minimum) {
  if (
    is.na(installed) ||
    !nzchar(trimws(installed)) ||
    is.na(minimum) ||
    !nzchar(trimws(minimum))
  ) {
    return(NA)
  }

  tryCatch(
    utils::compareVersion(
      installed,
      minimum
    ) >= 0L,
    error = function(error) {
      NA
    }
  )
}


.gpbiometrics_interop_status_message <- function(
    target,
    dependency,
    status,
    installed_version,
    minimum_version,
    optional,
    missing_bridge_functions) {
  if (identical(status, "missing_bridge")) {
    return(
      paste0(
        "Missing gpbiometrics bridge export(s) for ",
        target,
        ": ",
        paste(
          missing_bridge_functions,
          collapse = ", "
        ),
        "."
      )
    )
  }

  if (identical(status, "available")) {
    return(
      paste0(
        dependency,
        " ",
        installed_version,
        " is installed and meets the minimum tested version ",
        minimum_version,
        "."
      )
    )
  }

  if (identical(status, "available_unpinned")) {
    return(
      paste0(
        dependency,
        " ",
        installed_version,
        " is installed; no historical minimum tested version ",
        "has yet been declared."
      )
    )
  }

  if (identical(status, "declared")) {
    return(
      paste0(
        target,
        " specification ",
        minimum_version,
        " is declared by the package contract."
      )
    )
  }

  if (identical(status, "below_minimum")) {
    return(
      paste0(
        dependency,
        " ",
        installed_version,
        " is below the minimum tested version ",
        minimum_version,
        "."
      )
    )
  }

  if (identical(status, "version_unreadable")) {
    return(
      paste0(
        "The installed version of ",
        dependency,
        " could not be interpreted."
      )
    )
  }

  if (identical(status, "missing_dependency")) {
    suffix <- if (isTRUE(optional)) {
      paste0(
        "; the bridge contract remains available but runtime ",
        "construction was not checked."
      )
    } else {
      "."
    }

    return(
      paste0(
        "Optional dependency ",
        dependency,
        " is not installed",
        suffix
      )
    )
  }

  if (identical(status, "runtime_unavailable")) {
    return(
      paste0(
        "A usable Python runtime was unavailable for checking ",
        dependency,
        "."
      )
    )
  }

  if (identical(status, "not_checked")) {
    return(
      paste0(
        "Python inspection was disabled for ",
        dependency,
        "."
      )
    )
  }

  paste0(
    "Interoperability status for ",
    target,
    ": ",
    status,
    "."
  )
}


.gpbiometrics_interop_package_version <- function() {
  if (file.exists("DESCRIPTION")) {
    version <- tryCatch(
      read.dcf(
        "DESCRIPTION",
        fields = "Version"
      )[1L, 1L],
      error = function(error) {
        NA_character_
      }
    )

    if (
      !is.na(version) &&
      nzchar(version)
    ) {
      return(
        as.character(version)
      )
    }
  }

  tryCatch(
    as.character(
      utils::packageVersion(
        "gpbiometrics"
      )
    ),
    error = function(error) {
      NA_character_
    }
  )
}


.gpbiometrics_interop_os_string <- function() {
  info <- Sys.info()

  values <- c(
    info[["sysname"]],
    info[["release"]]
  )

  values <- values[
    !is.na(values) &
      nzchar(values)
  ]

  if (length(values) == 0L) {
    return(
      R.version$os
    )
  }

  paste(
    values,
    collapse = " "
  )
}
