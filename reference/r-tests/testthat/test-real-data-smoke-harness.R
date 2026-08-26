local_make_smoke_tree <- function(
    dataset_names = c(
      "complete_recording",
      "dropout_recording"
    )) {
  root <- tempfile(
    "gpbiometrics-private-smoke-"
  )

  dir.create(
    root,
    recursive = TRUE,
    showWarnings = FALSE
  )

  for (dataset_name in dataset_names) {
    dataset_dir <- file.path(
      root,
      dataset_name
    )

    dir.create(
      dataset_dir,
      recursive = TRUE,
      showWarnings = FALSE
    )

    utils::write.csv(
      data.frame(
        TIME = seq(
          0,
          0.4,
          by = 0.1
        ),
        GSR = c(
          0.1,
          0.11,
          0.12,
          0.11,
          0.13
        ),
        HR = c(
          70,
          71,
          70,
          72,
          71
        )
      ),
      file.path(
        dataset_dir,
        "private-participant-P001.csv"
      ),
      row.names = FALSE
    )
  }

  root
}


local_smoke_workflow_runner <- function(
    path,
    ...) {
  list(
    imported = TRUE,
    internal_path = path
  )
}


local_smoke_summary_runner <- function(
    workflow) {
  data.frame(
    n_rows = 120,
    n_participants = 2,
    n_trials = 4,
    n_events = 8,
    detected_schema = "Gazepoint Biometrics",
    active_signal_groups = 3,
    stringsAsFactors = FALSE
  )
}


local_smoke_diagnostic_runner <- function(
    workflow,
    ...) {
  data.frame(
    status = "pass",
    reason = "Synthetic contract is ready.",
    stringsAsFactors = FALSE
  )
}


test_that("smoke harness requires an external data directory", {
  expect_error(
    run_gazepoint_real_data_smoke(
      data_dir = "",
      workflow_runner =
        local_smoke_workflow_runner,
      summary_runner =
        local_smoke_summary_runner,
      diagnostic_runner =
        local_smoke_diagnostic_runner
    ),
    "`data_dir` must be one non-empty directory path"
  )

  expect_error(
    run_gazepoint_real_data_smoke(
      data_dir = file.path(
        tempdir(),
        "directory-that-does-not-exist"
      ),
      workflow_runner =
        local_smoke_workflow_runner,
      summary_runner =
        local_smoke_summary_runner,
      diagnostic_runner =
        local_smoke_diagnostic_runner
    ),
    "does not exist"
  )
})


test_that("subdirectories become anonymized aggregate datasets", {
  root <- local_make_smoke_tree()

  on.exit(
    unlink(
      root,
      recursive = TRUE,
      force = TRUE
    ),
    add = TRUE
  )

  smoke <- run_gazepoint_real_data_smoke(
    data_dir = root,
    dataset_mode = "subdirectories",
    workflow_runner =
      local_smoke_workflow_runner,
    summary_runner =
      local_smoke_summary_runner,
    diagnostic_runner =
      local_smoke_diagnostic_runner
  )

  expect_s3_class(
    smoke,
    "gazepoint_real_data_smoke"
  )

  expect_named(
    smoke,
    c(
      "results",
      "conditions",
      "session",
      "settings"
    )
  )

  expect_identical(
    smoke$results$dataset_id,
    c(
      "smoke_001",
      "smoke_002"
    )
  )

  expect_identical(
    smoke$results$n_csv_files,
    c(
      1L,
      1L
    )
  )

  expect_true(
    all(
      smoke$results$workflow_ok
    )
  )

  expect_true(
    all(
      smoke$results$summary_ok
    )
  )

  expect_true(
    all(
      smoke$results$diagnostic_ok
    )
  )

  expect_true(
    all(
      smoke$results$smoke_status ==
        "pass"
    )
  )

  expect_true(
    all(
      smoke$results$n_rows == 120
    )
  )

  expect_true(
    all(
      smoke$results$n_participants == 2
    )
  )

  expect_true(
    all(
      smoke$results$n_trials == 4
    )
  )

  expect_true(
    all(
      smoke$results$n_events == 8
    )
  )

  expect_false(
    any(
      basename(
        list.dirs(
          root,
          recursive = FALSE
        )
      ) %in%
        smoke$results$dataset_id
    )
  )

  privacy <- attr(
    smoke,
    "privacy_audit"
  )

  expect_s3_class(
    privacy,
    "gazepoint_smoke_privacy_audit"
  )

  expect_true(
    all(
      privacy$status == "pass"
    )
  )
})


test_that("root mode treats one folder as one dataset", {
  root <- local_make_smoke_tree(
    dataset_names = "single_dataset"
  )

  on.exit(
    unlink(
      root,
      recursive = TRUE,
      force = TRUE
    ),
    add = TRUE
  )

  smoke <- run_gazepoint_real_data_smoke(
    data_dir = file.path(
      root,
      "single_dataset"
    ),
    dataset_mode = "root",
    workflow_runner =
      local_smoke_workflow_runner,
    summary_runner =
      local_smoke_summary_runner,
    diagnostic_runner =
      local_smoke_diagnostic_runner
  )

  expect_equal(
    NROW(smoke$results),
    1L
  )

  expect_identical(
    smoke$results$dataset_id,
    "smoke_001"
  )
})


test_that("warnings and messages are sanitized", {
  root <- local_make_smoke_tree(
    dataset_names = "warning_dataset"
  )

  on.exit(
    unlink(
      root,
      recursive = TRUE,
      force = TRUE
    ),
    add = TRUE
  )

  noisy_runner <- function(
    path,
    ...) {
    message(
      "Reading ",
      file.path(
        path,
        "participant-P998.csv"
      )
    )

    warning(
      paste0(
        "Review participant P998 at ",
        file.path(
          path,
          "participant-P998.csv"
        ),
        " and contact private.person@example.org"
      ),
      call. = FALSE
    )

    list(
      internal_path = path
    )
  }

  smoke <- run_gazepoint_real_data_smoke(
    data_dir = root,
    workflow_runner = noisy_runner,
    summary_runner =
      local_smoke_summary_runner,
    diagnostic_runner =
      local_smoke_diagnostic_runner
  )

  expect_identical(
    smoke$results$smoke_status,
    "review"
  )

  expect_equal(
    smoke$results$n_warnings,
    1L
  )

  expect_equal(
    smoke$results$n_messages,
    1L
  )

  expect_true(
    all(
      c(
        "warning",
        "message"
      ) %in%
        smoke$conditions$condition_type
    )
  )

  retained_text <- paste(
    unlist(
      smoke[
        c(
          "results",
          "conditions",
          "session",
          "settings"
        )
      ],
      recursive = TRUE,
      use.names = FALSE
    ),
    collapse = " "
  )

  expect_false(
    grepl(
      root,
      retained_text,
      fixed = TRUE
    )
  )

  expect_false(
    grepl(
      "participant-P998.csv",
      retained_text,
      fixed = TRUE
    )
  )

  expect_false(
    grepl(
      "private.person@example.org",
      retained_text,
      fixed = TRUE
    )
  )

  expect_match(
    retained_text,
    "<private-path>|<private-file>|<private-email>"
  )
})


test_that("workflow errors are aggregated without retaining paths", {
  root <- local_make_smoke_tree(
    dataset_names = c(
      "a_failure",
      "b_success"
    )
  )

  on.exit(
    unlink(
      root,
      recursive = TRUE,
      force = TRUE
    ),
    add = TRUE
  )

  conditional_runner <- function(
    path,
    ...) {
    if (
      grepl(
        "failure",
        basename(path),
        fixed = TRUE
      )
    ) {
      stop(
        "Could not import ",
        file.path(
          path,
          "participant-P432.csv"
        ),
        call. = FALSE
      )
    }

    list(
      internal_path = path
    )
  }

  smoke <- run_gazepoint_real_data_smoke(
    data_dir = root,
    workflow_runner = conditional_runner,
    summary_runner =
      local_smoke_summary_runner,
    diagnostic_runner =
      local_smoke_diagnostic_runner,
    stop_on_error = FALSE
  )

  expect_equal(
    NROW(smoke$results),
    2L
  )

  expect_identical(
    smoke$results$smoke_status,
    c(
      "fail",
      "pass"
    )
  )

  expect_identical(
    smoke$results$error_stage[[1L]],
    "workflow"
  )

  expect_false(
    grepl(
      root,
      smoke$results$error_message[[1L]],
      fixed = TRUE
    )
  )

  expect_false(
    grepl(
      "participant-P432.csv",
      smoke$results$error_message[[1L]],
      fixed = TRUE
    )
  )
})


test_that("stop_on_error stops after the first failed dataset", {
  root <- local_make_smoke_tree(
    dataset_names = c(
      "a_failure",
      "b_success"
    )
  )

  on.exit(
    unlink(
      root,
      recursive = TRUE,
      force = TRUE
    ),
    add = TRUE
  )

  conditional_runner <- function(
    path,
    ...) {
    if (
      grepl(
        "failure",
        basename(path),
        fixed = TRUE
      )
    ) {
      stop(
        "Synthetic workflow failure.",
        call. = FALSE
      )
    }

    list(
      internal_path = path
    )
  }

  smoke <- run_gazepoint_real_data_smoke(
    data_dir = root,
    workflow_runner = conditional_runner,
    summary_runner =
      local_smoke_summary_runner,
    diagnostic_runner =
      local_smoke_diagnostic_runner,
    stop_on_error = TRUE
  )

  expect_equal(
    NROW(smoke$results),
    1L
  )

  expect_identical(
    smoke$results$smoke_status,
    "fail"
  )
})


test_that("diagnostic review and failure states are respected", {
  root <- local_make_smoke_tree(
    dataset_names = "diagnostic_dataset"
  )

  on.exit(
    unlink(
      root,
      recursive = TRUE,
      force = TRUE
    ),
    add = TRUE
  )

  review_smoke <- run_gazepoint_real_data_smoke(
    data_dir = root,
    workflow_runner =
      local_smoke_workflow_runner,
    summary_runner =
      local_smoke_summary_runner,
    diagnostic_runner = function(
    workflow,
    ...) {
      data.frame(
        status = "review",
        stringsAsFactors = FALSE
      )
    }
  )

  expect_identical(
    review_smoke$results$smoke_status,
    "review"
  )

  fail_smoke <- run_gazepoint_real_data_smoke(
    data_dir = root,
    workflow_runner =
      local_smoke_workflow_runner,
    summary_runner =
      local_smoke_summary_runner,
    diagnostic_runner = function(
    workflow,
    ...) {
      data.frame(
        status = "fail",
        stringsAsFactors = FALSE
      )
    }
  )

  expect_identical(
    fail_smoke$results$smoke_status,
    "fail"
  )

  expect_identical(
    fail_smoke$results$error_stage,
    "diagnostic"
  )
})


test_that("privacy audit detects unsafe retained content", {
  safe <- list(
    results = data.frame(
      dataset_id = "smoke_001",
      smoke_status = "pass",
      stringsAsFactors = FALSE
    ),
    conditions = data.frame(
      dataset_id = character(),
      stage = character(),
      condition_type = character(),
      condition_class = character(),
      message = character(),
      stringsAsFactors = FALSE
    ),
    session = data.frame(
      r_version = R.version.string,
      stringsAsFactors = FALSE
    ),
    settings = data.frame(
      private_data_retained = FALSE,
      stringsAsFactors = FALSE
    )
  )

  safe_audit <- audit_gazepoint_smoke_privacy(
    safe
  )

  expect_true(
    all(
      safe_audit$status == "pass"
    )
  )

  unsafe_column <- safe
  unsafe_column$results$participant_id <-
    "P001"

  column_audit <- audit_gazepoint_smoke_privacy(
    unsafe_column
  )

  expect_identical(
    column_audit$status[
      column_audit$check ==
        "no_forbidden_columns"
    ],
    "fail"
  )

  unsafe_path <- safe
  unsafe_path$conditions <- data.frame(
    dataset_id = "smoke_001",
    stage = "workflow",
    condition_type = "error",
    condition_class = "error",
    message =
      "C:/Private/Study/participant-P001.csv",
    stringsAsFactors = FALSE
  )

  path_audit <- audit_gazepoint_smoke_privacy(
    unsafe_path,
    private_values =
      "C:/Private/Study"
  )

  expect_identical(
    path_audit$status[
      path_audit$check ==
        "no_absolute_paths"
    ],
    "fail"
  )

  expect_identical(
    path_audit$status[
      path_audit$check ==
        "no_private_values"
    ],
    "fail"
  )
})


test_that("writer creates four aggregate files outside the repository", {
  root <- local_make_smoke_tree(
    dataset_names = "writer_dataset"
  )

  output_dir <- tempfile(
    "gpbiometrics-smoke-output-"
  )

  on.exit(
    {
      unlink(
        root,
        recursive = TRUE,
        force = TRUE
      )

      unlink(
        output_dir,
        recursive = TRUE,
        force = TRUE
      )
    },
    add = TRUE
  )

  smoke <- run_gazepoint_real_data_smoke(
    data_dir = root,
    workflow_runner =
      local_smoke_workflow_runner,
    summary_runner =
      local_smoke_summary_runner,
    diagnostic_runner =
      local_smoke_diagnostic_runner
  )

  files <- write_gazepoint_real_data_smoke(
    smoke,
    output_dir = output_dir
  )

  expect_length(
    files,
    4L
  )

  expect_named(
    files,
    c(
      "results",
      "conditions",
      "session",
      "settings"
    )
  )

  expect_true(
    all(
      file.exists(files)
    )
  )

  written_results <- utils::read.csv(
    files[["results"]],
    stringsAsFactors = FALSE
  )

  expect_true(
    all(
      c(
        "dataset_id",
        "n_files",
        "smoke_status",
        "n_warnings",
        "elapsed_seconds"
      ) %in%
        names(written_results)
    )
  )

  expect_false(
    any(
      c(
        "participant_id",
        "filename",
        "file_path",
        "path",
        "workflow"
      ) %in%
        names(written_results)
    )
  )

  expect_error(
    write_gazepoint_real_data_smoke(
      smoke,
      output_dir = output_dir
    ),
    "Refusing to overwrite"
  )

  expect_silent(
    write_gazepoint_real_data_smoke(
      smoke,
      output_dir = output_dir,
      overwrite = TRUE
    )
  )
})


test_that("run-and-write mode records written files as an attribute", {
  root <- local_make_smoke_tree(
    dataset_names = "automatic_writer"
  )

  output_dir <- tempfile(
    "gpbiometrics-smoke-auto-output-"
  )

  on.exit(
    {
      unlink(
        root,
        recursive = TRUE,
        force = TRUE
      )

      unlink(
        output_dir,
        recursive = TRUE,
        force = TRUE
      )
    },
    add = TRUE
  )

  smoke <- run_gazepoint_real_data_smoke(
    data_dir = root,
    output_dir = output_dir,
    workflow_runner =
      local_smoke_workflow_runner,
    summary_runner =
      local_smoke_summary_runner,
    diagnostic_runner =
      local_smoke_diagnostic_runner,
    write_results = TRUE
  )

  written_files <- attr(
    smoke,
    "written_files"
  )

  expect_length(
    written_files,
    4L
  )

  expect_true(
    all(
      file.exists(written_files)
    )
  )
})


test_that("workflow and diagnostic reserved arguments are rejected", {
  root <- local_make_smoke_tree(
    dataset_names = "argument_dataset"
  )

  on.exit(
    unlink(
      root,
      recursive = TRUE,
      force = TRUE
    ),
    add = TRUE
  )

  expect_error(
    run_gazepoint_real_data_smoke(
      data_dir = root,
      workflow_args = list(
        path = "not-allowed"
      ),
      workflow_runner =
        local_smoke_workflow_runner,
      summary_runner =
        local_smoke_summary_runner,
      diagnostic_runner =
        local_smoke_diagnostic_runner
    ),
    "must not contain `path`"
  )

  expect_error(
    run_gazepoint_real_data_smoke(
      data_dir = root,
      diagnostic_args = list(
        workflow = "not-allowed"
      ),
      workflow_runner =
        local_smoke_workflow_runner,
      summary_runner =
        local_smoke_summary_runner,
      diagnostic_runner =
        local_smoke_diagnostic_runner
    ),
    "must not contain `workflow`"
  )
})


test_that("runner arguments must be functions", {
  root <- local_make_smoke_tree(
    dataset_names = "runner_dataset"
  )

  on.exit(
    unlink(
      root,
      recursive = TRUE,
      force = TRUE
    ),
    add = TRUE
  )

  expect_error(
    run_gazepoint_real_data_smoke(
      data_dir = root,
      workflow_runner = "not-a-function",
      summary_runner =
        local_smoke_summary_runner,
      diagnostic_runner =
        local_smoke_diagnostic_runner
    ),
    "not functions"
  )
})


test_that("repository protection rejects repository-local paths", {
  fake_repository <- tempfile(
    "gpbiometrics-fake-repository-"
  )

  dir.create(
    file.path(
      fake_repository,
      ".git"
    ),
    recursive = TRUE,
    showWarnings = FALSE
  )

  writeLines(
    c(
      "Package: gpbiometricsFakeRepository",
      "Version: 0.0.0"
    ),
    file.path(
      fake_repository,
      "DESCRIPTION"
    )
  )

  nested_working_directory <- file.path(
    fake_repository,
    "tests",
    "testthat"
  )

  dir.create(
    nested_working_directory,
    recursive = TRUE,
    showWarnings = FALSE
  )

  unsafe_data_dir <- file.path(
    fake_repository,
    "private-data-smoke-test"
  )

  dir.create(
    unsafe_data_dir,
    recursive = TRUE,
    showWarnings = FALSE
  )

  utils::write.csv(
    data.frame(
      TIME = 0,
      GSR = 0.1
    ),
    file.path(
      unsafe_data_dir,
      "synthetic.csv"
    ),
    row.names = FALSE
  )

  external_data_dir <- local_make_smoke_tree(
    dataset_names = "external_dataset"
  )

  unsafe_output_dir <- file.path(
    fake_repository,
    "smoke-test-output"
  )

  original_working_directory <- getwd()

  on.exit(
    {
      setwd(
        original_working_directory
      )

      unlink(
        fake_repository,
        recursive = TRUE,
        force = TRUE
      )

      unlink(
        external_data_dir,
        recursive = TRUE,
        force = TRUE
      )
    },
    add = TRUE
  )

  setwd(
    nested_working_directory
  )

  expect_error(
    run_gazepoint_real_data_smoke(
      data_dir = unsafe_data_dir,
      workflow_runner =
        local_smoke_workflow_runner,
      summary_runner =
        local_smoke_summary_runner,
      diagnostic_runner =
        local_smoke_diagnostic_runner,
      protect_repository = TRUE
    ),
    "must remain outside the package repository"
  )

  expect_error(
    run_gazepoint_real_data_smoke(
      data_dir = external_data_dir,
      output_dir = unsafe_output_dir,
      workflow_runner =
        local_smoke_workflow_runner,
      summary_runner =
        local_smoke_summary_runner,
      diagnostic_runner =
        local_smoke_diagnostic_runner,
      write_results = TRUE,
      protect_repository = TRUE
    ),
    "outputs must remain outside the package repository"
  )
})
