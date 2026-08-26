#' Run privacy-safe smoke tests on private Gazepoint exports
#'
#' Runs the standard gpbiometrics workflow, workflow summary, and workflow
#' diagnostic on one or more private Gazepoint export folders. Raw data,
#' participant-level values, source filenames, and private paths are never
#' retained in the returned object.
#'
#' The source directory should normally be outside the package repository and
#' supplied through the `GPBIOMETRICS_SMOKE_DIR` environment variable.
#'
#' @param data_dir Private external data directory. Defaults to
#'   `Sys.getenv("GPBIOMETRICS_SMOKE_DIR")`.
#' @param output_dir Optional directory for aggregate smoke-test outputs.
#'   This should remain outside the package repository.
#' @param dataset_mode How datasets are identified. `"subdirectories"` treats
#'   each immediate subdirectory containing matching files as one dataset.
#'   `"root"` treats `data_dir` as one dataset.
#' @param pattern Regular expression used to identify candidate input files.
#' @param recursive Search recursively within each dataset directory?
#' @param workflow_args Named list of additional arguments passed to
#'   [run_gazepoint_biometrics_workflow()].
#' @param diagnostic_args Named list of additional arguments passed to
#'   [diagnose_gazepoint_biometrics_workflow()].
#' @param workflow_runner Optional workflow function. Defaults to
#'   [run_gazepoint_biometrics_workflow()]. This argument primarily supports
#'   controlled testing.
#' @param summary_runner Optional summary function. Defaults to
#'   [summarise_gazepoint_biometrics_workflow()].
#' @param diagnostic_runner Optional diagnostic function. Defaults to
#'   [diagnose_gazepoint_biometrics_workflow()].
#' @param stop_on_error Stop after the first failed dataset?
#' @param write_results Write aggregate CSV outputs to `output_dir`?
#' @param overwrite Permit replacement of existing aggregate output files?
#' @param protect_repository Reject private input or generated output
#'   directories located inside the current package repository?
#'
#' @return An object of class `"gazepoint_real_data_smoke"` containing only
#'   privacy-safe aggregate results, condition summaries, runtime metadata,
#'   and non-sensitive settings.
#'
#' @examples
#' private_dir <- Sys.getenv("GPBIOMETRICS_SMOKE_DIR")
#'
#' if (nzchar(private_dir) && dir.exists(private_dir)) {
#'   smoke <- run_gazepoint_real_data_smoke(
#'     data_dir = private_dir
#'   )
#'
#'   smoke$results
#' }
#'
#' @export
run_gazepoint_real_data_smoke <- function(
    data_dir = Sys.getenv(
      "GPBIOMETRICS_SMOKE_DIR",
      unset = ""
    ),
    output_dir = NULL,
    dataset_mode = c(
      "subdirectories",
      "root"
    ),
    pattern = "\\.csv$",
    recursive = TRUE,
    workflow_args = list(),
    diagnostic_args = list(),
    workflow_runner = NULL,
    summary_runner = NULL,
    diagnostic_runner = NULL,
    stop_on_error = FALSE,
    write_results = FALSE,
    overwrite = FALSE,
    protect_repository = TRUE) {
  dataset_mode <- match.arg(
    dataset_mode
  )

  .gpbiometrics_smoke_assert_flag(
    recursive,
    "recursive"
  )

  .gpbiometrics_smoke_assert_flag(
    stop_on_error,
    "stop_on_error"
  )

  .gpbiometrics_smoke_assert_flag(
    write_results,
    "write_results"
  )

  .gpbiometrics_smoke_assert_flag(
    overwrite,
    "overwrite"
  )

  .gpbiometrics_smoke_assert_flag(
    protect_repository,
    "protect_repository"
  )

  data_dir <- .gpbiometrics_smoke_validate_directory(
    data_dir,
    argument = "data_dir",
    must_exist = TRUE
  )

  if (
    !is.character(pattern) ||
    length(pattern) != 1L ||
    is.na(pattern) ||
    !nzchar(pattern)
  ) {
    stop(
      "`pattern` must be one non-empty regular expression.",
      call. = FALSE
    )
  }

  if (!is.list(workflow_args)) {
    stop(
      "`workflow_args` must be a list.",
      call. = FALSE
    )
  }

  if (!is.list(diagnostic_args)) {
    stop(
      "`diagnostic_args` must be a list.",
      call. = FALSE
    )
  }

  if (
    !is.null(names(workflow_args)) &&
    "path" %in% names(workflow_args)
  ) {
    stop(
      "`workflow_args` must not contain `path`.",
      call. = FALSE
    )
  }

  if (
    !is.null(names(diagnostic_args)) &&
    "workflow" %in% names(diagnostic_args)
  ) {
    stop(
      "`diagnostic_args` must not contain `workflow`.",
      call. = FALSE
    )
  }

  if (is.null(workflow_runner)) {
    workflow_runner <-
      run_gazepoint_biometrics_workflow
  }

  if (is.null(summary_runner)) {
    summary_runner <-
      summarise_gazepoint_biometrics_workflow
  }

  if (is.null(diagnostic_runner)) {
    diagnostic_runner <-
      diagnose_gazepoint_biometrics_workflow
  }

  runners <- list(
    workflow_runner = workflow_runner,
    summary_runner = summary_runner,
    diagnostic_runner = diagnostic_runner
  )

  invalid_runners <- names(runners)[
    !vapply(
      runners,
      is.function,
      logical(1)
    )
  ]

  if (length(invalid_runners) > 0L) {
    stop(
      "These runners are not functions: ",
      paste(
        invalid_runners,
        collapse = ", "
      ),
      ".",
      call. = FALSE
    )
  }

  if (isTRUE(write_results)) {
    if (is.null(output_dir)) {
      output_dir <- file.path(
        tempdir(),
        "gpbiometrics-real-data-smoke"
      )
    }

    output_dir <-
      .gpbiometrics_smoke_validate_directory(
        output_dir,
        argument = "output_dir",
        must_exist = FALSE
      )
  }

  repository_root <-
    .gpbiometrics_smoke_repository_root()

  if (
    isTRUE(protect_repository) &&
    !is.null(repository_root)
  ) {
    if (
      .gpbiometrics_smoke_is_within(
        data_dir,
        repository_root
      )
    ) {
      stop(
        "Private smoke-test data must remain outside the package ",
        "repository.",
        call. = FALSE
      )
    }

    if (
      isTRUE(write_results) &&
      .gpbiometrics_smoke_is_within(
        output_dir,
        repository_root
      )
    ) {
      stop(
        "Smoke-test outputs must remain outside the package repository.",
        call. = FALSE
      )
    }
  }

  datasets <- .gpbiometrics_smoke_discover_datasets(
    data_dir = data_dir,
    dataset_mode = dataset_mode,
    pattern = pattern,
    recursive = recursive
  )

  if (length(datasets) == 0L) {
    stop(
      "No dataset folders containing matching files were found.",
      call. = FALSE
    )
  }

  timestamp_utc <- format(
    Sys.time(),
    tz = "UTC",
    usetz = TRUE
  )

  result_rows <- vector(
    "list",
    length(datasets)
  )

  condition_rows <- vector(
    "list",
    length(datasets)
  )

  private_values <- unique(
    c(
      data_dir,
      vapply(
        datasets,
        function(dataset) {
          dataset$path
        },
        character(1)
      )
    )
  )

  for (index in seq_along(datasets)) {
    dataset <- datasets[[index]]

    started <- proc.time()[["elapsed"]]

    workflow_capture <-
      .gpbiometrics_smoke_capture(
        thunk = function() {
          do.call(
            workflow_runner,
            c(
              list(
                path = dataset$path
              ),
              workflow_args
            )
          )
        },
        private_values = private_values
      )

    summary_capture <-
      .gpbiometrics_smoke_empty_capture(
        status = "not_run"
      )

    diagnostic_capture <-
      .gpbiometrics_smoke_empty_capture(
        status = "not_run"
      )

    if (isTRUE(workflow_capture$ok)) {
      summary_capture <-
        .gpbiometrics_smoke_capture(
          thunk = function() {
            summary_runner(
              workflow_capture$value
            )
          },
          private_values = private_values
        )

      diagnostic_capture <-
        .gpbiometrics_smoke_capture(
          thunk = function() {
            do.call(
              diagnostic_runner,
              c(
                list(
                  workflow =
                    workflow_capture$value
                ),
                diagnostic_args
              )
            )
          },
          private_values = private_values
        )
    }

    elapsed_seconds <-
      proc.time()[["elapsed"]] - started

    workflow_summary <-
      if (isTRUE(summary_capture$ok)) {
        summary_capture$value
      } else {
        NULL
      }

    workflow_diagnostic <-
      if (isTRUE(diagnostic_capture$ok)) {
        diagnostic_capture$value
      } else {
        NULL
      }

    diagnostic_status <-
      .gpbiometrics_smoke_diagnostic_status(
        workflow_diagnostic
      )

    all_captures <- list(
      workflow = workflow_capture,
      summary = summary_capture,
      diagnostic = diagnostic_capture
    )

    n_warnings <- sum(
      vapply(
        all_captures,
        function(capture) {
          length(capture$warnings)
        },
        integer(1)
      )
    )

    n_messages <- sum(
      vapply(
        all_captures,
        function(capture) {
          length(capture$messages)
        },
        integer(1)
      )
    )

    error_stages <- names(all_captures)[
      !vapply(
        all_captures,
        function(capture) {
          isTRUE(capture$ok) ||
            identical(
              capture$status,
              "not_run"
            )
        },
        logical(1)
      )
    ]

    failed <- length(error_stages) > 0L ||
      identical(
        diagnostic_status,
        "fail"
      )

    review <- !failed &&
      (
        identical(
          diagnostic_status,
          "review"
        ) ||
          n_warnings > 0L
      )

    smoke_status <- if (failed) {
      "fail"
    } else if (review) {
      "review"
    } else {
      "pass"
    }

    error_stage <- if (
      length(error_stages) > 0L
    ) {
      error_stages[[1L]]
    } else if (
      identical(
        diagnostic_status,
        "fail"
      )
    ) {
      "diagnostic"
    } else {
      NA_character_
    }

    error_message <- if (
      length(error_stages) > 0L
    ) {
      all_captures[[error_stages[[1L]]]]$error_message
    } else if (
      identical(
        diagnostic_status,
        "fail"
      )
    ) {
      "The workflow diagnostic returned a fail status."
    } else {
      NA_character_
    }

    result_rows[[index]] <- data.frame(
      dataset_id = dataset$dataset_id,
      n_files = dataset$n_files,
      n_csv_files = dataset$n_csv_files,
      total_bytes = dataset$total_bytes,
      n_rows =
        .gpbiometrics_smoke_extract_numeric(
          workflow_summary,
          c(
            "n_rows",
            "rows",
            "all_gaze_rows",
            "imported_rows"
          )
        ),
      n_participants =
        .gpbiometrics_smoke_extract_numeric(
          workflow_summary,
          c(
            "n_participants",
            "participant_count",
            "participants"
          )
        ),
      n_trials =
        .gpbiometrics_smoke_extract_numeric(
          workflow_summary,
          c(
            "n_trials",
            "trial_count",
            "trials"
          )
        ),
      n_events =
        .gpbiometrics_smoke_extract_numeric(
          workflow_summary,
          c(
            "n_events",
            "event_count",
            "ttl_events"
          )
        ),
      detected_schema =
        .gpbiometrics_smoke_extract_character(
          workflow_summary,
          c(
            "detected_schema",
            "schema",
            "export_schema"
          )
        ),
      active_signal_groups =
        .gpbiometrics_smoke_extract_numeric(
          workflow_summary,
          c(
            "active_signal_groups",
            "n_active_signal_groups",
            "n_active_channels"
          )
        ),
      workflow_ok =
        isTRUE(workflow_capture$ok),
      summary_ok =
        isTRUE(summary_capture$ok),
      diagnostic_ok =
        isTRUE(diagnostic_capture$ok),
      diagnostic_status =
        diagnostic_status,
      smoke_status =
        smoke_status,
      n_warnings =
        n_warnings,
      n_messages =
        n_messages,
      elapsed_seconds =
        unname(
          round(
            elapsed_seconds,
            digits = 3L
          )
        ),
      error_stage =
        error_stage,
      error_message =
        error_message,
      timestamp_utc =
        timestamp_utc,
      gpbiometrics_version =
        .gpbiometrics_smoke_package_version(),
      stringsAsFactors = FALSE
    )

    condition_rows[[index]] <-
      .gpbiometrics_smoke_condition_rows(
        dataset_id = dataset$dataset_id,
        captures = all_captures
      )

    if (
      isTRUE(stop_on_error) &&
      identical(
        smoke_status,
        "fail"
      )
    ) {
      result_rows <- result_rows[
        seq_len(index)
      ]

      condition_rows <- condition_rows[
        seq_len(index)
      ]

      break
    }
  }

  results <- do.call(
    rbind,
    result_rows
  )

  rownames(results) <- NULL

  conditions <- .gpbiometrics_smoke_bind_conditions(
    condition_rows
  )

  session <- data.frame(
    timestamp_utc = timestamp_utc,
    gpbiometrics_version =
      .gpbiometrics_smoke_package_version(),
    r_version = R.version.string,
    platform = R.version$platform,
    operating_system =
      .gpbiometrics_smoke_os_string(),
    stringsAsFactors = FALSE
  )

  settings <- data.frame(
    dataset_mode = dataset_mode,
    file_pattern = pattern,
    recursive = recursive,
    n_datasets = NROW(results),
    stop_on_error = stop_on_error,
    workflow_argument_names =
      paste(
        names(workflow_args),
        collapse = ";"
      ),
    diagnostic_argument_names =
      paste(
        names(diagnostic_args),
        collapse = ";"
      ),
    private_data_retained = FALSE,
    source_paths_retained = FALSE,
    source_filenames_retained = FALSE,
    stringsAsFactors = FALSE
  )

  output <- list(
    results = results,
    conditions = conditions,
    session = session,
    settings = settings
  )

  class(output) <- c(
    "gazepoint_real_data_smoke",
    "list"
  )

  privacy <- audit_gazepoint_smoke_privacy(
    output,
    private_values = private_values
  )

  if (!all(privacy$status == "pass")) {
    failed_checks <- privacy$check[
      privacy$status != "pass"
    ]

    stop(
      "The smoke-test result failed its privacy audit: ",
      paste(
        failed_checks,
        collapse = ", "
      ),
      ".",
      call. = FALSE
    )
  }

  attr(
    output,
    "privacy_audit"
  ) <- privacy

  if (isTRUE(write_results)) {
    written_files <-
      write_gazepoint_real_data_smoke(
        output,
        output_dir = output_dir,
        overwrite = overwrite,
        protect_repository =
          protect_repository
      )

    attr(
      output,
      "written_files"
    ) <- written_files
  }

  output
}


#' Audit a smoke-test result for private information
#'
#' Checks that a smoke-test result contains no private paths, source filenames,
#' participant-level identifier columns, or retained raw workflow objects.
#'
#' @param x Object returned by [run_gazepoint_real_data_smoke()].
#' @param private_values Optional private path strings that must not occur in
#'   the object.
#'
#' @return A data frame of privacy checks and pass/fail statuses.
#'
#' @export
audit_gazepoint_smoke_privacy <- function(
    x,
    private_values = NULL) {
  required_components <- c(
    "results",
    "conditions",
    "session",
    "settings"
  )

  component_check <- all(
    required_components %in% names(x)
  )

  data_frames_only <- component_check &&
    all(
      vapply(
        x[required_components],
        is.data.frame,
        logical(1)
      )
    )

  all_names <- if (data_frames_only) {
    unlist(
      lapply(
        x[required_components],
        names
      ),
      use.names = FALSE
    )
  } else {
    character()
  }

  forbidden_columns <- c(
    "path",
    "file_path",
    "filepath",
    "filename",
    "file_name",
    "source_file",
    "source_filename",
    "participant",
    "participant_id",
    "subject",
    "subject_id",
    "user",
    "user_id",
    "raw_data",
    "workflow"
  )

  forbidden_column_hits <- intersect(
    tolower(all_names),
    forbidden_columns
  )

  serialized_values <- if (data_frames_only) {
    unlist(
      lapply(
        x[required_components],
        function(data) {
          as.character(
            unlist(
              data,
              recursive = TRUE,
              use.names = FALSE
            )
          )
        }
      ),
      use.names = FALSE
    )
  } else {
    character()
  }

  serialized_values <- serialized_values[
    !is.na(serialized_values)
  ]

  absolute_path_pattern <- paste0(
    "(",
    "[A-Za-z]:[/\\\\]",
    "|",
    "(^|[[:space:]])/[A-Za-z0-9._-]+/",
    ")"
  )

  path_hits <- if (
    length(serialized_values) > 0L
  ) {
    grepl(
      absolute_path_pattern,
      serialized_values,
      perl = TRUE
    )
  } else {
    logical()
  }

  private_hits <- logical(
    length(serialized_values)
  )

  if (
    length(private_values) > 0L &&
    length(serialized_values) > 0L
  ) {
    private_values <- unique(
      private_values[
        !is.na(private_values) &
          nzchar(private_values)
      ]
    )

    for (private_value in private_values) {
      private_hits <- private_hits |
        grepl(
          private_value,
          serialized_values,
          fixed = TRUE
        )
    }
  }

  raw_object_names <- setdiff(
    names(x),
    c(
      required_components,
      "written_files"
    )
  )

  checks <- data.frame(
    check = c(
      "required_components",
      "aggregate_data_frames_only",
      "no_forbidden_columns",
      "no_absolute_paths",
      "no_private_values",
      "no_raw_workflow_objects"
    ),
    status = c(
      if (component_check) {
        "pass"
      } else {
        "fail"
      },
      if (data_frames_only) {
        "pass"
      } else {
        "fail"
      },
      if (length(forbidden_column_hits) == 0L) {
        "pass"
      } else {
        "fail"
      },
      if (!any(path_hits)) {
        "pass"
      } else {
        "fail"
      },
      if (!any(private_hits)) {
        "pass"
      } else {
        "fail"
      },
      if (length(raw_object_names) == 0L) {
        "pass"
      } else {
        "fail"
      }
    ),
    message = c(
      if (component_check) {
        "All required aggregate components are present."
      } else {
        "One or more required aggregate components are missing."
      },
      if (data_frames_only) {
        "All retained components are aggregate data frames."
      } else {
        "One or more retained components are not data frames."
      },
      if (length(forbidden_column_hits) == 0L) {
        "No participant, filename, path, or raw-data columns were found."
      } else {
        paste0(
          "Forbidden columns found: ",
          paste(
            forbidden_column_hits,
            collapse = ", "
          ),
          "."
        )
      },
      if (!any(path_hits)) {
        "No absolute path-like values were found."
      } else {
        "One or more absolute path-like values were found."
      },
      if (!any(private_hits)) {
        "No supplied private values were found."
      } else {
        "One or more supplied private values were found."
      },
      if (length(raw_object_names) == 0L) {
        "No raw workflow objects were retained."
      } else {
        paste0(
          "Unexpected retained components: ",
          paste(
            raw_object_names,
            collapse = ", "
          ),
          "."
        )
      }
    ),
    stringsAsFactors = FALSE
  )

  class(checks) <- c(
    "gazepoint_smoke_privacy_audit",
    "data.frame"
  )

  checks
}


#' Write privacy-safe real-data smoke-test summaries
#'
#' Writes only aggregate dataset summaries, sanitized condition information,
#' runtime metadata, and non-sensitive settings.
#'
#' @param x Object returned by [run_gazepoint_real_data_smoke()].
#' @param output_dir External output directory.
#' @param prefix Output filename prefix.
#' @param overwrite Permit replacement of existing files?
#' @param protect_repository Reject output directories inside the current
#'   package repository?
#'
#' @return Invisibly returns a named character vector of written files.
#'
#' @export
write_gazepoint_real_data_smoke <- function(
    x,
    output_dir,
    prefix = "gpbiometrics-real-data-smoke",
    overwrite = FALSE,
    protect_repository = TRUE) {
  if (!inherits(x, "gazepoint_real_data_smoke")) {
    stop(
      "`x` must be returned by ",
      "`run_gazepoint_real_data_smoke()`.",
      call. = FALSE
    )
  }

  .gpbiometrics_smoke_assert_flag(
    overwrite,
    "overwrite"
  )

  .gpbiometrics_smoke_assert_flag(
    protect_repository,
    "protect_repository"
  )

  output_dir <-
    .gpbiometrics_smoke_validate_directory(
      output_dir,
      argument = "output_dir",
      must_exist = FALSE
    )

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

  repository_root <-
    .gpbiometrics_smoke_repository_root()

  if (
    isTRUE(protect_repository) &&
    !is.null(repository_root) &&
    .gpbiometrics_smoke_is_within(
      output_dir,
      repository_root
    )
  ) {
    stop(
      "Smoke-test outputs must remain outside the package repository.",
      call. = FALSE
    )
  }

  privacy <- audit_gazepoint_smoke_privacy(
    x
  )

  if (!all(privacy$status == "pass")) {
    stop(
      "Refusing to write a smoke-test object that failed its privacy audit.",
      call. = FALSE
    )
  }

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
      paste0(
        prefix,
        "-results.csv"
      )
    ),
    conditions = file.path(
      output_dir,
      paste0(
        prefix,
        "-conditions.csv"
      )
    ),
    session = file.path(
      output_dir,
      paste0(
        prefix,
        "-session.csv"
      )
    ),
    settings = file.path(
      output_dir,
      paste0(
        prefix,
        "-settings.csv"
      )
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
    x$conditions,
    files[["conditions"]],
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
    x$settings,
    files[["settings"]],
    row.names = FALSE,
    na = ""
  )

  normalized <- normalizePath(
    unname(files),
    winslash = "/",
    mustWork = TRUE
  )

  names(normalized) <- names(files)

  invisible(normalized)
}


#' @export
print.gazepoint_real_data_smoke <- function(
    x,
    ...) {
  status_counts <- table(
    x$results$smoke_status
  )

  cat(
    "<gazepoint_real_data_smoke>\n",
    sep = ""
  )

  cat(
    "Datasets: ",
    NROW(x$results),
    "\n",
    sep = ""
  )

  for (status in c(
    "pass",
    "review",
    "fail"
  )) {
    count <- if (
      status %in% names(status_counts)
    ) {
      unname(
        status_counts[[status]]
      )
    } else {
      0L
    }

    cat(
      paste0(
        tools::toTitleCase(status),
        ": ",
        count,
        "\n"
      )
    )
  }

  cat(
    "Private data retained: FALSE\n",
    sep = ""
  )

  invisible(x)
}


.gpbiometrics_smoke_discover_datasets <- function(
    data_dir,
    dataset_mode,
    pattern,
    recursive) {
  if (identical(dataset_mode, "root")) {
    candidate_paths <- data_dir
  } else {
    candidate_paths <- list.dirs(
      data_dir,
      full.names = TRUE,
      recursive = FALSE
    )

    candidate_paths <- candidate_paths[
      !grepl(
        "^\\.",
        basename(candidate_paths)
      )
    ]

    has_matching_files <- vapply(
      candidate_paths,
      function(path) {
        length(
          list.files(
            path,
            pattern = pattern,
            recursive = recursive,
            full.names = TRUE,
            ignore.case = TRUE
          )
        ) > 0L
      },
      logical(1)
    )

    candidate_paths <- candidate_paths[
      has_matching_files
    ]

    if (
      length(candidate_paths) == 0L &&
      length(
        list.files(
          data_dir,
          pattern = pattern,
          recursive = recursive,
          full.names = TRUE,
          ignore.case = TRUE
        )
      ) > 0L
    ) {
      candidate_paths <- data_dir
    }
  }

  candidate_paths <- sort(
    unique(candidate_paths)
  )

  lapply(
    seq_along(candidate_paths),
    function(index) {
      path <- candidate_paths[[index]]

      all_files <- list.files(
        path,
        recursive = recursive,
        full.names = TRUE,
        all.files = FALSE,
        no.. = TRUE
      )

      all_files <- all_files[
        file.exists(all_files) &
          !dir.exists(all_files)
      ]

      matching_files <- list.files(
        path,
        pattern = pattern,
        recursive = recursive,
        full.names = TRUE,
        ignore.case = TRUE
      )

      matching_files <- matching_files[
        file.exists(matching_files) &
          !dir.exists(matching_files)
      ]

      sizes <- file.info(
        all_files
      )$size

      list(
        dataset_id = sprintf(
          "smoke_%03d",
          index
        ),
        path = path,
        n_files = length(all_files),
        n_csv_files = length(matching_files),
        total_bytes = sum(
          sizes,
          na.rm = TRUE
        )
      )
    }
  )
}


.gpbiometrics_smoke_capture <- function(
    thunk,
    private_values) {
  warnings <- character()
  messages <- character()
  error <- NULL

  value <- tryCatch(
    withCallingHandlers(
      thunk(),
      warning = function(condition) {
        warnings <<- c(
          warnings,
          conditionMessage(condition)
        )

        invokeRestart(
          "muffleWarning"
        )
      },
      message = function(condition) {
        messages <<- c(
          messages,
          conditionMessage(condition)
        )

        invokeRestart(
          "muffleMessage"
        )
      }
    ),
    error = function(condition) {
      error <<- condition
      NULL
    }
  )

  warnings <- vapply(
    warnings,
    .gpbiometrics_smoke_sanitize_message,
    character(1),
    private_values = private_values
  )

  messages <- vapply(
    messages,
    .gpbiometrics_smoke_sanitize_message,
    character(1),
    private_values = private_values
  )

  error_message <- if (is.null(error)) {
    NA_character_
  } else {
    .gpbiometrics_smoke_sanitize_message(
      conditionMessage(error),
      private_values = private_values
    )
  }

  list(
    ok = is.null(error),
    status = if (
      is.null(error)
    ) {
      "completed"
    } else {
      "error"
    },
    value = value,
    warnings = unname(warnings),
    messages = unname(messages),
    error_class = if (
      is.null(error)
    ) {
      NA_character_
    } else {
      class(error)[[1L]]
    },
    error_message = error_message
  )
}


.gpbiometrics_smoke_empty_capture <- function(
    status = "not_run") {
  list(
    ok = FALSE,
    status = status,
    value = NULL,
    warnings = character(),
    messages = character(),
    error_class = NA_character_,
    error_message = NA_character_
  )
}


.gpbiometrics_smoke_sanitize_message <- function(
    message,
    private_values = NULL) {
  if (
    length(message) == 0L ||
    is.na(message)
  ) {
    return(NA_character_)
  }

  message <- as.character(
    message[[1L]]
  )

  if (length(private_values) > 0L) {
    private_values <- unique(
      private_values[
        !is.na(private_values) &
          nzchar(private_values)
      ]
    )

    private_values <- private_values[
      order(
        nchar(private_values),
        decreasing = TRUE
      )
    ]

    for (private_value in private_values) {
      variants <- unique(
        c(
          private_value,
          gsub(
            "\\\\",
            "/",
            private_value
          ),
          gsub(
            "/",
            "\\\\",
            private_value,
            fixed = TRUE
          )
        )
      )

      for (variant in variants) {
        message <- gsub(
          variant,
          "<private-path>",
          message,
          fixed = TRUE
        )
      }
    }
  }

  message <- gsub(
    "[A-Za-z]:[/\\\\][^[:space:]]+",
    "<private-path>",
    message,
    perl = TRUE
  )

  message <- gsub(
    "(^|[[:space:]])/[^[:space:]]+",
    "\\1<private-path>",
    message,
    perl = TRUE
  )

  message <- gsub(
    "[^[:space:]/\\\\]+\\.[Cc][Ss][Vv]\\b",
    "<private-file>.csv",
    message,
    perl = TRUE
  )

  message <- gsub(
    "[[:alnum:]._%+-]+@[[:alnum:].-]+\\.[A-Za-z]{2,}",
    "<private-email>",
    message,
    perl = TRUE
  )

  message <- gsub(
    "\"[^\"]*\"",
    "\"<redacted>\"",
    message,
    perl = TRUE
  )

  message <- gsub(
    "'[^']*'",
    "'<redacted>'",
    message,
    perl = TRUE
  )

  message <- gsub(
    "\\b[A-Z]{1,5}[0-9]{2,}\\b",
    "<private-identifier>",
    message,
    perl = TRUE
  )

  message <- gsub(
    "[\r\n\t]+",
    " ",
    message
  )

  message <- trimws(
    message
  )

  if (nchar(message) > 300L) {
    message <- paste0(
      substr(
        message,
        1L,
        297L
      ),
      "..."
    )
  }

  message
}


.gpbiometrics_smoke_condition_rows <- function(
    dataset_id,
    captures) {
  rows <- list()
  counter <- 0L

  for (stage in names(captures)) {
    capture <- captures[[stage]]

    if (length(capture$warnings) > 0L) {
      for (message in capture$warnings) {
        counter <- counter + 1L

        rows[[counter]] <- data.frame(
          dataset_id = dataset_id,
          stage = stage,
          condition_type = "warning",
          condition_class = "warning",
          message = message,
          stringsAsFactors = FALSE
        )
      }
    }

    if (length(capture$messages) > 0L) {
      for (message in capture$messages) {
        counter <- counter + 1L

        rows[[counter]] <- data.frame(
          dataset_id = dataset_id,
          stage = stage,
          condition_type = "message",
          condition_class = "message",
          message = message,
          stringsAsFactors = FALSE
        )
      }
    }

    if (
      identical(
        capture$status,
        "error"
      )
    ) {
      counter <- counter + 1L

      rows[[counter]] <- data.frame(
        dataset_id = dataset_id,
        stage = stage,
        condition_type = "error",
        condition_class =
          capture$error_class,
        message =
          capture$error_message,
        stringsAsFactors = FALSE
      )
    }
  }

  if (length(rows) == 0L) {
    return(
      data.frame(
        dataset_id = character(),
        stage = character(),
        condition_type = character(),
        condition_class = character(),
        message = character(),
        stringsAsFactors = FALSE
      )
    )
  }

  output <- do.call(
    rbind,
    rows
  )

  rownames(output) <- NULL

  output
}


.gpbiometrics_smoke_bind_conditions <- function(
    condition_rows) {
  condition_rows <- Filter(
    function(data) {
      is.data.frame(data) &&
        NROW(data) > 0L
    },
    condition_rows
  )

  if (length(condition_rows) == 0L) {
    return(
      data.frame(
        dataset_id = character(),
        stage = character(),
        condition_type = character(),
        condition_class = character(),
        message = character(),
        stringsAsFactors = FALSE
      )
    )
  }

  output <- do.call(
    rbind,
    condition_rows
  )

  rownames(output) <- NULL

  output
}


.gpbiometrics_smoke_diagnostic_status <- function(
    diagnostic) {
  value <- .gpbiometrics_smoke_extract_character(
    diagnostic,
    c(
      "status",
      "readiness_status",
      "overall_status",
      "decision"
    )
  )

  if (
    is.na(value) ||
    !nzchar(value)
  ) {
    return(
      if (is.null(diagnostic)) {
        "not_available"
      } else {
        "completed"
      }
    )
  }

  value <- tolower(
    trimws(value)
  )

  if (
    value %in%
    c(
      "pass",
      "passed",
      "ready",
      "ok",
      "complete",
      "completed"
    )
  ) {
    return("pass")
  }

  if (
    value %in%
    c(
      "review",
      "warning",
      "warn",
      "caution",
      "partial"
    )
  ) {
    return("review")
  }

  if (
    value %in%
    c(
      "fail",
      "failed",
      "not_ready",
      "error",
      "exclude"
    )
  ) {
    return("fail")
  }

  value
}


.gpbiometrics_smoke_extract_numeric <- function(
    object,
    candidates) {
  value <- .gpbiometrics_smoke_extract_value(
    object,
    candidates
  )

  if (
    length(value) == 0L ||
    is.null(value) ||
    all(is.na(value))
  ) {
    return(NA_real_)
  }

  converted <- suppressWarnings(
    as.numeric(
      value[[1L]]
    )
  )

  if (
    length(converted) == 0L ||
    is.na(converted)
  ) {
    return(NA_real_)
  }

  converted
}


.gpbiometrics_smoke_extract_character <- function(
    object,
    candidates) {
  value <- .gpbiometrics_smoke_extract_value(
    object,
    candidates
  )

  if (
    length(value) == 0L ||
    is.null(value) ||
    all(is.na(value))
  ) {
    return(NA_character_)
  }

  as.character(
    value[[1L]]
  )
}


.gpbiometrics_smoke_extract_value <- function(
    object,
    candidates) {
  if (is.null(object)) {
    return(NULL)
  }

  candidates <- tolower(
    candidates
  )

  if (
    is.data.frame(object) ||
    is.list(object)
  ) {
    object_names <- names(object)

    if (!is.null(object_names)) {
      matched <- match(
        candidates,
        tolower(object_names),
        nomatch = 0L
      )

      matched <- matched[
        matched > 0L
      ]

      if (length(matched) > 0L) {
        value <- object[[matched[[1L]]]]

        if (length(value) > 0L) {
          return(value)
        }
      }
    }

    if (is.list(object)) {
      for (element in object) {
        value <-
          .gpbiometrics_smoke_extract_value(
            element,
            candidates
          )

        if (
          !is.null(value) &&
          length(value) > 0L
        ) {
          return(value)
        }
      }
    }
  }

  NULL
}


.gpbiometrics_smoke_validate_directory <- function(
    value,
    argument,
    must_exist) {
  if (
    is.null(value) ||
    !is.character(value) ||
    length(value) != 1L ||
    is.na(value) ||
    !nzchar(trimws(value))
  ) {
    stop(
      "`",
      argument,
      "` must be one non-empty directory path.",
      call. = FALSE
    )
  }

  if (
    isTRUE(must_exist) &&
    !dir.exists(value)
  ) {
    stop(
      "`",
      argument,
      "` does not exist or is not a directory.",
      call. = FALSE
    )
  }

  if (dir.exists(value)) {
    return(
      normalizePath(
        value,
        winslash = "/",
        mustWork = TRUE
      )
    )
  }

  parent <- dirname(value)

  if (!dir.exists(parent)) {
    dir.create(
      parent,
      recursive = TRUE,
      showWarnings = FALSE
    )
  }

  normalized_parent <- normalizePath(
    parent,
    winslash = "/",
    mustWork = TRUE
  )

  file.path(
    normalized_parent,
    basename(value)
  )
}


.gpbiometrics_smoke_repository_root <- function(
    start = getwd()) {
  current <- normalizePath(
    start,
    winslash = "/",
    mustWork = TRUE
  )

  repeat {
    if (
      file.exists(
        file.path(
          current,
          "DESCRIPTION"
        )
      ) &&
      dir.exists(
        file.path(
          current,
          ".git"
        )
      )
    ) {
      return(current)
    }

    parent <- dirname(current)

    if (identical(parent, current)) {
      break
    }

    current <- parent
  }

  NULL
}


.gpbiometrics_smoke_is_within <- function(
    path,
    parent) {
  normalized_path <- normalizePath(
    path,
    winslash = "/",
    mustWork = FALSE
  )

  normalized_parent <- normalizePath(
    parent,
    winslash = "/",
    mustWork = TRUE
  )

  if (identical(.Platform$OS.type, "windows")) {
    normalized_path <- tolower(
      normalized_path
    )

    normalized_parent <- tolower(
      normalized_parent
    )
  }

  identical(
    normalized_path,
    normalized_parent
  ) ||
    startsWith(
      normalized_path,
      paste0(
        normalized_parent,
        "/"
      )
    )
}


.gpbiometrics_smoke_assert_flag <- function(
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


.gpbiometrics_smoke_package_version <- function() {
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


.gpbiometrics_smoke_os_string <- function() {
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
